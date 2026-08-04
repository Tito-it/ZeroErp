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


# 1) Aggiorna pip — PINNATO a < 26.2 (2026-08-01)
#    pip 26.2 ha RIMOSSO `stdlib_pkgs` da `pip._internal.utils.compat`, che
#    pip-tools importa in `piptools/sync.py`: con pip >= 26.2 sia
#    `python -m piptools compile` sia `pip-sync` muoiono con ImportError
#    all'import del modulo (7.6.0 e' l'ultima release pip-tools esistente,
#    non c'e' una versione a cui salire).
#    RIMUOVERE IL PIN quando pip-tools pubblica una release compatibile con
#    pip >= 26.2 (verifica: `pip index versions pip-tools`).
python -m pip install -U "pip<26.2"

# 2) Assicura pip-tools
python -m pip install -U pip-tools

# 3) Genera requirements.txt bloccato (risolve deps) a partire da requirements.in
# --upgrade aggiorna alle versioni più recenti consentite dai range in requirements.in
python -m piptools compile --upgrade "$IN" --output-file "$OUT"

# 4) Sincronizza l'ambiente con requirements.txt (installa e rimuove pacchetti extra)
python -m piptools sync "$OUT"

# 5) Aggiorna pacchetti tool del venv non in requirements.in
python -m pip install -U wheel setuptools 2>/dev/null || true

# 6) Verifica integrità dipendenze
python -m pip check

echo "OK -> $OUT updated and venv synced"
