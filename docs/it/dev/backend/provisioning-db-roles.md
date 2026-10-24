# Provisioning ruoli DB (runtime, migratore, RLS)

> **Ultimo aggiornamento**: 15 ottobre 2026
>
> **Destinatari**: chi prepara un database ZeroErp (sviluppo, CI, produzione) e
> chi configura il backend che ci si collega.
>
> **Vedi anche** — guide correlate:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
> * [Architettura multi face auth](/guide/architettura-multi-face-auth) — vesti, RLS come difesa
> * [Contratto GUC APP](/guide/contratto-guc-app) — l'identità che arriva al DB, fail-closed
> * [Processi automatici — classe e identità](/guide/processi-automatici-classe-e-identita) — utenti tecnici dei job
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — chi possiede le shadow di `storico`
>
> **Vedi anche** — sviluppo:
>
> * [Configurazione Django su backend-dev](configurazione-django.md) — dove si scrive `DB_USER`
> * [Playbook operativo backend](play-book-operativo-backend.md) §7-bis — lo stesso passo, solo comandi

---

## Scopo

Un processo unico e ripetibile per dare ai ruoli PostgreSQL di ZeroErp i
privilegi giusti, **dagli script versionati e mai a mano**: un privilegio dato a
mano esiste su una sola macchina, e il database ricostruito da zero (la CI) non
lo ha ([linee-guida-sql §11.9](/linee-guida-sql)).

## Il principio

* Il backend si collega **sempre** con un solo ruolo tecnico, `zeroerp_app`.
* L'**identità** di chi sta operando non è il ruolo DB: arriva con le GUC di
  sessione (`app.current_user_id`, `app.current_identita_id`,
  `app.ruolo_applicativo`, `app.soggetto_ruolo_id`, …) che il backend imposta a
  ogni richiesta. Contratto completo: [Contratto GUC APP](/guide/contratto-guc-app).
* Le **policy RLS** filtrano le righe su quelle GUC, non sul nome del ruolo.
  Senza GUC coerenti operano **fail-closed**: zero righe in lettura, rifiuto in
  scrittura.

Quindi:

* il **ruolo DB** dice *con quale utenza tecnica il backend parla a PostgreSQL*;
* le **GUC** dicono *per conto di chi*;
* la **RLS** decide *quali righe*.

⛔ Cambiare `DB_USER` in un ruolo owner, superuser o `BYPASSRLS` **spegne la
RLS** in silenzio. Il backend lo rifiuta: il middleware verifica a ogni richiesta
che la connessione non scavalchi le policy, e se sì risponde
`E_DB_ROLE_UNSAFE` (`core.services.system_context.connection_role_bypasses_rls`).

## I ruoli di sistema

