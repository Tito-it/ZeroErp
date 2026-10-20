{% include-markdown "it/dbzero/pratiche/manual/trgfn_calcoli_tempo_set_periodo.md" %}
# ⚙️ Funzione `trgfn_calcoli_tempo_set_periodo`

```sql
CREATE FUNCTION trgfn_calcoli_tempo_set_periodo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_calcoli_tempo_set_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: sync periodo_calcolo tstzrange da data_inizio_calcolo / data_fine_calcolo.
-- Regole:
--   - data_inizio_calcolo NOT NULL (immutabile): periodo sempre valorizzato
--   - data_fine_calcolo NULL = calcolo in corso (infinity)
--   - Bounds '[)' (standard PG per range continui)
BEGIN
    NEW.periodo_calcolo := tstzrange(
        NEW.data_inizio_calcolo,
        COALESCE(NEW.data_fine_calcolo, 'infinity'::timestamptz),
        '[)'
    );
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_calcoli_tempo_set_periodo()
IS 'Sync periodo_calcolo tstzrange da data_inizio_calcolo/data_fine_calcolo. Migrazione daterange.';
```

</div>

---
{% include-markdown "signature-core.md" %}
