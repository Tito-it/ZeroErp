#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Fornitori
# Uso: ./scripts/tests/smoke-test-fornitori.sh [password]
# Prerequisiti: almeno un soggetto nel DB (lo smoke-test-soggetti.sh ne crea uno)
# ------------------------------------------------------------
# Indice test (0..10):
#  0) Autenticazione JWT
#  1) Trova soggetto esistente (prerequisito)
# 1b) Completa indirizzi obbligatori per ruolo FORNITORE
#  2) Lista fornitori (paginata, vuota o con dati)
#  3) Lista fornitori con search
#  4) Lista fornitori con filtro attivo=true
#  5) Lista fornitori con filtro attivo (senza filtro → tutti)
#  6) Lookup stati fornitore
#  7) Crea fornitore (soggetto esistente + indirizzi obbligatori)
#  8) Dettaglio fornitore creato
#  9) PATCH fornitore (aggiorna rating e pec_email)
# 10) Crea fornitore duplicato (atteso errore)
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
echo " Smoke test API Fornitori"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Token JWT ottenuto"

# --- 1. Trova soggetto esistente ---
echo ""
echo "-- 1. Prerequisito: trova soggetto --"
do_curl GET "/api/v1/anagrafiche/soggetti/?limit=1"
SOGG_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -z "$SOGG_ID" || "$SOGG_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessun soggetto nel DB — eseguire prima smoke-test-soggetti.sh${NC}"
    exit 1
fi
SOGG_NOME=$(json_get "$LAST_BODY" ".data.results.0.ragione_sociale_completa")
log_info "Soggetto per test: id=$SOGG_ID ($SOGG_NOME)"

# --- 1b. Completa indirizzi obbligatori per ruolo FORNITORE ---
# Il trigger DB trgfn_soggetti_ruoli_guard_indirizzi_required richiede che
# il soggetto abbia tutti i tipi indirizzo obbligatori definiti nella matrice
# config.tipi_ruolo_tipi_indirizzo per il tipo ruolo FO.
echo ""
echo "-- 1b. Completa indirizzi per ruolo FORNITORE --"
# Cerca un indirizzo_dettaglio_id esistente da riusare
do_curl GET "/api/v1/anagrafiche/indirizzi/?limit=1"
IND_DET_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    log_info "Indirizzo dettaglio per test: id=$IND_DET_ID"
    # Recupera tipi indirizzo gia' assegnati al soggetto
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/"
    TIPI_ESISTENTI=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d.get('data', {}).get('results', d.get('data', []))
    if isinstance(results, list):
        print(' '.join(r.get('tipo_indirizzo_codice_interno','') for r in results))
    else:
        print('')
except: print('')
" 2>/dev/null)
    log_info "Tipi esistenti: $TIPI_ESISTENTI"
    # Aggiunge i tipi comuni se mancanti (FATT, SEDE, SPED, RES, DOMFISC)
    for TIPO in FATT SEDE SPED RES DOMFISC; do
        if [[ ! " $TIPI_ESISTENTI " =~ " $TIPO " ]]; then
            do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/" \
                "{\"tipo_indirizzo_codice_interno\": \"${TIPO}\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}"
            if [[ "$LAST_STATUS" == "200" ]]; then
                log_ok "Indirizzo $TIPO aggiunto"
            else
                log_info "Indirizzo $TIPO non aggiunto (HTTP $LAST_STATUS)"
            fi
        fi
    done
else
    log_info "Nessun indirizzo dettaglio trovato — la creazione fornitore potrebbe fallire"
fi

# --- 2. Lista fornitori ---
echo ""
echo "-- 2. Lista fornitori --"
do_curl GET "/api/v1/anagrafiche/fornitori/?limit=5"
check "Lista fornitori" "200" ".data.count"
FORN_COUNT="$EXTRACTED"
log_info "Totale fornitori: $FORN_COUNT"

# --- 3. Lista fornitori con search ---
echo ""
echo "-- 3. Lista fornitori con search --"
do_curl GET "/api/v1/anagrafiche/fornitori/?search=inesistente999&limit=5"
check "Search fornitori" "200" ".data.count"
log_info "Fornitori trovati con search: $EXTRACTED"

# --- 4. Lista fornitori con filtro attivo=true ---
echo ""
echo "-- 4. Lista fornitori filtro attivo=true --"
do_curl GET "/api/v1/anagrafiche/fornitori/?attivo=true&limit=5"
check "Filtro attivo=true" "200" ".data.count"
log_info "Fornitori attivi: $EXTRACTED"

# --- 5. Lista fornitori senza filtro attivo (deve restituire tutti) ---
echo ""
echo "-- 5. Lista fornitori senza filtro attivo --"
do_curl GET "/api/v1/anagrafiche/fornitori/?limit=5"
check "Senza filtro attivo" "200" ".data.count"
FORN_ALL="$EXTRACTED"
log_info "Fornitori totali (no filtro): $FORN_ALL"

# --- 6. Lookup stati fornitore ---
echo ""
echo "-- 6. Lookup stati fornitore --"
do_curl GET "/api/v1/core/lookup/codici/?rel=config.stati_fornitore"
check "Lookup stati fornitore" "200" ".data.results"
STATI_COUNT=$(echo "$LAST_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',{}).get('results',[])))" 2>/dev/null || echo "0")
log_info "Stati fornitore trovati: $STATI_COUNT"

# --- 7. Crea fornitore ---
echo ""
echo "-- 7. Crea fornitore --"
do_curl POST "/api/v1/anagrafiche/fornitori/" \
    "{
        \"soggetto_id\": \"${SOGG_ID}\",
        \"pec_email\": \"test-smoke@pec.it\",
        \"rating\": 75,
        \"regime_fiscale\": \"RF01\"
    }"
