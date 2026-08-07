#!/usr/bin/env bash
# Wrapper per pg_prove con internal.env
#
# Supporta test pgTAP sia da db/pgtap/ (test DB-layer storici) sia da
# backend/pgtap/ (test diagnostici lanciabili dal server backend).
#
# Uso:
#   da root del repo:
#     scripts/testpgtap.sh anagrafiche/soggetti-con-contatti.sql
#     scripts/testpgtap.sh backend/anagrafiche/test-fn-sync-auth-user-is-active-or-transizione.sql
#
# Risoluzione path:
#   - il prefisso esplicito 'backend/' forza backend/pgtap/
#   - il prefisso esplicito 'db/' forza db/pgtap/
#   - in mancanza di prefisso: auto-detect (prima db/pgtap, poi backend/pgtap)
#   - errore ambiguo se il file esiste in entrambi senza prefisso
#
# CON CHE UTENTE GIRA IL TEST — variabile PGTAP_RUNNER
#
#   PGTAP_RUNNER=owner   (default oggi) l'utente dell'env file, cioe' l'owner
#                        degli oggetti. ⚠️ L'owner NON e' soggetto alla RLS
#                        (salvo FORCE), quindi nessuna policy viene esercitata.
#   PGTAP_RUNNER=app     l'utente applicativo (PGTAP_APP_USER, default
#                        zeroerp_app): i test girano come gira l'applicazione,
#                        RLS attiva. La password arriva da ~/.pgpass — la
#                        PGPASSWORD dell'env file viene tolta apposta, altrimenti
#                        si tenterebbe la password dell'owner sull'utente app.
#
#   Esempi:
#     PGTAP_RUNNER=app scripts/testpgtap.sh vendite/test-promo-articoli-v1.sql
#     PGTAP_RUNNER=app scripts/pgtap-baseline.sh vendite
#
# ECCEZIONE PER FILE — marcatore `-- pgtap-runner: owner`
#
# Due categorie di test, e solo due, hanno diritto all'eccezione.
#
#   1. **Fanno DDL** (ALTER TABLE … FORCE ROW LEVEL SECURITY, CREATE TABLE
#      dbops.…) che il ruolo applicativo non puo' fare e non deve poter fare.
#      Non sono difetti: nei test RLS e' proprio il FORCE a rendere l'owner
#      soggetto alle policy, e l'identita' la simulano le GUC `app.*`, non il
#      ruolo di connessione.
#
#   2. **La fixture costruisce un mondo che l'operatore non deve vedere.**
#      Un test sulla separazione fra emittenti deve creare i documenti
#      dell'emittente ALTRUI: nessun operatore puo' farlo, ed e' esattamente
#      cio' che la policy deve impedirgli. Stessa natura della categoria 1 —
#      il test allestisce la scena e poi la osserva sotto restrizione.
#      (Aggiunta il 2026-08-07, brief §26.)
#
# ⚠️ Quello che NON e' un'eccezione: un `permesso negato` o una violazione di
# policy che l'applicazione non incontrerebbe mai. Li' il difetto e' nella
# fixture — scrive dove l'applicazione non scrive — oppure nella policy, e il
# marcatore lo nasconderebbe invece di risolverlo.
#
# Quei file dichiarano in intestazione, entro le prime 80 righe:
#
#     -- pgtap-runner: owner
#     -- pgtap-runner-motivo: <perche', in chiaro>
#
# e restano sull'owner anche con PGTAP_RUNNER=app. Il marcatore va accanto al
# test (lo segue nelle rinomine) e pretende la ragione scritta: e' un'eccezione
# motivata, non un interruttore per far sparire un permesso mancante.
#
# Censimento dei marcati:
#   grep -rlE '^-- pgtap-runner:[[:space:]]*owner' db/pgtap/*/*.sql

set -e

# Cartella dello script (ZeroErp/scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Root del progetto (ZeroErp)
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DB_PGTAP_DIR="$ROOT_DIR/db/pgtap"
BE_PGTAP_DIR="$ROOT_DIR/backend/pgtap"

