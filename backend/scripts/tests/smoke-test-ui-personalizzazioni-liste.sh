#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API UI personalizzazioni liste
# Uso: ./scripts/tests/smoke-test-ui-personalizzazioni-liste.sh [password]
# Prerequisiti:
#   - Backend Django in esecuzione su BASE_URL (default localhost:8000)
#   - Seed Blocco E atterrati su DB (`anagrafiche.clienti` in
#     ui.lista_definizione + lista_colonna + lista_preset + lista_preset_colonna)
#   - Utente con accesso ai domini `/api/v1/ui/*` (skip_area_check, JWT operatore)
# ------------------------------------------------------------
# Indice test (0..9):
#  0) Autenticazione JWT
#  1) Cleanup proattivo: DELETE preferenza precedente (silent OK)
#  2) GET /config con codice valido → 200, JSONB con colonne risolte
#  3) GET /config con codice inesistente → 404 E_UI_LISTA_NON_TROVATA
#  4) GET /catalogo con codice valido → 200, lista colonne arricchita
#  5) PUT /preferenza senza Idempotency-Key → 400 E_IDEMPOTENCY_KEY_REQUIRED
#  6) PUT /preferenza con Idempotency-Key → 200, salva
#  7) GET /config dopo PUT → contiene la preferenza salvata (verifica round-trip)
#  8) PUT /preferenza con chiave extra → 400 E_UI_PREFERENZA_VALIDAZIONE
#  9) DELETE /preferenza → 200 deleted=true; DELETE idempotente → 200 deleted=false
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_errori.sh"   # smoke_check_codice
LISTA_CODICE="${SMOKE_LISTA_CODICE:-anagrafiche.clienti}"

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
    if isinstance(d, (dict, list)):
        print(json.dumps(d, ensure_ascii=False))
    else:
        print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}" extra_header="${4:-}"
    if [[ "$method" == "GET" || "$method" == "DELETE" ]]; then
        if [[ -n "$extra_header" ]]; then
            curl -s -w '\n%{http_code}' \
                -X "$method" \
                -H "Authorization: Bearer ${TOKEN:-none}" \
                -H "$extra_header" \
                "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
        else
            curl -s -w '\n%{http_code}' \
                -X "$method" \
                -H "Authorization: Bearer ${TOKEN:-none}" \
                "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
        fi
    else
        if [[ -n "$extra_header" ]]; then
            curl -s -w '\n%{http_code}' \
                -X "$method" \
                -H "Authorization: Bearer ${TOKEN:-none}" \
                -H "Content-Type: application/json" \
                -H "$extra_header" \
                -d "$data" \
                "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
        else
            curl -s -w '\n%{http_code}' \
                -X "$method" \
                -H "Authorization: Bearer ${TOKEN:-none}" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
        fi
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

# Generate UUIDv4-like string for Idempotency-Key. python3 uuid e' robusto.
gen_uuid() {
    python3 -c "import uuid; print(uuid.uuid4())"
}

# ================================================================
echo ""
echo "========================================="
echo " Smoke test UI personalizzazioni liste"
echo " Base URL:      $BASE_URL"
echo " Lista codice:  $LISTA_CODICE"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Token JWT ottenuto"

# --- 1. Cleanup proattivo ---
# Memoria progetto: smoke test idempotenti devono ripulire residui
# di run precedenti prima di iniziare. DELETE su preferenza assente
# torna deleted=false (200), niente errore.
echo ""
echo "-- 1. Cleanup proattivo (DELETE preferenza eventuale) --"
do_curl DELETE "/api/v1/ui/liste/$LISTA_CODICE/preferenza/"
if [[ "$LAST_STATUS" == "200" ]]; then
    deleted_pre=$(json_get "$LAST_BODY" ".data.deleted")
    log_info "Cleanup eseguito (deleted=$deleted_pre)"
else
    log_fail "Cleanup proattivo — HTTP $LAST_STATUS atteso 200"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 2. GET /config su codice valido ---
echo ""
echo "-- 2. GET /config (cascata BE) --"
do_curl GET "/api/v1/ui/liste/$LISTA_CODICE/config/"
check "GET config $LISTA_CODICE" "200" ".data"
COLONNE_COUNT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('data',{}).get('colonne') or []))" 2>/dev/null || echo "0")
log_info "Colonne risolte (visibili): $COLONNE_COUNT"
PAGE_DIM=$(json_get "$LAST_BODY" ".data.pagina_dimensione")
log_info "pagina_dimensione: $PAGE_DIM"
COLONNE_NUOVE=$(json_get "$LAST_BODY" ".data.colonne_nuove")
log_info "colonne_nuove: $COLONNE_NUOVE"
if [[ "$COLONNE_COUNT" == "0" ]]; then
    log_fail "GET config: 0 colonne risolte — verificare seed Blocco E2"
