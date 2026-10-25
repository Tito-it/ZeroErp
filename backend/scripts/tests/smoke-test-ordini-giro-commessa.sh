#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Giro ordine di vendita → commessa (passo 6
# analisi-ordini-vendita.md §7: conferma end-to-end + push singolo).
# Uso: ./scripts/tests/smoke-test-ordini-giro-commessa.sh [password]
#
# Copre contro DB+API reali (ciò che gli unit test mockano):
# creazione ordine BOZZA (numero già valorizzato dal trigger, §8.1),
# guard push pre-conferma, conferma da /emetti/ (BOZZA→CONFERMATO), push singolo a
# commessa (pr_run_commesse_push_one ORDINE_VENDITA), stato dell'ordine
# INVARIATO dall'invio (D-6), idempotenza re-push (nessuna riga da mandare),
# consultazione push log; poi il ritorno: annullo della commessa con la
# conferma dei legami, l'ordine resta CONFERMATO e torna da mandare.
#
# ⭐ D-6 di brief-db-annullo-a-valle-riapre-a-monte (2026-10-12): «Evaso»
# vuol dire «la merce e' partita», e lo dicono solo le bolle. Fino a quel
# giorno il passo 7 si aspettava EVASO dopo l'invio in commessa: era il
# difetto (un ordine PARZIALMENTE_EVASO mandato in commessa diventava EVASO).
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
#  5) Conferma (BOZZA → CONFERMATO) da /emetti/ (multipart)
#  6) Push singolo → COMPLETATO (created >= 1, commesse_ids esposti)
#  7) Detail → stato CONFERMATO (l'invio in commessa non lo cambia, D-6)
#  8) Commessa emittibile: stato PRONTA_FATTURAZIONE + approvate >= 1
#  9) Re-push → 4xx (le righe sono gia' in commessa: niente da mandare)
# 10) GET push log (consultazione operativa)
# 11) Annullo commessa senza conferma → 409 E_DOC_ANNULLO_CON_LEGAMI
# 12) GET legami della commessa → >= 1, origine ORDINE_VENDITA verso l'ordine
# 13) Annullo con la conferma (legami_confermati) → ANNULLATA
# 14) Ordine: stato CONFERMATO, e di nuovo da mandare (re-push COMPLETATO)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_articolo_merce, smoke_emetti

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

