{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione.md" %}
# 🔍 View `vw_processi_programmazione`

> 📝 **Descrizione**
>
> PANORAMA: per ogni processo automatico attivo — quale job pgAgent lo sveglia, quando girera', quando ha girato secondo pgAgent e secondo il nostro giornale. ⭐ La colonna che vale piu' di tutte e' `stato`, e il valore che conta e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non lo sa — e' la firma esatta di un lavoro che muore prima di riuscire a raccontarlo, cioe' di R-12, il job morto per sei mesi con l'ultimo verdetto a «done». Questo confronto lo avrebbe trovato in un giorno. ⚠️ Il legame col job NON e' il nome: si legge da dbops.processi.jobname_pgagent, perche' due job su quattordici si chiamano diversamente dal processo che registrano. ⚠️ Il giornale si legge per processo_codice OPPURE per jobname: le corse storiche hanno la prima colonna vuota, e senza il ripiego ogni processo sembrerebbe non aver mai girato prima di settembre 2026. ⛔ IL CONFRONTO GUARDA CHI HA SCRITTO LA RISPOSTA, rev 2026-09-07 (brief-db-sveglia-dei-processi §9.5-bis, segnalato dal backend): il ramo GIRA_E_NON_REGISTRA legge `giornale_ultima_corsa_pgagent`, non `giornale_ultima_corsa`. La domanda e' «la sveglia di pgAgent ha lasciato traccia?», e una corsa scritta da un altro attore sotto lo stesso codice non e' una risposta a quella domanda — spostava avanti la data e spegneva il rilevatore di R-12 sul job sorvegliato. ⭐ DUE STATI NON SONO GUASTI E NON LO SARANNO MAI, ma per ragioni OPPOSTE (rev 2026-09-06, brief-db-sveglia-dei-processi §8.6): FUORI_PORTATA e' un limite di VISTA — i COMMAND li sveglia systemd e di loro il database non puo' sapere se stanno partendo; chi puo' saperlo e' il backend, che dal 2026-09-06 lo presidia da backend/deploy/sveglie.json. SU_RICHIESTA e' invece un fatto della NATURA del processo: i CODA li sveglia una persona, quindi una cadenza da confrontare non esiste affatto. Tenerli sotto la stessa parola faceva contare insieme cose diverse. ⚠️ listen_cambio_reparto resta fra i COMMAND di proposito: e' un listener che scrive un solo run, ma che sia un listener il database non lo sa — nessuna colonna lo dice, e dedurlo dal nome sarebbe una coincidenza travestita da regola. ⭐ E' un panorama, non un presidio: elenca anche i sani, perche' senza sapere quanti sono i sani un guasto sembra la norma. ⛔ Il presidio NON si scrive piu' come un NOT IN a mano: e' la colonna `da_guardare`, calcolata qui accanto al CASE che produce gli stati, e la vista dbops.vw_processi_programmazione_da_guardare la proietta. Il criterio del guasto sta in UN posto solo: uno stato nuovo non ha un default in cui cadere, e chi lo aggiunge deve decidere qui.

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_programmazione AS
WITH panorama AS (
         SELECT p.codice AS processo_codice,
            p.classe,
            p.canale,
            p.jobname_pgagent,
            g.abilitato AS job_abilitato,
            g.prossima_esecuzione AS prossima_corsa,
            g.ultima_esecuzione AS pgagent_ultima_corsa,
            l.ultima_corsa AS giornale_ultima_corsa,
            l.ultima_corsa_pgagent,
            l.ultimo_esito,
                CASE
                    WHEN (p.canale = 'CODA'::text) THEN 'SU_RICHIESTA'::text
                    WHEN (p.canale = 'COMMAND'::text) THEN 'FUORI_PORTATA'::text
                    WHEN (p.jobname_pgagent IS NULL) THEN 'NON_PROGRAMMATO'::text
                    WHEN (g.abilitato IS NULL) THEN 'JOB_ASSENTE'::text
                    WHEN (g.abilitato IS FALSE) THEN 'JOB_SPENTO'::text
                    WHEN ((g.ultima_esecuzione IS NOT NULL) AND (COALESCE(l.ultima_corsa_pgagent, '-infinity'::timestamp with time zone) < (g.ultima_esecuzione - '01:00:00'::interval))) THEN 'GIRA_E_NON_REGISTRA'::text
                    WHEN (g.ultima_esecuzione IS NULL) THEN 'MAI_PARTITO'::text
                    ELSE 'OK'::text
                END AS stato
           FROM ((dbops.processi p
             LEFT JOIN LATERAL dbops.fn_get_pgagent_job_stato(p.jobname_pgagent) g(abilitato, ultima_esecuzione, prossima_esecuzione) ON (true))
             LEFT JOIN LATERAL ( SELECT max(r.started_at) AS ultima_corsa,
                    max(r.started_at) FILTER (WHERE ((r.origine)::text = 'PGAGENT'::text)) AS ultima_corsa_pgagent,
                    ( SELECT r2.ok
                           FROM maintenance.job_run_log r2
                          WHERE ((r2.processo_codice = p.codice) OR (r2.jobname = p.codice))
                          ORDER BY r2.started_at DESC, r2.id DESC
                         LIMIT 1) AS ultimo_esito
                   FROM maintenance.job_run_log r
                  WHERE ((r.processo_codice = p.codice) OR (r.jobname = p.codice))) l ON (true))
          WHERE (p.attivo AND (p.obsoleto_dal IS NULL))
        )
 SELECT processo_codice,
    classe,
    canale,
    jobname_pgagent,
    job_abilitato,
    prossima_corsa,
    pgagent_ultima_corsa,
    giornale_ultima_corsa,
    ultimo_esito,
    stato,
    (stato <> ALL (ARRAY['OK'::text, 'FUORI_PORTATA'::text, 'SU_RICHIESTA'::text])) AS da_guardare,
    ultima_corsa_pgagent AS giornale_ultima_corsa_pgagent
   FROM panorama
  ORDER BY canale, processo_codice;
```


---
{% include-markdown "signature-core.md" %}