ZeroERP porta con sé un **modello di ruoli fisso**: nomi, attributi e diritti sono
parte del prodotto, come le tabelle. Lo crea e lo allinea un solo script,
[`scripts/sql/provision_zeroerp.sql`](#provision_zeroerpsql-cosa-fa), lo stesso
per la CI, il database di prova e un'installazione nuova.

| Ruolo | Chi lo usa | Attributi | Che cosa può fare |
| --- | --- | --- | --- |
| **`zeroerp_owner`** | Liquibase (tutte le passate tranne quelle da superuser), `manage.py migrate` | `LOGIN`, non superuser, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE` | è il **proprietario** del database e di **tutti** gli oggetti del progetto, tranne le funzioni del registro `dbops.sec_functions_owner` (sotto); è membro di `pg_read_all_stats`, così chi legge come proprietario (il digest) vede l'orario delle sessioni degli altri ruoli |
| **`zeroerp_job`** | il demone **pgAgent** | `LOGIN`, non superuser, `NOBYPASSRLS`, **non possiede niente** | chiama **soltanto** le procedure dei job (`maintenance.proc_*_job`), che girano come `zeroerp_owner`; legge e scrive le tabelle di `pgagent` che servono al demone |
| **`zeroerp_app`** | il backend Django (`DB_USER`): web, management command, timer | `LOGIN`, **`NOBYPASSRLS`**, non proprietario | quello che dà la fase `post` di `provision_zeroerp.sql` ([La postura di zeroerp_app](#la-postura-di-zeroerp_app)); la RLS lo filtra |
| `zeroerp_log` | il canale di log via `dblink` (scrive `dbops.error_log` fuori dalla transazione che fallisce) | `LOGIN` | solo `INSERT` su `dbops.error_log` — vedi [dblink](/postgresql/dblink) |
| `postgres` | **solo** il provisioning | superuser | crea ruoli, database ed estensioni, poi passa la mano |

### Le regole

* ⛔ **I nomi sono di sistema e non si configurano.** Il database li nomina per
  esteso nei `GRANT`, nelle policy e nei presidi: un nome diverso darebbe un
  database che si rompe in silenzio.
* ⭐ **Chi vuole un utente suo lo aggiunge come membro, non rinomina.** Per esempio
  `GRANT zeroerp_app TO mario_dba`. ⚠️ Un utente personale **membro di
  `zeroerp_owner`** che crea oggetti li crea a nome **suo**, non dell'owner: gli
  serve anche `ALTER ROLE <utente> SET role = zeroerp_owner`, così ogni sua
  sessione lavora come il proprietario.
* ⛔ **Le password non hanno default.** Lo script le chiede e si ferma se mancano;
  servono solo per **creare** un ruolo: di un ruolo che esiste non tocca la
  password, perché i ruoli valgono per tutto il cluster e lo stesso ruolo può
  servire un altro database.
* ⭐ **Un owner solo.** Tutto ciò che è del progetto è di `zeroerp_owner`. Le
  **sole eccezioni** sono le funzioni dichiarate in `dbops.sec_functions_owner`,
  che devono appartenere a un **superuser** (il canale `dblink` rifiuta la
  connessione senza password a chi non lo è), più `dbops.fn_sync_functions_owner`
  che le allinea. Le riassegna a `postgres` il provision-post di Liquibase.
* ⭐ **I job girano come il proprietario, chiunque li lanci.** Le procedure
  `maintenance.proc_*_job` sono `SECURITY DEFINER` di `zeroerp_owner`, con
  `search_path` fissato e **senza** `EXECUTE` per `PUBLIC`: pgAgent, collegato come
  `zeroerp_job`, può solo chiamarle, e ciò che creano (shadow di storico, trigger,
  indici delle FK) nasce del proprietario. Lo presidia
  `db/pgtap/maintenance/test-proc-job-definer-v1.sql`.
* ⛔ **Si controlla che cosa un ruolo può fare, non come si chiama.** Un presidio
  che pretende `session_user = 'zeroerp_job'` darebbe un falso rosso a chi fa
  girare pgAgent con un suo utente membro di `zeroerp_job`: si controllano la
  membership (`pg_has_role`) e gli attributi (`rolsuper`).
* ⛔ **Il superuser non lavora.** Un job che gira come `postgres` crea oggetti col
  proprietario sbagliato, ed è il motivo per cui è esistito
  `provision_storico_scope.sql` (sotto).

### Dove il modello è in vigore

| Ambiente | Proprietario degli oggetti | Chi migra | Con chi gira pgAgent |
| --- | --- | --- | --- |
| Database di prova (`scripts/ci-local.sh`, `zeroerp_ruoli`) | `zeroerp_owner` | `zeroerp_owner` | nessun demone: i job li esegue `ci_apply` |
| CI di GitHub (`ci.yaml`, `ci-validate.yaml`) | `zeroerp_owner` | `zeroerp_owner` | pgAgent non c'è |
| Sviluppo (`zeroerp`) | `zeroerp_owner` | un utente personale che lavora come `zeroerp_owner` | `zeroerp_job` |

**Un utente personale che lavora come proprietario.** Sullo sviluppo ci si collega
col proprio nome, che è **membro** di `zeroerp_owner`, e ogni sessione su quel
database lavora come proprietario (`ALTER ROLE <utente> IN DATABASE zeroerp SET role
= zeroerp_owner`). Così ciò che si crea, a mano o con Liquibase, nasce di
`zeroerp_owner`. Un database i cui oggetti appartengono ancora a un utente personale
si converte con `scripts/sql/converti_db_al_modello_ruoli.sql` (da superuser, a
pgAgent fermo, prima con `-v solo_prova=1`).

⚠️ Con il `SET role` chi si collega e chi lavora sono due utenti diversi anche fuori
da una funzione `SECURITY DEFINER`. Il codice che deve capire «sto dentro una
DEFINER?» confronta l'utente corrente con il **ruolo di sessione** (il parametro
`role`), non con l'utente collegato; e `pg_stat_activity` mostra l'orario delle
sessioni altrui solo a chi ha `pg_read_all_stats`, che `zeroerp_owner` ha.

⚠️ La RLS è attiva in modalità `ENABLE`, **non** `FORCE`: proprietario e superuser ne
sono esenti per natura PostgreSQL. È per questo che `zeroerp_owner` e `postgres` non
vanno mai usati come utenza del backend.

I processi automatici che toccano i dati di un'azienda (fatturazione, code di
lavoro, stampa, email) girano **come `zeroerp_app`**, con l'identità di un **utente
tecnico per (processo × azienda)**, dentro il perimetro RLS di quell'azienda. Non
esistono canali di sistema che scavalcano la RLS. Il modello sta nella guida
[Processi automatici](/guide/processi-automatici-classe-e-identita).

### Nessun ruolo che scavalca la RLS

⛔ Un processo che ha bisogno di vedere i dati di più aziende **non** riceve un ruolo
`BYPASSRLS`: riceve un utente tecnico per ogni azienda. Il controllo
[vw_processi_che_bypassano](/dbzero/dbops/manual/vw_processi_che_bypassano) legge i
ruoli in diretta e deve restare vuoto.

Per togliere dal server un ruolo che non serve più c'è
`scripts/ritira_ruoli_dismessi.sh`, da superuser. Un ruolo ha privilegi in **ogni**
database del server, e `DROP OWNED` lavora solo su quello a cui si è collegati:
lo script li gira tutti, si ferma se il ruolo possiede ancora qualcosa, e senza
`--esegui` fa una prova a vuoto.

```bash
PGPASSWORD=… scripts/ritira_ruoli_dismessi.sh <ruolo>
PGPASSWORD=… scripts/ritira_ruoli_dismessi.sh --esegui <ruolo>
```

## `provision_zeroerp.sql` — cosa fa

Da superuser, idempotente, in **tre fasi** scelte con `-v fase=…`:

| Fase | Quando | Che cosa |
| --- | --- | --- |
| `ruoli` | prima di tutto, sul database `postgres` | crea `zeroerp_owner`, `zeroerp_job`, `zeroerp_app` e `zeroerp_log` se mancano (con la password passata); se un ruolo esiste con attributi diversi dal modello **si ferma** e lo nomina, non lo corregge; scrive il commento dei ruoli; con `-v db_name=…` crea il database, o gliene passa la proprietà, e dà `CONNECT` a job, app e log; dà a `zeroerp_owner` `pg_read_all_stats` |
| `pre` | dopo il provision-pre di Liquibase | passa a `zeroerp_owner` schemi, tabelle e funzioni che il superuser ha creato (le tabelle di Liquibase, lo schema `internal`); dà a owner e job i diritti su `pgagent` |
| `post` | alla fine: dopo Liquibase, `ci_apply`, `manage.py migrate` | `EXECUTE` di `zeroerp_job` sulle procedure dei job; ripassa la proprietà; **verifica «un owner solo»** e, se un oggetto del progetto non è di `zeroerp_owner` fuori dal registro, **si ferma** nominandolo |

Restano fuori, per struttura: gli schemi di sistema, gli oggetti di un'estensione,
gli schemi che **ospitano** un'estensione (`pgagent`, `topology`).

```bash
# fase ruoli: sul database postgres
psql "host=<DB_HOST> port=5432 dbname=postgres user=<ADMIN_DB_USER>" \
  -v fase=ruoli -v db_name=zeroerp \
  -v owner_password='<…>' -v job_password='<…>' -v app_password='<…>' \
  -v log_password='<…>' \
  -f scripts/sql/provision_zeroerp.sql

# fasi pre e post: sul database del progetto
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v fase=post -f scripts/sql/provision_zeroerp.sql
```

L'ordine completo, passo per passo, è quello di `.github/workflows/ci-validate.yaml`
e di `scripts/ci-local.sh`. La postura di `zeroerp_app` la dà la fase `post` (sotto);
il canale di log resta a `provision_dblink_log_channel.sql`, che dipende dall'ambiente.

## La postura di zeroerp_app

È la fase `post` di `provision_zeroerp.sql`.

È **idempotente** e si rilancia senza danni. È anche l'**ultima parola** sulla
postura di `zeroerp_app`: in CI (`ci-validate.yaml`) e in `scripts/ci-local.sh`
gira **dopo** Liquibase **e dopo** `manage.py migrate`, perché le tabelle dello
schema `django` nascono con il secondo.

1. Pretende che `zeroerp_app` esista: lo crea la fase `ruoli`, e la sua password
   non si tocca mai (i ruoli sono di cluster).
2. `CONNECT` e `TEMP` sul database.
3. `search_path = django,public,config,dbops,script,anagrafiche` sul ruolo (lo
   stesso di `settings.py`).
4. Sugli schemi della **whitelist applicativa** — una sola tabella temporanea in
   testa allo script, `_app_schemas`: `USAGE`, DML su tutte le tabelle,
   sequenze, `EXECUTE` su tutte le funzioni, e le `ALTER DEFAULT PRIVILEGES` del
   migratore, così gli oggetti creati dopo ereditano gli stessi privilegi. Gli
   schemi che non esistono nel database corrente vengono saltati.
   * `django` **è** nella whitelist: sedici funzioni `SECURITY INVOKER` leggono e
     scrivono `django.auth_user` con il ruolo applicativo.
   * `maintenance` **non** c'è: l'app ne riceve solo `USAGE` e il `SELECT` sul
     giornale dei job; scrive attraverso `script.fn_job_run_start/end`.
5. **Ritira** ciò che il grant largo del punto 4 ha dato ma il modello nega. Sono
   le «porte»: tabelle che l'app legge ma scrive solo attraverso una funzione
   `SECURITY DEFINER` del proprietario, e funzioni riservate a quei verbi.
   Rientrano qui i registri append-only (`dbops.audit_log`, `dbops.error_log`),
   lo schema `storico` senza `DELETE`, il ledger di magazzino, lo stato delle
   credenziali, il pannello di configurazione, il registro degli owner.
   L'elenco vivo è nei commenti dello script, uno per porta, ognuno con il suo
   brief e il suo pgTAP.

⚠️ Ogni elenco di porte è scritto in **tre sedi** che devono coincidere: questo
script, il loop di `90_end/ci_apply/20260205-41` e il changeSet forward della
porta. Chi ne cambia una cambia le altre; i pgTAP di postura (per esempio
`db/pgtap/dbops/test-registri-append-only-postura-v1.sql`,
`db/pgtap/dbops/test-app-postura-schema-django-v1.sql`) lo segnalano se non lo
fa.

## Esecuzione

La postura di `zeroerp_app` si rilancia con la fase `post`, da un utente
amministrativo e dopo ogni migrazione che crea uno schema o una tabella:

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v fase=post -f scripts/sql/provision_zeroerp.sql
```

Canale di log `dblink`, una volta per database:

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -f scripts/sql/provision_dblink_log_channel.sql
```

Il ruolo `zeroerp_log` lo crea la fase `ruoli`, prima delle migrazioni: questo
script gli dà i diritti su `dbops.error_log` e imposta i parametri del canale, e si
ferma se il ruolo manca. `log_service` (default `zeroerp_log`) è il nome del
*service*.

La password non va nelle GUC: lo script imposta solo il nome del *service*.
Password e host stanno in `pg_service.conf`/`.pgpass`, come indica lo script alla
fine.

⚠️ Il canale si imposta per il migratore, per `zeroerp_app` **e per `zeroerp_job`**.
Il verbale di un job fallito (`maintenance.fn_job_run_log_failure`) legge il
parametro della **sessione**, cioè del ruolo che si è collegato: sotto pgAgent è
`zeroerp_job`, anche se la procedura del job gira come il proprietario. Senza, un
job fallito emette un avviso e non lascia il verbale. Un database che imposta il
parametro per tutti (`ALTER DATABASE … SET`) è già coperto.

### Il ruolo di ogni corsa, e il presidio

Ogni corsa del giornale dei job (`maintenance.job_run_log`) registra in
`ruolo_sessione` il ruolo che si è collegato (`session_user`): pgAgent, il
migratore in `ci_apply`, una persona. Il presidio
`maintenance.vw_job_run_da_superuser` deve restare vuoto: nomina i processi la
cui ultima corsa è stata fatta da un **superuser**. Basta guardare il superuser
perché le procedure dei job le possono chiamare solo il proprietario,
`zeroerp_job` e un superuser; si giudica dall'attributo `rolsuper`, mai dal nome.

### Scope congelato delle shadow di `storico`

`scripts/sql/provision_storico_scope.sql`, da superuser, **una volta per
database**. ⚠️ Serve dove i job hanno girato come `postgres` (lo sviluppo, finché
non si allinea al modello): con le procedure dei job `DEFINER` del proprietario
le shadow nascono già sue. Riassegna al migratore la proprietà delle tabelle
`storico.*` create dal job pgAgent come `postgres`, aggiunge le colonne dello scope, accende la RLS
dove la tabella madre è protetta, rifà il backfill e revoca il `DELETE`
all'applicazione. Finché non passa, il changeSet `20260911-28` (trigger di
storico) si ferma su una `preCondition`: è voluto.

```bash
sudo -u postgres psql -X -d zeroerp \
     -f scripts/sql/provision_storico_scope.sql
```

Regola e motivazione: guida [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle),
sezione «Di chi è una versione».

## Verifiche

### Privilegi

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -f scripts/sql/check_db_role_access.sql
```

Lo script scorre tutti gli schemi non di sistema e non ha una lista scritta a
mano: mostra cosa il ruolo vede e cosa no.

### Attributi dei ruoli

```sql
SELECT rolname, rolcanlogin, rolbypassrls, rolsuper
FROM pg_roles
WHERE rolname LIKE 'zeroerp%' OR rolname = 'postgres'
ORDER BY 1;

-- chi possiede il database e gli oggetti (atteso col modello: zeroerp_owner,
-- più le funzioni del registro dbops.sec_functions_owner di un superuser)
SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database();

SELECT * FROM dbops.vw_processi_che_bypassano;   -- atteso: nessuna riga
```

Atteso: `zeroerp_owner`, `zeroerp_job`, `zeroerp_app` e `zeroerp_log` hanno
`rolcanlogin = true`, `rolbypassrls = false` e `rolsuper = false`. La verifica
completa del proprietario la fa la fase `post` di `provision_zeroerp.sql`.

Se `zeroerp_app` risulta `BYPASSRLS`:

```sql
ALTER ROLE zeroerp_app NOBYPASSRLS;
```

### RLS

Il perimetro RLS cresce con il modello: non si verifica contro una lista scritta
qui, che sarebbe vecchia al primo changeSet. Si legge dal catalogo:

```sql
SELECT n.nspname AS schema_name, c.relname AS table_name,
       c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p') AND c.relrowsecurity
ORDER BY 1, 2;
```

Atteso: `rls_forced = false` su tutte (modalità `ENABLE`).

Quali tabelle **devono** essere protette non si decide da questa query: lo
presidiano i pgTAP in `db/pgtap/rls/` (struttura delle policy, perimetro dei
satelliti, `test-rls-perimetro-scoperto.sql`).

## Configurazione Django

In `backend/env.sh` **e** `backend/.env.systemd` (su una variabile presente in
tutti e due vince `env.sh`: vedi [Configurazione Django](configurazione-django.md)):

```bash
DB_NAME=zeroerp
DB_USER=zeroerp_app
DB_PASSWORD=<PASSWORD_FOR_ZEROERP_APP>
DB_HOST=<DB_HOST>
DB_PORT=5432
```

Poi `sudo systemctl restart zeroerp-gunicorn`.

## Note operative

* Uno **schema applicativo nuovo** si aggiunge a `_app_schemas` in
  `provision_zeroerp.sql` (fase post), e lo script si rilancia.
* Una **tabella che l'app legge ma non deve scrivere direttamente** è una porta
  nuova: va nelle tre sedi (sopra), con il suo pgTAP.
* Una **query di diagnosi a mano** su una tabella con RLS, senza GUC, restituisce
  **zero righe**, e sembra un dato. Per leggere come un operatore si impostano le
  GUC (`SET app.current_user_id = …`, eccetera) come fa il backend; lo spiega il
  [Contratto GUC APP](/guide/contratto-guc-app).
* ⛔ Non si usa il migratore o `postgres` come utenza del backend per «aggirare»
  un filtro: vorrebbe dire uscire dal perimetro di sicurezza.
* Una **procedura di job nuova** (`maintenance.proc_*_job`) nasce `SECURITY DEFINER`
  con `search_path` fissato (`pg_catalog` per primo) e con `REVOKE EXECUTE … FROM
  PUBLIC`; l'`EXECUTE` a `zeroerp_job` lo dà la fase `post`. Il presidio la trova da
  solo, per nome.