fi

# --- 3. GET /config con codice inesistente ---
echo ""
echo "-- 3. GET /config con codice inesistente --"
do_curl GET "/api/v1/ui/liste/non.esiste.smoke/config/"
smoke_check_codice "GET config codice fittizio" 404 E_UI_LISTA_NON_TROVATA

# --- 4. GET /catalogo ---
echo ""
echo "-- 4. GET /catalogo (per modale personalizzazione) --"
do_curl GET "/api/v1/ui/liste/$LISTA_CODICE/catalogo/"
check "GET catalogo $LISTA_CODICE" "200" ".data.colonne"
CATALOGO_COUNT=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('data',{}).get('colonne') or []))" 2>/dev/null || echo "0")
log_info "Colonne catalogo (filtrate per permessi): $CATALOGO_COUNT"
# Estrai il primo codice colonna utile per il PUT successivo
FIRST_COLONNA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
cols = d.get('data',{}).get('colonne') or []
print(cols[0]['codice'] if cols else '')" 2>/dev/null || echo "")
log_info "Prima colonna catalogo: $FIRST_COLONNA"

# --- 5. PUT /preferenza senza Idempotency-Key ---
echo ""
echo "-- 5. PUT /preferenza senza Idempotency-Key (atteso 400) --"
do_curl PUT "/api/v1/ui/liste/$LISTA_CODICE/preferenza/" '{"colonne":[]}'
check "PUT senza Idempotency-Key" "400"
ERR_CODE=$(json_get "$LAST_BODY" ".error.code")
log_info "error.code: $ERR_CODE"

# --- 6. PUT /preferenza con Idempotency-Key ---
echo ""
echo "-- 6. PUT /preferenza con Idempotency-Key --"
IDEM_KEY=$(gen_uuid)
log_info "Idempotency-Key: $IDEM_KEY"
PREF_BODY="{\"colonne\":[{\"codice\":\"$FIRST_COLONNA\",\"ordine\":1,\"visibile\":true}],\"pagina_dimensione\":50}"
do_curl PUT "/api/v1/ui/liste/$LISTA_CODICE/preferenza/" "$PREF_BODY" "Idempotency-Key: $IDEM_KEY"
check "PUT preferenza valida" "200" ".data.id"
PREF_ID="$EXTRACTED"
log_info "ID preferenza salvata: $PREF_ID"

# --- 7. GET /config dopo PUT ---
echo ""
echo "-- 7. GET /config dopo salvataggio (verifica round-trip) --"
do_curl GET "/api/v1/ui/liste/$LISTA_CODICE/config/"
check "GET config post PUT" "200" ".data.pagina_dimensione"
NEW_PAGE_DIM="$EXTRACTED"
if [[ "$NEW_PAGE_DIM" == "50" ]]; then
    log_ok "pagina_dimensione persistita correttamente: $NEW_PAGE_DIM"
else
    log_fail "pagina_dimensione attesa 50, trovata: $NEW_PAGE_DIM"
fi

# --- 8. PUT /preferenza con chiave extra ---
echo ""
echo "-- 8. PUT /preferenza con chiave non whitelisted (atteso 400) --"
IDEM_KEY=$(gen_uuid)
do_curl PUT "/api/v1/ui/liste/$LISTA_CODICE/preferenza/" \
    '{"colonne":[],"chiave_maliziosa":"<script>"}' "Idempotency-Key: $IDEM_KEY"
smoke_check_codice "PUT preferenza con chiave extra" 400 E_UI_PREFERENZA_VALIDAZIONE

# --- 9. DELETE /preferenza + idempotenza ---
echo ""
echo "-- 9. DELETE /preferenza + verifica idempotenza --"
do_curl DELETE "/api/v1/ui/liste/$LISTA_CODICE/preferenza/"
check "DELETE preferenza esistente" "200" ".data.deleted"
DELETED1="$EXTRACTED"
if [[ "$DELETED1" == "True" || "$DELETED1" == "true" ]]; then
    log_ok "deleted=true sulla preferenza salvata in step 6"
else
    log_fail "Atteso deleted=true, ricevuto: $DELETED1"
fi

# Seconda DELETE: idempotente, deleted=false
do_curl DELETE "/api/v1/ui/liste/$LISTA_CODICE/preferenza/"
check "DELETE preferenza inesistente (idempotente)" "200" ".data.deleted"
DELETED2="$EXTRACTED"
if [[ "$DELETED2" == "False" || "$DELETED2" == "false" ]]; then
    log_ok "deleted=false sulla seconda DELETE (idempotenza)"
else
    log_fail "Atteso deleted=false, ricevuto: $DELETED2"
fi

# ================================================================
echo ""
echo "========================================="
echo " Riepilogo: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}"
echo "========================================="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
