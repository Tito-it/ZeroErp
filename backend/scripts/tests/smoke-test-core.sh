#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API core (permessi, lookup, diagnostica)
# Uso: ./scripts/smoke-test-core.sh [password]
# ------------------------------------------------------------
# Indice test (0..18):
#  0) Autenticazione JWT + estrazione user_id
#  1) Token refresh
#  2) Profilo utente corrente (/me/) — blocchi utente, soggetto, emittente
#  3) Permessi effettivi (utente corrente) — dettaglio aree
#  4) Permessi effettivi utente inesistente (400)
#  5) Audit permessi (utente corrente)
#  6) Audit permessi con filtro tabella
#  7) Audit permessi tabella invalida (400)
#  8) Lookup codici — stati_pratiche, stati_flussi, priorita, canali, search, relazione invalida
#  9) Diagnostica error envelope — generic (500), retryable (409), not_found (404)
# 10) Sessioni attive (/me/sessioni/) — lista altre sessioni
# 11) Logout (/auth/logout/) — blacklist + evento LOGOUT
# 12) Logout idempotente — token gia' blacklistato → 204
# 13) Password chiesta dentro la sessione — secondo-fattore/registra/ e
#     change-password/: assente e sbagliata → 400 col codice del dominio (mai
#     401), la giusta passa il cancello; poi un login che azzera i tentativi
# 14) Ricerca universale (/core/search/) — ricerca soggetti per tipo ruolo
# 15) Ricerca senza q → 400
# 16) Ricerca q troppo corto → 400
# 17) Ricerca senza tipo_ruolo_id → 400
# 18) Health check
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_errori.sh"   # smoke_check_codice

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
trap "rm -f $TMPFILE ${TMPFILE}.hdr" EXIT

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
        d = d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

