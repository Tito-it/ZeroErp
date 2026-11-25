# Installazione

> **Ultimo aggiornamento**: 25 novembre 2026

Questa pagina dice **in che ordine** si tira su ZeroErp su una macchina nuova e
rimanda alle pagine che spiegano ogni passo. Ciò che si configura **dentro** il
programma (azienda, operatori, posta, timer) sta in
[Configurazione iniziale](configurazione-iniziale.md).

La procedura qui sotto è quella con l'**ambiente virtuale Python** (venv), che
è il setup di oggi. Un'installazione con Docker non c'è ancora: se e come farla
è una decisione aperta ([promemoria](dev/work-in-progress/promemoria-installazione-md.md)).
La parte del database non dipende da quella scelta.

Questa pagina vale per una macchina qualsiasi. I comandi passo per passo del
server di riferimento (container Proxmox, Tailscale, UFW, certificato
self-signed) stanno nel
[play-book operativo](dev/backend/play-book-operativo-backend.md): sono
**l'infrastruttura di quella macchina**, non requisiti di ZeroErp.

L'ordine:

1. prerequisiti, codice, ambiente Python e Liquibase;
2. le variabili d'ambiente, che servono già al database;
3. il database;
4. il backend, dietro Nginx;
5. il primo amministratore;
6. i processi automatici;
7. il frontend.

## Prerequisiti

- Python, alla versione di `.python-version`, con le dipendenze del backend
  (`backend/requirements.txt`, Django compreso)
- PostgreSQL 18, con le estensioni del paragrafo «Il database»
- Java 17 e Liquibase Community con il driver JDBC di PostgreSQL: le versioni sono
  fissate in `scripts/liquibase-versioni.env` e li installa
  `scripts/installa-liquibase.sh` (paragrafo «Liquibase» qui sotto). `tools/` non è
  nel repository: ogni macchina lo popola con lo script
- Node.js, per il frontend (Vue 3 + Vite), alla versione di `engines.node` in
  `frontend/package.json`
- Redis, la cache del backend (in alternativa, solo per una prova, `CACHE_BACKEND=locmem`)
- Nginx, l'unico ingresso: davanti al backend e, in sviluppo, anche davanti a Vite
- systemd, per il backend e per i processi automatici
- Le **librerie di sistema di WeasyPrint**, che stampa i PDF: senza, l'import di WeasyPrint fallisce
  e non esce nessuna stampa. L'elenco dei pacchetti è uno solo, nel `Dockerfile` (il blocco
  `apt-get install` delle librerie native, fra cui `libharfbuzz-subset0`), e sulle macchine di
  sviluppo si installano gli stessi con `apt install`

Versioni consigliate: [Versioni supportate](versioni-supportate.md).

## Il codice e l'ambiente Python

