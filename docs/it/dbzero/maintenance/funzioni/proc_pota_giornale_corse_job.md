{% include-markdown "it/dbzero/maintenance/manual/proc_pota_giornale_corse_job.md" %}
# ⚙️ Procedura `proc_pota_giornale_corse_job`

```sql
CREATE PROCEDURE proc_pota_giornale_corse_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_pota_giornale_corse_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    -- Scopo: la ritenzione del giornale delle corse, 12 mesi: la soglia e'
    --   l'inizio del giorno aziendale di 12 mesi fa. Il jobname e' il
    --   codice del processo in dbops.processi.
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'pota_giornale_corse',
      p_stepname := 'pota_giornale_corse',
      p_sql      := 'SELECT maintenance.fn_pota_giornale_corse(script.fn_inizio_giorno_operativo(script.fn_mesi_dopo(script.fn_giorno_operativo(now()), -12)));',
      p_lock_key := hashtext('pota_giornale_corse')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_pota_giornale_corse_job()
IS 'Job pota_giornale_corse: la ritenzione del giornale delle corse. Chiama maintenance.fn_pota_giornale_corse dentro maintenance.fn_run_and_log, con lock e giornale, con la soglia all''inizio del giorno aziendale di 12 mesi fa (script.fn_giorno_operativo, script.fn_mesi_dopo, script.fn_inizio_giorno_operativo). La ritenzione di 12 mesi sta qui. SECURITY DEFINER del proprietario, search_path fissato; l''EXECUTE va solo a zeroerp_job (provisioning). Fuori dalla convergenza di ci_apply (dbops.processi.ci_esclusione); ogni notte da pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
