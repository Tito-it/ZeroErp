#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test per sistema email, cambio password, reset password
# Uso: ./scripts/tests/smoke-test-email-auth.sh [password]
# ------------------------------------------------------------
# Indice test (0..11):
#  0) Login JWT admin
#  1) GET /amm-software/email-accounts/
#  2) GET /amm-software/email-templates/
#  3) GET /amm-software/email-templates/?codice=INVITO_OPERATORE
#  4) POST /amm-software/email-templates/{id}/preview/
#  5) GET /amm-software/email-log/
#  6) POST /core/email/prepare/
#  7) GET /core/email/outbox/
#  8) POST /core/email/outbox/{id}/cancel/
#  9) POST /auth/password-reset-request/
# 10) GET /auth/password-reset-validate/token-inesistente/
# 11) POST /auth/password-reset-confirm/
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        if k.isdigit(): d = d[int(k)]
        else: d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

# ================================================================
echo ""
echo "========================================="
echo " Smoke test Email + Auth"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Login JWT ---
echo ""
echo "-- 0. Login JWT admin --"

# Login vero: il passo legge la risposta del login (password_change_required).
smoke_login --login-vero
ACCESS_TOKEN="$TOKEN"
log_ok "Login riuscito (HTTP $AUTH_STATUS)"

PW_FLAG=$(json_get "$AUTH_BODY" "password_change_required")
if [[ -n "$PW_FLAG" && "$PW_FLAG" != "" ]]; then
    log_info "password_change_required=$PW_FLAG"
fi

