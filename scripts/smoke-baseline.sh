#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: eseguire TUTTI gli smoke di backend/scripts/tests/ e distinguere in un
#        colpo d'occhio un esito non-verde NUOVO da uno gia' noto.
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
# Tempo: ~4 minuti sugli undici file. `c9-fatturazione-parte-alta` da solo
# supera i due minuti: senza un timeout generoso sembra bloccato.
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
    -h|--help) sed -n '2,58p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    -*) echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
    *) FILTRI+=("$arg") ;;
  esac
done

# Perimetro. ⚠️ `find`, non un glob: se un giorno gli smoke finissero in una
#   sottocartella, un glob a un livello solo direbbe «tutto a posto» quando in
#   realta' non ha guardato.
FILES=$(find "$SMOKE_DIR" -maxdepth 2 -name 'smoke-*.py' -not -path '*/archive/*' | sort)
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

CORRENTE=$(mktemp); NOTI=$(mktemp); ATTUALI=$(mktemp)
trap 'rm -f "$CORRENTE" "$NOTI" "$ATTUALI"' EXIT

echo "smoke baseline — $TOT file (timeout ${TIMEOUT}s ciascuno)"
echo
n=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$((n+1)); rel=$(basename "$f")
  printf '\r  %d/%d  %-52.52s' "$n" "$TOT" "$rel" >&2
  out=$(cd "$ROOT_DIR/backend" && timeout "$TIMEOUT" ./manage-env.sh shell < "$f" 2>&1; [ $? -eq 124 ] && echo __TIMEOUT__)
  esito=$(classifica "$out")
  [ "$esito" = "VERDE" ] && continue
  printf '%s\t%s\n' "$rel" "$esito" >> "$CORRENTE"
done <<< "$FILES"
printf '\r%*s\r' 70 '' >&2

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
      grep -v "^$(basename "$f")"$'\t' "$TMP" > "$TMP.f" && mv "$TMP.f" "$TMP"
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
