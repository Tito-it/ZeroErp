#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Ritira dal CLUSTER uno o piu' ruoli PostgreSQL dismessi.
#   Copyright (C) 2026 Tid (Michele Carlo Titini)
#   Brief: docs/it/dev/work-done/brief-db-ruoli-di-sistema.md §18
#
# A COSA SERVE: un `DROP ROLE` riesce solo quando il ruolo non ha piu' niente in
#   NESSUN database del cluster — privilegi, privilegi di default, oggetti. Ma
#   `DROP OWNED BY` lavora sul database a cui si e' collegati. Questo script
#   gira su ogni database, poi toglie il ruolo.
#   ⭐ Sostituisce scripts/sql/retire_db_role_batch_fatturazione.sql (fase 4,
#   2026-10-15), che lavorava su un database solo e non sarebbe nemmeno partito:
#   usava variabili psql dentro blocchi `DO`, dove psql non le sostituisce.
#
# ⛔ NON cancella OGGETTI. Se un ruolo POSSIEDE qualcosa (una tabella, una
#   funzione, un database), lo script si ferma e lo nomina: `DROP OWNED` lo
#   cancellerebbe, e quella e' una decisione da prendere guardandolo. Unica
#   eccezione: un database nominato con --cancella-database, che si cancella
#   PRIMA (con tutto cio' che contiene), ed e' irreversibile.
#
# USO (da un utente che si collega come superuser; password in PGPASSWORD):
#   scripts/ritira_ruoli_dismessi.sh zeroerp_batch_fatturazione pgagent
#        -> PROVA A VUOTO (default): elenca, prova ogni DROP OWNED e annulla
#   scripts/ritira_ruoli_dismessi.sh --esegui zeroerp_batch_fatturazione pgagent
#   scripts/ritira_ruoli_dismessi.sh --esegui --cancella-database zeroerp_ci zeroerp
#
#   Connessione: PGHOST/PGPORT (default localhost:5432), utente PGUSER
#   (default postgres). Il database di sviluppo letto da db/internal.env non si
#   cancella mai, ne' si ritirano i ruoli di sistema.
# ------------------------------------------------------------
set -euo pipefail

ESEGUI=false
DB_DA_CANCELLARE=()
RUOLI=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --esegui) ESEGUI=true ;;
    --cancella-database) shift; DB_DA_CANCELLARE+=("${1:?manca il nome del database}") ;;
    -h|--help) sed -n "2,$(($(grep -n '^set -euo pipefail' "$0" | head -1 | cut -d: -f1) - 1))p" "$0"; exit 0 ;;
    -*) echo "Opzione sconosciuta: $1" >&2; exit 1 ;;
    *) RUOLI+=("$1") ;;
  esac
  shift
