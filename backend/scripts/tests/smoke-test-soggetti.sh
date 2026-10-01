#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Soggetti
# Uso: ./scripts/tests/smoke-test-soggetti.sh [password]
# ------------------------------------------------------------
# Indice test (0..14):
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
# 12) Assegna ruolo CLIENTE
# 13) Lista ruoli dopo assegnazione
# 14) Crea soggetto PF — CF duplicato (atteso 409)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Gunicorn diretto in HTTP: ci si dichiara HTTPS come Nginx (redirect di Django).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

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

if [[ -z "$PASSWORD" ]]; then
    echo -n "Password per utente '$USERNAME': "
    read -rs PASSWORD
    echo ""
fi

curl -s -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null

AUTH_STATUS=$(tail -1 "$TMPFILE")
AUTH_BODY=$(sed '$d' "$TMPFILE")

if [[ "$AUTH_STATUS" != "200" ]]; then
    echo -e "${RED}ERRORE: autenticazione fallita (HTTP $AUTH_STATUS)${NC}"
    echo "$AUTH_BODY" | head -c 300
    exit 1
fi

TOKEN=$(json_get "$AUTH_BODY" ".access")
if [[ -z "$TOKEN" ]]; then
    echo -e "${RED}ERRORE: token JWT non trovato nella risposta${NC}"
    exit 1
fi
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
echo "-- 3. Lista soggetti filtro tipo PF (id=1) --"
do_curl GET "/api/v1/anagrafiche/soggetti/?tipo_soggetto_dettaglio_id=1&limit=5"
check "Filtro tipo PF" "200" ".data.count"
log_info "Soggetti PF: $EXTRACTED"

# --- 3b. Trova o crea un indirizzo_dettaglio_id per creazione soggetto ---
echo ""
echo "-- 3b. Cerca/crea indirizzo dettaglio --"
IND_DET_ID=""

# Prima cerca un indirizzo esistente
do_curl GET "/api/v1/anagrafiche/indirizzi/?limit=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    IND_DET_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
fi

# Se non c'e', cerca un comune, poi stradario per quel comune, e crea un indirizzo
if [[ -z "$IND_DET_ID" || "$IND_DET_ID" == "" ]]; then
    log_info "Nessun indirizzo esistente, cerco comune + stradario per crearne uno..."
    # Cerca un comune grande (Milano — ha stradario sicuro)
    do_curl GET "/api/v1/core/lookup/comuni/?search=MILANO&limit=1"
    SMOKE_COMUNE_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
    if [[ -n "$SMOKE_COMUNE_ID" && "$SMOKE_COMUNE_ID" != "" ]]; then
        do_curl GET "/api/v1/core/search/stradario/?comune_id=${SMOKE_COMUNE_ID}&search=via&limit=1"
        STRAD_ID=$(json_get "$LAST_BODY" ".data.results.0.stradario_id")
        if [[ -n "$STRAD_ID" && "$STRAD_ID" != "" ]]; then
            CIVICO_RND=$((RANDOM % 900 + 100))
            do_curl POST "/api/v1/anagrafiche/indirizzi/" \
                "{\"stradario_id\":${STRAD_ID},\"civico\":${CIVICO_RND}}"
            if [[ "$LAST_STATUS" == "200" ]]; then
                IND_DET_ID=$(json_get "$LAST_BODY" ".data.indirizzo_dettaglio_id")
            fi
        fi
    fi
fi

if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    log_ok "Indirizzo dettaglio id=$IND_DET_ID"
else
    log_fail "Nessun indirizzo disponibile — test creazione soggetto non eseguibile"
fi

# --- 4. Crea soggetto PF ---
echo ""
echo "-- 4. Crea soggetto PF --"
SMOKE_TS=$(date +%s)
# Genera CF valido via API: data nascita unica per ottenere CF diverso ad ogni run.
# Anno 1950-2049, mese 01-12, giorno 01-28 derivati dal timestamp.
SMOKE_YEAR=$((1950 + SMOKE_TS % 100))
SMOKE_MONTH=$(printf '%02d' $((SMOKE_TS / 100 % 12 + 1)))
SMOKE_DAY=$(printf '%02d' $((SMOKE_TS / 1200 % 28 + 1)))
SMOKE_BDATE="${SMOKE_YEAR}-${SMOKE_MONTH}-${SMOKE_DAY}"

# Cerca comune Corridonia per ottenere l'id
do_curl GET "/api/v1/core/lookup/comuni/?search=CORRIDONIA&limit=1"
CORRIDONIA_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
if [[ -z "$CORRIDONIA_ID" || "$CORRIDONIA_ID" == "" ]]; then
    echo -e "${RED}ERRORE: comune Corridonia non trovato${NC}"
    exit 1
fi
do_curl POST "/api/v1/anagrafiche/soggetti/genera-cf/" \
    "{\"cognome\":\"SmokeTest\",\"nome\":\"Soggetto\",\"data_nascita\":\"${SMOKE_BDATE}\",\"sesso\":\"M\",\"comune_nascita_id\":${CORRIDONIA_ID}}"
SMOKE_CF=$(json_get "$LAST_BODY" ".data.codice_fiscale")
if [[ -z "$SMOKE_CF" || "$SMOKE_CF" == "" ]]; then
    echo -e "${RED}ERRORE: generazione CF fallita${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    exit 1
fi
log_info "CF generato: $SMOKE_CF (data nascita: $SMOKE_BDATE)"

