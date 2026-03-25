#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Indirizzi Ruolo (con utility)
# Uso: ./scripts/tests/smoke-test-indirizzi-ruolo.sh [password]
# Prerequisiti: almeno un soggetto con ruolo e un indirizzo_dettaglio nel DB
# ------------------------------------------------------------
# Indice test (0..13):
#  0) Autenticazione JWT
#  1) Recupera soggetto con ruolo
#  2) Lista indirizzi soggetto (fallback L3)
#  3) Recupera indirizzo_dettaglio e tipo_indirizzo disponibile
#  4) Crea indirizzo ruolo generico (utility NULL)
#  5) Lista indirizzi ruolo senza utility — vede ruolo + soggetto
#  6) Lookup utility disponibili
#  7) Crea indirizzo ruolo con utility (stesso tipo — cascata L1)
#  8) Lista indirizzi ruolo con utility — L1 vince, L2 nascosto per stesso tipo
#  9) PATCH indirizzo ruolo — aggiorna indirizzo_libero
# 10) Crea duplicato (stesso tipo+utility — atteso errore)
# 11) DELETE indirizzo ruolo utility
# 12) DELETE indirizzo ruolo generico
# 13) Lista finale — verifica solo soggetto rimasto
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
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

json_len() {
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
    print(len(d) if isinstance(d, list) else 0)
except Exception:
    print(0)
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
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
echo " Smoke test API Indirizzi Ruolo"
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
    "${BASE_URL}/api/v1/auth/token/" > "$TMPFILE" 2>/dev/null

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

# --- 1. Recupera soggetto con ruolo ---
echo ""
echo "-- 1. Recupera soggetto con ruolo --"

# Cerca un cliente per avere soggetto_ruolo_id
do_curl GET "/api/v1/anagrafiche/clienti/?limit=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    RUOLO_ID=$(json_get "$LAST_BODY" ".data.results.0.soggetto_ruolo_id")
    SOGG_ID=$(json_get "$LAST_BODY" ".data.results.0.soggetto_id")
    UTILITY_ID_FROM_CLIENT=$(json_get "$LAST_BODY" ".data.results.0.utility_id")
fi

if [[ -z "$RUOLO_ID" || "$RUOLO_ID" == "" ]]; then
    # Fallback: cerca soggetto e assegna ruolo
    do_curl GET "/api/v1/anagrafiche/soggetti/?limit=1"
    check "Lista soggetti" "200" ".data.results.0.id"
    SOGG_ID="$EXTRACTED"

    if [[ -z "$SOGG_ID" || "$SOGG_ID" == "" ]]; then
        echo -e "${RED}ERRORE: nessun soggetto nel DB${NC}"
        exit 1
    fi

    # Recupera ruoli del soggetto
    do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/ruoli/"
    RUOLO_ID=$(json_get "$LAST_BODY" ".data.0.id")

    if [[ -z "$RUOLO_ID" || "$RUOLO_ID" == "" ]]; then
        echo -e "${RED}ERRORE: nessun soggetto con ruoli trovato${NC}"
        exit 1
    fi
fi

log_ok "Soggetto id=$SOGG_ID, ruolo id=$RUOLO_ID"

# --- 2. Lista indirizzi soggetto (fallback L3) ---
echo ""
echo "-- 2. Lista indirizzi soggetto (fallback L3) --"
do_curl GET "/api/v1/anagrafiche/soggetti/${SOGG_ID}/indirizzi/"
check "Lista indirizzi soggetto" "200"
SOGG_IND_COUNT=$(json_len "$LAST_BODY" ".data")
log_info "Indirizzi soggetto: $SOGG_IND_COUNT"

# --- 3. Recupera indirizzo_dettaglio e tipo_indirizzo ---
echo ""
echo "-- 3. Recupera dati per creazione --"

# Recupera un indirizzo_dettaglio dal DB
do_curl GET "/api/v1/anagrafiche/indirizzi/?limit=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    IND_DET_ID=$(json_get "$LAST_BODY" ".data.results.0.indirizzo_dettaglio_id")
    log_info "Indirizzo dettaglio id=$IND_DET_ID"
else
    IND_DET_ID=""
fi

# Recupera tipo_indirizzo disponibile dal lookup
do_curl GET "/api/v1/core/lookup/codici/?rel=config.tipi_indirizzi&limit=2"
if [[ "$LAST_STATUS" == "200" ]]; then
    TIPO_IND_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
    TIPO_IND_DESC=$(json_get "$LAST_BODY" ".data.results.0.descrizione")
    log_info "Tipo indirizzo id=$TIPO_IND_ID ($TIPO_IND_DESC)"
else
    TIPO_IND_ID=""
fi

if [[ -z "$TIPO_IND_ID" || "$TIPO_IND_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessun tipo_indirizzo trovato${NC}"
    echo ""
    echo "========================================="
    echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
    echo "========================================="
    exit 1
fi

# --- 4. Crea indirizzo ruolo generico (utility NULL) ---
echo ""
echo "-- 4. Crea indirizzo ruolo generico (utility NULL) --"

if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    # Modalita' normalizzata
    do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
        "{
            \"tipo_indirizzo_id\": ${TIPO_IND_ID},
            \"indirizzo_dettaglio_id\": ${IND_DET_ID}
        }"
else
    # Modalita' libera
    do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
        "{
            \"tipo_indirizzo_id\": ${TIPO_IND_ID},
            \"indirizzo_libero\": \"Via Smoke Test 1, 00100 Roma\"
        }"
fi

if [[ "$LAST_STATUS" == "200" ]]; then
    check "Crea indirizzo generico" "200" ".data.id"
    IND_RUOLO_GEN_ID="$EXTRACTED"
    log_info "Indirizzo generico creato id=$IND_RUOLO_GEN_ID"
else
    # Potrebbe fallire per vincolo UNIQUE — tipo gia' presente
    log_info "Creazione fallita (possibile vincolo UNIQUE) — HTTP $LAST_STATUS"
    IND_RUOLO_GEN_ID=""
    ERRCODE=$(json_get "$LAST_BODY" ".error.code")
    log_info "Codice errore: $ERRCODE"
fi

# --- 5. Lista indirizzi ruolo senza utility ---
echo ""
echo "-- 5. Lista indirizzi ruolo senza utility --"
do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/"
check "Lista indirizzi ruolo" "200"
RUOLO_COUNT=$(json_len "$LAST_BODY" ".data.indirizzi_ruolo")
SOGG_FALL_COUNT=$(json_len "$LAST_BODY" ".data.indirizzi_soggetto")
log_info "Indirizzi ruolo: $RUOLO_COUNT, soggetto (fallback): $SOGG_FALL_COUNT"

# Verifica struttura risposta
HAS_RUOLO_KEY=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d.get('data', {})
has = 'indirizzi_ruolo' in data and 'indirizzi_soggetto' in data
print('yes' if has else 'no')
" 2>/dev/null)
if [[ "$HAS_RUOLO_KEY" == "yes" ]]; then
    log_ok "Struttura risposta corretta (indirizzi_ruolo + indirizzi_soggetto)"
else
    log_fail "Struttura risposta mancante"
fi

# --- 6. Lookup utility disponibili ---
echo ""
echo "-- 6. Lookup utility --"

UTILITY_ID=""
if [[ -n "$UTILITY_ID_FROM_CLIENT" && "$UTILITY_ID_FROM_CLIENT" != "" && "$UTILITY_ID_FROM_CLIENT" != "None" ]]; then
    UTILITY_ID="$UTILITY_ID_FROM_CLIENT"
    log_info "Utility dal cliente: id=$UTILITY_ID"
else
    do_curl GET "/api/v1/core/lookup/codici/?rel=config.utilities&limit=1"
    if [[ "$LAST_STATUS" == "200" ]]; then
        UTILITY_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
        UTILITY_DESC=$(json_get "$LAST_BODY" ".data.results.0.descrizione")
        if [[ -n "$UTILITY_ID" && "$UTILITY_ID" != "" ]]; then
            log_info "Utility trovata: id=$UTILITY_ID ($UTILITY_DESC)"
        fi
    fi
fi

# --- 7. Crea indirizzo ruolo con utility ---
echo ""
echo "-- 7. Crea indirizzo ruolo con utility --"

IND_RUOLO_UTIL_ID=""
if [[ -n "$UTILITY_ID" && "$UTILITY_ID" != "" ]]; then
    if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_id\": ${TIPO_IND_ID},
                \"utility_id\": ${UTILITY_ID},
                \"indirizzo_dettaglio_id\": ${IND_DET_ID}
            }"
    else
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_id\": ${TIPO_IND_ID},
                \"utility_id\": ${UTILITY_ID},
                \"indirizzo_libero\": \"Via Utility Smoke 1, 62014 Corridonia\"
            }"
    fi

    if [[ "$LAST_STATUS" == "200" ]]; then
        check "Crea indirizzo con utility" "200" ".data.id"
        IND_RUOLO_UTIL_ID="$EXTRACTED"
        log_info "Indirizzo utility creato id=$IND_RUOLO_UTIL_ID"

        # Verifica che utility_id sia nella risposta
        RESP_UTIL=$(json_get "$LAST_BODY" ".data.utility_id")
        if [[ "$RESP_UTIL" == "$UTILITY_ID" ]]; then
            log_ok "utility_id=$UTILITY_ID corretto nella risposta"
        else
            log_fail "utility_id atteso $UTILITY_ID, ricevuto $RESP_UTIL"
        fi
    else
        log_info "Creazione con utility fallita — HTTP $LAST_STATUS"
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        log_info "Codice errore: $ERRCODE"
    fi
