#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Anagrafiche (indirizzi, toponomastica, comuni)
# Uso: ./scripts/tests/smoke-test-anagrafiche.sh [password]
# ------------------------------------------------------------
# Indice test (0..10):
#  0) Autenticazione JWT
#  1) Lista toponomastica (paginata)
#  2) Crea toponomastica
#  3) Modifica toponomastica
#  4) Lista comuni (paginata con search)
#  5) Lista indirizzi (paginata)
#  6) Lista indirizzi con filtro comune_id
#  7) Codici postali per comune
#  8) Crea indirizzo (via esistente)
#  9) Dettaglio indirizzo creato
# 10) Modifica indirizzo
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Gunicorn diretto in HTTP: ci si dichiara HTTPS come Nginx (redirect di Django).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"
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
echo " Smoke test API Anagrafiche"
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

# --- 1. Lista toponomastica ---
echo ""
echo "-- 1. Lista toponomastica --"
do_curl GET "/api/v1/anagrafiche/toponomastica/?limit=5"
check "Lista toponomastica" "200" ".data.count"
TOPO_COUNT="$EXTRACTED"
log_info "Totale toponomastica: $TOPO_COUNT"

# --- 2. Crea toponomastica ---
echo ""
echo "-- 2. Crea toponomastica --"
TOPO_NAME="SmokeTest_$(date +%s)"
do_curl POST "/api/v1/anagrafiche/toponomastica/" \
    "{\"descrizione\":\"$TOPO_NAME\"}"
check "Crea toponomastica '$TOPO_NAME'" "200" ".data.id"
TOPO_ID="$EXTRACTED"
log_info "Creato id=$TOPO_ID"

# --- 3. Modifica toponomastica ---
echo ""
echo "-- 3. Modifica toponomastica --"
do_curl PATCH "/api/v1/anagrafiche/toponomastica/${TOPO_ID}/" \
    "{\"attivo\":false}"
check "Disattiva toponomastica id=$TOPO_ID" "200"

# --- 4. Lista comuni ---
echo ""
echo "-- 4. Lista comuni (search 'Milano') --"
do_curl GET "/api/v1/anagrafiche/comuni/?search=Milano&limit=5"
check "Lista comuni con search" "200" ".data.count"
COMUNI_COUNT="$EXTRACTED"
log_info "Comuni trovati: $COMUNI_COUNT"

# Estrai primo comune_id per test successivi
FIRST_COMUNE_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -n "$FIRST_COMUNE_ID" && "$FIRST_COMUNE_ID" != "" ]]; then
    log_info "Primo comune id=$FIRST_COMUNE_ID"
else
    log_fail "Nessun comune trovato per i test successivi"
    FIRST_COMUNE_ID=""
fi

# --- 5. Lista indirizzi ---
echo ""
echo "-- 5. Lista indirizzi --"
do_curl GET "/api/v1/anagrafiche/indirizzi/?limit=5"
check "Lista indirizzi" "200" ".data.count"
IND_COUNT="$EXTRACTED"
log_info "Totale indirizzi: $IND_COUNT"

# --- 6. Lista indirizzi con filtro comune_id ---
echo ""
echo "-- 6. Lista indirizzi filtro comune --"
if [[ -n "$FIRST_COMUNE_ID" ]]; then
    do_curl GET "/api/v1/anagrafiche/indirizzi/?comune_id=${FIRST_COMUNE_ID}&limit=5"
    check "Indirizzi filtro comune_id=$FIRST_COMUNE_ID" "200" ".data.count"
    log_info "Indirizzi per comune: $EXTRACTED"
else
    log_info "Skipped (nessun comune disponibile)"
fi

# --- 7. Codici postali per comune ---
echo ""
echo "-- 7. Codici postali per comune --"
if [[ -n "$FIRST_COMUNE_ID" ]]; then
    do_curl GET "/api/v1/anagrafiche/codici-postali/?comune_id=${FIRST_COMUNE_ID}"
    check "Codici postali comune_id=$FIRST_COMUNE_ID" "200"
    CAP_COUNT=$(json_get "$LAST_BODY" ".data.results" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    log_info "CAP trovati: $CAP_COUNT"
else
    log_info "Skipped (nessun comune disponibile)"
fi

# --- 8. Crea indirizzo (richiede stradario_id valido) ---
echo ""
echo "-- 8. Crea indirizzo --"
# Cerca un indirizzo esistente per ottenere uno stradario_id
STRADARIO_ID=""
if [[ "$IND_COUNT" != "0" && -n "$IND_COUNT" ]]; then
    STRADARIO_ID=$(json_get "$LAST_BODY" ".data.results.0.stradario_id" 2>/dev/null || echo "")
fi

# Se non ci sono indirizzi ma abbiamo un comune, cerca nello stradario
if [[ -z "$STRADARIO_ID" && -n "$FIRST_COMUNE_ID" ]]; then
    do_curl GET "/api/v1/core/search/stradario/?comune_id=${FIRST_COMUNE_ID}&search=via&limit=1"
    if [[ "$LAST_STATUS" == "200" ]]; then
        STRADARIO_ID=$(json_get "$LAST_BODY" ".data.results.0.id" 2>/dev/null || echo "")
    fi
fi

if [[ -n "$STRADARIO_ID" && "$STRADARIO_ID" != "" ]]; then
    CIVICO_SMOKE=$((RANDOM % 9000 + 1000))
    do_curl POST "/api/v1/anagrafiche/indirizzi/" \
        "{\"stradario_id\":${STRADARIO_ID},\"civico\":${CIVICO_SMOKE},\"interno\":\"SMOKE\"}"
    check "Crea indirizzo civico=$CIVICO_SMOKE" "200" ".data.indirizzo_dettaglio_id"
    CREATED_IND_ID="$EXTRACTED"
    log_info "Indirizzo creato/trovato id=$CREATED_IND_ID"

    # --- 9. Dettaglio indirizzo ---
    echo ""
    echo "-- 9. Dettaglio indirizzo --"
    do_curl GET "/api/v1/anagrafiche/indirizzi/${CREATED_IND_ID}/"
    check "Dettaglio indirizzo id=$CREATED_IND_ID" "200"
    IND_NORM=$(json_get "$LAST_BODY" ".data.indirizzo_normalizzato")
    log_info "Indirizzo: $IND_NORM"

    # --- 10. Modifica indirizzo ---
    echo ""
    echo "-- 10. Modifica indirizzo --"
    do_curl PATCH "/api/v1/anagrafiche/indirizzi/${CREATED_IND_ID}/" \
        "{\"interno\":\"SMOKE_UPD\"}"
    check "Modifica indirizzo id=$CREATED_IND_ID" "200"
else
    log_info "Skipped test 8-10 (nessuno stradario_id disponibile)"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
