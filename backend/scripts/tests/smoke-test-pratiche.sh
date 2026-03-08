#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API pratiche
# Esegue il ciclo completo: autenticazione → pratica → flusso → lifecycle
# Uso: ./scripts/smoke-test-pratiche.sh [password]
# ------------------------------------------------------------
# Indice test (0..17):
#  0) Autenticazione JWT
#  1) Lista pratiche (con filtro emittente)
#  2) Creazione pratica
#  3) Dettaglio pratica
#  4) Aggiornamento pratica (PATCH descrizione)
#  5) Cambio stato pratica BOZZA → APERTA
#  6) Giornale pratica
#  7) Creazione flusso
#  8) Lista flussi
#  9) Dettaglio flusso
# 10) Avvio flusso DA_ESEGUIRE → IN_CORSO
# 11) Completamento flusso IN_CORSO → COMPLETATO
# 12) Prerequisiti flusso
# 13) Canali flusso
# 14) Regole generazione
# 15) Pratiche generate
# 16) Giornale finale (conteggio eventi)
# 17) Test errori attesi — pratica/flusso inesistente (404), completa senza esito (400)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

# --- Riferimenti DB (valori di dev) ---
EMITTENTE_FISCALE_ID="${EMITTENTE_ID:-32}"
TIPO_PRESTAZIONE_ID="${TIPO_PRESTAZIONE_ID:-26}"
PRIORITA_ID="${PRIORITA_ID:-1}"

# --- Colori output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
PRATICA_ID=""
FLUSSO_ID=""
LAST_STATUS=""
LAST_BODY=""
EXTRACTED=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

# Estrae un valore JSON con python3 (senza jq)
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

# Wrapper curl: salva status e body separatamente
do_curl() {
    local method="$1" url="$2" data="${3:-}"
    local auth_header=""
    if [[ -n "${TOKEN:-}" ]]; then
        auth_header="-H Authorization: Bearer $TOKEN"
    fi

    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    elif [[ "$method" == "PATCH" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -X PATCH -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    fi

    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# Verifica risposta HTTP + opzionalmente estrae un campo JSON
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
echo " Smoke test API Pratiche"
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
log_ok "JWT ottenuto per '$USERNAME'"

# --- 1. Lista pratiche ---
echo ""
echo "-- 1. Lista pratiche --"

do_curl GET "/api/v1/pratiche/?emittente_fiscale_id=$EMITTENTE_FISCALE_ID"
check "GET lista pratiche" 200

# --- 2. Crea pratica ---
echo ""
echo "-- 2. Creazione pratica --"

do_curl POST "/api/v1/pratiche/" "{
    \"emittente_fiscale_id\": $EMITTENTE_FISCALE_ID,
    \"tipo_prestazione_id\": $TIPO_PRESTAZIONE_ID,
    \"priorita_id\": $PRIORITA_ID,
    \"descrizione\": \"Smoke test $(date +%Y%m%d-%H%M%S)\"
}"
check "POST crea pratica" 200 ".data.pratica_id" || true
PRATICA_ID="$EXTRACTED"

if [[ -z "$PRATICA_ID" || "$PRATICA_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere pratica_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "pratica_id = $PRATICA_ID"

# --- 3. Dettaglio pratica ---
echo ""
echo "-- 3. Dettaglio pratica --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/"
check "GET dettaglio pratica" 200

# --- 4. Aggiorna pratica ---
echo ""
echo "-- 4. Aggiornamento pratica --"

do_curl PATCH "/api/v1/pratiche/${PRATICA_ID}/" '{"descrizione": "Smoke test aggiornato"}'
check "PATCH aggiorna pratica" 200

# --- 5. Cambio stato pratica BOZZA → APERTA ---
echo ""
echo "-- 5. Cambio stato pratica --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/stato/" '{"nuovo_stato": "APERTA"}'
check "POST stato BOZZA→APERTA" 200

# --- 6. Giornale pratica ---
echo ""
echo "-- 6. Giornale pratica --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/giornale/"
check "GET giornale pratica" 200 ".data.count"
log_info "eventi giornale: $EXTRACTED"

# --- 7. Crea flusso ---
echo ""
echo "-- 7. Creazione flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" '{
    "sequenza": 1,
    "meta": {"smoke": true}
}'
check "POST crea flusso" 200 ".data.flusso_id" || true
FLUSSO_ID="$EXTRACTED"

if [[ -z "$FLUSSO_ID" || "$FLUSSO_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere flusso_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "flusso_id = $FLUSSO_ID"

# --- 8. Lista flussi ---
echo ""
echo "-- 8. Lista flussi --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/"
check "GET lista flussi" 200

# --- 9. Dettaglio flusso ---
echo ""
echo "-- 9. Dettaglio flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/"
check "GET dettaglio flusso" 200

# --- 10. Avvia flusso (DA_ESEGUIRE → IN_CORSO) ---
echo ""
echo "-- 10. Avvio flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "IN_CORSO"}'
check "POST stato DA_ESEGUIRE→IN_CORSO" 200

# --- 11. Completa flusso (IN_CORSO → COMPLETATO) ---
echo ""
echo "-- 11. Completamento flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{
    "nuovo_stato": "COMPLETATO",
    "esito": "POSITIVO",
    "note_esito": "Smoke test OK"
}'
check "POST stato IN_CORSO→COMPLETATO" 200

# --- 12. Prerequisiti flusso ---
echo ""
echo "-- 12. Prerequisiti flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/prerequisiti/"
check "GET prerequisiti flusso" 200

# --- 13. Canali flusso ---
echo ""
echo "-- 13. Canali flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/canali/"
check "GET canali flusso" 200

# --- 14. Regole generazione ---
echo ""
echo "-- 14. Regole generazione --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/regole-generazione/"
check "GET regole generazione" 200

# --- 15. Pratiche generate ---
echo ""
echo "-- 15. Pratiche generate --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/pratiche-generate/"
check "GET pratiche generate" 200

# --- 16. Giornale finale ---
echo ""
echo "-- 16. Giornale finale --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/giornale/"
check "GET giornale finale" 200 ".data.count"
log_info "eventi giornale totali: $EXTRACTED"

# --- 17. Test errori attesi ---
echo ""
echo "-- 17. Test errori attesi --"

do_curl GET "/api/v1/pratiche/999999/"
check "GET pratica inesistente → 404" 404

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/999999/"
check "GET flusso inesistente → 404" 404

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "COMPLETATO"}'
check "POST completa senza esito → 400" 400

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
