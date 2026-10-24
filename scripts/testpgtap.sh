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

# --check-automazioni: risponde a «su QUESTO database e' stata eseguita la
# passata delle AUTOMAZIONI (`--contexts=ci_apply`)?».
#   exit 0 = si'  ·  exit 1 = no  ·  exit 3 = non misurabile (DB irraggiungibile)
#
# ⭐ PERCHE' LA DOMANDA STA QUI e non in scripts/pgtap-baseline.sh: questo file
#   e' l'unico che sa come si RAGGIUNGE il database bersaglio — la catena
#   dell'env file (PGTAP_ENV_FILE, db/internal.env, backend/…), il mapping
#   DB_* -> PG* e la scelta dell'utente vivono tutti qui. Una seconda copia di
#   quella catena diverge, ed e' lo stesso motivo per cui il default del runner
#   non e' duplicato ma CHIESTO (--print-runner, qui sopra).
#
# ⭐ COME SI MISURA, e non e' un conteggio. I changeSet sotto
#   `90_end/ci_apply/` dichiarano `context: ci_apply`: Liquibase li esegue
#   SOLO quando quel contesto e' nell'invocazione. ⇒ La loro presenza nel
#   `databasechangelog` E' la passata, e la loro assenza e' la sua mancanza.
#   ⛔ Non si confrontano NUMERI di trigger fra due database: i nomi generati
#   dal framework non coincidono (portano un hash), e un totale e' una
#   fotografia — direbbe «diverso», non «mancante».
# ⚠️ Un `if` e non `[ … ] && MODO_CHECK=1`: con `set -e` attivo la forma corta
#   dipende da una clausola d'eccezione della shell, e qui non c'e' motivo di
#   appoggiarcisi.
MODO_CHECK=0
if [ "$1" = "--check-automazioni" ]; then
  MODO_CHECK=1
fi

TARGET="$1"

# ⚠️ In modalita' `--check-automazioni` non c'e' nessun file da risolvere:
#   il percorso si salta invece di inventare un bersaglio finto che lo
#   attraversi. L'env file, che serve a entrambe le modalita', si carica dopo.
if [ "$MODO_CHECK" -eq 0 ]; then
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
fi

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
#   (`scripts/ci-local.sh`: `zeroerp_ruoli`) crede di misurare quello e
#   misura SVILUPPO. Con `pgtap-baseline.sh --update` finirebbe per scrivere i
#   rossi di sviluppo dentro la baseline della CI, cioe' un metro sbagliato
#   dentro il file che esiste apposta per tenere il metro omogeneo.
#   ⭐ Quindi la scelta si fa a livello di FILE — un env file per database —
#   non variabile per variabile: cosi' host, porta, utente, password e database
#   restano un insieme coerente e non se ne puo' spostare mezzo.
#
#   Uso:
#     PGTAP_ENV_FILE=db/internal.ruoli.env PGTAP_BASELINE=db/pgtap/baseline-rossi-scratch.tsv \
#       scripts/pgtap-baseline.sh --update
#   (db/internal.ruoli.env: lo scratch del modello dei ruoli, `zeroerp_ruoli`,
#    utente zeroerp_owner.)
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

# --- la risposta a `--check-automazioni` ------------------------------------
# ⚠️ Si interroga con l'utente dell'ENV FILE (l'owner), non con quello del
#   runner: `databasechangelog` e' il registro del migratore, e il ruolo
#   applicativo puo' legittimamente non vederlo. Qui la domanda e' sul
#   DATABASE, non su cosa vede l'applicazione.
if [ "$MODO_CHECK" -eq 1 ]; then
  n=$(psql --no-psqlrc -X -A -t -v ON_ERROR_STOP=1 \
        -c "SELECT count(*) FROM databasechangelog
             WHERE filename LIKE '%90_end/ci_apply/%'" 2>/dev/null) || exit 3
  case "$n" in
    ''|*[!0-9]*) exit 3 ;;
    0)           exit 1 ;;
    *)           exit 0 ;;
  esac
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

# --- fuso della sessione: OSTILE a quello dell'azienda -----------------------
# (brief-be-db-fe-un-solo-fuso-aziendale, T-5.) Il giorno dell'applicazione e'
# quello dell'azienda (`script.fn_data_operativa()`), non quello della sessione.
# Se il test gira in una sessione che ha lo stesso giorno dell'azienda, un
# `CURRENT_DATE` o un `::date` su un istante che sfugge da' la risposta giusta
# per coincidenza: e' rosso solo nella finestra notturna, cioe' quasi mai.
#
# ⭐ Quindi la sessione gira in un fuso il cui giorno DIFFERISCE da quello
#   dell'azienda, scelto file per file fra due estremi:
#     Pacific/Kiritimati (+14)  se adesso il suo giorno non e' quello aziendale,
#     Pacific/Pago_Pago  (−11)  altrimenti.
#   Per qualunque fuso aziendale uno dei due differisce SEMPRE: con l'azienda a
#   offset o e l'ora aziendale h, Kiritimati ha lo stesso giorno solo per
#   h < 10+o, Pago Pago solo per h >= 11+o — le due condizioni non stanno
#   insieme. Un fuso fisso (+14 e basta) sarebbe ostile per mezza giornata:
#   il rosso dipenderebbe dall'ora della corsa.
# ⚠️ Si sceglie a ogni file, non una volta per corsa: una suite che attraversa
#   la mezzanotte aziendale cambia estremo a meta' strada.
# ⚠️ La domanda si fa al DATABASE, che e' la sede del fuso aziendale: una copia
#   del parametro qui divergerebbe al primo cambio.
# ⭐ `PGTZ` gia' impostato vince (per esempio `PGTZ=Europe/Rome` per riprodurre
#   un rosso nel fuso dell'azienda): libpq lo manda all'avvio della sessione, e
#   vince anche su un `ALTER ROLE … SET timezone`.
if [ -z "${PGTZ:-}" ]; then
  PGTZ=$(psql --no-psqlrc -X -A -t -v ON_ERROR_STOP=1 -c \
    "SELECT CASE WHEN (now() AT TIME ZONE 'Pacific/Kiritimati')::date
                      <> script.fn_data_operativa()
                 THEN 'Pacific/Kiritimati' ELSE 'Pacific/Pago_Pago' END" \
    2>/dev/null) || PGTZ=""
  if [ -z "$PGTZ" ]; then
    # Database senza il fuso aziendale, o irraggiungibile: il test fallira'
    # comunque per conto suo; qui si resta ostili alla meta' piu' probabile.
    PGTZ="Pacific/Kiritimati"
    echo "⚠️  fuso aziendale non leggibile: sessione su $PGTZ" >&2
  fi
  export PGTZ
fi

# pg_prove con path assoluto (funziona da qualsiasi CWD)
pg_prove "$FULL_PATH"
