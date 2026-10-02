#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Giro ordine di vendita → commessa (passo 6
# analisi-ordini-vendita.md §7: conferma end-to-end + push singolo).
# Uso: ./scripts/tests/smoke-test-ordini-giro-commessa.sh [password]
#
# Copre contro DB+API reali (ciò che gli unit test mockano):
# creazione ordine BOZZA (numero già valorizzato dal trigger, §8.1),
# guard push pre-conferma, conferma (BOZZA→CONFERMATO), push singolo a
# commessa (pr_run_commesse_push_one ORDINE_VENDITA), transizione
# automatica CONFERMATO→EVASO a push COMPLETATO, idempotenza re-push
# (E_ORD_STATO_TRANSIZIONE da EVASO), consultazione push log.
#
# Ponte emittibilita` (2026-06-10): il push rende la commessa emittibile
# (righe APPROVATA + testata PRONTA_FATTURAZIONE) ed espone `commesse_ids`
# nella response — verificato al passo 8. La fatturazione vera e propria
# (pipeline lotto → fattura, `POST /vendite/pipeline/run/`) resta fuori
# scope di questo smoke: gia` collaudata a valle delle commesse emittibili.
# ------------------------------------------------------------
# Indice:
#  0) Autenticazione JWT
#  1) Setup: tripla BA+utility coerente + articolo di catalogo
#  2) Crea ordine BOZZA (fatturazione_trigger=CONFERMATO) + verifica numero
#  3) Aggiungi riga merce
#  4) Push su BOZZA → 4xx E_ORD_STATO_TRANSIZIONE (guard pre-conferma)
#  5) Conferma (BOZZA → CONFERMATO)
#  6) Push singolo → COMPLETATO (created >= 1, commesse_ids esposti)
#  7) Detail → stato EVASO (transizione automatica post-push)
#  8) Commessa emittibile: stato PRONTA_FATTURAZIONE + approvate >= 1
#  9) Re-push → 4xx E_ORD_STATO_TRANSIZIONE (idempotenza via stato EVASO)
# 10) GET push log (consultazione operativa)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; SKIP=0
EXTRACTED=""; LAST_STATUS=""; LAST_BODY=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_skip() { ((SKIP++)) || true; echo -e "  ${YELLOW}SKIP${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        d = d[int(k)] if k.isdigit() else d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    fi
    LAST_STATUS=$(tail -1 "$TMPFILE"); LAST_BODY=$(sed '$d' "$TMPFILE")
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
    [[ -n "$json_expr" ]] && EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    return 0
}

# --- 0. Auth ---
echo "== Smoke giro ordine → commessa =="
smoke_login --senza-prompt --uscita 2
log_ok "Autenticazione JWT"

