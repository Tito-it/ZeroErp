{% include-markdown "it/dbzero/vendite/manual/fn_fail_lotto_task_run.md" %}
# ⚙️ Funzione `fn_fail_lotto_task_run`

```sql
CREATE FUNCTION fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: chiude con esito ERRORE un task-run lotto.
  PERFORM vendite.fn_set_runtime_task_run_esito(
    p_task_run_id => p_task_run_id,
    p_task_stato => 'ERRORE',
    p_error_code => p_error_code,
    p_error_message => p_error_message,
    p_meta => p_meta
  );
END
$function$

COMMENT ON FUNCTION vendite.fn_fail_lotto_task_run(p_task_run_id bigint, p_error_code character varying, p_error_message text, p_meta jsonb)
IS 'Chiude un task run lotto con esito ERRORE (via helper condiviso). rev 2026-08-04: l''helper non ha piu'' p_scope.';
```

</div>

---
{% include-markdown "signature-core.md" %}
