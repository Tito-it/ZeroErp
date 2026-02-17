#!/usr/bin/env bash

# Script per fare rebase del branch corrente su un branch di base aggiornato ./scripts/rebase.sh su Tito-dev
# Usa: ./scripts/rebase.sh [BASE_BRANCH] [DO_PUSH]
# Esempio aggiorna da Tito-dev e fa push in local:
# ./scripts/rebase.sh Tito-dev yes



#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="${1:-Tito-dev}"
DO_PUSH="${2:-no}"   # yes/no

TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "${TOPLEVEL}" ]] || { echo "Errore: non sei in un repo git."; exit 1; }
cd "${TOPLEVEL}"

CURRENT_BRANCH="$(git branch --show-current)"
[[ -n "${CURRENT_BRANCH}" ]] || { echo "Errore: detached HEAD."; exit 1; }

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Errore: hai modifiche non committate."
  git status --porcelain
  exit 1
fi

echo "Repo: ${TOPLEVEL}"
echo "Branch corrente: ${CURRENT_BRANCH}"
echo "Base remota: origin/${BASE_BRANCH}"
echo

git fetch origin

if [[ "${CURRENT_BRANCH}" == "${BASE_BRANCH}" ]]; then
  echo "Sei già su ${BASE_BRANCH}: nessun rebase."
  exit 0
fi

git rebase "origin/${BASE_BRANCH}"
echo "OK: rebase completato."

if [[ "${DO_PUSH}" == "yes" ]]; then
  git push --force-with-lease origin "${CURRENT_BRANCH}"
  echo "OK: push completato."
fi
