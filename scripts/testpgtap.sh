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
#   PGTAP_RUNNER=app     ⭐ **IL DEFAULT dal 2026-08-07.** L'utente applicativo
#                        (PGTAP_APP_USER, default zeroerp_app): i test girano
#                        come gira l'applicazione, con la RLS attiva. La password
#                        arriva da ~/.pgpass — la PGPASSWORD dell'env file viene
#                        tolta apposta, altrimenti si tenterebbe la password
#                        dell'owner sull'utente app.
#   PGTAP_RUNNER=owner   l'utente dell'env file, cioe' l'owner degli oggetti.
#                        ⚠️ L'owner NON e' soggetto alla RLS (salvo FORCE):
#                        girando cosi' NESSUNA policy viene esercitata. Serve per
#                        confronti diagnostici — «questo rosso dipende dal ruolo
#                        o no?» — non per validare una modifica.
#
# ⭐ La commutazione del default e' l'obiettivo per cui esiste
#    brief-db-pgtap-runner-rls-baseline.md, ed e' arrivata quando il divario fra
#    i due runner e' sceso a ZERO (§30): nessun file si comporta peggio come
#    applicazione. Prima di allora girare come app avrebbe solo prodotto rossi
#    che non erano difetti.
#
#   Esempi:
#     PGTAP_RUNNER=app scripts/testpgtap.sh vendite/test-promo-articoli-v1.sql
#     PGTAP_RUNNER=app scripts/pgtap-baseline.sh vendite
#
# ECCEZIONE PER FILE — marcatore `-- pgtap-runner: owner`
#
# IL CRITERIO, UNO SOLO:
#
#     ⭐ il SOGGETTO del test non e' raggiungibile dall'applicazione.
#
# Non «il test non passa come app» — quello e' quasi sempre un difetto. È che
# la cosa che il test collauda **non sta sul percorso applicativo**, quindi
# fingere di essere l'applicazione non lo rende piu' fedele: lo rende muto.
#
# Le tre forme incontrate finora (brief §24.3, §26.3, §29.3-bis):
#
#   1. **Il test fa DDL.** ALTER TABLE … FORCE ROW LEVEL SECURITY, CREATE TABLE
#      in dbops, CREATE TRIGGER per fault injection, ADD CONSTRAINT temporaneo.
#      Nei test RLS e' proprio il FORCE a rendere l'owner soggetto alle policy,
#      e l'identita' la simulano le GUC `app.*`, non il ruolo di connessione.
#
#   2. **La fixture costruisce un mondo che l'operatore non deve vedere.**
#      Un test sulla separazione fra emittenti deve creare i documenti
#      dell'emittente ALTRUI: nessun operatore puo' farlo, ed e' esattamente
#      cio' che la policy deve impedirgli.
#
#   3. **Il test collauda un guard che solo uno scrittore privilegiato puo' far
#      scattare.** I guard su pratiche.workflow_definizioni difendono da chi
#      scrive DIRETTAMENTE (una migrazione, un job, qualcuno con psql): le
#      transizioni che vietano — «PUBBLICATA -> BOZZA», cambio di versione su
#      una pubblicata — nessun entry point le offre, quindi l'applicazione non
#      puo' nemmeno tentarle. Stessa forma per le tabelle che solo le
#      migrazioni popolano (ui.dashboard_definizione: nessuno ci scrive a
#      runtime, ne' una funzione DB ne' il backend).
#
# ⛔ COSA IL CRITERIO ESCLUDE — e senza questo elenco e' una scusa, non un
#    criterio. Tutti e tre i casi sono successi davvero, e nessuno e' stato
#    marcato:
#
#   * `permesso negato` su una tabella dove l'applicazione **scrive davvero**
#     -> o manca un GRANT (difetto di prodotto) o la fixture scrive dove
#     l'applicazione non scrive (difetto di test). Il marcatore lo nasconde;
#   * **violazione di policy RLS** su un documento dell'emittente di chi agisce
#     -> difetto di fixture: tre file omettevano l'emittente su
#     vendite.commesse, e su 58 righe reali zero ce l'hanno a NULL (§26.3, C1);
#   * un errore che dipende da **come e' scritta la query**, non da chi la
#     esegue -> due file creavano fattura e righe nella stessa CTE, che la
#     policy non puo' soddisfare per via della snapshot condivisa (§26.2).
#     Si riscrive la query, non si cambia utente.
#
# In una riga: **se l'applicazione quella cosa la fa, il marcatore e' sbagliato.**
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
#   grep -rlE '^-- pgtap-runner:[[:space:]]*owner' --include='*.sql' -r db/pgtap

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

