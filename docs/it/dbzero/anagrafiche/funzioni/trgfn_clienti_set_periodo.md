{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_set_periodo.md" %}
# ⚙️ Funzione `trgfn_clienti_set_periodo`

```sql
CREATE FUNCTION trgfn_clienti_set_periodo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_set_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
fine_esclusiva DATE;
v_codice_stato config.stati_cliente.codice_interno%TYPE;
BEGIN
-- Trigger function: normalizza "periodo" = [data_attivazione, data_chiusura)  
-- Inclusività della data_chiusura: se valorizzata, usiamo come estremo esclusivo

-- recupero codice interno stato cliente
    SELECT sc.codice_interno
    INTO v_codice_stato
    FROM config.stati_cliente sc
    WHERE sc.id = NEW.stato_cliente_id;


-- controlli di coerenza date in base allo stato cliente

    -- in caso di annullamento, azzero date e periodo                   
    IF v_codice_stato = 'AN' THEN
        -- annullato: nessuna data, nessun periodo
        NEW.data_attivazione := NULL;
        NEW.data_chiusura    := NULL;
        NEW.periodo          := NULL;
        RETURN NEW;
    END IF;

    -- in caso di chiusura, data_chiusura deve essere valorizzata 
    -- e >= data_attivazione
    IF v_codice_stato = 'CH' and NEW.data_attivazione IS NOT NULL THEN
        IF NEW.data_chiusura < NEW.data_attivazione THEN

            PERFORM script.fn_log_and_raise_error(
                          'CLIENTI',
                          'anagrafiche.trgfn_clienti_set_periodo',
                          'E_DATA_CHIUSURA',
                          jsonb_build_object(
                              'campo', 'data_chiusura',
                              'data_chiusura', NEW.data_chiusura,
                              'data_attivazione', NEW.data_attivazione,
                              'cliente_id', NEW.id
                          ),
                          new.tx_id,
                          NEW.data_chiusura::text, NEW.data_attivazione::text, 
                          NEW.id::text
                      );   
        END IF;
    END IF;

    -- in caso di attivazione, data_attivazione deve essere valorizzata
    IF v_codice_stato = 'AT' and NEW.data_attivazione IS NULL THEN

        PERFORM script.fn_log_and_raise_error(
                          'CLIENTI',
                          'anagrafiche.trgfn_clienti_set_periodo',
                          'E_DATA_APERTURA',
                          jsonb_build_object(
                              'campo', 'data_attivazione',
                              'cliente_id', NEW.id
                          ),
                          new.tx_id,
                          NEW.id::text
                      );   
    END IF;

-- calcolo periodo [data_attivazione, data_chiusura)
fine_esclusiva := CASE
    WHEN NEW.data_chiusura IS NULL THEN 'infinity'::date
    ELSE NEW.data_chiusura 
END;

IF NEW.data_attivazione IS NOT NULL THEN
    NEW.periodo := daterange(NEW.data_attivazione, fine_esclusiva, '[)');
ELSE
    NEW.periodo := NULL;
END IF;

RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_set_periodo()
IS 'Imposta periodo = [data_attivazione, data_chiusura] 
     per modellare fine inclusiva in un range con estremo destro esclusivo. imposta
     controlli di coerenza date in base allo stato cliente.
     Solo per stati AT, CH, AN.';
```

---
{% include-markdown "signature-core.md" %}
