#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Catalogo Fase 3 (UoM, componenti, note)
# Uso: NOTE_STYLE_ID=1 ./scripts/tests/smoke-test-catalogo-phase3.sh [password]
# ------------------------------------------------------------
# Indice test (0..17):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi area catalogo (richiede TUTTO)
#  2) Lookup UoM attive e scelta UoM seed
#  3) Crea articolo padre composito
#  4) Crea articolo figlio componente
#  5) Dettaglio articolo padre (array Fase 3)
#  6) Create UoM operativa
#  7) Lista UoM operative
#  8) PATCH UoM operativa
#  9) Create componente BoM
# 10) Lista componenti BoM
# 11) PATCH componente BoM
# 12) Create componente self-reference (400 atteso)
# 13) Lista note articolo
# 14) Create nota articolo (opzionale, richiede NOTE_STYLE_ID)
# 15) PATCH nota articolo (opzionale)
# 16) DELETE nota / componente / UoM
# 17) Disattiva articoli di test
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Gunicorn diretto in HTTP: ci si dichiara HTTPS come Nginx (redirect di Django).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"
NOTE_STYLE_ID="${NOTE_STYLE_ID:-}"

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
    elif [[ "$method" == "DELETE" ]]; then
        curl -s -w '\n%{http_code}' \
            -X DELETE \
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
        echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
        return 1
    fi
    if [[ -n "$json_expr" ]]; then
        EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    fi
    return 0
}

echo ""
echo "========================================="
echo " Smoke test API Catalogo Fase 3"
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

log_ok "Permessi catalogo validi per Fase 3 (livello=$CATALOGO_LEVEL)"

TEST_SUFFIX=$(date +%Y%m%d%H%M%S)
PARENT_CODE="SMK-CAT3-P-${TEST_SUFFIX}"
CHILD_CODE="SMK-CAT3-C-${TEST_SUFFIX}"
PARENT_DESC="Smoke catalogo fase 3 padre ${TEST_SUFFIX}"
CHILD_DESC="Smoke catalogo fase 3 figlio ${TEST_SUFFIX}"

# --- 2. Lookup UoM attive ---
echo ""
echo "-- 2. Lookup UoM seed --"
do_curl GET "/api/v1/catalogo/unita-misura/lookup/?limit=5"
check "Lookup UoM attive" "200"
UOM_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
UOM_CODE=$(json_get "$LAST_BODY" ".data.results.0.codice")
if [[ -z "$UOM_ID" ]]; then
    echo -e "${RED}ERRORE:${NC} nessuna UoM attiva trovata; impossibile eseguire la Fase 3."
    exit 3
fi
log_info "UoM seed: id=${UOM_ID} codice=${UOM_CODE:-?}"

# --- 3. Crea articolo padre composito ---
echo ""
echo "-- 3. Create articolo padre composito --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${PARENT_CODE}\",\"descrizione\":\"${PARENT_DESC}\",\"uom_id\":${UOM_ID},\"is_composito\":true}"
check "Create articolo padre composito" "200" ".data.id"
PARENT_ID="$EXTRACTED"
log_info "Articolo padre creato: id=${PARENT_ID}"

# --- 4. Crea articolo figlio componente ---
echo ""
echo "-- 4. Create articolo figlio componente --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${CHILD_CODE}\",\"descrizione\":\"${CHILD_DESC}\",\"uom_id\":${UOM_ID},\"is_solo_componente\":true}"
check "Create articolo figlio componente" "200" ".data.id"
CHILD_ID="$EXTRACTED"
log_info "Articolo figlio creato: id=${CHILD_ID}"

# --- 5. Dettaglio articolo padre ---
echo ""
echo "-- 5. Dettaglio articolo padre --"
do_curl GET "/api/v1/catalogo/articoli/${PARENT_ID}/"
check "Dettaglio articolo padre" "200" ".data.is_composito"
UOM_INITIAL_COUNT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    print(len(d.get('uom_operative', [])))
except Exception:
    print('')
" 2>/dev/null)
COMP_INITIAL_COUNT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    print(len(d.get('componenti', [])))
except Exception:
    print('')
" 2>/dev/null)
log_info "Dettaglio arrays: uom_operative=${UOM_INITIAL_COUNT:-?} componenti=${COMP_INITIAL_COUNT:-?}"

# --- 6. Create UoM operativa ---
echo ""
echo "-- 6. Create UoM operativa --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/uom/" "{\"uom_id\":${UOM_ID},\"is_base\":true,\"factor_to_base\":\"1\"}"
check "Create UoM operativa base" "200" ".data.id"
UOM_OP_ID="$EXTRACTED"
log_info "UoM operativa creata: id=${UOM_OP_ID}"

