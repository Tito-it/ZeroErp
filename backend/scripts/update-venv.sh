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

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "⚠️  Non sembra attiva una virtualenv (VIRTUAL_ENV non impostata)."
  read -r -p "Vuoi continuare lo stesso? [y/N] " RESP
  [[ "${RESP}" == "y" ]] || exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"

# 1) Aggiorna pip
${PYTHON_BIN} -m pip install --upgrade pip

# 2) Elenco pacchetti da aggiornare (evita broken pipe)
echo " Cerco pacchetti da aggiornare..."
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
  echo " Fatto: requirements.txt aggiornato."
  exit 0
else
  echo "❌ Conflitti rilevati. requirements.txt NON aggiornato. Risolvi e riprova."
  exit ${STATUS}
fi
