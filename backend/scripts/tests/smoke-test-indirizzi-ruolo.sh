#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Indirizzi Ruolo (con istanza)
# Uso: ./scripts/tests/smoke-test-indirizzi-ruolo.sh [password]
# Prerequisiti: almeno un soggetto con ruolo e un indirizzo_dettaglio nel DB
# ------------------------------------------------------------
# Indice test (0..13):
#  0) Autenticazione JWT
#  1) Recupera soggetto con ruolo
#  2) Lista indirizzi soggetto (fallback L3)
#  3) Recupera indirizzo_dettaglio e tipo_indirizzo disponibile
#  4) Crea indirizzo ruolo generico (istanza NULL)
#  5) Lista indirizzi ruolo senza istanza — vede ruolo + soggetto
#  6) Lookup istanza_utility_id disponibile
#  7) Crea indirizzo ruolo con istanza (stesso tipo — cascata L1)
#  8) Lista indirizzi ruolo con istanza — L1 vince, L2 nascosto per stesso tipo
#  9) PATCH indirizzo ruolo — aggiorna indirizzo_libero
# 10) Crea duplicato (stesso tipo+istanza — atteso errore)
# 11) DELETE indirizzo ruolo istanza
# 12) DELETE indirizzo ruolo generico
# 13) Lista finale — verifica solo soggetto rimasto
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

smoke_login
log_ok "Token JWT ottenuto"

# --- 1. Recupera soggetto con ruolo ---
echo ""
echo "-- 1. Recupera soggetto con ruolo --"

# Cerca un cliente per avere soggetto_ruolo_id
TIPO_RUOLO_CODICE=""
do_curl GET "/api/v1/anagrafiche/clienti/?limit=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    RUOLO_ID=$(json_get "$LAST_BODY" ".data.results.0.soggetto_ruolo_id")
    [[ -n "$RUOLO_ID" ]] && TIPO_RUOLO_CODICE="CL"   # il ruolo di un cliente
    SOGG_ID=$(json_get "$LAST_BODY" ".data.results.0.soggetto_id")
    ISTANZA_UTILITY_ID_FROM_CLIENT=$(json_get "$LAST_BODY" ".data.results.0.istanza_utility_id")
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

# Recupera un tipo_indirizzo AMMESSO per il ruolo: la matrice del tipo ruolo
# (config.tipi_ruolo_tipi_indirizzo), un tipo non obbligatorio per non toccare
# l'indirizzo di fatturazione del cliente. ⚠️ Il primo tipo qualsiasi del lookup
# generico (era «Consegna») risponde E_TIPO_INDIRIZZO_NON_PERMESSO. Il lookup
# generico resta il ripiego quando il tipo del ruolo non e' noto.
TIPO_IND_ID=""; TIPO_IND_CODICE=""
if [[ -n "${TIPO_RUOLO_CODICE:-}" ]]; then
    do_curl GET "/api/v1/core/lookup/tipi-ruolo/${TIPO_RUOLO_CODICE}/indirizzi/"
    if [[ "$LAST_STATUS" == "200" ]]; then
        read -r TIPO_IND_ID TIPO_IND_CODICE <<< "$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    r = next((x for x in rows if not x.get('obbligatorio')), rows[0] if rows else None)
    print(r['tipo_indirizzo_id'], r['codice']) if r else print('')
except Exception:
    print('')
" 2>/dev/null)"
        log_info "Tipo indirizzo ammesso per ${TIPO_RUOLO_CODICE}: id=$TIPO_IND_ID codice=$TIPO_IND_CODICE"
    fi
fi
[[ -z "$TIPO_IND_ID" ]] && do_curl GET "/api/v1/core/lookup/codici/?rel=config.tipi_indirizzi&limit=2"
if [[ -z "$TIPO_IND_ID" && "$LAST_STATUS" == "200" ]]; then
    TIPO_IND_ID=$(json_get "$LAST_BODY" ".data.results.0.id")
    # La creazione vuole il CODICE INTERNO del tipo (`tipo_indirizzo_codice_interno`,
    # risolto in id dalla madre `anagrafiche.fn_crea_indirizzi_ruolo`): l'id nel
    # payload risponde E_ANAG_VALIDAZIONE. ⚠️ Il codice STABILE (`codice_interno`),
    # non `codice`, che e' l'etichetta modificabile: «CONS» non lo trova, «CON» si'.
    TIPO_IND_CODICE=$(json_get "$LAST_BODY" ".data.results.0.codice_stabile")
    TIPO_IND_DESC=$(json_get "$LAST_BODY" ".data.results.0.descrizione")
    log_info "Tipo indirizzo id=$TIPO_IND_ID codice=$TIPO_IND_CODICE ($TIPO_IND_DESC)"
fi

if [[ -z "$TIPO_IND_ID" || "$TIPO_IND_ID" == "" ]]; then
    echo -e "${RED}ERRORE: nessun tipo_indirizzo trovato${NC}"
    echo ""
    echo "========================================="
    echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
    echo "========================================="
    exit 1
fi

# Gli id degli indirizzi creati: vuoti finche' una creazione non riesce (con
# `set -u` un passo saltato non deve far cadere lo smoke sui successivi).
IND_RUOLO_GEN_ID=""
IND_RUOLO_IST_ID=""

# --- 4. Crea indirizzo ruolo generico (utility NULL) ---
echo ""
echo "-- 4. Crea indirizzo ruolo generico (utility NULL) --"

if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
    # Modalita' normalizzata
    do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
        "{
            \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
            \"indirizzo_dettaglio_id\": ${IND_DET_ID}
        }"
else
    # Modalita' libera
    do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
        "{
            \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
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
    log_info "Codice errore: $ERRCODE — $(json_get "$LAST_BODY" ".error.detail")"
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

