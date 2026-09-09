#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Riproduce IN LOCALE la passata di migrate della CI, su un database SCRATCH.
#   Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# A COSA SERVE, in una riga:
#   «trovare il prossimo changeSet che rompe un database ricostruito da zero,
#    senza aspettare un giro di GitHub Actions».
#
# ── ⭐ IL GUADAGNO VERO NON E' LA VELOCITA': E' L'INCREMENTALITA' ──────
#   GitHub ricostruisce il container a ogni corsa, quindi ogni volta ripercorre
#   tutti i changeSet dall'inizio. Qui il database scratch RESTA: dopo una
#   costruzione completa, una ri-esecuzione applica solo cio' che manca.
#   ⇒ Il ciclo «correggo → provo» passa da una corsa intera a pochi secondi.
#
#   ⚠️ E vale finche' si lavora sulla FRONTIERA. Se una correzione tocca un
#   changeSet gia' applicato, l'incrementale non la vede: li' serve `--fresh`.
#
# ── ⛔ COSA NON RIPRODUCE, E PERCHE' E' UNA SCELTA ─────────────────────
#   * il provisioning del ruolo batch (`provision_db_role_batch_*.sql`): fa
#     `ALTER ROLE … PASSWORD`, e i ruoli sono di CLUSTER — cambierebbe la
#     password del ruolo usato dal database di sviluppo. Si salta;
#   * di conseguenza la passata `--contexts=ci_apply`, che da quel ruolo
#     dipende, gira solo con `--ci-apply` e sapendo cosa si sta facendo;
#   * i test Django e la build della documentazione: non c'entrano col migrate.
#   ⇒ Copre la passata `--contexts="!provision and !dati_macchina"`, che e' dove il migrate si
#   ferma ogni volta.
#
# ── ⚠️ ISOLAMENTO DAL DATABASE DI SVILUPPO ────────────────────────────
#   I ruoli PostgreSQL sono di cluster, i database no. Percio' qui:
#     * il ruolo `zeroerp` NON si ricrea se esiste;
#     * le sue GUC si impostano con `ALTER ROLE … IN DATABASE <scratch>`, mai
#       globalmente — altrimenti si riscriverebbe la configurazione con cui
#       lavora il database di sviluppo;
#     * lo script RIFIUTA di operare sul database nominato in `db/internal.env`.
#
# USO:
#   scripts/ci-local.sh              # incrementale: riprende da dove si era fermato
#   scripts/ci-local.sh --fresh      # ricostruisce il database scratch da zero
#   scripts/ci-local.sh --ci-apply   # + la passata delle automazioni (vedi sopra)
#   CI_DB=altro_nome scripts/ci-local.sh
#
# ── ⭐ E PREPARA LO SCRATCH ANCHE PER I pgTAP, sempre e da solo ────────
#   Il migrate costruisce lo schema, ma la suite pretende altre tre cose che in
#   CI fanno tre passi separati dopo Liquibase. Qui si fanno in fondo, sempre,
#   e sono tutte e tre idempotenti:
#
#     1. l'estensione `pgtap` — non la crea nessun changelog. Senza, ogni file
#        muore su `SELECT plan(N)`;
#     2. i privilegi di `zeroerp_app` (`scripts/sql/provision_db_roles.sql`) —
#        senza, ogni rosso e' un permesso e non un difetto;
#     3. lo schema `django`, COPIATO da `$DEV_DB` — lo costruisce
#        `manage.py migrate`, che su questa macchina non c'e'. Diciassette
#        funzioni plpgsql scrivono e leggono `django.auth_user`.
#
#   ⚠️ Nessun flag: una preparazione che dipende da cosa uno si ricorda non
#   sopravvive a un `--fresh`. E' la lezione del `GRANT USAGE` su `maintenance`,
#   che esisteva solo su dbdev perche' era stato dato a mano — e per questo un
#   pgTAP era verde qui e rosso su ogni installazione nuova.
#   ⛔ Lo schema `django` si COPIA: e' fedele oggi, e invecchia in silenzio il
#   giorno in cui arriva una migration Django nuova. La strada fedele resta
#   lanciare `manage.py migrate` DAL SERVER BACKEND puntando a questo host.
#
# PREREQUISITI: `sudo -u postgres` (per creare il database) e `db/internal.env`
#   per host/porta.
# ⚠️ Liquibase si invoca SEMPRE via `scripts/liquibase5.sh`, mai un binario nel
#   PATH: dal 02-09-2026 nel PATH non ce n'e' piu' nessuno (l'installazione di
#   sistema `/opt/liquibase-5.0.2` e i suoi symlink sono stati rimossi), cosi'
#   un `liquibase` nudo fallisce subito invece di far girare in silenzio una
#   versione vecchia e senza driver. Il wrapper prende
#   `tools/liquibase/current` (5.0.4, la stessa della CI) e il driver JDBC
#   versionato nel repo (`tools/liquibase/jdbc/postgresql-42.7.10.jar`).
# ------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

