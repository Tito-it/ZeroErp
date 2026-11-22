{% include-markdown "it/dbzero/maintenance/manual/vw_job_run_corsie.md" %}
# 🔍 View `vw_job_run_corsie`

> 📝 **Descrizione**
>
> Le corsie del giornale: una riga per ogni coppia (processo_codice, jobname) che ha almeno una corsa in maintenance.job_run_log. La corsia e' la coppia, non il solo jobname: il modello non lega un jobname a un processo solo, e due processi possono avere una corsia con lo stesso nome. Si legge con una discesa ricorsiva sull'indice ix_job_run_log_processo_codice_jobname_started_at (la coppia successiva), quindi il costo segue il numero delle corsie, non la storia del giornale. La leggono maintenance.vw_job_run_da_guardare e maintenance.fn_pota_giornale_corse.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW maintenance.vw_job_run_corsie AS
WITH RECURSIVE corsie AS (
        ( SELECT c0.processo_codice,
            c0.jobname
           FROM maintenance.job_run_log c0
          ORDER BY c0.processo_codice, c0.jobname
         LIMIT 1)
        UNION ALL
         SELECT n.processo_codice,
            n.jobname
           FROM (corsie c
             CROSS JOIN LATERAL ( SELECT c1.processo_codice,
                    c1.jobname
                   FROM maintenance.job_run_log c1
                  WHERE (ROW(c1.processo_codice, c1.jobname) > ROW(c.processo_codice, c.jobname))
                  ORDER BY c1.processo_codice, c1.jobname
                 LIMIT 1) n)
        )
 SELECT processo_codice,
    jobname
   FROM corsie;
```

</div>


---
{% include-markdown "signature-core.md" %}
