{% include-markdown "it/dbzero/vendite/manual/fn_get_attivita_branch_summary.md" %}
# ⚙️ Funzione `fn_get_attivita_branch_summary`

```sql
CREATE FUNCTION fn_get_attivita_branch_summary(p_lotto_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_attivita_branch_summary(p_lotto_attivita_id bigint)
 RETURNS TABLE(branch_code character varying, task_stato character varying, cnt bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire il riepilogo runtime task-runs attivita
  --   aggregato per branch_code e task_stato.
  --
  -- Regole:
  --   - p_lotto_attivita_id obbligatorio e > 0
  --   - output ordinato per branch_code/task_stato
  -- =========================================================
  IF p_lotto_attivita_id IS NULL OR p_lotto_attivita_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_attivita_branch_summary', 'E_GENERICO',
      jsonb_build_object(
        'scope', 'ATTIVITA_FATTURABILI',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', p_lotto_attivita_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail', 'lotto_attivita_id obbligatorio')
      ),
      NULL::uuid,
      'lotto_attivita_id obbligatorio'
    );
  END IF;

  RETURN QUERY
  SELECT
    r.branch_code,
    r.task_stato,
    COUNT(*)::bigint AS cnt
  FROM vendite.attivita_fatturabili_lotti_task_runs r
  WHERE r.lotto_attivita_id = p_lotto_attivita_id
  GROUP BY r.branch_code, r.task_stato
  ORDER BY r.branch_code, r.task_stato;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_attivita_branch_summary(p_lotto_attivita_id bigint)
IS 'Riepiloga i task-runs runtime del lotto attivita per branch_code e task_stato.';
```

---
{% include-markdown "signature-core.md" %}
