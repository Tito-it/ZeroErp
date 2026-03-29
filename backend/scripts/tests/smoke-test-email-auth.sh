#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test per sistema email, cambio password, reset password
# Uso: ./scripts/tests/smoke-test-email-auth.sh [password]
# Prerequisiti: utente ADMIN con accesso API, DB con tabelle email
# ------------------------------------------------------------
# Indice test (0..11):
#  0) Login JWT admin
#  1) GET /amm-software/email-accounts/ → lista account
#  2) GET /amm-software/email-templates/ → lista template
#  3) GET /amm-software/email-templates/?codice=INVITO_OPERATORE → filtro codice
#  4) POST /amm-software/email-templates/{id}/preview/ → rendering variabili
#  5) GET /amm-software/email-log/ → lista log (puo' essere vuota)
#  6) POST /core/email/prepare/ → prepara bozza outbox
#  7) GET /core/email/outbox/ → lista bozze operatore
#  8) POST /core/email/outbox/{id}/cancel/ → annulla bozza
#  9) POST /auth/password-reset-request/ → richiesta reset (sempre 200)
# 10) GET /auth/password-reset-validate/token-inesistente/ → token invalido
# 11) POST /auth/password-reset-confirm/ → token invalido (errore atteso)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

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

do_get() {
    local path="$1"
    curl -s -w '\n%{http_code}' \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        "${BASE_URL}${path}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

do_post() {
    local path="$1" body="${2:-{}}"
    curl -s -w '\n%{http_code}' \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d "$body" \
        "${BASE_URL}${path}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

do_post_anon() {
    local path="$1" body="${2:-{}}"
    curl -s -w '\n%{http_code}' \
        -H "Content-Type: application/json" \
        -d "$body" \
        "${BASE_URL}${path}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

do_get_anon() {
    local path="$1"
    curl -s -w '\n%{http_code}' \
        "${BASE_URL}${path}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
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

if [[ -z "$PASSWORD" ]]; then
    echo -n "Password per utente '$USERNAME': "
    read -rs PASSWORD
    echo ""
fi

curl -s -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/auth/token/" > "$TMPFILE" 2>/dev/null

AUTH_STATUS=$(tail -1 "$TMPFILE")
AUTH_BODY=$(sed '$d' "$TMPFILE")

if [[ "$AUTH_STATUS" != "200" ]]; then
    echo -e "${RED}ERRORE: autenticazione fallita (HTTP $AUTH_STATUS)${NC}"
    echo "$AUTH_BODY" | head -c 300
    exit 1
fi

ACCESS_TOKEN=$(json_get "$AUTH_BODY" "access")
log_ok "Login riuscito (HTTP $AUTH_STATUS)"

# Verifica flag password_change_required (se presente)
PW_FLAG=$(json_get "$AUTH_BODY" "password_change_required")
if [[ -n "$PW_FLAG" && "$PW_FLAG" != "" ]]; then
    log_info "password_change_required=$PW_FLAG"
fi

# --- 1. Lista account email ---
echo ""
echo "-- 1. GET /email-accounts/ --"
do_get "/api/v1/amm-software/email-accounts/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Lista account email: count=$COUNT"
else
    log_fail "Lista account email: HTTP $LAST_STATUS"
fi

# --- 2. Lista template email ---
echo ""
echo "-- 2. GET /email-templates/ --"
do_get "/api/v1/amm-software/email-templates/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Lista template email: count=$COUNT"
else
    log_fail "Lista template email: HTTP $LAST_STATUS"
fi

# --- 3. Filtro template per codice ---
echo ""
echo "-- 3. GET /email-templates/?codice=INVITO_OPERATORE --"
do_get "/api/v1/amm-software/email-templates/?codice=INVITO_OPERATORE"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Template INVITO_OPERATORE: count=$COUNT"
    # Salva ID per preview
    TEMPLATE_ID=$(json_get "$LAST_BODY" "data.results.0.id")
else
    log_fail "Template filtro codice: HTTP $LAST_STATUS"
    TEMPLATE_ID=""
fi

# --- 4. Preview template ---
echo ""
echo "-- 4. POST /email-templates/{id}/preview/ --"
if [[ -n "$TEMPLATE_ID" && "$TEMPLATE_ID" != "" ]]; then
    do_post "/api/v1/amm-software/email-templates/${TEMPLATE_ID}/preview/" \
        '{"variabili":{"nome":"Mario","cognome":"Rossi","azienda":"ZeroErp","link":"https://example.com","scadenza_ore":"72","invitato_da":"Admin"}}'
    if [[ "$LAST_STATUS" == "200" ]]; then
        OGGETTO=$(json_get "$LAST_BODY" "data.oggetto")
        log_ok "Preview: oggetto='$OGGETTO'"
    else
        log_fail "Preview template: HTTP $LAST_STATUS"
    fi
else
    log_info "Skipped (nessun template trovato)"
fi

# --- 5. Lista log email ---
echo ""
echo "-- 5. GET /email-log/ --"
do_get "/api/v1/amm-software/email-log/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Log email: count=$COUNT"
else
    log_fail "Log email: HTTP $LAST_STATUS"
fi

# --- 6. Prepara bozza outbox ---
echo ""
echo "-- 6. POST /core/email/prepare/ --"
do_post "/api/v1/core/email/prepare/" \
    '{"codice_template":"NOTIFICA_GENERICA","destinatario":"test@example.com","variabili":{"oggetto_custom":"Test smoke","corpo_custom":"Corpo di test"}}'
if [[ "$LAST_STATUS" == "200" ]]; then
    OUTBOX_ID=$(json_get "$LAST_BODY" "data.id")
    log_ok "Bozza creata: id=$OUTBOX_ID"
else
    log_fail "Prepara bozza: HTTP $LAST_STATUS"
    log_info "$LAST_BODY" | head -c 300
    OUTBOX_ID=""
fi

# --- 7. Lista outbox ---
echo ""
echo "-- 7. GET /core/email/outbox/ --"
do_get "/api/v1/core/email/outbox/"
if [[ "$LAST_STATUS" == "200" ]]; then
    COUNT=$(json_get "$LAST_BODY" "data.count")
    log_ok "Outbox: count=$COUNT"
else
    log_fail "Outbox lista: HTTP $LAST_STATUS"
fi

# --- 8. Annulla bozza ---
echo ""
echo "-- 8. POST /core/email/outbox/{id}/cancel/ --"
if [[ -n "$OUTBOX_ID" && "$OUTBOX_ID" != "" ]]; then
    do_post "/api/v1/core/email/outbox/${OUTBOX_ID}/cancel/"
    if [[ "$LAST_STATUS" == "200" ]]; then
        STATO=$(json_get "$LAST_BODY" "data.stato")
        if [[ "$STATO" == "CANCELLED" ]]; then
            log_ok "Bozza annullata: stato=$STATO"
        else
            log_fail "Bozza annullata: stato atteso CANCELLED, ricevuto $STATO"
        fi
    else
        log_fail "Annulla bozza: HTTP $LAST_STATUS"
    fi
else
    log_info "Skipped (nessuna bozza creata)"
fi

# --- 9. Reset password request (anonimo) ---
echo ""
echo "-- 9. POST /auth/password-reset-request/ --"
do_post_anon "/api/v1/auth/password-reset-request/" \
    '{"email":"inesistente@nowhere.test"}'
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "Reset request: HTTP 200 (risposta opaca, email inesistente)"
else
    log_fail "Reset request: HTTP $LAST_STATUS (atteso 200)"
fi

# --- 10. Reset password validate (token invalido) ---
echo ""
echo "-- 10. GET /auth/password-reset-validate/token-inesistente/ --"
do_get_anon "/api/v1/auth/password-reset-validate/token-inesistente/"
if [[ "$LAST_STATUS" == "200" ]]; then
    VALID=$(json_get "$LAST_BODY" "data.valid")
    if [[ "$VALID" == "False" ]]; then
        log_ok "Token invalido: valid=False"
    else
        log_fail "Token invalido: atteso valid=False, ricevuto valid=$VALID"
    fi
else
    log_fail "Validate token: HTTP $LAST_STATUS"
fi

# --- 11. Reset password confirm (token invalido → errore) ---
echo ""
echo "-- 11. POST /auth/password-reset-confirm/ --"
do_post_anon "/api/v1/auth/password-reset-confirm/" \
    '{"token":"token-inesistente","new_password":"NuovaPass123!","new_password_confirm":"NuovaPass123!"}'
if [[ "$LAST_STATUS" == "400" ]]; then
    CODE=$(json_get "$LAST_BODY" "error.code")
    log_ok "Confirm con token invalido: HTTP 400, code=$CODE"
elif [[ "$LAST_STATUS" == "429" ]]; then
    log_ok "Rate limited (429) — corretto per test ripetuti"
else
    log_fail "Confirm token invalido: HTTP $LAST_STATUS (atteso 400)"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
