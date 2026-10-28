{% include-markdown "it/dbzero/maintenance/manual/proc_automations_overlap_job.md" %}
# ⚙️ Procedura `proc_automations_overlap_job`

```sql
CREATE PROCEDURE proc_automations_overlap_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_overlap_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_overlap',
      p_stepname := 'run_automations_overlap',
      p_sql      := 'SELECT dbops.fn_apply_automazione_overlap(''SCHEDULED'', false);',
      p_lock_key := hashtext('automations_overlap')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_overlap_job()
IS 'Job wrapper per chiamare fn_apply_automazione_overlap (OVERLAP) con logging e lock. Ricrea gli EXCLUDE mancanti dalle righe active=true di dbops.automazione_overlap.';
```

</div>

---
{% include-markdown "signature-core.md" %}
