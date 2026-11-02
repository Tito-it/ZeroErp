# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------

#!/usr/bin/env bash

# Aggiornamento dipendenze frontend (npm)
#
# Utilizzo:
#   cd frontend
#   ./scripts/update-front-npm.sh
#
# ----------------------------------------------------------------
# Comandi manuali utili (da eseguire prima se vuoi capire lo stato):
#
#   npm outdated                  # mostra Current / Wanted / Latest
#                                 # Wanted = max compatibile col range ^
#                                 # Latest = ultima su npm
#
#   npx npm-check-updates         # mostra anche i major update disponibili
#                                 # (quelli fuori dal range ^ in package.json)
#
#   npx npm-check-updates -u      # aggiorna package.json alle ultime versioni
#                                 # ATTENZIONE: include major/breaking changes
#                                 # meglio farlo pacchetto per pacchetto:
#                                 #   npx npm-check-updates -u --filter "primevue"
#                                 #   npm install
#
#   npm audit                     # verifica vulnerabilita' note
#   npm audit fix                 # fix automatici vulnerabilita'
# ----------------------------------------------------------------

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Aggiornamento frontend npm ==="
echo ""

# 1) Aggiorna dipendenze entro i range definiti in package.json
echo "--- npm update (entro i range ^) ---"
npm update

# 2) Clean install da lock file (verifica coerenza)
echo ""
echo "--- npm ci (clean install) ---"
npm ci

# 3) Verifica build
echo ""
echo "--- npm run build ---"
npm run build

# 4) Verifica lint
echo ""
echo "--- npm run lint ---"
npm run lint

# 5) Audit sicurezza
echo ""
echo "--- npm audit ---"
npm audit || true

# 6) Mostra major update disponibili (solo lista, non modifica nulla)
echo ""
echo "--- Major update disponibili (solo informativo) ---"
npx --yes npm-check-updates

echo ""
echo "OK -> dipendenze frontend aggiornate e verificate"