CI_DB="${CI_DB:-zeroerp_ci}"
FRESH=false
CI_APPLY=false
for a in "$@"; do
  case "$a" in
    --fresh)    FRESH=true ;;
    --ci-apply) CI_APPLY=true ;;
    -h|--help)  sed -n '2,73p' "$0"; exit 0 ;;
    *) echo "Opzione sconosciuta: $a" >&2; exit 1 ;;
  esac
done

# --- Host/porta dal file env del progetto (NON il nome del database)
[[ -f db/internal.env ]] || { echo "Manca db/internal.env" >&2; exit 1; }
# shellcheck disable=SC1091
set -a; . db/internal.env; set +a
PGHOST="${PGHOST:-${DB_HOST:-localhost}}"
PGPORT="${PGPORT:-${DB_PORT:-5432}}"
DEV_DB="${DB_NAME:-zeroerp}"

# ⛔ Il cancello che rende questo script sicuro: non si tocca il database di
#    sviluppo, per nessuna ragione e con nessuna variabile d'ambiente.
if [[ "$CI_DB" == "$DEV_DB" ]]; then
  echo "⛔ RIFIUTO: CI_DB ('$CI_DB') e' il database di sviluppo. Scegline un altro." >&2
  exit 1
fi

export PGHOST PGPORT
psql_admin() { sudo -u postgres psql --no-psqlrc -v ON_ERROR_STOP=1 -X -q "$@"; }

# --- L'utenza admin per Liquibase (provision pre/post): serve un SUPERUSER,
#     perche' quei changeSet creano estensioni (postgis, pgtap, plpgsql_check,
#     dblink) che non sono «trusted».
ADMIN_USER="${CI_ADMIN_USER:-postgres}"
ADMIN_PWD="${PGPASSWORD_POSTGRES:-}"

# ⛔ PRE-VOLO. Liquibase si connette via TCP, non col socket: `sudo -u postgres`
#   qui non aiuta, serve una PASSWORD. Meglio scoprirlo adesso, in due secondi,
#   che dopo aver creato il database e macinato meta' provisioning.
# ⚠️ Si PROVA la connessione invece di pretendere una password: se il cluster ha
#   `trust` sul TCP locale, una password non serve — e un controllo sulla
#   variabile vuota direbbe di no a un caso che funziona.
if ! PGPASSWORD="$ADMIN_PWD" psql -X -q -A -t -w \
      -h "$PGHOST" -p "$PGPORT" -U "$ADMIN_USER" -d postgres \
      -c "SELECT 1" >/dev/null 2>&1; then
  cat >&2 <<MSG
⛔ Non riesco a connettermi via TCP come '$ADMIN_USER'.
   Liquibase usa JDBC, quindi il socket e 'sudo -u postgres' non bastano: i passi
   di provisioning creano ESTENSIONI (postgis, pgtap, plpgsql_check, dblink), che
   richiedono un superuser con password.

   Due strade:
     1) se il ruolo '$ADMIN_USER' ha gia' una password, passala:
          PGPASSWORD_POSTGRES='<password>' CI_DB=$CI_DB $0 ${*:-}
     2) se hai un ALTRO superuser con password, usalo:
          CI_ADMIN_USER=<ruolo> PGPASSWORD_POSTGRES='<password>' CI_DB=$CI_DB $0 ${*:-}

   ⚠️ Assegnare una password a 'postgres' e' una modifica al CLUSTER, quindi
   condivisa col database di sviluppo: falla solo se sai di volerla.
