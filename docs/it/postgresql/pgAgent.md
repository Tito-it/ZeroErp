# Estensione PostgreSQL: pgAgent

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: chi installa o gestisce il server, chi deve capire dove stanno i lavori a orario
>
> **Vedi anche**:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — l'elenco dei lavori, il naming, come se ne aggiunge uno, con che utente girano
> * [I lavori automatici: natura e identità](/guide/processi-automatici-classe-e-identita) — un lavoro che tocca i dati di un'azienda non esegue nell'orologio, va in coda
> * [Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — audit, giornale delle corse, task
> * [Installazione](/installazione) — passo 10, il demone
> * [Provisioning ruoli DB](/dev/backend/provisioning-db-roles) — il ruolo `zeroerp_job`

**pgAgent** è lo schedulatore dei lavori a orario di PostgreSQL. È fatto di due pezzi: un'**estensione**,
che tiene job, orari e passi in tabelle del database, e un **demone** di sistema, che si collega al
database e lancia i passi quando è ora. In Zero ERP lo usano i lavori periodici: manutenzione, automazioni,
allineamenti, e le «sveglie» che mettono in coda i lavori di dominio.

Questa pagina descrive l'estensione e il demone. **Quali lavori esistono e come se ne scrive uno** sta
nella guida [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali).

---

## Concetti

| Concetto | Tabella | Che cos'è |
| --- | --- | --- |
| Job | `pgagent.pga_job` | il lavoro: nome, descrizione, acceso o spento, prossima corsa |
| Schedule | `pgagent.pga_schedule` | quando parte: minuti, ore, giorni della settimana e del mese, mesi |
| Step | `pgagent.pga_jobstep` | cosa esegue: `jstkind = 's'` SQL, `'b'` comando di sistema (non usato) |
| Classe | `pgagent.pga_jobclass` | la categoria; i lavori del progetto stanno in *Routine Maintenance* |
| Log | `pgagent.pga_joblog`, `pga_jobsteplog` | l'esito tecnico di ogni corsa, visto da pgAgent |

Job e orari stanno nello schema `pgagent` del database: non ci sono file esterni.

---

## Come è fatto un lavoro nel progetto

In breve (il dettaglio è nella guida dei processi):

* **Nasce da un changeSet** in `db/changelog/migrations_v2/85_pgagent/`, che cancella e ricrea il job per
  nome. Un job creato o cambiato a mano da pgAdmin non è del progetto: alla prossima migrazione torna com'è
  scritto nel changeSet.
* **Lo step chiama una procedura sola**, `maintenance.proc_<nome>_job()`, `SECURITY DEFINER` del
  proprietario. Lo step è avvolto nel cancello della sveglia: se il processo è spento
  (`maintenance.fn_sveglia_accesa('<codice>')` falso), non parte.
* **La procedura passa dal giornale**: `maintenance.fn_run_and_log` scrive la corsa in
  `maintenance.job_run_log`, con lock contro le sovrapposizioni; se la corsa fallisce, il verbale viaggia
  fuori transazione via [`dblink`](/postgresql/dblink) e resta anche dopo il rollback.

Il giornale che conta è `maintenance.job_run_log`, non il log di pgAgent: dice anche **chi** ha girato e
per conto di chi.

---

## Installazione

### L'estensione

La crea il primo passo di Liquibase (`changelog-provision-pre.yaml`, baseline `001-01-02`), **solo se il
pacchetto pgAgent è installato sul server** (`pg_available_extensions`). Senza pacchetto l'installazione
prosegue: i changeSet di `85_pgagent` vengono saltati e i lavori a orario non esistono. È il caso della
CI, la cui immagine PostgreSQL non ha pgAgent.

I diritti di `zeroerp_job` su `pgagent` e l'`EXECUTE` sulle procedure dei job li dà
`scripts/sql/provision_zeroerp.sql` (fasi `pre` e `post`).

### Il demone

Il demone si collega come **`zeroerp_job`**, un ruolo di sistema che non possiede niente e può soltanto
avviare le procedure dei job.

* ⛔ **Non come `postgres`**: un job che gira da superuser crea oggetti col proprietario sbagliato (le
  tabelle di storico, per esempio). `maintenance.vw_job_run_da_superuser` segnala ogni processo la cui
  ultima corsa è stata fatta da un superuser.
* ⛔ **Non come il proprietario**: uno step scritto a mano potrebbe fare qualunque cosa sul progetto.

La stringa di connessione porta `user=zeroerp_job`, la password sta nel `.pgpass` dell'utente di sistema
che fa girare il demone. La connessione va su **`127.0.0.1`**, non sul socket locale: sul socket
PostgreSQL accetta solo l'utente di sistema con lo stesso nome, e il demone gira come `postgres`.

**Linux (systemd).** L'unità fa girare il demone come utente di sistema `postgres`, collegato al
database come `zeroerp_job`. È quella del server di sviluppo:

```ini
# /etc/systemd/system/pgagent.service
[Unit]
Description=pgAgent - PostgreSQL Job Scheduler
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=postgres
Group=postgres
ExecStart=/usr/bin/pgagent -f -l 1 "host=127.0.0.1 dbname=zeroerp user=zeroerp_job"
Restart=on-failure
RestartSec=5s
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

La password non sta nell'unità: sta in `/var/lib/postgresql/.pgpass` (proprietario `postgres`,
`chmod 600`), riga `127.0.0.1:5432:zeroerp:zeroerp_job:<password>`. Poi
`systemctl daemon-reload && systemctl enable --now pgagent`.

**Windows.** Si installa come servizio con `pgagent.exe INSTALL <nome-servizio> -u <account>
"host=127.0.0.1 dbname=zeroerp user=zeroerp_job"` e si avvia con `sc start <nome-servizio>`; la
password va nel `pgpass.conf` dell'account del servizio, non nella stringa.

### pgAdmin

Il nodo *pgAgent Jobs* è a livello di **server** e legge il *Maintenance database* impostato nelle
proprietà del server: deve essere il database che contiene `pgagent.*` (`zeroerp`).

---

## Operazioni veloci

Da superuser, per un controllo o una prova su una macchina. Un cambio che deve restare va nel changeSet.

```sql
-- Prossima corsa e stato dei job
SELECT jobname, jobenabled, jobnextrun, joblastrun
  FROM pgagent.pga_job
 ORDER BY jobname;

-- Forzare una corsa subito (il demone la prende al giro successivo)
UPDATE pgagent.pga_job
   SET jobnextrun = now() - interval '1 minute'
 WHERE jobname = 'sync_auth_user_expired_daily';

-- Il codice di uno step
SELECT s.jstname, s.jstcode
  FROM pgagent.pga_jobstep s
  JOIN pgagent.pga_job j ON j.jobid = s.jstjobid
 WHERE j.jobname = 'sync_auth_user_expired_daily';
```

Per sapere com'è andata una corsa si guarda `maintenance.job_run_log`, e
`maintenance.vw_job_run_da_guardare` per le corse che chiedono attenzione.

---

## Troubleshooting

* **Job non visibile in pgAdmin**: il *Maintenance database* del server non è quello con `pgagent.*`.
* **Il job non parte mai**: il demone non è in esecuzione, la stringa punta al database sbagliato, o il
  processo è spento e il cancello della sveglia lo ferma (è voluto: si accende dal catalogo dei processi).
* **Lo step fallisce con «permesso negato»**: lo step non è una chiamata a `maintenance.proc_*_job()`, e
  `zeroerp_job` da solo non può fare altro. È voluto.
* **Il job gira ma il giornale tace sui fallimenti**: il canale dblink manca per `zeroerp_job`
  (`myapp.dblink_log_connection`); si rilancia `scripts/sql/provision_dblink_log_channel.sql`.

---

## Le corse perse

pgAgent **non recupera** le corse che cadono mentre il server o il demone sono spenti: la prossima corsa
è quella successiva in calendario. Per questo un lavoro deve essere idempotente e non deve essere l'unica
fonte di un dato operativo (la regola è nella guida dei processi, «fonte di verità = dato operativo»).

---
{% include-markdown "signature-core.md" %}
