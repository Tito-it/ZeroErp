#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Conti Bancari
# Uso: ./scripts/tests/smoke-test-conti-bancari.sh [password]
# Prerequisiti: almeno un soggetto e una filiale bancaria nel DB
# ------------------------------------------------------------
# Indice test (0..17):
#  0) Autenticazione JWT
#  1) Lista soggetti — recupera un soggetto esistente
#  2) Lookup filiali bancarie
#  3) Lookup conti bancari (registro IBAN)
#  4) Lista conti bancari del soggetto (iniziale)
#  5) Crea conto bancario soggetto (IBAN nuovo, uso INCASSO, predefinito)
#  6) Lista conti bancari dopo creazione
#  7) Crea secondo conto (uso PAGAMENTO)
#  8) Aggiorna conto — cambia intestazione dichiarata
#  9) Crea conto duplicato (stesso uso+soggetto — atteso 409)
# 10) Elimina secondo conto
# 11) Lista conti bancari dopo eliminazione
# 12) Dettaglio soggetto — verifica sezione conti_bancari
# 13) Recupera ruolo e istanza per test cascata
# 14) Crea conto ruolo con istanza
# 15) Lista conti ruolo con istanza_utility_id — cascata con fonte
# 16) DELETE conto ruolo istanza
# 17) Lista conti ruolo senza istanza — retrocompatibile
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

