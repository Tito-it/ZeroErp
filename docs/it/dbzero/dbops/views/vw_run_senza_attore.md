{% include-markdown "it/dbzero/dbops/manual/vw_run_senza_attore.md" %}
# 🔍 View `vw_run_senza_attore`

> 📝 **Descrizione**
>
> Job la cui ULTIMA corsa non dice chi l'ha eseguita (maintenance.job_run_log.processo_codice NULL). Una riga per job da sistemare, non una per run. ⛔ Il criterio e' l'ULTIMA corsa, non «esiste una corsa senza attore»: le righe storiche hanno processo_codice NULL e resteranno NULL per sempre — sono giornale di ieri — quindi contandole la vista non arriverebbe a zero nemmeno a lavoro finito, e un registro di debito che non cala e' rumore. ⭐ Cosi' invece un job sparisce appena comincia a dichiarare l'attore, e i dodici job pgAgent si tolgono da soli alla prima corsa notturna (fn_run_and_log deriva il codice dal jobname). run_senza_attore resta come CONTESTO — quanto e' vecchia l'omissione — non come criterio. processo_registrato false = manca la riga in dbops.processi; true con origine CRON/COMMAND = il chiamante headless non passa ancora il parametro (lavoro di backend). Quando la vista e' vuota, processo_codice puo' diventare NOT NULL. Brief: brief-db-processi-automatici-identita-e-perimetro §8.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_run_senza_attore AS
WITH ultima_corsa AS (
         SELECT DISTINCT ON (jrl.jobname, jrl.origine) jrl.jobname,
            jrl.origine,
            jrl.processo_codice,
            jrl.started_at
           FROM maintenance.job_run_log jrl
          ORDER BY jrl.jobname, jrl.origine, jrl.started_at DESC, jrl.id DESC
        )
 SELECT jobname,
    origine,
    started_at AS ultimo_run,
    ( SELECT count(*) AS count
           FROM maintenance.job_run_log j
          WHERE ((j.jobname = u.jobname) AND ((j.origine)::text = (u.origine)::text) AND (j.processo_codice IS NULL))) AS run_senza_attore,
    (EXISTS ( SELECT 1
           FROM dbops.processi pr
          WHERE (pr.codice = u.jobname))) AS processo_registrato
   FROM ultima_corsa u
  WHERE (processo_codice IS NULL);
```

</div>


---
{% include-markdown "signature-core.md" %}
