#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API sospensioni e calcoli tempo
# Prerequisito: smoke-test-pratiche.sh deve aver girato almeno una volta
#   (serve una pratica APERTA con un flusso IN_CORSO).
# Uso: ./scripts/smoke-test-sospensioni.sh [password]
# ------------------------------------------------------------
# Indice test (0..14):
#  0) Autenticazione JWT
#  1) Creazione pratica di test
#  2) Stato pratica BOZZA → APERTA
#  3) Creazione flusso
#  4) Avvio flusso DA_ESEGUIRE → IN_CORSO
#  5) Sospendi pratica
#  6) Lista sospensioni pratica (verifica 1 sospensione attiva)
#  7) Riattiva pratica
#  8) Sospendi flusso
#  9) Riattiva flusso
# 10) Calcoli tempo pratica (GET — anche se vuoto)
# 11) Sospendi pratica senza motivo → 400
# 12) Sospendi flusso senza motivo → 400
# 13) Sospendi pratica gia' sospesa → 400
# 14) Sospendi senza JWT → 401
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

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
        if k.isdigit():
            d = d[int(k)]
        else:
            d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

# Wrapper curl: salva status e body separatamente
do_curl() {
    local method="$1" url="$2" data="${3:-}"

    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    elif [[ "$method" == "POST_NOAUTH" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Content-Type: application/json" \
            -d "$data" \
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
echo " Smoke test API Sospensioni / Calcoli Tempo"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "JWT ottenuto per '$USERNAME'"

# --- 1. Crea pratica di test ---
echo ""
echo "-- 1. Creazione pratica --"

do_curl POST "/api/v1/pratiche/" "{
    \"emittente_fiscale_id\": $EMITTENTE_FISCALE_ID,
    \"tipo_prestazione_id\": $TIPO_PRESTAZIONE_ID,
    \"priorita_id\": $PRIORITA_ID,
    \"descrizione\": \"Smoke sospensioni $(date +%Y%m%d-%H%M%S)\"
}"
check "POST crea pratica" 200 ".data.pratica_id" || true
PRATICA_ID="$EXTRACTED"

if [[ -z "$PRATICA_ID" || "$PRATICA_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere pratica_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "pratica_id = $PRATICA_ID"

# --- 2. Stato pratica BOZZA → APERTA ---
echo ""
echo "-- 2. Stato BOZZA → APERTA --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/stato/" '{"nuovo_stato": "APERTA"}'
check "POST stato BOZZA→APERTA" 200

# --- 3. Crea flusso ---
echo ""
echo "-- 3. Creazione flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" '{
    "sequenza": 1,
    "meta": {"smoke_sospensioni": true}
}'
check "POST crea flusso" 200 ".data.flusso_id" || true
FLUSSO_ID="$EXTRACTED"

if [[ -z "$FLUSSO_ID" || "$FLUSSO_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere flusso_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "flusso_id = $FLUSSO_ID"

# --- 4. Avvio flusso DA_ESEGUIRE → IN_CORSO ---
echo ""
echo "-- 4. Avvio flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "IN_CORSO"}'
check "POST stato DA_ESEGUIRE→IN_CORSO" 200

# --- 5. Sospendi pratica ---
echo ""
echo "-- 5. Sospendi pratica --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/sospendi/" '{
    "motivo": "Smoke test — attesa documenti",
    "data_riattivazione_prevista": "2026-12-31"
}'
check "POST sospendi pratica" 200 ".data.sospensione_id" || true
SOSPENSIONE_ID="$EXTRACTED"
log_info "sospensione_id = $SOSPENSIONE_ID"

# --- 6. Lista sospensioni ---
echo ""
echo "-- 6. Lista sospensioni --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/sospensioni/"
check "GET sospensioni pratica" 200

SOSP_COUNT=$(json_get "$LAST_BODY" ".data.results" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(len(d))
except:
    print(0)
" 2>/dev/null || echo "0")

# Verifica alternativa: conta risultati dal body JSON direttamente
SOSP_COUNT_ALT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(len(d.get('data', {}).get('results', [])))
except:
    print(0)
" 2>/dev/null || echo "0")

if [[ "$SOSP_COUNT_ALT" -ge 1 ]]; then
    log_ok "Almeno 1 sospensione trovata (count=$SOSP_COUNT_ALT)"
else
    log_fail "Attesa almeno 1 sospensione, trovate $SOSP_COUNT_ALT"
fi

# --- 7. Riattiva pratica ---
echo ""
echo "-- 7. Riattiva pratica --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/riattiva/" '{}'
check "POST riattiva pratica" 200

# --- 8. Sospendi flusso ---
echo ""
echo "-- 8. Sospendi flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/sospendi/" '{
    "motivo": "Smoke test — attesa tecnico"
}'
check "POST sospendi flusso" 200 ".data.sospensione_id" || true
log_info "sospensione_flusso_id = $EXTRACTED"

# --- 9. Riattiva flusso ---
echo ""
echo "-- 9. Riattiva flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/riattiva/" '{}'
check "POST riattiva flusso" 200

# --- 10. Calcoli tempo ---
echo ""
echo "-- 10. Calcoli tempo --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/calcoli-tempo/"
check "GET calcoli tempo" 200

# --- 11. Errore: sospendi senza motivo → 400 ---
echo ""
echo "-- 11. Errore: sospendi senza motivo --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/sospendi/" '{}'
check "POST sospendi senza motivo → 400" 400

# --- 12. Errore: sospendi flusso senza motivo → 400 ---
echo ""
echo "-- 12. Errore: sospendi flusso senza motivo --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/sospendi/" '{}'
check "POST sospendi flusso senza motivo → 400" 400

# --- 13. Errore: sospendi pratica gia' sospesa → 400 ---
echo ""
echo "-- 13. Errore: doppia sospensione --"

# Prima sospendi
do_curl POST "/api/v1/pratiche/${PRATICA_ID}/sospendi/" '{"motivo": "Prima sospensione"}'
check "POST sospendi pratica (prep)" 200

# Poi risospendi — deve fallire
do_curl POST "/api/v1/pratiche/${PRATICA_ID}/sospendi/" '{"motivo": "Seconda sospensione"}'
check "POST doppia sospensione → 400" 400

# Cleanup: riattiva
do_curl POST "/api/v1/pratiche/${PRATICA_ID}/riattiva/" '{}'
check "POST riattiva (cleanup)" 200

# --- 14. Errore: sospendi senza JWT → 401 ---
echo ""
echo "-- 14. Sospendi senza JWT --"

do_curl POST_NOAUTH "/api/v1/pratiche/${PRATICA_ID}/sospendi/" '{"motivo": "test"}'
check "POST sospendi senza JWT → 401" 401

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