json_len() {
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
    print(len(d) if isinstance(d, list) else 0)
except Exception:
    print(0)
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
echo " Smoke test API Conti Bancari"
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

# --- 1. Recupera un soggetto esistente ---
echo ""
echo "-- 1. Recupera soggetto esistente --"
do_curl GET "/api/v1/anagrafiche/soggetti/?limit=1"
check "Lista soggetti" "200" ".data.results.0.id"
SOGG_ID="$EXTRACTED"

if [[ -z "$SOGG_ID" || "$SOGG_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessun soggetto nel DB — impossibile proseguire${NC}"
    exit 1
fi
log_info "Soggetto id=$SOGG_ID"

# --- 2. Lookup filiali bancarie ---
echo ""
echo "-- 2. Lookup filiali bancarie --"
do_curl GET "/api/v1/anagrafiche/bank-branches/lookup/?search=banca&limit=5"
if [[ "$LAST_STATUS" == "200" ]]; then
    BRANCH_COUNT=$(json_len "$LAST_BODY" ".data.results")
    log_ok "Lookup filiali (HTTP 200)"
    log_info "Filiali trovate: $BRANCH_COUNT"
    BRANCH_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
else
    log_fail "Lookup filiali — HTTP $LAST_STATUS"
    BRANCH_ID=""
fi

# Se non trovata con "banca", cerca con search piu' generico
if [[ -z "$BRANCH_ID" || "$BRANCH_ID" == "" ]]; then
    log_info "Nessuna filiale con 'banca', provo ricerca generica..."
    do_curl GET "/api/v1/anagrafiche/bank-branches/lookup/?search=fi&limit=1"
    if [[ "$LAST_STATUS" == "200" ]]; then
        BRANCH_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
    fi
fi

if [[ -z "$BRANCH_ID" || "$BRANCH_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessuna filiale bancaria nel DB — impossibile testare creazione${NC}"
    echo -e "${YELLOW}Suggerimento: popolare anagrafiche.bank_branches con almeno una filiale${NC}"
    echo ""
    echo "========================================="
    echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
    echo "========================================="
    exit 1
fi
log_info "Filiale id=$BRANCH_ID"

# --- 3. Lookup conti bancari (registro IBAN) ---
echo ""
echo "-- 3. Lookup conti bancari --"
do_curl GET "/api/v1/anagrafiche/conti-bancari/lookup/?search=IT&limit=5"
check "Lookup IBAN" "200"
IBAN_COUNT=$(json_len "$LAST_BODY" ".data.results")
log_info "IBAN trovati nel registro: $IBAN_COUNT"

# --- 4. Lista conti bancari del soggetto (iniziale) ---
echo ""
echo "-- 4. Lista conti bancari soggetto (iniziale) --"
do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/"
check "Lista conti soggetto" "200"
INITIAL_COUNT=$(json_len "$LAST_BODY" ".data.results")
log_info "Conti iniziali: $INITIAL_COUNT"

# --- 5. Crea conto bancario soggetto ---
echo ""
echo "-- 5. Crea conto bancario (INCASSO, predefinito) --"
# IBAN unico per ogni run
SMOKE_TS=$(date +%s)
SMOKE_IBAN_NUM=$(printf '%023d' "$SMOKE_TS")
SMOKE_IBAN="IT00X${SMOKE_IBAN_NUM}"

do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/" \
    "{
        \"iban\": \"${SMOKE_IBAN}\",
        \"bic_swift\": \"TESTIT00XXX\",
        \"bank_branch_id\": ${BRANCH_ID},
        \"intestatario_predefinito\": \"Smoke Test\",
        \"uso\": \"INCASSO\",
        \"predefinito\": true
    }"
check "Crea conto INCASSO" "200" ".data.id"
CONTO_SOGG_ID_1="$EXTRACTED"
log_info "Legame creato id=$CONTO_SOGG_ID_1, IBAN=$SMOKE_IBAN"

# --- 6. Lista conti bancari dopo creazione ---
echo ""
echo "-- 6. Lista conti dopo creazione --"
do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/"
check "Lista conti dopo create" "200"
AFTER_CREATE_COUNT=$(json_len "$LAST_BODY" ".data.results")
log_info "Conti dopo creazione: $AFTER_CREATE_COUNT (era $INITIAL_COUNT)"

# Verifica che sia aumentato di 1
EXPECTED_COUNT=$((INITIAL_COUNT + 1))
if [[ "$AFTER_CREATE_COUNT" == "$EXPECTED_COUNT" ]]; then
    log_ok "Conteggio corretto (+1)"
else
    log_fail "Conteggio atteso $EXPECTED_COUNT, ottenuto $AFTER_CREATE_COUNT"
fi

# --- 7. Crea secondo conto (uso PAGAMENTO) ---
echo ""
echo "-- 7. Crea secondo conto (PAGAMENTO) --"
SMOKE_IBAN_2="IT00Y$(printf '%023d' $((SMOKE_TS + 1)))"
do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/" \
    "{
        \"iban\": \"${SMOKE_IBAN_2}\",
        \"bank_branch_id\": ${BRANCH_ID},
        \"uso\": \"PAGAMENTO\"
    }"
check "Crea conto PAGAMENTO" "200" ".data.id"
CONTO_SOGG_ID_2="$EXTRACTED"
log_info "Legame creato id=$CONTO_SOGG_ID_2"

# --- 8. Aggiorna conto ---
echo ""
echo "-- 8. Aggiorna conto (intestazione dichiarata) --"
if [[ -n "$CONTO_SOGG_ID_2" && "$CONTO_SOGG_ID_2" != "" ]]; then
    do_curl PATCH "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/${CONTO_SOGG_ID_2}/" \
        "{\"intestazione_dichiarata\": \"Smoke Updated\"}"
    check "Aggiorna intestazione" "200"
else
    log_info "Skipped"
fi

# --- 9. Crea conto duplicato (stesso IBAN + uso — atteso 409) ---
echo ""
echo "-- 9. Crea conto duplicato (atteso 409) --"
do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/" \
    "{
        \"iban\": \"${SMOKE_IBAN}\",
        \"bank_branch_id\": ${BRANCH_ID},
        \"uso\": \"INCASSO\"
    }"
check "Duplicato → errore 409" "409"
ERRCODE=$(json_get "$LAST_BODY" ".error.code")
log_info "Codice errore: $ERRCODE"

# --- 10. Elimina secondo conto ---
echo ""
echo "-- 10. Elimina secondo conto --"
if [[ -n "$CONTO_SOGG_ID_2" && "$CONTO_SOGG_ID_2" != "" ]]; then
    do_curl DELETE "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/${CONTO_SOGG_ID_2}/"
    check "Elimina conto" "200"
else
    log_info "Skipped"
fi

# --- 11. Lista conti dopo eliminazione ---
echo ""
echo "-- 11. Lista conti dopo eliminazione --"
do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/"
check "Lista conti dopo delete" "200"
AFTER_DELETE_COUNT=$(json_len "$LAST_BODY" ".data.results")
log_info "Conti dopo eliminazione: $AFTER_DELETE_COUNT"

# --- 12. Dettaglio soggetto — verifica sezione conti_bancari ---
echo ""
echo "-- 12. Dettaglio soggetto — sezione conti_bancari --"
do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/"
check "Dettaglio soggetto" "200"
CB_IN_DETAIL=$(json_len "$LAST_BODY" ".data.conti_bancari")
log_info "Conti bancari nel dettaglio soggetto: $CB_IN_DETAIL"

# Verifica che la chiave conti_bancari esista nel dettaglio
HAS_CB_KEY=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('yes' if 'conti_bancari' in d.get('data', {}) else 'no')
" 2>/dev/null)
if [[ "$HAS_CB_KEY" == "yes" ]]; then
    log_ok "Chiave conti_bancari presente nel dettaglio"
else
    log_fail "Chiave conti_bancari mancante nel dettaglio soggetto"
fi

# --- 13. Recupera ruolo e istanza per test cascata ---
echo ""
echo "-- 13. Recupera ruolo e istanza --"

RUOLO_ID=""
ISTANZA_UTILITY_ID=""

# Cerca un cliente per avere soggetto_ruolo_id e istanza_utility_id
do_curl GET "/api/v1/anagrafiche/clienti/?limit=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    RUOLO_ID=$(json_get "$LAST_BODY" ".data.results.0.soggetto_ruolo_id")
    ISTANZA_UTILITY_ID=$(json_get "$LAST_BODY" ".data.results.0.istanza_utility_id")
fi

# Fallback: ruoli del soggetto
if [[ -z "$RUOLO_ID" || "$RUOLO_ID" == "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/"
    if [[ "$LAST_STATUS" == "200" ]]; then
        RUOLO_ID=$(json_get "$LAST_BODY" ".data.0.id")
    fi
fi

CONTO_RUOLO_IST_ID=""

if [[ -n "$RUOLO_ID" && "$RUOLO_ID" != "" ]]; then
    log_ok "Ruolo id=$RUOLO_ID trovato"

    # --- 14. Crea conto ruolo con istanza ---
    echo ""
    echo "-- 14. Crea conto ruolo con istanza --"

    SMOKE_IBAN_RUOLO="IT00Z$(printf '%023d' $((SMOKE_TS + 2)))"

    PAYLOAD="{\"iban\": \"${SMOKE_IBAN_RUOLO}\", \"bank_branch_id\": ${BRANCH_ID}, \"uso\": \"INCASSO\""
    if [[ -n "$ISTANZA_UTILITY_ID" && "$ISTANZA_UTILITY_ID" != "" && "$ISTANZA_UTILITY_ID" != "None" ]]; then
        PAYLOAD="${PAYLOAD}, \"istanza_utility_id\": ${ISTANZA_UTILITY_ID}"
    fi
    PAYLOAD="${PAYLOAD}}"

    do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/conti-bancari/" "$PAYLOAD"
    if [[ "$LAST_STATUS" == "200" ]]; then
        check "Crea conto ruolo" "200" ".data.id"
        CONTO_RUOLO_IST_ID="$EXTRACTED"
        log_info "Conto ruolo creato id=$CONTO_RUOLO_IST_ID"
    else
        log_info "Crea conto ruolo fallito — HTTP $LAST_STATUS (possibile vincolo UNIQUE)"
    fi

    # --- 15. Lista conti ruolo con istanza_utility_id ---
    echo ""
    echo "-- 15. Lista conti ruolo con cascata istanza --"

    if [[ -n "$ISTANZA_UTILITY_ID" && "$ISTANZA_UTILITY_ID" != "" && "$ISTANZA_UTILITY_ID" != "None" ]]; then
        do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/conti-bancari/?istanza_utility_id=${ISTANZA_UTILITY_ID}"
    else
        do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/conti-bancari/"
    fi
    check "Lista conti ruolo cascata" "200"
    CR_COUNT=$(json_len "$LAST_BODY" ".data.conti_ruolo")
    CE_COUNT=$(json_len "$LAST_BODY" ".data.conti_ereditati")
    log_info "Conti ruolo: $CR_COUNT, ereditati: $CE_COUNT"

    # Verifica campo fonte nei conti_ruolo
    if [[ "$CR_COUNT" -gt 0 ]]; then
        FIRST_FONTE=$(json_get "$LAST_BODY" ".data.conti_ruolo.0.fonte")
        if [[ "$FIRST_FONTE" == "istanza" || "$FIRST_FONTE" == "ruolo" ]]; then
            log_ok "Campo fonte presente: '$FIRST_FONTE'"
        else
            log_fail "Campo fonte mancante o errato: '$FIRST_FONTE'"
        fi
    fi

    # --- 16. DELETE conto ruolo istanza ---
    echo ""
    echo "-- 16. DELETE conto ruolo istanza --"
    if [[ -n "$CONTO_RUOLO_IST_ID" && "$CONTO_RUOLO_IST_ID" != "" ]]; then
        do_curl DELETE "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/conti-bancari/${CONTO_RUOLO_IST_ID}/"
        check "DELETE conto ruolo" "200"
    else
        log_info "Skip — nessun conto ruolo creato"
    fi

    # --- 17. Lista conti ruolo senza istanza (retrocompatibile) ---
    echo ""
    echo "-- 17. Lista conti ruolo senza istanza --"
    do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/conti-bancari/"
    check "Lista conti ruolo (no istanza)" "200"
    CR_FINAL=$(json_len "$LAST_BODY" ".data.conti_ruolo")
    CE_FINAL=$(json_len "$LAST_BODY" ".data.conti_ereditati")
    log_info "Finale: ruolo=$CR_FINAL, ereditati=$CE_FINAL"

else
    log_info "Nessun ruolo trovato — skip test 13-17"
fi

# --- Cleanup: elimina il primo conto creato ---
echo ""
echo "-- Cleanup --"
if [[ -n "$CONTO_SOGG_ID_1" && "$CONTO_SOGG_ID_1" != "" ]]; then
    do_curl DELETE "/api/v1/anagrafiche/soggetti/${SOGG_ID}/conti-bancari/${CONTO_SOGG_ID_1}/"
    if [[ "$LAST_STATUS" == "200" ]]; then
        log_ok "Cleanup conto INCASSO eliminato"
    else
        log_info "Cleanup conto INCASSO — HTTP $LAST_STATUS"
    fi
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
