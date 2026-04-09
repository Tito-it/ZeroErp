#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Vendite Listini (Fase 5 backend)
# Uso: ./scripts/tests/smoke-test-listini.sh [password]
# ------------------------------------------------------------
# Indice test (0..30):
#  0) Autenticazione JWT + estrazione user_id
#  1) Preflight permessi aree vendite/catalogo + anagrafiche
#  2) Seed articolo attivo + UoM da catalogo
#  3) Crea listino
#  4) Dettaglio listino creato
#  5) PATCH listino
#  6) PATCH codice listino non ammesso (400 atteso)
#  7) Crea versione SENZA valido_dal (400 atteso)
#  7b) Crea versione BOZZA con valido_dal
#  8) Lista versioni
#  9) PATCH versione
# 10) Crea riga prezzo fallback
# 11) Lista righe prezzo
# 12) PATCH riga prezzo
# 13) Lookup BA con scope emittente (q < 2 char rifiutato)
# 13b) Lookup BA con q valida (200 + struttura results)
# 13c) Crea associazione fallback (senza BA)
# 14) Lista associazioni
# 15) PATCH associazione
# 16) Attiva versione
# 17) Test resolver prezzo
# 18) [F2] PATCH versione ATTIVA con valido_al ammesso (200 atteso)
# 19) [F2] PATCH versione ATTIVA con codice_versione rifiutato (400 atteso)
# 20) [F1] POST riga su versione ATTIVA rifiutato (400 atteso)
# 21) [F1] PATCH riga su versione ATTIVA rifiutato (400 atteso)
# 22) [F1] DELETE riga su versione ATTIVA rifiutato (400 atteso)
# 23) [O1/D2] Clone versione retroattivo prima di src.valido_dal (400 atteso)
# 24) [O1] Clone versione ATTIVA in nuova BOZZA con valido_dal futuro
# 25) [D3] Preview attivazione clone (dry_run=true) — verifica auto-close listato
# 26) [D3] Attivazione clone reale: precedente auto-chiusa, clone passa ad ATTIVA
# 27) [O2] DELETE versione ATTIVA rifiutato (400 atteso)
# 28) DELETE associazione
# 29) [O3] DELETE listino con figli rifiutato (400 atteso)
# 30) Cleanup finale: PATCH listino attivo=false (soft-delete)
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
echo " Smoke test API Vendite Listini"
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

# --- 1. Preflight permessi aree vendite/catalogo ---
echo ""
echo "-- 1. Preflight permessi aree vendite/catalogo --"
do_curl GET "/api/v1/core/users/${USER_ID}/permessi-effettivi/"
check "Permessi effettivi utente corrente" "200"

