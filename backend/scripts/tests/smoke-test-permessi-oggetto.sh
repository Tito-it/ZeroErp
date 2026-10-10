#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API override oggetti (permessi v2 — livello model)
# Uso: ./scripts/tests/smoke-test-permessi-oggetto.sh [password]
# Prerequisiti:
#  - almeno un operatore non-super-admin presente nel DB
#  - catalogo config.area_model_overrides popolato (seed 11 model)
# Copertura:
#  - CRUD admin su override oggetti
#  - Validazione catalogo (model non registrato -> errore)
#  - Idempotenza (stato iniziale ripristinato a fine run)
# Nota: l'enforcement BE (403 su endpoint con model_permission + livello
# LETTURA/BLOCCATO) e' gia' coperto da pgTAP
# db/pgtap/script/test-permessi-funzioni-risoluzione.sql (test 7-9, 31-34).
# La verifica end-to-end FE (drawer readonly via useReadonlyMode + modelName)
# resta test manuale browser.
# ------------------------------------------------------------
# Indice test (0..11):
#  0) Autenticazione JWT
#  1) Lookup catalogo model-overrides — >= 1 riga
#  2) Lista operatori non-super-admin — pick target
#  3) Stato iniziale override oggetti target (snapshot per cleanup)
#  4) PUT override BLOCCATO su anagrafiche.conto_bancario
#  5) GET verifica persistenza BLOCCATO
#  6) PUT con model non registrato — atteso 4xx (E_AMM_VALIDAZIONE)
#  7) PUT aggiornamento a LETTURA (stesso model)
#  8) GET verifica livello LETTURA
#  9) PUT lista vuota — cancellazione completa
# 10) GET verifica lista vuota
# 11) Ripristino stato iniziale (idempotenza)
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

# Scopo: filtra per livello in un payload lista (data.results[*]).
json_livello_per_model() {
    local json="$1" app="$2" model="$3"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    items = d.get('data', {}).get('results', []) or d.get('results', [])
    for it in items:
        if it.get('app_label') == '$app' and it.get('model_name') == '$model':
            print(it.get('livello',''))
            break
    else:
        print('')
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
    local label="$1" expected="$2"
    if [[ "$LAST_STATUS" == "$expected" ]]; then
        log_ok "$label (HTTP $LAST_STATUS)"
    else
        log_fail "$label — atteso HTTP $expected, ricevuto $LAST_STATUS"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
        return 1
    fi
    return 0
}

# ================================================================
echo ""
echo "========================================="
echo " Smoke test Override Oggetti (permessi v2)"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Autenticazione JWT ($USERNAME)"

# --- 1. Lookup catalogo model-overrides ---
echo ""
echo "-- 1. Catalogo model-overrides --"
do_curl GET "/api/v1/amm-software/lookup/model-overrides/"
check "Lookup catalogo" "200" || exit 1
CATALOG_LEN=$(json_len "$LAST_BODY" ".data.results")
if [[ "$CATALOG_LEN" -ge 1 ]]; then
    log_ok "Catalogo contiene $CATALOG_LEN model"
else
    log_fail "Catalogo vuoto (atteso >= 1) — verificare seed 80_data"
    exit 1
fi

# Verifica presenza di anagrafiche.conto_bancario (usato nei test 4-5)
HAS_CB=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('results', [])
print('yes' if any(i.get('app_label')=='anagrafiche' and i.get('model_name')=='conto_bancario' for i in items) else 'no')
" 2>/dev/null)
if [[ "$HAS_CB" == "yes" ]]; then
    log_ok "Catalogo include anagrafiche.conto_bancario"
else
    log_fail "anagrafiche.conto_bancario non presente nel catalogo — test downstream non significativi"
    exit 1
fi

# --- 2. Pick operatore non-super-admin ---
echo ""
echo "-- 2. Pick operatore target --"
do_curl GET "/api/v1/amm-software/operatori/?is_super_admin=false&is_active=true&limit=50"
check "Lista operatori non-super-admin" "200" || exit 1

# Scopo: escludi l'utente corrente (admin) e prendi il primo altro operatore.
TARGET_ID=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('results', [])
# preferenza: ruolo_sistema = OPERATIVO
for it in items:
    if (it.get('ruolo_sistema') == 'OPERATIVO'
        and it.get('username') != '$USERNAME'):
        print(it.get('auth_user_id') or it.get('id'))
        break
else:
    for it in items:
        if it.get('username') != '$USERNAME':
            print(it.get('auth_user_id') or it.get('id'))
            break
    else:
        print('')
" 2>/dev/null)

if [[ -z "$TARGET_ID" ]]; then
    log_fail "Nessun operatore non-super-admin disponibile per il test — creane uno e rilancia"
    exit 1
