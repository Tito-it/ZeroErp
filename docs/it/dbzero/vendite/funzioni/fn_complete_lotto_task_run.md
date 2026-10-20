{% include-markdown "it/dbzero/vendite/manual/fn_complete_lotto_task_run.md" %}
# ⚙️ Funzione `fn_complete_lotto_task_run`

```sql
CREATE FUNCTION fn_complete_lotto_task_run(p_task_run_id bigint, p_meta jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_complete_lotto_task_run(p_task_run_id bigint, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: chiude con esito COMPLETATO un task-run lotto.
  PERFORM vendite.fn_set_runtime_task_run_esito(
    p_task_run_id => p_task_run_id,
    p_task_stato => 'COMPLETATO',
    p_error_code => NULL,
    p_error_message => NULL,
    p_meta => p_meta
  );
END
$function$

COMMENT ON FUNCTION vendite.fn_complete_lotto_task_run(p_task_run_id bigint, p_meta jsonb)
IS 'Chiude un task run lotto con esito COMPLETATO (via helper condiviso). rev 2026-08-04: l''helper non ha piu'' p_scope.';
```

</div>

---
{% include-markdown "signature-core.md" %}