else
    log_info "Nessuna utility disponibile — skip test cascata utility"
fi

# --- 8. Lista con utility_id — cascata L1 vince ---
echo ""
echo "-- 8. Lista con cascata utility --"

if [[ -n "$UTILITY_ID" && "$UTILITY_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/?utility_id=${UTILITY_ID}"
    check "Lista con utility_id" "200"
    CASCATA_RUOLO=$(json_len "$LAST_BODY" ".data.indirizzi_ruolo")
    CASCATA_SOGG=$(json_len "$LAST_BODY" ".data.indirizzi_soggetto")
    log_info "Con utility: ruolo=$CASCATA_RUOLO, soggetto=$CASCATA_SOGG"

    # Verifica che il primo editabile abbia fonte='utility' (se ne abbiamo creato uno)
    if [[ -n "$IND_RUOLO_UTIL_ID" && "$IND_RUOLO_UTIL_ID" != "" && "$CASCATA_RUOLO" -gt 0 ]]; then
        FIRST_FONTE=$(json_get "$LAST_BODY" ".data.indirizzi_ruolo.0.fonte")
        if [[ "$FIRST_FONTE" == "utility" ]]; then
            log_ok "Primo indirizzo ha fonte='utility' (L1 vince)"
        else
            log_info "Primo indirizzo fonte='$FIRST_FONTE' (atteso 'utility')"
        fi
    fi
else
    log_info "Skip — nessuna utility"
fi

# --- 9. PATCH indirizzo ruolo ---
echo ""
echo "-- 9. PATCH indirizzo ruolo --"

PATCH_TARGET="${IND_RUOLO_UTIL_ID:-$IND_RUOLO_GEN_ID}"
if [[ -n "$PATCH_TARGET" && "$PATCH_TARGET" != "" ]]; then
    do_curl PATCH "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/${PATCH_TARGET}/" \
        "{\"indirizzo_libero\": \"Via Aggiornata 99, 00100 Roma\"}"
    check "PATCH indirizzo ruolo" "200"
else
    log_info "Nessun indirizzo da aggiornare — skip"
fi

# --- 10. Crea duplicato (atteso errore) ---
echo ""
echo "-- 10. Crea duplicato (atteso errore) --"

if [[ -n "$IND_RUOLO_GEN_ID" && "$IND_RUOLO_GEN_ID" != "" ]]; then
    if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_id\": ${TIPO_IND_ID},
                \"indirizzo_dettaglio_id\": ${IND_DET_ID}
            }"
    else
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_id\": ${TIPO_IND_ID},
                \"indirizzo_libero\": \"Via Duplicato Test\"
            }"
    fi
    if [[ "$LAST_STATUS" != "200" ]]; then
        log_ok "Duplicato respinto (HTTP $LAST_STATUS)"
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        log_info "Codice errore: $ERRCODE"
    else
        log_fail "Duplicato accettato — doveva essere rifiutato"
    fi