MSG
  exit 1
fi
echo "── admin per il provisioning: $ADMIN_USER (connessione TCP verificata)"

echo "── database scratch: $CI_DB   (sviluppo: $DEV_DB, intoccato)"

if $FRESH; then
  echo "── ricostruisco da zero"
  psql_admin -d postgres -c "DROP DATABASE IF EXISTS \"$CI_DB\" WITH (FORCE);"
fi

if ! psql_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$CI_DB'" | grep -q 1; then
  echo "── creo $CI_DB"
  psql_admin -d postgres -c "CREATE DATABASE \"$CI_DB\" OWNER postgres;"
fi

# --- Ruolo applicativo: si crea SOLO se manca (i ruoli sono di cluster).
#     Le GUC si impostano PER DATABASE, mai globalmente.
psql_admin -d "$CI_DB" <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='zeroerp') THEN
    CREATE ROLE zeroerp LOGIN PASSWORD 'secret';
  END IF;
END \$\$;
ALTER ROLE zeroerp IN DATABASE "$CI_DB" SET myapp.user_language = 'it';
ALTER ROLE zeroerp IN DATABASE "$CI_DB" SET myapp.dblink_log_connection =
  'hostaddr=127.0.0.1 port=$PGPORT dbname=$CI_DB user=zeroerp password=secret';
GRANT USAGE, CREATE ON SCHEMA public TO zeroerp;
GRANT CREATE ON DATABASE "$CI_DB" TO zeroerp;
SQL

# ── ⛔ LA DIVERGENZA CHE QUESTA REPLICA NON PUO' EVITARE, E COME SI CHIUDE ──
#
#   I database sono per-database, i RUOLI sono di CLUSTER. In GitHub il
#   container e' vergine, quindi durante la passata principale
#   `zeroerp_batch_fatturazione` NON ESISTE (lo provisiona il passo dopo).
#   Qui esiste sempre: lo usa il database di sviluppo.
#
#   ⚠️ E c'e' una guardia che distingue proprio quei due mondi —
#   `20260729-05-enable-rls-fatture-satelliti`, la cui preCondition conta
#   «ruoli batch con la postura SBAGLIATA»:
#     (a) ruolo assente        -> 0, niente da proteggere  ← GitHub
#     (b) ruolo presente senza BYPASSRLS o senza i GRANT -> 1, HALT
#   Sul database scratch cadiamo in (b) per un motivo che non e' un difetto:
#   il ruolo c'e' (cluster) ma i GRANT no, perche' i GRANT sono per-database e
#   questo database e' nuovo.
#
#   ⭐ Si chiude con ALTER DEFAULT PRIVILEGES, lo stesso meccanismo che il
#   provisioning usa per gli oggetti futuri: ogni tabella creata da `zeroerp`
#   durante la passata nasce gia' con il DML per il ruolo batch. E' per
#   DATABASE (vive in pg_default_acl di questo database), quindi non tocca
#   sviluppo.
#
#   🔴 E VA DICHIARATO: cosi' il database scratch da al ruolo batch PIU' di
#   quanto il provisioning vero gli darebbe — li' il DML e' un perimetro
#   esplicito di 28 tabelle, qui e' tutto. ⇒ Questo database serve a trovare
#   i changeSet che rompono un migrate da zero, NON a collaudare la postura
#   dei permessi: per quella c'e'
#   db/pgtap/rls/test-role-batch-fatturazione-postura.sql, che va girato sul
#   database vero.
#   ⚠️ SENZA `IN SCHEMA`, e non e' pigrizia: la forma con lo schema pretende
#   che lo schema ESISTA, e qui gli schemi li crea la passata principale, dopo.
#   Crearli in anticipo sarebbe peggio del problema: un changeSet con
#   `CREATE SCHEMA` senza `IF NOT EXISTS` morirebbe. La forma senza schema vale
#   per l'intero database, compresi quelli che nasceranno.
if psql_admin -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='zeroerp_batch_fatturazione'" | grep -q 1; then
  echo "── il ruolo batch esiste nel cluster: gli do il DML sugli oggetti futuri di $CI_DB"
  psql_admin -d "$CI_DB" -c "
    ALTER DEFAULT PRIVILEGES FOR ROLE zeroerp
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zeroerp_batch_fatturazione;
    ALTER DEFAULT PRIVILEGES FOR ROLE postgres
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zeroerp_batch_fatturazione;" >/dev/null
fi

