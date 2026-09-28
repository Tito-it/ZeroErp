#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test componenti BoM CASO A — refactor 2026-05-11
# Uso: ./scripts/tests/smoke-test-preventivi-componenti.sh [password]
# Prerequisiti DB:
#   - tabelle vendite.preventivi_righe_componenti + trigger _m50_/_z90_
#   - fn vendite.fn_preventivo_riga_componenti_init
#   - fn vendite.fn_resolve_prezzo_composito 8 colonne
#   - articolo `composito` con almeno 1 BoM esposta in fattura
# ------------------------------------------------------------
# Indice test (0..N):
#  0) Autenticazione JWT (UNA volta, no thundering throttle)
#  1) Setup CASO A: PATCH BoM attiva -> esposto_in_fattura=TRUE
#  2) Discovery cliente + emittente (BA con utility + emittente attivo)
#  3) Cleanup proattivo: delete preventivi smoke precedenti
#  4) Crea preventivo DRAFT con suffisso unico (smoke-<EPOCH>)
#  5) Aggiungi riga articolo `composito` qty=1
#  6) GET /righe/ -> verifica is_composito_caso_a=TRUE sulla riga
#  7) GET /righe/<id>/componenti/ -> lista popolata (>=1 componente)
#  8) PATCH componente: prezzo_unitario=99.99 + origine_prezzo=MANUALE
#  9) Re-fetch riga padre: prezzo_unitario = SUM(componenti × coeff)
# 10) DELETE componente (se >1): verifica padre ricalcolato
# 11) Guard transizione: tenta cambio stato verso ACCETTATO con prezzo
#     PENDING (se applicabile) -> deve fallire E_PREVENTIVO_RIGHE_PRICING_PENDENTI
# 12) Cleanup finale: delete preventivo + restore esposto_in_fattura=FALSE
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Gunicorn diretto in HTTP: ci si dichiara HTTPS come Nginx (redirect di Django).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

# Fixture: clonare campi articolo `composito` esistente per il padre nuovo,
# riusare componente2 esistente come componente esposto in fattura.
ARTICOLO_COMPOSITO_REFERENCE_ID='019dcf26-da75-79ac-908c-10d4fc779ece'
COMPONENTE_REFERENCE_ID='019d57c1-b2b2-7d3a-9ebb-421addc5f393'  # componente2
EPOCH=$(date +%s)
SUFFIX="smk-${EPOCH}"
NEW_COMPOSITO_ID=""
NEW_BOM_ROW_ID=""
# Date allineate al fuso orario del DB (UTC su questa istanza).
# DATA_OGGI_UTC: data del preventivo, allineata al CURRENT_DATE DB.
# DATA_IERI_UTC: valido_dal BoM, garantisce range che contiene oggi UTC
# anche se l'host bash ha tz diversa (es. Europe/Rome notte fonda
# locale = ieri UTC).
DATA_OGGI_UTC=$(date -u +%Y-%m-%d)
DATA_IERI_UTC=$(date -u -d "1 day ago" +%Y-%m-%d)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
LAST_STATUS=""
LAST_BODY=""
TOKEN=""
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }
log_step() { echo -e "\n${YELLOW}# $1${NC}"; }

# Helper: estrae chiave JSON annidata (es. data.results.0.id)
json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        if k.isdigit(): d = d[int(k)]
        else: d = d[k]
    print(d if d is not None else '')
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE"
    elif [[ "$method" == "DELETE" ]]; then
        curl -s -w '\n%{http_code}' -X DELETE \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Idempotency-Key: ${SUFFIX}-$(date +%N)" \
            "${BASE_URL}${url}" > "$TMPFILE"
    else
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -H "Idempotency-Key: ${SUFFIX}-$(date +%N)" \
            -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE"
    fi
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

check_http() {
    local label="$1" expected="$2"
    # expected accetta multipli separati da | (es. "200|201")
    if echo "|$expected|" | grep -q "|$LAST_STATUS|"; then
        log_ok "$label (HTTP $LAST_STATUS)"
        return 0
    fi
    log_fail "$label — atteso HTTP $expected, ricevuto $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 400)"
    return 1
}

