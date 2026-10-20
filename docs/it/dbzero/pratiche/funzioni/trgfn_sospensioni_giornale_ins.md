{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_giornale_ins.md" %}
# ⚙️ Funzione `trgfn_sospensioni_giornale_ins`

```sql
CREATE FUNCTION trgfn_sospensioni_giornale_ins()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_giornale_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: registra SOSPENSIONE_REGISTRATA nel giornale con motivo e date.
BEGIN
    INSERT INTO pratiche.giornale (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
    VALUES (
        NEW.pratica_id,
        NEW.flusso_id,
        'SOSPENSIONE_REGISTRATA',
        'SISTEMA',
        jsonb_build_object(
            'sospensione_id', NEW.id,
            'motivo', NEW.motivo,
            'data_inizio', NEW.data_inizio,
            'data_riattivazione_prevista', NEW.data_riattivazione_prevista,
            'livello', CASE WHEN NEW.flusso_id IS NULL THEN 'PRATICA' ELSE 'FLUSSO' END
        ),
        COALESCE(NEW.tx_id, gen_random_uuid())
    );
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_giornale_ins()
IS 'AFTER INSERT su sospensioni: registra SOSPENSIONE_REGISTRATA nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