# --- L'autogen, come in CI: l'ordine dei changeSet e' generato, non versionato
echo "── rigenero changelog-autogen.yaml (--strict)"
python3 scripts/gen_master_autogen.py \
  --root db/changelog/migrations_v2 \
  --out  db/changelog/migrations_v2/changelog-autogen.yaml \
  --strict

URL_CI="jdbc:postgresql://${PGHOST}:${PGPORT}/${CI_DB}?options=-c%20myapp.env%3Dci"
URL_APP="jdbc:postgresql://${PGHOST}:${PGPORT}/${CI_DB}?options=-c%20myapp.log_with_dblink%3Doff"

# ⛔ DIFESA 1 — un defaults-file VUOTO.
#   `db/liquibase.properties` contiene `url=…/zeroerp` e `username=titodb`,
#   cioe' il database di sviluppo. Gli argomenti espliciti hanno la precedenza
#   sul file, ma qui non si vuole dipendere da una regola di precedenza: si
#   toglie di mezzo il file. Con un defaults-file vuoto NESSUN properties puo'
#   iniettare un url, nemmeno se qualcuno ne aggiungesse uno domani nella
#   directory da cui si lancia.
DEFAULTS_VUOTO="$(mktemp)"
trap 'rm -f "$DEFAULTS_VUOTO"' EXIT

# ⛔ DIFESA 2 — il TESTIMONE sul database di sviluppo.
#   Non si dichiara «non lo tocco»: si misura. Si legge lo stato del
#   `databasechangelog` di sviluppo PRIMA e DOPO, e se cambia lo script grida.
#   ⚠️ E' l'unica forma di garanzia che non dipende dal fatto che io abbia
#   letto bene la documentazione di Liquibase.
testimone_dev() {
  PGPASSWORD="${PGPASSWORD:-${DB_PASSWORD:-}}" psql -X -A -t \
    -U "${PGUSER:-${DB_USER:-}}" -d "$DEV_DB" \
    -c "SELECT count(*)||'/'||COALESCE(max(dateexecuted)::text,'-') FROM databasechangelog" 2>/dev/null || echo "?"
}
DEV_PRIMA="$(testimone_dev)"
echo "── testimone su $DEV_DB (prima): $DEV_PRIMA"

LB="$SCRIPT_DIR/liquibase5.sh"
echo "── $("$LB" --version 2>/dev/null | grep -i '^Liquibase Version' || echo 'Liquibase: versione?')"

echo "── provision pre"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username="$ADMIN_USER" --password="$ADMIN_PWD" \
  --changeLogFile=db/changelog/changelog-provision-pre.yaml update --contexts=provision

# ⛔ LE GRANT VANNO QUI, DOPO IL PROVISION-PRE — e l'ordine e' tutto.
#   Il provision-pre gira come SUPERUSER e crea `public.databasechangelog`; la
#   passata principale gira come `zeroerp`, che su una tabella creata da un
#   altro ruolo non ha nessun diritto. `GRANT … ON ALL TABLES` fotografa le
#   tabelle CHE ESISTONO nel momento in cui lo si esegue: darlo prima non
#   copre una tabella che nascera' dopo.
#   ⚠️ Il sintomo, se lo si mette prima, non parla di permessi in modo
#   riconoscibile: Liquibase muore su una sua query interna di checksum —
#   «Error executing SQL SELECT MD5SUM FROM public.databasechangelog … :
#   permesso negato» — e sembra un problema di MD5.
#   ⭐ E' esattamente il passo «Grant CREATE on public (CI bootstrap)» di
#   ci.yaml, che sta anch'esso DOPO il provision-pre: qui si copia la sua
#   posizione, non solo il suo contenuto.
echo "── grant post-provision (come il passo 'CI bootstrap' di ci.yaml)"
psql_admin -d "$CI_DB" <<SQL
GRANT USAGE, CREATE ON SCHEMA public TO zeroerp;
GRANT CREATE ON DATABASE "$CI_DB" TO zeroerp;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zeroerp;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO zeroerp;
SQL

