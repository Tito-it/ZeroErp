{% include-markdown "it/dbzero/documenti/manual/fn_pubblica_template_documento_versione.md" %}
# ⚙️ Funzione `fn_pubblica_template_documento_versione`

```sql
CREATE FUNCTION fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
--     (documenti.fn_guard_versione_contesto).
--     Una BOZZA puo' dichiarare una forma che il builder non produce
--     ancora: il controllo e' qui, non sulla bozza;
--   - l'ordine delle date (p_valido_al non precede p_valido_dal) NON si
--     giudica qui: lo giudica il guard comune script.trgfn_guard_date_validita
--     sull'UPDATE della versione;
--   - prima della pubblicazione vengono rese OBSOLETE e chiuse a
--     p_valido_dal - 1 le versioni PUBBLICATE attive dello stesso
--     template con valido_dal < p_valido_dal e intervallo sovrapposto.
--     Una OBSOLETA stampa fino al suo valido_al: che cosa stampa lo
--     decide la validita' (documenti.vw_template_versioni_stampabili);
--   - la chiusura e' una scrittura sola, sotto la porta
--     zeroerp.allow_template_versione_chiusura_override: il Guard A1
--     protegge PUBBLICATA e OBSOLETA, e ammette solo questa forma;
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

    -- Il patto versione/forma dei dati: prima di toccare qualunque
    -- altra versione, cosi' un rifiuto non lascia niente a meta' da
    -- annullare. La riga e' gia' sotto FOR UPDATE: la forma letta dal
    -- guard non puo' cambiare fino al commit.
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
             -- La finestra nuova e' [p_valido_dal, oltre). Una versione
             --   che parte PRIMA di p_valido_dal si sovrappone alla nuova
             --   se e solo se e' ancora aperta a p_valido_dal: p_valido_al
             --   non conta. Un daterange(p_valido_dal, p_valido_al) qui
             --   solleverebbe 22000 con le date invertite PRIMA che
             --   l'UPDATE incontri il guard comune delle date.
             AND v.validita && daterange(p_valido_dal, NULL, '[)')
           ORDER BY v.valido_dal, v.id
           FOR UPDATE
      ) c;

    -- Calcola subito: evita GET DIAGNOSTICS post-UPDATE.
    v_closed_count := COALESCE(array_length(v_closed_ids, 1), 0);

    IF v_closed_count > 0 THEN
        -- Una scrittura sola, stato e data insieme: il Guard A1 protegge
        -- PUBBLICATA e OBSOLETA, e a porta aperta ammette solo questa
        -- forma (PUBBLICATA -> OBSOLETA, valido_al accorciato). La porta
        -- si apre qui, dopo la scelta delle versioni, e si richiude
        -- subito: nessun'altra scrittura della transazione la trova aperta.
        PERFORM set_config('zeroerp.allow_template_versione_chiusura_override', 'on', true);

        UPDATE documenti.template_documenti_versioni
           SET stato     = 'OBSOLETA',
               valido_al = p_valido_dal - 1
         WHERE id = ANY(v_closed_ids);

        PERFORM set_config('zeroerp.allow_template_versione_chiusura_override', 'off', true);
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
IS 'Pubblica una versione template BOZZA e chiude, nella stessa transazione, le versioni PUBBLICATE precedenti sovrapposte: OBSOLETE con fine al giorno prima della nuova, e stampabili fino a quel giorno (documenti.vw_template_versioni_stampabili). La chiusura passa dal Guard A1 a porta zeroerp.allow_template_versione_chiusura_override aperta. p_versione_contesto (obbligatorio) e'' la forma dei dati che il builder produce: la versione si pubblica solo se dichiara di leggere quella forma (documenti.fn_guard_versione_contesto: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA). L''ordine delle date lo giudica il guard comune script.trgfn_guard_date_validita sull''UPDATE della versione (E_DATA_AL_MINORE_DAL).';
```

</div>

---
{% include-markdown "signature-core.md" %}
