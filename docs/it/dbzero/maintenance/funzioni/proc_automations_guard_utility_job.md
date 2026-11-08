{% include-markdown "it/dbzero/maintenance/manual/proc_automations_guard_utility_job.md" %}
# ⚙️ Procedura `proc_automations_guard_utility_job`

```sql
CREATE PROCEDURE proc_automations_guard_utility_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_guard_utility_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    -- Scopo: il job del guard utility/tipo ruolo, nella catena dei processi strutturali
    --   (dbops.processi, ci_ordine 75: dopo il blocco delle cancellazioni, prima dell'overlap).
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_guard_utility',
      p_stepname := 'run_automations_guard_utility',
      p_sql      := 'SELECT dbops.fn_run_automations_guard_utility(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_guard_utility')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_guard_utility_job()
IS 'Job automations_guard_utility: chiama dbops.fn_run_automations_guard_utility(''SCHEDULED'', NULL, false) dentro maintenance.fn_run_and_log, con lock e giornale. SECURITY DEFINER del proprietario, search_path fissato; l''EXECUTE va solo a zeroerp_job (provisioning). Nella catena dei processi strutturali di ci_apply (dbops.processi, ci_ordine 75) e di notte da pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