# ── ⚠️ E LE TABELLE CHE ESISTONO GIA' ─────────────────────────────────
#   `ALTER DEFAULT PRIVILEGES` copre solo cio' che NASCE dopo. Su una corsa
#   incrementale — cioe' la seconda in poi — meta' schema esiste gia', creato
#   prima che quella riga ci fosse: quelle tabelle restano senza i grant, e la
#   guardia di 20260729-05 continua a vedere la postura sbagliata.
#   ⇒ Le due cose servono entrambe: il default per il futuro, il GRANT per il
#   passato. E' idempotente, quindi si rifa' a ogni corsa.
if psql_admin -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='zeroerp_batch_fatturazione'" | grep -q 1; then
  echo "── grant al ruolo batch sulle tabelle GIA' create (corsa incrementale)"
  psql_admin -d "$CI_DB" <<'SQL' >/dev/null
DO $$
DECLARE s text;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace
            WHERE nspname NOT LIKE 'pg\_%' AND nspname <> 'information_schema'
  LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO zeroerp_batch_fatturazione', s);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO zeroerp_batch_fatturazione', s);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO zeroerp_batch_fatturazione', s);
  END LOOP;
END $$;
SQL
fi

# ── ⚠️ pgAgent: qui la fase 85_pgagent GIRA DAVVERO, in CI no ─────────
#   I nove changeSet di `85_pgagent` sono protetti da
#   `onFail: MARK_RAN` + «esiste l'estensione pgagent». Sull'immagine della CI
#   l'estensione non e' disponibile, quindi vengono saltati tutti e quella fase
#   non e' mai stata eseguita da nessuna parte. Qui l'estensione c'e', quindi
#   girano — ed e' un guadagno: si collauda codice che GitHub non puo' provare.
#   ⚠️ Ma il migratore ha bisogno dei diritti sullo schema `pgagent`, che
#   appartiene a chi ha creato l'estensione (postgres). Su dbdev il problema non
#   si vede perche' pgAgent fu installato a mano dallo stesso utente.
#   🔵 Domanda aperta per il deploy vero: in produzione, chi lancia Liquibase ha
#   USAGE su `pgagent`? Se no, quei nove changeSet falliranno li' come qui.
if psql_admin -d "$CI_DB" -tAc "SELECT 1 FROM pg_namespace WHERE nspname='pgagent'" | grep -q 1; then
  echo "── grant su schema pgagent a zeroerp (la fase 85 qui gira davvero)"
  psql_admin -d "$CI_DB" <<'SQL' >/dev/null
GRANT USAGE ON SCHEMA pgagent TO zeroerp;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pgagent TO zeroerp;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pgagent TO zeroerp;
ALTER DEFAULT PRIVILEGES IN SCHEMA pgagent
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zeroerp;
SQL
fi

echo "── passata principale  (--contexts=\"!provision and !dati_macchina\")"
echo "   ⭐ e' qui che il migrate si ferma: guarda il numero 'Run:' salire"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_APP" --username=zeroerp --password=secret \
  --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts="!provision and !dati_macchina"

if $CI_APPLY; then
  echo "── automazioni  (--contexts=ci_apply)"
  echo "   ⚠️ senza il ruolo batch provisionato, i grant runtime possono fallire"
  "$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username=zeroerp --password=secret \
    --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts=ci_apply
fi

