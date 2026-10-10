{% include-markdown "it/dbzero/maintenance/manual/vw_job_run_da_guardare.md" %}
# 🔍 View `vw_job_run_da_guardare`

> 📝 **Descrizione**
>
> I job che chiedono un occhio: quelli la cui ULTIMA corsa e' FALLITA, e quelli la cui ultima corsa e' rimasta APERTA da oltre un'ora (il processo e' morto senza arrivare nemmeno al gestore d'eccezione). DEVE restare VUOTA. ⭐ Esiste perche' dal changeSet 20260905-36 una corsa fallita lascia finalmente una riga rossa: prima il verbale veniva scritto e annullato dal RAISE, e nel giornale non e' MAI esistito un fallimento di un job pgAgent (misurato: 0 rossi con origine PGAGENT contro 31 dei command). ⛔ Ma righe rosse in una tabella che nessuno interroga sono un silenzio nuovo, e questa vista e' il posto dove guardare. ⭐ Si guarda solo l'ULTIMA corsa di ogni job, non tutti i rossi: cosi' un job che ricomincia a funzionare ESCE DA SOLO, senza colonne «visto» ne' finestre arbitrarie — e sync_auth_user_active, che il 2026-09-05 aveva 29 fallimenti in un giorno, occupa UNA riga invece di ventinove. ⭐ E un TERZO motivo prende l'intermittenza: ultima corsa verde ma almeno un rosso negli ultimi sette giorni — senza, un job che fallisce e passa sarebbe invisibile, ed e' proprio il caso di sync_auth_user_active. Anche quel ramo si auto-pulisce: dopo sette giorni senza rossi il job esce da solo. ⛔ E non vede IL JOB CHE NON PARTE AFFATTO: per quello servirebbe che ogni processo dichiarasse ogni quanto deve girare, e dbops.processi non ce l'ha — stessa forma di R-12 da un altro lato, e resta scoperta. ⚠️ Niente RLS: un giro di manutenzione non appartiene a un'azienda. Chi la vede lo decide il backend con area funzionale e profilo, come per le viste di presidio sorelle. ⛔ Rev 2026-10-10: l'ultima corsa e' l'ultima corsa VERA — le righe saltate (maintenance.job_run_log.saltata) sono escluse. Una corsa appesa tiene il lock, e ogni sveglia successiva scrive una skip piu' recente: prima la skip diventava l'ultima corsa e il ramo «presa e mai chiusa» non scattava piu'. Brief: brief-db-corsa-saltata-non-e-una-corsa §2.2.

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
            l.meta
           FROM maintenance.job_run_log l
          WHERE (NOT l.saltata)
          ORDER BY l.jobname, l.started_at DESC, l.id DESC
        )
 SELECT jobname,
    processo_codice,
    origine,
    started_at,
    ended_at,
        CASE
            WHEN (ok IS FALSE) THEN 'l''ultima corsa e'' FALLITA'::text
            WHEN ((ok IS NULL) AND (ended_at IS NULL)) THEN 'presa e mai chiusa: il job e'' morto senza dire niente'::text
            ELSE 'ultima corsa OK, ma ha fallito di recente: intermittente'::text
        END AS motivo,
    error_code,
    message,
    error_detail,
    (now() - started_at) AS da_quanto,
    run_uuid,
    id AS job_run_id,
    ( SELECT count(*) AS count
           FROM maintenance.job_run_log p
          WHERE ((p.jobname = u.jobname) AND (p.ok IS FALSE) AND (p.started_at >= (u.started_at - '7 days'::interval)))) AS falliti_ultimi_7_giorni
   FROM ultima u
  WHERE ((ok IS FALSE) OR (EXISTS ( SELECT 1
           FROM maintenance.job_run_log p
          WHERE ((p.jobname = u.jobname) AND (p.ok IS FALSE) AND (p.started_at >= (now() - '7 days'::interval))))) OR ((ok IS NULL) AND (ended_at IS NULL) AND (started_at < (now() - '01:00:00'::interval))));
```


---
{% include-markdown "signature-core.md" %}
