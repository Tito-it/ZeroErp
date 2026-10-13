#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API pratiche
# Esegue il ciclo completo: autenticazione → pratica → flusso → lifecycle
# Uso: ./scripts/smoke-test-pratiche.sh [password]
# ------------------------------------------------------------
# Indice test (0..25):
#  0) Autenticazione JWT
#  1) Lista pratiche (con filtro emittente)
#  2) Creazione pratica
#  3) Dettaglio pratica + verifica display fields (v2)
#  4) Aggiornamento pratica (PATCH descrizione)
#  5) Cambio stato pratica BOZZA → APERTA
#  6) Giornale pratica
#  7) Creazione flusso
#  8) Lista flussi + verifica display fields flusso (v2)
#  9) Dettaglio flusso
# 10) Avvio flusso DA_ESEGUIRE → IN_CORSO
# 11) Completamento flusso IN_CORSO → COMPLETATO
# 12) Prerequisiti flusso
# 13) Canali flusso
# 14) Regole generazione
# 15) Pratiche generate
# 16) Giornale finale (conteggio eventi)
# 17) Test errori attesi — pratica/flusso inesistente (404), completa senza esito (400)
# 18) Ricerca pratiche con parametro search (v2)
# 19) Verifica codice pratica con prefisso PRA (v2)
# 20) Verifica campi contesto anagrafico nel dettaglio (v2)
# 21) Crea nota pratica (v2)
# 22) Lista note pratica (v2)
# 23) Aggiorna nota pratica (v2)
# 24) Elimina nota pratica (v2)
# 25) Lista allegati pratica — vuota (v2)
# 26) Coda lavoro operatore (v2.1)
# 27) Coda lavoro senza emittente → errore (v2.1)
# 28) Competenze flussi lista (v2.1)
# 29) Verifica data_apertura nel dettaglio (v2.1)
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_pratiche.sh"    # smoke_template_percorso

# --- Riferimenti DB (valori di dev) ---
PRIORITA_ID="${PRIORITA_ID:-1}"

# --- Colori output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
PRATICA_ID=""
FLUSSO_ID=""
LAST_STATUS=""
LAST_BODY=""
EXTRACTED=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

# Estrae un valore JSON con python3 (senza jq)
json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