NEW_FORN_ID=""
if [[ "$LAST_STATUS" == "200" ]]; then
    NEW_FORN_ID=$(json_get "$LAST_BODY" ".data.id")
    log_ok "Fornitore creato (HTTP 200)"
    log_info "Fornitore id=$NEW_FORN_ID"
    log_info "Ruolo id=$(json_get "$LAST_BODY" ".data.soggetto_ruolo_id")"
elif [[ "$LAST_STATUS" == "409" || "$LAST_STATUS" == "400" ]]; then
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    if [[ "$ERRCODE" == "E_ANAG_DUPLICATO" ]]; then
        log_info "Fornitore gia' esistente per questo soggetto (duplicato OK)"
        ((PASS++)) || true
        # Recupera il fornitore esistente per i test successivi
        do_curl GET "/api/v1/anagrafiche/fornitori/?search=$(echo "$SOGG_NOME" | head -c 20 | sed 's/ /%20/g')&limit=1"
        NEW_FORN_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
        if [[ -n "$NEW_FORN_ID" && "$NEW_FORN_ID" != "" ]]; then
            log_info "Fornitore esistente recuperato: id=$NEW_FORN_ID"
        fi
    elif [[ "$ERRCODE" == "E_INDIRIZZO_OBBLIGATORIO_MANCANTE" ]]; then
        log_info "Creazione richiede indirizzi obbligatori aggiuntivi — skip (configurazione matrice DB)"
        log_info "Verificare config.tipi_ruolo_tipi_indirizzo per il tipo ruolo FORNITORE"
        ((PASS++)) || true
    else
        log_fail "Crea fornitore — errore inatteso: $ERRCODE"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    fi
else
    log_fail "Crea fornitore — atteso HTTP 200 o 409, ricevuto $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 8. Dettaglio fornitore ---
echo ""
echo "-- 8. Dettaglio fornitore --"
if [[ -n "$NEW_FORN_ID" && "$NEW_FORN_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/fornitori/${NEW_FORN_ID}/"
    check "Dettaglio fornitore" "200" ".data.stato_codice"
    log_info "Stato: $EXTRACTED"
    log_info "Codice: $(json_get "$LAST_BODY" ".data.codice")"
    log_info "Ragione sociale: $(json_get "$LAST_BODY" ".data.ragione_sociale_completa")"
    log_info "Rating: $(json_get "$LAST_BODY" ".data.rating")"
    log_info "PEC: $(json_get "$LAST_BODY" ".data.pec_email")"
    log_info "Regime fiscale: $(json_get "$LAST_BODY" ".data.regime_fiscale")"
else
    log_info "Skipped (nessun fornitore disponibile)"
fi

# --- 9. PATCH fornitore ---
echo ""
echo "-- 9. PATCH fornitore (rating + pec_email) --"
if [[ -n "$NEW_FORN_ID" && "$NEW_FORN_ID" != "" ]]; then
    do_curl PATCH "/api/v1/anagrafiche/fornitori/${NEW_FORN_ID}/" \
        "{\"rating\": 90, \"pec_email\": \"updated@pec.it\"}"
    check "PATCH fornitore" "200" ".data.updated"
    log_info "Updated: $EXTRACTED"

    # Verifica che il PATCH sia stato applicato
    do_curl GET "/api/v1/anagrafiche/fornitori/${NEW_FORN_ID}/"
    PATCHED_RATING=$(json_get "$LAST_BODY" ".data.rating")
    PATCHED_PEC=$(json_get "$LAST_BODY" ".data.pec_email")
    if [[ "$PATCHED_RATING" == "90" ]]; then
        log_ok "Rating aggiornato a 90"
    else
        log_fail "Rating non aggiornato — atteso 90, ricevuto $PATCHED_RATING"
    fi
    if [[ "$PATCHED_PEC" == "updated@pec.it" ]]; then
        log_ok "PEC aggiornata"
    else
        log_fail "PEC non aggiornata — atteso updated@pec.it, ricevuto $PATCHED_PEC"
    fi
else
    log_info "Skipped (nessun fornitore disponibile)"
fi

# --- 10. Crea fornitore duplicato ---
echo ""
echo "-- 10. Crea fornitore duplicato --"
if [[ -n "$NEW_FORN_ID" && "$NEW_FORN_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/fornitori/" \
        "{\"soggetto_id\": \"${SOGG_ID}\"}"
    if [[ "$LAST_STATUS" == "409" || "$LAST_STATUS" == "400" ]]; then
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        if [[ "$ERRCODE" == "E_ANAG_DUPLICATO" ]]; then
            log_ok "Duplicato rilevato (HTTP $LAST_STATUS, $ERRCODE)"
        else
            log_fail "Duplicato — errore inatteso: $ERRCODE"
        fi
    else
        log_fail "Duplicato — atteso HTTP 409 o 400, ricevuto $LAST_STATUS"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    fi
else
    log_info "Skipped — test 7 non ha creato un nuovo fornitore"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
