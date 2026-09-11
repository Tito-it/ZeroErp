# ⚙️ Procedura `proc_guardiano_digest_job`

```sql
CREATE PROCEDURE proc_guardiano_digest_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_guardiano_digest_job()
 LANGUAGE plpgsql
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

---
{% include-markdown "signature-core.md" %}
