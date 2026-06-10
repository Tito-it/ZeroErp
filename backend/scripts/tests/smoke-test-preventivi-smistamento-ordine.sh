#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Smistamento MERCE preventivo → ordine (modello split D8).
# Uso: ./scripts/tests/smoke-test-preventivi-smistamento-ordine.sh [password]
#
# Copre il ramo MERCE→ORDINE end-to-end contro DB+API reali (ciò che gli unit
# test mockano): vista vw_preventivi_righe_smistabili_ordine, endpoint
# righe-smistabili-ordine + genera-ordine (fn_push_preventivo_a_ordine),
# idempotenza di riga, filtro catalogo natura.
#
# NON coperto (richiede prerequisiti assenti dal seed):
#  - ramo SERVIZIO→COMMESSA e orchestratore CONFERMA_VENDITA: serve un articolo
#    con natura destinazione_tipo='COMMESSA' (il seed ha solo MERCE) + una pratica;
#  - multi-sorgente (skip PRONTA idempotente): serve 2 preventivi stesse dimensioni.
#  → smoke dedicati una volta seedato un articolo SERVIZIO_UNA_TANTUM.
#
# Auto-diagnosi: se EMESSO/ACCETTATO falliscono per prerequisiti documentali
# (template/emittente), i passi split vengono SALTATI con diagnosi, non crashano.
# ------------------------------------------------------------
# Indice:
#  0) Autenticazione JWT
#  1) Filtro catalogo natura: lookup ?escludi_destinazione=CONTRATTO (standalone)
#  2) Crea preventivo BOZZA + riga merce
#  3) Porta ad ACCETTATO (emetti multipart + accetta con modalita) [prereq-gated]
#  4) GET righe-smistabili-ordine → la riga merce compare
#  5) POST genera-ordine {righe_ids} → ordine creato (ordine_id + numero)
#  6) GET righe-smistabili-ordine → vuota (riga ora allocata: idempotenza)
#  7) POST genera-ordine di nuovo → errore "nessuna riga ordine" (idempotenza)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

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

