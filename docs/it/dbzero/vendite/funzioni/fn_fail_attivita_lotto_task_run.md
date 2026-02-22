{% include-markdown "it/dbzero/vendite/manual/fn_fail_attivita_lotto_task_run.md" %}
# ⚙️ Funzione `fn_fail_attivita_lotto_task_run`

```sql
CREATE FUNCTION fn_fail_attivita_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fail_attivita_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: chiude con esito ERRORE un task-run attività.
  PERFORM vendite.fn_set_runtime_task_run_esito(
    p_scope => 'ATTIVITA_FATTURABILI',
    p_task_run_id => p_task_run_id,
    p_task_stato => 'ERRORE',
    p_error_code => p_error_code,
    p_error_message => p_error_message,
    p_meta => p_meta
  );
END
$function$

COMMENT ON FUNCTION vendite.fn_fail_attivita_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
IS 'Marca in ERRORE un task-run runtime attivita (via helper condiviso).';
```

---
{% include-markdown "signature-core.md" %}
