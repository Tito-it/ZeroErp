# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Script aggiornamento dipendenze npm per Zero ERP frontend
# Copyright (C) 2025 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------

#!/usr/bin/env bash

# Scopo: aggiorna tutti i pacchetti npm (patch + minor) e rigenera il lockfile.
#
# Eseguire dalla root del repo:
#   bash frontend/scripts/update-npm.sh
#
# Solo lista pacchetti da aggiornare (entro il range di package.json):
#   cd frontend && npm outdated
#
# Lista completa inclusi quelli fuori range (major disponibili):
#   cd frontend && npx npm-check-updates

set -euo pipefail
cd "$(dirname "$0")/.."

# Verifica che siamo nella cartella frontend
[[ -f "package.json" ]] || { echo "Errore: package.json non trovato in $(pwd)"; exit 1; }

echo "=== Aggiornamento dipendenze npm frontend ==="
echo ""

# 1) Mostra pacchetti da aggiornare (prima di toccare nulla)
echo "--- Pacchetti con aggiornamenti disponibili ---"
npx npm-check-updates || true
echo ""

# 2) Aggiorna package.json con patch + minor (no major/breaking)
echo "--- Aggiornamento package.json (patch + minor) ---"
npx npm-check-updates -u --target minor
echo ""

# 3) Installa e rigenera package-lock.json
echo "--- npm install ---"
npm install
echo ""

# 4) Verifica vulnerabilita' note
echo "--- Audit sicurezza ---"
npm audit --omit=dev || true
echo ""

# 5) Build di verifica
echo "--- Build di verifica ---"
npx vite build
echo ""

echo "OK -> package.json aggiornato, package-lock.json rigenerato, build verificata"
