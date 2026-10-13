#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test per audit sessioni, request logging e token blacklist
# Uso: ./scripts/smoke-test-audit-logging.sh [password]
# ------------------------------------------------------------
# Indice test (0..5):
#  0) Login JWT → verifica record in dbops.sessioni_utente (LOGIN)
#  1) Token refresh → verifica record in dbops.sessioni_utente (REFRESH)
#  2) Request log → verifica record in dbops.request_log
#  3) Token blacklist → verifica refresh token ruotato (vecchio blacklistato)
#  4) Login fallito → nessun record sessione
#  5) Request log error_code → verifica estrazione codice errore
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
LAST_STATUS=""
LAST_BODY=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE ${TMPFILE}.hdr" EXIT

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
        d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# backend/scripts/tests -> backend: DUE livelli (come jwt-audit-guc e listini-v5).
# Con uno solo cercava backend/scripts/manage-env.sh, la query tornava vuota e
# `set -e` chiudeva lo smoke al passo 0 senza una parola.
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

db_query() {
    local sql="$1"
    "${BACKEND_DIR}/manage-env.sh" dbshell -- -t -A -c "$sql" 2>/dev/null | grep -v '^$'
}

# ================================================================
echo ""
echo "========================================="
echo " Smoke test Audit / Logging / Blacklist"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Login JWT + verifica sessione ---
echo ""
echo "-- 0. Login JWT → sessione audit --"

# Conta sessioni prima
SESS_BEFORE=$(db_query "SELECT count(*) FROM dbops.sessioni_utente WHERE evento='LOGIN'" | tail -1)

# Login vero (-D lo implica): il passo conta il record LOGIN che apre.
smoke_login -D "${TMPFILE}.hdr"
# Il refresh e' nel cookie HttpOnly, non nel corpo.
REFRESH=$(refresh_dal_set_cookie "${TMPFILE}.hdr")
log_ok "JWT ottenuto (HTTP 200)"

# Verifica sessione inserita
sleep 0.5
SESS_AFTER=$(db_query "SELECT count(*) FROM dbops.sessioni_utente WHERE evento='LOGIN'" | tail -1)
if [[ "$SESS_AFTER" -gt "$SESS_BEFORE" ]]; then
    log_ok "Record LOGIN inserito in sessioni_utente ($SESS_BEFORE → $SESS_AFTER)"
else
    log_fail "Nessun record LOGIN inserito in sessioni_utente ($SESS_BEFORE → $SESS_AFTER)"
fi

# Verifica jti popolato nell'ultimo record
LAST_JTI=$(db_query "SELECT jti FROM dbops.sessioni_utente WHERE evento='LOGIN' ORDER BY data_insert DESC LIMIT 1" | tail -1)
if [[ -n "$LAST_JTI" && "$LAST_JTI" != "None" ]]; then
    log_ok "jti popolato nell'ultimo record LOGIN: ${LAST_JTI:0:20}..."
else
    log_fail "jti non popolato nell'ultimo record LOGIN: '$LAST_JTI'"
fi

# --- 1. Token refresh → sessione audit ---
echo ""
echo "-- 1. Token refresh → sessione audit --"

SESS_BEFORE_R=$(db_query "SELECT count(*) FROM dbops.sessioni_utente WHERE evento='REFRESH'" | tail -1)

curl_refresh "$REFRESH" -s -w '\n%{http_code}' -D "${TMPFILE}.hdr" -X POST \
    "${BASE_URL}/api/v1/admin/token/refresh/" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")
LAST_BODY=$(sed '$d' "$TMPFILE")

if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "Token refresh (HTTP 200)"
    # Il refresh ruotato torna nel cookie.
    NEW_REFRESH=$(refresh_dal_set_cookie "${TMPFILE}.hdr")
else
    log_fail "Token refresh fallito (HTTP $LAST_STATUS)"
    NEW_REFRESH=""
fi

sleep 0.5
SESS_AFTER_R=$(db_query "SELECT count(*) FROM dbops.sessioni_utente WHERE evento='REFRESH'" | tail -1)
if [[ "$SESS_AFTER_R" -gt "$SESS_BEFORE_R" ]]; then
    log_ok "Record REFRESH inserito in sessioni_utente ($SESS_BEFORE_R → $SESS_AFTER_R)"
else
    log_fail "Nessun record REFRESH inserito ($SESS_BEFORE_R → $SESS_AFTER_R)"
fi

# --- 2. Request log → verifica record ---
echo ""
echo "-- 2. Request log → verifica record --"

RL_BEFORE=$(db_query "SELECT count(*) FROM dbops.request_log" | tail -1)

