#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Clienti
# Uso: ./scripts/tests/smoke-test-clienti.sh [password]
# Prerequisiti: il soggetto lo crea lo smoke (BB _smoke_soggetto.sh), uno per giro
# ------------------------------------------------------------
# Indice test (0..12):
#  0) Autenticazione JWT
#  1) Lookup utility ammesse per creazione manuale
#  2) Lista clienti (paginata, vuota o con dati)
#  3) Lista clienti con search
#  4) Lista clienti con filtro utility
#  5) Crea cliente manuale (soggetto NUOVO del giro + utility senza PDP)
#  6) Dettaglio cliente creato
#  7) Crea cliente manuale — utility GAS bloccata (atteso errore)
#  8) Secondo cliente manuale, stessa chiave -> 409 E_CLIENTE_STESSA_CHIAVE
#  --- Fix #1 analisi-fix-transazioni: update via fn madre atomica ---
#  9) Update campi cliente (fn madre) + verifica persistenza su dettaglio
# 10) Update ATOMICO categoria BA + campo cliente in una sola fn + verifica
# 11) Update campo numerico nullable con "" -> NULL (no crash cast, regressione)
# 12) Update senza campi -> 400 E_ANAG_VALIDAZIONE (guard "nessun campo")
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_soggetto.sh"

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
echo " Smoke test API Clienti"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Token JWT ottenuto"

# --- 1. Lookup utility ammesse ---
echo ""
echo "-- 1. Lookup utility ammesse per creazione manuale --"
do_curl GET "/api/v1/anagrafiche/utilities/manual-lookup/"
check "Lookup utility manuali" "200" ".data.results"
UTIL_COUNT=$(echo "$LAST_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',{}).get('results',[])))" 2>/dev/null || echo "0")
log_info "Utility ammesse: $UTIL_COUNT"

