#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: distinguere in un secondo un pgTAP rosso NUOVO da uno gia' noto.
#
# IL PROBLEMA CHE RISOLVE. La suite pgTAP ha un blocco di rossi preesistenti
# (fixture rimaste indietro rispetto a guard entrati dopo). Chi esegue una
# batteria di regressione dopo una modifica vede quei rossi e, ogni volta, deve
# ri-verificare a mano se c'entrano con il proprio lavoro. E' successo piu'
# volte, e ogni verifica costa piu' del lavoro stesso.
#
# Peggio: una suite con molti rossi noti insegna a ignorare il rosso — che e'
# esattamente cio' che i test dovrebbero impedire.
#
# COME FUNZIONA. Un file di baseline committato elenca i rossi NOTI. Lo script
# riesegue la suite e confronta:
#   - un rosso presente in baseline  -> atteso, silenzio
#   - un rosso NON in baseline       -> REGRESSIONE, exit 1
#   - un file in baseline ora verde  -> RIENTRATO, va tolto dalla baseline
#
# ⚠️ La baseline NON e' una lista di eccezioni permanenti: e' un registro di
# debito, e deve calare. Ogni riga e' un file la cui copertura oggi vale ZERO
# (se fallisce nel fixture non esegue nessuna asserzione), non "parziale".
#
# ⚠️ E VALE SOLO SE E' STATA REGISTRATA COL MEDESIMO UTENTE. Un rosso puo'
# dipendere dal ruolo di connessione (permessi, RLS): confrontare una corsa da
# utente applicativo con una baseline presa da owner produce decine di finte
# regressioni. E' il difetto che ha originato il brief
# `brief-db-pgtap-runner-rls-baseline.md`. Da qui la prima riga del file di
# baseline, `# pgtap-runner: <owner|app>`, e il rifiuto di confrontare corse
# disomogenee.
#
# USO
#   scripts/pgtap-baseline.sh                  # confronta tutta la suite
#   scripts/pgtap-baseline.sh vendite config   # solo alcuni schemi (piu' veloce)
#   scripts/pgtap-baseline.sh --update         # rigenera la baseline
#   scripts/pgtap-baseline.sh --update vendite # rigenera solo quegli schemi
#
#   PGTAP_RUNNER=app scripts/pgtap-baseline.sh vendite   # come gira l'applicazione
#
# La scelta dell'utente sta in scripts/testpgtap.sh (variabile PGTAP_RUNNER e
# marcatore `-- pgtap-runner: owner` per i file che richiedono l'owner).
#
# EXIT CODE
#   0 = nessuna regressione (eventuali rientri sono solo segnalati)
#   1 = almeno un rosso nuovo
#
# Tempo: ~1s per file. La suite intera (~400 file) richiede circa 7 minuti;
# restringere agli schemi toccati e' quasi sempre sufficiente.
# ------------------------------------------------------------

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASELINE="$ROOT_DIR/db/pgtap/baseline-rossi.tsv"

UPDATE=0
SCHEMI=()
for arg in "$@"; do
  case "$arg" in
    --update) UPDATE=1 ;;
    -h|--help) sed -n '2,45p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    -*) echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
    *) SCHEMI+=("$arg") ;;
  esac
done

