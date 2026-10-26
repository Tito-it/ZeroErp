{% include-markdown "it/dbzero/maintenance/manual/proc_automations_lock_columns_job.md" %}
# ⚙️ Procedura `proc_automations_lock_columns_job`

```sql
CREATE PROCEDURE proc_automations_lock_columns_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_lock_columns_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    -- rev 20260923-46: anche il guard delle date di validita'
    --   (automazione DATE_VALIDITA), stessa famiglia del lock.
    -- rev 20260926-05: niente piu' fn_run_automations_drop_lock_trg;
    --   togliere un lock e' un'azione del runner che converge.
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_lock_columns',
      p_stepname := 'run_automations_lock_columns',
      p_sql      := 'SELECT dbops.fn_run_automations_lock_columns(''SCHEDULED'', NULL, false); ' ||
                   'SELECT dbops.fn_run_automations_date_validita(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_lock_columns')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_lock_columns_job()
IS 'Job wrapper per dbops.fn_run_automations_lock_columns, che converge i trigger di lock columns verso il registro (crea, rigenera, toglie). Rev 20260923-46: monta anche il guard delle date di validita'' (dbops.fn_run_automations_date_validita, automazione DATE_VALIDITA), stessa famiglia del lock. Rev 20260926-05: non chiama piu'' dbops.fn_run_automations_drop_lock_trg (ritirata), che cancellava per funzione anche i lock scritti a mano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
