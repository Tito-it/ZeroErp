#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Preventivi vendita
# Uso: ./scripts/tests/smoke-test-preventivi.sh [password]
# Prerequisiti DB: tabelle preventivi, stati_doc_preventivi seed,
#   fn_cambia_stato_preventivo, fn_ricalcola_totali_preventivo
# ------------------------------------------------------------
# Indice test (0..14):
#  0) Autenticazione JWT
#  1) Lista preventivi (GET, paginata)
#  2) Crea preventivo BOZZA
#  3) Dettaglio preventivo creato
#  4) PATCH testata preventivo
#  5) Aggiungi riga (POST)
#  6) Lista righe
#  7) PATCH riga
#  8) Cambio stato BOZZA → EMESSO
#  9) PATCH su EMESSO (409 atteso)
# 10) Cambio stato EMESSO → ACCETTATO
# 11) Smistamento (GET, shape {aggregato, righe})
# 12) Push commessa (POST)
# 13) Lista pratiche collegate (GET)
# 14) DELETE riga (soft delete) — crea nuovo preventivo per test
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_emetti

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
    local extra_headers=""
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
            -H "Idempotency-Key: smoke-$(date +%s%N)" \
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
echo " Smoke test API Preventivi vendita"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Login JWT OK"

# --- 1. Lista preventivi ---
echo ""
echo "-- 1. Lista preventivi --"
do_curl GET "/api/v1/vendite/preventivi/?limit=5"
check "GET lista preventivi" 200

# --- 2. Crea preventivo ---
echo ""
echo "-- 2. Crea preventivo BOZZA --"
# Il preventivo nasce SEMPRE col suo cliente (brief-db-istanza-nasce-col-ba):
# la terna dal BB _smoke_cliente.sh. Fino al 2026-10-12 lo smoke mandava il solo
# `utility_id: 1` cablato (400 «istanza_utility_id obbligatorio»). Nessun
# emittente nel payload: vale quello attivo, lo stesso del cliente.
smoke_cliente_dal_lookup
if [[ -z "$BA_ID" ]]; then
    echo -e "${RED}Setup fallito: nessun cliente dal lookup. Stop.${NC}"; exit 1
fi
do_curl POST "/api/v1/vendite/preventivi/" \
    "{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}, \"istanza_utility_id\": ${ISTANZA_ID}}"
check "POST crea preventivo" 200 "data.id"
PREV_ID="$EXTRACTED"
log_info "preventivo_id = $PREV_ID"

PREV_UID=$(json_get "$LAST_BODY" "data.uid")
log_info "preventivo_uid = $PREV_UID"

# --- 3. Dettaglio ---
echo ""
echo "-- 3. Dettaglio preventivo --"
do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/"
check "GET dettaglio preventivo" 200

STATO=$(json_get "$LAST_BODY" "data.stato_codice")
log_info "stato = $STATO"

# --- 4. PATCH testata ---
echo ""
echo "-- 4. PATCH testata --"
do_curl PATCH "/api/v1/vendite/preventivi/${PREV_ID}/" \
    '{"fatturazione_immediata": true}'
check "PATCH testata preventivo" 200

