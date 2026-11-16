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
--   Pubblica una versione template documento in modo atomico. E'
--   l'unica strada per cui una versione esce dalla bozza.
--
-- Regole:
--   - la versione target deve esistere, essere BOZZA ed essere
--     accesa: una bozza spenta pubblicata non stamperebbe, e
--     chiuderebbe la versione che stampa;
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
--   - le due scritture (la chiusura, la pubblicazione) passano sotto la
--     porta zeroerp.allow_template_versione_pubblicazione_override: il
--     guard dello stato (trgfn_template_documenti_versioni_protect_pubblicata)
--     a porta aperta ammette solo queste due forme. La porta si apre
--     dopo la scelta delle versioni e si richiude prima di uscire,
--     anche in errore;
--   - il vincolo EXCLUDE resta il guardrail finale contro overlap
--     residui o race concorrenti.
DECLARE
    v_template_id  documenti.template_documenti_versioni.template_documento_id%TYPE;
    v_stato        documenti.template_documenti_versioni.stato%TYPE;
    v_attivo       documenti.template_documenti_versioni.attivo%TYPE;
    v_versione     documenti.template_documenti_versioni.versione%TYPE;
    v_modello      documenti.template_documenti.descrizione%TYPE;
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

    SELECT v.template_documento_id, v.stato, v.attivo, v.versione, t.descrizione
      INTO v_template_id, v_stato, v_attivo, v_versione, v_modello
      FROM documenti.template_documenti_versioni v
      JOIN documenti.template_documenti t ON t.id = v.template_documento_id
     WHERE v.id = p_versione_id
     FOR UPDATE OF v;

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

    -- Una bozza spenta non stampa: pubblicarla chiuderebbe la
    -- versione che stampa e lascerebbe il modello senza stampa.
    IF v_attivo IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_SPENTA',
            jsonb_build_object(
                'versione_id',           p_versione_id,
                'template_documento_id', v_template_id,
                'versione',              v_versione
            ),
            NULL::uuid,
            v_versione::text, v_modello::text
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

    -- Le due scritture del verbo, sotto la sua porta. Si apre qui,
    -- dopo la scelta delle versioni, e si richiude prima di uscire:
    -- nel blocco EXCEPTION anche in errore, perche' il terzo argomento
    -- di set_config lega il valore alla transazione, non alla chiamata.
    BEGIN
        PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', 'on', true);

        IF v_closed_count > 0 THEN
            -- Una scrittura sola, stato e data insieme: a porta aperta il
            -- guard ammette solo questa forma (PUBBLICATA -> OBSOLETA,
            -- valido_al accorciato).
            UPDATE documenti.template_documenti_versioni
               SET stato     = 'OBSOLETA',
                   valido_al = p_valido_dal - 1
             WHERE id = ANY(v_closed_ids);
        END IF;

        -- A porta aperta il guard ammette solo BOZZA -> PUBBLICATA con
        -- le sole date cambiate.
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

        PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', 'off', true);
    EXCEPTION WHEN OTHERS THEN
        PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', 'off', true);
        RAISE;
    END;

    versione_id           := p_versione_id;
    template_documento_id := v_template_id;
    versioni_obsolete     := v_closed_count;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
IS 'Pubblica una versione template BOZZA, ed e'' l''unica strada per cui una versione esce dalla bozza. Nella stessa transazione chiude le versioni PUBBLICATE precedenti sovrapposte: OBSOLETE con fine al giorno prima della nuova, e stampabili fino a quel giorno (documenti.vw_template_versioni_stampabili). Le due scritture passano sotto la porta zeroerp.allow_template_versione_pubblicazione_override, che il guard dello stato (documenti.trgfn_template_documenti_versioni_protect_pubblicata) chiede e che il verbo richiude prima di uscire, anche in errore. Rifiuti: parametri mancanti (E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO), versione inesistente (E_DOCUMENTI_VERSIONE_NOT_FOUND), non in bozza (E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO), bozza spenta (E_DOCUMENTI_VERSIONE_PUBBLICA_SPENTA: non stamperebbe, e chiuderebbe la versione che stampa). p_versione_contesto (obbligatorio) e'' la forma dei dati che il builder produce: la versione si pubblica solo se dichiara di leggere quella forma (documenti.fn_guard_versione_contesto: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA). L''ordine delle date lo giudica il guard comune script.trgfn_guard_date_validita sull''UPDATE della versione (E_DATA_AL_MINORE_DAL); una sovrapposizione che la chiusura non risolve (stesso inizio di una versione fuori bozza, inizio dentro una OBSOLETA) la ferma il vincolo ex_template_documenti_versioni_no_overlap_pubblicata (23P01).';
```

</div>

---
{% include-markdown "signature-core.md" %}
