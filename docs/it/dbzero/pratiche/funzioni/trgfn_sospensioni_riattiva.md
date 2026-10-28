{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_riattiva.md" %}
# ⚙️ Funzione `trgfn_sospensioni_riattiva`

```sql
CREATE FUNCTION trgfn_sospensioni_riattiva()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_riattiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: ripristina gli stati precedenti alla riattivazione.
-- Solo per sospensioni a livello pratica (flusso_id IS NULL).
-- I flussi SOSPESO tornano allo stato che avevano prima della sospensione
-- (recuperato dal giornale). La pratica torna ad APERTA.
DECLARE
    v_stato_aperta_id config.stati_pratiche.id%TYPE;
    v_stato_sospeso_id config.stati_flussi_pratiche.id%TYPE;
    v_flusso RECORD;
    v_stato_precedente_id INTEGER;
BEGIN
    -- Solo quando data_fine passa da NULL a valorizzata (chiusura sospensione)
    IF OLD.data_fine IS NOT NULL OR NEW.data_fine IS NULL THEN
        RETURN NEW;
    END IF;

    -- Solo sospensioni a livello pratica
    IF NEW.flusso_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Recupera ID stato APERTA per la pratica
    SELECT id INTO v_stato_aperta_id
    FROM config.stati_pratiche WHERE codice_interno = 'APERTA';

    -- Recupera ID stato SOSPESO per i flussi
    SELECT id INTO v_stato_sospeso_id
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'SOSPESO';

    -- Ripristina la pratica ad APERTA
    UPDATE pratiche.pratiche
    SET stato_id = v_stato_aperta_id
    WHERE id = NEW.pratica_id;

    -- Ripristina ogni flusso SOSPESO al suo stato precedente
    FOR v_flusso IN
        SELECT f.id
        FROM pratiche.flussi f
        WHERE f.pratica_id = NEW.pratica_id
          AND f.stato_id = v_stato_sospeso_id
    LOOP
        -- Cerca lo stato precedente nel giornale (ultimo FLUSSO_STATO_CAMBIATO
        -- prima della sospensione, con stato_nuovo = SOSPESO)
        SELECT (g.dettaglio->>'stato_precedente_id')::INTEGER
        INTO v_stato_precedente_id
        FROM pratiche.giornale g
        WHERE g.flusso_id = v_flusso.id
          AND g.azione = 'FLUSSO_STATO_CAMBIATO'
          AND (g.dettaglio->>'stato_nuovo_id')::INTEGER = v_stato_sospeso_id
        ORDER BY g.data_insert DESC
        LIMIT 1;

        IF v_stato_precedente_id IS NOT NULL THEN
            UPDATE pratiche.flussi
            SET stato_id = v_stato_precedente_id
            WHERE id = v_flusso.id;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_riattiva()
IS 'AFTER UPDATE OF data_fine: ripristina stati flussi e pratica alla riattivazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
