# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------       


#!/usr/bin/env bash

# come Eseguire 
#./update-venv.sh

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# In alternativa usare questi comandi manualmente:

# python -m pip install --upgrade pip
# python -m pip list --outdated --format=json
# python -m pip install --upgrade <package_name>
# python -m pip check
# pip list --outdated --format=columns | ForEach-Object { if ($_ -match '^\S+') { pip install --upgrade $matches[0] } } -- aggiorna tutto
# python -m pip freeze > requirements.txt




set -euo pipefail

# ⛔ ANCORAGGIO (2026-08-26). Sotto c'e' un `pip freeze > requirements.txt` senza
#    percorso: prima di questa riga scriveva nella CARTELLA CORRENTE, quindi
#    lanciato da `backend/` sostituiva `backend/requirements.txt` — che e'
#    generato da `pip-compile` — con un freeze piatto, cancellando il lock.
#    ⚠️ Ed e' un errore facile: i due script si chiamano UGUALE
#    (`scripts/update-venv.sh` qui, `backend/scripts/update-venv.sh` la'), e il
#    fratello del backend e' gia' ancorato cosi'.
cd "$(dirname "$0")/.."

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "⚠️  Non sembra attiva una virtualenv (VIRTUAL_ENV non impostata)."
  read -r -p "Vuoi continuare lo stesso? [y/N] " RESP
  [[ "${RESP}" == "y" ]] || exit 1
fi

# ⛔ E non dev'essere la venv del BACKEND: qui si fa `pip freeze` di tutto
#    l'ambiente sul requirements.txt di radice, quindi con quella attiva la lista
#    degli strumenti di sviluppo diventerebbe l'elenco dei pacchetti Django.
#    ⚠️ Si vieta quella sbagliata invece di pretendere quella giusta: dove viva
#    l'ambiente degli strumenti e' una scelta della macchina (qui
#    ~/.venvs/zeroerp-tools), e cablarla renderebbe lo script inservibile
#    altrove. La venv del backend, invece, sta nel repo e la sappiamo.
VENV_BACKEND="$(pwd)/backend/.venv"
if [[ -n "${VIRTUAL_ENV:-}" \
      && "$(readlink -f "${VIRTUAL_ENV}")" == "$(readlink -f "${VENV_BACKEND}")" ]]; then
  echo "Venv sbagliata: questa e' quella del BACKEND, governata da pip-compile."
  echo "  attiva: ${VIRTUAL_ENV}"
  echo "Per il backend si usa backend/scripts/update-venv.sh."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"

# 1) Aggiorna pip
${PYTHON_BIN} -m pip install --upgrade pip

# 2) Elenco pacchetti da aggiornare (evita broken pipe)
echo "🔎 Cerco pacchetti da aggiornare..."
export OUTDATED_JSON="$(${PYTHON_BIN} -m pip list --outdated --format=json || true)"

TO_UPDATE="$(${PYTHON_BIN} - <<'PY'
import sys, json, os
data = os.environ.get("OUTDATED_JSON","").strip()
if not data:
    sys.exit(0)
try:
    pkgs = json.loads(data)
    for p in pkgs:
        name = p.get("name")
        if name:
            print(name)
except Exception:
    sys.exit(0)
PY
)"

if [[ -z "${TO_UPDATE}" ]]; then
  echo "✅ Nessun pacchetto da aggiornare."
else
  echo "⟹ Aggiorno:"
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    echo "   - $name"
    ${PYTHON_BIN} -m pip install --upgrade "$name"
  done <<< "${TO_UPDATE}"
fi

# 3) Verifica dipendenze
echo
echo "▶️  Eseguo 'pip check'..."
set +e
CHECK_OUT="$(${PYTHON_BIN} -m pip check 2>&1)"
STATUS=$?
set -e
echo "${CHECK_OUT}"

# 4) Freeze solo se OK
if [[ ${STATUS} -eq 0 ]]; then
  echo
  echo "✅ Dipendenze OK. Scrivo requirements.txt..."
  ${PYTHON_BIN} -m pip freeze > requirements.txt
  echo "📝 Fatto: requirements.txt aggiornato."
  exit 0
else
  echo "❌ Conflitti rilevati. requirements.txt NON aggiornato. Risolvi e riprova."
  exit ${STATUS}
fi
