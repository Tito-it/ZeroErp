#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: eseguire TUTTI gli smoke di backend/scripts/tests/ e distinguere in un
#        colpo d'occhio un esito non-verde NUOVO da uno gia' noto.
#        Due famiglie, un registro solo:
#        - `smoke-*.py`, in-process (`manage-env.sh shell <`), in transazione
#          ritirata: non lasciano niente;
#        - `smoke-test-*.sh`, via HTTP contro il backend in esecuzione
#          (BASE_URL), con l'utente degli smoke di `backend/env.sh`
#          (`SMOKE_USER`, `dev.smoke`). ⚠️ Questi SCRIVONO sul database di
#          sviluppo (documenti di prova, sull'emittente attivo dell'utente
#          degli smoke) e lasciano quello che creano.
#        Fino al 2026-10-12 il perimetro era solo `smoke-*.py`: i 36 bash non li
#        lanciava nessuno, e quel giorno il primo giro completo ne ha trovati
#        rossi piu' della meta' (contratti API cambiati sotto, id cablati).
#
# IL PROBLEMA CHE RISOLVE. Gli smoke non li lancia nessuno: non li raccoglie il
# runner Django (stanno in scripts/tests/, hanno il trattino nel nome e il
# pattern di scoperta e' `test*.py`) e non li esegue la CI. Ognuno documenta
# solo come si lancia DA SOLO. ⇒ Marciscono in silenzio.
# Misurato il 2026-08-27: SEI degli undici erano rotti da un giorno — la colonna
# `vendite.attivita_fatturabili.fatturato` era diventata GENERATED e le fixture
# continuavano a scriverla. Il difetto e' arrivato da un cantiere che quei file
# non li ha nemmeno aperti, ed e' esattamente cio' che un test dovrebbe
# impedire.
#
# ⛔ IL CODICE DI USCITA NON DICE LA VERITA', ed e' la ragione per cui questo
#    script non e' un `for` con `&&`. `smoke-fatturazione-render-stampa` stampa
#    «=== ESITO: FALLITO ===» e esce 0. Si classifica dall'OUTPUT.
#
# ⚠️ GLI ESITI SONO TRE, non due. Oltre a verde e rosso c'e' SENZA_MATERIA: lo
#    script si ferma su una precondizione assente (`raise SystemExit("Nessun
#    billing account: smoke impossibile.")`). Non e' un difetto del codice ed e'
#    giusto che lo dichiari — ma la sua copertura quel giorno vale ZERO, non
#    "parziale", e va vista. Tenerlo insieme ai rossi lo nasconderebbe; tenerlo
#    insieme ai verdi sarebbe una bugia.
#
# COME FUNZIONA. Un file di baseline committato elenca i non-verdi NOTI:
#   - non-verde presente in baseline -> atteso, silenzio
#   - non-verde NON in baseline      -> REGRESSIONE, exit 1
#   - file in baseline ora verde     -> RIENTRATO, va tolto dalla baseline
#
# ⚠️ La baseline NON e' una lista di eccezioni permanenti: e' un registro di
#    debito e deve calare. Una suite con molti rossi noti insegna a ignorare il
#    rosso.
#
# ⚠️ E QUESTI SMOKE LEGGONO IL DATABASE DI SVILUPPO, con dati veri. Alcuni si
#    scelgono un soggetto esistente come template: se l'ambiente si muove sotto,
#    il rosso e' della fixture, non del codice. La causa registrata serve a
#    triagiare senza riaprire ogni file.
#
# USO
#   scripts/smoke-baseline.sh                      # tutti
#   scripts/smoke-baseline.sh fattura-scadenze     # solo quelli col nome dato
#   scripts/smoke-baseline.sh --update             # rigenera la baseline
#   scripts/smoke-baseline.sh --update fattura     # rigenera solo quei file
#
#   SMOKE_TIMEOUT=600 scripts/smoke-baseline.sh    # default 300s per file
#
# EXIT CODE
#   0 = nessuna regressione (i rientri sono solo segnalati)
#   1 = almeno un non-verde nuovo
#   2 = errore d'uso
#
# Tempo (2026-10-13, freni allentati in sviluppo): ~5 minuti e mezzo il giro
# intero. `c9-fatturazione-parte-alta` ne prende quasi due da solo (aspetta i
# worker di systemd, per scelta: prova il percorso vero), e dal 2026-10-13 e'
# ESCLUSO dal giro normale — non fa rollback ed emette fatture: si lancia per
# nome (`scripts/smoke-baseline.sh c9`, con SMOKE_C9_COMPETENZA).
#
# GLI SMOKE BASH. Login UNO per il giro (`smoke-login.sh`, SMOKE_TOKEN), rinnovato
# quando sta per scadere: ogni smoke e' un processo a se', e un login fatto
# dentro uno smoke non passa al successivo — senza il rinnovo qui, dopo dieci
# minuti ogni smoke rifarebbe il suo login e il freno dei login (429) fermerebbe
# il giro. Gli smoke che provano il login VERO lo fanno comunque, e c'e' anche
# il freno delle RICERCHE (30/min per IP, DJANGO_API_SEARCH_THROTTLE_RATE),
# che smoke consecutivi pieni di lookup raggiungono: su un 429 lo script
# aspetta e riprova una volta (LIMITE_RICHIESTE se non basta).
# ⚠️ Esclusi, e stampati come tali (mai in silenzio): vedi `escluso_perche`.
# ------------------------------------------------------------

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SMOKE_DIR="$ROOT_DIR/backend/scripts/tests"
BASELINE="${SMOKE_BASELINE:-$SMOKE_DIR/baseline-smoke.tsv}"
TIMEOUT="${SMOKE_TIMEOUT:-300}"

