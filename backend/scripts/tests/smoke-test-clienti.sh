#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Clienti
# Uso: ./scripts/tests/smoke-test-clienti.sh [password]
# Prerequisiti: almeno un soggetto nel DB (lo smoke-test-soggetti.sh ne crea uno)
# ------------------------------------------------------------
# Indice test (0..8):
#  0) Autenticazione JWT
#  1) Lookup utility ammesse per creazione manuale
#  2) Lista clienti (paginata, vuota o con dati)
#  3) Lista clienti con search
#  4) Lista clienti con filtro utility
#  5) Crea cliente manuale (soggetto esistente + utility manifatturiero)
#  6) Dettaglio cliente creato
#  7) Crea cliente manuale — utility GAS bloccata (atteso errore)
#  8) Crea cliente manuale — duplicato istanza (atteso errore)
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
EXTRACTED=""
LAST_STATUS=""
LAST_BODY=""

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
        if k.isdigit():
            d = d[int(k)]
        else:
            d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' \
            -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    fi
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

check() {
    local label="$1" expected="$2" json_expr="${3:-}"
    if [[ "$LAST_STATUS" == "$expected" ]]; then
        log_ok "$label (HTTP $LAST_STATUS)"
    else
        log_fail "$label — atteso HTTP $expected, ricevuto $LAST_STATUS"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
        return 1
    fi
    if [[ -n "$json_expr" ]]; then
        EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    fi
    return 0
}

# ================================================================
echo ""
echo "========================================="
echo " Smoke test API Clienti"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

if [[ -z "$PASSWORD" ]]; then
    echo -n "Password per utente '$USERNAME': "
    read -rs PASSWORD
    echo ""
fi

curl -s -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null

AUTH_STATUS=$(tail -1 "$TMPFILE")
AUTH_BODY=$(sed '$d' "$TMPFILE")

if [[ "$AUTH_STATUS" != "200" ]]; then
    echo -e "${RED}ERRORE: autenticazione fallita (HTTP $AUTH_STATUS)${NC}"
    echo "$AUTH_BODY" | head -c 300
    exit 1
fi

TOKEN=$(json_get "$AUTH_BODY" ".access")
if [[ -z "$TOKEN" ]]; then
    echo -e "${RED}ERRORE: token JWT non trovato nella risposta${NC}"
    exit 1
fi
log_ok "Token JWT ottenuto"

# --- 1. Lookup utility ammesse ---
echo ""
echo "-- 1. Lookup utility ammesse per creazione manuale --"
do_curl GET "/api/v1/anagrafiche/utilities/manual-lookup/"
check "Lookup utility manuali" "200" ".data.results"
UTIL_COUNT=$(echo "$LAST_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',{}).get('results',[])))" 2>/dev/null || echo "0")
log_info "Utility ammesse: $UTIL_COUNT"

