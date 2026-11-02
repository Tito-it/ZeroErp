#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Aggiorna db/pgtap/baseline-rossi-ci.tsv con cio' che la CI HA MISURATO.
#   Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# A COSA SERVE, in una riga:
#   «togliere dal registro dei rossi della CI le righe che la CI stessa ha
#    dichiarato RIENTRATE, senza trascriverle a mano e senza usare la misura
#    di un altro database».
#
# ── ⛔ PERCHE' ESISTE ─────────────────────────────────────────────────
#   `baseline-rossi-ci.tsv` registra i rossi della corsa di GitHub, e
#   `scripts/pgtap-baseline.sh --update` su quel file e' un cancello fuori dalla
#   CI (GITHUB_ACTIONS != true ⇒ exit 2): la misura dello scratch locale non e'
#   la misura della CI — il 14-09 lo scratch dava 33 verdi «non registrati» e la
#   CI ne dichiarava 31, con tre file diversi da una parte e uno dall'altra.
#   ⚠️ Ma la CI non puo' committare: stampa l'elenco RIENTRATI e la riga si
#   toglieva A MANO. Un passo manuale che nessuno fa e' un registro che
#   invecchia: il 14-09 erano trentuno righe accumulate in due giorni.
#   ⇒ Questo script legge il log della corsa di GitHub (`gh`), prende l'elenco
#   che la CI ha stampato e toglie QUELLE righe. La sorgente e' la stessa del
#   cancello: la corsa di GitHub, non questo database.
#
# ── ⛔ LE REGRESSIONI NON SI AGGIUNGONO DA QUI ────────────────────────
#   Un rosso nuovo si stampa e si lascia a chi legge: entra in baseline solo
#   per decisione, con la causa letta nel log del container Postgres (passo
#   «Stop containers»). Un registro che si allunga da solo e' il posto dove i
#   problemi vanno a sparire.
#
# USO:
#   scripts/pgtap-baseline-ci-rientrati.sh             # ultima corsa utile su Tito-dev
#   scripts/pgtap-baseline-ci-rientrati.sh <run-id>    # una corsa precisa (gh run list)
#   scripts/pgtap-baseline-ci-rientrati.sh --dry-run   # mostra, non scrive
#
# «Corsa utile» = CI-Validate, push su Tito-dev, completata, in cui la suite
# pgTAP ha girato (il log porta «Rossi ora:»). Le PR verso Tito-dev non la
# eseguono; una push che non tocca db/ o scripts/ nemmeno.
#
# PREREQUISITI: `gh` autenticato sul repo.
# ------------------------------------------------------------
set -euo pipefail

BASELINE="db/pgtap/baseline-rossi-ci.tsv"
DRY_RUN=0
RUN_ID=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *[!0-9]*) echo "❌ argomento non riconosciuto: $arg" >&2; exit 2 ;;
    *) RUN_ID="$arg" ;;
  esac
done

cd "$(dirname "$0")/.."
[ -f "$BASELINE" ] || { echo "❌ manca $BASELINE (lanciare dalla radice del repo)" >&2; exit 2; }
command -v gh >/dev/null || { echo "❌ serve 'gh' (GitHub CLI) autenticato" >&2; exit 2; }

REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

# Scarica il log del job «validate» di una corsa, via API.
#   exit 1: la corsa non ha un job «validate»; exit 2: il log non c'e' piu'
#   (GitHub risponde 410 sulle corse di cui ha ritirato il log — succede gia'
#   a due giorni di distanza: l'elenco va preso dalla corsa mentre c'e').
#   Scrive nel file passato come secondo argomento. ⚠️ Niente `grep -q` in
#   coda a una pipeline: con `pipefail` chiude il pipe al primo byte e la
#   pipeline risulta fallita anche quando il log c'e'.
scarica_log() {
  local run="$1" dest="$2" job
  job="$(gh run view "$run" --json jobs --jq '.jobs[] | select(.name=="validate") | .databaseId')"
  [ -n "$job" ] || return 1
  gh api "repos/$REPO/actions/jobs/$job/logs" > "$dest.raw" 2>/dev/null || { rm -f "$dest.raw"; return 2; }
  sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z //' "$dest.raw" > "$dest"
  rm -f "$dest.raw"
  [ -s "$dest" ] || return 2
}

LOG="$(mktemp)"
trap 'rm -f "$LOG" "$LOG.raw"' EXIT