# --- 5. Aggiungi riga ---
echo ""
echo "-- 5. Aggiungi riga --"
# Serve un articolo_id UUID valido dal catalogo
# Query per trovare il primo articolo attivo
ARTICOLO_ID=$(curl -s \
    -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?limit=1" 2>/dev/null | \
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    r = d.get('data',{}).get('results',[])
    if r: print(r[0]['id'])
    else: print('')
except: print('')
" 2>/dev/null)

if [[ -z "$ARTICOLO_ID" ]]; then
    log_info "Nessun articolo trovato — skip test righe"
else
    log_info "articolo_id = $ARTICOLO_ID"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
        "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"10\", \"prezzo_unitario\": \"100.00\"}"
    check "POST aggiungi riga" 200 "data.id"
    RIGA_ID="$EXTRACTED"
    log_info "riga_id = $RIGA_ID"

    # --- 6. Lista righe ---
    echo ""
    echo "-- 6. Lista righe --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe/"
    check "GET lista righe" 200

    # --- 7. PATCH riga ---
    echo ""
    echo "-- 7. PATCH riga --"
    do_curl PATCH "/api/v1/vendite/preventivi/${PREV_ID}/righe/${RIGA_ID}/" \
        '{"qta_operativa": "20"}'
    check "PATCH riga" 200

    # --- 8. Emissione BOZZA → EMESSO ---
    # Dal BB _smoke_documenti.sh: /emetti/ (multipart, stato + documento). Il
    # cambio di stato diretto verso EMESSO risponde 400 «Usare l'endpoint
    # /emetti/», e fino al 2026-10-12 lo smoke lo usava.
    echo ""
    echo "-- 8. Emissione BOZZA -> EMESSO (/emetti/) --"
    smoke_emetti preventivi "$PREV_ID"
    if [[ "$SMOKE_EMETTI_SENZA_MODELLO" == "1" ]]; then
        log_info "$(json_get "$LAST_BODY" ".error.detail")"
        echo ""
        echo "Smoke non conclusivo: nessun modello di documento per i preventivi dell'emittente"
        echo "attivo (Configurazione → modelli documento). Passi 8 e seguenti non eseguiti."
        echo " Risultato: ${PASS} OK / ${FAIL} FAIL (interrotto al passo 8)"
        [[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
    fi
    check "Emissione preventivo (/emetti/)" 200

    # --- 9. PATCH su EMESSO (409 atteso) ---
    # Fuori bozza l'identita' della testata non cambia (BB
    # vendite.trgfn_doc_testata_lock_fuori_bozza, E_DOC_IDENTITA_FUORI_BOZZA): si
    # prova la valuta, cambiandola con un'altra valuta VERA (lookup), cosi' il
    # rifiuto e' il blocco e non una chiave sbagliata. ⚠️ Fino al 2026-10-12 il
    # passo provava `fatturazione_immediata`, che dal D-14 di
    # brief-db-annullo-a-valle-riapre-a-monte si blocca solo con una commessa
    # aperta: su un preventivo appena emesso la modifica e' giusto che passi.
    echo ""
    echo "-- 9. PATCH su EMESSO (409 atteso) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/"
    VALUTA_ATTUALE=$(json_get "$LAST_BODY" "data.valuta_id")
    do_curl GET "/api/v1/core/lookup/codici/?rel=config.valute&limit=20"
    ALTRA_VALUTA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    print(next((r['id'] for r in rows if str(r['id']) != sys.argv[1]), ''))
except Exception:
    print('')
" "$VALUTA_ATTUALE" 2>/dev/null)
    do_curl PATCH "/api/v1/vendite/preventivi/${PREV_ID}/" \
        "{\"valuta_id\": ${ALTRA_VALUTA:-0}}"
    check "PATCH valuta su EMESSO bloccata" 409
    ERR_CODE=$(json_get "$LAST_BODY" "error.code")
    [[ "$ERR_CODE" == "E_DOC_IDENTITA_FUORI_BOZZA" ]] && log_ok "codice E_DOC_IDENTITA_FUORI_BOZZA" \
        || log_fail "codice atteso E_DOC_IDENTITA_FUORI_BOZZA, ricevuto '${ERR_CODE:-<vuoto>}'"

    # --- 10. Cambio stato EMESSO → ACCETTATO ---
    echo ""
    echo "-- 10. Cambio stato EMESSO -> ACCETTATO --"
    # Accettare vuol dire anche scegliere la modalita' di fatturazione
    # (fatturazione_immediata obbligatorio; con false serve competenza_mese).
    # Fino al 2026-10-12 lo smoke non la passava (400 E_PREV_VALIDAZIONE).
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/stato/" \
        '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
    check "POST cambio stato ACCETTATO" 200

    # --- 11. Smistamento (sostituisce /stato-fatturazione/, 2026-06-12:
    #         risposta annidata {aggregato, righe} dalle viste
    #         vw_preventivi_smistamento + _righe) ---
    echo ""
    echo "-- 11. Smistamento --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/smistamento/"
    check "GET smistamento" 200
    if echo "$LAST_BODY" | grep -q '"aggregato"' && echo "$LAST_BODY" | grep -q '"righe"'; then
        log_ok "GET smistamento: shape {aggregato, righe}"
    else
        log_fail "GET smistamento — attesi campi aggregato+righe, body: $(echo "$LAST_BODY" | head -c 200)"
    fi

    # --- 12. Push commessa ---
    echo ""
    echo "-- 12. Push commessa --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/push-commessa/" '{}'
    # Puo' essere 200 o 400 (E_PREV_NESSUNA_RIGA se fn_list_preventivi_da_pushare non trova righe)
    if [[ "$LAST_STATUS" == "200" || "$LAST_STATUS" == "400" ]]; then
        log_ok "POST push commessa (HTTP $LAST_STATUS)"
    else
        log_fail "POST push commessa — atteso 200 o 400, ricevuto $LAST_STATUS"
    fi

    # --- 13. (ritirato) Pratiche collegate ---
    # La rotta `preventivi/<id>/pratiche/` e' stata ritirata il 2026-07-16
    # (commit bbf0c9ebd6): il passo provava un endpoint che non c'e' piu'.
fi

# --- 14. DELETE riga (crea nuovo preventivo per test soft delete) ---
echo ""
echo "-- 14. Soft delete riga --"
do_curl POST "/api/v1/vendite/preventivi/" '{"utility_id": 1}'
if [[ "$LAST_STATUS" == "200" ]]; then
    PREV2_ID=$(json_get "$LAST_BODY" "data.id")
    if [[ -n "$ARTICOLO_ID" && -n "$PREV2_ID" ]]; then
        do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/righe/" \
            "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"5\", \"prezzo_unitario\": \"50.00\"}"
        RIGA2_ID=$(json_get "$LAST_BODY" "data.id")
        if [[ -n "$RIGA2_ID" ]]; then
            do_curl DELETE "/api/v1/vendite/preventivi/${PREV2_ID}/righe/${RIGA2_ID}/"
            check "DELETE riga soft delete" 200
        else
            log_info "Skip delete riga — creazione riga fallita"
        fi
    else
        log_info "Skip delete riga — articolo non disponibile"
    fi
else
    log_info "Skip delete riga — creazione preventivo fallita"
fi

# --- Riepilogo ---
echo ""
echo "========================================="
TOTAL=$((PASS + FAIL))
echo -e " Risultato: ${GREEN}$PASS${NC} OK / ${RED}$FAIL${NC} FAIL / $TOTAL totali"
echo "========================================="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
