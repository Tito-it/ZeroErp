#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Catalogo (articoli + lookup UoM)
# Uso: ./scripts/tests/smoke-test-catalogo.sh [password]
# ------------------------------------------------------------
# Indice test (0..8):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi area catalogo
#  2) Lista articoli (paginata)
#  3) Lista articoli con search e ordinamento
#  4) Dettaglio primo articolo (se presente)
#  5) Dettaglio articolo inesistente (404 atteso)
#  6) Lookup articoli con search (se presente un articolo)
#  7) Lookup UoM attive
#  8) Lista articoli con parametro invalido (400 atteso)
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

echo ""
echo "========================================="
echo " Smoke test API Catalogo"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login

USER_ID=$(smoke_jwt_claim "$TOKEN" user_id)

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
    echo "Verificare seed config.aree_funzionali o il profilo permessi."
    exit 2
fi

if [[ "$CATALOGO_LEVEL" != "LETTURA" && "$CATALOGO_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' senza accesso read all'area 'catalogo' (livello=$CATALOGO_LEVEL)."
    echo "Concedere almeno LETTURA sull'area catalogo oppure eseguire lo smoke test con un utente abilitato."
    exit 2
fi

log_ok "Permessi catalogo validi (livello=$CATALOGO_LEVEL)"

# --- 2. Lista articoli ---
echo ""
echo "-- 2. Lista articoli --"
do_curl GET "/api/v1/catalogo/articoli/?limit=5"
check "Lista articoli" "200" ".data.count"
ARTICOLI_COUNT="$EXTRACTED"
log_info "Totale articoli: $ARTICOLI_COUNT"

FIRST_ART_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
FIRST_ART_CODICE=$(json_get "$LAST_BODY" ".data.results.0.codice")
FIRST_ART_SEARCH=$(echo "$FIRST_ART_CODICE" | cut -c1-3)

# --- 3. Lista articoli con search e ordinamento ---
echo ""
echo "-- 3. Lista articoli con search/ordinamento --"
if [[ -n "$FIRST_ART_SEARCH" ]]; then
    do_curl GET "/api/v1/catalogo/articoli/?search=${FIRST_ART_SEARCH}&order_by=codice&order_dir=asc&limit=5"
    check "Lista articoli con search='${FIRST_ART_SEARCH}'" "200"
else
    log_info "Skipped (nessun articolo disponibile per costruire la search)"
fi

# --- 4. Dettaglio primo articolo ---
echo ""
echo "-- 4. Dettaglio primo articolo --"
if [[ -n "$FIRST_ART_ID" ]]; then
    do_curl GET "/api/v1/catalogo/articoli/${FIRST_ART_ID}/"
    check "Dettaglio articolo id=${FIRST_ART_ID}" "200" ".data.codice"
    log_info "Codice articolo: $EXTRACTED"
else
    log_info "Skipped (nessun articolo disponibile)"
fi

# --- 5. Dettaglio articolo inesistente ---
echo ""
echo "-- 5. Dettaglio articolo inesistente --"
do_curl GET "/api/v1/catalogo/articoli/00000000-0000-0000-0000-000000000000/"
check "Dettaglio articolo inesistente" "404"

# --- 6. Lookup articoli ---
echo ""
echo "-- 6. Lookup articoli --"
if [[ -n "$FIRST_ART_SEARCH" ]]; then
    do_curl GET "/api/v1/catalogo/articoli/lookup/?search=${FIRST_ART_SEARCH}&limit=10"
    check "Lookup articoli search='${FIRST_ART_SEARCH}'" "200" ".data.count"
    log_info "Articoli trovati: $EXTRACTED"
else
    log_info "Skipped (nessun articolo disponibile per lookup search)"
fi

# --- 7. Lookup UoM attive ---
echo ""
echo "-- 7. Lookup UoM --"
# Il lookup dedicato `catalogo/unita-misura/lookup/` e' stato ritirato: le UoM
# passano dal lookup generico whitelist (`rel=catalogo.unita_misura`), come il
# frontend e smoke-test-catalogo-crud.
do_curl GET "/api/v1/core/lookup/codici/?rel=catalogo.unita_misura&limit=20"
check "Lookup UoM attive" "200" ".data.count"
log_info "UoM trovate: $EXTRACTED"

# --- 8. Parametro invalido ---
echo ""
echo "-- 8. Parametro invalido --"
do_curl GET "/api/v1/catalogo/articoli/?tipo_voce_id=abc"
check "Lista articoli con tipo_voce_id invalido" "400"

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