```bash
git clone git@github.com:Tito-it/ZeroErp.git
cd ZeroErp
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

⚠️ Il `requirements.txt` in radice contiene solo gli strumenti di sviluppo e della
documentazione (pre-commit, Zensical): **non** installa Django.

## Liquibase

```bash
scripts/installa-liquibase.sh
```

Scarica Liquibase e il driver JDBC nelle versioni di `scripts/liquibase-versioni.env`
dalle sorgenti ufficiali ([release di Liquibase](https://github.com/liquibase/liquibase/releases),
Maven Central per il driver), ne verifica lo SHA-256 e li mette in `tools/liquibase/`.
Si può rilanciare: ciò che c'è già nella versione giusta non si riscarica. Da lì in
poi Liquibase si lancia **solo** dal wrapper `scripts/liquibase5.sh`, che aggancia il
driver della versione fissata; nel `PATH` non serve nessun `liquibase`. La CI legge
le stesse versioni dallo stesso file.

## Le variabili d'ambiente

Si fanno **prima del database**, perché il passo 7 (`manage.py migrate`) le legge.

```bash
cd backend
cp .env.example env.sh && chmod 600 env.sh
# si valorizza env.sh, poi lo stesso elenco senza «export» per systemd:
sed 's/^export //' env.sh > .env.systemd && chmod 600 .env.systemd
cd ..
```

Le obbligatorie sono `DJANGO_SECRET_KEY`, `DJANGO_FIELD_ENCRYPTION_KEYS`,
`DB_NAME`, `DB_USER` (sempre `zeroerp_app`), `DB_PASSWORD`,
`DJANGO_TRUSTED_PROXY_COUNT` e `FRONTEND_URL`. Poi `DB_HOST` e
`DJANGO_ALLOWED_HOSTS`, che servono appena il database o il browser non sono
sulla stessa macchina. Che cosa decide ognuna, come si generano le chiavi e
quale dei tre file vince su quale (`env.sh`, `.env.systemd`, `.env`) è spiegato
in [Configurazione Django](dev/backend/configurazione-django.md), «Variabili
d'ambiente»: l'elenco vale lì e non si ricopia qui.

⛔ Nessuno di questi file si committa: li tengono fuori `.gitignore` e gitleaks.

⚠️ Due variabili sbagliate **non danno errore**. Con `DJANGO_TRUSTED_PROXY_COUNT`
il backend si fida dell'indirizzo sbagliato, e con `FRONTEND_URL` le email
mandano link rotti.

## Il database

### I ruoli: nomi fissi, uguali ovunque

Il database ha **ruoli di sistema** con nomi che non si cambiano: il database li
nomina nei suoi permessi e nei suoi controlli. Chi installa può aggiungere un suo
utente come **membro** di un ruolo di sistema, ma non rinominarli.

| Ruolo | Chi lo usa |
| --- | --- |
| `zeroerp_owner` | proprietario di tutto; con lui girano Liquibase e `manage.py migrate` |
| `zeroerp_job` | il programmatore dei lavori notturni (pgAgent): può solo avviare i lavori previsti |
| `zeroerp_app` | il backend: vede solo i dati del perimetro dell'utente collegato |
| `zeroerp_log` | il canale che scrive i registri degli errori fuori dalla transazione che fallisce |
| `postgres` | solo l'installazione: crea ruoli, database ed estensioni, poi non lavora più |

Il perché di ogni ruolo e le regole stanno in
[Provisioning ruoli DB](dev/backend/provisioning-db-roles.md).

⛔ Le **password** non hanno valori predefiniti: si scelgono all'installazione e
si passano agli script. Di un ruolo che esiste già, nessuno script cambia la
password: i ruoli valgono per tutto il server PostgreSQL, non per un database solo.

### Le estensioni

Sul server PostgreSQL devono essere installati i pacchetti di: PostGIS (con
`postgis_topology`), `plpgsql_check`, pgAgent, e per i test pgTAP. Le estensioni
del pacchetto base (`dblink`, `pg_trgm`, `pgcrypto`, `btree_gist`, `unaccent`,
`uuid-ossp`) ci sono già.

Nel database le creano tre momenti diversi:

- **il passo 2** (`changelog-provision-pre.yaml`, da superuser): `btree_gist`,
  `dblink`, `pgcrypto`, `postgis`, `postgis_topology`, `unaccent`, `pg_trgm`,
  `plpgsql_check` e `pgagent`. `pgagent` solo se il pacchetto c'è: senza, si
  prosegue e i lavori a orario non esistono;
- **il passo 4** (lo schema, come `zeroerp_owner`): `uuid-ossp`, dalla baseline
  `010-tables-config`. Il proprietario può crearla perché è un'estensione
  *trusted*;
- **la suite dei test**: `pgtap`, che non è di Liquibase. In CI la crea il passo
  dei pgTAP, sullo scratch `scripts/ci-local.sh`.

A che cosa serve ciascuna: [Estensioni utilizzate](postgresql/estensioni-utilizzate.md).

### Il limite dei file aperti del server

Ogni processo di PostgreSQL tiene aperti tanti file quante sono le tabelle e gli
indici che sta usando, più alcuni per la memoria condivisa delle query parallele,
per la compilazione JIT e, in PostgreSQL 18, per l'I/O asincrono (`io_uring`).
Il sistema operativo mette un tetto a quanti file può aprire un processo, e su
Debian il servizio PostgreSQL parte col tetto di sistema: **1024**.

ZeroErp ha centinaia di tabelle e quasi duemila indici, e alcune operazioni lunghe
(la convergenza delle automazioni a ogni aggiornamento, le suite pgTAP) li
toccano quasi tutti nella stessa sessione. Con 1024 il processo arriva al tetto e
l'operazione si ferma con `Troppi file aperti` (`Too many open files`), di solito
mentre apre un segmento di memoria condivisa o il JIT. Non è un errore dei dati e
non dipende dai changeSet: è il limite del servizio.

⛔ Su ogni server, sviluppo e produzione, si alza il tetto **prima** del primo
aggiornamento, con un drop-in di systemd:

```bash
sudo mkdir -p /etc/systemd/system/postgresql@18-main.service.d
printf '[Service]\nLimitNOFILE=65536\n' | sudo tee /etc/systemd/system/postgresql@18-main.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart postgresql@18-main
grep 'open files' /proc/$(pgrep -o -f 'bin/postgres -D')/limits   # deve dire 65536
```

`postgresql@18-main` è il nome dell'unità per il cluster `18/main` di Debian; con
un altro cluster cambia il nome. `max_files_per_process` (1000 di default) resta
com'è: è il tetto che PostgreSQL si dà da solo **sotto** quello del sistema, e
serve che il sistema gli lasci spazio sopra. In un container il limite si dà al
container (`--ulimit nofile=65536:65536` o `ulimits` in compose).

### L'ordine dei passi

È lo stesso che la CI ripete da zero a ogni modifica
(`.github/workflows/ci-validate.yaml`), quindi è provato. Ogni passo ha bisogno
di quelli prima.

| # | Passo | Chi | Che cosa fa |
| --- | --- | --- | --- |
| 1 | `provision_zeroerp.sql`, fase `ruoli` | `postgres` | crea i ruoli di sistema e il database, di proprietà di `zeroerp_owner` |
| 2 | Liquibase, `changelog-provision-pre.yaml` | `postgres` | le estensioni e le tabelle di Liquibase |
| 3 | `provision_zeroerp.sql`, fase `pre` | `postgres` | passa a `zeroerp_owner` ciò che il passo 2 ha creato; i diritti su pgAgent |
| 4 | Liquibase, `changelog-master-v2.yaml` | `zeroerp_owner` | lo schema del programma |
| 5 | Liquibase, `changelog-provision-post.yaml` | `postgres` | le poche funzioni che devono essere di un superuser |
| 6 | Liquibase, contesto `ci_apply` | `zeroerp_owner` | le automazioni: storico, registri, trigger generati |
| 7 | `manage.py migrate`, in quattro tempi | `zeroerp_owner` | le tabelle di Django |
| 8 | `provision_zeroerp.sql`, fase `post` | `postgres` | i diritti di `zeroerp_app` e di `zeroerp_job`, l'**ambiente** dell'installazione (sviluppo o produzione), e la verifica che il proprietario sia uno solo |
| 9 | `provision_dblink_log_channel.sql` | `postgres` | il canale dei registri degli errori |
| 10 | pgAgent come `zeroerp_job` | sistema | il demone dei lavori notturni |

I comandi:

```bash
# 1. ruoli e database (sul database «postgres»)
psql -h <DB_HOST> -U postgres -d postgres \
  -v fase=ruoli -v db_name=zeroerp \
  -v owner_password='…' -v job_password='…' -v app_password='…' -v log_password='…' \
  -f scripts/sql/provision_zeroerp.sql

