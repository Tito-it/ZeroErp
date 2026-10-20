{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_giornale_riattivazione.md" %}
# ⚙️ Funzione `trgfn_sospensioni_giornale_riattivazione`

```sql
CREATE FUNCTION trgfn_sospensioni_giornale_riattivazione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_giornale_riattivazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: registra SOSPENSIONE_CHIUSA nel giornale con data_fine.
BEGIN
    INSERT INTO pratiche.giornale (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
    VALUES (
        NEW.pratica_id,
        NEW.flusso_id,
        'SOSPENSIONE_CHIUSA',
        'SISTEMA',
        jsonb_build_object(
            'sospensione_id', NEW.id,
            'data_inizio', NEW.data_inizio,
            'data_fine', NEW.data_fine,
            'motivo', NEW.motivo,
            'livello', CASE WHEN NEW.flusso_id IS NULL THEN 'PRATICA' ELSE 'FLUSSO' END
        ),
        COALESCE(NEW.tx_id, gen_random_uuid())
    );
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_giornale_riattivazione()
IS 'AFTER UPDATE OF data_fine su sospensioni: registra SOSPENSIONE_CHIUSA nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