UPDATE=0
FILTRI=()
for arg in "$@"; do
  case "$arg" in
    --update) UPDATE=1 ;;
    -h|--help) awk 'NR>1 && !/^#/{exit} NR>1' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    -*) echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
    *) FILTRI+=("$arg") ;;
  esac
done

# Perimetro. ⚠️ `find`, non un glob: se un giorno gli smoke finissero in una
#   sottocartella, un glob a un livello solo direbbe «tutto a posto» quando in
#   realta' non ha guardato.
#   `smoke-test-*.sh` e non `smoke-*.sh`: `smoke-login.sh` non e' un test.
FILES=$(find "$SMOKE_DIR" -maxdepth 2 \( -name 'smoke-*.py' -o -name 'smoke-test-*.sh' \) \
          -not -path '*/archive/*' | sort)
if [ ${#FILTRI[@]} -gt 0 ]; then
  pat=$(printf '%s\n' "${FILTRI[@]}" | paste -sd'|')
  FILES=$(echo "$FILES" | grep -E "$pat")
  [ -z "$FILES" ] && { echo "Nessuno smoke corrisponde a: ${FILTRI[*]}" >&2; exit 2; }
fi
TOT=$(echo "$FILES" | grep -c '')

# Scopo: dice com'e' andato UNO smoke leggendo cio' che ha stampato.
#        L'ordine dei rami e' il contratto: un file che dichiara FALLITO e
#        stampa anche un traceback e' un'ASSERZIONE fallita, non un errore.
classifica() {
  local out="$1"
  if echo "$out" | grep -qE '=== (ESITO: )?TUTT[IO] (VERDE|I TEST OK)|TUTTO VERDE'; then
    echo "VERDE"; return
  fi
  if echo "$out" | grep -qE 'ESITO: FALLITO|^ *FAIL '; then
    if echo "$out" | grep -qiE 'colonna generata|non DEFAULT'; then echo "SCHEMA_DERIVATO"
    elif echo "$out" | grep -qiE 'oltre la soglia|scegliere una fattura|gia. (numerat|emess)'; then echo "FIXTURE_DERIVATA"
    else echo "ASSERZIONE"; fi
    return
  fi
  if echo "$out" | grep -qiE 'colonna generata|non DEFAULT'; then echo "SCHEMA_DERIVATO"; return; fi
  if echo "$out" | grep -q 'Traceback (most recent call last)'; then echo "ERRORE"; return; fi
  if echo "$out" | grep -q '__TIMEOUT__'; then echo "TIMEOUT"; return; fi
  # Nessun verde, nessun fallimento, nessuna eccezione: si e' fermato prima di
  # asserire — precondizione assente. Copertura di quel giro: zero.
  echo "SENZA_MATERIA"
}

# Scopo: dice com'e' andato UNO smoke BASH. Il suo codice di uscita qui e'
#        affidabile (`set -e`, contatore FAIL), ma da solo non distingue un rosso
#        da uno smoke che non e' arrivato ad asserire: si legge anche l'output.
#        L'ordine dei rami e' il contratto: un FAIL e' un'asserzione anche se
#        poi lo smoke si ferma.
classifica_sh() {
  local out rc="$2"
  # I colori stanno PRIMA di «FAIL» (`\033[0;31mFAIL`): senza toglierli nessun
  # rosso e' riconosciuto, e lo smoke cade sul ramo del codice d'uscita.
  out=$(printf '%s' "$1" | sed 's/\x1b\[[0-9;]*m//g; s/\\033\[[0-9;]*m//g')
  if echo "$out" | grep -q '__TIMEOUT__'; then echo "TIMEOUT"; return; fi
  if echo "$out" | grep -qE 'HTTP 429|throttled'; then echo "LIMITE_RICHIESTE"; return; fi
  # «FAIL <cosa>», non «FAIL:  0»: quello e' il contatore di un riepilogo verde.
  if echo "$out" | grep -qE '^ *FAIL [^:]'; then echo "ASSERZIONE"; return; fi
  # «non conclusivo», «Setup fallito: nessun …»: precondizione assente. ⚠️ Non
  # «nessun … disponibile» da solo: e' anche il SKIP di un passo dentro uno
  # smoke che per il resto e' verde.
  if echo "$out" | grep -qiE 'non conclusivo|setup fallito'; then
    echo "SENZA_MATERIA"; return
  fi
  # «Risultato: N OK, M FAIL, K SKIP» con K > 0: i passi saltati sono copertura
  # zero, e chiamarlo verde nasconderebbe proprio la parte che non gira (es.
  # /emetti/ senza modello di documento: il push del contratto non parte mai).
  if echo "$out" | grep -qE 'Risultato:.*[1-9][0-9]* SKIP'; then echo "PARZIALE"; return; fi
  if [ "$rc" -eq 0 ]; then echo "VERDE"; return; fi
  echo "ERRORE"   # uscito storto senza dire perche' (es. variabile non assegnata)
}

# Scopo: il motivo per cui uno smoke non si lancia in questo ambiente, o niente.
#        Un escluso si stampa: un file che sparisce dal giro senza dirlo e' un
#        verde finto.
escluso_perche() {
  case "$(basename "$1")" in
    smoke-test-ai-assistant.sh)
      [ "${AI_PROVIDER:-mock}" != "mock" ] &&
        echo "vuole AI_PROVIDER=mock, l'ambiente ha '${AI_PROVIDER}': chiamerebbe il modello vero" ;;
    smoke-c9-fatturazione-parte-alta.py)
      # ⛔ NON fa rollback (decisione di Tid, 2026-10-13): approva, EMETTE
      #    fatture, consuma la numerazione fiscale. Nel giro di ogni notte o
      #    emetterebbe fatture su dbdev, o — mese gia' lavorato — girerebbe a
      #    vuoto e direbbe verde. Si lancia solo chiamandolo per nome, su una
      #    competenza scelta (SMOKE_C9_COMPETENZA).
      [[ " ${FILTRI[*]-} " != *c9* ]] &&
        echo "non fa rollback (emette fatture): solo per nome, 'scripts/smoke-baseline.sh c9' con SMOKE_C9_COMPETENZA" ;;
  esac
}

