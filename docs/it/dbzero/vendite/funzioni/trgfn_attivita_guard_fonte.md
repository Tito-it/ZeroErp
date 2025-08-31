# ⚙️ Funzione `trgfn_attivita_guard_fonte`

```sql
CREATE FUNCTION trgfn_attivita_guard_fonte()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_guard_fonte()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE v_fonte TEXT;
BEGIN



  SELECT r.fonte_quantita
    INTO v_fonte
  FROM vendite.regole_fatturazione_articolo r
  WHERE r.prodotto_id = NEW.articolo_id;

  IF v_fonte IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',                              
        'attivita_fatturabili',                 
        'E_REGOLA_FATTURAZIONE_MANCANTE',       
        jsonb_build_object(
          'context', 'inserimento/aggiornamento attivita_fatturabili',
          'articolo_id', NEW.articolo_id
        ),
        NULL::uuid,
        NEW.articolo_id
      );    
  END IF;

  
  
  IF v_fonte NOT IN ('TIMESHEET','MANUALE','FISSA') THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'attivita_fatturabili',
      'E_FONTE_QUANTITA_NON_VALIDA',
      jsonb_build_object(
        'context','validazione fonte_quantita',
        'fonte_quantita', v_fonte,
        'articolo_id', NEW.articolo_id
      ),
     NULL::uuid,
     v_fonte, NEW.articolo_id
    );
  END IF;

  
  IF NEW.competenza_mese IS NOT NULL
    AND date_trunc('month', NEW.data_attivita)::date > NEW.competenza_mese THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'attivita_fatturabili',
      'E_COMPETENZA_SUPERATA',
      jsonb_build_object(
        'context','validazione competenza',
        'data_attivita', NEW.data_attivita,
        'competenza_mese', NEW.competenza_mese
      ),
     NULL::uuid,
    NEW.data_attivita, NEW.competenza_mese
    );
  END IF;

  
  IF NEW.competenza_data IS NOT NULL
    AND  NEW.data_attivita > NEW.competenza_data THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'attivita_fatturabili',
      'E_COMPETENZA_SUPERATA',
      jsonb_build_object(
        'context','validazione competenza',
        'data_attivita', NEW.data_attivita,
        'competenza_data', NEW.competenza_data
      ),
     NULL::uuid,
    NEW.data_attivita, NEW.competenza_data
    );
  END IF;

  
  IF NEW.competenza_data IS NOT NULL 
    AND  NEW.competenza_mese IS NOT NULL
  THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'attivita_fatturabili',
      'E_COMPETENZA',
      jsonb_build_object(
        'context','validazione competenza',
        'competenza mese', NEW.competenza_mese,
        'competenza_data', NEW.competenza_data
      ),
     NULL::uuid,
    NEW.competenza_mese, NEW.competenza_data
    );
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
