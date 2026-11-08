{% include-markdown "it/dbzero/maintenance/manual/proc_apply_storicizza_defaults_job.md" %}
# ⚙️ Procedura `proc_apply_storicizza_defaults_job`

```sql
CREATE PROCEDURE proc_apply_storicizza_defaults_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  -- ⭐ Una SELECT e non una CALL: fn_run_and_log legge l'esito
  --   e una corsa con tabelle fallite e' rossa.
  --   Brief: brief-db-revisione-maintenance D11.
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'apply_storicizza_weekly',
      p_stepname := 'run_proc_apply_storicizza',
      p_sql      := 'SELECT maintenance.fn_apply_storicizza_defaults();',
      p_lock_key := hashtext('proc_apply_storicizza_defaults')  -- evita overlap
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
IS 'Wrapper del processo apply_storicizza_weekly: chiama maintenance.fn_apply_storicizza_defaults con una SELECT, passando da maintenance.fn_run_and_log con lock. L''esito (applicate, saltate, fallite) va in meta.esito, e una corsa con tabelle fallite e'' rossa (E_JOB_ESITO_CON_SCARTI). La chiamano il job pgAgent del sabato, dopo il sync, e la convergenza in CI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
