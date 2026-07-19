{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_causale_emissione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_causale_emissione`

```sql
CREATE FUNCTION trgfn_ddt_guard_causale_emissione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare l'emissione (EMESSO) di un DDT che non dichiara
--   la causale, o che dichiara una causale fatturabile ma ha righe
--   senza prezzo risolvibile (brief-db-fatturazione-ddt-resi §4a,
--   DL-28). rev 2026-07-19: valutazione delegata a
--   script.fn_check_ddt_emittibile — single source con la capability.
DECLARE
    v_stato_codice  config.stati_doc_ddt.codice_interno%TYPE;
    v_motivo        jsonb;
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
        IF v_motivo->>'codice' = 'E_DDT_CAUSALE_OBBLIGATORIA' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_CAUSALE_OBBLIGATORIA',
                jsonb_build_object(
                    'ddt_id', NEW.id,
                    'numero', NEW.numero),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text)
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_PREZZO_NON_RISOLVIBILE' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_PREZZO_NON_RISOLVIBILE',
                jsonb_build_object(
                    'ddt_id',   NEW.id,
                    'numero',   NEW.numero,
                    'riga_id',  (v_motivo->'dettaglio'->>'riga_id')::bigint),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'riga_id', 'NULL')
            );
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
IS 'Gate all''emissione DDT (brief-db-fatturazione-ddt-resi §4a, DL-28): (1) causale di trasporto obbligatoria — in DRAFT il NULL resta legittimo; (2) se la causale e'' fatturabile, ogni riga attiva deve avere un prezzo risolvibile (proprio o ereditato dalla riga ordine via fulfillment). rev 2026-07-19: valutazione delegata a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt); codici errore e argomenti invariati (544/545).';
```

---
{% include-markdown "signature-core.md" %}
