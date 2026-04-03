#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Catalogo CRUD articolo (Fase 2)
# Uso: ./scripts/tests/smoke-test-catalogo-crud.sh [password]
# ------------------------------------------------------------
# Indice test (0..8):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi area catalogo (richiede TUTTO)
#  2) Crea articolo minimale
#  3) Dettaglio articolo creato
#  4) PATCH campi editabili
#  5) PATCH codice immutabile (400 atteso)
#  6) POST duplicato stesso codice (400 atteso)
#  7) Disattiva articolo
#  8) Disattiva articolo gia' inattivo (idempotente)
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
echo " Smoke test API Catalogo CRUD articolo"
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
    "${BASE_URL}/api/v1/auth/token/" > "$TMPFILE" 2>/dev/null

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

# --- 1. Preflight permessi area catalogo ---
echo ""
echo "-- 1. Preflight permessi area catalogo --"
do_curl GET "/api/v1/core/users/${USER_ID}/permessi-effettivi/"
check "Permessi effettivi utente corrente" "200"

CATALOGO_LEVEL=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    areas = json.load(sys.stdin)['data']['aree']
    for area in areas:
        if area.get('schema_db') == 'catalogo':
            print(area.get('livello', ''))
            break
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null)

if [[ -z "$CATALOGO_LEVEL" ]]; then
    echo -e "${RED}ERRORE:${NC} area funzionale 'catalogo' non trovata nei permessi effettivi dell'utente."
    exit 2
fi

if [[ "$CATALOGO_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' senza permesso write su 'catalogo' (livello=$CATALOGO_LEVEL)."
    echo "Per questo smoke serve livello TUTTO sull'area catalogo."
    exit 2
fi

log_ok "Permessi catalogo validi per CRUD (livello=$CATALOGO_LEVEL)"

TEST_SUFFIX=$(date +%Y%m%d%H%M%S)
ART_CODE="SMK-CAT-${TEST_SUFFIX}"
ART_DESC="Smoke articolo CRUD ${TEST_SUFFIX}"
ART_DESC_UPDATED="Smoke articolo CRUD aggiornato ${TEST_SUFFIX}"

# --- 2. Create articolo ---
echo ""
echo "-- 2. Create articolo --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${ART_CODE}\",\"descrizione\":\"${ART_DESC}\"}"
check "Create articolo minimale" "200" ".data.id"
ART_ID="$EXTRACTED"
log_info "Articolo creato: id=${ART_ID} codice=${ART_CODE}"

# --- 3. Dettaglio articolo creato ---
echo ""
echo "-- 3. Dettaglio articolo creato --"
do_curl GET "/api/v1/catalogo/articoli/${ART_ID}/"
check "Dettaglio articolo creato" "200" ".data.codice"
if [[ "$EXTRACTED" == "$ART_CODE" ]]; then
    log_ok "Codice dettaglio coerente (${EXTRACTED})"
else
    log_fail "Codice dettaglio incoerente: atteso ${ART_CODE}, ricevuto ${EXTRACTED:-<vuoto>}"
fi

# --- 4. PATCH campi editabili ---
echo ""
echo "-- 4. PATCH campi editabili --"
do_curl PATCH "/api/v1/catalogo/articoli/${ART_ID}/" "{\"descrizione\":\"${ART_DESC_UPDATED}\",\"descrizione_breve\":\"Breve ${TEST_SUFFIX}\",\"voce_utility\":true}"
check "PATCH articolo campi editabili" "200" ".data.descrizione"
if [[ "$EXTRACTED" == "$ART_DESC_UPDATED" ]]; then
    log_ok "Descrizione aggiornata coerente"
else
    log_fail "Descrizione aggiornata incoerente: atteso '${ART_DESC_UPDATED}', ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 5. PATCH codice immutabile ---
echo ""
echo "-- 5. PATCH codice immutabile --"
do_curl PATCH "/api/v1/catalogo/articoli/${ART_ID}/" "{\"codice\":\"${ART_CODE}-NEW\"}"
check "PATCH codice immutabile" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 6. Create duplicato stesso codice ---
echo ""
echo "-- 6. Create duplicato stesso codice --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${ART_CODE}\",\"descrizione\":\"Duplicato smoke\"}"
check "Create duplicato stesso codice" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 7. Disattiva articolo ---
echo ""
echo "-- 7. Disattiva articolo --"
do_curl POST "/api/v1/catalogo/articoli/${ART_ID}/disattiva/" "{}"
check "Disattiva articolo" "200" ".data.attivo"
if [[ "$EXTRACTED" == "False" || "$EXTRACTED" == "false" ]]; then
    log_ok "Articolo disattivato (attivo=false)"
else
    log_fail "Disattivazione incoerente: atteso attivo=false, ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 8. Disattiva articolo gia' inattivo ---
echo ""
echo "-- 8. Disattiva articolo gia' inattivo --"
do_curl POST "/api/v1/catalogo/articoli/${ART_ID}/disattiva/" "{}"
check "Disattiva articolo gia' inattivo" "200" ".data.attivo"
if [[ "$EXTRACTED" == "False" || "$EXTRACTED" == "false" ]]; then
    log_ok "Seconda disattivazione idempotente"
else
    log_fail "Seconda disattivazione non idempotente: atteso attivo=false, ricevuto '${EXTRACTED:-<vuoto>}'"
fi

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo "Nota: lo smoke crea un articolo di test e lo lascia disattivato."

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
