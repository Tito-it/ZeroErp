{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_set_data_apertura.md" %}
# ⚙️ Funzione `trgfn_pratiche_set_data_apertura`

```sql
CREATE FUNCTION trgfn_pratiche_set_data_apertura()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: valorizzare data_apertura quando la pratica entra in APERTA,
--   sia per creazione diretta (INSERT con stato APERTA) sia per
--   transizione BOZZA -> APERTA su UPDATE.
-- Regole:
--   1. INSERT con stato APERTA e data_apertura non fornita -> CURRENT_DATE
--   2. UPDATE: solo alla transizione BOZZA -> APERTA
--   3. Immutabile: se data_apertura e' gia' valorizzata, preserva il valore
--   4. Gli id degli stati vengono risolti da config.stati_pratiche
--      tramite codice_interno, mai hardcodati
DECLARE
    v_bozza_id  config.stati_pratiche.id%TYPE;
    v_aperta_id config.stati_pratiche.id%TYPE;
BEGIN
    -- Stato APERTA: serve sia al ramo INSERT che al ramo UPDATE
    SELECT id INTO v_aperta_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'APERTA';

    -- Ramo INSERT: creazione diretta in APERTA.
    -- Valorizza data_apertura solo se non gia' fornita dal chiamante
    -- (immutabilita' anche all'INSERT).
    IF TG_OP = 'INSERT' THEN
        IF NEW.data_apertura IS NULL AND NEW.stato_id = v_aperta_id THEN
            NEW.data_apertura := script.fn_data_operativa();
        END IF;
        RETURN NEW;
    END IF;

    -- Ramo UPDATE: logica preesistente invariata.
    -- Nessuna transizione: niente da fare
    IF OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- Immutabilita': se gia' valorizzata, preserva
    IF OLD.data_apertura IS NOT NULL THEN
        NEW.data_apertura := OLD.data_apertura;
        RETURN NEW;
    END IF;

    SELECT id INTO v_bozza_id
      FROM config.stati_pratiche
     WHERE codice_interno = 'BOZZA';

    -- Transizione BOZZA -> APERTA: valorizza data_apertura
    IF OLD.stato_id = v_bozza_id AND NEW.stato_id = v_aperta_id THEN
        NEW.data_apertura := script.fn_data_operativa();
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
IS 'BEFORE INSERT/UPDATE: valorizza data_apertura quando la pratica entra in APERTA (creazione diretta o transizione BOZZA -> APERTA). Immutabile dopo prima valorizzazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
