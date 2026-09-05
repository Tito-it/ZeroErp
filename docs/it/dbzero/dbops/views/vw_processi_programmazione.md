# 🔍 View `vw_processi_programmazione`

> 📝 **Descrizione**
>
> PANORAMA: per ogni processo automatico attivo — quale job pgAgent lo sveglia, quando girera', quando ha girato secondo pgAgent e secondo il nostro giornale. ⭐ La colonna che vale piu' di tutte e' `stato`, e il valore che conta e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non lo sa — e' la firma esatta di un lavoro che muore prima di riuscire a raccontarlo, cioe' di R-12, il job morto per sei mesi con l'ultimo verdetto a «done». Questo confronto lo avrebbe trovato in un giorno. ⚠️ Il legame col job NON e' il nome: si legge da dbops.processi.jobname_pgagent, perche' due job su quattordici si chiamano diversamente dal processo che registrano. ⚠️ Il giornale si legge per processo_codice OPPURE per jobname: le corse storiche hanno la prima colonna vuota, e senza il ripiego ogni processo sembrerebbe non aver mai girato prima di settembre 2026. ⚠️ FUORI_PORTATA non significa «tutto bene»: i COMMAND li programma crontab e i CODA li sveglia il backend, e di loro il database non puo' sapere se stanno partendo — dirlo OK sarebbe una bugia, dirlo guasto un falso allarme. ⭐ E' un panorama, non un presidio: elenca anche i sani, perche' senza sapere quanti sono i sani un guasto sembra la norma. Il presidio e' WHERE stato NOT IN (OK, FUORI_PORTATA).

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_programmazione AS
SELECT p.codice AS processo_codice,
    p.classe,
    p.canale,
    p.jobname_pgagent,
    g.abilitato AS job_abilitato,
    g.prossima_esecuzione AS prossima_corsa,
    g.ultima_esecuzione AS pgagent_ultima_corsa,
    l.ultima_corsa AS giornale_ultima_corsa,
    l.ultimo_esito,
        CASE
            WHEN (p.canale = ANY (ARRAY['COMMAND'::text, 'CODA'::text])) THEN 'FUORI_PORTATA'::text
            WHEN (p.jobname_pgagent IS NULL) THEN 'NON_PROGRAMMATO'::text
            WHEN (g.abilitato IS NULL) THEN 'JOB_ASSENTE'::text
            WHEN (g.abilitato IS FALSE) THEN 'JOB_SPENTO'::text
            WHEN ((g.ultima_esecuzione IS NOT NULL) AND (COALESCE(l.ultima_corsa, '-infinity'::timestamp with time zone) < (g.ultima_esecuzione - '01:00:00'::interval))) THEN 'GIRA_E_NON_REGISTRA'::text
            WHEN (g.ultima_esecuzione IS NULL) THEN 'MAI_PARTITO'::text
            ELSE 'OK'::text
        END AS stato
   FROM ((dbops.processi p
     LEFT JOIN LATERAL dbops.fn_get_pgagent_job_stato(p.jobname_pgagent) g(abilitato, ultima_esecuzione, prossima_esecuzione) ON (true))
     LEFT JOIN LATERAL ( SELECT max(r.started_at) AS ultima_corsa,
            ( SELECT r2.ok
                   FROM maintenance.job_run_log r2
                  WHERE ((r2.processo_codice = p.codice) OR (r2.jobname = p.codice))
                  ORDER BY r2.started_at DESC, r2.id DESC
                 LIMIT 1) AS ultimo_esito
           FROM maintenance.job_run_log r
          WHERE ((r.processo_codice = p.codice) OR (r.jobname = p.codice))) l ON (true))
  WHERE (p.attivo AND (p.obsoleto_dal IS NULL))
  ORDER BY p.canale, p.codice;
```


---
{% include-markdown "signature-core.md" %}
