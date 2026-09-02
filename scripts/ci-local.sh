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
#   ⇒ Copre la passata `--contexts="!provision"`, che e' dove il migrate si
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
# PREREQUISITI: `sudo -u postgres` (per creare il database) e `db/internal.env`
#   per host/porta.
# ⚠️ Liquibase si invoca SEMPRE via `scripts/liquibase5.sh`, mai col binario nel
#   PATH: quello e' `/opt/liquibase` → 5.0.2, un residuo. Il wrapper prende
#   `tools/liquibase/current` (5.0.3, la stessa della CI) e il driver JDBC
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
    -h|--help)  sed -n '2,50p' "$0"; exit 0 ;;
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
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username=postgres --password="${PGPASSWORD_POSTGRES:-postgres}" \
  --changeLogFile=db/changelog/changelog-provision-pre.yaml update --contexts=provision

echo "── passata principale  (--contexts=\"!provision\")"
echo "   ⭐ e' qui che il migrate si ferma: guarda il numero 'Run:' salire"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_APP" --username=zeroerp --password=secret \
  --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts="!provision"

if $CI_APPLY; then
  echo "── automazioni  (--contexts=ci_apply)"
  echo "   ⚠️ senza il ruolo batch provisionato, i grant runtime possono fallire"
  "$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username=zeroerp --password=secret \
    --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts=ci_apply
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