fi
log_ok "Target operatore auth_user_id=$TARGET_ID"

# --- 3. Snapshot stato iniziale (per cleanup idempotente) ---
echo ""
echo "-- 3. Snapshot stato iniziale --"
do_curl GET "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/"
check "GET override oggetti iniziale" "200" || exit 1
INITIAL_LEN=$(json_len "$LAST_BODY" ".data.results")
INITIAL_ITEMS=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('results', [])
out = [{'app_label': i['app_label'], 'model_name': i['model_name'],
        'livello': i['livello'], 'motivo': i.get('motivo'),
        'valido_dal': i.get('valido_dal'), 'valido_al': i.get('valido_al')}
       for i in items]
print(json.dumps(out))
" 2>/dev/null)
log_info "Override iniziali: $INITIAL_LEN item(s). Snapshot salvato per ripristino."

# --- 4. PUT override BLOCCATO su anagrafiche.conto_bancario ---
echo ""
echo "-- 4. PUT override BLOCCATO --"
PAYLOAD='{"items":[{"app_label":"anagrafiche","model_name":"conto_bancario","livello":"BLOCCATO","motivo":"smoke-test"}]}'
do_curl PUT "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/" "$PAYLOAD"
check "PUT override BLOCCATO" "200" || exit 1

# --- 5. GET verifica persistenza ---
echo ""
echo "-- 5. Verifica persistenza BLOCCATO --"
do_curl GET "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/"
check "GET dopo PUT BLOCCATO" "200" || exit 1
LIV=$(json_livello_per_model "$LAST_BODY" "anagrafiche" "conto_bancario")
if [[ "$LIV" == "BLOCCATO" ]]; then
    log_ok "Livello persistito = BLOCCATO"
else
    log_fail "Livello atteso=BLOCCATO, trovato='$LIV'"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 6. PUT con model non registrato — atteso 4xx ---
echo ""
echo "-- 6. Validazione catalogo --"
BAD_PAYLOAD='{"items":[{"app_label":"fantasma","model_name":"inesistente","livello":"BLOCCATO"}]}'
do_curl PUT "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/" "$BAD_PAYLOAD"
if [[ "$LAST_STATUS" =~ ^4 ]]; then
    log_ok "PUT con model non registrato respinto (HTTP $LAST_STATUS)"
else
    log_fail "Atteso 4xx, ricevuto HTTP $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 7. PUT aggiornamento a LETTURA ---
echo ""
echo "-- 7. PUT aggiornamento LETTURA --"
PAYLOAD='{"items":[{"app_label":"anagrafiche","model_name":"conto_bancario","livello":"LETTURA","motivo":"smoke-test-update"}]}'
do_curl PUT "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/" "$PAYLOAD"
check "PUT update a LETTURA" "200" || exit 1

# --- 8. GET verifica LETTURA ---
echo ""
echo "-- 8. Verifica livello LETTURA --"
do_curl GET "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/"
check "GET dopo PUT LETTURA" "200" || exit 1
LIV=$(json_livello_per_model "$LAST_BODY" "anagrafiche" "conto_bancario")
if [[ "$LIV" == "LETTURA" ]]; then
    log_ok "Livello aggiornato = LETTURA"
else
    log_fail "Livello atteso=LETTURA, trovato='$LIV'"
fi

# --- 9. PUT lista vuota — cancellazione ---
echo ""
echo "-- 9. PUT lista vuota --"
do_curl PUT "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/" '{"items":[]}'
check "PUT cancellazione" "200" || exit 1

# --- 10. GET verifica vuoto ---
echo ""
echo "-- 10. Verifica lista vuota --"
do_curl GET "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/"
check "GET dopo cancellazione" "200" || exit 1
LEN=$(json_len "$LAST_BODY" ".data.results")
if [[ "$LEN" == "0" ]]; then
    log_ok "Lista override vuota"
else
    log_fail "Atteso 0 item, trovato $LEN"
fi

# --- 11. Ripristino stato iniziale (idempotenza) ---
echo ""
echo "-- 11. Ripristino stato iniziale --"
RESTORE_PAYLOAD="{\"items\":$INITIAL_ITEMS}"
do_curl PUT "/api/v1/amm-software/operatori/$TARGET_ID/override-oggetti/" "$RESTORE_PAYLOAD"
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "Stato iniziale ripristinato ($INITIAL_LEN item)"
else
    log_fail "Ripristino fallito (HTTP $LAST_STATUS) — verificare manualmente l'operatore $TARGET_ID"
fi

# ================================================================
echo ""
echo "========================================="
echo " Riepilogo: PASS=$PASS FAIL=$FAIL"
echo "========================================="

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
