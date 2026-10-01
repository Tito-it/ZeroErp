#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API AI Assistant
# Testa l'endpoint /api/v1/ai-assistant/query/ con provider mock.
# Prerequisito: Django in esecuzione con AI_ENABLED=1 AI_PROVIDER=mock
# Uso: ./scripts/tests/smoke-test-ai-assistant.sh [password]
# ------------------------------------------------------------
# Indice test (0..5):
#  0) Autenticazione JWT
#  1) Query AI con provider mock — risposta con envelope
#  2) Query AI messaggio vuoto — errore 400
#  3) Query AI messaggio troppo lungo — errore 400
#  4) Query AI con conversation_id — riuso conversazione
#  5) Conteggio risultati
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Gunicorn diretto in HTTP: ci si dichiara HTTPS come Nginx (redirect di Django).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

# --- Colori output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
LAST_STATUS=""
LAST_BODY=""
CONVERSATION_ID=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }

do_post() {
  local url="$1"
  local data="$2"
  local auth="${3:-}"
  local auth_header=""
  [[ -n "$auth" ]] && auth_header="Authorization: Bearer $auth"
  LAST_STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    ${auth_header:+-H "$auth_header"} \
    -d "$data")
  LAST_BODY=$(cat "$TMPFILE")
}

extract() {
  echo "$LAST_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo ""
}

echo ""
echo "=========================================="
echo "  Smoke test AI Assistant"
echo "  $BASE_URL"
echo "=========================================="

# --- 0) Autenticazione JWT ---
echo ""
echo "--- 0) Autenticazione ---"
if [[ -z "$PASSWORD" ]]; then
  echo -e "  ${RED}SKIP${NC} PASSWORD non fornita. Uso: $0 <password>"
  exit 1
fi

do_post "$BASE_URL/api/v1/admin/token/" \
  "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}"
if [[ "$LAST_STATUS" == "200" ]]; then
  TOKEN=$(extract "['access']")
  log_ok "Login OK — token ottenuto"
else
  log_fail "Login fallito (HTTP $LAST_STATUS)"
  echo "$LAST_BODY"
  exit 1
fi

# --- 1) Query AI con provider mock ---
echo ""
echo "--- 1) Query AI (provider mock) ---"
do_post "$BASE_URL/api/v1/ai-assistant/query/" \
  '{"message":"mostrami le pratiche aperte"}' \
  "$TOKEN"
if [[ "$LAST_STATUS" == "200" ]]; then
  RESPONSE=$(extract "['data']['response']")
  CONVERSATION_ID=$(extract "['data']['conversation_id']")
  if [[ -n "$RESPONSE" && -n "$CONVERSATION_ID" ]]; then
    log_ok "Query OK — response: ${RESPONSE:0:50}..."
  else
    log_fail "Query OK ma campi mancanti nella risposta"
    echo "$LAST_BODY"
  fi
else
  log_fail "Query fallita (HTTP $LAST_STATUS)"
  echo "$LAST_BODY"
fi

# --- 2) Query messaggio vuoto ---
echo ""
echo "--- 2) Query messaggio vuoto ---"
do_post "$BASE_URL/api/v1/ai-assistant/query/" \
  '{"message":""}' \
  "$TOKEN"
if [[ "$LAST_STATUS" == "400" ]]; then
  ERROR_CODE=$(extract "['error']['code']")
  if [[ "$ERROR_CODE" == "E_AI_QUERY_EMPTY" ]]; then
    log_ok "Messaggio vuoto → errore 400 E_AI_QUERY_EMPTY"
  else
    log_fail "Errore 400 ma codice inatteso: $ERROR_CODE"
  fi
else
  log_fail "Atteso 400, ricevuto $LAST_STATUS"
fi

# --- 3) Query messaggio troppo lungo ---
echo ""
echo "--- 3) Query messaggio troppo lungo ---"
LONG_MSG=$(python3 -c "print('x' * 2001)")
do_post "$BASE_URL/api/v1/ai-assistant/query/" \
  "{\"message\":\"$LONG_MSG\"}" \
  "$TOKEN"
if [[ "$LAST_STATUS" == "400" ]]; then
  ERROR_CODE=$(extract "['error']['code']")
  if [[ "$ERROR_CODE" == "E_AI_QUERY_TOO_LONG" ]]; then
    log_ok "Messaggio lungo → errore 400 E_AI_QUERY_TOO_LONG"
  else
    log_fail "Errore 400 ma codice inatteso: $ERROR_CODE"
  fi
else
  log_fail "Atteso 400, ricevuto $LAST_STATUS"
fi

# --- 4) Query con conversation_id ---
echo ""
echo "--- 4) Riuso conversazione ---"
if [[ -n "$CONVERSATION_ID" ]]; then
  do_post "$BASE_URL/api/v1/ai-assistant/query/" \
    "{\"message\":\"e quelle chiuse?\",\"conversation_id\":\"$CONVERSATION_ID\"}" \
    "$TOKEN"
  if [[ "$LAST_STATUS" == "200" ]]; then
    CONV2=$(extract "['data']['conversation_id']")
    if [[ "$CONV2" == "$CONVERSATION_ID" ]]; then
      log_ok "Conversazione riusata — stesso conversation_id"
    else
      log_fail "conversation_id diverso: atteso $CONVERSATION_ID, ricevuto $CONV2"
    fi
  else
    log_fail "Riuso conversazione fallito (HTTP $LAST_STATUS)"
  fi
else
  log_fail "SKIP — conversation_id non disponibile dal test 1"
fi

# --- 5) Riepilogo ---
echo ""
echo "=========================================="
TOTAL=$((PASS + FAIL))
echo -e "  Risultati: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC} (su $TOTAL)"
echo "=========================================="
echo ""

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