if [ -n "$RUN_ID" ]; then
  rc=0; scarica_log "$RUN_ID" "$LOG" || rc=$?
  case "$rc" in
    1) echo "❌ corsa $RUN_ID: nessun job 'validate' (e' una corsa CI-Validate?)" >&2; exit 2 ;;
    2) echo "❌ corsa $RUN_ID: log non piu' disponibile (GitHub 410). L'elenco RIENTRATI si prende dalla corsa mentre il log c'e'." >&2; exit 2 ;;
  esac
  grep -q '^Rossi ora:' "$LOG" || { echo "❌ corsa $RUN_ID: la suite pgTAP non ha girato (nessun «Rossi ora:»)" >&2; exit 2; }
else
  # ⚠️ Si scorre finche' se ne trova una in cui la suite ha girato: le push
  #   solo-backend la saltano, e sarebbero «nessun rientrato» per il motivo
  #   sbagliato.
  while IFS=$'\t' read -r id conclusion; do
    [ "$conclusion" = "cancelled" ] && continue
    scarica_log "$id" "$LOG" || continue
    if grep -q '^Rossi ora:' "$LOG"; then RUN_ID="$id"; break; fi
  done < <(gh run list --workflow CI-Validate --branch Tito-dev --event push \
             --status completed --limit 15 --json databaseId,conclusion \
             --jq '.[] | "\(.databaseId)\t\(.conclusion)"')
  [ -n "$RUN_ID" ] || { echo "❌ nessuna corsa recente su Tito-dev in cui la suite abbia girato" >&2; exit 2; }
fi

INFO="$(gh run view "$RUN_ID" --json conclusion,headSha,createdAt,displayTitle \
          --jq '"\(.conclusion) · \(.createdAt) · \(.headSha[0:9]) · \(.displayTitle)"')"
SHA="$(gh run view "$RUN_ID" --json headSha --jq '.headSha[0:9]')"
echo "Corsa CI-Validate $RUN_ID — $INFO"
grep -m1 '^Rossi ora:' "$LOG"
echo

# Gli elenchi, cosi' come la CI li stampa: righe indentate sotto il titolo.
# ⚠️ Dentro l'elenco puo' comparire una riga di SOLI SPAZI — il residuo della
#   barra di avanzamento («N/M file») che il log di GitHub cattura: si salta,
#   non chiude l'elenco. Trovato al primo giro: 29 righe lette su 31 stampate.
elenco() {
  awk -v titolo="$1" '
    index($0, titolo) { f = 1; next }
    f && /^[[:space:]]*$/ { next }
    f && /^ +db\/pgtap\// { sub(/^ +/, ""); print; next }
    f { f = 0 }
  ' "$LOG"
}
RIENTRATI="$(elenco 'RIENTRATI — ora verdi')"
REGRESSIONI="$(elenco 'REGRESSIONI — rossi NUOVI')"

if [ -n "$REGRESSIONI" ]; then
  echo "❌ REGRESSIONI dichiarate dalla CI — NON entrano in baseline da qui:"
  echo "$REGRESSIONI" | sed 's/^/   /'
  echo "   La causa vera sta nel log del container Postgres (passo «Stop containers»):"
  echo "   gh run view $RUN_ID --job <job> --log | grep -A3 'ERROR:'"
  echo
fi

if [ -z "$RIENTRATI" ]; then
  echo "✅ Nessun rientrato in questa corsa: la baseline e' allineata alla CI."
  exit 0
fi

# Solo le righe che stanno davvero nel registro: una gia' tolta non e' un errore.
DA_TOGLIERE="$(echo "$RIENTRATI" | while IFS= read -r f; do
  grep -q "^${f}"$'\t' "$BASELINE" && echo "$f" || true
done)"

if [ -z "$DA_TOGLIERE" ]; then
  echo "✅ I rientrati della CI ($(echo "$RIENTRATI" | grep -c '')) sono gia' fuori dal registro."
  exit 0
fi

N="$(echo "$DA_TOGLIERE" | grep -c '')"
echo "✅ RIENTRATI dichiarati dalla CI, da togliere da $BASELINE ($N):"
echo "$DA_TOGLIERE" | while IFS= read -r f; do
  printf '   %-70s %s\n' "$f" "$(grep "^${f}"$'\t' "$BASELINE" | cut -f2)"
done
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(dry-run: niente scritto)"
  exit 0
fi

TMP="$(mktemp)"
grep -v -F -x -f <(echo "$DA_TOGLIERE" | while IFS= read -r f; do grep "^${f}"$'\t' "$BASELINE"; done) "$BASELINE" > "$TMP"
mv "$TMP" "$BASELINE"

PRIMA=$((N + $(grep -vc '^#' "$BASELINE")))
echo "✅ $BASELINE: $PRIMA → $(grep -vc '^#' "$BASELINE") righe, dalla corsa $RUN_ID."
echo "   Da citare nel commit: «baseline CI allineata alla corsa $RUN_ID ($SHA)»."
