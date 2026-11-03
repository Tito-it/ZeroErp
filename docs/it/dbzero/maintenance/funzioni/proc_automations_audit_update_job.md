{% include-markdown "it/dbzero/maintenance/manual/proc_automations_audit_update_job.md" %}
# ⚙️ Procedura `proc_automations_audit_update_job`

```sql
CREATE PROCEDURE proc_automations_audit_update_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_audit_update_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_audit_update',
    p_stepname := 'run_automations_audit_update',
    p_sql      := 'SELECT dbops.fn_run_automations_audit_update(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_audit_update')
  );
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_audit_update_job()
IS 'Wrapper del processo automations_audit_update: esegue dbops.fn_run_automations_audit_update in modo SCHEDULED su tutto l''ambito, passando da maintenance.fn_run_and_log, che registra la corsa in maintenance.job_run_log sotto il codice del processo e tiene un advisory lock contro due corse sovrapposte. Non aggiunge logica. Il runner monta, sulle tabelle che hanno le colonne di audit, il trigger script.trgfn_audit_data_user_generic, che a ogni scrittura dice chi ha toccato la riga e quando. Aggiunge e non toglie. Lo chiamano il job pgAgent automations_audit_update e la convergenza del rilascio (dbops.processi.ci_ordine). SECURITY DEFINER: gira come il proprietario, non come il ruolo con cui si collega pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