# Controllo parametro
if [ $# -lt 1 ]; then
  cat >&2 <<EOF
Uso: scripts/testpgtap.sh [db/|backend/]schema/file.sql

Esempi:
  scripts/testpgtap.sh anagrafiche/soggetti-con-contatti.sql
  scripts/testpgtap.sh backend/anagrafiche/test-fn-sync-auth-user-is-active-or-transizione.sql
  scripts/testpgtap.sh db/anagrafiche/test-sync-auth-user-is-active.sql
EOF
  exit 1
fi

TARGET="$1"

# Normalizza prefissi superflui: pgtap/, db/pgtap/, backend/pgtap/
case "$TARGET" in
  db/pgtap/*)      TARGET="db/${TARGET#db/pgtap/}" ;;
  backend/pgtap/*) TARGET="backend/${TARGET#backend/pgtap/}" ;;
  pgtap/*)         TARGET="${TARGET#pgtap/}" ;;
esac

# Determina radice pgTAP e path relativo al suo interno
case "$TARGET" in
  backend/*)
    PGTAP_ROOT="$BE_PGTAP_DIR"
    REL_PATH="${TARGET#backend/}"
    BASE_DIR="$ROOT_DIR/backend"
    ;;
  db/*)
    PGTAP_ROOT="$DB_PGTAP_DIR"
    REL_PATH="${TARGET#db/}"
    BASE_DIR="$ROOT_DIR/db"
    ;;
  *)
    # Auto-detect: prima db/pgtap, poi backend/pgtap
    IN_DB=0
    IN_BE=0
    [ -f "$DB_PGTAP_DIR/$TARGET" ] && IN_DB=1
    [ -f "$BE_PGTAP_DIR/$TARGET" ] && IN_BE=1

    if [ "$IN_DB" -eq 1 ] && [ "$IN_BE" -eq 1 ]; then
      echo "Errore: '$TARGET' presente sia in db/pgtap/ che in backend/pgtap/." >&2
      echo "Usa il prefisso esplicito 'db/' o 'backend/' per disambiguare." >&2
      exit 2
    elif [ "$IN_DB" -eq 1 ]; then
      PGTAP_ROOT="$DB_PGTAP_DIR"
      BASE_DIR="$ROOT_DIR/db"
    elif [ "$IN_BE" -eq 1 ]; then
      PGTAP_ROOT="$BE_PGTAP_DIR"
      BASE_DIR="$ROOT_DIR/backend"
    else
      echo "Errore: '$TARGET' non trovato ne' in db/pgtap/ ne' in backend/pgtap/." >&2
      exit 2
    fi
    REL_PATH="$TARGET"
    ;;
esac

# Carica le variabili PG* per pg_prove.
# Priorita':
#   1) db/internal.env       (server DB, fonte primaria)
#   2) backend/internal.env  (server backend con env pgTAP dedicato)
#   3) backend/.env          (server backend, usa DB_* -> mappa su PG*)
ENV_FILE=""
ENV_STYLE=""   # "pg" = variabili PG* native, "django" = DB_* da mappare
if [ -f "$ROOT_DIR/db/internal.env" ]; then
  ENV_FILE="$ROOT_DIR/db/internal.env"
  ENV_STYLE="pg"
elif [ -f "$ROOT_DIR/backend/internal.env" ]; then
  ENV_FILE="$ROOT_DIR/backend/internal.env"
  ENV_STYLE="pg"
elif [ -f "$ROOT_DIR/backend/.env" ]; then
  ENV_FILE="$ROOT_DIR/backend/.env"
  ENV_STYLE="django"
else
  echo "Errore: nessun env file trovato (cercati: db/internal.env, backend/internal.env, backend/.env)." >&2
  exit 3
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Mapping DB_* -> PG* quando sorgente e' backend/.env (stile Django)
if [ "$ENV_STYLE" = "django" ]; then
  export PGHOST="${PGHOST:-${DB_HOST:-}}"
  export PGPORT="${PGPORT:-${DB_PORT:-}}"
  export PGDATABASE="${PGDATABASE:-${DB_NAME:-}}"
  export PGUSER="${PGUSER:-${DB_USER:-}}"
  export PGPASSWORD="${PGPASSWORD:-${DB_PASSWORD:-}}"

  if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGDATABASE" ]; then
    echo "Errore: DB_HOST/DB_USER/DB_NAME non definite in $ENV_FILE." >&2
    exit 3
  fi
fi

FULL_PATH="$PGTAP_ROOT/$REL_PATH"
if [ ! -f "$FULL_PATH" ]; then
  echo "Errore: file non trovato: $FULL_PATH" >&2
  exit 2
fi

# --- scelta dell'utente di connessione ---------------------------------------
# Default owner (comportamento storico). Con PGTAP_RUNNER=app si passa all'utente
# applicativo, tranne per i file che dichiarano il marcatore in intestazione.
PGTAP_RUNNER="${PGTAP_RUNNER:-owner}"
PGTAP_APP_USER="${PGTAP_APP_USER:-zeroerp_app}"

case "$PGTAP_RUNNER" in
  owner) ;;
  app)
    if head -n 80 "$FULL_PATH" | grep -qE '^--[[:space:]]*pgtap-runner:[[:space:]]*owner[[:space:]]*$'; then
      # Eccezione dichiarata nel file: resta sull'owner, e lo dice.
      motivo=$(head -n 80 "$FULL_PATH" \
                 | grep -m1 -E '^--[[:space:]]*pgtap-runner-motivo:' \
                 | sed -E 's/^--[[:space:]]*pgtap-runner-motivo:[[:space:]]*//')
      if [ -z "$motivo" ]; then
        echo "Errore: $REL_PATH dichiara 'pgtap-runner: owner' senza 'pgtap-runner-motivo'." >&2
        echo "L'eccezione va motivata nel file." >&2
        exit 4
      fi
      echo "ℹ️  $REL_PATH resta su owner ($PGUSER): $motivo" >&2
    else
      export PGUSER="$PGTAP_APP_USER"
      # La password dell'owner non vale per l'utente app: si lascia decidere a
      # ~/.pgpass. Senza questo unset, PGPASSWORD dell'env file vincerebbe.
      unset PGPASSWORD
    fi
    ;;
  *)
    echo "Errore: PGTAP_RUNNER='$PGTAP_RUNNER' non valido (attesi: owner, app)." >&2
    exit 4
    ;;
esac

# pg_prove con path assoluto (funziona da qualsiasi CWD)
pg_prove "$FULL_PATH"
