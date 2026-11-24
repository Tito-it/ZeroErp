#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: LA PARTENZA DI OGNI LISTA CONFIGURABILE, sul DB vero: ordinamento
#        (`meta.ordinamento`, che accende l'intestazione), misura, ordine delle
#        righe e clic sulla colonna di partenza, rotta per rotta
#        (brief-be-collaudo-partenza-liste-dal-preset §2, la parte BE del
#        collaudo; la parte FE resta a video, sui campioni del brief).
#        Il login e' quello degli smoke (`smoke_login`, utente `dev.smoke`); il
#        giro lo fa `_smoke_partenza_liste.py`, in-process, col token del login.
# Uso:
#   ./scripts/tests/smoke-test-ui-partenza-liste.sh [password]
#   PARTENZA_FILTRO=magazzino ./scripts/tests/smoke-test-ui-partenza-liste.sh
# Prerequisiti: backend in esecuzione su BASE_URL (per il login), utente degli
#   smoke provvisto (`provision_utenti_sviluppo`).
# Esito: «FAIL <lista>» per ogni rotta che sbaglia la partenza, «SKIP» per
#   quelle non verificate (col motivo), riepilogo «Risultato: N OK, M FAIL,
#   K SKIP». ⛔ Solo letture.
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "-- 0. Autenticazione JWT --"
INTESTAZIONI=$(mktemp)
trap 'rm -f "$INTESTAZIONI"' EXIT
if [[ -n "${PARTENZA_EMITTENTE:-}" ]]; then
    # Il cambio di emittente vuole il cookie del refresh: login vero.
    smoke_login -D "$INTESTAZIONI"
else
    smoke_login
fi
echo "  OK  login (${SMOKE_LOGIN_FONTE})"

# Scopo: cambia l'emittente attivo della sessione degli smoke e rimette in
#        TOKEN l'access nuovo (il POST riemette i token: la verita' della
#        richiesta e' il claim). ⚠️ Il cambio SALVA la preferenza dell'utente:
#        chi lo chiama la rimette com'era (trap sotto).
cambia_emittente() {
    local cookie corpo
    cookie=$(grep -i '^set-cookie:' "$INTESTAZIONI" | sed 's/^[^:]*: //; s/;.*//' | tr -d '\r' | paste -sd';' -)
    corpo=$(curl -s -X POST -H "Authorization: Bearer ${TOKEN}" -H "Cookie: ${cookie}" \
        -H 'Content-Type: application/json' -d "{\"emittente_fiscale_id\": $1}" \
        "${BASE_URL}/api/v1/core/me/emittente-attivo/")
    TOKEN=$(printf '%s' "$corpo" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["access"])' 2>/dev/null || true)
    if [[ -z "$TOKEN" ]]; then
        echo "  FAIL cambio dell'emittente attivo a $1: $(printf '%s' "$corpo" | head -c 300)"
        return 1
    fi
}

# Facoltativo: il giro su un emittente scelto (`PARTENZA_EMITTENTE=<id>`, uno
# di GET /api/v1/core/me/emittente-attivo/). Senza, vale l'emittente attivo
# dell'utente degli smoke, che puo' avere poche righe: le liste vuote escono
# SKIP, copertura zero. Alla fine si rimette l'emittente di prima.
if [[ -n "${PARTENZA_EMITTENTE:-}" ]]; then
    EMITTENTE_PRIMA=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/core/me/" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["emittente_attivo"]["emittente_fiscale_id"] or "")')
    if [[ -z "$EMITTENTE_PRIMA" ]]; then
        echo "  Setup fallito: nessun emittente attivo da rimettere alla fine (modalita' globale)."
        exit 1
    fi
    cambia_emittente "$PARTENZA_EMITTENTE"
    trap 'cambia_emittente "$EMITTENTE_PRIMA" && echo "  OK  emittente attivo rimesso a $EMITTENTE_PRIMA"; rm -f "$INTESTAZIONI"' EXIT
    echo "  OK  emittente attivo $PARTENZA_EMITTENTE (prima: $EMITTENTE_PRIMA)"
fi

echo "-- 1. La partenza, rotta per rotta --"
PARTENZA_TOKEN="$TOKEN" "${BACKEND_DIR}/manage-env.sh" shell \
    < "${BACKEND_DIR}/scripts/tests/_smoke_partenza_liste.py" 2>&1 \
    | grep -vE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[^ ]+ (DEBUG|INFO) |objects imported automatically'