readarray -t PERM_LEVELS < <(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    areas = json.load(sys.stdin)['data']['aree']
    wanted = {'vendite': '', 'catalogo': ''}
    for area in areas:
        schema = area.get('schema_db')
        if schema in wanted:
            wanted[schema] = area.get('livello', '')
    print(wanted['vendite'])
    print(wanted['catalogo'])
except Exception:
    print('')
    print('')
" 2>/dev/null)

VENDITE_LEVEL="${PERM_LEVELS[0]:-}"
CATALOGO_LEVEL="${PERM_LEVELS[1]:-}"

if [[ -z "$VENDITE_LEVEL" ]]; then
    echo -e "${RED}ERRORE:${NC} area funzionale 'vendite' non trovata nei permessi effettivi dell'utente."
    exit 2
fi

if [[ "$VENDITE_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' senza permesso write su 'vendite' (livello=$VENDITE_LEVEL)."
    echo "Per questo smoke serve livello TUTTO sull'area vendite."
    exit 2
fi

if [[ -z "$CATALOGO_LEVEL" ]]; then
    echo -e "${RED}ERRORE:${NC} area funzionale 'catalogo' non trovata nei permessi effettivi dell'utente."
    exit 2
fi

if [[ "$CATALOGO_LEVEL" != "LETTURA" && "$CATALOGO_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' senza permesso read su 'catalogo' (livello=$CATALOGO_LEVEL)."
    echo "Per questo smoke serve almeno LETTURA sull'area catalogo."
    exit 2
fi

log_ok "Permessi vendite validi per CRUD (livello=$VENDITE_LEVEL)"
log_ok "Permessi catalogo validi per lookup seed (livello=$CATALOGO_LEVEL)"

# --- 1.5 Cleanup residui run precedenti ---
# Lo smoke test non e' idempotente di natura: se un run fallisce a meta'
# (es. step 17 in pareggio resolver) i listini SMK-LST-* restano attivi
# in DB con le loro associazioni, e i run successivi producono N
# candidati con stesso match level sullo stesso articolo seed → tie.
# Disattiviamo le associazioni dei listini SMK-LST-* preesistenti via
# dbshell prima di iniziare. Le associazioni inattive sono ignorate dal
# resolver, quindi e' sufficiente per garantire un campo pulito.
echo ""
echo "-- 1.5 Cleanup associazioni residue listini SMK-LST-* --"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CLEANUP_OUT=$("${BACKEND_DIR}/manage-env.sh" dbshell -- -t -A -c "
    UPDATE vendite.listini_associazioni a
       SET attivo = false
      FROM vendite.listini l
     WHERE a.listino_id = l.id
       AND l.codice LIKE 'SMK-LST-%'
       AND a.attivo IS TRUE
    RETURNING a.id
" 2>/dev/null | grep -cE '^[0-9]+$' || true)
log_info "Associazioni smoke residue disattivate: ${CLEANUP_OUT}"

TEST_SUFFIX=$(date +%Y%m%d%H%M%S)
TODAY=$(date +%F)
LISTINO_CODE="SMK-LST-${TEST_SUFFIX}"
LISTINO_DESC="Smoke listino ${TEST_SUFFIX}"
LISTINO_DESC_UPDATED="Smoke listino aggiornato ${TEST_SUFFIX}"
VERSION_CODE="V-${TEST_SUFFIX}"

# --- 2. Seed articolo attivo + UoM da catalogo ---
echo ""
echo "-- 2. Seed articolo attivo + UoM --"
do_curl GET "/api/v1/catalogo/articoli/?attivo=true&page=1&page_size=1&order_by=codice&order_dir=asc"
check "Lista articoli attivi seed" "200"
ARTICOLO_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
ARTICOLO_CODE=$(json_get "$LAST_BODY" ".data.results.0.codice")
UOM_ID=$(json_get "$LAST_BODY" ".data.results.0.uom_id")
UOM_CODE=$(json_get "$LAST_BODY" ".data.results.0.uom_codice")

if [[ -z "$ARTICOLO_ID" || -z "$UOM_ID" ]]; then
    echo -e "${RED}ERRORE:${NC} nessun articolo attivo con UoM disponibile trovato; impossibile eseguire lo smoke listini."
    exit 3
fi

log_info "Articolo seed: id=${ARTICOLO_ID} codice=${ARTICOLO_CODE:-?} uom_id=${UOM_ID} uom=${UOM_CODE:-?}"

# --- 3. Crea listino ---
echo ""
echo "-- 3. Crea listino --"
do_curl POST "/api/v1/vendite/listini/" "{\"codice\":\"${LISTINO_CODE}\",\"descrizione\":\"${LISTINO_DESC}\",\"dominio\":\"COMMERCIO\"}"
check "Create listino" "200" ".data.id"
LISTINO_ID="$EXTRACTED"
log_info "Listino creato: id=${LISTINO_ID} codice=${LISTINO_CODE}"

# --- 4. Dettaglio listino creato ---
echo ""
echo "-- 4. Dettaglio listino creato --"
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/"
check "Dettaglio listino creato" "200" ".data.codice"
if [[ "$EXTRACTED" == "$LISTINO_CODE" ]]; then
    log_ok "Codice dettaglio coerente (${EXTRACTED})"
else
    log_fail "Codice dettaglio incoerente: atteso ${LISTINO_CODE}, ricevuto ${EXTRACTED:-<vuoto>}"
fi

# --- 5. PATCH listino ---
echo ""
echo "-- 5. PATCH listino --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/" "{\"descrizione\":\"${LISTINO_DESC_UPDATED}\"}"
check "PATCH listino descrizione" "200" ".data.descrizione"
if [[ "$EXTRACTED" == "$LISTINO_DESC_UPDATED" ]]; then
    log_ok "Descrizione listino aggiornata coerente"
else
    log_fail "Descrizione listino incoerente: atteso '${LISTINO_DESC_UPDATED}', ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 6. PATCH codice listino non ammesso ---
echo ""
echo "-- 6. PATCH codice listino non ammesso --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/" "{\"codice\":\"${LISTINO_CODE}-NEW\"}"
check "PATCH codice listino non ammesso" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 7. Crea versione SENZA valido_dal (400 atteso) ---
echo ""
echo "-- 7. Crea versione SENZA valido_dal (atteso 400) --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/" "{\"codice_versione\":\"${VERSION_CODE}-NODATE\"}"
check "Create versione senza valido_dal rifiutata" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 7b. Crea versione BOZZA con valido_dal ---
echo ""
echo "-- 7b. Crea versione BOZZA con valido_dal --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/" "{\"codice_versione\":\"${VERSION_CODE}\",\"valido_dal\":\"${TODAY}\"}"
check "Create versione BOZZA" "200" ".data.id"
VERSIONE_ID="$EXTRACTED"
log_info "Versione creata: id=${VERSIONE_ID} codice=${VERSION_CODE}"

# --- 8. Lista versioni ---
echo ""
echo "-- 8. Lista versioni --"
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/versioni/"
check "Lista versioni listino" "200" ".data.count"
log_info "Versioni trovate: ${EXTRACTED:-?}"

# --- 9. PATCH versione (aggiorna codice_versione su BOZZA) ---
echo ""
echo "-- 9. PATCH versione --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/" "{\"codice_versione\":\"${VERSION_CODE}-r2\"}"
check "PATCH versione codice" "200" ".data.codice_versione"
log_info "Codice versione aggiornato: ${EXTRACTED:-n/d}"

# --- 10. Crea riga prezzo fallback ---
echo ""
echo "-- 10. Crea riga prezzo fallback --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/" "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"prezzo\":\"12.5000000000\"}"
check "Create riga prezzo fallback" "200" ".data.id"
RIGA_ID="$EXTRACTED"
log_info "Riga creata: id=${RIGA_ID}"

# --- 11. Lista righe prezzo ---
echo ""
echo "-- 11. Lista righe prezzo --"
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/"
check "Lista righe prezzo" "200" ".data.count"
log_info "Righe trovate: ${EXTRACTED:-?}"

# --- 12. PATCH riga prezzo ---
echo ""
echo "-- 12. PATCH riga prezzo --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/${RIGA_ID}/" "{\"prezzo\":\"13.7500000000\"}"
check "PATCH riga prezzo" "200" ".data.prezzo"
log_info "Prezzo riga aggiornato: ${EXTRACTED:-n/d}"

# --- 13. Lookup BA: query troppo corta (400 atteso) ---
echo ""
echo "-- 13. Lookup BA q troppo corta --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=A"
check "Lookup BA q < 2 char rifiutato" "400" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 13b. Lookup BA con query valida ---
echo ""
echo "-- 13b. Lookup BA con q valida --"
do_curl GET "/api/v1/anagrafiche/billing-account/lookup/?q=BA"
check "Lookup BA q valida" "200" ".data.limit"
LOOKUP_LIMIT="$EXTRACTED"
LOOKUP_TOTAL=$(json_get "$LAST_BODY" ".data.total_count")
LOOKUP_FIRST_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
log_info "Lookup BA: limit=${LOOKUP_LIMIT:-?} total=${LOOKUP_TOTAL:-?} first_id=${LOOKUP_FIRST_ID:-<vuoto>}"
# Se c'e' almeno un BA, prova anche il restore by id
if [[ -n "$LOOKUP_FIRST_ID" ]]; then
    do_curl GET "/api/v1/anagrafiche/billing-account/${LOOKUP_FIRST_ID}/lookup/"
    check "Lookup BA restore by id" "200" ".data.id"
    log_info "Restore BA: id=${EXTRACTED:-?}"
fi

# --- 13c. Crea associazione fallback (senza BA per coerenza con seed) ---
echo ""
echo "-- 13c. Crea associazione fallback --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/associazioni/" "{\"valido_dal\":\"${TODAY}\"}"
check "Create associazione fallback" "200" ".data.id"
ASSOC_ID="$EXTRACTED"
log_info "Associazione creata: id=${ASSOC_ID}"

# --- 14. Lista associazioni ---
echo ""
echo "-- 14. Lista associazioni --"
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/associazioni/"
check "Lista associazioni listino" "200" ".data.count"
log_info "Associazioni trovate: ${EXTRACTED:-?}"

# --- 15. PATCH associazione (programmazione chiusura via valido_al) ---
echo ""
echo "-- 15. PATCH associazione --"
ASSOC_VALIDO_AL=$(date -d "+180 days" +%F 2>/dev/null || date -v+180d +%F)
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/associazioni/${ASSOC_ID}/" "{\"valido_al\":\"${ASSOC_VALIDO_AL}\"}"
check "PATCH associazione valido_al" "200" ".data.valido_al"
log_info "Associazione valido_al aggiornato: ${EXTRACTED:-n/d}"

# --- 16. Attiva versione ---
echo ""
echo "-- 16. Attiva versione --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/stato/" "{\"stato\":\"ATTIVA\"}"
check "Attiva versione listino" "200" ".data.stato"
if [[ "$EXTRACTED" == "ATTIVA" ]]; then
    log_ok "Versione attivata coerentemente"
else
    log_fail "Stato versione incoerente: atteso ATTIVA, ricevuto '${EXTRACTED:-<vuoto>}'"
fi

# --- 17. Test resolver prezzo ---
echo ""
echo "-- 17. Test resolver prezzo --"
do_curl POST "/api/v1/vendite/listini/test-prezzo/" "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"data_riferimento\":\"${TODAY}\"}"
check "Test resolver prezzo" "200" ".data.prezzo"
log_info "Prezzo risolto: ${EXTRACTED:-n/d}"
MATCH_LEVEL=$(json_get "$LAST_BODY" ".data.match_level")
log_info "Match level: ${MATCH_LEVEL:-n/d}"

# --- 18. [F2] PATCH versione ATTIVA: valido_al ammesso ---
echo ""
echo "-- 18. [F2] PATCH versione ATTIVA: valido_al ammesso --"
FUTURE_DATE=$(date -d "+90 days" +%F 2>/dev/null || date -v+90d +%F)
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/" "{\"valido_al\":\"${FUTURE_DATE}\"}"
check "PATCH valido_al su versione ATTIVA" "200" ".data.valido_al"
log_info "valido_al aggiornato: ${EXTRACTED:-n/d}"

# --- 19. [F2] PATCH versione ATTIVA: codice_versione rifiutato ---
echo ""
echo "-- 19. [F2] PATCH versione ATTIVA: codice_versione rifiutato --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/" "{\"codice_versione\":\"V999-NO\"}"
check "PATCH codice_versione su versione ATTIVA" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 20. [F1] POST riga su versione ATTIVA rifiutato ---
echo ""
echo "-- 20. [F1] POST riga su versione ATTIVA rifiutato --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/" \
    "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"prezzo\":\"99.99\"}"
check "POST riga su versione ATTIVA" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 21. [F1] PATCH riga su versione ATTIVA rifiutato ---
echo ""
echo "-- 21. [F1] PATCH riga su versione ATTIVA rifiutato --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/${RIGA_ID}/" "{\"prezzo\":\"77.77\"}"
check "PATCH riga su versione ATTIVA" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 22. [F1] DELETE riga su versione ATTIVA rifiutato ---
echo ""
echo "-- 22. [F1] DELETE riga su versione ATTIVA rifiutato --"
do_curl DELETE "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/${RIGA_ID}/"
check "DELETE riga su versione ATTIVA" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 23. [O1/D2] Clone con valido_dal precedente alla sorgente: 400 atteso ---
echo ""
echo "-- 23. [O1/D2] Clone retroattivo prima di src.valido_dal --"
SRC_VALIDO_DAL=$(date +%F)
DATA_PRIMA_SRC=$(date -d "$SRC_VALIDO_DAL -1 day" +%F 2>/dev/null || date -v-1d -j -f "%F" "$SRC_VALIDO_DAL" +%F)
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/clona/" \
    "{\"codice_versione\":\"${VERSION_CODE}-clone-bad\",\"valido_dal\":\"${DATA_PRIMA_SRC}\"}"
check "Clone retroattivo oltre src" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 24. [O1] Clone versione in nuova BOZZA con valido_dal futuro ---
echo ""
echo "-- 24. [O1] Clone versione ATTIVA in nuova BOZZA --"
CLONE_VALIDO_DAL=$(date -d "+30 days" +%F 2>/dev/null || date -v+30d +%F)
CLONE_CODE="${VERSION_CODE}-clone"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/clona/" \
    "{\"codice_versione\":\"${CLONE_CODE}\",\"valido_dal\":\"${CLONE_VALIDO_DAL}\"}"
check "Clone versione" "200" ".data.id"
CLONE_VERSIONE_ID="$EXTRACTED"
log_info "Clone creato: id=${CLONE_VERSIONE_ID} codice=${CLONE_CODE} valido_dal=${CLONE_VALIDO_DAL}"
CLONE_RIGHE=$(json_get "$LAST_BODY" ".data.righe_count")
log_info "Righe copiate: ${CLONE_RIGHE:-n/d}"

# --- 25. [D3] Preview attivazione clone (dry_run=true) ---
echo ""
echo "-- 25. [D3] Preview attivazione clone (dry_run) --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${CLONE_VERSIONE_ID}/stato/" \
    "{\"stato\":\"ATTIVA\",\"dry_run\":true}"
check "Preview attivazione clone" "200" ".data.dry_run"
PREVIEW_AUTOCLOSE_COUNT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    print(len(json.load(sys.stdin)['data']['auto_close']))
except Exception:
    print('')
" 2>/dev/null)
if [[ "$PREVIEW_AUTOCLOSE_COUNT" == "1" ]]; then
    log_ok "Preview elenca 1 versione da auto-chiudere (la sorgente)"
else
    log_fail "Preview auto_close count atteso=1 ricevuto='${PREVIEW_AUTOCLOSE_COUNT:-<vuoto>}'"
fi

# --- 26. [D3] Attivazione reale del clone con auto-close della precedente ---
echo ""
echo "-- 26. [D3] Attivazione clone reale con auto-close --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${CLONE_VERSIONE_ID}/stato/" \
    "{\"stato\":\"ATTIVA\"}"
check "Attiva clone" "200" ".data.stato"
if [[ "$EXTRACTED" == "ATTIVA" ]]; then
    log_ok "Clone passato a ATTIVA"
else
    log_fail "Stato clone inatteso: '${EXTRACTED:-<vuoto>}'"
fi
# Verifica che la sorgente abbia ora valido_al = clone.valido_dal - 1
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/"
check "Verifica auto-close sorgente" "200" ".data.valido_al"
SORGENTE_VALIDO_AL_ATTESO=$(date -d "${CLONE_VALIDO_DAL} -1 day" +%F 2>/dev/null || date -v-1d -j -f "%F" "$CLONE_VALIDO_DAL" +%F)
if [[ "$EXTRACTED" == "$SORGENTE_VALIDO_AL_ATTESO" ]]; then
    log_ok "Sorgente auto-chiusa al ${EXTRACTED}"
else
    log_fail "Sorgente valido_al atteso=${SORGENTE_VALIDO_AL_ATTESO} ricevuto='${EXTRACTED:-<vuoto>}'"
fi

# --- 27. [O2] DELETE versione ATTIVA rifiutato ---
echo ""
echo "-- 27. [O2] DELETE versione ATTIVA rifiutato --"
do_curl DELETE "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${CLONE_VERSIONE_ID}/"
check "DELETE versione ATTIVA" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 28. DELETE associazione ---
echo ""
echo "-- 28. DELETE associazione --"
do_curl DELETE "/api/v1/vendite/listini/${LISTINO_ID}/associazioni/${ASSOC_ID}/"
check "DELETE associazione" "200" ".data.deleted"
log_info "Associazione rimossa: ${EXTRACTED:-n/d}"

# --- 29. [O3] DELETE listino con figli rifiutato ---
echo ""
echo "-- 29. [O3] DELETE listino con figli rifiutato --"
do_curl DELETE "/api/v1/vendite/listini/${LISTINO_ID}/"
check "DELETE listino con figli" "400" ".error.code"
if [[ "$EXTRACTED" == "E_VENDITE_VALIDATION" ]]; then
    log_ok "Errore corretto: $EXTRACTED (listino ha versioni, suggerito attivo=false)"
else
    log_fail "Codice errore inatteso: '${EXTRACTED:-<vuoto>}'"
fi

# --- 30. Cleanup finale: tentativo soft-delete listino (best-effort) ---
# Nota: alcune installazioni hanno un trigger DB che impedisce di disattivare
# un listino con versioni/associazioni attive. Questo step e' best-effort:
# se fallisce non blocca lo smoke.
echo ""
echo "-- 30. Cleanup finale (PATCH attivo=false, best-effort) --"
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/" "{\"attivo\":false}"
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "Listino disattivato (cleanup riuscito)"
else
    log_info "Cleanup non riuscito (HTTP $LAST_STATUS): listino di test resta attivo. Lo smoke ha completato i test funzionali."
fi

echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo "Nota: lo smoke disattiva il listino di test (attivo=false) ma non lo elimina"
echo "      perche' contiene versioni e righe storiche (vedi guard O3)."

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