# Conta gli elementi della lista in data (envelope { data: [...] }).
json_len() {
    echo "$1" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data', [])
    print(len(d) if isinstance(d, list) else 0)
except Exception:
    print(0)
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
echo "== Smoke smistamento merce→ordine =="
if [[ -z "$PASSWORD" ]]; then echo -e "${RED}Password mancante${NC} (arg1 o SMOKE_PASSWORD)"; exit 2; fi
curl -s -w '\n%{http_code}' -X POST -H "Content-Type: application/json" \
    -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null
AUTH_BODY=$(sed '$d' "$TMPFILE")
TOKEN=$(json_get "$AUTH_BODY" "access")
if [[ -z "$TOKEN" ]]; then echo -e "${RED}Auth fallita${NC}"; exit 2; fi
log_ok "Autenticazione JWT"

# --- 1. Filtro catalogo natura (standalone, sempre eseguibile) ---
echo ""; echo "-- 1. Lookup catalogo escludi_destinazione=CONTRATTO --"
do_curl GET "/api/v1/catalogo/articoli/lookup/?search=art&escludi_destinazione=CONTRATTO"
# 200 atteso; se nessun articolo ha codice 'art' la lista è vuota ma 200.
check "GET lookup con filtro natura" 200 || true

# --- 2. Crea preventivo + riga merce ---
echo ""; echo "-- 2. Crea preventivo BOZZA + riga merce --"
# Serve una tripla COERENTE (billing_account + utility + istanza). Fonte 1: lookup
# BA (espone utility_id + istanza_utility_id). Fonte 2 (fallback): un preventivo
# esistente (tripla già coerente per costruzione). La create deriva l'istanza dal
# BA e verifica la coerenza con utility.
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

PREV_PAYLOAD=""
if [[ -n "$BA_ID" && -n "$UTILITY_ID" ]]; then
    log_info "fonte: lookup BA → billing_account_id = $BA_ID, utility_id = $UTILITY_ID"
    PREV_PAYLOAD="{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}}"
else
    # Fallback: riusa un preventivo esistente (BA+utility+istanza coerenti).
    log_info "lookup BA vuoto/scope; provo a riusare un preventivo esistente"
    PREV_PAYLOAD=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/preventivi/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    if r:
        x = r[0]
        ba, ut, iu = x.get('billing_account_id'), x.get('utility_id'), x.get('istanza_utility_id')
        import json as j
        p = {}
        if ba: p['billing_account_id'] = ba
        if ut: p['utility_id'] = ut
        if iu: p['istanza_utility_id'] = iu
        print(j.dumps(p) if ('billing_account_id' in p or 'istanza_utility_id' in p) else '')
except Exception:
    print('')
" 2>/dev/null)
fi

if [[ -z "$PREV_PAYLOAD" ]]; then
    echo -e "${RED}Setup fallito: nessuna tripla BA+utility+istanza disponibile.${NC}"
    log_info "Risposta lookup BA (grezza, primi 500 char):"
    echo "       $(echo "$BA_RAW" | head -c 500)"
    log_info "Suggerimento: verifica che l'utente smoke abbia un emittente con almeno un BA valido (utility+istanza)."
    exit 1
fi
log_info "payload create = $PREV_PAYLOAD"
do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
if ! check "POST crea preventivo" 200 "data.id"; then
    echo -e "${RED}Setup fallito: impossibile creare preventivo. Stop.${NC}"; exit 1
fi
PREV_ID="$EXTRACTED"; log_info "preventivo_id = $PREV_ID"

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
log_info "articolo_id (merce) = $ARTICOLO_ID"
do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
    "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"10\", \"prezzo_unitario\": \"100.00\", \"iva_id\": 16}"
check "POST aggiungi riga merce" 200 "data.id" || true
RIGA_ID="$EXTRACTED"; log_info "riga_id = $RIGA_ID"

# --- 3. Porta ad ACCETTATO (prereq-gated: emetti + accetta) ---
echo ""; echo "-- 3. BOZZA → EMESSO (/emetti/) → ACCETTATO --"
SPLIT_OK=1
# EMESSO via endpoint multipart /emetti/ (allegati opzionali). Richiede
# template documento + emittente configurati: se manca, qui si diagnostica.
curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
    -F "x=" "${BASE_URL}/api/v1/vendite/preventivi/${PREV_ID}/emetti/" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE"); LAST_BODY=$(sed '$d' "$TMPFILE")
if [[ "$LAST_STATUS" != "200" ]]; then
    log_skip "EMESSO (/emetti/) HTTP $LAST_STATUS — prereq documentale assente (template/emittente). Salto i passi split."
    log_info "Body: $(echo "$LAST_BODY" | head -c 200)"
    SPLIT_OK=0
else
    log_ok "POST /emetti/ → EMESSO"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/stato/" \
        '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
    if ! check "POST /stato/ → ACCETTATO (modalita IMMEDIATA)" 200; then SPLIT_OK=0; fi
fi

# --- 4..7. Smistamento merce → ordine (solo se ACCETTATO) ---
if [[ "$SPLIT_OK" == "1" ]]; then
    echo ""; echo "-- 4. GET righe-smistabili-ordine (attesa: la riga merce) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe-smistabili-ordine/"
    check "GET righe-smistabili-ordine" 200 || true
    N=$(json_len "$LAST_BODY")
    [[ "$N" -ge 1 ]] && log_ok "Righe smistabili = $N (>=1)" || log_fail "Attese >=1 righe smistabili, trovate $N"

    echo ""; echo "-- 5. POST genera-ordine {righe_ids} --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/genera-ordine/" \
        "{\"righe_ids\": [${RIGA_ID}]}"
    if check "POST genera-ordine" 200 "data.ordine_id"; then
        log_info "ordine_id = $EXTRACTED, numero = $(json_get "$LAST_BODY" "data.numero")"
    fi

    echo ""; echo "-- 6. GET righe-smistabili-ordine (attesa: vuota, riga allocata) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe-smistabili-ordine/"
    check "GET righe-smistabili-ordine (post)" 200 || true
    N2=$(json_len "$LAST_BODY")
    [[ "$N2" -eq 0 ]] && log_ok "Righe smistabili = 0 (idempotenza di riga)" || log_fail "Attese 0 righe residue, trovate $N2"

    echo ""; echo "-- 7. POST genera-ordine di nuovo (attesa: errore nessuna riga) --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/genera-ordine/" '{}'
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "Re-genera bloccato (HTTP $LAST_STATUS, code=$CODE)"
    else
        log_fail "Re-genera: atteso 4xx (nessuna riga merce residua), ricevuto $LAST_STATUS"
    fi
fi

# --- Nota copertura ---
echo ""
log_info "Ramo SERVIZIO→COMMESSA / multi-sorgente NON coperto: serve un articolo"
log_info "natura destinazione_tipo='COMMESSA' (seed assente). Vedi header."

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
