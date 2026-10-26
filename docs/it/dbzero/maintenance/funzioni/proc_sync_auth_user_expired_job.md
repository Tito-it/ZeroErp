# ⚙️ Procedura `proc_sync_auth_user_expired_job`

```sql
CREATE PROCEDURE proc_sync_auth_user_expired_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_sync_auth_user_expired_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
    PERFORM maintenance.fn_run_and_log(
        p_jobname  := 'sync_auth_user_expired_daily',
        p_stepname := 'run_sync_auth_user_expired',
        p_sql      := 'SELECT anagrafiche.fn_sync_auth_user_expired();');
END
$procedure$

COMMENT ON PROCEDURE maintenance.proc_sync_auth_user_expired_job()
IS 'Wrapper del job sync_auth_user_expired_daily: disattiva le utenze scadute PASSANDO dal giornale. ⛔ Quel job girava dal principio con una SELECT diretta, quindi non ha MAI scritto una riga di corsa — non falliva, semplicemente non esisteva per chi guarda i presidi. L''ha trovato dbops.vw_processi_programmazione confrontando quello che pgAgent sa con quello che il giornale dice.';
```

</div>

---
{% include-markdown "signature-core.md" %}
