# Installazione

Questa pagina dice **in che ordine** si tira su ZeroErp su una macchina nuova e
rimanda alle pagine che spiegano ogni passo. Ciò che si configura **dentro** il
programma (azienda, operatori, posta, timer) sta in
[Configurazione iniziale](configurazione-iniziale.md).

⚠️ La forma del setup «macchina singola» (Docker o ambiente virtuale Python) non
è ancora decisa ([promemoria](dev/work-in-progress/promemoria-installazione-md.md)).
La parte del **database** non dipende da quella scelta ed è scritta per intero qui
sotto. La messa in opera completa di un server è nel
[play-book operativo](dev/backend/play-book-operativo-backend.md).

## Prerequisiti

- Python, con le dipendenze di `requirements.txt` (Django compreso)
- PostgreSQL 18, con le estensioni del paragrafo «Il database»
- Liquibase: si usa quello del repository, con `scripts/liquibase5.sh`
- Node.js, per il frontend (Vue 3 + Vite)

Versioni consigliate: [Versioni supportate](versioni-supportate.md).

## Il codice e l'ambiente Python

```bash
git clone git@github.com:Tito-it/ZeroErp.git
cd ZeroErp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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
`uuid-ossp`) ci sono già. Le crea nel database il primo passo di Liquibase, da
superuser.

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