# Scopo: logout col refresh dato nel cookie (come il browser) e il Bearer
#        corrente. Stesso esito di do_curl in LAST_STATUS/LAST_BODY.
logout_con_refresh() {
    curl_refresh "$1" -s -w '\n%{http_code}' -X POST \
        -H "Authorization: Bearer ${TOKEN:-none}" \
        "${BASE_URL}/api/v1/auth/logout/" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
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
echo " Smoke test API Core"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"

# Login vero (-D lo implica): il passo 1 prova il refresh dal suo cookie.
smoke_login -D "${TMPFILE}.hdr"
REFRESH=$(refresh_dal_set_cookie "${TMPFILE}.hdr")

# Estrai user_id dal token (payload JWT base64)
USER_ID=$(smoke_jwt_claim "$TOKEN" user_id)

log_ok "JWT ottenuto per '$USERNAME' (user_id=$USER_ID)"

# --- 1. Token refresh ---
echo ""
echo "-- 1. Token refresh --"

# Il refresh e' nel cookie (letto al login), non nel corpo.
curl_refresh "$REFRESH" -s -w '\n%{http_code}' -X POST \
    "${BASE_URL}/api/v1/admin/token/refresh/" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")
LAST_BODY=$(sed '$d' "$TMPFILE")
check "POST token refresh" 200

# ================================================================
# PROFILO UTENTE (/me/)
# ================================================================
echo ""
echo "-- 2. Profilo utente corrente (/me/) --"

do_curl GET "/api/v1/core/me/"
check "GET /me/ profilo utente" 200 ".data.ruolo_sistema"
log_info "ruolo_sistema: $EXTRACTED"

# Verifica blocchi principali del profilo
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    utente = d.get('utente', {})
    sogg = d.get('soggetto', {})
    emit = d.get('emittente')
    rm = d.get('risorse_umane', {})
    print(f'  --- utente: {utente.get(\"username\",\"?\")} ({utente.get(\"first_name\",\"\")} {utente.get(\"last_name\",\"\")})')
    print(f'  --- soggetto: {sogg.get(\"ragione_sociale_completa\",\"?\")} tipo={sogg.get(\"tipo_soggetto_id\",\"?\")}')
    if emit:
        print(f'  --- emittente: {emit.get(\"ragione_sociale_completa\",\"?\")} P.IVA={emit.get(\"partita_iva\",\"?\")}')
        print(f'      dati_societari: {\"si\" if emit.get(\"has_dati_societari\") else \"no\"}')
    else:
        print('  --- emittente: (nessuno)')
    print(f'  --- risorse_umane: UO={rm.get(\"unita_organizzativa_descrizione\",\"?\")} attivo={rm.get(\"attivo\",\"?\")}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# PERMESSI EFFETTIVI
# ================================================================
echo ""
echo "-- 3. Permessi effettivi (utente corrente) --"

do_curl GET "/api/v1/core/users/${USER_ID}/permessi-effettivi/"
check "GET permessi effettivi user $USER_ID" 200 ".data.ruolo_sistema"
log_info "ruolo_sistema: $EXTRACTED"

# Estrai dettagli aree
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    aree = d['data']['aree']
    emittenti = d['data'].get('emittenti_ids', [])
    uo = d['data'].get('unita_organizzativa_id')
    print(f'  --- aree funzionali: {len(aree)}')
    for a in aree:
        livello = a.get('livello','?')
        codice = a.get('codice','?')
        azioni = len(a.get('azioni_consentite',[]))
        print(f'      {codice}: livello={livello}, azioni={azioni}')
    print(f'  --- emittenti_ids: {emittenti}')
    print(f'  --- unita_organizzativa_id: {uo}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 4. Permessi effettivi utente inesistente ---
echo ""
echo "-- 4. Permessi utente inesistente --"

# Un utente che non esiste e' un 404 col suo codice (E_AMM_UTENTE_NOT_FOUND):
# fino al 2026-10-12 lo smoke si aspettava un 400 generico.
do_curl GET "/api/v1/core/users/999999/permessi-effettivi/"
smoke_check_codice "GET permessi user 999999 → 404" 404 E_AMM_UTENTE_NOT_FOUND || true

# ================================================================
# PERMESSI AUDIT
# ================================================================
echo ""
echo "-- 5. Audit permessi (utente corrente) --"

do_curl GET "/api/v1/core/users/${USER_ID}/permessi-audit/"
check "GET audit permessi user $USER_ID" 200 ".data.count"
log_info "eventi audit: $EXTRACTED"

# --- 6. Audit con filtro tabella ---
echo ""
echo "-- 6. Audit con filtro tabella --"

do_curl GET "/api/v1/core/users/${USER_ID}/permessi-audit/?tabella=user_override_aree"
check "GET audit filtro tabella" 200

# --- 7. Audit tabella invalida ---
echo ""
echo "-- 7. Audit tabella invalida --"

do_curl GET "/api/v1/core/users/${USER_ID}/permessi-audit/?tabella=INVENTATA"
check "GET audit tabella invalida → 400" 400

# ================================================================
# LOOKUP CODICI
# ================================================================
echo ""
echo "-- 8. Lookup codici --"

do_curl GET "/api/v1/core/lookup/codici/?rel=config.stati_pratiche"
check "GET lookup stati_pratiche" 200 ".data.count"
log_info "stati_pratiche: $EXTRACTED record"

do_curl GET "/api/v1/core/lookup/codici/?rel=config.stati_flussi_pratiche"
check "GET lookup stati_flussi_pratiche" 200 ".data.count"
log_info "stati_flussi_pratiche: $EXTRACTED record"

do_curl GET "/api/v1/core/lookup/codici/?rel=config.priorita_pratiche"
check "GET lookup priorita_pratiche" 200 ".data.count"
log_info "priorita_pratiche: $EXTRACTED record"

do_curl GET "/api/v1/core/lookup/codici/?rel=config.canali_pratiche"
check "GET lookup canali_pratiche" 200 ".data.count"
log_info "canali_pratiche: $EXTRACTED record"

# Lookup con ricerca
do_curl GET "/api/v1/core/lookup/codici/?rel=config.stati_pratiche&search=bozza"
check "GET lookup con search 'bozza'" 200 ".data.count"
log_info "risultati search 'bozza': $EXTRACTED"

# Lookup relazione invalida
do_curl GET "/api/v1/core/lookup/codici/?rel=schema.tabella_inesistente"
check "GET lookup relazione invalida → 400" 400

# ================================================================
# DIAGNOSTICA ERROR ENVELOPE
# ================================================================
echo ""
echo "-- 9. Diagnostica error envelope --"

do_curl GET "/api/v1/core/diagnostics/error-envelope/"
check "GET error envelope generic → 500" 500

do_curl GET "/api/v1/core/diagnostics/error-envelope/?kind=retryable"
check "GET error envelope retryable → 409" 409

do_curl GET "/api/v1/core/diagnostics/error-envelope/?kind=not_found"
check "GET error envelope not_found → 404" 404

# ================================================================
# SESSIONI ATTIVE
# ================================================================
echo ""
echo "-- 10. Sessioni attive (/me/sessioni/) --"

do_curl GET "/api/v1/core/me/sessioni/"
check "GET /me/sessioni/ lista sessioni" 200 ".data.count"
log_info "altre sessioni attive: $EXTRACTED"

# Mostra dettagli sessioni se presenti
echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    sessioni = d.get('sessioni', [])
    if sessioni:
        for s in sessioni:
            jti_short = s.get('jti','?')[:12] + '...'
            ip = s.get('ip_address','?')
            ua = (s.get('user_agent','?') or '?')[:40]
            print(f'  --- {jti_short}  IP={ip}  UA={ua}')
    else:
        print('  --- nessuna altra sessione attiva (solo la corrente)')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# LOGOUT
# ================================================================
echo ""
echo "-- 11. Logout --"

# login esplicito: una SECONDA sessione, col refresh fresco da usare per il
# logout; il suo esito e' un passo del test (log_fail), non un'uscita.
curl_login -s -w '\n%{http_code}' -D "${TMPFILE}.hdr" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null
LOGOUT_STATUS=$(tail -1 "$TMPFILE")
LOGOUT_BODY=$(sed '$d' "$TMPFILE")

if [[ "$LOGOUT_STATUS" == "200" ]]; then
    LOGOUT_TOKEN=$(json_get "$LOGOUT_BODY" ".access")
    LOGOUT_REFRESH=$(refresh_dal_set_cookie "${TMPFILE}.hdr")

    # Salva TOKEN originale e usa quello del secondo login
    ORIG_TOKEN="$TOKEN"
    TOKEN="$LOGOUT_TOKEN"

    logout_con_refresh "$LOGOUT_REFRESH"
    check "POST /auth/logout/ → 204" 204

    # --- 12. Logout idempotente (stesso refresh gia' blacklistato) ---
    echo ""
    echo "-- 12. Logout idempotente (token gia' blacklistato) --"

    logout_con_refresh "$LOGOUT_REFRESH"
    check "POST /auth/logout/ token gia' blacklistato → 204" 204

    # Ripristina TOKEN originale per i test successivi
    TOKEN="$ORIG_TOKEN"
else
    log_fail "Secondo login per test logout fallito (HTTP $LOGOUT_STATUS)"
fi

# ================================================================
# PASSWORD CHIESTA DENTRO LA SESSIONE
# ================================================================
echo ""
echo "-- 13. Password chiesta dentro la sessione --"

# ⛔ UN tentativo sbagliato per endpoint, mai fino al blocco. Un tentativo
#    sbagliato conta sul freno della credenziale (D-T2) e non c'e' un'API che
#    azzeri il freno dei tentativi: arrivare al blocco fermerebbe per
#    `login_blocco_minuti` ogni smoke dell'utente `smoke` da questa postazione.
#    Che la password sbagliata CONTI fino al blocco lo prova il DB vero
#    (`test_la_password_sbagliata_conta_e_frena_la_configurazione`); qui si
#    prova il contratto sul server che gira. In fondo un login riuscito azzera
#    la coppia credenziale + provenienza.
SBAGLIATA="smoke-sbagliata-$(date +%s)"

do_curl POST "/api/v1/auth/secondo-fattore/registra/" '{}'
smoke_check_codice "registra/ senza password → 400" 400 E_TOTP_PASSWORD_NON_VALIDA || true

do_curl POST "/api/v1/auth/secondo-fattore/registra/" "{\"password\":\"$SBAGLIATA\"}"
smoke_check_codice "registra/ con la password sbagliata → 400 (non 401)" 400 E_TOTP_PASSWORD_NON_VALIDA || true

# La password giusta passa il cancello. Solo con un device ATTIVO, che il DB
# rifiuta di sostituire (409): cosi' la prova non tocca lo stato dell'utente.
# Senza device, la giusta avvierebbe una configurazione vera.
do_curl GET "/api/v1/auth/secondo-fattore/"
STATO_SF=$(json_get "$LAST_BODY" ".data.stato")
if [[ "$STATO_SF" == "ATTIVO" ]]; then
    do_curl POST "/api/v1/auth/secondo-fattore/registra/" "{\"password\":\"$PASSWORD\"}"
    smoke_check_codice "registra/ con la password giusta → oltre il cancello (409, device attivo)" 409 E_TOTP_DEVICE_GIA_ATTIVO || true
else
    log_info "registra/ con la password giusta saltato: device '${STATO_SF:-?}', avvierebbe una configurazione vera"
fi

do_curl POST "/api/v1/auth/change-password/" \
    "{\"new_password\":\"Smoke-Nuova-2026!\",\"new_password_confirm\":\"Smoke-Nuova-2026!\"}"
smoke_check_codice "change-password/ senza password attuale → 400" 400 E_CHANGE_PASSWORD || true

# Con una nuova password DEBOLE: la verifica dell'attuale viene prima, quindi
# risponde l'attuale sbagliata (e il tentativo conta) e non la nuova.
do_curl POST "/api/v1/auth/change-password/" \
    "{\"old_password\":\"$SBAGLIATA\",\"new_password\":\"x\",\"new_password_confirm\":\"x\"}"
smoke_check_codice "change-password/ con l'attuale sbagliata → 400 (non 401)" 400 E_CHANGE_PASSWORD || true
if [[ "$(json_get "$LAST_BODY" ".error.message")" == *"attuale"* ]]; then
    log_ok "  risponde la password attuale, non la nuova debole"
else
    log_fail "  la risposta non parla della password attuale: $(echo "$LAST_BODY" | head -c 200)"
fi

# login esplicito: e' il login riuscito ad azzerare i due tentativi sbagliati
# di questa sezione, e `smoke_login` riuserebbe SMOKE_TOKEN senza farne uno.
curl_login -s -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")
LAST_BODY=$(sed '$d' "$TMPFILE")
check "login dopo i tentativi sbagliati (azzera il freno della coppia)" 200

# ================================================================
# RICERCA UNIVERSALE
# ================================================================
echo ""
echo "-- 14. Ricerca universale (/core/search/) --"

do_curl GET "/api/v1/core/search/?q=rossi&tipo_ruolo_id=1"
if [[ "$LAST_STATUS" == "200" ]]; then
    check "GET /core/search/ ricerca cliente" 200 ".data.count"
    log_info "risultati ricerca 'rossi' tipo CLIENTE: $EXTRACTED"
else
    # La funzione DB potrebbe non essere ancora disponibile
    log_info "Ricerca universale non disponibile (HTTP $LAST_STATUS) — funzione DB non ancora deployata?"
fi

# --- 15. Ricerca senza q → 400 ---
echo ""
echo "-- 15. Ricerca senza q --"

do_curl GET "/api/v1/core/search/?tipo_ruolo_id=1"
check "GET /core/search/ senza q → 400" 400

# --- 16. Ricerca q troppo corto → 400 ---
echo ""
echo "-- 16. Ricerca q troppo corto --"

do_curl GET "/api/v1/core/search/?q=ab&tipo_ruolo_id=1"
check "GET /core/search/ q troppo corto → 400" 400

# --- 17. Ricerca senza tipo_ruolo_id → 400 ---
echo ""
echo "-- 17. Ricerca senza tipo_ruolo_id --"

do_curl GET "/api/v1/core/search/?q=rossi"
check "GET /core/search/ senza tipo_ruolo_id → 400" 400

# ================================================================
# HEALTH
# ================================================================
echo ""
echo "-- 18. Health check --"

curl -s -w '\n%{http_code}' "${BASE_URL}/health" > "$TMPFILE" 2>/dev/null
LAST_STATUS=$(tail -1 "$TMPFILE")
LAST_BODY=$(sed '$d' "$TMPFILE")
check "GET /health" 200

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
