#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Soggetti
# Uso: ./scripts/tests/smoke-test-soggetti.sh [password]
# ------------------------------------------------------------
# Indice test (0..16):
#  0) Autenticazione JWT
#  1) Lista soggetti (paginata)
#  2) Lista soggetti con search
#  3) Lista soggetti con filtro tipo
#  4) Crea soggetto PF
#  5) Dettaglio soggetto creato (con contatti, indirizzi, ruoli)
#  6) Modifica soggetto (PATCH cognome)
#  7) Lista contatti del soggetto
#  8) Crea contatto aggiuntivo
#  9) Modifica contatto
# 10) Lista indirizzi del soggetto
# 11) Lista ruoli del soggetto
# 12) Ruoli: CLIENTE rifiutato (flusso Clienti), VETTORE assegnato
# 13) Lista ruoli dopo assegnazione (VETTORE presente)
# 14) Crea soggetto PF — CF duplicato (atteso 409)
# 15) Crea privato SENZA sesso → 400 E_SESSO_OBBLIGATORIO, campo `sesso`
#     (il guard del DB: nessun default, brief-db-sesso-senza-default)
# 16) Crea ditta individuale con P.IVA e senza sesso → nasce DI, sesso NULL
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
# Indirizzo, tipo privato e soggetto nuovo: un BB, condiviso col contratto.
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
echo " Smoke test API Soggetti"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "Token JWT ottenuto"

# --- 1. Lista soggetti ---
echo ""
echo "-- 1. Lista soggetti --"
do_curl GET "/api/v1/anagrafiche/soggetti/?limit=5"
check "Lista soggetti" "200" ".data.count"
SOGG_COUNT="$EXTRACTED"
log_info "Totale soggetti: $SOGG_COUNT"

# --- 2. Lista soggetti con search ---
echo ""
echo "-- 2. Lista soggetti con search --"
do_curl GET "/api/v1/anagrafiche/soggetti/?search=smoke&limit=5"
check "Search soggetti" "200" ".data.count"
log_info "Soggetti trovati con search: $EXTRACTED"

# --- 3. Lista soggetti con filtro tipo ---
echo ""
echo "-- 3. Lista soggetti filtro tipo PF privato --"
smoke_tipo_privato
do_curl GET "/api/v1/anagrafiche/soggetti/?tipo_soggetto_dettaglio_id=${TIPO_PRIVATO_ID}&limit=5"
check "Filtro tipo PF" "200" ".data.count"
log_info "Soggetti PF: $EXTRACTED"

# --- 3b. Trova o crea un indirizzo_dettaglio_id per creazione soggetto ---
echo ""
echo "-- 3b. Cerca/crea indirizzo dettaglio --"
IND_DET_ID=""
smoke_indirizzo_dettaglio   # BB _smoke_soggetto.sh: esistente, o nuovo a Milano
if [[ -n "$IND_DET_ID" ]]; then
    log_ok "Indirizzo dettaglio id=$IND_DET_ID"
else
    log_fail "Nessun indirizzo disponibile — test creazione soggetto non eseguibile"
fi

# --- 4. Crea soggetto PF ---
echo ""
echo "-- 4. Crea soggetto PF --"
# Il BB genera il CF (data di nascita dal timestamp), il contatto e gli
# indirizzi RES + DOMFISC; qui si prova la sua POST col `check` di sempre.
SOGG_ID=""
if [[ -n "$IND_DET_ID" ]]; then
    smoke_soggetto_privato "Soggetto"
    if [[ -z "$SOGG_CF" ]]; then
        echo -e "${RED}ERRORE: preparazione del soggetto fallita (motivo sopra)${NC}"
        exit 1
    fi
    SMOKE_CF="$SOGG_CF"
    CORRIDONIA_ID="$COMUNE_NASCITA_ID"
    log_info "CF generato: $SMOKE_CF (data nascita: $SMOKE_BDATE)"
    LAST_STATUS="$SOGG_LAST_STATUS"; LAST_BODY="$SOGG_LAST_BODY"
    check "Crea soggetto PF" "200" ".data.id"
    SOGG_ID="${SOGG_ID:-}"
    log_info "Soggetto creato id=$SOGG_ID"