# Scopo: POST con Idempotency-Key (le scritture che la vogliono, es. lo
#        stato della commessa).
do_post_idem() {
    local url="$1" data="$2"
    curl -s -w '\n%{http_code}' -X POST \
        -H "Authorization: Bearer ${TOKEN:-none}" \
        -H "Content-Type: application/json" \
        -H "Idempotency-Key: smoke-$(python3 -c 'import uuid; print(uuid.uuid4())')" \
        -d "$data" "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
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
smoke_cliente_dal_lookup   # BB _smoke_cliente.sh: BA_ID, UTILITY_ID, ISTANZA_ID

if [[ -z "$BA_ID" || -z "$UTILITY_ID" ]]; then
    log_info "lookup BA vuoto/scope; provo a riusare un ordine esistente"
    PAIR=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/ordini/?limit=1" 2>/dev/null | python3 -c "
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

smoke_articolo_merce   # BB _smoke_documenti.sh: una MERCE (va in un ordine/bolla)
if [[ -z "$ARTICOLO_ID" ]]; then
    echo -e "${RED}Setup fallito: nessun articolo nel catalogo. Stop.${NC}"; exit 1
fi
log_info "articolo_id = $ARTICOLO_ID"

# --- 2. Crea ordine BOZZA ---
echo ""; echo "-- 2. Crea ordine BOZZA (fatturazione_trigger=CONFERMATO) --"
# trigger CONFERMATO esplicito: e' il ramo che pusha a commessa (gli altri
# trigger SPEDITO/CONSEGNATO passano dal DDT, fuori scope — §7 analisi).
# ⛔ Nessun emittente nel payload: e' quello del cliente. Fino al 2026-10-12
# qui c'era un id cablato (32), che con un cliente di un'altra azienda
# risponde E_DOC_EMITTENTE_BA_INCOERENTE. Override solo se serve: EMITTENTE_ID.
EMITTENTE_JSON=""
[[ -n "${EMITTENTE_ID:-}" ]] && EMITTENTE_JSON=", \"emittente_fiscale_id\": ${EMITTENTE_ID}"
do_curl POST "/api/v1/vendite/ordini/" \
    "{\"billing_account_id\": ${BA_ID}${EMITTENTE_JSON}, \"fatturazione_trigger\": \"CONFERMATO\"}"
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
    "{\"articolo_id\": \"$ARTICOLO_ID\", \"descrizione\": \"Riga merce smoke giro commessa\", \"qta_operativa\": \"5\", \"prezzo_unitario\": \"80.00\"}"
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
# ⭐ L'ordine si conferma solo da «Emetti» (numero e PDF nella stessa
#    transazione, M-2): `POST /conferma/` e' ritirato dal 2026-10-25 (Z-2,
#    brief-modello-documento-vendita §9.6).
echo ""; echo "-- 5. Conferma (BOZZA → CONFERMATO, da /emetti/) --"
smoke_emetti ordini "${ORDINE_ID}"   # BB _smoke_documenti.sh
if [[ "$SMOKE_EMETTI_SENZA_MODELLO" == "1" ]]; then
    log_info "Smoke non conclusivo: nessun modello di documento per l'ordine, i passi a valle non girano."
    echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
    [[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
fi
check "POST emetti (conferma)" 200 || true
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

# --- 7. Detail: lo stato non cambia (D-6) ---
echo ""; echo "-- 7. Detail post-push (attesa: stato CONFERMATO, l'invio non lo cambia) --"
if [[ "$PUSH_OK" == "1" ]]; then
    do_curl GET "/api/v1/vendite/ordini/${ORDINE_ID}/"
    STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$STATO" == "CONFERMATO" ]] && log_ok "stato = CONFERMATO (D-6: Evaso lo dicono le bolle)" \
        || log_fail "stato atteso CONFERMATO dopo l'invio in commessa, trovato '$STATO'"
else
    log_skip "push non COMPLETATO: salto verifica dello stato"
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
echo ""; echo "-- 9. Re-push (attesa: bloccato, niente da mandare) --"
if [[ "$PUSH_OK" == "1" ]]; then
    do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" '{}'
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "Re-push bloccato (HTTP $LAST_STATUS, code=$CODE)"
    else
        log_fail "Re-push: atteso 4xx (righe gia' in commessa), ricevuto $LAST_STATUS"
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

# --- 11..14. Il ritorno: annullare la commessa riapre l'ordine ---
# brief-db-annullo-a-valle-riapre-a-monte D-1/D-2/D-6: la commessa ha righe
# NON_EMESSA spinte dall'ordine, quindi l'annullo diretto e' una DOMANDA
# (409 confirm_and_retry), la conferma dichiara i legami letti, e l'ordine
# non cambia stato ma torna da mandare.
echo ""; echo "-- 11. Annullo commessa senza conferma (attesa: 409 E_DOC_ANNULLO_CON_LEGAMI) --"
ANNULLO_OK=0
if [[ "$PUSH_OK" == "1" && -n "${COMMESSA_ID:-}" && "$COMMESSA_ID" != "None" ]]; then
    do_post_idem "/api/v1/vendite/commesse/${COMMESSA_ID}/stato/" '{"nuovo_stato": "ANNULLATA"}'
    CODE=$(json_get "$LAST_BODY" "error.code")
    UI=$(json_get "$LAST_BODY" "error.ui_action")
    if [[ "$LAST_STATUS" == "409" && "$CODE" == "E_DOC_ANNULLO_CON_LEGAMI" && "$UI" == "confirm_and_retry" ]]; then
        log_ok "annullo diretto: domanda (409 $CODE, $UI)"
    else
        log_fail "annullo diretto: atteso 409 E_DOC_ANNULLO_CON_LEGAMI, ricevuto $LAST_STATUS code=$CODE"
    fi

    echo ""; echo "-- 12. GET legami della commessa --"
    do_curl GET "/api/v1/vendite/commesse/${COMMESSA_ID}/legami/"
    if check "GET legami commessa" 200 "data.legami"; then
        LEGAMI="$EXTRACTED"
        # ⚠️ Il NOSTRO ordine fra TUTTI i legami, non il primo: la commessa e'
        # trovata o creata per cliente, e raccoglie righe di piu' documenti. Il
        # passo 14 di un giro precedente lascia una commessa aperta (il secondo
        # invio), e questo giro, stesso cliente, la riusa: i legami sono due, e il
        # primo e' dell'ordine di ieri. E' il modello, non un difetto.
        NOSTRI=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    righe = json.load(sys.stdin).get('data', {}).get('righe') or []
    print(sum(1 for r in righe if r.get('origine') == 'ORDINE_VENDITA' and str(r.get('origine_id')) == '$ORDINE_ID'))
except Exception:
    print(0)
" 2>/dev/null)
        if [[ -n "$LEGAMI" && "$LEGAMI" -ge 1 && "${NOSTRI:-0}" -ge 1 ]] 2>/dev/null; then
            log_ok "legami = $LEGAMI, di cui $NOSTRI verso l'ordine $ORDINE_ID"
        else
            log_fail "legami attesi >= 1 verso l'ordine $ORDINE_ID, letti legami=$LEGAMI (nostri: ${NOSTRI:-0})"
        fi

        echo ""; echo "-- 13. Annullo con la conferma (legami_confermati=$LEGAMI) --"
        do_post_idem "/api/v1/vendite/commesse/${COMMESSA_ID}/stato/" \
            "{\"nuovo_stato\": \"ANNULLATA\", \"legami_confermati\": $LEGAMI}"
        if check "POST annullo confermato" 200 "data.stato_a"; then
            [[ "$EXTRACTED" == "ANNULLATA" ]] && { log_ok "commessa ANNULLATA"; ANNULLO_OK=1; } \
                || log_fail "stato_a atteso ANNULLATA, trovato '$EXTRACTED'"
        fi
    fi
else
    log_skip "push non COMPLETATO o commessa assente: salto l'annullo"
fi

echo ""; echo "-- 14. Ordine dopo l'annullo (attesa: CONFERMATO e di nuovo da mandare) --"
if [[ "$ANNULLO_OK" == "1" ]]; then
    do_curl GET "/api/v1/vendite/ordini/${ORDINE_ID}/"
    STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$STATO" == "CONFERMATO" ]] && log_ok "ordine CONFERMATO (D-6: l'annullo non lo cambia)" \
        || log_fail "ordine atteso CONFERMATO, trovato '$STATO'"
    do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" '{}'
    if check "POST re-push dopo l'annullo" 200 "data.stato"; then
        [[ "$EXTRACTED" == "COMPLETATO" ]] && log_ok "ordine di nuovo da mandare: re-push COMPLETATO" \
            || log_fail "re-push: atteso COMPLETATO, trovato '$EXTRACTED'"
    fi
else
    log_skip "annullo non riuscito: salto la verifica dell'ordine"
fi

# --- Nota copertura ---
echo ""
log_info "Fatturazione (pipeline lotto → fattura) fuori scope: la commessa esce"
log_info "emittibile da questo giro; il run lotto e' collaudato a valle."

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
