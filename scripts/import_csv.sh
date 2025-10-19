#!/usr/bin/env bash
set -euo pipefail

print_usage() {
  cat <<'EOF'
Uso:
  import_csv.sh --schema <schema> [--env <file.env>] [--all] [tabella1 tabella2 ...]
Esempi:
  import_csv.sh --schema config --all
  import_csv.sh -s config tipi_ruoli valute
  import_csv.sh -s config -e /path/a/internal.env --all

Note:
- internal.env deve contenere: POSTGRESQL_USER, POSTGRESQL_PWD, DB_HOST, DB_PORT, DB_NAME
- I CSV sono letti da: <repo_root>/db/changelog/migrations_v2/80_data/sql/<schema>/
EOF
}

# --- Percorsi progetto (repo_root = parent della cartella dello script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE_DEFAULT="$REPO_ROOT/internal.env"

SCHEMA=""
ENV_FILE=""
DUMP_ALL=false
TABLES=()

# --- Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--schema) SCHEMA="${2:-}"; shift 2 ;;
    -e|--env)    ENV_FILE="${2:-}"; shift 2 ;;
    --all)       DUMP_ALL=true; shift ;;
    -h|--help)   print_usage; exit 0 ;;
    --)          shift; break ;;
    -*)          echo "Opzione sconosciuta: $1" >&2; print_usage; exit 1 ;;
    *)           TABLES+=("$1"); shift ;;
  esac
done

# --- Validazioni
if [[ -z "$SCHEMA" ]]; then
  echo "Errore: --schema è obbligatorio" >&2
  print_usage; exit 1
fi

# Env file effettivo
if [[ -z "$ENV_FILE" ]]; then ENV_FILE="$ENV_FILE_DEFAULT"; fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env non trovato: $ENV_FILE" >&2
  exit 1
fi

# --- Carica env KEY=VALUE (ignora commenti/righe vuote, ripulisce CRLF)
# Variabili attese: POSTGRESQL_USER, POSTGRESQL_PWD, DB_HOST, DB_PORT, DB_NAME
while IFS='=' read -r k v; do
  [[ -z "${k// }" ]] && continue
  [[ "$k" =~ ^# ]] && continue
  k="$(echo "$k" | tr -d '\r' | xargs)"
  v="$(echo "$v" | tr -d '\r' | sed 's/^ *//;s/ *$//')"
  case "$k" in
    POSTGRESQL_USER) PGUSER="$v" ;;
    POSTGRESQL_PWD)  PGPASSWORD="$v" ;;
    DB_HOST)         PGHOST="$v" ;;
    DB_PORT)         PGPORT="$v" ;;
    DB_NAME)         PGDATABASE="$v" ;;
    *)               : ;;
  esac
done < "$ENV_FILE"

: "${PGUSER:?manca POSTGRESQL_USER in $ENV_FILE}"
: "${PGPASSWORD:?manca POSTGRESQL_PWD in $ENV_FILE}"
: "${PGHOST:?manca DB_HOST in $ENV_FILE}"
: "${PGPORT:?manca DB_PORT in $ENV_FILE}"
: "${PGDATABASE:?manca DB_NAME in $ENV_FILE}"

export PGUSER PGPASSWORD PGHOST PGPORT PGDATABASE
export PGCLIENTENCODING=UTF8
export PGOPTIONS="-c search_path=${SCHEMA}"

# --- Base CSV
BASE_DIR="$REPO_ROOT/db/changelog/migrations_v2/80_data/sql/$SCHEMA"
if [[ ! -d "$BASE_DIR" ]]; then
  echo "Errore: directory CSV non trovata: $BASE_DIR" >&2
  exit 1
fi

# Se --all, prendi tutti i .csv presenti (senza estensione), ordinati
if $DUMP_ALL; then
  mapfile -t TABLES < <(find "$BASE_DIR" -maxdepth 1 -type f -name '*.csv' -printf '%f\n' \
                        | sort | sed 's/\.csv$//' )
fi
if [[ ${#TABLES[@]} -eq 0 ]]; then
  echo "Errore: nessuna tabella specificata (usa --all o elenca le tabelle)" >&2
  exit 1
fi

# --- Import funzione
import_table() {
  local tbl="$1"
  local file="$BASE_DIR/$tbl.csv"
  echo ">> Import ${SCHEMA}.${tbl} ← ${file}"
  if [[ ! -s "$file" ]]; then
    echo "⚠️  File mancante o vuoto: $file" >&2
    return 0
  fi
  # \COPY lato client: evita permessi server sul path
  psql -X -v ON_ERROR_STOP=1 --pset footer=off \
    -c "\\COPY \"${SCHEMA}\".\"${tbl}\" FROM '$file' WITH (FORMAT CSV, HEADER, ENCODING 'UTF8')"
}

# --- Loop
RC=0
for tbl in "${TABLES[@]}"; do
  if ! import_table "$tbl"; then
    RC=1
  fi
done

if [[ $RC -eq 0 ]]; then
  echo "✅ Import CSV completato per schema $SCHEMA"
else
  echo "❌ Completato con errori (vedi messaggi sopra)" >&2
fi

exit $RC