# Scopo: un SMOKE_TOKEN che valga ancora almeno 4 minuti (uno smoke lungo).
#        Il login vero lo fa `smoke-login.sh`, una volta, e qui si rifa' solo
#        quando il token sta per scadere.
token_fresco() {
  local resto
  resto=$(python3 -c "
import base64, json, sys, time
try:
    p = sys.argv[1].split('.')[1]; p += '=' * (-len(p) % 4)
    print(int(json.loads(base64.urlsafe_b64decode(p))['exp'] - time.time()))
except Exception:
    print(0)
" "${SMOKE_TOKEN:-}")
  [ "$resto" -gt 240 ] && return 0
  local riga
  local errore
  errore=$(mktemp)
  riga=$(cd "$ROOT_DIR/backend" && ./scripts/tests/smoke-login.sh 2>"$errore") || riga=""
  if [ -z "$riga" ]; then
    attendi_freno "$(cat "$errore")"   # il freno dei login, poi un secondo tentativo
    riga=$(cd "$ROOT_DIR/backend" && ./scripts/tests/smoke-login.sh 2>/dev/null) || riga=""
  fi
  rm -f "$errore"
  [ -n "$riga" ] && eval "$riga"
}

# Scopo: aspetta quanto chiede il freno (429): «Expected available in N
#        seconds», piu' un margine; 75 se il server non lo dice, mai oltre 300.
#        Un'attesa fissa non basta: il freno dei login si somma fra smoke che
#        fanno il login vero (core, email-auth).
ATTESA_FRENO=0      # secondi d'attesa sul freno, nel giro (vedi TEMPI)
attendi_freno() {
  local secondi
  secondi=$(printf '%s' "${1:-}" | grep -oE 'available in [0-9]+' | grep -oE '[0-9]+' | tail -1)
  secondi=$(( ${secondi:-70} + 5 ))
  (( secondi > 300 )) && secondi=300
  ATTESA_FRENO=$(( ATTESA_FRENO + secondi ))
  sleep "$secondi"
}

# Gli smoke bash leggono utente, password e secondo fattore da `backend/env.sh`,
# e anche uno smoke `.py` legge l'utente da li' (`smoke-c9-…`, SMOKE_USER dal
# 2026-10-18). ⛔ Si carica SEMPRE: fino al 2026-10-26 si caricava solo se nel
# giro c'era un bash, e `smoke-baseline.sh c9` falliva sull'utente mancante.
set -a; source "$ROOT_DIR/backend/env.sh" >/dev/null 2>&1; set +a

ESCLUSI=""
# TEMPI: una riga per smoke, «secondi attesa_freno nome». Serve a scegliere sui
# numeri come rendere il giro piu' corto (2026-10-13: un giro dei soli bash
# durava ~40 minuti, e uno smoke che nessuno ha tempo di lanciare marcisce).
TEMPI=$(mktemp); INIZIO_GIRO=$SECONDS
# L'output di ogni smoke NON verde resta su file: un rosso del giro completo che
# da solo e' verde (dipende da cio' che gira prima) senza il suo output non si
# diagnostica. SMOKE_LOG_DIR per sceglierla.
LOG_DIR="${SMOKE_LOG_DIR:-${TMPDIR:-/tmp}/smoke-baseline-$(date +%Y%m%d-%H%M%S)}"
CORRENTE=$(mktemp); NOTI=$(mktemp); ATTUALI=$(mktemp)
trap 'rm -f "$CORRENTE" "$NOTI" "$ATTUALI" "$TEMPI"' EXIT

echo "smoke baseline — $TOT file (timeout ${TIMEOUT}s ciascuno)"
echo
n=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$((n+1)); rel=$(basename "$f")
  printf '\r  %d/%d  %-52.52s' "$n" "$TOT" "$rel" >&2
  inizio_file=$SECONDS; attesa_prima=$ATTESA_FRENO
  perche=$(escluso_perche "$f")
  if [ -n "$perche" ]; then ESCLUSI+="   $rel — $perche"$'\n'; continue; fi
  if [[ "$f" == *.sh ]]; then
    for tentativo in 1 2; do
      token_fresco
      out=$(cd "$ROOT_DIR/backend" && timeout "$TIMEOUT" bash "$f" </dev/null 2>&1); rc=$?
      [ $rc -eq 124 ] && out+=$'\n__TIMEOUT__'
      if [ $tentativo -eq 1 ] && echo "$out" | grep -qE 'HTTP 429|throttled'; then
        attendi_freno "$out"; continue
      fi
      break
    done
    esito=$(classifica_sh "$out" "$rc")
  else
    out=$(cd "$ROOT_DIR/backend" && timeout "$TIMEOUT" ./manage-env.sh shell < "$f" 2>&1; [ $? -eq 124 ] && echo __TIMEOUT__)
    esito=$(classifica "$out")
  fi
  printf '%d %d %s\n' $(( SECONDS - inizio_file )) $(( ATTESA_FRENO - attesa_prima )) "$rel" >> "$TEMPI"
  [ "$esito" = "VERDE" ] && continue
  mkdir -p "$LOG_DIR" && printf '%s\n' "$out" > "$LOG_DIR/${rel}.log"
  printf '%s\t%s\n' "$rel" "$esito" >> "$CORRENTE"
done <<< "$FILES"
printf '\r%*s\r' 70 '' >&2
# Tempi: i piu' lenti e i totali (durata comprensiva dell'attesa sul freno).
if [ -s "$TEMPI" ]; then
  echo "⏱  Tempi — giro $(( SECONDS - INIZIO_GIRO ))s, di cui attesa sul freno ${ATTESA_FRENO}s. I piu' lenti:"
  sort -rn "$TEMPI" | head -8 | awk '{ printf "   %5ss  (freno %ss)  %s\n", $1, $2, $3 }'
  echo
fi
[ -d "$LOG_DIR" ] && { echo "📄 Output dei non-verdi: $LOG_DIR"; echo; }
if [ -n "$ESCLUSI" ]; then
  echo "⚠️  ESCLUSI in questo ambiente (non contano ne' verdi ne' rossi):"
  printf '%s' "$ESCLUSI"; echo
fi

sort -o "$CORRENTE" "$CORRENTE"
NONVERDI=$(grep -c '' "$CORRENTE" || true)

if [ "$UPDATE" -eq 1 ]; then
  TMP=$(mktemp)
  if [ ${#FILTRI[@]} -eq 0 ]; then
    cp "$CORRENTE" "$TMP"
  else
    # Aggiornamento parziale: si sostituiscono SOLO le righe dei file eseguiti.
    grep -v '^#' "$BASELINE" 2>/dev/null > "$TMP"
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      # ⚠️ `|| true`: togliere l'ULTIMA riga lascia grep senza output, che
      #    esce 1 — con `&& mv` la riga restava, e l'ultimo non-verde non
      #    rientrava mai (2026-10-28).
      { grep -v "^$(basename "$f")"$'\t' "$TMP" || true; } > "$TMP.f"
      mv "$TMP.f" "$TMP"
    done <<< "$FILES"
    cat "$CORRENTE" >> "$TMP"; sort -o "$TMP" "$TMP"
  fi
  { echo "# smoke non-verdi noti — rigenerato da scripts/smoke-baseline.sh"
    echo "# ⚠️ registro di DEBITO, non lista di eccezioni: deve calare."
    cat "$TMP"; } > "$BASELINE"
  rm -f "$TMP"
  echo "Baseline aggiornata: $BASELINE ($(grep -vc '^#' "$BASELINE") non-verdi noti)"
  exit 0
fi

if [ ! -f "$BASELINE" ]; then
  echo "Baseline assente ($BASELINE)." >&2
  echo "Generala con: scripts/smoke-baseline.sh --update" >&2
  exit 2
fi

# Confronto sul solo NOME: la causa e' informativa, non identitaria — lo stesso
# file puo' cambiare causa restando non-verde, e non e' una regressione.
if [ ${#FILTRI[@]} -eq 0 ]; then
  grep -v '^#' "$BASELINE" | cut -f1 | sort > "$NOTI"
else
  pat=$(printf '%s\n' "${FILTRI[@]}" | paste -sd'|')
  grep -v '^#' "$BASELINE" | cut -f1 | grep -E "$pat" | sort > "$NOTI"
fi
cut -f1 "$CORRENTE" | sort > "$ATTUALI"
NUOVI=$(comm -13 "$NOTI" "$ATTUALI")
RIENTRATI=$(comm -23 "$NOTI" "$ATTUALI")

echo "Non-verdi ora: $NONVERDI su $TOT   |   noti in baseline (perimetro): $(grep -c '' "$NOTI")"
echo
if [ -n "$RIENTRATI" ]; then
  echo "✅ RIENTRATI — ora verdi, vanno tolti dalla baseline:"
  echo "$RIENTRATI" | sed 's/^/   /'
  echo "   → scripts/smoke-baseline.sh --update ${FILTRI[*]:-}"
  echo
fi
if [ -n "$NUOVI" ]; then
  echo "❌ REGRESSIONI — non erano in baseline:"
  while IFS= read -r nf; do
    [ -z "$nf" ] && continue
    printf '   %-48s %s\n' "$nf" "$(grep -F "$nf"$'\t' "$CORRENTE" | cut -f2)"
  done <<< "$NUOVI"
  echo
  echo "Sono da guardare: tutto il resto era gia' non-verde prima."
  exit 1
fi
echo "✅ Nessuna regressione: ogni non-verde era gia' noto."
exit 0
