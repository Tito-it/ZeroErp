# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------


#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Genera CSV da PostgreSQL usando psql e salva in:
#   db/changelog/migrations_v2/80_data/sql/<schema>/
#
# Usa un file env stile KEY=VALUE (default: ../internal.env) per:
#   POSTGRESQL_USER, POSTGRESQL_PWD, DB_HOST, DB_PORT, DB_NAME
#
# USO:
#   ./export_csv.sh -s <schema> [--all] [tabella1 tabella2 ...]
#   ./export_csv.sh -s config --all
#   ./export_csv.sh -s config stati valute iva
#   ./export_csv.sh -s config -e /percorso/custom.env --all
# -----------------------------------------------------------------------------

SCHEMA=""
ENV_FILE=""
DUMP_ALL=false
TABLES=()

print_usage() {
  cat <<EOF
Uso: $0 -s <schema> [-e <env_file>] [--all] [tabella1 tabella2 ...]
 -s|--schema     Nome schema (obbligatorio)
 -e|--env        File env (default: <repo_root>/internal.env)
 --all           Esporta tutte le tabelle BASE dello schema
 Se NON usi --all, specifica i nomi tabella dopo le opzioni.
EOF
}

# --- Percorsi progetto (repo_root = parent della cartella dello script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Default env file
ENV_FILE_DEFAULT="$REPO_ROOT/internal.env"

# --- Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--schema)
      SCHEMA="${2:-}"; shift 2 ;;
    -e|--env)
      ENV_FILE="${2:-}"; shift 2 ;;
    --all)
      DUMP_ALL=true; shift ;;
    -h|--help)
      print_usage; exit 0 ;;
    --) shift; break ;;
    -*)
      echo "Opzione sconosciuta: $1" >&2; print_usage; exit 1 ;;
    *)
      TABLES+=("$1"); shift ;;
  esac
done

# --- Validazioni
if [[ -z "$SCHEMA" ]]; then
  echo "Errore: --schema è obbligatorio" >&2
  print_usage; exit 1
fi

# Env file effettivo
if [[ -z "$ENV_FILE" ]]; then
  ENV_FILE="$ENV_FILE_DEFAULT"
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env non trovato: $ENV_FILE" >&2
  exit 1
fi

# --- Carica env KEY=VALUE (ignora commenti/righe vuote)
# Variabili attese: POSTGRESQL_USER, POSTGRESQL_PWD, DB_HOST, DB_PORT, DB_NAME
# (non usa 'export $(grep ...)' per evitare problemi con spazi)
while IFS='=' read -r k v; do
  [[ -z "${k// }" ]] && continue
  [[ "$k" =~ ^# ]] && continue
  k="$(echo "$k" | xargs)"
  v="$(echo "$v" | sed 's/^ *//;s/ *$//')"
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

# --- Verifica psql
command -v psql >/dev/null 2>&1 || { echo "Errore: 'psql' non trovato nel PATH"; exit 1; }

# --- Directory di output
OUT_DIR="$REPO_ROOT/db/changelog/migrations_v2/80_data/sql/$SCHEMA"
mkdir -p "$OUT_DIR"

# --- Se richiesto, auto-scopri tutte le tabelle BASE dello schema
if $DUMP_ALL; then
  mapfile -t TABLES < <(
    psql -X -A -t -v ON_ERROR_STOP=1 \
      -c "select table_name
            from information_schema.tables
           where table_schema = '${SCHEMA}'
             and table_type = 'BASE TABLE'
        order by table_name"
  )
fi

# --- Se non ci sono tabelle, esci pulito
if [[ ${#TABLES[@]} -eq 0 ]]; then
  echo "Nessuna tabella specificata/trovata per lo schema '$SCHEMA'. Niente da fare."
  exit 0
fi

dump_table() {
  local tbl="$1"
  local out="$2"
  local tmp
  tmp="$(mktemp)"

  echo ">> ${SCHEMA}.${tbl}  →  ${out}"

  # Esegui il dump su file temporaneo
  if ! psql -X -v ON_ERROR_STOP=1 --pset footer=off \
       -c "\COPY \"${SCHEMA}\".\"${tbl}\" TO STDOUT WITH (FORMAT CSV, HEADER, ENCODING 'UTF8')" \
       > "$tmp"; then
    echo "!! ERRORE psql su ${SCHEMA}.${tbl}" >&2
    rm -f "$tmp"
    return 1
  fi

  # File vuoto = errore (es. tabella inesistente)
  if [ ! -s "$tmp" ]; then
    echo "!! Nessun dato esportato per ${SCHEMA}.${tbl} (file vuoto): probabile errore" >&2
    rm -f "$tmp"
    return 1
  fi

  # Ok: promuovi il temporaneo a output finale
  mv -f "$tmp" "$out"

  # Solo header? (1 riga)
  if [ "$(wc -l < "$out")" -eq 1 ]; then
    echo "-- Tabella vuota: ${SCHEMA}.${tbl} (solo header)"
  fi
}


# --- Loop
FAILED=0
for t in "${TABLES[@]}"; do
  CSV_PATH="$OUT_DIR/$t.csv"
  if ! dump_table "$t" "$CSV_PATH"; then
    echo "!! ERRORE su tabella: $t" >&2
    FAILED=$((FAILED+1))
  fi
done

echo "--------------------------------------------"
echo "Export completato in: $OUT_DIR"
[[ $FAILED -gt 0 ]] && echo "Tabelle fallite: $FAILED" >&2 && exit 2 || exit 0
