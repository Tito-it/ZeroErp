{% include-markdown "it/dbzero/vendite/manual/fn_execute_pipeline_step.md" %}
# ⚙️ Funzione `fn_execute_pipeline_step`

```sql
CREATE FUNCTION fn_execute_pipeline_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_rollback boolean, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_execute_pipeline_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_rollback boolean DEFAULT false, p_dry_run boolean DEFAULT false)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_processi jsonb;
  v_task text;
  v_fase text;
  v_params jsonb;
  v_fn text;
  v_competenza vendite.fatturazione_lotti.competenza_mese%TYPE;
  v_tipo_doc_fiscale_id config.tipi_doc_fiscale.id%TYPE;
  v_utility_id config.utilities.id%TYPE;
  v_billing_account_id anagrafiche.billing_account.id%TYPE;
  v_lock_batch_id vendite.fatturazione_lotti.lock_batch_id%TYPE;
  v_data_fatturazione date;
  v_lock boolean;
  v_valuta_id config.valute.id%TYPE;
  v_emittente_id anagrafiche.soggetti_ruoli.id%TYPE;
  v_limit integer;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Esegue i task di uno step pipeline leggendo la tabella
  --   vendite.fatturazione_pipeline (processi o rollback).
  --
  -- Regole:
  --   - nessuna esecuzione di SQL arbitrario (whitelist task).
  --   - se p_dry_run=true, logga solo le fasi.
  -- =========================================================

  IF p_lotto_id IS NULL OR p_stato_doc_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_execute_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail','lotto_id e stato_doc_fiscale_id obbligatori'),
      NULL::uuid, 'Parametri obbligatori mancanti'
    );
  END IF;

  SELECT competenza_mese,
         tipo_doc_fiscale_id,
         utility_id,
         billing_account_id,
         lock_batch_id
    INTO v_competenza,
         v_tipo_doc_fiscale_id,
         v_utility_id,
         v_billing_account_id,
         v_lock_batch_id
    FROM vendite.fatturazione_lotti
   WHERE id = p_lotto_id;

  IF v_competenza IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_execute_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail','lotto non trovato', 'lotto_id', p_lotto_id),
      NULL::uuid, 
      concat('Lotto non trovato', ' lotto_id:', p_lotto_id)
    );
  END IF;

  SELECT CASE WHEN p_rollback THEN rollback ELSE processi END
    INTO v_processi
    FROM vendite.fatturazione_pipeline
   WHERE stato_doc_fiscale_id = p_stato_doc_fiscale_id
     AND attivo IS TRUE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_execute_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail','pipeline non trovata', 'stato_doc_fiscale_id', p_stato_doc_fiscale_id),
      NULL::uuid, 
      concat('Pipeline non trovata', ' stato_doc_fiscale_id:', p_stato_doc_fiscale_id)  
    );
  END IF;

  IF v_processi IS NULL OR jsonb_typeof(v_processi) <> 'array' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_execute_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail','processi non validi', 'stato_doc_fiscale_id', p_stato_doc_fiscale_id),
      NULL::uuid, 
      concat('Processi non validi', ' stato_doc_fiscale_id:', p_stato_doc_fiscale_id)
    );
  END IF;

  FOR v_task, v_fase, v_params IN
    SELECT
      COALESCE(elem->>'task',''),
      NULLIF(elem->>'fase',''),
      COALESCE(elem->'params','{}'::jsonb)
    FROM jsonb_array_elements(v_processi) elem
  LOOP
    v_fn := NULLIF(v_params->>'fn','');

    PERFORM vendite.fn_log_pipeline_fase(
      p_lotto_id,
      p_stato_doc_fiscale_id,
      v_fase,
      'I',
      NULL,
      jsonb_build_object(
        'task', v_task,
        'params', v_params,
        'rollback', p_rollback,
        'dry_run', p_dry_run
      )
    );

    IF p_dry_run THEN
      CONTINUE;
    END IF;

    IF v_task IN ('noop','log_only') THEN
      CONTINUE;
    END IF;

    IF v_task = 'select_attivita' THEN
      v_lock := COALESCE((v_params->>'lock')::boolean, false);
      v_data_fatturazione := COALESCE((v_params->>'data_fatturazione')::date, CURRENT_DATE);
      v_valuta_id := NULLIF(v_params->>'valuta_id','')::bigint;
      v_emittente_id := NULLIF(v_params->>'emittente_soggetto_ruolo_id','')::bigint;
      v_limit := NULLIF(v_params->>'limit','')::integer;

      IF v_fn IS NULL THEN
        PERFORM vendite.fn_select_attivita_fatturabili(
          p_competenza_mese => v_competenza,
          p_tipo_doc_fiscale_id => v_tipo_doc_fiscale_id,
          p_lock_batch_id => CASE WHEN v_lock THEN v_lock_batch_id ELSE NULL END,
          p_lock => v_lock,
          p_data_fatturazione => v_data_fatturazione,
          p_billing_account_id => v_billing_account_id,
          p_utility_id => v_utility_id,
          p_valuta_id => v_valuta_id,
          p_emittente_soggetto_ruolo_id => v_emittente_id,
          p_limit => v_limit
        );
      ELSE
        -- whitelist funzione esplicita (override)
        IF v_fn <> 'vendite.fn_select_attivita_fatturabili' THEN
          PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_execute_pipeline_step', 'E_TASK_NOT_ALLOWED',
            jsonb_build_object('fn', v_fn, 'task', v_task),
            NULL::uuid, 
            concat('Funzione non ammessa', ' fn:', v_fn)
          );
        END IF;

        EXECUTE format(
          'SELECT %s(%L,%L,%L,%L,%L,%L,%L,%L,%L,%L)',
          v_fn,
          v_competenza,
          v_tipo_doc_fiscale_id,
          CASE WHEN v_lock THEN v_lock_batch_id ELSE NULL END,
          v_lock,
          v_data_fatturazione,
          v_billing_account_id,
          v_utility_id,
          v_valuta_id,
          v_emittente_id,
          v_limit
        );
      END IF;

      CONTINUE;
    END IF;

    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_execute_pipeline_step', 'E_TASK_NOT_IMPLEMENTED',
      jsonb_build_object('task', v_task, 'fase', v_fase),
      NULL::uuid, 
      concat('Task pipeline non implementato', ' task:', v_task, ' fase:', v_fase)
    );
  END LOOP;
END
$function$

COMMENT ON FUNCTION vendite.fn_execute_pipeline_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_rollback boolean, p_dry_run boolean)
IS 'Esegue i task di uno step pipeline leggendo processi/rollback.';
```

---
{% include-markdown "signature-core.md" %}