# 2. il primo passo di Liquibase, da superuser
scripts/liquibase5.sh --url=jdbc:postgresql://<DB_HOST>:5432/zeroerp \
  --username=postgres --password='…' \
  --changeLogFile=db/changelog/changelog-provision-pre.yaml update --contexts=provision

# 3. proprietà e pgAgent
psql -h <DB_HOST> -U postgres -d zeroerp -v fase=pre -f scripts/sql/provision_zeroerp.sql

# 4. lo schema, come zeroerp_owner
scripts/liquibase5.sh --url=jdbc:postgresql://<DB_HOST>:5432/zeroerp \
  --username=zeroerp_owner --password='…' \
  --changeLogFile=db/changelog/changelog-master-v2.yaml \
  update --contexts="!provision and !dati_macchina"

# 5. le funzioni da superuser
scripts/liquibase5.sh --url=jdbc:postgresql://<DB_HOST>:5432/zeroerp \
  --username=postgres --password='…' \
  --changeLogFile=db/changelog/changelog-provision-post.yaml update --contexts=provision

# 6. le automazioni, come zeroerp_owner
scripts/liquibase5.sh --url=jdbc:postgresql://<DB_HOST>:5432/zeroerp \
  --username=zeroerp_owner --password='…' \
  --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts=ci_apply

