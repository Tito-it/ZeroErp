#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Tracciamento (audit log, task registry, job runs)
# Uso: ./scripts/smoke-test-tracciamento.sh [password]
# ------------------------------------------------------------
# Indice test (0..14):
#  0) Autenticazione JWT
#  1) Audit log — lista completa
#  2) Audit log — filtro status SUCCESS / FAILED
#  3) Audit log — paginazione (limit=5)
#  4) Audit log — search ILIKE
#  5) Domini task — lista con dettaglio
#  6) Task registry — lista completa
#  7) Task registry — filtro dominio FATTURAZIONE
#  8) Task implementations — lista con dettaglio handler
#  9) Job runs — lista completa
# 10) Job runs — filtro ok=true / ok=false
# 11) Job runs — search ILIKE
# 12) Job summary — riepilogo con dettaglio
# 13) Validazione — status invalido (400), limit oltre il massimo (400)
# 14) Accesso senza token valido (401)
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
        d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2"
    # Pausa tra chiamate per evitare SearchBurstRateThrottle
    sleep 0.5
    curl -s -w '\n%{http_code}' \
        -H "Authorization: Bearer ${TOKEN:-none}" \
        "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
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
echo " Smoke test API Tracciamento"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "JWT ottenuto per '$USERNAME'"

# ================================================================
# AUDIT LOG
# ================================================================
echo ""
echo "-- 1. Audit log (lista) --"

do_curl GET "/api/v1/core/tracciamento/audit-log/"
check "GET audit-log" 200 ".data.count"
log_info "audit log totali: $EXTRACTED"

# Con filtro status
echo ""
echo "-- 2. Audit log filtro status=SUCCESS --"

do_curl GET "/api/v1/core/tracciamento/audit-log/?status=SUCCESS"
check "GET audit-log status=SUCCESS" 200 ".data.count"
log_info "audit SUCCESS: $EXTRACTED"

# Con filtro status FAILED
do_curl GET "/api/v1/core/tracciamento/audit-log/?status=FAILED"
check "GET audit-log status=FAILED" 200 ".data.count"
log_info "audit FAILED: $EXTRACTED"

# Con paginazione
echo ""
echo "-- 3. Audit log paginazione --"

do_curl GET "/api/v1/core/tracciamento/audit-log/?limit=5"
check "GET audit-log limit=5" 200 ".data.page_size"
log_info "page_size restituito: $EXTRACTED"

# Con ricerca
echo ""
echo "-- 4. Audit log search --"

do_curl GET "/api/v1/core/tracciamento/audit-log/?search=fn_"
check "GET audit-log search='fn_'" 200 ".data.count"
log_info "risultati search 'fn_': $EXTRACTED"

# ================================================================
# DOMINI TASK
# ================================================================
echo ""
echo "-- 5. Domini task --"

do_curl GET "/api/v1/core/tracciamento/domini-task/"
check "GET domini-task" 200 ".data.count"
log_info "domini task: $EXTRACTED"

# Mostra dettaglio domini
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d['data']['results']
    for r in results[:10]:
        codice = r.get('codice','?')
        desc = r.get('descrizione','?')
        attivo = r.get('attivo', '?')
        print(f'      {codice}: {desc} (attivo={attivo})')
except Exception as e:
    print(f'      (errore parsing: {e})')
" 2>/dev/null

# ================================================================
# TASK REGISTRY
# ================================================================
echo ""
sleep 1
echo "-- 6. Task registry (tutti) --"

do_curl GET "/api/v1/core/tracciamento/task-registry/"
check "GET task-registry" 200 ".data.count"
log_info "task registrati: $EXTRACTED"

# Con filtro dominio
echo ""
echo "-- 7. Task registry filtro dominio --"

do_curl GET "/api/v1/core/tracciamento/task-registry/?dominio=FATTURAZIONE"
check "GET task-registry dominio=FATTURAZIONE" 200 ".data.count"
log_info "task FATTURAZIONE: $EXTRACTED"

# ================================================================
# TASK IMPLEMENTATIONS
# ================================================================
echo ""
sleep 1
echo "-- 8. Task implementations --"

do_curl GET "/api/v1/core/tracciamento/task-implementations/"
check "GET task-implementations" 200 ".data.count"
log_info "implementazioni: $EXTRACTED"

# Mostra dettaglio implementazioni
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d['data']['results']
    for r in results[:10]:
        tc = r.get('task_code','?')
        ik = r.get('implementation_key','?')
        hc = r.get('handler_code','?')
        default = r.get('is_default', False)
        print(f'      {tc}/{ik}: handler={hc} default={default}')
except Exception as e:
    print(f'      (errore parsing: {e})')
" 2>/dev/null

# ================================================================
# JOB RUNS
# ================================================================
echo ""
echo "-- 9. Job runs --"

do_curl GET "/api/v1/core/tracciamento/job-runs/"
check "GET job-runs" 200 ".data.count"
log_info "job runs totali: $EXTRACTED"

# Con filtro ok=true
echo ""
echo "-- 10. Job runs filtro ok=true --"

do_curl GET "/api/v1/core/tracciamento/job-runs/?ok=true"
check "GET job-runs ok=true" 200 ".data.count"
log_info "job runs OK: $EXTRACTED"

# Con filtro ok=false (pausa per evitare throttle burst)
sleep 2
do_curl GET "/api/v1/core/tracciamento/job-runs/?ok=false"
check "GET job-runs ok=false" 200 ".data.count"
log_info "job runs FAIL: $EXTRACTED"

# Con search
echo ""
sleep 1
echo "-- 11. Job runs search --"

do_curl GET "/api/v1/core/tracciamento/job-runs/?search=maintenance"
check "GET job-runs search='maintenance'" 200 ".data.count"
log_info "risultati search 'maintenance': $EXTRACTED"

# ================================================================
# JOB SUMMARY
# ================================================================
echo ""
echo "-- 12. Job summary --"

do_curl GET "/api/v1/core/tracciamento/job-summary/"
check "GET job-summary" 200 ".data.count"
log_info "job distinti: $EXTRACTED"

# Mostra dettaglio summary
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d['data']['results']
    for r in results[:10]:
        jn = r.get('jobname','?')
        total = r.get('total_runs', 0)
        ok = r.get('ok_count', 0)
        fail = r.get('fail_count', 0)
        last = r.get('last_run_at','?')
        print(f'      {jn}: total={total} ok={ok} fail={fail} last={last}')
except Exception as e:
    print(f'      (errore parsing: {e})')
" 2>/dev/null

# ================================================================
# TEST ERRORI
# ================================================================
echo ""
sleep 1
echo "-- 13. Test errori validazione --"

# Audit log con status invalido → errore di validazione atteso (400)
do_curl GET "/api/v1/core/tracciamento/audit-log/?status=INVALIDO"
check "GET audit-log status=INVALIDO → 400" 400

# Un limit oltre il massimo (200) e' un 400 dal 2026-10-21, non una riduzione muta
do_curl GET "/api/v1/core/tracciamento/audit-log/?limit=500"
check "GET audit-log limit=500 → 400" 400

# ================================================================
# SENZA TOKEN (401 atteso)
# ================================================================
echo ""
echo "-- 14. Accesso senza token --"

OLD_TOKEN="$TOKEN"
TOKEN="invalid-token-test"
do_curl GET "/api/v1/core/tracciamento/audit-log/"
if [[ "$LAST_STATUS" == "401" ]]; then
    log_ok "GET audit-log senza token valido → 401"
else
    log_fail "GET audit-log senza token — atteso 401, ricevuto $LAST_STATUS"
fi
TOKEN="$OLD_TOKEN"

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