# Prendi la prima utility ammessa (richiede_pdp=false)
MANUAL_UTIL_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
MANUAL_UTIL_DESC=$(json_get "$LAST_BODY" ".data.results.0.descrizione")
if [[ -z "$MANUAL_UTIL_ID" || "$MANUAL_UTIL_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessuna utility con richiede_pdp=false trovata${NC}"
    echo "       Verificare seed config.utilities"
    exit 1
fi
log_info "Utility per test: id=$MANUAL_UTIL_ID ($MANUAL_UTIL_DESC)"

# --- Il soggetto del giro: NUOVO a ogni giro ---
echo ""
echo "-- Prerequisito: crea il soggetto del giro --"
# ⭐ Dal 2026-10-14 un soggetto ha UN cliente manuale per utility e azienda
# (E_CLIENTE_STESSA_CHIAVE, brief-db-cliente-manuale-uno-per-soggetto-e-utility
# C-1/C-2). Fino ad allora lo smoke prendeva il soggetto del primo cliente
# della lista e gli creava un cliente in piu' a ogni giro: su dbdev ne aveva
# lasciati decine sullo stesso soggetto, e dal giorno del guard il passo 5 era
# rifiutato e i passi 9-11 lavoravano su un doppione. Il soggetto lo crea il
# BB dall'API; gli indirizzi del RUOLO cliente (FATT, ripiego DOMFISC) si
# passano alla creazione del cliente, al passo 5.
smoke_soggetto_privato "Cliente"
if [[ -z "$SOGG_ID" ]]; then
    echo -e "${RED}ERRORE: impossibile creare il soggetto del giro (motivo sopra)${NC}"
    exit 1
fi
SOGG_NOME="SmokeTest Cliente${SMOKE_TS}"
IND_RUOLO_JSON="[{\"tipo_indirizzo_codice\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}]"
log_info "Soggetto per test: id=$SOGG_ID ($SOGG_NOME, CF $SOGG_CF)"

# --- 2. Lista clienti ---
echo ""
echo "-- 2. Lista clienti --"
do_curl GET "/api/v1/anagrafiche/clienti/?limit=5"
check "Lista clienti" "200" ".data.count"
CLI_COUNT="$EXTRACTED"
log_info "Totale clienti: $CLI_COUNT"

# --- 3. Lista clienti con search ---
echo ""
echo "-- 3. Lista clienti con search --"
do_curl GET "/api/v1/anagrafiche/clienti/?search=inesistente999&limit=5"
check "Search clienti" "200" ".data.count"
log_info "Clienti trovati con search: $EXTRACTED"

# --- 4. Lista clienti con filtro utility ---
echo ""
echo "-- 4. Lista clienti filtro utility --"
do_curl GET "/api/v1/anagrafiche/clienti/?utility_id=${MANUAL_UTIL_ID}&limit=5"
check "Filtro utility" "200" ".data.count"
log_info "Clienti per utility $MANUAL_UTIL_ID: $EXTRACTED"

# La creazione apre anche il BA, e il BA nasce con la sua categoria cliente
# (pricing v5): `ba_categoria_cliente_id` e' obbligatorio. Una qualsiasi, dal
# lookup generico.
do_curl GET "/api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti&limit=1"
CAT_CREA_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
[[ -z "$CAT_CREA_ID" ]] && { echo -e "${RED}ERRORE: nessuna categoria cliente${NC}"; exit 1; }
log_info "Categoria cliente per le creazioni: id=$CAT_CREA_ID"

# --- 5. Crea cliente manuale ---
echo ""
echo "-- 5. Crea cliente manuale --"
do_curl POST "/api/v1/anagrafiche/clienti/" \
    "{
        \"soggetto_id\": \"${SOGG_ID}\",
        \"utility_id\": ${MANUAL_UTIL_ID},
        \"ba_categoria_cliente_id\": ${CAT_CREA_ID},
        \"indirizzi\": ${IND_RUOLO_JSON}
    }"
NEW_CLI_ID=""
if [[ "$LAST_STATUS" == "200" ]]; then
    NEW_CLI_ID=$(json_get "$LAST_BODY" ".data.id")
    log_ok "Cliente creato (HTTP 200)"
    log_info "Cliente id=$NEW_CLI_ID"
    log_info "Istanza id=$(json_get "$LAST_BODY" ".data.istanza_utility_id")"
    log_info "BA id=$(json_get "$LAST_BODY" ".data.billing_account_id")"
elif [[ "$LAST_STATUS" == "403" ]]; then
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    if [[ "$ERRCODE" == "E_BA_ADMIN_GLOBALE_VIETATO" ]]; then
        # Guard operatore-emittenti: admin globale non crea BA con emittenti
        # presenti. Atteso in ambienti con emittenti fiscali seed. I test di
        # update (9-12) usano un cliente esistente della lista come fallback.
        log_info "Creazione BA vietata ad admin globale (guard OK, si usa cliente esistente)"
        ((PASS++)) || true
    else
        log_fail "Crea cliente — errore 403 inatteso: $ERRCODE"
    fi
else
    # ⛔ Niente piu' «409 = duplicato, va bene»: il soggetto e' nuovo, un
    # rifiuto qui e' un difetto.
    log_fail "Crea cliente — atteso HTTP 200 (o 403 admin globale), ricevuto $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
fi

# --- 6. Dettaglio cliente ---
echo ""
echo "-- 6. Dettaglio cliente --"
if [[ -n "$NEW_CLI_ID" && "$NEW_CLI_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/clienti/${NEW_CLI_ID}/"
    check "Dettaglio cliente" "200" ".data.stato_codice"
    log_info "Stato: $EXTRACTED"
    log_info "BA codice: $(json_get "$LAST_BODY" ".data.ba_codice")"
    log_info "Utility: $(json_get "$LAST_BODY" ".data.utility_descrizione")"
    log_info "Ragione sociale: $(json_get "$LAST_BODY" ".data.ragione_sociale_completa")"
else
    log_info "Skipped (creazione non ha prodotto nuovo id)"
fi

# --- 7. Crea cliente — utility GAS bloccata ---
echo ""
echo "-- 7. Crea cliente utility GAS (richiede_pdp=true) --"
# Trova utility GAS
GAS_UTIL_ID=""
do_curl GET "/api/v1/core/lookup/codici/?rel=config.utilities&search=GAS&limit=1"
GAS_UTIL_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -n "$GAS_UTIL_ID" && "$GAS_UTIL_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/clienti/" \
        "{
            \"soggetto_id\": \"${SOGG_ID}\",
            \"utility_id\": ${GAS_UTIL_ID},
            \"ba_categoria_cliente_id\": ${CAT_CREA_ID}
        }"
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    ERRMSG=$(json_get "$LAST_BODY" ".error.message")
    # ⚠️ Il 400 deve essere QUELLO del PDP: lo stesso codice esce anche per un
    # payload incompleto (fino al 2026-10-12 il passo era verde per la categoria
    # mancante, non per il PDP).
    if [[ "$LAST_STATUS" == "400" && "$ERRCODE" == "E_ANAG_VALIDAZIONE" && "$ERRMSG" == *PDP* ]]; then
        log_ok "Utility GAS bloccata per creazione manuale (HTTP 400, $ERRCODE)"
    elif [[ "$LAST_STATUS" == "403" && "$ERRCODE" == "E_BA_ADMIN_GLOBALE_VIETATO" ]]; then
        # In ambienti con emittenti fiscali il guard operatore-emittenti (403)
        # scatta prima del check PDP (400): la creazione resta comunque bloccata.
        log_ok "Utility GAS bloccata a monte dal guard emittenti (HTTP 403, $ERRCODE)"
    else
        log_fail "Utility GAS — atteso 400/E_ANAG_VALIDAZIONE o 403/E_BA_ADMIN_GLOBALE_VIETATO, ricevuto $LAST_STATUS/$ERRCODE"
    fi
else
    log_info "Skipped — utility GAS non trovata nel DB"
fi

# --- 8. Secondo cliente manuale con la stessa chiave ---
# ⭐ Deciso da Tid il 2026-10-13 (C-1/C-2): un cliente manuale per soggetto,
# utility e azienda, attivo nello stesso periodo. Il secondo e' rifiutato dal
# DB col codice del cliente esistente nel messaggio (C-3), classe
# CONFLITTO_STATO (409). ⛔ Si pretende IL CODICE, non «un 400 o un 409
# qualsiasi»: prima il passo passava su qualunque rifiuto, anche di tutt'altro.
echo ""
echo "-- 8. Secondo cliente, stessa chiave --"
if [[ -n "$NEW_CLI_ID" && "$NEW_CLI_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/clienti/" \
        "{
            \"soggetto_id\": \"${SOGG_ID}\",
            \"utility_id\": ${MANUAL_UTIL_ID},
            \"ba_categoria_cliente_id\": ${CAT_CREA_ID},
            \"indirizzi\": ${IND_RUOLO_JSON}
        }"
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    if [[ "$LAST_STATUS" == "409" && "$ERRCODE" == "E_CLIENTE_STESSA_CHIAVE" ]]; then
        log_ok "Secondo cliente rifiutato (HTTP 409, $ERRCODE)"
        log_info "$(json_get "$LAST_BODY" ".error.message")"
    else
        log_fail "Secondo cliente — atteso 409/E_CLIENTE_STESSA_CHIAVE, ricevuto $LAST_STATUS/$ERRCODE"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    fi
else
    log_info "Skipped — test 5 non ha creato un nuovo cliente"
fi

# ================================================================
# Fix #1 (analisi-fix-transazioni, Classe A): update cliente via funzione
# madre atomica anagrafiche.fn_update_cliente. Serve un cliente su cui agire:
# riusa quello creato al test 5, altrimenti il primo della lista.
# ================================================================
echo ""
echo "-- Prerequisito update: individua cliente bersaglio --"
TARGET_CLI_ID="$NEW_CLI_ID"
if [[ -z "$TARGET_CLI_ID" || "$TARGET_CLI_ID" == "" ]]; then
    do_curl GET "/api/v1/anagrafiche/clienti/?limit=1"
    TARGET_CLI_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
fi

if [[ -z "$TARGET_CLI_ID" || "$TARGET_CLI_ID" == "" ]]; then
    log_info "Skipped test 9-12 — nessun cliente disponibile da aggiornare"
else
    log_info "Cliente bersaglio update: id=$TARGET_CLI_ID"
    # Categoria valida da riusare nell'update combinato: leggo quella corrente
    # dal dettaglio (BA.categoria_cliente_id e' NOT NULL => sempre presente).
    do_curl GET "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/"
    CAT_ID=$(json_get "$LAST_BODY" ".data.ba_categoria_cliente_id")
    log_info "Categoria BA corrente: $CAT_ID"

    # --- 9. Update campi cliente (fn madre) + verifica persistenza ---
    # ⚠️ Contratto della PATCH (CLIENTE_UPDATE_ALLOWED + ba_categoria_cliente_id):
    # pagamento, servizio_da_fatturare, garanzia, categoria del BA. Fino al
    # 2026-10-12 lo smoke scriveva codice_commessa e i giorni di scadenza, usciti
    # dal contratto (400 «Campi non supportati»). Il bersaglio puo' essere un
    # cliente vero: ogni valore toccato torna com'era.
    echo ""
    echo "-- 9. Update campi cliente (fn madre atomica) --"
    do_curl GET "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/"
    ORIG_SERV=$(json_get "$LAST_BODY" ".data.servizio_da_fatturare")
    ORIG_GAR=$(json_get "$LAST_BODY" ".data.garanzia_importo")
    if [[ "$ORIG_SERV" == "True" || "$ORIG_SERV" == "true" ]]; then ORIG_SERV_JSON=true; NEW_SERV_JSON=false
    else ORIG_SERV_JSON=false; NEW_SERV_JSON=true; fi
    do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" \
        "{\"servizio_da_fatturare\": ${NEW_SERV_JSON}}"
    if check "PATCH update campi" "200"; then
        do_curl GET "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/"
        GOT_SERV=$(json_get "$LAST_BODY" ".data.servizio_da_fatturare" | tr '[:upper:]' '[:lower:]')
        if [[ "$GOT_SERV" == "$NEW_SERV_JSON" ]]; then
            log_ok "Persistenza verificata (servizio_da_fatturare=$GOT_SERV)"
        else
            log_fail "Persistenza KO (servizio_da_fatturare=$GOT_SERV, atteso $NEW_SERV_JSON)"
        fi
    fi

    # --- 10. Update ATOMICO categoria BA + campo cliente ---
    echo ""
    echo "-- 10. Update atomico categoria BA + campo cliente --"
    if [[ -n "$CAT_ID" && "$CAT_ID" != "" && "$CAT_ID" != "None" ]]; then
        do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" \
            "{\"ba_categoria_cliente_id\": ${CAT_ID}, \"servizio_da_fatturare\": ${ORIG_SERV_JSON}}"
        if check "PATCH categoria+campo (una sola fn madre)" "200"; then
            do_curl GET "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/"
            GOT_SERV=$(json_get "$LAST_BODY" ".data.servizio_da_fatturare" | tr '[:upper:]' '[:lower:]')
            GOT_CAT=$(json_get "$LAST_BODY" ".data.ba_categoria_cliente_id")
            if [[ "$GOT_SERV" == "$ORIG_SERV_JSON" && "$GOT_CAT" == "$CAT_ID" ]]; then
                log_ok "Scrittura atomica verificata (categoria=$GOT_CAT, servizio_da_fatturare=$GOT_SERV, ripristinato)"
            else
                log_fail "Scrittura atomica KO (categoria=$GOT_CAT, servizio_da_fatturare=$GOT_SERV)"
            fi
        fi
    else
        log_info "Skipped — categoria BA corrente non risolta"
        do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" \
            "{\"servizio_da_fatturare\": ${ORIG_SERV_JSON}}"   # ripristino
    fi

    # --- 11. Regressione: campo numerico nullable "" -> NULL (no crash cast) ---
    # "" su un numerico nullable deve arrivare alla fn come NULL (normalizzazione
    # BE), non far crashare il cast. Poi si rimette il valore di partenza.
    echo ""
    echo "-- 11. Update garanzia_importo=\"\" -> NULL (normalizzazione BE) --"
    do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" \
        '{"garanzia_importo": ""}'
    if check "PATCH stringa vuota su numerico nullable" "200"; then
        do_curl GET "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/"
        GOT_GAR=$(json_get "$LAST_BODY" ".data.garanzia_importo")
        if [[ -z "$GOT_GAR" || "$GOT_GAR" == "None" ]]; then
            log_ok "Campo azzerato a NULL (garanzia_importo vuoto)"
        else
            log_fail "Atteso NULL, ricevuto garanzia_importo=$GOT_GAR"
        fi
    fi
    if [[ -n "$ORIG_GAR" && "$ORIG_GAR" != "None" ]]; then
        do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" \
            "{\"garanzia_importo\": ${ORIG_GAR}}"   # ripristino
    fi

    # --- 12. Update senza campi -> guard "nessun campo" ---
    # Un PATCH vuoto su un cliente che esiste e' un payload sbagliato: 400
    # E_ANAG_VALIDAZIONE «Nessun campo da aggiornare». Fino al 2026-10-12 lo
    # smoke si aspettava 404 E_ANAG_NOT_FOUND, che diceva «non trovato» di un
    # cliente presente.
    echo ""
    echo "-- 12. Update senza campi (atteso 400 E_ANAG_VALIDAZIONE) --"
    do_curl PATCH "/api/v1/anagrafiche/clienti/${TARGET_CLI_ID}/" '{}'
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    if [[ "$LAST_STATUS" == "400" && "$ERRCODE" == "E_ANAG_VALIDAZIONE" ]]; then
        log_ok "Guard nessun campo (HTTP 400, $ERRCODE)"
    else
        log_fail "Update vuoto — atteso 400/E_ANAG_VALIDAZIONE, ricevuto $LAST_STATUS/$ERRCODE"
    fi
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
