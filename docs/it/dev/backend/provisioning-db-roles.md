# Provisioning ruoli DB (runtime, migratore, RLS)

> **Ultimo aggiornamento**: 26 settembre 2026
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

## Ruoli

| Ruolo | Chi lo usa | Attributi attesi | Provisioning |
| --- | --- | --- | --- |
| `zeroerp_app` | il backend Django (`DB_USER`): web, management command, timer | `LOGIN`, **`NOBYPASSRLS`**, non owner delle tabelle | `scripts/sql/provision_db_roles.sql` |
| migratore (`titodb` su dev, `zeroerp` in CI) | Liquibase; **owner** degli oggetti applicativi | `LOGIN`, non superuser | fuori dagli script: è il ruolo con cui si crea il database |
| `zeroerp_log` | il canale di log via `dblink` (scrive `dbops.error_log` fuori dalla transazione che fallisce) | `LOGIN`, solo `INSERT` su `dbops.error_log` | `scripts/sql/provision_dblink_log_channel.sql` — vedi [dblink](/postgresql/dblink) |
| `postgres` | provisioning, manutenzione, pgAgent | superuser | — |

Note:

* La RLS è attiva in modalità `ENABLE`, **non** `FORCE`: owner e superuser ne
  sono esenti per natura PostgreSQL. È per questo che il migratore e `postgres`
  non vanno mai usati come utenza del backend.
* I processi automatici (fatturazione, code di lavoro, stampa, email) girano
  **come `zeroerp_app`**, con l'identità di un **utente tecnico per (processo ×
  azienda)**, dentro il perimetro RLS di quell'azienda. Non esistono più canali
  di sistema che scavalcano la RLS. Il modello sta nella guida
  [Processi automatici](/guide/processi-automatici-classe-e-identita).

### ⚠️ `zeroerp_batch_fatturazione` — in ritiro

Era il ruolo `BYPASSRLS` con cui il batch notturno vedeva tutte le aziende,
quando i processi non avevano un'identità propria.

* **Il backend non lo usa più** dal 2026-09-05: l'alias `system_fatturazione`
  in `settings.py` è stato tolto, e il test
  `apps/core/tests/test_system_context_usage_whitelist.py` impedisce che un
  canale `BYPASSRLS` ritorni.
* **Il ruolo esiste ancora nel database** finché non si lancia il ritiro. Lo
  dichiara `dbops.vw_processi_che_bypassano`, che legge `pg_roles` in diretta:
  una riga = un bypass ancora vivo.
  ([vw_processi_che_bypassano](/dbzero/dbops/manual/vw_processi_che_bypassano))
* Il ritiro è `scripts/sql/retire_db_role_batch_fatturazione.sql`, da
  superuser, perché il `DROP ROLE` di un ruolo `BYPASSRLS` lo richiede:

  ```bash
  psql -h <DB_HOST> -U postgres -d zeroerp \
       -v batch_role=zeroerp_batch_fatturazione \
       -f scripts/sql/retire_db_role_batch_fatturazione.sql
  ```

  Chiuso quando `SELECT * FROM dbops.vw_processi_che_bypassano;` non restituisce
  righe.
* ⚠️ Finché il ritiro non è fatto, restano vivi anche i pezzi che lo creano:
  `scripts/sql/provision_db_role_batch_fatturazione.sql`,
  `check_db_role_batch_fatturazione.sql`, lo step «Provision ruolo batch
  fatturazione» di `.github/workflows/ci-validate.yaml` e il pgTAP
  `db/pgtap/rls/test-role-batch-fatturazione-postura.sql`. Vanno via **insieme**
  al ruolo, non prima.
* ⛔ Un processo nuovo **non** riceve un ruolo `BYPASSRLS`: riceve un utente
  tecnico.

## `provision_db_roles.sql` — cosa fa

È **idempotente** e si rilancia senza danni. È anche l'**ultima parola** sulla
postura di `zeroerp_app`: in CI (`ci-validate.yaml`) e in `scripts/ci-local.sh`
gira **dopo** Liquibase **e dopo** `manage.py migrate`, perché le tabelle dello
schema `django` nascono con il secondo.

1. Crea `zeroerp_app` se manca e ne **aggiorna sempre la password**.
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

Da un host che raggiunge PostgreSQL, con un utente amministrativo:

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -v app_password='<PASSWORD_FOR_ZEROERP_APP>' \
  -v migrator_role=titodb \
  -f scripts/sql/provision_db_roles.sql
```

`migrator_role` ha default `titodb`, e `db_name` ha default il database
corrente.

Canale di log `dblink`, una volta per database:

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v log_password='<PASSWORD_FOR_ZEROERP_LOG>' \
  -f scripts/sql/provision_dblink_log_channel.sql
```

La password non va nelle GUC: lo script imposta solo il nome del *service*.
Password e host stanno in `pg_service.conf`/`.pgpass`, come indica lo script alla
fine.

### Scope congelato delle shadow di `storico`

`scripts/sql/provision_storico_scope.sql`, da superuser, **una volta per
database**. Riassegna al migratore la proprietà delle tabelle `storico.*` create
dal job pgAgent come `postgres`, aggiunge le colonne dello scope, accende la RLS
dove la tabella madre è protetta, rifà il backfill e revoca il `DELETE`
all'applicazione. Finché non passa, il changeSet `20260911-28` (trigger di
storico) si ferma su una `preCondition`: è voluto.

```bash
sudo -u postgres psql -X -d zeroerp -v migrator_role=titodb \
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
WHERE rolname LIKE 'zeroerp%' OR rolname IN ('titodb', 'postgres')
ORDER BY 1;

SELECT * FROM dbops.vw_processi_che_bypassano;   -- atteso: nessuna riga
```

Atteso: `zeroerp_app` e `zeroerp_log` hanno `rolcanlogin = true` e
`rolbypassrls = false`.

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
  `provision_db_roles.sql`, e lo script si rilancia.
* Una **tabella che l'app legge ma non deve scrivere direttamente** è una porta
  nuova: va nelle tre sedi (sopra), con il suo pgTAP.
* Una **query di diagnosi a mano** su una tabella con RLS, senza GUC, restituisce
  **zero righe**, e sembra un dato. Per leggere come un operatore si impostano le
  GUC (`SET app.current_user_id = …`, eccetera) come fa il backend; lo spiega il
  [Contratto GUC APP](/guide/contratto-guc-app).
* ⛔ Non si usa il migratore o `postgres` come utenza del backend per «aggirare»
  un filtro: vorrebbe dire uscire dal perimetro di sicurezza.
