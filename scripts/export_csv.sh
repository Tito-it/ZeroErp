# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
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

  # --- Ordinamento: la chiave primaria, se c'e'.
  # ⚠️ Senza ORDER BY, \COPY esce in ordine FISICO: il diff cambia a ogni
  #   riesportazione anche quando i dati non sono cambiati, e una revisione non
  #   riesce piu' a distinguere «e' cambiato un valore» da «si sono mosse le
  #   righe». Fallback: nessun ordinamento se la tabella non ha PK.
  local pk order_by
  pk="$(psql -X -A -t -v ON_ERROR_STOP=1 -c "
      SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY k.ord)
        FROM pg_constraint c
        JOIN pg_class t     ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
       WHERE c.contype = 'p' AND n.nspname = '${SCHEMA}' AND t.relname = '${tbl}'" 2>/dev/null || true)"
  if [[ -n "${pk// }" ]]; then order_by=" ORDER BY ${pk}"; else order_by=""; fi

  # Esegui il dump su file temporaneo
  # ⚠️ NULL 'NULL' — NON e' un dettaglio di formato: i mirror `loadUpdateData`
  #   del progetto leggono il TOKEN LETTERALE `NULL`, ed e' la convenzione
  #   scritta in AGENTS §80_data. Con il default di \COPY un NULL esce come
  #   cella VUOTA, e Liquibase la rende come stringa '' su ogni colonna
  #   dichiarata STRING: su una colonna numerica il migrate muore con
  #   «sintassi di input non valida per il tipo integer: ""», su una varchar
  #   passa e scrive '' dove c'era NULL — che e' peggio, perche' non lo dice.
  #   Successo il 2026-09-02 su vendite.registri_fatturazione.utility_id.
  #   ⭐ E il giro e' fedele: un NULL esce come `NULL` nudo, una stringa
  #   davvero vuota come `""`, quindi le due cose restano distinguibili.
  if ! psql -X -v ON_ERROR_STOP=1 --pset footer=off \
       -c "\COPY (SELECT * FROM \"${SCHEMA}\".\"${tbl}\"${order_by}) TO STDOUT WITH (FORMAT CSV, HEADER, NULL 'NULL', ENCODING 'UTF8')" \
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
