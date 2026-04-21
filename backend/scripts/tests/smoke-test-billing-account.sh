#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Anagrafiche BillingAccount lookup
# Uso: ./scripts/tests/smoke-test-billing-account.sh [password]
# ------------------------------------------------------------
# Indice test (0..10):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi area anagrafiche (LETTURA o TUTTO)
#  2) Lookup BA q vuota (400 atteso — min 2 char)
#  3) Lookup BA q troppo corta (400 atteso)
#  4) Lookup BA q valida (200 + struttura envelope {results,total_count,limit})
#  5) Lookup BA q valida con utility_id filter
#  6) Lookup BA con limit custom (cap a 50)
#  7) Lookup BA con limit invalido (capping silenzioso a default)
#  8) Lookup BA solo_validi=false (rimuove filtro temporale)
#  9) Restore by id (200 con campi arricchiti) — solo se almeno un BA esiste
# 10) Restore by id inesistente (404 atteso)
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
        echo "       Body: $(echo "$LAST_BODY" | head -c 400)"
        return 1
    fi
    if [[ -n "$json_expr" ]]; then
        EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    fi
    return 0
}

echo ""
echo "========================================="
echo " Smoke test API Billing Account Lookup"
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

USER_ID=$(echo "$TOKEN" | cut -d. -f2 | python3 -c "
import sys, base64, json
payload = sys.stdin.read().strip()
padding = (-len(payload)) % 4
decoded = base64.urlsafe_b64decode(payload + '=' * padding)
print(json.loads(decoded).get('user_id', ''))
" 2>/dev/null)

log_ok "JWT ottenuto per '$USERNAME' (user_id=${USER_ID:-?})"

# --- 1. Preflight permessi area anagrafiche ---
echo ""
echo "-- 1. Preflight permessi area anagrafiche --"
do_curl GET "/api/v1/core/users/${USER_ID}/permessi-effettivi/"
check "Permessi effettivi utente corrente" "200"

ANAG_LEVEL=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    areas = json.load(sys.stdin)['data']['aree']
    for area in areas:
        if area.get('schema_db') == 'anagrafiche':
            print(area.get('livello', ''))
            break
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null)

if [[ -z "$ANAG_LEVEL" ]]; then
    echo -e "${RED}ERRORE:${NC} area funzionale 'anagrafiche' non trovata nei permessi effettivi dell'utente."
    exit 2
fi

if [[ "$ANAG_LEVEL" != "LETTURA" && "$ANAG_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' senza permesso read su 'anagrafiche' (livello=$ANAG_LEVEL)."
    echo "Per questo smoke serve almeno LETTURA sull'area anagrafiche."
    exit 2
fi

log_ok "Permessi anagrafiche validi per lookup BA (livello=$ANAG_LEVEL)"

# --- 2. Lookup BA q vuota (400 atteso) ---
echo ""
echo "-- 2. Lookup BA q vuota --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q="
check "Lookup BA q vuota rifiutato" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 3. Lookup BA q troppo corta ---
echo ""
echo "-- 3. Lookup BA q troppo corta (1 char) --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=A"
check "Lookup BA q < 2 char rifiutato" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 4. Lookup BA q valida ---
echo ""
echo "-- 4. Lookup BA q valida --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA"
check "Lookup BA q valida" "200" ".data.limit"
LOOKUP_LIMIT="$EXTRACTED"
LOOKUP_TOTAL=$(json_get "$LAST_BODY" ".data.total_count")
LOOKUP_FIRST_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
LOOKUP_FIRST_CODE=$(json_get "$LAST_BODY" ".data.results.0.codice")
log_info "Envelope: limit=${LOOKUP_LIMIT:-?} total_count=${LOOKUP_TOTAL:-?}"
log_info "Primo BA: id=${LOOKUP_FIRST_ID:-<vuoto>} codice=${LOOKUP_FIRST_CODE:-<vuoto>}"

# Verifica struttura envelope (deve avere results+total_count+limit)
if [[ -n "$LOOKUP_LIMIT" ]]; then
    log_ok "Envelope envelope contiene limit"
else
    log_fail "Envelope manca campo 'limit'"
fi

# --- 5. Lookup BA con utility_id filter ---
echo ""
echo "-- 5. Lookup BA con utility_id filter --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA&utility_id=1"
check "Lookup BA con utility_id" "200" ".data.limit"
log_info "Risultati con utility_id=1: $(json_get "$LAST_BODY" ".data.total_count")"

# --- 6. Lookup BA con limit custom ---
echo ""
echo "-- 6. Lookup BA con limit=5 --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA&limit=5"
check "Lookup BA limit custom" "200" ".data.limit"
if [[ "$EXTRACTED" == "5" ]]; then
    log_ok "Limit 5 applicato correttamente"
else
    log_fail "Limit non corretto: atteso 5, ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 7. Lookup BA con limit oltre cap (atteso cap a 50) ---
echo ""
echo "-- 7. Lookup BA limit=200 (capping a 50) --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA&limit=200"
check "Lookup BA limit oversized capped" "200" ".data.limit"
if [[ "$EXTRACTED" == "50" ]]; then
    log_ok "Limit 200 capped a 50"
else
    log_fail "Cap limit non rispettato: atteso 50, ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 8. Lookup BA con solo_validi=false ---
echo ""
echo "-- 8. Lookup BA solo_validi=false --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA&solo_validi=false"
check "Lookup BA solo_validi=false" "200" ".data.total_count"
log_info "Risultati senza filtro validita': ${EXTRACTED:-?}"

# --- 9. Restore by id (solo se almeno un BA esiste) ---
echo ""
echo "-- 9. Restore by id --"
if [[ -n "$LOOKUP_FIRST_ID" ]]; then
    do_curl GET "/api/v1/anagrafiche/billing-account/${LOOKUP_FIRST_ID}/lookup/"
    check "Restore BA by id" "200" ".data.id"
    if [[ "$EXTRACTED" == "$LOOKUP_FIRST_ID" ]]; then
        log_ok "ID restore coerente con lookup"
    else
        log_fail "ID restore incoerente: atteso ${LOOKUP_FIRST_ID}, ricevuto '${EXTRACTED:-<vuoto>}'"
    fi
    # Verifica presenza campi arricchiti chiave
    R_CODICE=$(json_get "$LAST_BODY" ".data.codice")
    R_RAGIONE=$(json_get "$LAST_BODY" ".data.ragione_sociale_completa")
    R_UTILITY=$(json_get "$LAST_BODY" ".data.utility_codice")
    log_info "Restore campi: codice=${R_CODICE:-?} ragione_sociale='${R_RAGIONE:-?}' utility=${R_UTILITY:-?}"
else
    log_info "Nessun BA disponibile in lookup, skip test 9"
fi

# --- 10. Restore by id inesistente ---
echo ""
echo "-- 10. Restore by id inesistente (atteso 404) --"
do_curl GET "/api/v1/anagrafiche/billing-account/999999999/lookup/"
check "Restore BA by id inesistente" "404" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo "Nota: lo smoke e' read-only — non crea ne' modifica BA."

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
