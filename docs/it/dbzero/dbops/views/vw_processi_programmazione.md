{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione.md" %}
# 🔍 View `vw_processi_programmazione`

> 📝 **Descrizione**
>
> PANORAMA: per ogni processo automatico vivo (ritiro non raggiunto, script.fn_e_obsoleto: un ritiro programmato compare fino al suo giorno), quale job pgAgent lo sveglia, quando girera', quando ha girato secondo pgAgent e secondo il giornale, e il verdetto. E' un panorama, non un presidio: elenca anche i sani; il presidio e' la colonna `da_guardare` (causa IS NOT NULL), proiettata da dbops.vw_processi_programmazione_da_guardare. Il legame col job si legge da dbops.processi.jobname_pgagent, non dal nome; il giornale per processo_codice o per jobname (le corse storiche hanno la prima colonna vuota). `stato` e `causa` escono in coppia da un solo CASE, nell'ordine: CODA -&gt; SU_RICHIESTA; sveglia spenta su questa installazione (colonna `acceso`, da dbops.fn_processo_acceso_dichiarato) -&gt; SPENTO, senza causa; COMMAND con segno di vita SESSIONE -&gt; OK se in pg_stat_activity c'e' una connessione viva con application_name = codice, altrimenti MUTO/SERVIZIO_GIU (conta l'esistenza della sessione, non backend_start, che pg_stat_activity maschera a chi non e' lo stesso utente); COMMAND con tolleranza -&gt; MAI_PARTITO/TIMER_NON_INSTALLATO, MUTO/TIMER_FERMO oltre la tolleranza, OK; COMMAND senza contratto -&gt; FUORI_PORTATA; PGAGENT -&gt; NON_PROGRAMMATO, JOB_ASSENTE, JOB_SPENTO (il job disabilitato dentro pgAgent), GIRA_E_NON_REGISTRA (pgAgent dice che e' girato e il giornale non ha la corsa di pgAgent: un lavoro che muore prima di raccontarlo), MAI_PARTITO/JOB_MAI_PARTITO (mai girato e la prossima esecuzione passata da piu' di un'ora), IN_ATTESA (mai girato, prima corsa futura), IN_RITARDO/JOB_IN_RITARDO (corsa dovuta passata da piu' di un'ora: col demone fermo pgAgent non aggiorna la prossima esecuzione), OK. La causa sceglie il testo per chi agisce (dbops.presidi.colonna_variante = 'causa').

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_programmazione AS
WITH panorama AS (
         SELECT p.codice AS processo_codice,
            p.classe,
            p.canale,
            p.jobname_pgagent,
            p.tolleranza_minuti,
            p.segno_di_vita,
            g.abilitato AS job_abilitato,
            g.prossima_esecuzione AS prossima_corsa,
            g.ultima_esecuzione AS pgagent_ultima_corsa,
            l.ultima_corsa AS giornale_ultima_corsa,
            l.ultima_corsa_pgagent,
            l.ultimo_esito,
            s.viva_dal AS sessione_viva_dal,
            acc.acceso,
                CASE
                    WHEN (p.canale = 'CODA'::text) THEN ARRAY['SU_RICHIESTA'::text, NULL::text]
                    WHEN (acc.acceso IS FALSE) THEN ARRAY['SPENTO'::text, NULL::text]
                    WHEN ((p.canale = 'COMMAND'::text) AND (p.segno_di_vita = 'SESSIONE'::text)) THEN
                    CASE
                        WHEN s.viva THEN ARRAY['OK'::text, NULL::text]
                        ELSE ARRAY['MUTO'::text, 'SERVIZIO_GIU'::text]
                    END
                    WHEN ((p.canale = 'COMMAND'::text) AND (p.tolleranza_minuti IS NOT NULL)) THEN
                    CASE
                        WHEN (l.ultima_corsa IS NULL) THEN ARRAY['MAI_PARTITO'::text, 'TIMER_NON_INSTALLATO'::text]
                        WHEN (l.ultima_corsa < (now() - make_interval(mins => p.tolleranza_minuti))) THEN ARRAY['MUTO'::text, 'TIMER_FERMO'::text]
                        ELSE ARRAY['OK'::text, NULL::text]
                    END
                    WHEN (p.canale = 'COMMAND'::text) THEN ARRAY['FUORI_PORTATA'::text, NULL::text]
                    WHEN (p.jobname_pgagent IS NULL) THEN ARRAY['NON_PROGRAMMATO'::text, 'NON_PROGRAMMATO'::text]
                    WHEN (g.abilitato IS NULL) THEN ARRAY['JOB_ASSENTE'::text, 'JOB_ASSENTE'::text]
                    WHEN (g.abilitato IS FALSE) THEN ARRAY['JOB_SPENTO'::text, 'JOB_SPENTO'::text]
                    WHEN ((g.ultima_esecuzione IS NOT NULL) AND (COALESCE(l.ultima_corsa_pgagent, '-infinity'::timestamp with time zone) < (g.ultima_esecuzione - '01:00:00'::interval))) THEN ARRAY['GIRA_E_NON_REGISTRA'::text, 'GIRA_E_NON_REGISTRA'::text]
                    WHEN ((g.ultima_esecuzione IS NULL) AND ((g.prossima_esecuzione IS NULL) OR (g.prossima_esecuzione < (now() - '01:00:00'::interval)))) THEN ARRAY['MAI_PARTITO'::text, 'JOB_MAI_PARTITO'::text]
                    WHEN (g.ultima_esecuzione IS NULL) THEN ARRAY['IN_ATTESA'::text, NULL::text]
                    WHEN (g.prossima_esecuzione < (now() - '01:00:00'::interval)) THEN ARRAY['IN_RITARDO'::text, 'JOB_IN_RITARDO'::text]
                    ELSE ARRAY['OK'::text, NULL::text]
                END AS verdetto
           FROM ((((dbops.processi p
             LEFT JOIN LATERAL dbops.fn_get_pgagent_job_stato(p.jobname_pgagent) g(abilitato, ultima_esecuzione, prossima_esecuzione) ON (true))
             LEFT JOIN LATERAL ( SELECT max(r.started_at) AS ultima_corsa,
                    max(r.started_at) FILTER (WHERE ((r.origine)::text = 'PGAGENT'::text)) AS ultima_corsa_pgagent,
                    ( SELECT r2.ok
                           FROM maintenance.job_run_log r2
                          WHERE (((r2.processo_codice = p.codice) OR (r2.jobname = p.codice)) AND (NOT r2.saltata))
                          ORDER BY r2.started_at DESC, r2.id DESC
                         LIMIT 1) AS ultimo_esito
                   FROM maintenance.job_run_log r
                  WHERE ((r.processo_codice = p.codice) OR (r.jobname = p.codice))) l ON (true))
             LEFT JOIN LATERAL ( SELECT (count(*) > 0) AS viva,
                    min(a.backend_start) AS viva_dal
                   FROM pg_stat_activity a
                  WHERE ((p.segno_di_vita = 'SESSIONE'::text) AND (a.datname = current_database()) AND (a.application_name = p.codice))) s ON (true))
             LEFT JOIN LATERAL ( SELECT dbops.fn_processo_acceso_dichiarato(p.codice) AS acceso) acc ON (true))
          WHERE (NOT script.fn_e_obsoleto(p.obsoleto_dal))
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
    verdetto[1] AS stato,
    (verdetto[2] IS NOT NULL) AS da_guardare,
    ultima_corsa_pgagent AS giornale_ultima_corsa_pgagent,
    tolleranza_minuti,
    segno_di_vita,
        CASE
            WHEN (segno_di_vita = 'SESSIONE'::text) THEN sessione_viva_dal
            ELSE giornale_ultima_corsa
        END AS ultimo_segno_di_vita,
    verdetto[2] AS causa,
    acceso
   FROM panorama
  ORDER BY canale, processo_codice;
```

</div>


---
{% include-markdown "signature-core.md" %}
