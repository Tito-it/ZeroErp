{% include-markdown "it/dbzero/maintenance/manual/vw_job_run_da_guardare.md" %}
# 🔍 View `vw_job_run_da_guardare`

> 📝 **Descrizione**
>
> I job che chiedono un occhio: quelli la cui ULTIMA corsa e' FALLITA, e quelli la cui ultima corsa e' rimasta APERTA da oltre un'ora (il processo e' morto senza arrivare nemmeno al gestore d'eccezione). DEVE restare VUOTA. ⭐ Esiste perche' dal changeSet 20260905-36 una corsa fallita lascia finalmente una riga rossa: prima il verbale veniva scritto e annullato dal RAISE, e nel giornale non e' MAI esistito un fallimento di un job pgAgent (misurato: 0 rossi con origine PGAGENT contro 31 dei command). ⛔ Ma righe rosse in una tabella che nessuno interroga sono un silenzio nuovo, e questa vista e' il posto dove guardare. ⭐ Si guarda solo l'ULTIMA corsa di ogni job, non tutti i rossi: cosi' un job che ricomincia a funzionare ESCE DA SOLO, senza colonne «visto» ne' finestre arbitrarie — e sync_auth_user_active, che il 2026-09-05 aveva 29 fallimenti in un giorno, occupa UNA riga invece di ventinove. ⭐ E un TERZO motivo prende l'intermittenza: ultima corsa verde ma almeno un rosso negli ultimi sette giorni — senza, un job che fallisce e passa sarebbe invisibile, ed e' proprio il caso di sync_auth_user_active. Anche quel ramo si auto-pulisce: dopo sette giorni senza rossi il job esce da solo. ⛔ E non vede IL JOB CHE NON PARTE AFFATTO: per quello servirebbe che ogni processo dichiarasse ogni quanto deve girare, e dbops.processi non ce l'ha — stessa forma di R-12 da un altro lato, e resta scoperta. ⚠️ Niente RLS: un giro di manutenzione non appartiene a un'azienda. Chi la vede lo decide il backend con area funzionale e profilo, come per le viste di presidio sorelle. ⛔ Rev 2026-10-10: l'ultima corsa e' l'ultima corsa VERA — le righe saltate (maintenance.job_run_log.saltata) sono escluse. Una corsa appesa tiene il lock, e ogni sveglia successiva scrive una skip piu' recente: prima la skip diventava l'ultima corsa e il ramo «presa e mai chiusa» non scattava piu'. Brief: brief-db-corsa-saltata-non-e-una-corsa §2.2. ⭐ Rev 2026-10-16: tre colonne in coda. sqlstate (dell'ultima corsa, da job_run_log.sqlstate); causa (dbops.cause_fallimento), da cui dbops.presidi_cause dice a chi tocca la riga: corsa appesa o SQLSTATE dell'ultimo rosso di classe 08/53/57/58 → AMBIENTE; poi la causa del codice dell'ultimo rosso (config.codici_errore.causa_fallimento), poi quella del processo (dbops.processi.causa_fallimento), e PROGRAMMA senza processo a catalogo. Mai NULL. ultimo_rosso_job_run_id: la corsa da cui la causa e' letta (per un intermittente l'ultima corsa e' verde). ⛔ E il motivo «presa e mai chiusa» vale solo oltre l'ora: una corsa in corso da meno, con rossi recenti, era detta morta; ora e' «in corso adesso, ma ha fallito di recente: intermittente». Prima il presidio aveva un solo destinatario (SISTEMISTA) per guasti di natura diversa. Brief: brief-db-presidio-job-run-a-chi-tocca. ⭐ Rev 2026-10-16 (bis): la lista degli SQLSTATE dell'ambiente sta in script.fn_sqlstate_di_ambiente, sede unica con i gestori WHEN others del framework automazioni (D8), e si allarga a 42501 (privilegio mancante) e 55P03 (lock non ottenuto, D10). Brief: brief-db-presidio-job-run-a-chi-tocca §10. ⭐ Rev 2026-10-18: l'intermittenza copre due guasti, il RESIDUO (una corsa lavora una parte, e il verde non riprende cio' che il rosso ha lasciato) e l'INSTABILITA' (il lavoro cade, si rialza, ricade). Per un processo il cui ogni giro e' un verdetto completo (dbops.processi.corsa_verdetto_completo: lo smoke notturno, le automazioni, il digest) il residuo non esiste: il motivo scatta solo se nei sette giorni ci sono almeno DUE TRATTI ROSSI separati da un verde (motivo «ricaduto dopo essere tornato verde: instabile»), e un solo tratto rosso esce al primo verde. sync_auth_user_active riallineava tutti gli utenti a ogni corsa: era un verdetto completo instabile, e resterebbe in vista. E per un verdetto completo la corsa in corso da meno di un'ora non e' un verdetto: conta l'ultima corsa chiusa (D2). Per gli altri processi niente cambia. falliti_ultimi_7_giorni resta per tutti. Brief: brief-db-intermittente-e-verdetto-completo.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW maintenance.vw_job_run_da_guardare AS
WITH ultima AS (
         SELECT DISTINCT ON (l.jobname) l.id,
            l.jobname,
            l.stepname,
            l.processo_codice,
            l.origine,
            l.started_at,
            l.ended_at,
            l.ok,
            l.error_code,
            l.message,
            l.error_detail,
            l.run_uuid,
            l.auth_user_id,
            l.meta,
            l.sqlstate,
            COALESCE(pr_1.corsa_verdetto_completo, false) AS verdetto_completo
           FROM (maintenance.job_run_log l
             LEFT JOIN dbops.processi pr_1 ON ((pr_1.codice = l.processo_codice)))
          WHERE ((NOT l.saltata) AND (NOT (COALESCE(pr_1.corsa_verdetto_completo, false) AND (l.ok IS NULL) AND (l.ended_at IS NULL) AND (l.started_at >= (now() - '01:00:00'::interval)))))
          ORDER BY l.jobname, l.started_at DESC, l.id DESC
        ), tratti AS (
         SELECT s.jobname,
            count(*) FILTER (WHERE ((s.ok IS FALSE) AND (s.precedente IS DISTINCT FROM false))) AS tratti_rossi
           FROM ( SELECT p.jobname,
                    p.ok,
                    lag(p.ok) OVER (PARTITION BY p.jobname ORDER BY p.started_at, p.id) AS precedente
                   FROM maintenance.job_run_log p
                  WHERE ((NOT p.saltata) AND (p.ok IS NOT NULL) AND (p.started_at >= (now() - '7 days'::interval)))) s
          GROUP BY s.jobname
        ), da_guardare AS (
         SELECT u.id,
            u.jobname,
            u.stepname,
            u.processo_codice,
            u.origine,
            u.started_at,
            u.ended_at,
            u.ok,
            u.error_code,
            u.message,
            u.error_detail,
            u.run_uuid,
            u.sqlstate,
            ((u.ok IS NULL) AND (u.ended_at IS NULL) AND (u.started_at < (now() - '01:00:00'::interval))) AS appesa,
            u.verdetto_completo
           FROM (ultima u
             LEFT JOIN tratti t ON ((t.jobname = u.jobname)))
          WHERE ((u.ok IS FALSE) OR ((NOT u.verdetto_completo) AND (EXISTS ( SELECT 1
                   FROM maintenance.job_run_log p
                  WHERE ((p.jobname = u.jobname) AND (p.ok IS FALSE) AND (p.started_at >= (now() - '7 days'::interval)))))) OR (u.verdetto_completo AND (COALESCE(t.tratti_rossi, (0)::bigint) >= 2)) OR ((u.ok IS NULL) AND (u.ended_at IS NULL) AND (u.started_at < (now() - '01:00:00'::interval))))
        )
 SELECT g.jobname,
    g.processo_codice,
    g.origine,
    g.started_at,
    g.ended_at,
        CASE
            WHEN (g.ok IS FALSE) THEN 'l''ultima corsa e'' FALLITA'::text
            WHEN g.appesa THEN 'presa e mai chiusa: il job e'' morto senza dire niente'::text
            WHEN g.verdetto_completo THEN 'ultima corsa OK, ma e'' ricaduto dopo essere tornato verde: instabile'::text
            WHEN ((g.ok IS NULL) AND (g.ended_at IS NULL)) THEN 'in corso adesso, ma ha fallito di recente: intermittente'::text
            ELSE 'ultima corsa OK, ma ha fallito di recente: intermittente'::text
        END AS motivo,
    g.error_code,
    g.message,
    g.error_detail,
    (now() - g.started_at) AS da_quanto,
    g.run_uuid,
    g.id AS job_run_id,
    ( SELECT count(*) AS count
           FROM maintenance.job_run_log p
          WHERE ((p.jobname = g.jobname) AND (p.ok IS FALSE) AND (p.started_at >= (g.started_at - '7 days'::interval)))) AS falliti_ultimi_7_giorni,
    g.sqlstate,
        CASE
            WHEN g.appesa THEN 'AMBIENTE'::text
            WHEN script.fn_sqlstate_di_ambiente(r.sqlstate) THEN 'AMBIENTE'::text
            ELSE COALESCE(ce.causa_fallimento, pr.causa_fallimento, 'PROGRAMMA'::text)
        END AS causa,
    r.id AS ultimo_rosso_job_run_id
   FROM (((da_guardare g
     LEFT JOIN LATERAL ( SELECT p.id,
            p.error_code,
            p.sqlstate,
            p.processo_codice
           FROM maintenance.job_run_log p
          WHERE ((p.jobname = g.jobname) AND (p.ok IS FALSE))
          ORDER BY p.started_at DESC, p.id DESC
         LIMIT 1) r ON (true))
     LEFT JOIN config.codici_errore ce ON ((ce.codice = r.error_code)))
     LEFT JOIN dbops.processi pr ON ((pr.codice = COALESCE(r.processo_codice, g.processo_codice))));
```

</div>


---
{% include-markdown "signature-core.md" %}