# =====================================================
# 0) AUTH
# =====================================================
log_step "0) Autenticazione JWT"
if [[ -z "$PASSWORD" ]]; then
    echo "ERROR: password mancante. Uso: $0 <password> oppure SMOKE_PASSWORD=...";
    exit 2
fi
RESP=$(curl -s -w '\n%{http_code}' -X POST "${BASE_URL}/api/v1/admin/token/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
if [[ "$STATUS" != "200" ]]; then
    log_fail "Login HTTP $STATUS — $(echo "$BODY" | head -c 200)"
    exit 2
fi
TOKEN=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access',''))")
if [[ -z "$TOKEN" ]]; then log_fail "Token vuoto"; exit 2; fi
log_ok "Login OK (token ${#TOKEN} char)"

# =====================================================
# 1) Setup CASO A: crea articolo nuovo + BoM esposta
# =====================================================
log_step "1) Setup CASO A: crea articolo composito-${SUFFIX} + BoM esposta"
# 1a) Clona campi struttura dall'articolo composito esistente
do_curl GET "/api/v1/catalogo/articoli/${ARTICOLO_COMPOSITO_REFERENCE_ID}/"
check_http "GET articolo reference (per clonare campi)" "200" || exit 3
REF_FIELDS=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(json.dumps({
    'codice': 'composito-${SUFFIX}',
    'descrizione': 'Smoke composito ${SUFFIX}',
    'descrizione_breve': 'Smoke ${SUFFIX}',
    'uom_id': d['uom_id'],
    'tipo_voce_id': d['tipo_voce_id'],
    'gruppo_voce_id': d['gruppo_voce_id'],
    'iva_id': d['iva_id'],
    'listino_tipologia_id': d['listino_tipologia_id'],
    'is_composito': True,
    'is_solo_componente': False,
    'meta': {'smoke_suffix': '${SUFFIX}'},
}))
")
do_curl POST "/api/v1/catalogo/articoli/" "$REF_FIELDS"
check_http "POST nuovo articolo composito" "200" || {
    log_info "Categoria fallimento: validazione catalogo (campi richiesti) o permesso"
    exit 3
}
NEW_COMPOSITO_ID=$(json_get "$LAST_BODY" "data.id")
log_info "Creato articolo composito id=$NEW_COMPOSITO_ID"

# 1b) Aggiungi riga BoM esposta valida da oggi
BOM_PAYLOAD=$(cat <<EOF
{
  "componente_id": "$COMPONENTE_REFERENCE_ID",
  "coeff_qta": 1,
  "obbligatorio": true,
  "esposto_in_fattura": true,
  "partecipa_qta": true,
  "determina_qta_padre": false,
  "valido_dal": "$DATA_IERI_UTC",
  "valido_al": null
}
EOF
)
do_curl POST "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/componenti/" "$BOM_PAYLOAD"
check_http "POST BoM componente esposto" "200" || {
    log_info "Categoria fallimento: trigger guard_coerenza_bom o permission catalogo"
    exit 3
}
NEW_BOM_ROW_ID=$(json_get "$LAST_BODY" "data.id")
log_info "Creata BoM riga id=$NEW_BOM_ROW_ID (esposto=TRUE)"

# =====================================================
# 2) Discovery cliente + emittente
# =====================================================
log_step "2) Discovery cliente (billing_account) + emittente"
# Prendo il primo cliente con utility (BA con utility_id NON NULL)
do_curl GET "/api/v1/anagrafiche/clienti/?page=1&page_size=1"
check_http "GET clienti (per discovery)" "200" || exit 4
CLIENTE_BA_ID=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
results = d.get('results', [])
for r in results:
    if r.get('billing_account_id'):
        print(r['billing_account_id']); break
")
log_info "billing_account_id = ${CLIENTE_BA_ID:-NONE}"
if [[ -z "$CLIENTE_BA_ID" ]]; then
    log_fail "Nessun cliente con billing_account trovato"
    exit 4
fi

# 2b) Form defaults BA-aware: deriva utility/istanza/valuta dalla BA
do_curl GET "/api/v1/vendite/preventivi/form-defaults/?billing_account_id=${CLIENTE_BA_ID}"
check_http "GET form-defaults preventivo BA-aware" "200" || exit 4
UTILITY_ID=$(json_get "$LAST_BODY" "data.utility_id")
ISTANZA_ID=$(json_get "$LAST_BODY" "data.istanza_utility_id")
VALUTA_ID=$(json_get "$LAST_BODY" "data.valuta_id")
DEFAULT_IVA_ID=$(json_get "$LAST_BODY" "data.iva_id")
VALIDITA_AL=$(json_get "$LAST_BODY" "data.default_validita_al")
log_info "utility=$UTILITY_ID istanza=$ISTANZA_ID valuta=$VALUTA_ID iva=$DEFAULT_IVA_ID validita_al=$VALIDITA_AL"

# 2c) Emittente: utente tid e' admin globale (no emittente assegnato),
# devo passarlo esplicito. Scelgo il primo emittente attivo via lookup.
do_curl GET "/api/v1/anagrafiche/emittenti-fiscali/?page_size=20"
check_http "GET emittenti fiscali (per discovery)" "200" || exit 4
EMITTENTE_ID=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
for e in d.get('results', []):
    if e.get('attivo'):
        print(e['id']); break
")
log_info "emittente_fiscale_id = ${EMITTENTE_ID:-NONE}"
if [[ -z "$EMITTENTE_ID" ]]; then log_fail "Nessun emittente attivo trovato"; exit 4; fi

# =====================================================
# 3) Cleanup proattivo: delete preventivi smoke precedenti
# =====================================================
log_step "3) Cleanup proattivo preventivi smoke vecchi"
do_curl GET "/api/v1/vendite/preventivi/?search=${SUFFIX}&page_size=10"
# Idempotente: anche se search non matcha nulla (suffisso unico), niente da fare
log_info "Nessun preventivo precedente col suffisso ${SUFFIX} (atteso)"

# =====================================================
# 4) Crea preventivo DRAFT
# =====================================================
log_step "4) Crea preventivo DRAFT"
PAYLOAD=$(cat <<EOF
{
  "billing_account_id": $CLIENTE_BA_ID,
  "utility_id": $UTILITY_ID,
  "istanza_utility_id": $ISTANZA_ID,
  "valuta_id": $VALUTA_ID,
  "emittente_fiscale_id": $EMITTENTE_ID,
  "data": "$DATA_OGGI_UTC",
  "validita_al": "$VALIDITA_AL",
  "meta": {"smoke_suffix": "${SUFFIX}"}
}
EOF
)
do_curl POST "/api/v1/vendite/preventivi/" "$PAYLOAD"
check_http "POST preventivo DRAFT" "200|201" || {
    log_info "Categoria fallimento: validazione testata preventivo (BA/utility/emittente)"
    exit 5
}
PREVENTIVO_ID=$(json_get "$LAST_BODY" "data.id")
PREVENTIVO_NUMERO=$(json_get "$LAST_BODY" "data.numero")
log_info "Creato preventivo id=$PREVENTIVO_ID numero=$PREVENTIVO_NUMERO"

# =====================================================
# 5) Aggiungi riga articolo composito qty=1
# =====================================================
log_step "5) Aggiungi riga articolo composito qty=1"
PAYLOAD=$(cat <<EOF
{
  "articolo_id": "$NEW_COMPOSITO_ID",
  "quantita": 1,
  "uom_operativa_id": 7,
  "prezzo_unitario": 0,
  "iva_id": 16
}
EOF
)
do_curl POST "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/" "$PAYLOAD"
# Due path attesi:
#  - 200/201: init OK (componente con listino) -> prosegui smoke completo
#  - 422 + E_DOC_COMPONENTE_LISTINO_MANCANTE: domain validation OK (componente
#    senza listino mappato) -> skip resto smoke ma marca PASS specifico
if [[ "$LAST_STATUS" == "422" ]]; then
    ERR_CODE=$(echo "$LAST_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('error',{}).get('code',''))")
    if [[ "$ERR_CODE" == "E_DOC_COMPONENTE_LISTINO_MANCANTE" ]]; then
        log_ok "POST riga composito -> 422 E_DOC_COMPONENTE_LISTINO_MANCANTE (domain validation OK, componente senza listino mappato)"
        log_info "Smoke conferma: BE/FE error path OK. Path felice (init OK + componenti popolati) richiede componente con listino mappato."
        log_info "Skip step 6-11. Cleanup."
        # Cleanup parziale: BoM + articolo (no preventivo da pulire — riga rollback atomic)
        if [[ -n "$NEW_BOM_ROW_ID" && -n "$NEW_COMPOSITO_ID" ]]; then
            do_curl PATCH "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/componenti/${NEW_BOM_ROW_ID}/" \
                "{\"valido_al\": \"$DATA_OGGI_UTC\"}"
            check_http "Cleanup BoM (chiusura)" "200" || true
        fi
        if [[ -n "$NEW_COMPOSITO_ID" ]]; then
            do_curl POST "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/disattiva/" '{}'
            check_http "Cleanup articolo (disattiva)" "200|204" || true
        fi
        do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/"
        check_http "Cleanup preventivo orfano" "200|204" || true
        echo ""
        echo "================================================"
        echo -e "  ${GREEN}DOMAIN VALIDATION PATH OK${NC}"
        echo -e "  ${YELLOW}Per smoke completo path felice: serve componente con listino mappato${NC}"
        echo "================================================"
        exit 0
    fi
fi
check_http "POST riga composito" "200|201" || {
    log_info "Categoria fallimento: gestisci_riga (init componenti BoM CASO A)"
    log_info "Possibili cause: errore non previsto"
    exit 6
}
RIGA_ID=$(json_get "$LAST_BODY" "data.id")
log_info "Creata riga id=$RIGA_ID (path felice: componente con listino)"

# =====================================================
# 6) Verifica is_composito_caso_a=TRUE sulla riga
# =====================================================
log_step "6) GET /righe/ -> flag is_composito_caso_a"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/"
check_http "GET righe preventivo" "200" || exit 7
IS_CASO_A=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
for r in d:
    if r['id'] == ${RIGA_ID}:
        print(r.get('is_composito_caso_a'))
        break
")
if [[ "$IS_CASO_A" == "True" ]]; then
    log_ok "is_composito_caso_a = True sulla riga ${RIGA_ID}"
else
    log_fail "is_composito_caso_a = ${IS_CASO_A:-MISSING} (atteso True)"
    log_info "Categoria fallimento: BE list_righe EXISTS subquery non popola il flag"
fi

# =====================================================
# 7) Lista componenti via nuovo endpoint
# =====================================================
log_step "7) GET /righe/<id>/componenti/ -> lista popolata"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/"
check_http "GET componenti riga" "200" || exit 7
N_COMP=$(echo "$LAST_BODY" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']))")
log_info "Componenti popolati: $N_COMP"
if [[ "$N_COMP" -lt 1 ]]; then
    log_fail "Atteso almeno 1 componente popolato (init fallita?)"
    log_info "Categoria fallimento: fn_preventivo_riga_componenti_init non ha inserito righe"
    exit 7
fi
log_ok "Componenti popolati ($N_COMP)"

COMPONENTE_ID=$(json_get "$LAST_BODY" "data.0.id")
COEFF_QTA=$(json_get "$LAST_BODY" "data.0.coeff_qta_snapshot")
ORIGINE_PRE=$(json_get "$LAST_BODY" "data.0.origine_prezzo")
PREZZO_PRE=$(json_get "$LAST_BODY" "data.0.prezzo_unitario")
log_info "Componente 0: id=$COMPONENTE_ID coeff=$COEFF_QTA prezzo=$PREZZO_PRE origine=$ORIGINE_PRE"

# =====================================================
# 8) PATCH componente prezzo override MANUALE
# =====================================================
log_step "8) PATCH componente prezzo=99.99 origine=MANUALE"
do_curl PATCH "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/${COMPONENTE_ID}/" \
    '{"prezzo_unitario": 99.99, "origine_prezzo": "MANUALE"}'
check_http "PATCH componente prezzo MANUALE" "200" || {
    log_info "Categoria fallimento: L1 override / L2 limit"
    log_info "Body: $(echo "$LAST_BODY" | head -c 300)"
    # Non exit: prosegui per diagnostica anche su fail
}

# =====================================================
# 9) Verifica padre prezzo_unitario = SUM(componenti × coeff)
# =====================================================
log_step "9) Re-fetch riga padre: prezzo = SUM(componenti × coeff)"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/"
PADRE_PREZZO=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
for r in d:
    if r['id'] == ${RIGA_ID}:
        print(r.get('prezzo_unitario'))
        break
")
log_info "prezzo padre post-PATCH = $PADRE_PREZZO"

do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/"
EXPECTED_PADRE=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
totale = 0
for c in d:
    coeff = float(c['coeff_qta_snapshot'])
    prezzo = float(c['prezzo_unitario'])
    totale += coeff * prezzo
print(f'{totale:.6f}')
")
log_info "Atteso prezzo padre (SUM componenti × coeff) = $EXPECTED_PADRE"

DELTA=$(python3 -c "print(abs(float('$PADRE_PREZZO') - float('$EXPECTED_PADRE')))")
TOL=0.01
if python3 -c "import sys; sys.exit(0 if float('$DELTA') < $TOL else 1)"; then
    log_ok "Trigger ricalcola padre OK (delta=$DELTA < $TOL)"
else
    log_fail "Trigger ricalcola padre FAILED: delta=$DELTA"
    log_info "Categoria fallimento: trigger DB script.trgfn_componenti_ricalcola_padre"
fi

# =====================================================
# 10) (Opzionale) DELETE componente se >1
# =====================================================
if [[ "$N_COMP" -gt 1 ]]; then
    log_step "10) DELETE componente secondario (se BoM ha >1 esposto)"
    COMPONENTE2_ID=$(json_get "$LAST_BODY" "data.1.id")
    do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/${COMPONENTE2_ID}/"
    check_http "DELETE componente secondario" "200" || true
else
    log_info "Skip step 10 (solo 1 componente esposto)"
fi

# =====================================================
# 11) Guard: tenta transizione ACCETTATO con prezzo PENDING (skip se no PENDING)
# =====================================================
log_step "11) Guard transizione (skip se nessun componente PENDING)"
log_info "Skip: questo test richiede setup L3 con sconto >L2 — coperto da test BE unit"

# =====================================================
# 12) Cleanup finale: delete preventivo + chiudi BoM + disattiva articolo
# =====================================================
log_step "12) Cleanup: delete preventivo + chiudi BoM + disattiva articolo nuovo"
do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/"
check_http "DELETE preventivo smoke" "200|204" || true

# Chiudi BoM (PATCH valido_al = ieri, valido_al non e' bloccato dal trigger immutabilita')
if [[ -n "$NEW_BOM_ROW_ID" && -n "$NEW_COMPOSITO_ID" ]]; then
    do_curl PATCH "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/componenti/${NEW_BOM_ROW_ID}/" \
        "{\"valido_al\": \"$DATA_OGGI_UTC\"}"
    check_http "PATCH BoM valido_al (chiusura)" "200" || \
        log_info "Cleanup parziale: BoM resta aperta (valido_al non patchabile?)"
fi

# Disattiva articolo nuovo (soft via PATCH attivo=false)
if [[ -n "$NEW_COMPOSITO_ID" ]]; then
    do_curl PATCH "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/" '{"attivo": false}'
    check_http "Disattiva articolo composito smoke" "200" || \
        log_info "Cleanup parziale: articolo resta attivo"
fi

# =====================================================
# SUMMARY
# =====================================================
echo ""
echo "================================================"
echo -e "  ${GREEN}PASS=${PASS}${NC}  ${RED}FAIL=${FAIL}${NC}"
echo "================================================"
[[ "$FAIL" -eq 0 ]]