# Wrapper curl: salva status e body separatamente
do_curl() {
    local method="$1" url="$2" data="${3:-}"
    local auth_header=""
    if [[ -n "${TOKEN:-}" ]]; then
        auth_header="-H Authorization: Bearer $TOKEN"
    fi

    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    elif [[ "$method" == "PATCH" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -X PATCH -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    elif [[ "$method" == "DELETE" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -X DELETE \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    fi

    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

# Verifica risposta HTTP + opzionalmente estrae un campo JSON
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
echo " Smoke test API Pratiche"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

smoke_login
log_ok "JWT ottenuto per '$USERNAME'"
# L'emittente della pratica: quello ATTIVO dell'operatore (BB _smoke_cliente.sh),
# mai un id scritto a mano (era 32: E_SCOPE_EMITTENTE se l'operatore lavora su
# un altro). Override: EMITTENTE_ID.
smoke_emittente_attivo
EMITTENTE_FISCALE_ID="$EMITTENTE_ATTIVO_ID"
if [[ -z "$EMITTENTE_FISCALE_ID" ]]; then
    echo -e "${RED}Setup fallito: l'operatore non ha un emittente attivo. Stop.${NC}"; exit 1
fi
log_info "emittente attivo = $EMITTENTE_FISCALE_ID"
# Il tipo di prestazione per CODICE (BB _smoke_pratiche.sh): PREVENTIVI e' il
# tipo con un percorso attivo. Fino al 2026-10-12 qui c'era un id cablato.
smoke_tipo_prestazione PREVENTIVI
if [[ -z "$TIPO_PRESTAZIONE_ID" ]]; then
    echo -e "${RED}Setup fallito: tipo di prestazione PREVENTIVI non trovato. Stop.${NC}"; exit 1
fi
log_info "tipo prestazione = $TIPO_PRESTAZIONE_ID"

# --- 1. Lista pratiche ---
echo ""
echo "-- 1. Lista pratiche --"

do_curl GET "/api/v1/pratiche/?emittente_fiscale_id=$EMITTENTE_FISCALE_ID"
check "GET lista pratiche" 200

# --- 2. Crea pratica ---
echo ""
echo "-- 2. Creazione pratica --"

do_curl POST "/api/v1/pratiche/" "{
    \"emittente_fiscale_id\": $EMITTENTE_FISCALE_ID,
    \"tipo_prestazione_id\": $TIPO_PRESTAZIONE_ID,
    \"priorita_id\": $PRIORITA_ID,
    \"descrizione\": \"Smoke test $(date +%Y%m%d-%H%M%S)\"
}"
check "POST crea pratica" 200 ".data.pratica_id" || true
PRATICA_ID="$EXTRACTED"

if [[ -z "$PRATICA_ID" || "$PRATICA_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere pratica_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "pratica_id = $PRATICA_ID"

# --- 3. Dettaglio pratica + display fields (v2) ---
echo ""
echo "-- 3. Dettaglio pratica --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/"
check "GET dettaglio pratica" 200 ".data.stato_codice_interno"
log_info "stato_codice_interno = $EXTRACTED"

# Verifica presenza display fields nel JSON
DISPLAY_CHECK=$(json_get "$LAST_BODY" ".data.tipo_prestazione_descrizione")
if [[ -n "$DISPLAY_CHECK" && "$DISPLAY_CHECK" != "null" ]]; then
    log_ok "Display fields presenti (tipo_prestazione_descrizione = $DISPLAY_CHECK)"
else
    log_fail "Display fields mancanti nel dettaglio pratica"
fi

# --- 4. Aggiorna pratica ---
echo ""
echo "-- 4. Aggiornamento pratica --"

do_curl PATCH "/api/v1/pratiche/${PRATICA_ID}/" '{"descrizione": "Smoke test aggiornato"}'
check "PATCH aggiorna pratica" 200

# --- 5. Cambio stato pratica BOZZA → APERTA ---
echo ""
echo "-- 5. Cambio stato pratica --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/stato/" '{"nuovo_stato": "APERTA"}'
check "POST stato BOZZA→APERTA" 200

# --- 6. Giornale pratica ---
echo ""
echo "-- 6. Giornale pratica --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/giornale/"
check "GET giornale pratica" 200 ".data.count"
log_info "eventi giornale: $EXTRACTED"

# --- 7. Crea flusso ---
echo ""
echo "-- 7. Creazione flusso --"

# Un flusso nasce SEMPRE da un template del percorso della pratica
# (`template_flusso_id` obbligatorio, E_FLUSSO_VALIDATION): il primo del percorso,
# dal BB _smoke_pratiche.sh. Fino al 2026-10-12 lo smoke lo creava senza.
smoke_template_percorso "$PRATICA_ID"
if [[ -z "$TEMPLATE_FLUSSO_ID" ]]; then
    echo -e "${RED}ERRORE: il percorso della pratica non ha template — interrompo${NC}"; exit 1
fi
log_info "template_flusso_id = $TEMPLATE_FLUSSO_ID"
do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" "{
    \"template_flusso_id\": ${TEMPLATE_FLUSSO_ID},
    \"meta\": {\"smoke\": true}
}"
check "POST crea flusso" 200 ".data.flusso_id" || true
FLUSSO_ID="$EXTRACTED"

if [[ -z "$FLUSSO_ID" || "$FLUSSO_ID" == "null" ]]; then
    echo -e "${RED}ERRORE: impossibile ottenere flusso_id — interrompo${NC}"
    echo "       Body: $(echo "$LAST_BODY" | head -c 500)"
    exit 1
fi
log_info "flusso_id = $FLUSSO_ID"

# --- 8. Lista flussi + display fields (v2) ---
echo ""
echo "-- 8. Lista flussi --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/"
check "GET lista flussi" 200

# Verifica display fields nel primo flusso (se presente)
FLUSSO_STATO=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    r = d['data']['results']
    print(r[0]['stato_codice_interno'] if r else 'EMPTY')
except Exception:
    print('PARSE_ERR')
" 2>/dev/null)
if [[ "$FLUSSO_STATO" != "PARSE_ERR" && "$FLUSSO_STATO" != "" ]]; then
    log_ok "Display fields flusso presenti (stato_codice_interno = $FLUSSO_STATO)"
else
    log_info "Nessun flusso per verifica display (OK se lista vuota)"
fi

# --- 9. Dettaglio flusso ---
echo ""
echo "-- 9. Dettaglio flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/"
check "GET dettaglio flusso" 200

# --- 10. Avvia flusso (DA_ESEGUIRE → IN_CORSO) ---
echo ""
echo "-- 10. Avvio flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "IN_CORSO"}'
check "POST stato DA_ESEGUIRE→IN_CORSO" 200

# --- 11. Completa flusso (IN_CORSO → COMPLETATO) ---
echo ""
echo "-- 11. Completamento flusso --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{
    "nuovo_stato": "COMPLETATO",
    "esito": "POSITIVO",
    "note_esito": "Smoke test OK"
}'
check "POST stato IN_CORSO→COMPLETATO" 200

# --- 12. Prerequisiti flusso ---
echo ""
echo "-- 12. Prerequisiti flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/prerequisiti/"
check "GET prerequisiti flusso" 200

# --- 13. Canali flusso ---
echo ""
echo "-- 13. Canali flusso --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/canali/"
check "GET canali flusso" 200

# --- 14. Regole generazione ---
echo ""
echo "-- 14. Regole generazione --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/regole-generazione/"
check "GET regole generazione" 200

# --- 15. Pratiche generate ---
echo ""
echo "-- 15. Pratiche generate --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/pratiche-generate/"
check "GET pratiche generate" 200

# --- 16. Giornale finale ---
echo ""
echo "-- 16. Giornale finale --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/giornale/"
check "GET giornale finale" 200 ".data.count"
log_info "eventi giornale totali: $EXTRACTED"

# --- 17. Test errori attesi ---
echo ""
echo "-- 17. Test errori attesi --"

do_curl GET "/api/v1/pratiche/999999/"
check "GET pratica inesistente → 404" 404

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/999999/"
check "GET flusso inesistente → 404" 404

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "COMPLETATO"}'
check "POST completa senza esito → 400" 400

# --- 18. Ricerca pratiche con search (v2) ---
echo ""
echo "-- 18. Ricerca con search --"

do_curl GET "/api/v1/pratiche/?emittente_fiscale_id=$EMITTENTE_FISCALE_ID&search=Smoke"
check "GET lista con search" 200

# --- 19. Verifica codice con prefisso PRA (v2) ---
echo ""
echo "-- 19. Verifica codice pratica --"

CODICE=$(json_get "$LAST_BODY" ".data.results")
do_curl GET "/api/v1/pratiche/${PRATICA_ID}/"
CODICE_PRATICA=$(json_get "$LAST_BODY" ".data.codice")
if [[ "$CODICE_PRATICA" == PRA-* ]]; then
    log_ok "Codice pratica con prefisso PRA ($CODICE_PRATICA)"
else
    log_fail "Codice pratica senza prefisso PRA atteso — ricevuto: $CODICE_PRATICA"
fi

# --- 20. Verifica campi contesto anagrafico (v2) ---
echo ""
echo "-- 20. Campi contesto anagrafico --"

# Verifica che i campi esistano nella risposta (anche se NULL per pratica interna)
HAS_RUOLO=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('soggetto_ruolo_id' in d.get('data', {}))
" 2>/dev/null)
if [[ "$HAS_RUOLO" == "True" ]]; then
    log_ok "Campo soggetto_ruolo_id presente nel dettaglio"
else
    log_fail "Campo soggetto_ruolo_id mancante nel dettaglio"
fi

HAS_ISTANZA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('istanza_utility_id' in d.get('data', {}))
" 2>/dev/null)
if [[ "$HAS_ISTANZA" == "True" ]]; then
    log_ok "Campo istanza_utility_id presente nel dettaglio"
else
    log_fail "Campo istanza_utility_id mancante nel dettaglio"
fi

# --- 21. Crea nota pratica (v2) ---
echo ""
echo "-- 21. Crea nota --"

do_curl POST "/api/v1/pratiche/${PRATICA_ID}/note/" '{"tipo_nota_codice": "GENERALE", "contenuto": "Nota smoke test"}'
check "POST crea nota" 200 ".data.nota_id" || true
NOTA_ID="$EXTRACTED"
log_info "nota_id = $NOTA_ID"

# --- 22. Lista note pratica (v2) ---
echo ""
echo "-- 22. Lista note --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/note/"
check "GET lista note" 200

# --- 23. Aggiorna nota pratica (v2) ---
echo ""
echo "-- 23. Aggiorna nota --"

if [[ -n "$NOTA_ID" && "$NOTA_ID" != "null" ]]; then
    do_curl PATCH "/api/v1/pratiche/${PRATICA_ID}/note/${NOTA_ID}/" '{"contenuto": "Nota aggiornata"}'
    check "PATCH aggiorna nota" 200
fi

# --- 24. Elimina nota pratica (v2) ---
echo ""
echo "-- 24. Elimina nota --"

if [[ -n "$NOTA_ID" && "$NOTA_ID" != "null" ]]; then
    do_curl DELETE "/api/v1/pratiche/${PRATICA_ID}/note/${NOTA_ID}/"
    check "DELETE elimina nota" 200
fi

# --- 25. Lista allegati — vuota (v2) ---
echo ""
echo "-- 25. Lista allegati --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/allegati/"
check "GET lista allegati (vuota)" 200

# --- 26. Coda lavoro operatore (v2.1) ---
echo ""
echo "-- 26. Coda lavoro --"

do_curl GET "/api/v1/pratiche/coda-lavoro/?emittente_fiscale_id=$EMITTENTE_FISCALE_ID"
check "GET coda lavoro" 200

# --- 27. Coda lavoro senza emittente → errore (v2.1) ---
echo ""
echo "-- 27. Coda lavoro senza emittente --"

do_curl GET "/api/v1/pratiche/coda-lavoro/"
check "GET coda lavoro senza emittente → 400" 400

# --- 28. Competenze flussi lista (v2.1) ---
echo ""
echo "-- 28. Competenze flussi --"

do_curl GET "/api/v1/pratiche/competenze-flussi/"
check "GET competenze flussi" 200

# --- 29. Verifica data_apertura nel dettaglio (v2.1) ---
echo ""
echo "-- 29. Verifica data_apertura --"

do_curl GET "/api/v1/pratiche/${PRATICA_ID}/"
HAS_DATA_APERTURA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('data_apertura' in d.get('data', {}))
" 2>/dev/null)
if [[ "$HAS_DATA_APERTURA" == "True" ]]; then
    log_ok "Campo data_apertura presente nel dettaglio"
else
    log_fail "Campo data_apertura mancante nel dettaglio"
fi

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
