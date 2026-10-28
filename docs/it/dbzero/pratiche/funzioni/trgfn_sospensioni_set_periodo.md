{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_set_periodo.md" %}
# ⚙️ Funzione `trgfn_sospensioni_set_periodo`

```sql
CREATE FUNCTION trgfn_sospensioni_set_periodo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_set_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: sync periodo_sospensione tstzrange da data_inizio / data_fine.
-- Regole:
--   - data_inizio NOT NULL (sempre): periodo sempre valorizzato
--   - data_fine NULL = sospensione attiva (infinity)
--   - Bounds '[)' (standard PG per range continui)
BEGIN
    NEW.periodo_sospensione := tstzrange(
        NEW.data_inizio,
        COALESCE(NEW.data_fine, 'infinity'::timestamptz),
        '[)'
    );
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_set_periodo()
IS 'Sync periodo_sospensione tstzrange da data_inizio/data_fine. Migrazione daterange.';
```

</div>

---
{% include-markdown "signature-core.md" %}