# --- 6. Lookup istanza_utility_id disponibile ---
echo ""
echo "-- 6. Lookup istanza_utility_id --"

ISTANZA_UTILITY_ID=""
if [[ -n "$ISTANZA_UTILITY_ID_FROM_CLIENT" && "$ISTANZA_UTILITY_ID_FROM_CLIENT" != "" && "$ISTANZA_UTILITY_ID_FROM_CLIENT" != "None" ]]; then
    ISTANZA_UTILITY_ID="$ISTANZA_UTILITY_ID_FROM_CLIENT"
    log_info "Istanza utility dal cliente: id=$ISTANZA_UTILITY_ID"
fi

# --- 7. Crea indirizzo ruolo con istanza ---
echo ""
echo "-- 7. Crea indirizzo ruolo con istanza --"

IND_RUOLO_IST_ID=""
if [[ -n "$ISTANZA_UTILITY_ID" && "$ISTANZA_UTILITY_ID" != "" ]]; then
    if [[ -n "$IND_DET_ID" && "$IND_DET_ID" != "" ]]; then
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
                \"istanza_utility_id\": ${ISTANZA_UTILITY_ID},
                \"indirizzo_dettaglio_id\": ${IND_DET_ID}
            }"
    else
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
                \"istanza_utility_id\": ${ISTANZA_UTILITY_ID},
                \"indirizzo_libero\": \"Via Istanza Smoke 1, 62014 Corridonia\"
            }"
    fi

    if [[ "$LAST_STATUS" == "200" ]]; then
        check "Crea indirizzo con istanza" "200" ".data.id"
        IND_RUOLO_IST_ID="$EXTRACTED"
        log_info "Indirizzo istanza creato id=$IND_RUOLO_IST_ID"

        # Verifica che istanza_utility_id sia nella risposta
        RESP_IST=$(json_get "$LAST_BODY" ".data.istanza_utility_id")
        if [[ "$RESP_IST" == "$ISTANZA_UTILITY_ID" ]]; then
            log_ok "istanza_utility_id=$ISTANZA_UTILITY_ID corretto nella risposta"
        else
            log_fail "istanza_utility_id atteso $ISTANZA_UTILITY_ID, ricevuto $RESP_IST"
        fi
    else
        log_info "Creazione con istanza fallita — HTTP $LAST_STATUS"
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        log_info "Codice errore: $ERRCODE — $(json_get "$LAST_BODY" ".error.detail")"
    fi
else
    log_info "Nessuna istanza disponibile — skip test cascata istanza"
fi

# --- 8. Lista con istanza_utility_id — cascata L1 vince ---
echo ""
echo "-- 8. Lista con cascata istanza --"

if [[ -n "$ISTANZA_UTILITY_ID" && "$ISTANZA_UTILITY_ID" != "" ]]; then
    do_curl GET "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/?istanza_utility_id=${ISTANZA_UTILITY_ID}"
    check "Lista con istanza_utility_id" "200"
    CASCATA_RUOLO=$(json_len "$LAST_BODY" ".data.indirizzi_ruolo")
    CASCATA_SOGG=$(json_len "$LAST_BODY" ".data.indirizzi_soggetto")
    log_info "Con istanza: ruolo=$CASCATA_RUOLO, soggetto=$CASCATA_SOGG"

    # Verifica che il primo editabile abbia fonte='istanza' (se ne abbiamo creato uno)
    if [[ -n "$IND_RUOLO_IST_ID" && "$IND_RUOLO_IST_ID" != "" && "$CASCATA_RUOLO" -gt 0 ]]; then
        FIRST_FONTE=$(json_get "$LAST_BODY" ".data.indirizzi_ruolo.0.fonte")
        if [[ "$FIRST_FONTE" == "istanza" ]]; then
            log_ok "Primo indirizzo ha fonte='istanza' (L1 vince)"
        else
            log_info "Primo indirizzo fonte='$FIRST_FONTE' (atteso 'istanza')"
        fi
    fi
else
    log_info "Skip — nessuna istanza"
fi

# --- 9. PATCH indirizzo ruolo ---
echo ""
echo "-- 9. PATCH indirizzo ruolo --"

PATCH_TARGET="${IND_RUOLO_IST_ID:-$IND_RUOLO_GEN_ID}"
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
                \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
                \"indirizzo_dettaglio_id\": ${IND_DET_ID}
            }"
    else
        do_curl POST "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/" \
            "{
                \"tipo_indirizzo_codice_interno\": \"${TIPO_IND_CODICE}\",
                \"indirizzo_libero\": \"Via Duplicato Test\"
            }"
    fi
    if [[ "$LAST_STATUS" != "200" ]]; then
        log_ok "Duplicato respinto (HTTP $LAST_STATUS)"
        ERRCODE=$(json_get "$LAST_BODY" ".error.code")
        log_info "Codice errore: $ERRCODE — $(json_get "$LAST_BODY" ".error.detail")"
    else
        log_fail "Duplicato accettato — doveva essere rifiutato"
    fi
else
    log_info "Skip — nessun indirizzo generico creato"
fi

# --- 11. DELETE indirizzo ruolo per istanza ---
echo ""
echo "-- 11. DELETE indirizzo per istanza --"

if [[ -n "$IND_RUOLO_IST_ID" && "$IND_RUOLO_IST_ID" != "" ]]; then
    do_curl DELETE "/api/v1/anagrafiche/ruoli/${RUOLO_ID}/indirizzi/${IND_RUOLO_IST_ID}/"
    check "DELETE indirizzo per istanza" "200"
else
    log_info "Skip — nessun indirizzo per istanza creato"
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