# 7. le tabelle di Django, con le credenziali di zeroerp_owner
cd backend
set -a; source ./env.sh; set +a
export DB_USER=zeroerp_owner DB_PASSWORD='…'
python manage.py migrate contenttypes --noinput
python manage.py migrate auth --noinput
python manage.py migrate token_blacklist --fake
python manage.py migrate --noinput
cd ..

# 8. i diritti, l'ambiente e la verifica finale
psql -h <DB_HOST> -U postgres -d zeroerp -v fase=post -v ambiente=PRODUZIONE \
  -f scripts/sql/provision_zeroerp.sql

# 9. il canale dei registri degli errori
psql -h <DB_HOST> -U postgres -d zeroerp -f scripts/sql/provision_dblink_log_channel.sql
```

⚠️ **Il passo 4 vuole il filtro dei contesti per intero**,
`"!provision and !dati_macchina"`: con il solo `!provision` girerebbero anche i
dati che appartengono a una macchina precisa
([linee guida SQL](linee-guida-sql.md), «dati di macchina»).

⚠️ **Tutti i ruoli nascono al passo 1, prima delle migrazioni.** Durante il passo
4 alcune migrazioni danno diritti ai ruoli di sistema solo se esistono già: per
esempio a `zeroerp_log` quello di scrivere il giornale dei lavori notturni. Un
ruolo creato dopo resterebbe senza, in silenzio.

⚠️ **Il passo 7 va in quattro tempi**, come in CI: le tabelle di
`token_blacklist` le crea Liquibase, quindi quella migration di Django si segna
come fatta (`--fake`) invece di rifarle.

⚠️ **Il passo 8 si rilancia** dopo ogni migrazione che crea uno schema o una
tabella nuova: i diritti si danno su ciò che esiste in quel momento.

⛔ **L'ambiente si sceglie al passo 8, la prima volta, e non si cambia più.**
`-v ambiente=PRODUZIONE` per un'installazione vera, `-v ambiente=SVILUPPO` per
un server di sviluppo. Nessun valore di default: se manca, il passo 8 si ferma
e chiede di scegliere. Dalla seconda volta il parametro si può omettere; se c'è,
deve dire la stessa cosa. Dall'ambiente dipende quali processi automatici sono
accesi di default (lo smoke notturno, per esempio, gira solo in sviluppo) e se
si possono creare i dati di prova. Una copia della produzione usata per fare
prove resta produzione. Il perché è in
[dbops.installazione](dbzero/dbops/manual/installazione.md).

Il passo 9 imposta solo il nome di un *service*: indirizzo e password del canale
stanno in `pg_service.conf` e `.pgpass` dell'utente di sistema `postgres`
([dblink](postgresql/dblink.md)).

Il passo 10, cioè l'unità systemd e la password di `zeroerp_job`, è descritto in
[pgAgent](postgresql/pgAgent.md). La connessione va su `127.0.0.1` e non sul
socket locale: sul socket PostgreSQL accetta solo l'utente di sistema con lo
stesso nome.

### Un database nato prima dei ruoli di sistema

Se gli oggetti del database appartengono a un utente personale invece che a
`zeroerp_owner`, il database non si ricostruisce: si converte, da superuser e a pgAgent fermo, con
`scripts/sql/converti_db_al_modello_ruoli.sql`. Prima con `-v solo_prova=1`, che
fa tutto e poi annulla. I passi sono in
[Provisioning ruoli DB](dev/backend/provisioning-db-roles.md).

### Come so che è andata bene

* il passo 8 finisce con «un owner solo: verificato», e prima ha scritto
  «ambiente dichiarato» (o «già dichiarato»);
* le verifiche di [Provisioning ruoli DB](dev/backend/provisioning-db-roles.md)
  (privilegi, attributi dei ruoli, RLS);
* il giorno dopo, il pannello dei presidi non segnala lavori notturni eseguiti da
  un amministratore (`maintenance.vw_job_run_da_superuser` vuota).

## Il backend

Prima i file statici, poi il servizio:

```bash
cd backend
./manage-env.sh collectstatic --noinput
```

Il backend gira con Gunicorn, avviato dal wrapper versionato
`backend/bin/start-gunicorn.sh`. Il wrapper ascolta **solo** su `127.0.0.1:8000`
e legge `env.sh`. Lo avvia l'unità systemd `zeroerp-gunicorn`, con un drop-in
che aggiunge `.env.systemd`. L'unità, il vhost di Nginx e le impostazioni di
sicurezza dietro proxy sono in
[Configurazione Django](dev/backend/configurazione-django.md) («Gunicorn con
systemd», «Nginx»). I comandi per crearli sono nel play-book, §8 e §9.

```bash
sudo systemctl enable --now zeroerp-gunicorn
```

Per una prova senza systemd basta `./manage-env.sh run` (runserver su
`127.0.0.1:8000`).

⚠️ Il backend non si ricarica da solo: dopo una modifica al codice Python ci
vuole `kill -HUP` sul processo master. Dopo una modifica a una variabile
d'ambiente ci vuole `sudo systemctl restart zeroerp-gunicorn`, perché `HUP`
non rilegge l'ambiente.

⛔ Django (8000) e Vite (5173) non si espongono mai: si entra solo da Nginx. La
verifica è il §13 del play-book.

## Il primo amministratore

Il primo amministratore lo crea `manage.py crea_primo_amministratore`, una volta,
dopo il provisioning. Lo lancia la persona che diventerà amministratore: chiede la
password due volte, e l'account nasce con la veste già accesa, senza invito.

```bash
sudo -u $APP_USER bash -lc "
cd $APP_DIR/backend
./manage-env.sh crea_primo_amministratore \\
  --cognome Rossi --nome Anna --codice-fiscale RSSNNA80A41H501X --sesso F \\
  --email anna.rossi@azienda.it --username anna.rossi \\
  --residenza '{\"indirizzo_libero\": \"Via Roma 1\", \"stato_id\": 1, \"comune_id\": 5, \"codice_postale_id\": 9}'
