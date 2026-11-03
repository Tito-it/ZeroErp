{% include-markdown "it/dbzero/maintenance/manual/proc_automations_storico_job.md" %}
# ⚙️ Procedura `proc_automations_storico_job`

```sql
CREATE PROCEDURE proc_automations_storico_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_storico_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_storico',
    p_stepname := 'run_automations_storico',
    p_sql      := 'SELECT dbops.fn_run_automations_storico(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_storico')
  );
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_storico_job()
IS 'Wrapper del processo automations_storico: esegue dbops.fn_run_automations_storico in modo SCHEDULED su tutto l''ambito, passando da maintenance.fn_run_and_log, che registra la corsa in maintenance.job_run_log sotto il codice del processo e tiene un advisory lock contro due corse sovrapposte. Non aggiunge logica. Il runner monta il trigger script.trgfn_storico_generic sulle tabelle che hanno gia'' la gemella nello schema storico; se nella gemella manca la colonna verso la madre si ferma con E_STORICO_FK_COL_ASSENTE. Aggiunge e non toglie. La gemella non la crea lui: la crea maintenance.proc_automations_storico_provision_job. Lo chiamano il job pgAgent automations_storico e la convergenza del rilascio (dbops.processi.ci_ordine), che lo mette dopo la creazione delle gemelle. SECURITY DEFINER: gira come il proprietario, non come il ruolo con cui si collega pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
