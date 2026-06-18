# Provisioning ruoli DB (runtime + migrator + RLS)

## Scopo
Definire un processo unico e ripetibile per configurare i ruoli PostgreSQL di
ZeroErp in dev/stage/prod senza dipendere da utenti personali, allineato
all'architettura attuale di permessi, multi-face auth e Row Level Security.

## Contesto architetturale
Questo documento va letto insieme a:

- [architettura-permessi-e-autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
- [architettura-multi-face-auth](/guide/architettura-multi-face-auth)
- [contratto-guc-app](/guide/contratto-guc-app)

Punti fermi:

- `zeroerp_app` e` un **ruolo tecnico PostgreSQL**, non un utente Django
  `auth_user`.
- L'identita` applicativa arriva al DB tramite GUC di sessione settate dal
  backend (`JwtAuditAuthentication`), non tramite login DB dedicati per utente.
- La RLS attiva per gli **OPERATORI** usa queste GUC per filtrare i dati; quindi
  il ruolo runtime deve essere soggetto alle policy.

## Stato attuale RLS
Stato allineato alle attivita` RLS attive al **2026-06-04**:

- branch **OPERATORE / scope emittente fiscale**: **attiva** (`ENABLE`, no
  `FORCE`) su `vendite.fatture`, `vendite.fatture_scadenze`,
  `vendite.fatturazione_lotti`, `vendite.ordini`, `vendite.preventivi`,
  `vendite.contratti`, `vendite.offerte_commerciali`,
  `documenti.documenti_generati`, `pratiche.pratiche`,
  `anagrafiche.billing_account`;
- branch **CLIENTE_PORTALE / FORNITORE_PORTALE / SHOP_CUSTOMER**: architettura e
  policy presenti, ma attivazione runtime ancora differita per le API di
  dominio relative.

## Ruoli standard

### `zeroerp_app`
Ruolo runtime usato da Django (`DB_USER`).

Responsabilita':

- esegue query e DML applicativi;
- legge i GUC di sessione valorizzati dal backend;
- e` il ruolo che deve vedere applicate le policy RLS.

Requisiti:

- deve essere `LOGIN`;
- deve essere **non owner** delle tabelle dati applicative;
- deve essere **`NOBYPASSRLS`**;
- non deve essere usato per migrazioni Liquibase.

### `titodb`
Ruolo tecnico di migrazione/deploy usato da Liquibase.

Responsabilita':

- crea/aggiorna oggetti DB;
- riceve le `ALTER DEFAULT PRIVILEGES` cosi` gli oggetti futuri concedono subito
  i grant runtime a `zeroerp_app`.

Note:

- nelle attivazioni RLS correnti ZeroErp usa `ENABLE` e non `FORCE`, quindi
  owner e superuser restano esenti per natura PostgreSQL;
- `titodb` va trattato come ruolo di migrazione/owner, non come utente runtime.

### `postgres` o ruolo batch equivalente
Ruolo esente usato per attivita` di manutenzione o batch DB puri quando serve
operare fuori dal perimetro RLS applicativo.

Uso tipico:

- pgAgent;
- job SQL pianificati;
- manutenzione/amministrazione DB.

Non deve essere configurato come `DB_USER` del backend.

### Ruoli batch per-job `zeroerp_batch_<job>` (canale di sistema headless)

I processi headless applicativi (management command, cron, job) che operano su
tabelle protette da RLS **senza** un'identita' operatore usano un ruolo dedicato
**per singolo job** — non `zeroerp_app`, non `postgres`/`titodb`.

Modello (vedi
`dev/work-done/brief-db-contesto-sistema-batch-fatturazione-rls.md`):

- `BYPASSRLS` — bypassa l'isolamento per-emittente (semantica corretta per un
  processo di sistema che opera su **tutti** gli emittenti); trigger e constraint
  di business restano comunque attivi;
- `LOGIN`, `NOSUPERUSER NOCREATEDB NOCREATEROLE`;
- **SELECT + EXECUTE ampi** sugli schemi applicativi (letture cross-tenant a basso
  rischio; enumerare i lookup sarebbe fragile);
- **DML (INSERT/UPDATE/DELETE) SOLO sul perimetro di scrittura del job**: il vettore
  di danno di un ruolo `BYPASSRLS` e' la scrittura cross-tenant → va limitata. Una
  tabella fuori perimetro fallisce **rumorosamente** (`permission denied`), non in
  silenzio;
- **NO membership di `zeroerp_app`** (darebbe read+write su tutto): grant espliciti;
- usato via un **alias Django dedicato** (`DATABASES['system_<job>']`), **mai** come
  `DB_USER` del web.

> **Regola per-job**: un nuovo processo di sistema → **nuovo ruolo scoped**
> (`zeroerp_batch_<job>`), mai allargare i grant di un ruolo esistente. Alla comparsa
> del 2° job rivalutare "per-job vs ruolo condiviso-ma-scoped".

Ruolo esistente: **`zeroerp_batch_fatturazione`** (batch di fatturazione).

