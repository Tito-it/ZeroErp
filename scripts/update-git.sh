#!/usr/bin/env bash
# Script per aggiornare il branch locale di base (es. Tito-dev) ./scripts/update-git.sh
# e fare pull sul branch corrente (se ha upstream). 
# Usa: ./scripts/update-git.sh [BASE_BRANCH]  
# Esempio: ./scripts/update-git.sh main


set -euo pipefail

# Base branch che vuoi tenere aggiornato in locale
BASE_BRANCH="${1:-Tito-dev}"

# Sei in un repo git?
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${TOPLEVEL}" ]]; then
  echo "Errore: non sei dentro un repository git."
  exit 1
fi
cd "${TOPLEVEL}"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ -z "${CURRENT_BRANCH}" ]]; then
  echo "Errore: sei in detached HEAD. Fai checkout di un branch e riprova."
  exit 1
fi

# Working tree pulita
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Errore: hai modifiche non committate. Fai commit/stash prima di aggiornare."
  git status --porcelain
  exit 1
fi

echo "Repo: ${TOPLEVEL}"
echo "Branch corrente: ${CURRENT_BRANCH}"
echo "Base da mantenere aggiornata: ${BASE_BRANCH}"
echo

echo "1) Fetch da origin..."
git fetch origin

echo "2) Aggiorno in locale ${BASE_BRANCH} (senza checkout)..."
# Aggiorna il ref locale Tito-dev -> origin/Tito-dev, senza cambiare branch
git fetch origin "${BASE_BRANCH}:${BASE_BRANCH}" >/dev/null 2>&1 || true

echo "3) Aggiorno il branch corrente con fast-forward (se ha upstream)..."
UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [[ -z "${UPSTREAM}" ]]; then
  echo "Nota: il branch corrente non ha upstream. Impostalo con:"
  echo "  git push -u origin ${CURRENT_BRANCH}"
  echo
else
  # Solo fast-forward: se diverge, ti avvisa invece di fare merge
  git pull --ff-only
fi

echo
echo "OK: aggiornamento completato."