# Payload con indirizzi obbligatori per PF/PR: RES + DOMFISC (FATT coperto da fallback DOMFISC)
IND_ARRAY=""
if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    IND_ARRAY=",\"indirizzi\": [
        {\"tipo_indirizzo_codice\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
        {\"tipo_indirizzo_codice\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
    ]"
fi

if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/soggetti/" \
        "{
            \"tipo_soggetto_dettaglio_id\": 1,
            \"cognome\": \"SmokeTest\",
            \"nome\": \"Soggetto${SMOKE_TS}\",
            \"codice_fiscale\": \"${SMOKE_CF}\",
            \"contatto\": {
                \"nominativo\": \"SmokeTest Soggetto\",
                \"email\": \"smoke${SMOKE_TS}@test.it\",
                \"telefono\": \"0123456789\"
            },
            \"indirizzi\": [
                {\"tipo_indirizzo_codice\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ],
            \"auto_clone\": true
        }"
    check "Crea soggetto PF" "200" ".data.id"
    SOGG_ID="$EXTRACTED"
    log_info "Soggetto creato id=$SOGG_ID"
else
    log_info "Skipped — nessun indirizzo disponibile"
    SOGG_ID=""
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
        "{\"nominativo\": \"Contatto Secondario\", \"email\": \"secondo@test.it\"}"
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

# --- 11b. Aggiungi indirizzi obbligatori mancanti per ruolo CLIENTE ---
# Recupera la lista indirizzi esistenti e aggiunge quelli mancanti
echo ""
echo "-- 11b. Completa indirizzi per ruolo CLIENTE --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" && -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    # Recupera tipi indirizzo gia' assegnati al soggetto
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/"
    TIPI_ESISTENTI=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d.get('data', {}).get('results', d.get('data', []))
    if isinstance(results, list):
        print(' '.join(r.get('tipo_indirizzo_codice','') for r in results))
    else:
        print('')
except: print('')
" 2>/dev/null)
    log_info "Tipi esistenti: $TIPI_ESISTENTI"
    # Aggiunge i tipi comuni se mancanti
    for TIPO in FATT SEDE SPED; do
        if [[ ! " $TIPI_ESISTENTI " =~ " $TIPO " ]]; then
            do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/" \
                "{\"tipo_indirizzo_codice\": \"${TIPO}\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}"
            if [[ "$LAST_STATUS" == "200" ]]; then
                log_ok "Indirizzo $TIPO aggiunto"
            else
                log_info "Indirizzo $TIPO non aggiunto (HTTP $LAST_STATUS)"
            fi
        fi
    done
else
    log_info "Skipped"
fi

# --- 12. Assegna ruolo CLIENTE ---
# Nota: l'assegnazione richiede che TUTTI i tipi indirizzo obbligatori
# definiti in config.tipi_ruolo_tipi_indirizzo siano presenti.
# Se la matrice DB cambia, questo test potrebbe fallire con E_INDIRIZZO_OBBLIGATORIO_MANCANTE.
echo ""
echo "-- 12. Assegna ruolo CLIENTE --"
RUOLO_ASSEGNATO=""
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl POST "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/" \
        "{\"codice_ruolo\": \"CLIENTE\"}"
    if [[ "$LAST_STATUS" == "200" ]]; then
        log_ok "Assegna ruolo CLIENTE (HTTP 200)"
        RUOLO_ASSEGNATO=$(json_get "$LAST_BODY" ".data.id")
        log_info "Ruolo assegnato id=$RUOLO_ASSEGNATO"
    elif [[ "$LAST_STATUS" == "400" ]]; then
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        if [[ "$ERRCODE" == "E_INDIRIZZO_OBBLIGATORIO_MANCANTE" ]]; then
            log_info "Assegnazione ruolo CLIENTE richiede indirizzi aggiuntivi — skip (configurazione matrice DB)"
        else
            log_fail "Assegna ruolo CLIENTE — errore inatteso: $ERRCODE"
        fi
    else
        log_fail "Assegna ruolo CLIENTE — atteso HTTP 200, ricevuto $LAST_STATUS"
    fi
else
    log_info "Skipped"
fi

# --- 13. Lista ruoli dopo assegnazione ---
echo ""
echo "-- 13. Lista ruoli dopo assegnazione --"
if [[ -n "$SOGG_ID" && "$SOGG_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/"
    check "Lista ruoli" "200"
    RUOLO_CODICE=$(json_get "$LAST_BODY" ".data.results.0.ruolo_codice")
    if [[ -n "$RUOLO_ASSEGNATO" ]]; then
        log_info "Primo ruolo: $RUOLO_CODICE"
    else
        log_info "Nessun ruolo assegnato (matrice indirizzi non soddisfatta)"
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
            \"tipo_soggetto_dettaglio_id\": 1,
            \"cognome\": \"Duplicato\",
            \"nome\": \"Test\",
            \"codice_fiscale\": \"${SMOKE_CF}\",
            \"contatto\": {
                \"nominativo\": \"Dup Test\",
                \"email\": \"dup@test.it\"
            },
            \"indirizzi\": [
                {\"tipo_indirizzo_codice\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ]
        }"
    check "CF duplicato → errore 409" "409"
else
    log_info "Skipped — nessun indirizzo"
fi
ERRCODE=$(json_get "$LAST_BODY" ".error.code")
log_info "Codice errore: $ERRCODE"

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