"
```

* La **residenza** è obbligatoria. È un oggetto JSON nella forma degli indirizzi del
  soggetto, senza il tipo: un indirizzo libero (testo, stato e, per lo stato, comune
  e CAP del catalogo) oppure una via da risolvere. `--domicilio-fiscale`, nella
  stessa forma, è facoltativo: se manca, il domicilio fiscale è la residenza.
* Gli **id** dell'indirizzo (`stato_id`, `comune_id`, `codice_postale_id`) sono
  quelli del catalogo del database, e si leggono con `dbshell`, dalla stessa
  cartella, prima di lanciare il comando:

  ```bash
  # lo stato: per un indirizzo italiano e' l'Italia
  ./manage-env.sh dbshell -- -c "SELECT id, descrizione FROM config.stati WHERE sigla_stato = 'ITA'"

  # il comune e il CAP: si cambia il nome del comune; un comune con piu' CAP da' piu' righe
  ./manage-env.sh dbshell -- -c "
    SELECT c.id AS comune_id, c.descrizione AS comune, p.sigla AS provincia,
           cp.id AS codice_postale_id, cp.codice AS cap
      FROM config.comuni c
      JOIN config.codici_postali cp ON cp.comune_id = c.id
      LEFT JOIN config.province p ON p.id = c.provincia_id
     WHERE c.descrizione ILIKE 'Bologna'
     ORDER BY cp.codice"
  ```

  Per l'Italia servono il comune e il CAP, presi dalla **stessa riga**: il CAP deve
  essere di quel comune. Per uno stato estero, che non ha il catalogo dei comuni, al
  posto di `comune_id` e `codice_postale_id` si scrive la località (`"locality"`) e,
  se c'è, il codice postale (`"postal_code"`). Come vale la regola:
  [L'indirizzo libero](/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio).
* Senza terminale si aggiunge `--noinput` e la password si passa nella variabile
  `ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD`, mai come argomento.
* Se l'email è già di un account (per esempio uno creato con il vecchio
  `createsuperuser`), il comando lo mostra e chiede se riusarlo. Con `--noinput`
  il riuso si dichiara con `--riusa-credenziale <auth_user_id>`. Riusato, l'account
  tiene il suo nome utente e la sua password: quella digitata non si usa, e il
  comando lo dice prima di chiederla.
* Il comando funziona solo finché nessun accesso ha mai avuto il profilo
  SUPER_ADMIN; dopo risponde che il primo impianto è chiuso. Gli amministratori
  successivi li crea un SUPER_ADMIN, con l'invito.

⛔ `manage.py createsuperuser` non dà un amministratore: crea solo una credenziale
senza veste (il login risponde 403 `E_VESTE_NON_ATTIVA`), e il flag `is_superuser`
non concede niente. Il dettaglio è nel play-book, §11.

Una volta entrati, ciò che si configura dentro il programma (azienda, operatori,
posta, destinatario delle segnalazioni, parametri, modelli di stampa) è in
[Configurazione iniziale](configurazione-iniziale.md).

## I processi automatici

Fatturazione, code di lavoro e di stampa, email, digest dei presidi e listener
girano come timer e servizi systemd. Le unità sono template versionati in
`backend/deploy/systemd/`. Chi si sveglia e con che cadenza lo dichiara
`backend/deploy/sveglie.json`. Le installa uno script idempotente, che si può
rilanciare:

```bash
sudo backend/bin/install-timers.sh
systemctl list-timers | grep zeroerp
```

Se un processo lavora non lo decide l'installer. A ogni sveglia lo chiede al
database, secondo l'ambiente scelto al passo 8 o la scelta fatta a mano dal
drawer dei processi.

⚠️ I due giri di fatturazione nascono **spenti**: emettono documenti, e si
accendono dal drawer solo quando l'installazione è pronta per SDI.

Il modello e i comandi sono nel play-book, §15 e §16, e in
[Servizi ZeroERP — i comandi](dev/backend/servizi-zeroerp-comandi.md).

## Il frontend

```bash
cd frontend
npm install
npm run dev        # Vite su 127.0.0.1:5173: si apre da Nginx, https://<host>/
                   # (docs/it/dev/backend/configurazione-django.md). Mai --host.
```

## La documentazione

Si costruisce con `python scripts/build_docs_zensical.py`.

---
{% include-markdown "signature-core.md" %}
