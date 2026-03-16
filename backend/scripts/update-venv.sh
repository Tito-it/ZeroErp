# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.

# Workflow “pulito” consigliato:
# - requirements.in  -> top-level con range (no pin stretti)
# - requirements.txt -> generato e bloccato con pip-tools (pip-compile)
# - ambiente         -> sincronizzato con pip-sync

# ------------------------------------------------------------       

#!/usr/bin/env bash

# come Eseguire 
#./update-venv.sh


# In alternativa usare questi comandi manualmente:
# python -m pip install --upgrade pip
# python -m pip list --outdated --format=json
# python -m pip install --upgrade <package_name>
# python -m pip check
# pip list --outdated --format=columns | ForEach-Object { if ($_ -match '^\S+') { pip install --upgrade $matches[0] } } -- aggiorna tutto

#  Utilizzo
#cd backend
#./update-venv.sh

set -euo pipefail
cd "$(dirname "$0")"

IN="../requirements.in"
OUT="../requirements.txt"

[[ -f "$IN" ]] || { echo "Missing $IN"; exit 1; }
[[ -n "${VIRTUAL_ENV:-}" ]] || { echo "Activate venv first (source .venv/bin/activate)"; exit 1; }


python -m pip install -U pip

# 2) Assicura pip-tools
python -m pip install -U pip-tools

# 3) Genera requirements.txt bloccato (risolve deps) a partire da requirements.in
# --upgrade aggiorna alle versioni più recenti consentite dai range in requirements.in
python -m piptools compile --upgrade "$IN" --output-file "$OUT"

# 4) Sincronizza l'ambiente con requirements.txt (installa e rimuove pacchetti extra)
python -m piptools sync "$OUT"

# 5) Verifica integrità dipendenze
python -m pip check

echo "OK -> $OUT updated and venv synced"
