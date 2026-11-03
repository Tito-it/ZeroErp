{% include-markdown "it/dbzero/maintenance/manual/proc_automations_cleanup_job.md" %}
# ⚙️ Procedura `proc_automations_cleanup_job`

```sql
CREATE PROCEDURE proc_automations_cleanup_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_cleanup_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  -- ⭐ Ambito NULL: lo decide il registro (dbops.automation_scope
  --   per gli schemi, dbops.automation_rules_tbl per le tabelle).
  --   Brief: brief-db-revisione-maintenance D4.
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_cleanup',
      p_stepname := 'run_automations_cleanup',
      p_sql      := 'SELECT dbops.fn_run_automations_cleanup(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_cleanup')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_cleanup_job()
IS 'Wrapper del processo automations_cleanup: chiama dbops.fn_run_automations_cleanup in modo SCHEDULED, con l''ambito letto dal registro (p_schemas NULL: gli schemi di dbops.automation_scope, le tabelle dalle regole CLEANUP_AT e CLEANUP_PURGE), passando da maintenance.fn_run_and_log con lock. La chiamano il job pgAgent della domenica e la convergenza in CI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
