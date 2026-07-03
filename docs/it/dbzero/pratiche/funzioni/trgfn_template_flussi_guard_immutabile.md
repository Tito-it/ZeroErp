{% include-markdown "it/dbzero/pratiche/manual/trgfn_template_flussi_guard_immutabile.md" %}
# ⚙️ Funzione `trgfn_template_flussi_guard_immutabile`

```sql
CREATE FUNCTION trgfn_template_flussi_guard_immutabile()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: immutabilita' strutturale «Leggera» dei template su fork
--        PUBBLICATO. INSERT/DELETE vietati; UPDATE vietato se tocca
--        una colonna diversa da descrizione. Preset e BOZZA/RITIRATA
--        restano liberi.
DECLARE
  v_old_congelata boolean;
  v_new_congelata boolean;
  v_def_report    pratiche.workflow_definizioni.id%TYPE;
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF pratiche.fn_check_definizione_congelata(OLD.definizione_id) THEN
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'TEMPLATE_DEFINIZIONE_CONGELATA',
        jsonb_build_object(
          'operazione',        'DELETE',
          'tabella',           'template_flussi',
          'template_flusso_id', OLD.id,
          'codice',             OLD.codice,
          'definizione_id',     OLD.definizione_id
        ),
        OLD.tx_id,
        OLD.definizione_id::text
      );
    END IF;
    RETURN OLD;

  ELSIF TG_OP = 'INSERT' THEN
    IF pratiche.fn_check_definizione_congelata(NEW.definizione_id) THEN
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'TEMPLATE_DEFINIZIONE_CONGELATA',
        jsonb_build_object(
          'operazione',     'INSERT',
          'tabella',        'template_flussi',
          'codice',         NEW.codice,
          'definizione_id', NEW.definizione_id
        ),
        NEW.tx_id,
        NEW.definizione_id::text
      );
    END IF;
    RETURN NEW;

  ELSE  -- UPDATE
    v_old_congelata := pratiche.fn_check_definizione_congelata(OLD.definizione_id);
    v_new_congelata := pratiche.fn_check_definizione_congelata(NEW.definizione_id);

    -- Se una delle due edizioni (origine o destinazione del re-parent)
    -- e' congelata, blocca ogni cambiamento che non sia solo la
    -- descrizione. Il confronto esclude descrizione + audit tecnici;
    -- qualunque altra colonna (compreso il re-parent definizione_id)
    -- ricade nel diff => bloccata.
    IF (v_old_congelata OR v_new_congelata)
       AND (to_jsonb(NEW) - 'descrizione' - 'tx_id'
                          - 'data_insert' - 'user_insert'
                          - 'data_update' - 'user_update')
           IS DISTINCT FROM
           (to_jsonb(OLD) - 'descrizione' - 'tx_id'
                          - 'data_insert' - 'user_insert'
                          - 'data_update' - 'user_update')
    THEN
      v_def_report := CASE WHEN v_old_congelata
                           THEN OLD.definizione_id
                           ELSE NEW.definizione_id END;
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'TEMPLATE_DEFINIZIONE_CONGELATA',
        jsonb_build_object(
          'operazione',        'UPDATE',
          'tabella',           'template_flussi',
          'template_flusso_id', NEW.id,
          'codice',             NEW.codice,
          'definizione_id',     v_def_report
        ),
        NEW.tx_id,
        v_def_report::text
      );
    END IF;
    RETURN NEW;
  END IF;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()
IS 'BEFORE INS/UPD/DEL su pratiche.template_flussi: immutabilita'' strutturale «Leggera» (Fase 2b). Su edizione forkata pubblicata (fn_check_definizione_congelata) blocca INSERT/DELETE e ogni UPDATE che tocchi una colonna diversa da descrizione (audit esclusi) -> TEMPLATE_DEFINIZIONE_CONGELATA (514). Preset (emittente NULL) e BOZZA/RITIRATA restano editabili.';
```

---
{% include-markdown "signature-core.md" %}
