{% include-markdown "it/dbzero/vendite/manual/fn_fail_lotto_task_run.md" %}
# ⚙️ Funzione `fn_fail_lotto_task_run`

```sql
CREATE FUNCTION fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Chiude un task run con stato ERRORE.
  -- =========================================================
  IF p_task_run_id IS NULL OR p_task_run_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_fail_lotto_task_run', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','task_run_id obbligatorio','task_run_id',p_task_run_id)
      ),
      NULL::uuid,
      'task_run_id obbligatorio'
    );
  END IF;

  UPDATE vendite.fatturazione_lotti_task_runs
     SET task_stato = 'ERRORE',
         ended_at = now(),
         error_code = COALESCE(NULLIF(btrim(p_error_code), ''), 'E_GENERICO'),
         error_message = COALESCE(NULLIF(btrim(p_error_message), ''), 'Errore task'),
         meta = COALESCE(meta, '{}'::jsonb) || COALESCE(p_meta, '{}'::jsonb),
         data_update = now(),
         user_update = current_user
   WHERE id = p_task_run_id;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_fail_lotto_task_run', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','task_run non trovato','task_run_id',p_task_run_id)
      ),
      NULL::uuid,
      concat('task_run non trovato id:', p_task_run_id::text)
    );
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
IS 'Chiude un task run lotto con esito ERRORE, salvando codice/messaggio.';
```

---
{% include-markdown "signature-core.md" %}
