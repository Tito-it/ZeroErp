# 🔍 View `vw_job_run_da_superuser`

> 📝 **Descrizione**
>
> PRESIDIO «nessun superuser al lavoro»: per ogni processo l'ULTIMA corsa del giornale, se il ruolo che si e' collegato (ruolo_sessione) e' un superuser. Deve restare vuota. Basta «superuser» e non «membro di zeroerp_job» perche' le procedure dei job sono chiamabili solo da proprietario, zeroerp_job e superuser (EXECUTE tolto a PUBLIC, 20261014-55), e il giornale non distingue pgAgent da ci_apply (origine PGAGENT di default, nessun application_name). Si giudica da pg_roles.rolsuper, mai dal nome. Esclusi ruolo_sessione NULL (non registrato) e ruoli che non esistono piu'. Brief: brief-db-ruoli-di-sistema D-5.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW maintenance.vw_job_run_da_superuser AS
WITH ultima AS (
         SELECT DISTINCT ON (COALESCE(l.processo_codice, l.jobname)) COALESCE(l.processo_codice, l.jobname) AS processo_codice,
            l.jobname,
            l.started_at,
            l.ok,
            l.origine,
            l.ruolo_sessione
           FROM maintenance.job_run_log l
          WHERE (l.ruolo_sessione IS NOT NULL)
          ORDER BY COALESCE(l.processo_codice, l.jobname), l.started_at DESC, l.id DESC
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