# --- 7. Lista UoM operative ---
echo ""
echo "-- 7. Lista UoM operative --"
do_curl GET "/api/v1/catalogo/articoli/${PARENT_ID}/uom/"
check "Lista UoM operative articolo" "200" ".data.count"
log_info "UoM operative trovate: ${EXTRACTED:-?}"

# --- 8. PATCH UoM operativa ---
echo ""
echo "-- 8. PATCH UoM operativa --"
do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/uom/${UOM_OP_ID}/" "{\"is_sell_uom\":true,\"gtin\":\"SMK-${TEST_SUFFIX}\"}"
check "PATCH UoM operativa" "200" ".data.is_sell_uom"
log_info "Flag is_sell_uom: ${EXTRACTED:-n/d}"

# --- 9. Create componente BoM ---
echo ""
echo "-- 9. Create componente BoM --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/" "{\"componente_id\":\"${CHILD_ID}\",\"coeff_qta\":\"2\",\"valido_dal\":\"2026-01-01\",\"obbligatorio\":true}"
check "Create componente BoM" "200" ".data.id"
COMP_ROW_ID="$EXTRACTED"
log_info "Componente BoM creato: id=${COMP_ROW_ID}"

# --- 10. Lista componenti BoM ---
echo ""
echo "-- 10. Lista componenti BoM --"
do_curl GET "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/"
check "Lista componenti BoM" "200" ".data.count"
log_info "Componenti trovati: ${EXTRACTED:-?}"

# --- 11. PATCH componente BoM ---
echo ""
echo "-- 11. PATCH componente BoM --"
do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/${COMP_ROW_ID}/" "{\"coeff_qta\":\"3\",\"partecipa_qta\":true}"
check "PATCH componente BoM" "200" ".data.coeff_qta"
log_info "coeff_qta aggiornato: ${EXTRACTED:-n/d}"

# --- 12. Create componente self-reference ---
echo ""
echo "-- 12. Create componente self-reference --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/" "{\"componente_id\":\"${PARENT_ID}\",\"coeff_qta\":\"1\",\"valido_dal\":\"2026-01-01\"}"
check "Create componente self-reference" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 13. Lista note articolo ---
echo ""
echo "-- 13. Lista note articolo --"
do_curl GET "/api/v1/catalogo/articoli/${PARENT_ID}/note/"
check "Lista note articolo" "200" ".data.count"
log_info "Note iniziali: ${EXTRACTED:-?}"

NOTE_ID=""
if [[ -n "$NOTE_STYLE_ID" ]]; then
    # --- 14. Create nota articolo ---
    echo ""
    echo "-- 14. Create nota articolo --"
    do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/note/" "{\"id_stile\":${NOTE_STYLE_ID},\"testo\":\"Smoke nota ${TEST_SUFFIX}\",\"anchor_tipo\":\"DOCUMENTO\",\"posizione\":\"HEADER\",\"seq\":10}"
    check "Create nota articolo" "200" ".data.nota_id"
    NOTE_ID="$EXTRACTED"
    log_info "Nota creata: id=${NOTE_ID}"

    # --- 15. PATCH nota articolo ---
    echo ""
    echo "-- 15. PATCH nota articolo --"
    do_curl PATCH "/api/v1/catalogo/note/${NOTE_ID}/" "{\"testo\":\"Smoke nota aggiornata ${TEST_SUFFIX}\",\"visibile\":true}"
    check "PATCH nota articolo" "200" ".data.nota_id"
    log_info "Nota aggiornata: id=${EXTRACTED:-n/d}"
else
    echo ""
    echo "-- 14-15. Note write skipped --"
    log_info "NOTE_STYLE_ID non impostato: create/update nota saltati."
    log_info "Per coprire anche le note write: NOTE_STYLE_ID=<id_stile> ./scripts/tests/smoke-test-catalogo-phase3.sh"
fi

# --- 16. DELETE figli ---
echo ""
echo "-- 16. DELETE figli Fase 3 --"
if [[ -n "$NOTE_ID" ]]; then
    do_curl DELETE "/api/v1/catalogo/note/${NOTE_ID}/"
    check "DELETE nota articolo" "200" ".data.deleted"
else
    log_info "DELETE nota skipped"
fi
do_curl DELETE "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/${COMP_ROW_ID}/"
check "DELETE componente BoM" "200" ".data.deleted"
do_curl DELETE "/api/v1/catalogo/articoli/${PARENT_ID}/uom/${UOM_OP_ID}/"
check "DELETE UoM operativa" "200" ".data.deleted"

# --- 17. Disattiva articoli di test ---
echo ""
echo "-- 17. Disattiva articoli di test --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/disattiva/" "{}"
check "Disattiva articolo padre" "200" ".data.attivo"
do_curl POST "/api/v1/catalogo/articoli/${CHILD_ID}/disattiva/" "{}"
check "Disattiva articolo figlio" "200" ".data.attivo"

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo "Nota: lo smoke crea due articoli di test e li lascia disattivati."

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