done
[[ ${#RUOLI[@]} -gt 0 ]] || { echo "Nessun ruolo indicato (vedi --help)." >&2; exit 1; }

export PGHOST="${PGHOST:-localhost}" PGPORT="${PGPORT:-5432}" PGUSER="${PGUSER:-postgres}"
Q() { psql --no-psqlrc -X -q -v ON_ERROR_STOP=1 -At "$@"; }

# ⛔ Cancelli: superuser, mai i ruoli di sistema, mai il database di sviluppo.
[[ "$(Q -d postgres -c "SELECT rolsuper FROM pg_roles WHERE rolname = current_user")" == "t" ]] \
  || { echo "⛔ Serve un superuser (collegato come $PGUSER)." >&2; exit 1; }
DEV_DB=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$REPO_ROOT/db/internal.env" ]]; then
  DEV_DB="$(sed -n 's/^PGDATABASE=//p; s/^DB_NAME=//p' "$REPO_ROOT/db/internal.env" | head -1)"
fi
for r in "${RUOLI[@]}"; do
  case "$r" in
    zeroerp_owner|zeroerp_job|zeroerp_app|zeroerp_log|postgres)
      echo "⛔ $r e' un ruolo di sistema: non si ritira." >&2; exit 1 ;;
  esac
done
for d in "${DB_DA_CANCELLARE[@]}"; do
  if [[ "$d" == "$DEV_DB" || "$d" == "postgres" || "$d" == template* ]]; then
    echo "⛔ $d non si cancella." >&2; exit 1
  fi
done

$ESEGUI && echo "══ ESECUZIONE" || echo "══ PROVA A VUOTO (niente viene cambiato; --esegui per farlo)"

# ── 1. I database da cancellare (irreversibile)
for d in "${DB_DA_CANCELLARE[@]}"; do
  if [[ -z "$(Q -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$d'")" ]]; then
    echo "── database $d: non c'e'"; continue
  fi
  echo "── database $d: da cancellare (proprietario $(Q -d postgres -c "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$d'"), $(Q -d postgres -c "SELECT pg_size_pretty(pg_database_size('$d'))"))"
  if $ESEGUI; then
    Q -d postgres -c "DROP DATABASE \"$d\" WITH (FORCE)"
    echo "   cancellato"
  fi
done

# ── 2. Per ogni ruolo: sessioni, proprieta', poi DROP OWNED su ogni database
DBS=$(Q -d postgres -c "SELECT datname FROM pg_database WHERE datallowconn ORDER BY 1")
FERMO=false
for r in "${RUOLI[@]}"; do
  if [[ -z "$(Q -d postgres -c "SELECT 1 FROM pg_roles WHERE rolname = '$r'")" ]]; then
    echo "── $r: non esiste (gia' ritirato)"; continue
  fi
  echo "── $r"
  n=$(Q -d postgres -c "SELECT count(*) FROM pg_stat_activity WHERE usename = '$r'")
  if [[ "$n" != "0" ]]; then echo "   ⛔ $n sessioni collegate come $r: fermare chi lo usa"; FERMO=true; continue; fi

  # La proprieta': oggetti (deptype 'o') in un database che NON si cancella, e database interi.
  ESCLUSI="'$(IFS=,; echo "${DB_DA_CANCELLARE[*]:-}" | sed "s/,/','/g")'"
  POSSIEDE=$(Q -d postgres -c "
    SELECT string_agg(coalesce(d.datname, '(cluster)') || ': ' || s.classid::regclass || ' x' || s.n, ', ')
      FROM (SELECT dbid, classid, count(*) AS n FROM pg_shdepend
             WHERE refobjid = '$r'::regrole AND deptype = 'o' GROUP BY 1, 2) s
      LEFT JOIN pg_database d ON d.oid = s.dbid
     WHERE coalesce(d.datname, '') NOT IN ($ESCLUSI)
       AND s.classid <> 'pg_default_acl'::regclass")
  DB_SUOI=$(Q -d postgres -c "SELECT string_agg(datname, ', ') FROM pg_database
                               WHERE datdba = '$r'::regrole AND datname NOT IN ($ESCLUSI)")
  if [[ -n "$POSSIEDE" || -n "$DB_SUOI" ]]; then
    echo "   ⛔ possiede ancora: ${POSSIEDE:-}${DB_SUOI:+ database: $DB_SUOI}"
    echo "      (DROP OWNED lo cancellerebbe: va guardato e riassegnato a mano)"
    FERMO=true; continue
  fi

  for d in $DBS; do
    if printf '%s\n' "${DB_DA_CANCELLARE[@]:-}" | grep -qx "$d"; then continue; fi
    dip=$(Q -d postgres -c "SELECT count(*) FROM pg_shdepend s JOIN pg_database x ON x.oid = s.dbid
                             WHERE x.datname = '$d' AND s.refobjid = '$r'::regrole")
    [[ "$dip" == "0" ]] && continue
    if $ESEGUI; then
      Q -d "$d" -c "DROP OWNED BY \"$r\""
      echo "   $d: $dip dipendenze tolte (privilegi e privilegi di default)"
    else
      Q -d "$d" -c "BEGIN; DROP OWNED BY \"$r\"; ROLLBACK;"
      echo "   $d: $dip dipendenze (privilegi e privilegi di default) — DROP OWNED provato e annullato"
    fi
  done

  if $ESEGUI; then
    Q -d postgres -c "DROP ROLE \"$r\""
    echo "   ✅ ruolo $r ritirato"
  else
    echo "   (con --esegui: DROP ROLE $r; le sue impostazioni per database spariscono con lui)"
  fi
done

$FERMO && { echo "⛔ Qualcosa ha fermato il ritiro: vedi sopra."; exit 3; }
if $ESEGUI && [[ -n "$DEV_DB" ]] && [[ -n "$(Q -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$DEV_DB'")" ]]; then
  if [[ -n "$(Q -d "$DEV_DB" -c "SELECT to_regclass('dbops.vw_processi_che_bypassano')")" ]]; then
    echo "── presidio dbops.vw_processi_che_bypassano su $DEV_DB (atteso: nessuna riga)"
    Q -d "$DEV_DB" -c "SELECT ruolo || ' ' || stato FROM dbops.vw_processi_che_bypassano"
  fi
fi
echo "✅ fatto"