# Prendi la prima utility ammessa (richiede_pdp=false)
MANUAL_UTIL_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
MANUAL_UTIL_DESC=$(json_get "$LAST_BODY" ".data.results.0.descrizione")
if [[ -z "$MANUAL_UTIL_ID" || "$MANUAL_UTIL_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessuna utility con richiede_pdp=false trovata${NC}"
    echo "       Verificare seed config.utilities"
    exit 1
fi
log_info "Utility per test: id=$MANUAL_UTIL_ID ($MANUAL_UTIL_DESC)"

# --- Trova un soggetto esistente per i test ---
echo ""
echo "-- Prerequisito: trova soggetto --"
do_curl GET "/api/v1/anagrafiche/soggetti/?limit=1"
SOGG_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -z "$SOGG_ID" || "$SOGG_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessun soggetto nel DB — eseguire prima smoke-test-soggetti.sh${NC}"
    exit 1
fi
SOGG_NOME=$(json_get "$LAST_BODY" ".data.results.0.ragione_sociale_completa")
log_info "Soggetto per test: id=$SOGG_ID ($SOGG_NOME)"

# --- 2. Lista clienti ---
echo ""
echo "-- 2. Lista clienti --"
do_curl GET "/api/v1/anagrafiche/clienti/?limit=5"
check "Lista clienti" "200" ".data.count"
CLI_COUNT="$EXTRACTED"
log_info "Totale clienti: $CLI_COUNT"

# --- 3. Lista clienti con search ---
echo ""
echo "-- 3. Lista clienti con search --"
do_curl GET "/api/v1/anagrafiche/clienti/?search=inesistente999&limit=5"
check "Search clienti" "200" ".data.count"
log_info "Clienti trovati con search: $EXTRACTED"

# --- 4. Lista clienti con filtro utility ---
echo ""
echo "-- 4. Lista clienti filtro utility --"
do_curl GET "/api/v1/anagrafiche/clienti/?utility_id=${MANUAL_UTIL_ID}&limit=5"
check "Filtro utility" "200" ".data.count"
log_info "Clienti per utility $MANUAL_UTIL_ID: $EXTRACTED"

# --- 5. Crea cliente manuale ---
echo ""
echo "-- 5. Crea cliente manuale --"
do_curl POST "/api/v1/anagrafiche/clienti/" \
    "{
        \"soggetto_id\": \"${SOGG_ID}\",
        \"utility_id\": ${MANUAL_UTIL_ID}
    }"
NEW_CLI_ID=""
if [[ "$LAST_STATUS" == "200" ]]; then
    NEW_CLI_ID=$(json_get "$LAST_BODY" ".data.id")
    log_ok "Cliente creato (HTTP 200)"
    log_info "Cliente id=$NEW_CLI_ID"
    log_info "Istanza id=$(json_get "$LAST_BODY" ".data.istanza_utility_id")"
    log_info "BA id=$(json_get "$LAST_BODY" ".data.billing_account_id")"
elif [[ "$LAST_STATUS" == "409" ]]; then
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    if [[ "$ERRCODE" == "E_ANAG_DUPLICATO" ]]; then
        log_info "Cliente gia' esistente per questo soggetto/utility (duplicato OK)"
        ((PASS++)) || true
    else
        log_fail "Crea cliente — errore inatteso: $ERRCODE"
    fi
else
    log_fail "Crea cliente — atteso HTTP 200 o 409, ricevuto $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 6. Dettaglio cliente ---
echo ""
echo "-- 6. Dettaglio cliente --"
if [[ -n "$NEW_CLI_ID" && "$NEW_CLI_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/clienti/${NEW_CLI_ID}/"
    check "Dettaglio cliente" "200" ".data.stato_codice"
    log_info "Stato: $EXTRACTED"
    log_info "BA codice: $(json_get "$LAST_BODY" ".data.ba_codice")"
    log_info "Utility: $(json_get "$LAST_BODY" ".data.utility_descrizione")"
    log_info "Ragione sociale: $(json_get "$LAST_BODY" ".data.ragione_sociale_completa")"
else
    log_info "Skipped (creazione non ha prodotto nuovo id)"
fi

# --- 7. Crea cliente — utility GAS bloccata ---
echo ""
echo "-- 7. Crea cliente utility GAS (richiede_pdp=true) --"
# Trova utility GAS
GAS_UTIL_ID=""
do_curl GET "/api/v1/core/lookup/codici/?rel=config.utilities&search=GAS&limit=1"
GAS_UTIL_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -n "$GAS_UTIL_ID" && "$GAS_UTIL_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/clienti/" \
        "{
            \"soggetto_id\": \"${SOGG_ID}\",
            \"utility_id\": ${GAS_UTIL_ID}
        }"
    if [[ "$LAST_STATUS" == "400" ]]; then
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        if [[ "$ERRCODE" == "E_ANAG_VALIDAZIONE" ]]; then
            log_ok "Utility GAS bloccata per creazione manuale (HTTP 400, $ERRCODE)"
        else
            log_fail "Errore inatteso: $ERRCODE"
        fi
    else
        log_fail "Utility GAS — atteso HTTP 400, ricevuto $LAST_STATUS"
    fi
else
    log_info "Skipped — utility GAS non trovata nel DB"
fi

# --- 8. Crea cliente duplicato (stessa istanza) ---
echo ""
echo "-- 8. Crea cliente duplicato --"
if [[ -n "$NEW_CLI_ID" && "$NEW_CLI_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/clienti/" \
        "{
            \"soggetto_id\": \"${SOGG_ID}\",
            \"utility_id\": ${MANUAL_UTIL_ID}
        }"
    if [[ "$LAST_STATUS" == "409" ]]; then
        log_ok "Duplicato rilevato (HTTP 409)"
    elif [[ "$LAST_STATUS" == "400" ]]; then
        log_ok "Duplicato rilevato (HTTP 400)"
    else
        log_fail "Duplicato — atteso HTTP 409 o 400, ricevuto $LAST_STATUS"
    fi
else
    log_info "Skipped — test 5 non ha creato un nuovo cliente"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
