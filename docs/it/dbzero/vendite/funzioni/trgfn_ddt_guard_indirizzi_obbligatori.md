{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_indirizzi_obbligatori.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_indirizzi_obbligatori`

```sql
CREATE FUNCTION trgfn_ddt_guard_indirizzi_obbligatori()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare l'emissione (EMESSO) di un DDT privo degli
--   indirizzi marcati obbligatori per l'ambito DDT.
--   rev 2026-07-19: valutazione delegata a
--   script.fn_check_ddt_emittibile — single source con la capability.
DECLARE
    v_stato_codice config.stati_doc_ddt.codice_interno%TYPE;
    v_motivo       jsonb;
    v_mancanti     text[];
BEGIN
    SELECT sdd.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    IF v_stato_codice IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    SELECT m INTO v_motivo
      FROM jsonb_array_elements(script.fn_check_ddt_emittibile(NEW)) AS m
     WHERE m->>'codice' = 'E_INDIRIZZO_DOC_OBBLIGATORIO'
     LIMIT 1;

    IF v_motivo IS NOT NULL THEN
        SELECT array_agg(x) INTO v_mancanti
          FROM jsonb_array_elements_text(v_motivo->'dettaglio'->'mancanti') AS x;

        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_INDIRIZZO_DOC_OBBLIGATORIO',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'ambito',   'DDT',
                'mancanti', v_mancanti),
            NEW.tx_id,
            'DDT',
            NEW.id::text,
            array_to_string(v_mancanti, ', ')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()
IS 'Blocca l''emissione (EMESSO) di un DDT privo degli indirizzi marcati obbligatori per l''ambito DDT (E_INDIRIZZO_DOC_OBBLIGATORIO). rev 2026-07-19: valutazione delegata a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt); codice errore e argomenti invariati.';
```

---
{% include-markdown "signature-core.md" %}
