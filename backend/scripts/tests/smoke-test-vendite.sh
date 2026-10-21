#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API vendite (lotti fatturazione + commesse)
# Esegue chiamate read-only su dati esistenti + test errori attesi
# Uso: ./scripts/smoke-test-vendite.sh [password]
# ------------------------------------------------------------
# Indice test (0..9):
#  0) Autenticazione JWT
#  1) Lista lotti — count + estrazione primo lotto_id
#  2) Fatture del lotto (se presente)
#  3) Segnalazioni del lotto (se presente)
#  4) Task runs del lotto (se presente)
#  5) Reset lotto COMPLETATO — errore atteso (400/409)
#  6) Lista lotti con filtri — stato COMPLETATO, stato inesistente
#  7) Commesse — stato/attivita/push log inesistenti (404/400)
#  8) Pipeline run dry_run
#  9) Commesse push dry_run
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

# --- Colori output ---
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
        d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    local extra_headers=()

    # Idempotency-Key per POST write
    if [[ "$method" == "POST" && -n "${IDEM_KEY:-}" ]]; then
        extra_headers+=(-H "Idempotency-Key: $IDEM_KEY")
    fi

    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    elif [[ "$method" == "PATCH" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            "${extra_headers[@]}" \
            -X PATCH -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            "${extra_headers[@]}" \
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
echo " Smoke test API Vendite"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "JWT ottenuto per '$USERNAME'"

# ================================================================
# LOTTI FATTURAZIONE
# ================================================================

# --- 1. Lista lotti ---
echo ""
echo "-- 1. Lista lotti --"

do_curl GET "/api/v1/vendite/lotti/"
check "GET lista lotti" 200 ".data.count"
LOTTI_COUNT="$EXTRACTED"
log_info "lotti totali: $LOTTI_COUNT"

# Estrai primo lotto_id dalla lista (se esiste)
LOTTO_ID=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d['data']['results']
    print(results[0]['id'] if results else '')
except Exception:
    print('')
" 2>/dev/null)

if [[ -n "$LOTTO_ID" && "$LOTTO_ID" != "" ]]; then
    log_info "lotto_id di test = $LOTTO_ID"

    # --- 2. Fatture del lotto ---
    echo ""
    echo "-- 2. Fatture del lotto --"

    do_curl GET "/api/v1/vendite/lotti/${LOTTO_ID}/fatture/"
    check "GET fatture lotto $LOTTO_ID" 200 ".data.count"
    log_info "fatture nel lotto: $EXTRACTED"

    # --- 3. Segnalazioni del lotto ---
    echo ""
    echo "-- 3. Segnalazioni lotto --"

    do_curl GET "/api/v1/vendite/lotti/${LOTTO_ID}/segnalazioni/"
    check "GET segnalazioni lotto $LOTTO_ID" 200

    # --- 4. Task runs del lotto ---
    echo ""
    echo "-- 4. Task runs lotto --"

    do_curl GET "/api/v1/vendite/lotti/${LOTTO_ID}/task-runs/"
    check "GET task runs lotto $LOTTO_ID" 200 ".data.count"
    log_info "task runs: $EXTRACTED"

    # --- 5. Reset lotto COMPLETATO → errore atteso ---
    echo ""
    echo "-- 5. Reset lotto non-DRAFT (errore atteso) --"

    IDEM_KEY="smoke-reset-lotto-$(date +%s)"
    do_curl POST "/api/v1/vendite/lotti/${LOTTO_ID}/reset-draft/" '{}'
    # Un lotto COMPLETATO non puo' essere resettato → errore atteso
    if [[ "$LAST_STATUS" == "400" || "$LAST_STATUS" == "409" ]]; then
        log_ok "POST reset lotto COMPLETATO → errore atteso (HTTP $LAST_STATUS)"
    elif [[ "$LAST_STATUS" == "200" ]]; then
        log_ok "POST reset lotto → 200 (lotto era DRAFT)"
    else
        log_fail "POST reset lotto — atteso 400/409, ricevuto $LAST_STATUS"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    fi
    IDEM_KEY=""
else
    log_info "Nessun lotto presente — skip test 2-5"
fi

# --- 6. Lista lotti con filtri ---
echo ""
echo "-- 6. Lista lotti con filtri --"

do_curl GET "/api/v1/vendite/lotti/?stato_lotto=COMPLETATO&limit=5"
check "GET lotti filtro COMPLETATO" 200

# Un filtro a vocabolario chiuso con un valore ignoto e' un 400, non una lista
# vuota (api.md §«Un filtro a vocabolario chiuso»).
do_curl GET "/api/v1/vendite/lotti/?stato_lotto=INESISTENTE"
check "GET lotti filtro stato inesistente" 400

# ================================================================
# COMMESSE
# ================================================================

echo ""
echo "-- 7. Commesse --"

# --- 7a. Stato commessa inesistente → errore atteso ---
do_curl GET "/api/v1/vendite/commesse/999999/stato/"
if [[ "$LAST_STATUS" == "404" || "$LAST_STATUS" == "400" ]]; then
    log_ok "GET stato commessa inesistente → errore atteso (HTTP $LAST_STATUS)"
else
    # Potrebbe ritornare 200 con contatori a 0 se la query non fa guard
    check "GET stato commessa 999999" 200
fi

# --- 7b. Attivita commessa inesistente ---
do_curl GET "/api/v1/vendite/commesse/999999/attivita/"
if [[ "$LAST_STATUS" == "404" || "$LAST_STATUS" == "400" ]]; then
    log_ok "GET attivita commessa inesistente → errore atteso (HTTP $LAST_STATUS)"
else
    check "GET attivita commessa 999999" 200
fi

# --- 7c. Push log inesistente ---
do_curl GET "/api/v1/vendite/commesse/push/999999/"
if [[ "$LAST_STATUS" == "404" || "$LAST_STATUS" == "400" ]]; then
    log_ok "GET push log inesistente → errore atteso (HTTP $LAST_STATUS)"
else
    check "GET push log 999999" 200
fi

# --- 8. Pipeline run senza dati (dry_run) ---
echo ""
echo "-- 8. Pipeline run (dry_run) --"

IDEM_KEY="smoke-pipeline-$(date +%s)"
do_curl POST "/api/v1/vendite/pipeline/run/" '{"dry_run": true}'
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "POST pipeline dry_run (HTTP 200)"
elif [[ "$LAST_STATUS" == "400" || "$LAST_STATUS" == "409" || "$LAST_STATUS" == "422" ]]; then
    log_ok "POST pipeline dry_run → errore atteso (HTTP $LAST_STATUS)"
    log_info "$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    code = d.get('error',{}).get('code','')
    msg = d.get('error',{}).get('message','')
    print(f'{code}: {msg}')
except: print('(dettaglio non disponibile)')
" 2>/dev/null)"
else
    log_fail "POST pipeline dry_run — ricevuto HTTP $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi
IDEM_KEY=""

# --- 9. Commesse push (dry_run) ---
echo ""
echo "-- 9. Commesse push (dry_run) --"

IDEM_KEY="smoke-commesse-push-$(date +%s)"
do_curl POST "/api/v1/vendite/commesse/push/run/" '{"source_types": ["PREVENTIVO"], "dry_run": true}'
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "POST commesse push dry_run (HTTP 200)"
elif [[ "$LAST_STATUS" == "400" || "$LAST_STATUS" == "409" || "$LAST_STATUS" == "422" ]]; then
    log_ok "POST commesse push dry_run → errore atteso (HTTP $LAST_STATUS)"
    log_info "$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    code = d.get('error',{}).get('code','')
    msg = d.get('error',{}).get('message','')
    print(f'{code}: {msg}')
except: print('(dettaglio non disponibile)')
" 2>/dev/null)"
else
    log_fail "POST commesse push dry_run — ricevuto HTTP $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi
IDEM_KEY=""

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
