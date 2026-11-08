{% include-markdown "it/dbzero/maintenance/manual/proc_automations_storico_provision_job.md" %}
# ⚙️ Procedura `proc_automations_storico_provision_job`

```sql
CREATE PROCEDURE proc_automations_storico_provision_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_storico_provision_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_storico_provision',
    p_stepname := 'run_automations_storico_provision',
    p_sql      := 'SELECT dbops.fn_run_automations_storico_provision(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_storico_provision')
  );
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_storico_provision_job()
IS 'Wrapper del processo automations_storico_provision: esegue dbops.fn_run_automations_storico_provision in modo SCHEDULED su tutto l''ambito, passando da maintenance.fn_run_and_log, che registra la corsa in maintenance.job_run_log sotto il codice del processo e tiene un advisory lock contro due corse sovrapposte. Non aggiunge logica. Il runner crea o aggiorna nello schema storico la gemella di ogni tabella che ha la colonna storicizza, con dbops.fn_ensure_storico_table. Il trigger che scrive nella gemella non lo monta lui: lo monta maintenance.proc_automations_storico_job. Lo chiamano il job pgAgent automations_storico_provision e la convergenza del rilascio (dbops.processi.ci_ordine), che lo mette prima del trigger. SECURITY DEFINER: gira come il proprietario, non come il ruolo con cui si collega pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
