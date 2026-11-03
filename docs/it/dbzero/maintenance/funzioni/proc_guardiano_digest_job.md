{% include-markdown "it/dbzero/maintenance/manual/proc_guardiano_digest_job.md" %}
# ⚙️ Procedura `proc_guardiano_digest_job`

```sql
CREATE PROCEDURE proc_guardiano_digest_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_guardiano_digest_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
    -- ⚠️ `p_jobname` e' il CODICE DEL PROCESSO: e' cosi' che
    --   fn_run_and_log risale all'attore (cerca in
    --   dbops.processi.codice). Qui coincide col jobname pgAgent.
    PERFORM maintenance.fn_run_and_log(
        p_jobname  := 'guardiano_digest',
        p_stepname := 'guarda_il_digest',
        p_sql      := 'SELECT dbops.fn_guardiano_digest();');
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_guardiano_digest_job()
IS 'Wrapper del job guardiano_digest: esegue dbops.fn_guardiano_digest() PASSANDO dal giornale. ⭐ E'' cio'' che rende il guardiano un processo PGAGENT come gli altri, che dbops.vw_processi_programmazione guarda: il digest riporta il guardiano, il guardiano accoda per il digest — ognuno vede la morte dell''altro. ⛔ Senza il giornale il guardiano sarebbe invisibile a tutti i presidi, cioe'' il difetto che 20260906-06 ha chiuso su due job. Brief: brief-db-quattro-processi-senza-presidio §10.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
