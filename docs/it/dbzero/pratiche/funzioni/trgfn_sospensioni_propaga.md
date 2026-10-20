{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_propaga.md" %}
# ⚙️ Funzione `trgfn_sospensioni_propaga`

```sql
CREATE FUNCTION trgfn_sospensioni_propaga()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_propaga()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: propaga la sospensione pratica ai flussi attivi.
-- Solo per sospensioni a livello pratica (flusso_id IS NULL).
-- I flussi in DA_ESEGUIRE o IN_CORSO passano a SOSPESO.
-- Lo stato precedente viene salvato in meta per il ripristino.
DECLARE
    v_stato_sospeso_id config.stati_flussi_pratiche.id%TYPE;
    v_stati_attivi INTEGER[];
    v_stato_da_eseguire_id config.stati_flussi_pratiche.id%TYPE;
    v_stato_in_corso_id config.stati_flussi_pratiche.id%TYPE;
BEGIN
    -- Solo sospensioni a livello pratica
    IF NEW.flusso_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Recupera gli ID degli stati
    SELECT id INTO v_stato_sospeso_id
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'SOSPESO';

    SELECT id INTO v_stato_da_eseguire_id
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE';

    SELECT id INTO v_stato_in_corso_id
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO';

    v_stati_attivi := ARRAY[v_stato_da_eseguire_id, v_stato_in_corso_id];

    -- Propaga sospensione: passa i flussi attivi a SOSPESO
    UPDATE pratiche.flussi
    SET stato_id = v_stato_sospeso_id
    WHERE pratica_id = NEW.pratica_id
      AND stato_id = ANY(v_stati_attivi);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_propaga()
IS 'AFTER INSERT: propaga sospensione pratica ai flussi attivi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