else
    log_info "Skipped — nessun indirizzo disponibile"
fi

# --- 5. Dettaglio soggetto ---
echo ""
echo "-- 5. Dettaglio soggetto --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/"
    check "Dettaglio soggetto" "200" ".data.cognome"
    log_info "Cognome: $EXTRACTED"
    CONTATTI_COUNT=$(json_get "$LAST_BODY" ".data.contatti" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    log_info "Contatti: $CONTATTI_COUNT, Natura: $(json_get "$LAST_BODY" ".data.natura_soggetto")"
else
    log_info "Skipped (creazione fallita)"
fi

# --- 6. Modifica soggetto ---
echo ""
echo "-- 6. Modifica soggetto --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl PATCH "/api/v1/anagrafiche/soggetti/${SOGG_ID}/" \
        "{\"cognome\": \"SmokeTestUpd\"}"
    check "Modifica cognome" "200"
else
    log_info "Skipped"
fi

# --- 7. Lista contatti ---
echo ""
echo "-- 7. Lista contatti --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/contatti/"
    check "Lista contatti" "200"
    FIRST_CONTATTO_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
    log_info "Primo contatto id=$FIRST_CONTATTO_ID"
else
    log_info "Skipped"
fi

# --- 8. Crea contatto aggiuntivo ---
echo ""
echo "-- 8. Crea contatto aggiuntivo --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/contatti/" \
        "{\"nominativo\": \"Contatto Secondario\", \"email\": \"secondo@test.it\", \"tipo_contatto_id\": ${TIPO_CONTATTO_2_ID}}"
    check "Crea contatto" "200" ".data.id"
    NEW_CONTATTO_ID="$EXTRACTED"
    log_info "Contatto creato id=$NEW_CONTATTO_ID"
else
    log_info "Skipped"
fi

# --- 9. Modifica contatto ---
echo ""
echo "-- 9. Modifica contatto --"
if [[ -n "$SOGG_ID" && -n "${NEW_CONTATTO_ID:-}" && "$NEW_CONTATTO_ID" != "" ]]; then
    do_curl PATCH "/api/v1/anagrafiche/soggetti/${SOGG_ID}/contatti/${NEW_CONTATTO_ID}/" \
        "{\"telefono\": \"9876543210\"}"
    check "Modifica contatto" "200"
else
    log_info "Skipped"
fi

# --- 10. Lista indirizzi soggetto ---
echo ""
echo "-- 10. Lista indirizzi soggetto --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/"
    check "Lista indirizzi" "200"
else
    log_info "Skipped"
fi

# --- 11. Lista ruoli ---
echo ""
echo "-- 11. Lista ruoli --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/"
    check "Lista ruoli (vuota)" "200"
else
    log_info "Skipped"
fi

# --- 11b. Aggiungi indirizzi al soggetto ---
echo ""
echo "-- 11b. Completa indirizzi del soggetto --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" && -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
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
    # Solo tipi che la matrice del privato ammette
    # (config.tipi_soggetto_dettaglio_tipi_indirizzo): una sede non ce l'ha.
    for TIPO in FATT SPED; do
        if [[ ! " $TIPI_ESISTENTI " =~ " $TIPO " ]]; then
            do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/" \
                "{\"tipo_indirizzo_codice_interno\": \"${TIPO}\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}"
            check "Indirizzo $TIPO aggiunto" "200" || true
        fi
    done
else
    log_info "Skipped"
fi

# --- 12. Ruoli: CLIENTE dal suo flusso, VETTORE da qui ---
# CL, FO, EF e RIS_UMANA hanno un flusso dedicato (il CL nasce con la prima
# istanza e il suo billing account): l'endpoint generico li rifiuta sul campo
# (decisione di Tid, 2026-10-09). Un ruolo senza flusso dedicato si assegna.
echo ""
echo "-- 12. Assegna ruoli --"
RUOLO_ASSEGNATO=""
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/" "{\"codice_ruolo\": \"CLIENTE\"}"
    if check "CLIENTE dall'endpoint generico → 400" "400"; then
        CAMPI=$(json_get "$LAST_BODY" ".error.fields")
        MSG=$(json_get "$LAST_BODY" ".error.message")
        if [[ "$CAMPI" == *codice_ruolo* && "$MSG" == *Cliente* ]]; then
            log_ok "Rifiuta il ruolo Cliente (flusso dedicato), campo codice_ruolo"
        else
            log_fail "Atteso rifiuto del ruolo Cliente col campo — ricevuto: $MSG / $CAMPI"
        fi
    fi
    do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/" "{\"codice_ruolo\": \"VETTORE\"}"
    if check "Assegna ruolo VETTORE" "200" ".data.id"; then
        RUOLO_ASSEGNATO="$EXTRACTED"
    fi
else
    log_info "Skipped"
fi

# --- 13. Lista ruoli dopo assegnazione ---
echo ""
echo "-- 13. Lista ruoli dopo assegnazione --"
if [[ -n "$RUOLO_ASSEGNATO" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/"
    if check "Lista ruoli" "200"; then
        # ⚠️ La chiave e' `ruolo_codice_interno` dal 2026-11-04 (61eb42c39,
        #    «chiavi interne esatte»): con il nome vecchio il parser falliva
        #    in silenzio e la lista sembrava vuota.
        RUOLI=$(echo "$LAST_BODY" | python3 -c "
import sys, json
print(' '.join(r['ruolo_codice_interno'] for r in json.load(sys.stdin)['data']['results']))" 2>/dev/null || true)
        if [[ " $RUOLI " == *" VT "* ]]; then
            log_ok "VETTORE in lista ($RUOLI)"
        else
            log_fail "VETTORE assente dalla lista ruoli — ricevuto: '$RUOLI'"
        fi
    fi
else
    log_info "Skipped"
fi

# --- 14. Crea soggetto PF duplicato (CF uguale — atteso errore) ---
echo ""
echo "-- 14. Crea soggetto PF duplicato --"
if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/soggetti/" \
        "{
            \"tipo_soggetto_dettaglio_id\": ${TIPO_PRIVATO_ID},
            \"cognome\": \"Duplicato\",
            \"nome\": \"Test\",
            \"codice_fiscale\": \"${SMOKE_CF}\",
            \"sesso\": \"M\",
            \"contatto\": {\"tipo_contatto_id\": ${TIPO_CONTATTO_ID}, 
                \"nominativo\": \"Dup Test\",
                \"email\": \"dup@test.it\"
            },
            \"indirizzi\": [
                {\"tipo_indirizzo_codice_interno\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice_interno\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ]
        }"
    check "CF duplicato → errore 409" "409"
else
    log_info "Skipped — nessun indirizzo"
fi
ERRCODE=$(json_get "$LAST_BODY" ".error.code")
log_info "Codice errore: $ERRCODE"

# Scopo: un CF valido e nuovo, dal servizio genera-cf (nome diverso a ogni uso).
genera_cf_smoke() {
    local nome="$1"
    do_curl POST "/api/v1/anagrafiche/soggetti/genera-cf/" \
        "{\"cognome\":\"SmokeTest\",\"nome\":\"${nome}\",\"data_nascita\":\"${SMOKE_BDATE}\",\"sesso\":\"M\",\"comune_nascita_id\":${CORRIDONIA_ID}}"
    json_get "$LAST_BODY" ".data.codice_fiscale"
}

# --- 15. Privato senza sesso: lo rifiuta il guard del DB ---
echo ""
echo "-- 15. Crea privato senza sesso --"
if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    CF_SENZA=$(genera_cf_smoke "Senzasesso")
    do_curl POST "/api/v1/anagrafiche/soggetti/" \
        "{
            \"tipo_soggetto_dettaglio_id\": ${TIPO_PRIVATO_ID},
            \"cognome\": \"SmokeTest\",
            \"nome\": \"Senzasesso\",
            \"codice_fiscale\": \"${CF_SENZA}\",
            \"contatto\": {\"tipo_contatto_id\": ${TIPO_CONTATTO_ID}, \"nominativo\": \"SmokeTest Senzasesso\", \"email\": \"smoke${SMOKE_TS}ss@test.it\"},
            \"indirizzi\": [
                {\"tipo_indirizzo_codice_interno\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice_interno\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ]
        }"
    if check "Privato senza sesso → 400" "400"; then
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        CAMPI=$(json_get "$LAST_BODY" ".error.fields")
        if [[ "$ERRCODE" == "E_SESSO_OBBLIGATORIO" && "$CAMPI" == *sesso* ]]; then
            log_ok "Codice E_SESSO_OBBLIGATORIO col campo sesso"
        else
            log_fail "Atteso E_SESSO_OBBLIGATORIO col campo sesso — ricevuto $ERRCODE, campi $CAMPI"
        fi
    fi
else
    log_info "Skipped — nessun indirizzo"
fi

# --- 16. Ditta individuale: nasce DI, con la P.IVA e senza sesso ---
echo ""
echo "-- 16. Crea ditta individuale --"
do_curl GET "/api/v1/core/lookup/tipi-soggetto-dettaglio/"
DI_ID=$(echo "$LAST_BODY" | python3 -c "
import sys, json
r = json.load(sys.stdin)['data']['results']
print(next((t['id'] for t in r if t['codice_interno'] == 'DI'), ''))" 2>/dev/null)
# P.IVA valida e nuova: 7 cifre dal timestamp + ufficio 001 + cifra di controllo.
SMOKE_PIVA=$(python3 -c "
b = '%07d001' % ($SMOKE_TS % 10000000)
s = sum(int(c) if i % 2 == 0 else (2 * int(c)) // 10 + (2 * int(c)) % 10 for i, c in enumerate(b))
print(b + str((10 - s % 10) % 10))")
if [[ -n "$IND_DET_ID" && -n "$DI_ID" ]]; then
    CF_DI=$(genera_cf_smoke "Ditta")
    do_curl POST "/api/v1/anagrafiche/soggetti/" \
        "{
            \"tipo_soggetto_dettaglio_id\": ${DI_ID},
            \"cognome\": \"SmokeTest\",
            \"nome\": \"Ditta\",
            \"codice_fiscale\": \"${CF_DI}\",
            \"partita_iva\": \"${SMOKE_PIVA}\",
            \"contatto\": {\"tipo_contatto_id\": ${TIPO_CONTATTO_ID}, \"nominativo\": \"SmokeTest Ditta\", \"email\": \"smoke${SMOKE_TS}di@test.it\"},
            \"indirizzi\": [
                {\"tipo_indirizzo_codice_interno\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice_interno\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ],
            \"auto_clone\": true
        }"
    if check "Crea ditta individuale" "200" ".data.id"; then
        do_curl GET "/api/v1/anagrafiche/soggetti/${EXTRACTED}/"
        TERNA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(d['tipo_soggetto_dettaglio_id'], d['partita_iva'], d['sesso'])" 2>/dev/null)
        if [[ "$TERNA" == "${DI_ID} ${SMOKE_PIVA} None" ]]; then
            log_ok "Nata DI, con la P.IVA, sesso NULL"
        else
            log_fail "Attesi tipo ${DI_ID}, P.IVA ${SMOKE_PIVA}, sesso NULL — ricevuto: $TERNA"
        fi
    fi
else
    log_info "Skipped — nessun indirizzo o tipo DI assente"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
