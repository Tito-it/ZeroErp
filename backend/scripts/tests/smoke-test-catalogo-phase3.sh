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
#  6) UoM operativa base seminata dal DB (non si crea a mano)
#  7) Lista UoM operative
#  8) PATCH UoM operativa
#  9) Create componente BoM
# 10) Lista componenti BoM
# 11) Coefficiente BoM: struttura rifiutata (409), chiudi + inserisci la nuova versione
# 12) Create componente self-reference (400 atteso)
# 13) Lista note articolo
# 14) Create nota articolo (opzionale, richiede NOTE_STYLE_ID)
# 15) PATCH nota articolo (opzionale)
# 16) DELETE nota; righe BoM e UoM base disattivate (non si cancellano)
# 17) Disattiva articoli di test
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
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

log_ok "Permessi catalogo validi per Fase 3 (livello=$CATALOGO_LEVEL)"

TEST_SUFFIX=$(date +%Y%m%d%H%M%S)
PARENT_CODE="SMK-CAT3-P-${TEST_SUFFIX}"
CHILD_CODE="SMK-CAT3-C-${TEST_SUFFIX}"
PARENT_DESC="Smoke catalogo fase 3 padre ${TEST_SUFFIX}"
CHILD_DESC="Smoke catalogo fase 3 figlio ${TEST_SUFFIX}"

# --- 2. Lookup UoM attive ---
echo ""
echo "-- 2. Lookup UoM seed --"
# Il lookup dedicato `catalogo/unita-misura/lookup/` e' stato ritirato: le UoM
# passano dal lookup generico whitelist (`rel=catalogo.unita_misura`), come il
# frontend e smoke-test-catalogo-crud.
do_curl GET "/api/v1/core/lookup/codici/?rel=catalogo.unita_misura&limit=5"
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

# --- 6. UoM operativa base: la semina il DB ---
# ⭐ L'UoM operativa base nasce CON l'articolo (trigger
# catalogo.trgfn_articoli_seed_uom_base, uom_id = quello dell'articolo): crearla a
# mano risponde uq_artuomop_articolo_uom (duplicato). Si legge quella seminata.
echo ""
echo "-- 6. UoM operativa base seminata dal DB --"
do_curl GET "/api/v1/catalogo/articoli/${PARENT_ID}/uom/"
check "Lista UoM operative dopo la create" "200" ".data.results.0.id"
UOM_OP_ID="$EXTRACTED"
UOM_OP_BASE=$(json_get "$LAST_BODY" ".data.results.0.is_base")
if [[ "$UOM_OP_BASE" == "True" || "$UOM_OP_BASE" == "true" ]]; then
    log_ok "UoM operativa base seminata: id=${UOM_OP_ID} (is_base=true)"
else
    log_fail "UoM operativa seminata attesa is_base=true, ricevuto '${UOM_OP_BASE:-<vuoto>}'"
fi

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

# --- 11. Cambiare il coefficiente: chiudi + inserisci ---
# ⭐ La BoM e' immutabile nei campi di struttura (trigger
# catalogo.trgfn_articoli_componenti_block_modifica_struttura, E_BOM_MODIFICA_VIETATA):
# una riga non si corregge, si CHIUDE (valido_al) e se ne inserisce una nuova,
# come le versioni dei listini v5. Fino al 2026-10-12 lo smoke faceva PATCH di
# coeff_qta, che oggi e' giusto venga rifiutata: lo prova (11a), poi la strada vera.
OGGI=$(date +%F); DOMANI=$(date -d tomorrow +%F)
echo ""
echo "-- 11a. PATCH coeff_qta (struttura: atteso 409) --"
do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/${COMP_ROW_ID}/" "{\"coeff_qta\":\"3\"}"
check "PATCH struttura BoM rifiutata" "409" ".error.code"
[[ "$EXTRACTED" == "E_BOM_MODIFICA_VIETATA" ]] && log_ok "Codice corretto: E_BOM_MODIFICA_VIETATA" \
    || log_fail "Codice atteso E_BOM_MODIFICA_VIETATA, ricevuto '${EXTRACTED:-<vuoto>}'"
echo ""
echo "-- 11b. Chiudi la riga (valido_al = oggi) --"
do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/${COMP_ROW_ID}/" "{\"valido_al\":\"${OGGI}\"}"
check "Chiusura riga BoM" "200" ".data.id"
echo ""
echo "-- 11c. Inserisci la nuova versione (coeff_qta 3, da domani) --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/" "{\"componente_id\":\"${CHILD_ID}\",\"coeff_qta\":\"3\",\"valido_dal\":\"${DOMANI}\",\"obbligatorio\":true}"
check "Nuova versione riga BoM" "200" ".data.coeff_qta"
COMP_ROW_ID_V2=$(json_get "$LAST_BODY" ".data.id")
log_info "coeff_qta nuova versione: ${EXTRACTED:-n/d} (id=${COMP_ROW_ID_V2:-?})"

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
# Le righe BoM non si cancellano (DELETE bloccato, tracciabilita' delle
# versioni): si spengono, figli prima del padre (passo 17).
for comp in "$COMP_ROW_ID" "${COMP_ROW_ID_V2:-}"; do
    [[ -z "$comp" ]] && continue
    do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/componenti/${comp}/" "{\"attivo\":false}"
    check "Disattiva riga BoM ${comp}" "200" ".data.id"
done
# L'UoM operativa base non si cancella (e' quella dell'articolo): si disattiva,
# figlio prima del padre (passo 17, guard E_ATTIVO_BLOCK_CHILDREN_ACTIVE).
do_curl PATCH "/api/v1/catalogo/articoli/${PARENT_ID}/uom/${UOM_OP_ID}/" "{\"attivo\":false}"
check "Disattiva UoM operativa base del padre" "200" ".data.attivo"

# --- 17. Disattiva articoli di test ---
echo ""
echo "-- 17. Disattiva articoli di test --"
do_curl POST "/api/v1/catalogo/articoli/${PARENT_ID}/disattiva/" "{}"
check "Disattiva articolo padre" "200" ".data.attivo"
# Anche il figlio ha la sua UoM operativa base seminata: prima quella.
do_curl GET "/api/v1/catalogo/articoli/${CHILD_ID}/uom/"
CHILD_UOM_OP_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -n "$CHILD_UOM_OP_ID" ]]; then
    do_curl PATCH "/api/v1/catalogo/articoli/${CHILD_ID}/uom/${CHILD_UOM_OP_ID}/" "{\"attivo\":false}"
    check "Disattiva UoM operativa base del figlio" "200" ".data.attivo"
fi
do_curl POST "/api/v1/catalogo/articoli/${CHILD_ID}/disattiva/" "{}"
check "Disattiva articolo figlio" "200" ".data.attivo"

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo "Nota: lo smoke crea due articoli di test e li lascia disattivati."

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