# Facciamo una API call autenticata
curl -s -w '\n%{http_code}' \
    -H "Authorization: Bearer ${TOKEN}" \
    "${BASE_URL}/api/v1/core/lookup/codici/?rel=config.stati_pratiche" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")

if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "API call autenticata (HTTP 200)"
else
    log_fail "API call fallita (HTTP $LAST_STATUS)"
fi

sleep 0.5
RL_AFTER=$(db_query "SELECT count(*) FROM dbops.request_log" | tail -1)
if [[ "$RL_AFTER" -gt "$RL_BEFORE" ]]; then
    log_ok "Record inserito in request_log ($RL_BEFORE → $RL_AFTER)"
else
    log_fail "Nessun record inserito in request_log ($RL_BEFORE → $RL_AFTER)"
fi

# Verifica contenuto ultimo record
LAST_RL=$(db_query "SELECT method, path, status_code, auth_user_id FROM dbops.request_log ORDER BY data_insert DESC LIMIT 1" | tail -1)
log_info "Ultimo request_log: $LAST_RL"

# --- 3. Token blacklist → vecchio refresh blacklistato ---
echo ""
echo "-- 3. Token blacklist → rotation --"

if [[ -n "$NEW_REFRESH" ]]; then
    # Il vecchio refresh token dovrebbe essere blacklistato dopo la rotation
    # Proviamo a usare il vecchio refresh token — deve fallire
    curl_refresh "$REFRESH" -s -w '\n%{http_code}' -X POST \
        "${BASE_URL}/api/v1/admin/token/refresh/" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")

    if [[ "$LAST_STATUS" == "401" ]]; then
        log_ok "Vecchio refresh token rifiutato (HTTP 401 — blacklistato)"
    else
        log_fail "Vecchio refresh token accettato (HTTP $LAST_STATUS — doveva essere 401)"
    fi
else
    log_fail "Impossibile testare blacklist: refresh non disponibile"
fi

# --- 4. Login fallito → nessun record sessione ---
echo ""
echo "-- 4. Login fallito → nessun record --"

SESS_BEFORE_F=$(db_query "SELECT count(*) FROM dbops.sessioni_utente" | tail -1)

# login esplicito: il passo prova proprio il RIFIUTO del login (401) e che non
# apra sessioni; smoke_login uscirebbe al primo errore.
curl_login -s -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"password_errata_12345\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")

if [[ "$LAST_STATUS" == "401" ]]; then
    log_ok "Login rifiutato (HTTP 401)"
else
    log_fail "Login con password errata: HTTP $LAST_STATUS (atteso 401)"
fi

sleep 0.5
SESS_AFTER_F=$(db_query "SELECT count(*) FROM dbops.sessioni_utente" | tail -1)
if [[ "$SESS_AFTER_F" == "$SESS_BEFORE_F" ]]; then
    log_ok "Nessun record sessione per login fallito ($SESS_BEFORE_F = $SESS_AFTER_F)"
else
    log_fail "Record sessione inserito per login fallito ($SESS_BEFORE_F → $SESS_AFTER_F)"
fi

# --- 5. Request log error_code ---
echo ""
echo "-- 5. Request log → error_code su errore --"

RL_BEFORE_E=$(db_query "SELECT count(*) FROM dbops.request_log WHERE error_code IS NOT NULL" | tail -1)

# Facciamo una chiamata che genera errore con error_code
curl -s -w '\n%{http_code}' \
    -H "Authorization: Bearer ${TOKEN}" \
    "${BASE_URL}/api/v1/core/lookup/codici/?rel=schema.tabella_inesistente" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")

if [[ "$LAST_STATUS" == "400" ]]; then
    log_ok "API errore con error_code (HTTP 400)"
else
    log_fail "HTTP $LAST_STATUS (atteso 400)"
fi

sleep 0.5
RL_AFTER_E=$(db_query "SELECT count(*) FROM dbops.request_log WHERE error_code IS NOT NULL" | tail -1)
if [[ "$RL_AFTER_E" -gt "$RL_BEFORE_E" ]]; then
    log_ok "Record con error_code inserito in request_log ($RL_BEFORE_E → $RL_AFTER_E)"
    LAST_EC=$(db_query "SELECT error_code FROM dbops.request_log WHERE error_code IS NOT NULL ORDER BY data_insert DESC LIMIT 1" | tail -1)
    log_info "Ultimo error_code: $LAST_EC"
else
    log_fail "Nessun record con error_code ($RL_BEFORE_E → $RL_AFTER_E)"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
