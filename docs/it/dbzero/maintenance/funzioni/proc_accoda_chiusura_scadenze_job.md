# ⚙️ Procedura `proc_accoda_chiusura_scadenze_job`

```sql
CREATE PROCEDURE proc_accoda_chiusura_scadenze_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_accoda_chiusura_scadenze_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
    -- ⚠️ `p_jobname` e' il CODICE DEL PROCESSO: e' cosi' che
    --   fn_run_and_log risale all'attore (cerca in
    --   dbops.processi.codice). Passare il nome del job pgAgent
    --   lascerebbe la corsa senza attore.
    PERFORM maintenance.fn_run_and_log(
        p_jobname  := 'chiusura_scadenze_daily',
        p_stepname := 'accoda_chiusura_scadenze',
        p_sql      := 'SELECT dbops.fn_accoda_chiusura_scadenze();');
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_accoda_chiusura_scadenze_job()
IS 'Wrapper del job chiusura_scadenze_daily: sveglia la chiusura scadenze PASSANDO dal giornale. ⛔ Esiste perche'' il changeSet 20260905-25, trasformando quel job da esecutore a sveglia, ha sostituito lo step con una SELECT diretta e ha perso il wrapper — e con lui la registrazione della corsa. Il lavoro veniva accodato correttamente, ma della sveglia non restava traccia: nessun test poteva prenderlo, perche'' tutti guardavano che il lavoro fosse accodato. L''ha trovato dbops.vw_processi_programmazione confrontando pgAgent col giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