# --- 1. Setup: tripla BA+utility + articolo ---
echo ""; echo "-- 1. Setup tripla BA+utility + articolo --"
# Serve una coppia COERENTE billing_account+utility. Fonte 1: lookup BA
# (espone utility_id). Fonte 2 (fallback): un ordine esistente (coppia già
# coerente per costruzione).
BA_RAW=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/anagrafiche/billing-account/lookup/" 2>/dev/null)
BA_TRIPLE=$(echo "$BA_RAW" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data', {})
    rows = d.get('results', d) if isinstance(d, dict) else d
    for r in (rows or []):
        if r.get('utility_id') and r.get('istanza_utility_id'):
            print(r['id'], r['utility_id']); break
except Exception:
    pass
" 2>/dev/null)
BA_ID=$(echo "$BA_TRIPLE" | awk '{print $1}')
UTILITY_ID=$(echo "$BA_TRIPLE" | awk '{print $2}')

if [[ -z "$BA_ID" || -z "$UTILITY_ID" ]]; then
    log_info "lookup BA vuoto/scope; provo a riusare un ordine esistente"
    PAIR=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/ordini/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    if r and r[0].get('billing_account_id') and r[0].get('utility_id'):
        print(r[0]['billing_account_id'], r[0]['utility_id'])
except Exception:
    pass
" 2>/dev/null)
    BA_ID=$(echo "$PAIR" | awk '{print $1}')
    UTILITY_ID=$(echo "$PAIR" | awk '{print $2}')
fi
if [[ -z "$BA_ID" || -z "$UTILITY_ID" ]]; then
    echo -e "${RED}Setup fallito: nessuna coppia BA+utility disponibile.${NC}"
    log_info "Suggerimento: verifica che l'utente smoke abbia un emittente con almeno un BA valido (utility+istanza)."
    exit 1
fi
log_info "billing_account_id = $BA_ID, utility_id = $UTILITY_ID"

ARTICOLO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(r[0]['id'] if r else '')
except Exception: print('')
" 2>/dev/null)
if [[ -z "$ARTICOLO_ID" ]]; then
    echo -e "${RED}Setup fallito: nessun articolo nel catalogo. Stop.${NC}"; exit 1
fi
log_info "articolo_id = $ARTICOLO_ID"

# --- 2. Crea ordine BOZZA ---
echo ""; echo "-- 2. Crea ordine BOZZA (fatturazione_trigger=CONFERMATO) --"
# trigger CONFERMATO esplicito: e' il ramo che pusha a commessa (gli altri
# trigger SPEDITO/CONSEGNATO passano dal DDT, fuori scope — §7 analisi).
# L'operatore smoke puo' non avere emittente assegnato
# (E_CONTRATTO_EMITTENTE_NON_RISOLTO): inietta un emittente esplicito nel
# payload (default 32, override EMITTENTE_ID).
EMITTENTE_FISCALE_ID="${EMITTENTE_ID:-32}"
do_curl POST "/api/v1/vendite/ordini/" \
    "{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}, \"emittente_fiscale_id\": ${EMITTENTE_FISCALE_ID}, \"fatturazione_trigger\": \"CONFERMATO\"}"
if ! check "POST crea ordine" 200 "data.id"; then
    echo -e "${RED}Setup fallito: impossibile creare ordine. Stop.${NC}"; exit 1
fi
ORDINE_ID="$EXTRACTED"; log_info "ordine_id = $ORDINE_ID"

do_curl GET "/api/v1/vendite/ordini/${ORDINE_ID}/"
check "GET detail ordine" 200 "data.numero" || true
NUMERO="$EXTRACTED"
if [[ -n "$NUMERO" && "$NUMERO" != "None" ]]; then
    log_ok "numero gia' valorizzato in BOZZA = $NUMERO (trigger gen codice, §8.1)"
else
    log_fail "numero atteso valorizzato gia' in BOZZA, trovato vuoto"
fi
STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
[[ "$STATO" == "DRAFT" ]] && log_ok "stato iniziale = DRAFT (bozza)" || log_fail "stato iniziale atteso DRAFT, trovato '$STATO'"

# --- 3. Riga merce ---
echo ""; echo "-- 3. Aggiungi riga merce --"
do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/righe/" \
    "{\"articolo_id\": \"$ARTICOLO_ID\", \"descrizione\": \"Riga merce smoke giro commessa\", \"qta_operativa\": \"5\", \"prezzo_unitario\": \"80.00\", \"iva_id\": 16}"
check "POST aggiungi riga" 200 "data.riga_id" || true
RIGA_ID="$EXTRACTED"; log_info "riga_id = $RIGA_ID"

# --- 4. Push su BOZZA: guard ---
echo ""; echo "-- 4. Push su BOZZA (attesa: bloccato dal guard) --"
do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" '{}'
if [[ "$LAST_STATUS" =~ ^4 ]]; then
    CODE=$(json_get "$LAST_BODY" "error.code")
    log_ok "Push pre-conferma bloccato (HTTP $LAST_STATUS, code=$CODE)"
else
    log_fail "Push su BOZZA: atteso 4xx, ricevuto $LAST_STATUS"
fi

# --- 5. Conferma ---
echo ""; echo "-- 5. Conferma (BOZZA → CONFERMATO) --"
do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/conferma/" '{}'
check "POST conferma" 200 || true
do_curl GET "/api/v1/vendite/ordini/${ORDINE_ID}/"
STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
[[ "$STATO" == "CONFERMATO" ]] && log_ok "stato = CONFERMATO" || log_fail "stato atteso CONFERMATO, trovato '$STATO'"

# --- 6. Push singolo a commessa ---
echo ""; echo "-- 6. Push singolo a commessa --"
do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" '{}'
PUSH_OK=0
if check "POST push" 200 "data.stato"; then
    REPORT_STATO="$EXTRACTED"
    PUSH_LOG_ID=$(json_get "$LAST_BODY" "data.push_log_id")
    CREATED=$(json_get "$LAST_BODY" "data.handlers.0.created")
    COMMESSA_ID=$(json_get "$LAST_BODY" "data.commesse_ids.0")
    log_info "report: stato=$REPORT_STATO, push_log_id=$PUSH_LOG_ID, created=$CREATED, commessa_id=$COMMESSA_ID"
    if [[ "$REPORT_STATO" == "COMPLETATO" ]]; then
        log_ok "push COMPLETATO"
        PUSH_OK=1
    else
        log_fail "push: atteso stato COMPLETATO, trovato '$REPORT_STATO'"
    fi
    if [[ -n "$CREATED" && "$CREATED" -ge 1 ]] 2>/dev/null; then
        log_ok "attivita create = $CREATED (>=1)"
    else
        log_fail "attese >=1 attivita create dal handler, trovate '$CREATED'"
    fi
fi

# --- 7. Detail: EVASO ---
echo ""; echo "-- 7. Detail post-push (attesa: stato EVASO) --"
if [[ "$PUSH_OK" == "1" ]]; then
    do_curl GET "/api/v1/vendite/ordini/${ORDINE_ID}/"
    STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$STATO" == "EVASO" ]] && log_ok "stato = EVASO (transizione automatica)" \
        || log_fail "stato atteso EVASO post-push COMPLETATO, trovato '$STATO'"
else
    log_skip "push non COMPLETATO: salto verifica EVASO"
fi

# --- 8. Commessa emittibile (ponte post-push) ---
echo ""; echo "-- 8. Commessa emittibile (PRONTA_FATTURAZIONE + approvate) --"
if [[ "$PUSH_OK" == "1" && -n "${COMMESSA_ID:-}" && "$COMMESSA_ID" != "None" ]]; then
    do_curl GET "/api/v1/vendite/commesse/${COMMESSA_ID}/stato/"
    if check "GET stato commessa" 200; then
        C_STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
        C_APPROVATE=$(json_get "$LAST_BODY" "data.total_approvate")
        [[ "$C_STATO" == "PRONTA_FATTURAZIONE" ]] \
            && log_ok "commessa $COMMESSA_ID stato = PRONTA_FATTURAZIONE (ponte ok)" \
            || log_fail "commessa attesa PRONTA_FATTURAZIONE, trovata '$C_STATO'"
        if [[ -n "$C_APPROVATE" && "$C_APPROVATE" -ge 1 ]] 2>/dev/null; then
            log_ok "attivita approvate = $C_APPROVATE (>=1)"
        else
            log_fail "attese >=1 attivita approvate, trovate '$C_APPROVATE'"
        fi
    fi
else
    log_skip "push non COMPLETATO o commesse_ids assente: salto verifica emittibilita'"
fi

# --- 9. Re-push: idempotenza ---
echo ""; echo "-- 9. Re-push (attesa: bloccato da EVASO) --"
if [[ "$PUSH_OK" == "1" ]]; then
    do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" '{}'
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "Re-push bloccato (HTTP $LAST_STATUS, code=$CODE)"
    else
        log_fail "Re-push: atteso 4xx (stato EVASO non pushabile), ricevuto $LAST_STATUS"
    fi
else
    log_skip "push non COMPLETATO: salto verifica re-push"
fi

# --- 10. Push log ---
echo ""; echo "-- 10. GET push log --"
if [[ -n "${PUSH_LOG_ID:-}" && "$PUSH_LOG_ID" != "None" ]]; then
    do_curl GET "/api/v1/vendite/commesse/push/${PUSH_LOG_ID}/"
    check "GET push log" 200 || true
else
    log_skip "push_log_id assente: salto consultazione log"
fi

# --- Nota copertura ---
echo ""
log_info "Fatturazione (pipeline lotto → fattura) fuori scope: la commessa esce"
log_info "emittibile da questo giro; il run lotto e' collaudato a valle."

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
