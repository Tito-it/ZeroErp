{% include-markdown "it/dbzero/vendite/manual/fn_cancel_lotto_task_run.md" %}
# ⚙️ Funzione `fn_cancel_lotto_task_run`

```sql
CREATE FUNCTION fn_cancel_lotto_task_run(p_task_run_id bigint, p_meta jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cancel_lotto_task_run(p_task_run_id bigint, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: chiude con esito ANNULLATO un task-run lotto.
  -- ⚠️ E' la funzione che fn_riporta_lotto_a_draft chiama per
  -- azzerare lo stato di esecuzione del lotto riaperto (RD-6):
  -- il percorso vivo che passava accanto al ramo morto.
  PERFORM vendite.fn_set_runtime_task_run_esito(
    p_task_run_id => p_task_run_id,
    p_task_stato => 'ANNULLATO',
    p_error_code => NULL,
    p_error_message => NULL,
    p_meta => p_meta
  );
END
$function$

COMMENT ON FUNCTION vendite.fn_cancel_lotto_task_run(p_task_run_id bigint, p_meta jsonb)
IS 'Chiude un task run lotto con esito ANNULLATO (via helper condiviso). Chiamata da vendite.fn_riporta_lotto_a_draft (RD-6) per riportare i task_run del lotto riaperto a RUN. rev 2026-08-04: l''helper non ha piu'' p_scope.';
```

</div>

---
{% include-markdown "signature-core.md" %}