# Perimetro: tutti gli schemi o solo quelli richiesti.
if [ ${#SCHEMI[@]} -eq 0 ]; then
  FILES=$(ls "$ROOT_DIR"/db/pgtap/*/*.sql 2>/dev/null | sort)
else
  FILES=""
  for sc in "${SCHEMI[@]}"; do
    if [ ! -d "$ROOT_DIR/db/pgtap/$sc" ]; then
      echo "Schema inesistente: $sc (cerca in db/pgtap/)" >&2; exit 2
    fi
    FILES="$FILES"$'\n'"$(ls "$ROOT_DIR/db/pgtap/$sc"/*.sql 2>/dev/null | sort)"
  done
  FILES=$(echo "$FILES" | grep -v '^$')
fi

RUNNER="${PGTAP_RUNNER:-owner}"

# Utente registrato nella baseline. Prima riga `# pgtap-runner: <x>`; le
# baseline scritte prima dell'introduzione del marcatore non ce l'hanno e sono
# tutte da owner, che era l'unico modo di girare la suite.
baseline_runner() {
  local r
  r=$(grep -m1 -E '^# pgtap-runner:' "$BASELINE" 2>/dev/null | sed -E 's/^# pgtap-runner:[[:space:]]*//')
  echo "${r:-owner}"
}
# Righe vere della baseline (senza intestazione).
baseline_righe() { grep -v '^#' "$BASELINE" 2>/dev/null; }

# Metro omogeneo, verificato PRIMA di eseguire: un confronto fra utenti diversi
# non dice niente sulle regressioni, dice solo che i due utenti hanno permessi
# diversi. Il controllo sta qui e non in fondo perche' scoprirlo dopo costerebbe
# l'intera corsa (~7 minuti sulla suite).
# L'unico caso in cui un metro nuovo e' legittimo e' la ribaselinatura INTERA.
if [ -f "$BASELINE" ]; then
  PRECED=$(baseline_runner)
  RIBASE_INTERA=$([ "$UPDATE" -eq 1 ] && [ ${#SCHEMI[@]} -eq 0 ] && echo 1 || echo 0)
  if [ "$PRECED" != "$RUNNER" ] && [ "$RIBASE_INTERA" -eq 0 ]; then
    echo "❌ La baseline e' registrata con runner '$PRECED', questa corsa gira con '$RUNNER'." >&2
    if [ "$UPDATE" -eq 1 ]; then
      echo "   Un aggiornamento parziale mescolerebbe due metri nello stesso file." >&2
    else
      echo "   Un rosso puo' dipendere dal ruolo (permessi, RLS): il confronto" >&2
      echo "   produrrebbe finte regressioni." >&2
    fi
    echo "   O si gira con PGTAP_RUNNER=$PRECED, o si ribaselina l'INTERA suite:" >&2
    echo "      PGTAP_RUNNER=$RUNNER $0 --update" >&2
    exit 2
  fi
fi

TOT=$(echo "$FILES" | grep -c '' )
echo "pgTAP baseline — $TOT file da eseguire (~$((TOT))s) — runner: $RUNNER"
echo

CORRENTE=$(mktemp)
trap 'rm -f "$CORRENTE"' EXIT

n=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$((n+1))
  rel="${f#"$ROOT_DIR"/db/pgtap/}"
  printf '\r  %d/%d  %-58.58s' "$n" "$TOT" "$rel" >&2

  out=$(timeout 90 "$SCRIPT_DIR/testpgtap.sh" "db/$rel" 2>&1)
  echo "$out" | grep -q "Result: PASS" && continue

  # Classificazione della causa: serve a triagiare senza riaprire ogni file.
  if echo "$out" | grep -q "key_selector"; then
    causa="SORGENTE_POLIMORFA"
  elif echo "$out" | grep -q "ERRORE:"; then
    causa="ERRORE_FIXTURE"
  else
    causa="ASSERZIONE"
  fi
  printf 'db/pgtap/%s\t%s\n' "$rel" "$causa" >> "$CORRENTE"
done <<< "$FILES"
printf '\r%*s\r' 70 '' >&2

sort -o "$CORRENTE" "$CORRENTE"
ROSSI=$(grep -c '' "$CORRENTE" || true)

# --- modalita' aggiornamento -------------------------------------------------
if [ "$UPDATE" -eq 1 ]; then
  TMP=$(mktemp)
  if [ ${#SCHEMI[@]} -eq 0 ]; then
    cp "$CORRENTE" "$TMP"
  else
    # Aggiornamento parziale: si sostituiscono SOLO le righe degli schemi
    # eseguiti, lasciando intatto il resto della baseline.
    #
    # L'omogeneita' del metro e' gia' stata verificata prima della corsa.
    baseline_righe > "$TMP"
    for sc in "${SCHEMI[@]}"; do
      grep -v "^db/pgtap/$sc/" "$TMP" > "$TMP.f" && mv "$TMP.f" "$TMP"
    done
    cat "$CORRENTE" >> "$TMP"
    sort -o "$TMP" "$TMP"
  fi
  { echo "# pgtap-runner: $RUNNER"; cat "$TMP"; } > "$BASELINE"
  rm -f "$TMP"
  echo "Baseline aggiornata: $BASELINE ($(baseline_righe | grep -c '') rossi noti, runner: $RUNNER)"
  exit 0
fi

# --- modalita' confronto -----------------------------------------------------
if [ ! -f "$BASELINE" ]; then
  echo "Baseline assente ($BASELINE)." >&2
  echo "Generala con: scripts/pgtap-baseline.sh --update" >&2
  exit 2
fi

# Confronto sulla sola colonna file: la causa e' informativa, non identitaria
# (lo stesso file puo' cambiare causa restando rosso — non e' una regressione).
NOTI=$(mktemp); ATTUALI=$(mktemp)
trap 'rm -f "$CORRENTE" "$NOTI" "$ATTUALI"' EXIT
if [ ${#SCHEMI[@]} -eq 0 ]; then
  baseline_righe | cut -f1 | sort > "$NOTI"
else
  pat=$(printf 'db/pgtap/%s/\n' "${SCHEMI[@]}" | paste -sd'|')
  baseline_righe | cut -f1 | grep -E "^($pat)" | sort > "$NOTI"
fi
cut -f1 "$CORRENTE" | sort > "$ATTUALI"

NUOVI=$(comm -13 "$NOTI" "$ATTUALI")
RIENTRATI=$(comm -23 "$NOTI" "$ATTUALI")

echo "Rossi ora: $ROSSI su $TOT   |   noti in baseline (perimetro): $(grep -c '' "$NOTI")"
echo

if [ -n "$RIENTRATI" ]; then
  echo "✅ RIENTRATI — ora verdi, vanno tolti dalla baseline:"
  echo "$RIENTRATI" | sed 's/^/   /'
  echo "   → scripts/pgtap-baseline.sh --update ${SCHEMI[*]:-}"
  echo
fi

if [ -n "$NUOVI" ]; then
  echo "❌ REGRESSIONI — rossi NUOVI, non erano in baseline:"
  while IFS= read -r nf; do
    [ -z "$nf" ] && continue
    causa=$(grep -F "$nf"$'\t' "$CORRENTE" | cut -f2)
    printf '   %-62s %s\n' "$nf" "$causa"
  done <<< "$NUOVI"
  echo
  echo "Sono da guardare: tutto il resto era gia' rosso prima."
  exit 1
fi

echo "✅ Nessuna regressione: ogni rosso era gia' noto."
exit 0
