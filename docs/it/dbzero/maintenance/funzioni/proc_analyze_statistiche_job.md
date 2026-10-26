{% include-markdown "it/dbzero/maintenance/manual/proc_analyze_statistiche_job.md" %}
# ⚙️ Procedura `proc_analyze_statistiche_job`

```sql
CREATE PROCEDURE proc_analyze_statistiche_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_analyze_statistiche_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
    -- ⚠️ `p_jobname` e' il CODICE DEL PROCESSO: e' cosi' che
    --   fn_run_and_log risale all'attore (cerca in
    --   dbops.processi.codice). Qui coincide col jobname pgAgent.
    PERFORM maintenance.fn_run_and_log(
        p_jobname  := 'analyze_statistiche',
        p_stepname := 'analyze',
        p_sql      := 'SELECT maintenance.fn_analyze_statistiche();');
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_analyze_statistiche_job()
IS 'Wrapper del job analyze_statistiche: esegue maintenance.fn_analyze_statistiche() PASSANDO dal giornale, sotto il codice del processo. Lo chiamano il job pgAgent notturno e, in CI, la convergenza di 90_end/ci_apply/20260926-10 (dbops.processi.ci_procedura). ⭐ Il giornale e'' cio'' che rende visibile un''autoverifica rossa: fn_run_and_log scrive la riga del fallimento fuori transazione. Nessun COMMIT: in CI gira dentro la transazione del changeSet. Brief: brief-db-statistiche-tabelle-job-notturno (D15).';
```

</div>

---
{% include-markdown "signature-core.md" %}
