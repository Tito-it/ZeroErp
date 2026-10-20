{% include-markdown "it/dbzero/pratiche/manual/trgfn_template_flussi_guard_immutabile.md" %}
# ⚙️ Funzione `trgfn_template_flussi_guard_immutabile`

```sql
CREATE FUNCTION trgfn_template_flussi_guard_immutabile()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: immutabilita' strutturale «Leggera» dei template (strategia C).
--   INSERT/UPDATE vietati su edizione forkata emessa (pubblicata o
--   ritirata); DELETE vietato solo su pubblicata (in uso). RITIRATA:
--   non editabile ma cancellabile. descrizione sempre correggibile.
--   Preset e BOZZA liberi.
DECLARE
  v_old_bloccata boolean;
  v_new_bloccata boolean;
  v_def_report   pratiche.workflow_definizioni.id%TYPE;
BEGIN
  IF TG_OP = 'DELETE' THEN
    -- Cancellazione: vietata solo su edizione PUBBLICATA (in uso).
    -- Una RITIRATA-emittente resta cancellabile (housekeeping).
    IF pratiche.fn_check_definizione_congelata(OLD.definizione_id) THEN
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'E_TEMPLATE_DEFINIZIONE_CONGELATA',
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
    -- Inserimento: vietato su edizione emessa (pubblicata o ritirata).
    IF pratiche.fn_check_definizione_struttura_bloccata(NEW.definizione_id) THEN
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'E_TEMPLATE_DEFINIZIONE_CONGELATA',
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
    v_old_bloccata := pratiche.fn_check_definizione_struttura_bloccata(OLD.definizione_id);
    v_new_bloccata := pratiche.fn_check_definizione_struttura_bloccata(NEW.definizione_id);

    -- Blocca se una delle due edizioni (origine/destinazione del
    -- re-parent) e' emessa e cambia qualcosa oltre alla descrizione
    -- (+ audit tecnici esclusi dal confronto).
    IF (v_old_bloccata OR v_new_bloccata)
       AND (to_jsonb(NEW) - 'descrizione' - 'tx_id'
                          - 'data_insert' - 'user_insert'
                          - 'data_update' - 'user_update')
           IS DISTINCT FROM
           (to_jsonb(OLD) - 'descrizione' - 'tx_id'
                          - 'data_insert' - 'user_insert'
                          - 'data_update' - 'user_update')
    THEN
      v_def_report := CASE WHEN v_old_bloccata
                           THEN OLD.definizione_id
                           ELSE NEW.definizione_id END;
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_template_flussi_guard_immutabile',
        'E_TEMPLATE_DEFINIZIONE_CONGELATA',
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
IS 'BEFORE INS/UPD/DEL su pratiche.template_flussi: immutabilita'' strutturale «Leggera» strategia C. INSERT/UPDATE (oltre descrizione) vietati su edizione forkata emessa (pubblicata o ritirata, fn_check_definizione_struttura_bloccata); DELETE vietato solo su pubblicata (fn_check_definizione_congelata) -> RITIRATA cancellabile. Errore TEMPLATE_DEFINIZIONE_CONGELATA (514). Preset (emittente NULL) e BOZZA editabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