# ══════════════════════════════════════════════════════════════════════
# Preparazione al collaudo: cio' che serve ai pgTAP e che il migrate non fa.
# Tutte e tre idempotenti: a regime non stampano niente e non cambiano niente.
# ══════════════════════════════════════════════════════════════════════

# 0. ⛔ IL CANALE DI LOG dblink, SPENTO PER QUESTO DATABASE.
#    Il cluster ha un default `myapp.dblink_log_connection` che punta al
#    database di SVILUPPO come `titodb` e senza password. Su `zeroerp` non si
#    vede, perche' li' un override per-database lo copre con
#    `service=zeroerp_log`; su uno scratch appena creato quel default affiora.
#    ⇒ Ogni funzione che solleva un errore prova a scriverlo via dblink, e come
#    ruolo applicativo muore su «password or GSSAPI delegated credentials
#    required» — un 2F003 al posto del P0001 del dominio.
#    ⚠️ Misurato il 2026-09-09: 151 dei 194 file di `vendite` che fallivano nel
#    fixture riportavano QUEL messaggio invece del proprio. Non un rosso in
#    piu': un rosso che MENTE sulla causa, e che avrebbe mandato il triage a
#    inseguire un fantasma.
#    ⭐ Svuotarlo e' cio' che rende lo scratch simile alla CI, dove quella GUC
#    non e' impostata affatto: `fn_get_or_create_session_tx_id` prende il ramo
#    della sentinella, avvisa e prosegue.
#    ⚠️ Il ruolo `zeroerp` non e' toccato: ha un `ALTER ROLE ... IN DATABASE`
#    suo, impostato piu' sopra, che ha la precedenza. Il migratore continua a
#    registrare i propri tx_id.
psql_admin -d postgres -c \
  "ALTER DATABASE \"$CI_DB\" SET myapp.dblink_log_connection = '';" >/dev/null

# 1. L'estensione pgtap. In CI la crea il passo della suite; qui nessuno.
if ! psql_admin -d "$CI_DB" -tAc "SELECT 1 FROM pg_extension WHERE extname='pgtap'" | grep -q 1; then
  echo "── installo l'estensione pgtap su $CI_DB"
  psql_admin -d "$CI_DB" -c "CREATE EXTENSION IF NOT EXISTS pgtap;" >/dev/null
fi

# 2. I privilegi del ruolo applicativo, come il passo `provision_db_roles` della
#    CI. ⛔ La password si LEGGE da ~/.pgpass e non si inventa: lo script fa
#    `ALTER ROLE ... PASSWORD` e i ruoli sono di CLUSTER, quindi un valore nuovo
#    spaccherebbe l'accesso di zeroerp_app al database di sviluppo. Con la
#    password che ha gia', quella riga e' un non-evento.
#
# ⛔ E SI RILANCIA SEMPRE, non «solo se mancano i grant». `GRANT ... ON ALL
#   TABLES IN SCHEMA` e' una FOTOGRAFIA: copre le tabelle che esistono
#   nell'istante in cui gira, non quelle che nascono dopo. E dopo ne nascono
#   eccome — le tabelle `storico.*` le genera il framework delle automazioni
#   nella passata `ci_apply`, cioe' piu' tardi.
#   ⚠️ Successo il 2026-09-09 su questo script, con un guard «salta se i grant
#   ci sono gia'» che sembrava innocuo: quattro tabelle (`storico.user_override_*`,
#   `storico.user_emittenti_fiscali`) sono rimaste senza `SELECT` per
#   `zeroerp_app`, e `db/pgtap/dbops/test-audit-sources-seed.sql` e' diventato
#   rosso — perche' `information_schema.columns` mostra solo le colonne su cui
#   il ruolo ha privilegi, quindi quelle quattro «non esistevano».
#   ⭐ E' la ragione per cui in `ci-validate.yaml` il passo `provision_db_roles`
#   sta DOPO `--contexts=ci_apply` e non prima: qui si copia quell'ordine.
APP_PWD="$(awk -F: -v db="$DEV_DB" '$3==db && $4=="zeroerp_app" {print $5; exit}' ~/.pgpass 2>/dev/null || true)"
if [ -n "$APP_PWD" ]; then
  echo "── privilegi di zeroerp_app su $CI_DB (provision_db_roles)"
  # ⚠️ Dallo STDIN e non con `-f`: `/home/tid` e' `drwx------`, quindi l'utente
  #   `postgres` non puo' attraversarlo e un percorso non lo aprirebbe mai. Cosi'
  #   il file lo apre la shell, che gira come l'utente giusto, e a psql arriva
  #   gia' un descrittore.
  psql_admin -d "$CI_DB" \
    -v app_role=zeroerp_app -v app_password="$APP_PWD" -v migrator_role=zeroerp \
    < scripts/sql/provision_db_roles.sql >/dev/null
