#!/usr/bin/env bash

# Script per fare rebase del branch corrente su un branch di base aggiornato ./scripts/rebase.sh su Tito-dev
# Usa: ./scripts/rebase.sh [BASE_BRANCH] [DO_PUSH]
# Esempio: ./scripts/rebase.sh main yes 



set -euo pipefail

BASE_BRANCH="${1:-Tito-dev}"
DO_PUSH="${2:-no}"   # usa "yes" per pushare dopo il rebase

# Assicurati di essere dentro un repo git
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${TOPLEVEL}" ]]; then
  echo "Errore: non sei dentro un repository git."
  exit 1
fi

# Assicurati di essere nella root (se lo lanci da una sottocartella funziona lo stesso)
cd "${TOPLEVEL}"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ -z "${CURRENT_BRANCH}" ]]; then
  echo "Errore: sei in detached HEAD. Fai checkout di un branch e riprova."
  exit 1
fi

# Se hai modifiche non committate, fermati (best practice)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Errore: hai modifiche non committate. Fai commit/stash prima di rebase."
  git status --porcelain
  exit 1
fi

echo "Repo: ${TOPLEVEL}"
echo "Branch corrente: ${CURRENT_BRANCH}"
echo "Base branch: ${BASE_BRANCH}"
echo

echo "1) Fetch da origin..."
git fetch origin

echo "2) Aggiorno ${BASE_BRANCH} (fast-forward)..."
git checkout "${BASE_BRANCH}"
git pull --ff-only origin "${BASE_BRANCH}"

echo "3) Torno su ${CURRENT_BRANCH} e faccio rebase su ${BASE_BRANCH}..."
git checkout "${CURRENT_BRANCH}"

if [[ "${CURRENT_BRANCH}" == "${BASE_BRANCH}" ]]; then
  echo "Sei già su ${BASE_BRANCH}. Nessun rebase necessario."
else
  git rebase "${BASE_BRANCH}"
fi

echo
echo "OK: rebase completato."

if [[ "${DO_PUSH}" == "yes" && "${CURRENT_BRANCH}" != "${BASE_BRANCH}" ]]; then
  echo "4) Push del branch dopo rebase (force-with-lease)..."
  git push --force-with-lease
  echo "OK: push completato."
fi
