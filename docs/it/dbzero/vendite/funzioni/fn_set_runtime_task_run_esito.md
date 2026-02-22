{% include-markdown "it/dbzero/vendite/manual/fn_set_runtime_task_run_esito.md" %}
# ⚙️ Funzione `fn_set_runtime_task_run_esito`

```sql
CREATE FUNCTION fn_set_runtime_task_run_esito(p_scope text, p_task_run_id bigint, p_task_stato text, p_error_code text, p_error_message text, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_runtime_task_run_esito(p_scope text, p_task_run_id bigint, p_task_stato text, p_error_code text DEFAULT NULL::text, p_error_message text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_scope text;
  v_task_stato text;
  v_error_code text;
  v_meta jsonb;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Applicare in modo uniforme la chiusura task-run runtime
  --   su dominio LOTTO o ATTIVITA_FATTURABILI.
  --
  -- Regole:
  --   - validazione input minimi
  --   - update stato/ended_at/meta
  --   - fail: valorizza error_code/error_message
  --   - complete/cancel: non forza errori, salvo reset dedicato
  -- =========================================================
  v_scope := upper(COALESCE(NULLIF(btrim(p_scope), ''), ''));
  v_task_stato := upper(COALESCE(NULLIF(btrim(p_task_stato), ''), ''));
  v_error_code := NULLIF(btrim(p_error_code), '');
  v_meta := COALESCE(p_meta, '{}'::jsonb);

  IF p_task_run_id IS NULL OR p_task_run_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', COALESCE(NULLIF(v_scope, ''), 'SYSTEM'),
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'task_run_id obbligatorio',
          'task_run_id', p_task_run_id
        )
      ),
      NULL::uuid,
      'task_run_id obbligatorio'
    );
  END IF;

  IF v_scope NOT IN ('LOTTO', 'ATTIVITA_FATTURABILI') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', 'SYSTEM',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'scope non valido',
          'scope_value', p_scope
        )
      ),
      NULL::uuid,
      'scope non valido'
    );
  END IF;

  IF v_task_stato NOT IN ('COMPLETATO', 'ERRORE', 'ANNULLATO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', v_scope,
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'task_stato non valido',
          'task_stato', p_task_stato
        )
      ),
      NULL::uuid,
      'task_stato non valido'
    );
  END IF;

  IF v_scope = 'LOTTO' THEN
    UPDATE vendite.fatturazione_lotti_task_runs
       SET task_stato = v_task_stato,
           ended_at = now(),
           error_code = CASE
             WHEN v_task_stato = 'ERRORE' THEN COALESCE(v_error_code, 'E_GENERICO')
             ELSE error_code
           END,
           error_message = CASE
             WHEN v_task_stato = 'ERRORE' THEN COALESCE(NULLIF(btrim(p_error_message), ''), 'Errore task')
             ELSE error_message
           END,
           meta = COALESCE(meta, '{}'::jsonb) || v_meta,
           data_update = now(),
           user_update = current_user
     WHERE id = p_task_run_id;

    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite',
        'fn_set_runtime_task_run_esito',
        'E_GENERICO',
        jsonb_build_object(
          'scope', 'LOTTO',
          'severity', 'C',
          'code', 'E_GENERICO',
          'lotto_id', NULL,
          'fattura_id', NULL,
          'context', jsonb_build_object(
            'detail', 'task_run non trovato',
            'task_run_id', p_task_run_id
          )
        ),
        NULL::uuid,
        concat('task_run non trovato id:', p_task_run_id::text)
      );
    END IF;

  ELSE
    UPDATE vendite.attivita_fatturabili_lotti_task_runs
       SET task_stato = v_task_stato,
           ended_at = now(),
           error_code = CASE
             WHEN v_task_stato = 'ERRORE' THEN COALESCE(v_error_code, 'E_TASK_RUNTIME')
             WHEN v_task_stato = 'COMPLETATO' THEN NULL
             ELSE error_code
           END,
           error_message = CASE
             WHEN v_task_stato = 'ERRORE' THEN p_error_message
             WHEN v_task_stato = 'COMPLETATO' THEN NULL
             ELSE error_message
           END,
           meta = COALESCE(meta, '{}'::jsonb) || v_meta,
           data_update = now(),
           user_update = current_user
     WHERE id = p_task_run_id;

    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite',
        'fn_set_runtime_task_run_esito',
        'E_GENERICO',
        jsonb_build_object(
          'scope', 'ATTIVITA_FATTURABILI',
          'severity', 'C',
          'code', 'E_GENERICO',
          'lotto_id', NULL,
          'fattura_id', NULL,
          'context', jsonb_build_object(
            'detail', 'task_run non trovato',
            'task_run_id', p_task_run_id
          )
        ),
        NULL::uuid,
        'task_run non trovato'
      );
    END IF;
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_set_runtime_task_run_esito(p_scope text, p_task_run_id bigint, p_task_stato text, p_error_code text, p_error_message text, p_meta jsonb)
IS 'Helper condiviso per chiudere task-run runtime su dominio LOTTO o ATTIVITA_FATTURABILI.';
```

---
{% include-markdown "signature-core.md" %}
