#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Il login UNICO di una sessione di smoke: fa il login vero (col secondo
#        fattore, se l'utente lo ha) e stampa `export SMOKE_TOKEN=...`, che
#        `smoke_login` (`_smoke_auth.sh`) riusa negli smoke lanciati dopo, senza
#        rifare il login ne' aspettare il codice TOTP.
# Uso:
#   eval "$(backend/scripts/tests/smoke-login.sh [password])"
#   backend/scripts/tests/smoke-test-catalogo.sh      # niente login
# Note: sullo standard output va SOLO la riga `export` (la legge `eval`); la
#       domanda della password, i messaggi e gli errori vanno sul terminale
#       (standard error). Se il login fallisce non stampa niente da eseguire.
#       L'access dura 10 minuti (`SIMPLE_JWT`): gli smoke lo riusano finche'
#       vale piu' di SMOKE_TOKEN_MARGINE secondi, poi rifanno il login da se'.
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, SMOKE_TOKEN): un solo BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

smoke_login --login-vero >&2
printf 'export SMOKE_TOKEN=%q\n' "$TOKEN"
scade="$(smoke_jwt_claim "$TOKEN" exp)"
if [[ "$scade" =~ ^[0-9]+$ ]]; then
  echo "SMOKE_TOKEN di '${USERNAME}' pronto: vale fino alle $(date -d "@${scade}" +%H:%M:%S)" \
       "(gli smoke lo riusano fino a ${SMOKE_TOKEN_MARGINE}s prima)." >&2
fi