- Provisioning (admin DB): `scripts/sql/provision_db_role_batch_fatturazione.sql`
- Verifica postura: `scripts/sql/check_db_role_batch_fatturazione.sql`
- CI: step psql-as-`postgres` in `.github/workflows/ci.yaml` ("Provision ruolo batch
  fatturazione") che riusa lo stesso script
- pgTAP: `db/pgtap/rls/test-role-batch-fatturazione-postura.sql`

> **`BYPASSRLS` richiede superuser.** Il provisioning di questi ruoli (creazione +
> attributo `BYPASSRLS`) va eseguito **come superuser** (`postgres`): lo script admin e
> lo step CI girano come `postgres`. **Non** metterlo in un changeset Liquibase del flusso
> ordinario: lì la connessione e' `zeroerp_app`/`titodb` (non-superuser) e l'`ALTER ROLE
> ... BYPASSRLS` fallisce. I soli GRANT (senza attributi di ruolo) sarebbero invece
> eseguibili dall'owner degli oggetti.

## Come runtime e identita' si incontrano
Il backend apre la connessione come `zeroerp_app`, poi `JwtAuditAuthentication`
popola i GUC che rappresentano la veste applicativa della richiesta:

- `app.current_user_id`
- `app.current_identita_id`
- `app.ruolo_applicativo`
- `app.soggetto_ruolo_id`

Questa separazione e` fondamentale:

- il **ruolo DB** dice *con quale utenza tecnica il backend parla a PostgreSQL*;
- i **GUC** dicono *per conto di quale identita` applicativa sta operando quella
  richiesta*;
- le **policy RLS** filtrano sulle righe usando i GUC, non il nome del ruolo DB.

Conseguenza pratica: cambiare `DB_USER` da `zeroerp_app` a un ruolo owner o
`BYPASSRLS` neutralizza la RLS e rompe il modello di sicurezza.

## Script disponibili

- Provisioning idempotente: `scripts/sql/provision_db_roles.sql`
- Verifica grant runtime: `scripts/sql/check_db_role_access.sql`

Lo script di provisioning:

- crea il ruolo runtime se manca;
- aggiorna sempre la password del ruolo runtime;
- concede `CONNECT` e `TEMP` sul database;
- imposta `search_path = django,public,config,dbops,script,anagrafiche`;
- concede `USAGE`/DML/sequenze/funzioni sugli schemi applicativi whitelisted;
- imposta le `ALTER DEFAULT PRIVILEGES` per il ruolo migrator.

Gli schemi runtime sono centralizzati nello script. Oggi includono anche
`documenti`, `pratiche` e `ui`; `django` e `maintenance` sono volutamente fuori
dalla whitelist applicativa generale.

## Esecuzione provisioning (admin DB)
Eseguire da host che raggiunge PostgreSQL con un utente amministrativo.

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -v app_password='<PASSWORD_FOR_ZEROERP_APP>' \
  -v migrator_role=titodb \
  -f scripts/sql/provision_db_roles.sql
```

## Verifica grant runtime
Controllo rapido dei grant oggetto/schema:

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -f scripts/sql/check_db_role_access.sql
```

## Verifica postura RLS
`check_db_role_access.sql` verifica i grant, ma **non** basta per validare il
comportamento RLS. Controllare anche:

```sql
SELECT rolname, rolcanlogin, rolbypassrls
FROM pg_roles
WHERE rolname IN ('zeroerp_app', 'titodb', 'postgres', 'zeroerp_batch_fatturazione');
```

Atteso:

- `zeroerp_app`: `rolcanlogin = true`, `rolbypassrls = false`
- `titodb`: ruolo tecnico di migrazione
- `postgres`: superuser / ruolo esente
- `zeroerp_batch_fatturazione`: `rolcanlogin = true`, `rolbypassrls = **true**` (ruolo
  batch per-job; postura completa via `scripts/sql/check_db_role_batch_fatturazione.sql`)

Controllare inoltre che la RLS sia davvero attiva sulle tabelle del lotto:

```sql
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (n.nspname, c.relname) IN (
  ('vendite', 'fatture'),
  ('vendite', 'fatture_scadenze'),
  ('vendite', 'fatturazione_lotti'),
  ('vendite', 'ordini'),
  ('vendite', 'preventivi'),
  ('vendite', 'contratti'),
  ('vendite', 'offerte_commerciali'),
  ('documenti', 'documenti_generati'),
  ('pratiche', 'pratiche'),
  ('anagrafiche', 'billing_account')
)
ORDER BY 1, 2;
```

Atteso sullo stato corrente:

- `rls_enabled = true`
- `rls_forced = false`

Se l'ambiente e` fuori allineamento e `zeroerp_app` risulta `BYPASSRLS`,
correggere esplicitamente:

```sql
ALTER ROLE zeroerp_app NOBYPASSRLS;
```

## Configurazione Django
In `backend/env.sh` e `backend/.env.systemd` usare:

```bash
DB_NAME=zeroerp
DB_USER=zeroerp_app
DB_PASSWORD=<PASSWORD_FOR_ZEROERP_APP>
DB_HOST=<DB_HOST>
DB_PORT=5432
```

Dopo modifiche variabili:

```bash
sudo systemctl restart zeroerp-gunicorn
```

## Note operative

- Le `ALTER DEFAULT PRIVILEGES` vengono applicate per il ruolo migrator
  (`titodb`) cosi` gli oggetti futuri ereditano i grant runtime.
- Se nasce un nuovo schema applicativo, aggiornare la whitelist in
  `scripts/sql/provision_db_roles.sql`.
- I path HTTP autenticati devono passare da `JwtAuditAuthentication` e dal reset
  simmetrico dei GUC; senza GUC coerenti, le policy RLS operano fail-closed.
- CLI Django, management command e cron applicativi non passano automaticamente
  dal flusso JWT: se leggono tabelle protette da RLS con `zeroerp_app`, possono
  vedere zero righe o subire deny impliciti. In questi casi:
  - o si impostano i GUC in modo esplicito e coerente;
  - oppure si sposta l'operazione su job DB/batch esente governato a livello SQL.
- Non usare `titodb` o `postgres` come utenza del backend per "aggirare" filtri:
  significherebbe bypassare il perimetro di sicurezza atteso.