# --print-runner: stampa il runner che si risolverebbe e esce. Serve a
# scripts/pgtap-baseline.sh per NON avere un default suo: il valore di
# default deve stare in un posto solo, altrimenti i due divergono — ed e'
# successo davvero il 2026-08-07, con la baseline etichettata "owner"
# mentre la corsa andava come app.
if [ "$1" = "--print-runner" ]; then
  echo "${PGTAP_RUNNER:-app}"
  exit 0
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
#   0) PGTAP_ENV_FILE        (override esplicito — vedi sotto)
#   1) db/internal.env       (server DB, fonte primaria)
#   2) backend/internal.env  (server backend con env pgTAP dedicato)
#   3) backend/.env          (server backend, usa DB_* -> mappa su PG*)
#
# ── ⛔ PERCHE' SERVE UN OVERRIDE DI FILE, E NON BASTA `PGDATABASE=...` ──────
#   Il file viene caricato con `set -a; source`, quindi le sue righe
#   SOVRASCRIVONO l'ambiente: `PGDATABASE=altro scripts/testpgtap.sh …` non
#   sposta niente, e i test girano lo stesso sul database nominato nel file.
#   ⚠️ E' un fallimento SILENZIOSO, ed e' il peggiore che potesse capitare qui:
#   chi vuole misurare il database scratch della replica CI
#   (`scripts/ci-local.sh`, `CI_DB=zeroerp_ci`) crede di misurare quello e
#   misura SVILUPPO. Con `pgtap-baseline.sh --update` finirebbe per scrivere i
#   rossi di sviluppo dentro la baseline della CI, cioe' un metro sbagliato
#   dentro il file che esiste apposta per tenere il metro omogeneo.
#   ⭐ Quindi la scelta si fa a livello di FILE — un env file per database —
#   non variabile per variabile: cosi' host, porta, utente, password e database
#   restano un insieme coerente e non se ne puo' spostare mezzo.
#
#   Uso:
#     PGTAP_ENV_FILE=db/internal.ci.env scripts/pgtap-baseline.sh --update
ENV_FILE=""
ENV_STYLE=""   # "pg" = variabili PG* native, "django" = DB_* da mappare
if [ -n "${PGTAP_ENV_FILE:-}" ]; then
  # Path relativo alla root del repo o assoluto, indifferentemente.
  case "$PGTAP_ENV_FILE" in
    /*) ENV_FILE="$PGTAP_ENV_FILE" ;;
    *)  ENV_FILE="$ROOT_DIR/$PGTAP_ENV_FILE" ;;
  esac
  if [ ! -f "$ENV_FILE" ]; then
    echo "Errore: PGTAP_ENV_FILE='$PGTAP_ENV_FILE' non esiste (risolto in $ENV_FILE)." >&2
    exit 3
  fi
  # Stile: "django" se il file parla DB_* invece che PG*.
  if grep -qE '^[[:space:]]*DB_NAME=' "$ENV_FILE" && ! grep -qE '^[[:space:]]*PGDATABASE=' "$ENV_FILE"; then
    ENV_STYLE="django"
  else
    ENV_STYLE="pg"
  fi
elif [ -f "$ROOT_DIR/db/internal.env" ]; then
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
PGTAP_RUNNER="${PGTAP_RUNNER:-app}"
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
