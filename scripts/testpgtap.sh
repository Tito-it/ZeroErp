#!/usr/bin/env bash
# Wrapper per pg_prove con internal.env
# Uso:
#   da root del repo:  scripts/testpgtap.sh anagrafiche/soggetti-con-contatti.sql

set -e

# Cartella dello script (ZeroErp/scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Root del progetto (ZeroErp)
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# Cartella db (ZeroErp/db)
DB_DIR="$ROOT_DIR/db"

# Vai in ZeroErp/db
cd "$DB_DIR"

# Carica le variabili PG* da db/internal.env
set -a
source internal.env
set +a

# Controllo parametro
if [ $# -lt 1 ]; then
  echo "Uso: scripts/testpgtap.sh schema/file.sql (relativo a pgtap/)"
  echo "Esempio: scripts/testpgtap.sh anagrafiche/soggetti-con-contatti.sql"
  exit 1
fi

TARGET="$1"

# Normalizza: se uno scrive per sbaglio con prefisso db/ o pgtap/, lo ripuliamo
case "$TARGET" in
  db/*)    TARGET="${TARGET#db/}" ;;
esac

case "$TARGET" in
  pgtap/*) TARGET="${TARGET#pgtap/}" ;;
esac

# Esegue pg_prove sul file richiesto
pg_prove "pgtap/$TARGET"