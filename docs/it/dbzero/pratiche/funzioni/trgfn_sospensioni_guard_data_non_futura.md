{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_guard_data_non_futura.md" %}
# ⚙️ Funzione `trgfn_sospensioni_guard_data_non_futura`

```sql
CREATE FUNCTION trgfn_sospensioni_guard_data_non_futura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_guard_data_non_futura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: vieta date di sospensione/riattivazione nel futuro.
-- data_inizio e data_fine non possono superare now() + tolleranza
-- clock-skew (2 min). data_riattivazione_prevista (previsione) esclusa.
DECLARE
    v_limite pratiche.sospensioni.data_inizio%TYPE := now() + interval '2 minutes';
BEGIN
    IF NEW.data_inizio > v_limite THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_sospensioni_guard_data_non_futura',
            'E_SOSPENSIONE_DATA_FUTURA',
            jsonb_build_object('campo', 'data_inizio', 'valore', NEW.data_inizio, 'now', now()),
            NULL::uuid,
            NEW.data_inizio::text
        );
    END IF;

    IF NEW.data_fine IS NOT NULL AND NEW.data_fine > v_limite THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_sospensioni_guard_data_non_futura',
            'E_SOSPENSIONE_DATA_FUTURA',
            jsonb_build_object('campo', 'data_fine', 'valore', NEW.data_fine, 'now', now()),
            NULL::uuid,
            NEW.data_fine::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_guard_data_non_futura()
IS 'Guard: vieta data_inizio/data_fine nel futuro su sospensioni (tolleranza clock-skew 2 min). Non tocca data_riattivazione_prevista.';
```

</div>

---
{% include-markdown "signature-core.md" %}