# Helper: GET autenticato
auth_get() {
    curl -s -w '\n%{http_code}' \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        "${BASE_URL}$1" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# Helper: POST autenticato
auth_post() {
    curl -s -w '\n%{http_code}' \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d "$2" \
        "${BASE_URL}$1" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# Helper: POST anonimo
anon_post() {
    curl -s -w '\n%{http_code}' \
        -H "Content-Type: application/json" \
        -d "$2" \
        "${BASE_URL}$1" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# Helper: GET anonimo
anon_get() {
    curl -s -w '\n%{http_code}' \
        "${BASE_URL}$1" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# --- 1. Lista account email ---
echo ""
echo "-- 1. GET /email-accounts/ --"
auth_get "/api/v1/amm-software/email-accounts/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Lista account email: count=$COUNT"
else
    log_fail "Lista account email: HTTP $LAST_STATUS"
fi

# --- 2. Lista template email ---
echo ""
echo "-- 2. GET /email-templates/ --"
auth_get "/api/v1/amm-software/email-templates/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Lista template email: count=$COUNT"
else
    log_fail "Lista template email: HTTP $LAST_STATUS"
fi

# --- 3. Filtro template per codice ---
echo ""
echo "-- 3. GET /email-templates/?codice=INVITO_OPERATORE --"
auth_get "/api/v1/amm-software/email-templates/?codice=INVITO_OPERATORE"
TEMPLATE_ID=""
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    TEMPLATE_ID=$(json_get "$LAST_BODY" "data.results.0.id")
    log_ok "Template INVITO_OPERATORE: count=$COUNT id=$TEMPLATE_ID"
else
    log_fail "Template filtro codice: HTTP $LAST_STATUS"
fi

# --- 4. Preview template ---
echo ""
echo "-- 4. POST /email-templates/{id}/preview/ --"
if [[ -n "$TEMPLATE_ID" ]]; then
    auth_post "/api/v1/amm-software/email-templates/${TEMPLATE_ID}/preview/" \
              '{"variabili":{"nome":"Mario","cognome":"Rossi","azienda":"ZeroErp"}}'
    if [[ "$LAST_STATUS" == "200" ]]; then
        OGGETTO=$(json_get "$LAST_BODY" "data.oggetto")
        log_ok "Preview: oggetto=$(echo "$OGGETTO" | head -c 50)"
    else
        log_fail "Preview: HTTP $LAST_STATUS"
        log_info "$(echo "$LAST_BODY" | head -c 200)"
    fi
else
    log_info "Skipped (nessun template trovato)"
fi

# --- 5. Lista log email ---
echo ""
echo "-- 5. GET /email-log/ --"
auth_get "/api/v1/amm-software/email-log/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Log email: count=$COUNT"
else
    log_fail "Log email: HTTP $LAST_STATUS"
fi

# --- 6. Prepara bozza outbox ---
echo ""
echo "-- 6. POST /core/email/prepare/ --"
# `ambito` e' obbligatorio e senza default dal 2026-09-05 (SISTEMA e' trattato
# come segreto di sistema dalla RLS): una notifica scritta da un utente e'
# OPERATORE, e prende l'emittente attivo di chi la crea.
auth_post "/api/v1/core/email/prepare/" \
          '{"codice_template":"NOTIFICA_GENERICA","destinatario":"test@example.com","ambito":"OPERATORE","variabili":{"oggetto_custom":"Test","corpo_custom":"Corpo"}}'
OUTBOX_ID=""
if [[ "$LAST_STATUS" == "200" ]]; then
    OUTBOX_ID=$(json_get "$LAST_BODY" "data.id")
    log_ok "Bozza creata: id=$OUTBOX_ID"
else
    log_fail "Prepara bozza: HTTP $LAST_STATUS"
    log_info "$(echo "$LAST_BODY" | head -c 200)"
fi

# --- 7. Lista outbox ---
echo ""
echo "-- 7. GET /core/email/outbox/ --"
auth_get "/api/v1/core/email/outbox/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Outbox: count=$COUNT"
else
    log_fail "Outbox: HTTP $LAST_STATUS"
fi

# --- 8. Annulla bozza ---
echo ""
echo "-- 8. POST /core/email/outbox/{id}/cancel/ --"
if [[ -n "$OUTBOX_ID" ]]; then
    auth_post "/api/v1/core/email/outbox/${OUTBOX_ID}/cancel/" '{}'
    if [[ "$LAST_STATUS" == "200" ]]; then
        STATO=$(json_get "$LAST_BODY" "data.stato")
        if [[ "$STATO" == "CANCELLED" ]]; then
            log_ok "Bozza annullata: stato=$STATO"
        else
            log_fail "Stato atteso CANCELLED, ricevuto $STATO"
        fi
    else
        log_fail "Annulla bozza: HTTP $LAST_STATUS"
    fi
else
    log_info "Skipped (nessuna bozza)"
fi

# --- 9. Reset password request ---
echo ""
echo "-- 9. POST /auth/password-reset-request/ --"
anon_post "/api/v1/auth/password-reset-request/" '{"identificativo":"inesistente@nowhere.test"}'
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "Reset request: HTTP 200 (risposta opaca)"
elif [[ "$LAST_STATUS" == "429" ]]; then
    log_ok "Reset request: HTTP 429 (rate limited)"
else
    log_fail "Reset request: HTTP $LAST_STATUS"
    log_info "$(echo "$LAST_BODY" | head -c 200)"
fi

# --- 10. Validate token invalido ---
echo ""
echo "-- 10. GET /auth/password-reset-validate/token-inesistente/ --"
anon_get "/api/v1/auth/password-reset-validate/token-inesistente/"
if [[ "$LAST_STATUS" == "200" ]]; then
    VALID=$(json_get "$LAST_BODY" "data.valid")
    if [[ "$VALID" == "False" ]]; then
        log_ok "Token invalido: valid=False"
    else
        log_fail "Atteso valid=False, ricevuto $VALID"
    fi
else
    log_fail "Validate: HTTP $LAST_STATUS"
fi

# --- 11. Confirm con token invalido ---
echo ""
echo "-- 11. POST /auth/password-reset-confirm/ --"
anon_post "/api/v1/auth/password-reset-confirm/" '{"token":"bad","new_password":"Test123!","new_password_confirm":"Test123!"}'
if [[ "$LAST_STATUS" == "400" ]]; then
    log_ok "Confirm token invalido: HTTP 400"
elif [[ "$LAST_STATUS" == "429" ]]; then
    log_ok "Confirm: HTTP 429 (rate limited)"
else
    log_fail "Confirm: HTTP $LAST_STATUS"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]]