else
  echo "⚠️  password di zeroerp_app non trovata in ~/.pgpass: salto i privilegi." >&2
  echo "    (riga attesa: $PGHOST:$PGPORT:$DEV_DB:zeroerp_app:<password>)" >&2
  echo "    NON la invento: un ALTER ROLE con un valore nuovo e' di CLUSTER e" >&2
  echo "    romperebbe l'accesso al database di sviluppo. I pgTAP falliranno" >&2
  echo "    tutti per permessi finche' non la aggiungi." >&2
fi

# 3. Lo schema django, copiato da $DEV_DB. ⚠️ E' una COPIA, non un migrate: il
#    DDL e' quello che Django ha prodotto la', quindi fedele oggi. Si carica
#    come `zeroerp` cosi' le tabelle le possiede lui — i pgTAP marcati
#    `pgtap-runner: owner` girano con quel ruolo e ci scrivono dentro.
#    ⚠️ `django_migrations` resta vuota: e' dichiarato in intestazione.
if ! psql_admin -d "$CI_DB" -tAc \
       "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='django' AND c.relname='auth_user'" | grep -q 1; then
  if psql_admin -d "$DEV_DB" -tAc \
       "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='django' AND c.relname='auth_user'" | grep -q 1; then
    echo "── copio lo schema django da $DEV_DB (sola lettura di la')"
    # -T token_blacklist: quelle due tabelle su CI_DB le ha gia' create Liquibase.
    # Si tolgono `CREATE SCHEMA` (lo schema c'e' gia') e le ALTER DEFAULT
    # PRIVILEGES di un altro ruolo (zeroerp non puo' cambiarle, e qui non servono).
    sudo -u postgres pg_dump -d "$DEV_DB" --schema-only --no-owner \
         -n django -T 'django.token_blacklist_*' \
      | sed -e '/^CREATE SCHEMA django;$/d' -e '/^ALTER DEFAULT PRIVILEGES FOR ROLE/d' \
      | PGPASSWORD=secret psql --no-psqlrc -h "$PGHOST" -p "$PGPORT" -U zeroerp -d "$CI_DB" \
          -X -q -v ON_ERROR_STOP=1 >/dev/null
  else
    echo "⚠️  django.auth_user non c'e' nemmeno su $DEV_DB: niente da copiare." >&2
    echo "    Lancia 'manage.py migrate' dal server backend puntando a questo host." >&2
  fi
fi

DEV_DOPO="$(testimone_dev)"
echo "── testimone su $DEV_DB (dopo):  $DEV_DOPO"
if [[ "$DEV_PRIMA" != "$DEV_DOPO" ]]; then
  echo "🔴 ALLARME: il databasechangelog di '$DEV_DB' e' CAMBIATO durante la corsa." >&2
  echo "   prima: $DEV_PRIMA" >&2
  echo "   dopo : $DEV_DOPO"  >&2
  echo "   Qualcosa ha scritto sul database di sviluppo: fermarsi e capire." >&2
  exit 2
fi
echo "✅ il database di sviluppo '$DEV_DB' non e' stato toccato (testimone invariato)"

echo "──────────────────────────────────────────────"
echo "✅ passata completata su $CI_DB"
echo "   la prossima esecuzione e' INCREMENTALE: riapplica solo cio' che manca."
echo "   ⚠️ se hai corretto un changeSet GIA' applicato, serve --fresh."