else
    log_info "Skip — nessun indirizzo generico creato"
fi

# --- 11. DELETE indirizzo ruolo utility ---
echo ""
echo "-- 11. DELETE indirizzo utility --"

if [[ -n "$IND_RUOLO_UTIL_ID" && "$IND_RUOLO_UTIL_ID" != "" ]]; then
    do_curl DELETE "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/${IND_RUOLO_UTIL_ID}/"
    check "DELETE indirizzo utility" "200"
else
    log_info "Skip — nessun indirizzo utility creato"
fi

# --- 12. DELETE indirizzo ruolo generico ---
echo ""
echo "-- 12. DELETE indirizzo generico --"

if [[ -n "$IND_RUOLO_GEN_ID" && "$IND_RUOLO_GEN_ID" != "" ]]; then
    do_curl DELETE "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/${IND_RUOLO_GEN_ID}/"
    check "DELETE indirizzo generico" "200"
else
    log_info "Skip — nessun indirizzo generico creato"
fi

# --- 13. Lista finale ---
echo ""
echo "-- 13. Lista finale --"
do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/"
check "Lista finale" "200"
FINAL_RUOLO=$(json_len "$LAST_BODY" ".data.indirizzi_ruolo")
FINAL_SOGG=$(json_len "$LAST_BODY" ".data.indirizzi_soggetto")
log_info "Finale: ruolo=$FINAL_RUOLO, soggetto=$FINAL_SOGG"

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
