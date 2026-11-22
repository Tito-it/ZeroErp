{% include-markdown "it/dbzero/maintenance/manual/vw_job_run_da_superuser.md" %}
# 🔍 View `vw_job_run_da_superuser`

> 📝 **Descrizione**
>
> PRESIDIO «nessun superuser al lavoro»: per ogni processo l'ULTIMA corsa del giornale, se il ruolo che si e' collegato (ruolo_sessione) e' un superuser. Deve restare vuota. Basta «superuser» e non «membro di zeroerp_job» perche' le procedure dei job sono eseguibili solo dal proprietario, da zeroerp_job e dai superuser (EXECUTE tolto a PUBLIC), e il giornale non distingue pgAgent da ci_apply (origine PGAGENT di default, nessun application_name). Si giudica da pg_roles.rolsuper, mai dal nome. Esclusi ruolo_sessione NULL (non registrato) e i ruoli che non esistono piu'.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW maintenance.vw_job_run_da_superuser AS
WITH RECURSIVE processi_giornale AS (
         SELECT min(p0.processo_codice) AS chiave
           FROM maintenance.job_run_log p0
        UNION ALL
         SELECT ( SELECT min(p1.processo_codice) AS min
                   FROM maintenance.job_run_log p1
                  WHERE (p1.processo_codice > processi_giornale.chiave)) AS chiave
           FROM processi_giornale
          WHERE (processi_giornale.chiave IS NOT NULL)
        ), ultima AS (
         SELECT k.chiave AS processo_codice,
            x.jobname,
            x.started_at,
            x.ok,
            x.origine,
            x.ruolo_sessione
           FROM (processi_giornale k
             CROSS JOIN LATERAL ( SELECT l.jobname,
                    l.started_at,
                    l.ok,
                    l.origine,
                    l.ruolo_sessione
                   FROM maintenance.job_run_log l
                  WHERE ((l.processo_codice = k.chiave) AND (l.ruolo_sessione IS NOT NULL))
                  ORDER BY l.started_at DESC, l.id DESC
                 LIMIT 1) x)
          WHERE (k.chiave IS NOT NULL)
        )
 SELECT u.processo_codice,
    u.jobname,
    u.started_at,
    u.ok,
    u.origine,
    u.ruolo_sessione
   FROM (ultima u
     JOIN pg_roles r ON ((r.rolname = u.ruolo_sessione)))
  WHERE r.rolsuper;
```

</div>


---
{% include-markdown "signature-core.md" %}
