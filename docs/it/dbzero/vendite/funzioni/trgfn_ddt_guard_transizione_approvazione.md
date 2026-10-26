{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_transizione_approvazione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_transizione_approvazione`

```sql
CREATE FUNCTION trgfn_ddt_guard_transizione_approvazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_transizione_approvazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca la transizione a EMESSO di un DDT con componenti
--   BoM CASO A in workflow approvazione prezzo (PENDING) o con
--   prezzo_unitario IS NULL (pending valorizzazione).
--   rev 2026-07-19: valutazione delegata a
--   script.fn_check_ddt_emittibile — single source con la capability.
--   rev 2026-09-24: i motivi del prezzo non autorizzato sono ora
--   E_DOC_PREZZO_PENDENTE ed E_DOC_PREZZO_RIFIUTATO (building block
--   script.fn_check_prezzi_autorizzati), non piu' E_COMPONENTE_PREZZO_PENDENTE
--   (brief-db-preventivi-congelamento-pricing, D-6).
DECLARE
    v_stato_codice config.stati_doc_ddt.codice_interno%TYPE;
    v_motivo       jsonb;
BEGIN
    SELECT sdd.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    IF v_stato_codice IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    FOR v_motivo IN
        SELECT jsonb_array_elements(script.fn_check_ddt_emittibile(NEW))
    LOOP
        -- ⚠️ rev 2026-09-24: i due motivi del prezzo non autorizzato. La
        --   frase porta il CONTEGGIO, che la check emette in `valori`; la
        --   riga e il componente viaggiano nel contesto, per chi diagnostica.
        IF v_motivo->>'codice' = 'E_DOC_PREZZO_PENDENTE' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DOC_PREZZO_PENDENTE',
                jsonb_build_object('ddt_id', NEW.id)
                    || COALESCE(v_motivo->'dettaglio', '{}'::jsonb),
                NEW.tx_id, v_motivo->'valori'->>0
            );
        ELSIF v_motivo->>'codice' = 'E_DOC_PREZZO_RIFIUTATO' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DOC_PREZZO_RIFIUTATO',
                jsonb_build_object('ddt_id', NEW.id)
                    || COALESCE(v_motivo->'dettaglio', '{}'::jsonb),
                NEW.tx_id, v_motivo->'valori'->>0
            );
        ELSIF v_motivo->>'codice' = 'E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE',
                jsonb_build_object('ddt_id', NEW.id,
                    'hint', 'Uno o piu'' componenti BoM CASO A hanno prezzo non valorizzato. '
                         || 'Valorizzare tutti i prezzi prima di emettere il DDT.'),
                NULL::uuid, NEW.id::text
            );
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_transizione_approvazione()
IS 'Blocca la transizione a EMESSO di un DDT con componenti BoM CASO A in approvazione prezzo PENDING (E_COMPONENTE_PREZZO_PENDENTE) o con prezzo non valorizzato (E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE). rev 2026-07-19: valutazione delegata a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt); codici errore invariati. rev 2026-09-24: il prezzo non autorizzato dei componenti solleva E_DOC_PREZZO_PENDENTE o E_DOC_PREZZO_RIFIUTATO — i motivi del building block script.fn_check_prezzi_autorizzati, che fn_check_ddt_emittibile chiede quando la causale vende — con il conteggio nella frase e riga/componente nel contesto. Prima E_COMPONENTE_PREZZO_PENDENTE, solo sul PENDING. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
