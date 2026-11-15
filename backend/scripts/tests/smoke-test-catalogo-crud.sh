#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Catalogo CRUD articolo (Fase 2)
# Uso: ./scripts/tests/smoke-test-catalogo-crud.sh [password]
# ------------------------------------------------------------
# Indice test (0..12):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi area catalogo (richiede TUTTO)
#  1b) Seed UoM dal catalogo (per create articolo con uom_id obbligatorio)
#  2) Crea articolo SENZA uom_id (400 atteso — DDL NOT NULL)
#  2b) Crea articolo con uom_id valido
#  2c) Verifica seed automatico UoM operativa base (trigger DB)
#  3) Dettaglio articolo creato
#  4) PATCH campi editabili (no codice no uom_id)
#  5) PATCH codice immutabile (400 atteso)
#  5b) PATCH uom_id immutabile (400 atteso — lock_columns DDL)
#  6) POST duplicato stesso codice (400 atteso)
#  7) Disattiva articolo: 7a con l'UoM operativa attiva (409), 7b l'UoM, 7c l'articolo
#  8) Disattiva articolo gia' inattivo (idempotente)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_errori.sh"   # smoke_check_codice

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

# --- 1b. Seed UoM dal catalogo ---
echo ""
echo "-- 1b. Seed UoM dal catalogo --"
do_curl GET "/api/v1/core/lookup/codici/?rel=catalogo.unita_misura&limit=1"
check "Lookup UoM seed" "200" ".data.results.0.id"
SEED_UOM_ID="$EXTRACTED"
if [[ -z "$SEED_UOM_ID" ]]; then
    echo -e "${RED}ERRORE:${NC} nessuna UoM disponibile nel catalogo per il seed."
    exit 3
fi
log_info "UoM seed: id=${SEED_UOM_ID}"

# --- 2. Create articolo SENZA uom_id (atteso 400, NOT NULL DDL) ---
echo ""
echo "-- 2. Create articolo SENZA uom_id (atteso 400) --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${ART_CODE}-NOUOM\",\"descrizione\":\"Senza uom\"}"
check "Create articolo senza uom_id rifiutato" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 2b. Create articolo con uom_id valido ---
echo ""
echo "-- 2b. Create articolo con uom_id --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${ART_CODE}\",\"descrizione\":\"${ART_DESC}\",\"uom_id\":${SEED_UOM_ID}}"
check "Create articolo con uom_id valido" "200" ".data.id"
ART_ID="$EXTRACTED"
log_info "Articolo creato: id=${ART_ID} codice=${ART_CODE} uom_id=${SEED_UOM_ID}"

# --- 2c. Verifica seed automatico UoM operativa base ---
echo ""
echo "-- 2c. Verifica seed automatico UoM operativa base --"
do_curl GET "/api/v1/catalogo/articoli/${ART_ID}/uom/"
check "Lista UoM operative articolo (post-seed trigger)" "200" ".data.results.0.uom_id"
SEED_UOM_OPERATIVA=$(json_get "$LAST_BODY" ".data.results.0.uom_id")
SEED_UOM_OP_ROW_ID=$(json_get "$LAST_BODY" ".data.results.0.id")   # serve al passo 7
SEED_IS_BASE=$(json_get "$LAST_BODY" ".data.results.0.is_base")
SEED_COUNT=$(json_get "$LAST_BODY" ".data.count")
if [[ "$SEED_UOM_OPERATIVA" == "$SEED_UOM_ID" ]]; then
    log_ok "UoM operativa base ha lo stesso uom_id dell'articolo (${SEED_UOM_OPERATIVA})"
else
    log_fail "UoM operativa base incoerente: atteso ${SEED_UOM_ID}, ricevuto '${SEED_UOM_OPERATIVA:-<vuoto>}'"
fi
if [[ "$SEED_IS_BASE" == "True" || "$SEED_IS_BASE" == "true" ]]; then
    log_ok "is_base=true sulla riga seedata dal trigger DB"
else
    log_fail "is_base non true: ricevuto '${SEED_IS_BASE:-<vuoto>}'"
fi
log_info "Totale UoM operative dopo create: ${SEED_COUNT:-?}"

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
do_curl PATCH "/api/v1/catalogo/articoli/${ART_ID}/" "{\"descrizione\":\"${ART_DESC_UPDATED}\",\"descrizione_breve\":\"Breve ${TEST_SUFFIX}\"}"
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

# --- 5b. PATCH uom_id immutabile (rifiutato dal service prima del DDL trigger) ---
echo ""
echo "-- 5b. PATCH uom_id immutabile --"
do_curl PATCH "/api/v1/catalogo/articoli/${ART_ID}/" "{\"uom_id\":${SEED_UOM_ID}}"
check "PATCH uom_id immutabile" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 6. Create duplicato stesso codice ---
echo ""
echo "-- 6. Create duplicato stesso codice --"
do_curl POST "/api/v1/catalogo/articoli/" "{\"codice\":\"${ART_CODE}\",\"descrizione\":\"Duplicato smoke\",\"uom_id\":${SEED_UOM_ID}}"
check "Create duplicato stesso codice" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 7. Disattiva articolo: l'UoM base resta accesa ---
# ⭐ Dal 2026-11-11 (brief-db-revisione-catalogo, Q31 e Q34) la mappatura
# dell'unita' operativa e' STORIA, non un figlio vivo: e' in
# dbops.automazione_attivo_eccezioni, quindi non blocca lo spegnimento
# dell'articolo. E la riga base non si spegne mai
# (trgfn_articoli_uom_operativa_guard_base, E_UOM_RIGA_BASE_IMMUTABILE).
# Fino al 2026-11-11 lo smoke seguiva «figli prima del padre» (spegni la base,
# poi l'articolo): oggi il primo passo e' giusto che sia rifiutato (7a), e
# l'articolo si spegne con la base accesa (7b).
echo ""
echo "-- 7a. Spegni l'UoM operativa base (atteso 409) --"
do_curl PATCH "/api/v1/catalogo/articoli/${ART_ID}/uom/${SEED_UOM_OP_ROW_ID}/" "{\"attivo\":false}"
smoke_check_codice "Spegnimento della riga base rifiutato" 409 E_UOM_RIGA_BASE_IMMUTABILE

echo ""
echo "-- 7b. Disattiva articolo con la base accesa --"
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
