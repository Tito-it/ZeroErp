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

# ⛔ Guard sull'ambiente ATTIVO, non solo sulla sua esistenza (2026-08-26).
#    `piptools sync` fa quello che dichiara: installa E RIMUOVE i pacchetti che
#    non stanno in requirements.txt. Lanciato con attiva la venv degli STRUMENTI
#    di sviluppo (mkdocs, zensical, pre-commit) la SVUOTEREBBE — portandosi via
#    anche `pre-commit`, e con lui l'hook di .git/hooks, che punta proprio a
#    quell'interprete.
#    Il controllo qui sopra chiedeva solo che UNA venv fosse attiva: bastava
#    quando l'ambiente era uno solo, non basta piu' da quando sono due.
VENV_ATTESA="$(cd .. && pwd)/.venv"
if [[ "$(readlink -f "${VIRTUAL_ENV}")" != "$(readlink -f "${VENV_ATTESA}")" ]]; then
  echo "Venv sbagliata: questo script governa SOLO quella del backend."
  echo "  attiva:  ${VIRTUAL_ENV}"
  echo "  attesa:  ${VENV_ATTESA}"
  echo "Per gli strumenti di sviluppo si usa scripts/update-venv.sh dalla radice."
  exit 1
fi


# 1) Aggiorna pip
#    Storia: pip 26.2 aveva rimosso `stdlib_pkgs` da
#    `pip._internal.utils.compat`, importato da `piptools/sync.py` ->
#    ImportError su compile e sync. Chiusa da pip-tools 7.6.1 (2026-08-12).
#    Per questo lo script aggiorna pip-tools PRIMA di pip: invertire
#    l'ordine puo' lasciare l'ambiente con pip 26.2 e pip-tools vecchio.
python -m pip install -U pip-tools
python -m pip install -U pip


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
