{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione.md" %}
# 🔍 View `vw_processi_programmazione`

> 📝 **Descrizione**
>
> PANORAMA: per ogni processo automatico attivo — quale job pgAgent lo sveglia, quando girera', quando ha girato secondo pgAgent e secondo il nostro giornale. ⭐ La colonna che vale piu' di tutte e' `stato`, e il valore che conta e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non lo sa — e' la firma esatta di un lavoro che muore prima di riuscire a raccontarlo, cioe' di R-12, il job morto per sei mesi con l'ultimo verdetto a «done». Questo confronto lo avrebbe trovato in un giorno. ⚠️ Il legame col job NON e' il nome: si legge da dbops.processi.jobname_pgagent, perche' due job su quattordici si chiamano diversamente dal processo che registrano. ⚠️ Il giornale si legge per processo_codice OPPURE per jobname: le corse storiche hanno la prima colonna vuota, e senza il ripiego ogni processo sembrerebbe non aver mai girato prima di settembre 2026. ⛔ IL CONFRONTO GUARDA CHI HA SCRITTO LA RISPOSTA, rev 2026-09-07 (brief-db-sveglia-dei-processi §9.5-bis, segnalato dal backend): il ramo GIRA_E_NON_REGISTRA legge `giornale_ultima_corsa_pgagent`, non `giornale_ultima_corsa`. ⭐ I COMMAND CON UN CONTRATTO NON SONO PIU' FUORI_PORTATA, rev 2026-09-11 (brief-db-quattro-processi-senza-presidio §10.2, decisione di Tid): dal 20260911-13 il catalogo dichiara tolleranza_minuti e segno_di_vita, quindi il database SA che cosa aspettarsi. GIORNALE + tolleranza: OK se l'ultima corsa e' entro la tolleranza, MUTO se e' piu' vecchia, MAI_PARTITO se non c'e' — e MAI_PARTITO su un COMMAND e' il timer dichiarato e mai installato, cioe' il §11.5 dei presidi visto dal database. SESSIONE: OK se in pg_stat_activity c'e' una connessione viva con application_name = codice sul database corrente, altrimenti MUTO — e' la forma dei servizi sempre accesi (listen_cambio_reparto), il segno di vita e' un FATTO e non una dichiarazione. MUTO e' l'unico stato nuovo: «era vivo ed e' taciuto». FUORI_PORTATA resta per i COMMAND SENZA contratto: un limite di vista, non un guasto. SU_RICHIESTA resta per i CODA: una cadenza non esiste. ⭐ E' un panorama, non un presidio: elenca anche i sani. ⛔ Il presidio NON si scrive come un NOT IN a mano: e' la colonna `da_guardare`, calcolata qui accanto al CASE, e dbops.vw_processi_programmazione_da_guardare la proietta — MUTO e MAI_PARTITO ci entrano da soli, senza toccare quella riga. Tre colonne in coda dal 2026-09-11: tolleranza_minuti, segno_di_vita, ultimo_segno_di_vita (la corsa per GIORNALE, l'avvio della sessione per SESSIONE). ⛔ IL VERDETTO SESSIONE POGGIA SULL'ESISTENZA DELLA SESSIONE, rev 2026-09-14: pg_stat_activity mostra a tutti la riga (pid, usename, application_name) ma maschera backend_start e il resto a chi non e' lo stesso utente della sessione ne' pg_read_all_stats — e una vista non cambia l'utente che pg_stat_get_activity() guarda. Fino a quel giorno il ramo leggeva `viva_dal IS NOT NULL`: OK per zeroerp_app (la sessione del listener e' sua) e MUTO per chiunque altro, titodb compreso — cioe' per fn_conta_presidio, che e' SECURITY DEFINER. Il primo digest della giornaliera (14-09 07:00) ha contato 1 su un listener vivo da 31 ore e il perimetro LIBERO del presidio ha protestato: il conteggio diceva 1 e l'elenco letto come app era vuoto. Il pgTAP non lo vedeva perche' la sessione del test e' del suo stesso utente. ultimo_segno_di_vita per SESSIONE resta informazione (NULL a chi non puo' leggerlo), non verdetto. ⭐ LA CAUSA, rev 2026-10-09 (brief-db-presidio-processi-testo-per-causa §3 B.1, forma B di Tid): colonna `causa` in coda. Due stati hanno due cause con due rimedi — MUTO e' TIMER_FERMO su un COMMAND col giornale e SERVIZIO_GIU su un COMMAND con la sessione; MAI_PARTITO e' TIMER_NON_INSTALLATO su un COMMAND e JOB_MAI_PARTITO su un PGAGENT — e un testo unico dava il rimedio sbagliato (il 2026-10-09 diceva «Esegui ora» a un servizio sempre acceso). Ogni ramo del CASE consegna la coppia [stato, causa]: un secondo CASE farebbe due elenchi degli stessi casi. E `da_guardare` e' ora `causa IS NOT NULL`: i rami sani non hanno causa, i guasti ce l'hanno per costruzione, e il NOT IN sugli stati sani — un secondo elenco — non c'e' piu'. La causa sceglie il testo per chi agisce: dbops.presidi.colonna_variante = 'causa', dbops.presidi_testi.variante. ⭐ PGAGENT: IL SEGNALE E' LA CORSA DOVUTA, rev 2026-10-14 (brief-db-statistiche-tabelle-job-notturno §8): MAI_PARTITO/JOB_MAI_PARTITO solo se il job non ha mai girato E la prossima esecuzione e' passata da piu' di un'ora (o non ce n'e' una); mai girato con la prima corsa ancora futura e' IN_ATTESA, senza causa; ha girato ma la corsa dovuta e' passata da piu' di un'ora e' IN_RITARDO/JOB_IN_RITARDO. Col demone fermo pgAgent non aggiorna jobnextrun, che resta nel passato: e' il fatto che dice «il programmatore non gira». Prima si leggeva «non ha mai girato»: falso allarme su ogni job nuovo fino alla prima corsa (analyze_statistiche, 14-10) e silenzio sul demone fermo per ogni job che aveva gia' girato. ⭐ SPENTO NON E' MORTO, rev 2026-10-16 (brief-db-processi-accensione-per-ambiente §5.3): stato SPENTO, senza causa e quindi non da guardare, quando la sveglia del processo e' spenta su questa installazione — per il default del suo ambiente (dbops.processi.acceso_in_sviluppo/acceso_in_produzione) o per la scelta a mano (dbops.processi_accensione). Viene prima di ogni verdetto di liveness. Colonna `acceso` in coda, letta da dbops.fn_processo_acceso_dichiarato: NULL per i CODA e con l'ambiente non dichiarato (che dice il suo presidio, dbops.vw_ambiente_non_dichiarato). JOB_SPENTO resta un'altra cosa: il job disabilitato dentro pgAgent, fuori dal catalogo, e si guarda.

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
