{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_set_data_apertura.md" %}
# ⚙️ Funzione `trgfn_pratiche_set_data_apertura`

```sql
CREATE FUNCTION trgfn_pratiche_set_data_apertura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: valorizzare data_apertura alla transizione BOZZA → APERTA.
-- Regole:
--   1. Solo alla transizione da BOZZA a APERTA
--   2. Immutabile: se data_apertura e' gia' valorizzata, preserva il valore
--   3. Gli id degli stati vengono risolti da config.stati_pratiche
--      tramite codice_interno, mai hardcodati
DECLARE
    v_bozza_id  config.stati_pratiche.id%TYPE;
    v_aperta_id config.stati_pratiche.id%TYPE;
BEGIN
    -- Nessuna transizione: niente da fare
    IF OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- Immutabilita': se gia' valorizzata, preserva
    IF OLD.data_apertura IS NOT NULL THEN
        NEW.data_apertura := OLD.data_apertura;
        RETURN NEW;
    END IF;

    -- Risolvi id degli stati da codice_interno
    SELECT id INTO v_bozza_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'BOZZA';

    SELECT id INTO v_aperta_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'APERTA';

    -- Transizione BOZZA → APERTA: valorizza data_apertura
    IF OLD.stato_id = v_bozza_id AND NEW.stato_id = v_aperta_id THEN
        NEW.data_apertura := CURRENT_DATE;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
IS 'BEFORE UPDATE OF stato_id: valorizza data_apertura alla transizione BOZZA → APERTA. Immutabile dopo prima valorizzazione.';
```

---
{% include-markdown "signature-core.md" %}
