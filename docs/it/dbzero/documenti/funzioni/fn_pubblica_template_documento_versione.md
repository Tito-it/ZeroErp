{% include-markdown "it/dbzero/documenti/manual/fn_pubblica_template_documento_versione.md" %}
# ⚙️ Funzione `fn_pubblica_template_documento_versione`

```sql
CREATE FUNCTION fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date DEFAULT NULL::date)
 RETURNS TABLE(versione_id bigint, template_documento_id bigint, versioni_obsolete integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Pubblica una versione template documento in modo atomico.
--
-- Regole:
--   - la versione target deve esistere ed essere BOZZA;
--   - p_valido_dal e' obbligatorio;
--   - p_versione_contesto e' la forma dei dati che il builder del
--     backend produce per quel tipo di documento: la versione si
--     pubblica solo se dichiara di leggere quella forma
--     (documenti.fn_guard_versione_contesto, rev 20260930-21).
--     Una BOZZA puo' dichiarare una forma che il builder non produce
--     ancora (D-C4): il controllo e' qui, non sulla bozza;
--   - l'ordine delle date (p_valido_al non precede p_valido_dal) NON si
--     giudica qui: lo giudica il guard comune script.trgfn_guard_date_validita
--     sull'UPDATE della versione (rev 20260924-02: ritirata la copia sui
--     parametri, che rispondeva con E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO);
--   - prima della pubblicazione vengono rese OBSOLETE e chiuse a
--     p_valido_dal - 1 le versioni PUBBLICATE attive dello stesso
--     template con valido_dal < p_valido_dal e intervallo sovrapposto;
--   - il vincolo EXCLUDE resta il guardrail finale contro overlap
--     residui o race concorrenti.
DECLARE
    v_template_id  documenti.template_documenti_versioni.template_documento_id%TYPE;
    v_stato        documenti.template_documenti_versioni.stato%TYPE;
    -- id di documenti.template_documenti_versioni: %TYPE[] non e' sintassi valida
    v_closed_ids   bigint[] := ARRAY[]::bigint[];
    -- un conteggio: nessuna colonna di cui sia il riflesso
    v_closed_count integer  := 0;
BEGIN
    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            'versione_id deve essere un intero positivo'
        );
    END IF;

    IF p_valido_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('campo', 'valido_dal', 'versione_id', p_versione_id),
            NULL::uuid,
            'valido_dal e'' obbligatorio'
        );
    END IF;

    SELECT v.template_documento_id, v.stato
      INTO v_template_id, v_stato
      FROM documenti.template_documenti_versioni v
     WHERE v.id = p_versione_id
     FOR UPDATE;

    IF v_template_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_NOT_FOUND',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            p_versione_id::text
        );
    END IF;

    IF v_stato <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
            jsonb_build_object(
                'versione_id',   p_versione_id,
                'stato_corrente', v_stato
            ),
            NULL::uuid,
            p_versione_id::text, v_stato
        );
    END IF;

    -- Il patto versione/forma dei dati (rev 20260930-21): prima di
    -- toccare qualunque altra versione, cosi' un rifiuto non lascia
    -- niente a meta' da annullare. La riga e' gia' sotto FOR UPDATE:
    -- la forma letta dal guard non puo' cambiare fino al commit.
    PERFORM documenti.fn_guard_versione_contesto(p_versione_id, p_versione_contesto);

    -- Lock ordinato di tutte le versioni del template: evita race fra
    -- due pubblicazioni concorrenti dello stesso template.
    PERFORM 1
      FROM documenti.template_documenti_versioni v
     WHERE v.template_documento_id = v_template_id
     ORDER BY v.id
     FOR UPDATE;

    SELECT COALESCE(array_agg(c.id ORDER BY c.valido_dal, c.id), ARRAY[]::bigint[])
      INTO v_closed_ids
      FROM (
          SELECT v.id, v.valido_dal
            FROM documenti.template_documenti_versioni v
           WHERE v.template_documento_id = v_template_id
             AND v.id <> p_versione_id
             AND v.stato = 'PUBBLICATA'
             AND v.attivo IS TRUE
             AND v.valido_dal < p_valido_dal
             -- ⚠️ rev 20260924-02: la finestra nuova e' [p_valido_dal, oltre).
             --   Una versione che parte PRIMA di p_valido_dal si sovrappone
             --   alla nuova se e solo se e' ancora aperta a p_valido_dal:
             --   p_valido_al non conta. Prima qui si costruiva
             --   daterange(p_valido_dal, p_valido_al): con le date invertite
             --   sollevava 22000 (limite inferiore > superiore) PRIMA che
             --   l'UPDATE incontrasse il guard comune delle date.
             AND v.validita && daterange(p_valido_dal, NULL, '[)')
           ORDER BY v.valido_dal, v.id
           FOR UPDATE
      ) c;

    -- Calcola subito: evita GET DIAGNOSTICS post-UPDATE.
    v_closed_count := COALESCE(array_length(v_closed_ids, 1), 0);

    IF v_closed_count > 0 THEN
        -- Il trigger A1 blocca UPDATE OF valido_al quando OLD.stato = PUBBLICATA.
        -- Step 1: porta a OBSOLETA (colonna stato non e' nell''UPDATE OF' del trigger).
        -- Step 2: aggiorna valido_al (ora OLD.stato = OBSOLETA, trigger non blocca).
        UPDATE documenti.template_documenti_versioni
           SET stato = 'OBSOLETA'
         WHERE id = ANY(v_closed_ids);

        UPDATE documenti.template_documenti_versioni
           SET valido_al = p_valido_dal - 1
         WHERE id = ANY(v_closed_ids);
    END IF;

    UPDATE documenti.template_documenti_versioni
       SET stato      = 'PUBBLICATA',
           valido_dal = p_valido_dal,
           valido_al  = p_valido_al
     WHERE id    = p_versione_id
       AND stato = 'BOZZA';

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
            jsonb_build_object(
                'versione_id',    p_versione_id,
                'stato_corrente', v_stato
            ),
            NULL::uuid,
            p_versione_id::text, v_stato
        );
    END IF;

    versione_id           := p_versione_id;
    template_documento_id := v_template_id;
    versioni_obsolete     := v_closed_count;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
IS 'Pubblica una versione template documento con auto-close atomico delle versioni PUBBLICATE precedenti sovrapposte. Rev 20260930-21: p_versione_contesto (obbligatorio) e'' la forma dei dati che il builder produce; la versione si pubblica solo se dichiara di leggere quella forma (documenti.fn_guard_versione_contesto: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA). Rev 20260924-02: l''ordine delle date non e'' piu'' giudicato sui parametri: lo giudica il guard comune script.trgfn_guard_date_validita sull''UPDATE della versione (E_DATA_AL_MINORE_DAL).';
```

</div>

---
{% include-markdown "signature-core.md" %}
