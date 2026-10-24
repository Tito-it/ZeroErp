{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_pdp_set_default_stato.md" %}
# ⚙️ Funzione `trgfn_pdp_set_default_stato`

```sql
CREATE FUNCTION trgfn_pdp_set_default_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_set_default_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_disp_id bigint;
BEGIN
   ------------------------------------------------------------
   -- Funzione: anagrafiche.trgfn_pdp_set_default_stato()
   -- Imposta di default lo stato tecnico DISP se non specificato
  ------------------------------------------------------------

    -- Se già impostato, non modificare
    IF NEW.stato_pdp_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Recupera stato tecnico DISPONIBILE
    SELECT id
    INTO v_stato_disp_id
    FROM config.stati_pdp
    WHERE codice_interno = 'DISP';

    IF v_stato_disp_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
                'database',
                'anagrafiche.trgfn_pdp_set_default_stato',
                'E_CODICE',
                jsonb_build_object(
                    'config.stati_pdp: stato DISP non trovato (codice_interno = DISP)', 
                    v_stato_disp_id  
                ),
                new.tx_id,
                'DISP',
                'config.stati_pdp'
            );
    END IF;

    NEW.stato_pdp_id := v_stato_disp_id;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_pdp_set_default_stato()
IS 'Imposta automaticamente lo stato tecnico DISPONIBILE su anagrafiche.pdp
    se non specificato durante  inserimento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
