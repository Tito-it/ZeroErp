{% include-markdown "it/dbzero/maintenance/manual/vw_job_run_da_guardare.md" %}
# 🔍 View `vw_job_run_da_guardare`

> 📝 **Descrizione**
>
> I job che chiedono un occhio; deve restare VUOTA. Per ogni job si guarda l'ultima corsa VERA (le corse saltate sono escluse), cosi' un job che torna a funzionare esce da solo. Quattro motivi: l'ultima corsa e' FALLITA; e' rimasta aperta da oltre un'ora (presa e mai chiusa: il job e' morto senza arrivare al gestore d'eccezione); e' verde ma c'e' un rosso negli ultimi sette giorni (intermittente, anche se in corso da meno di un'ora); per un processo col verdetto completo, e' verde ma e' ricaduto dopo essere tornato verde (instabile, almeno due tratti rossi). falliti_ultimi_7_giorni conta le CORSE fallite (run_uuid distinti) dall'ultima corsa vera all'indietro: quando il chiamante di maintenance.fn_run_and_log cattura l'eccezione, una corsa fallita lascia due righe rosse con lo stesso run_uuid. Le colonne in coda dicono a chi tocca: sqlstate dell'ultima corsa; causa (dbops.cause_fallimento) = AMBIENTE per una corsa appesa o per lo SQLSTATE d'ambiente dell'ultimo rosso (script.fn_sqlstate_di_ambiente), poi la causa del codice dell'ultimo rosso (config.codici_errore), poi quella del processo (dbops.processi), PROGRAMMA senza processo a catalogo; ultimo_rosso_job_run_id e' la corsa da cui la causa e' letta. Il lavoro che non parte affatto non sta qui: lo vede dbops.vw_processi_programmazione_da_guardare, dalla tolleranza dichiarata nel catalogo. Niente RLS: un giro di manutenzione non appartiene a un'azienda; chi la vede lo decide il backend.

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
    ( SELECT count(DISTINCT p.run_uuid) AS count
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
