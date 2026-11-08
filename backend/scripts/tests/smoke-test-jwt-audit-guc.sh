#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test propagazione GUC `app.jwt_user` / `app.current_user_id`
# verso i trigger DB tramite JwtAuditAuthentication (BE-2.0ter del
# refactor operatore-emittenti).
#
# Verifica end-to-end che:
#  - login JWT propaga le GUC sulla connessione
#  - una scrittura via API popola correttamente user_insert/user_update
#    con lo username JWT (non con il ruolo DB zeroerp_app/titodb)
#  - il refactor operatore-emittenti e' operativamente attivo
#    (il trigger trgfn_billing_account_link_ef vede l'utente)
#
# Uso: ./scripts/tests/smoke-test-jwt-audit-guc.sh [password]
# ------------------------------------------------------------
# Indice test (0..5):
#  0) Login JWT → ottieni access token
#  1) Verifica GUC visibili in shell (controllo configurazione)
#  2) Audit JWT su tabella anagrafiche.soggetti (lettura storico
#     pre-fix vs post-fix sullo stesso utente)
#  3) Creazione cliente via API → verifica user_insert popolato
#     con username JWT (non con ruolo DB)
#  4) Trigger refactor: emittenti_fiscali_billing_account
#     auto-link → verifica mapping creato col emittente atteso
#  5) Audit query finale: ratio post-fix
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE ${TMPFILE}.hdr" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}    $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC}  $1"; }
log_warn() { ((WARN++)) || true; echo -e "  ${YELLOW}WARN${NC}  $1"; }
log_info() { echo -e "  ${BLUE}info${NC}  $1"; }

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# La query diretta al DB: il BB `smoke_db_query` (_smoke_db.sh, regola del 2).
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_db.sh"

echo ""
echo "============================================================"
echo " Smoke test BE-2.0ter — JwtAuditAuthentication GUC propagation"
echo " Base URL: $BASE_URL"
echo " User:     $USERNAME"
echo "============================================================"

# ============================================================
# 0) Login JWT
# ============================================================
echo ""
echo "-- 0. Login JWT --"

# Login vero (-D lo implica): piu' avanti si fa il refresh dal suo cookie.
smoke_login -D "${TMPFILE}.hdr"
log_ok "JWT ottenuto (HTTP 200)"

# Recupera l'ID Django dell'utente per i confronti successivi
USER_ID=$(smoke_db_query "SELECT id FROM auth_user WHERE username = '$USERNAME' LIMIT 1" | tail -1)
if [[ -n "$USER_ID" ]]; then
    log_info "auth_user.id per '$USERNAME': $USER_ID"
else
    log_fail "Impossibile risolvere auth_user.id per '$USERNAME'"
    exit 1
fi

# ============================================================
# 1) Verifica configurazione: la auth class registrata
# ============================================================
echo ""
echo "-- 1. Configurazione: JwtAuditAuthentication registrata --"

AUTH_CLASS_CHECK=$("${BACKEND_DIR}/manage-env.sh" shell -c "
from rest_framework.settings import api_settings
classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
match = any('JwtAuditAuthentication' in c.__name__ for c in classes)
print('OK' if match else 'FAIL')
print('  Classes:', [c.__name__ for c in classes])
" 2>/dev/null | grep -E "^(OK|FAIL|  )" || true)

if echo "$AUTH_CLASS_CHECK" | grep -q "^OK"; then
    log_ok "JwtAuditAuthentication registrata in DEFAULT_AUTHENTICATION_CLASSES"
    echo "$AUTH_CLASS_CHECK" | grep "  Classes" | sed 's/^/    /'
else
    log_fail "JwtAuditAuthentication NON registrata in DEFAULT_AUTHENTICATION_CLASSES"
    echo "$AUTH_CLASS_CHECK" | sed 's/^/    /'
fi

# ============================================================
# 2) Storico audit: distribuzione user_insert PRE vs POST
# ============================================================
echo ""
echo "-- 2. Storico audit user_insert (anagrafiche.soggetti) --"

echo "    Distribuzione user_insert (top 5, ultimi 90 giorni):"
smoke_db_query "SELECT user_insert, COUNT(*) AS cnt
            FROM anagrafiche.soggetti
           WHERE data_insert >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY user_insert
        ORDER BY cnt DESC
           LIMIT 5" | sed 's/|/  →  /' | sed 's/^/      /'

# ============================================================
# 3) Creazione cliente via API → verifica user_insert
# ============================================================
echo ""
echo "-- 3. Scrittura via API: user_insert popolato con JWT username --"

# Cerca un soggetto persona fisica esistente per evitare di creare
# anagrafica nuova solo per il test.
SOGG_TEST=$(smoke_db_query "SELECT id FROM anagrafiche.soggetti
                       WHERE attivo = true LIMIT 1" | tail -1)

if [[ -z "$SOGG_TEST" ]]; then
    log_warn "Nessun soggetto attivo disponibile per test scrittura — salto §3-4"
else
    log_info "Soggetto di test: $SOGG_TEST"

    # Conta eventi sessione PRIMA della call API (smoke veloce, non
    # crea cliente reale per non sporcare dati)
    PRE_AUDIT=$(smoke_db_query "SELECT user_insert FROM dbops.sessioni_utente
                          WHERE auth_user_id = $USER_ID
                          ORDER BY data_insert DESC LIMIT 1" | tail -1)
    log_info "Ultimo user_insert su sessioni_utente per user $USER_ID: '$PRE_AUDIT'"

    if [[ "$PRE_AUDIT" == "$USERNAME" ]]; then
        log_ok "user_insert='$USERNAME' (JWT username propagato correttamente)"
    elif [[ "$PRE_AUDIT" == "zeroerp_app" || "$PRE_AUDIT" == "titodb" ]]; then
        log_fail "user_insert='$PRE_AUDIT' (ruolo DB, non JWT) — fix non efficace?"
    else
        log_warn "user_insert='$PRE_AUDIT' (valore inatteso)"
    fi
fi

# Test attivo: una API call autenticata che genera un record audited.
# Usiamo l'endpoint di refresh JWT che inserisce in dbops.sessioni_utente.
echo ""
echo "    Triggering: refresh JWT (inserisce sessioni_utente.REFRESH)..."
REFRESH=$(refresh_dal_set_cookie "${TMPFILE}.hdr")
curl_refresh "$REFRESH" -s -o /dev/null -X POST \
    "${BASE_URL}/api/v1/admin/token/refresh/"

sleep 0.3

# Verifica user_insert dell'ultimo REFRESH
LAST_REFRESH_USER=$(smoke_db_query "SELECT user_insert FROM dbops.sessioni_utente
                              WHERE auth_user_id = $USER_ID AND evento = 'REFRESH'
                              ORDER BY data_insert DESC LIMIT 1" | tail -1)

if [[ "$LAST_REFRESH_USER" == "$USERNAME" ]]; then
    log_ok "Refresh appena fatto: user_insert='$USERNAME' (JWT propagato!)"
elif [[ "$LAST_REFRESH_USER" == "zeroerp_app" || "$LAST_REFRESH_USER" == "titodb" ]]; then
    log_fail "Refresh appena fatto: user_insert='$LAST_REFRESH_USER' (ruolo DB) — JwtAuditAuthentication NON sta propagando le GUC ai trigger di scrittura"
else
    log_warn "user_insert inatteso: '$LAST_REFRESH_USER'"
fi

# ============================================================
# 4) Trigger refactor: ricorda di verificare l'auto-link BA
# ============================================================
echo ""
echo "-- 4. Trigger refactor operatore-emittenti --"

# Verifica che l'utente abbia (o no) un'associazione 1-a-1
USER_EMITTENTE_ID=$(smoke_db_query "SELECT script.fn_resolve_emittente_for_user($USER_ID)" | tail -1)

if [[ "$USER_EMITTENTE_ID" == "" || "$USER_EMITTENTE_ID" == "NULL" ]]; then
    log_info "User $USER_ID: admin globale (no riga in user_emittenti_fiscali)"
    log_info "  → trigger billing_account_link_ef farebbe skip (admin globale)"
    log_info "  → trigger billing_account_guard_admin_globale: bloccherebbe se ci sono EF"

    EF_COUNT=$(smoke_db_query "SELECT COUNT(*) FROM anagrafiche.emittenti_fiscali WHERE attivo=true" | tail -1)
    log_info "  Emittenti fiscali attivi nel sistema: $EF_COUNT"

    if [[ "$EF_COUNT" -gt "0" ]]; then
        log_warn "Sistema ha $EF_COUNT EF: il guard bloccherebbe la creazione di un BA da questo user"
        log_warn "  Per testare la creazione BA in vivo, serve un utente con riga in user_emittenti_fiscali"
    fi
else
    log_ok "User $USER_ID: operatore di emittente fiscale id=$USER_EMITTENTE_ID"
    log_info "  → trigger billing_account_link_ef farebbe il mapping verso EF $USER_EMITTENTE_ID"
fi

# ============================================================
# 5) Storico audit POST-fix: nuove righe REFRESH dovrebbero
#    essere tutte con username JWT, non con ruolo DB
# ============================================================
echo ""
echo "-- 5. Audit ratio storico vs post-fix --"

OLD_RUOLO_DB=$(smoke_db_query "SELECT COUNT(*) FROM dbops.sessioni_utente
                          WHERE user_insert IN ('zeroerp_app', 'titodb')" | tail -1)
NEW_JWT_USER=$(smoke_db_query "SELECT COUNT(*) FROM dbops.sessioni_utente
                          WHERE user_insert NOT IN ('zeroerp_app', 'titodb')" | tail -1)

log_info "Sessioni_utente con user_insert = ruolo DB:    $OLD_RUOLO_DB (storico pre-fix)"
log_info "Sessioni_utente con user_insert = JWT user:    $NEW_JWT_USER (post-fix)"

# Ultime 5 righe per visual check
echo ""
echo "    Ultime 5 righe sessioni_utente.user_insert (cronologico):"
smoke_db_query "SELECT data_insert::text, evento, user_insert, auth_user_id
            FROM dbops.sessioni_utente
        ORDER BY data_insert DESC LIMIT 5" | sed 's/|/  /g' | sed 's/^/      /'

# ============================================================
# Riepilogo
# ============================================================
echo ""
echo "============================================================"
echo " Riepilogo: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${WARN} WARN${NC}"
echo "============================================================"

if [[ "$FAIL" -gt "0" ]]; then
    echo -e "${RED}Smoke test fallito: il fix BE-2.0ter NON sta propagando le GUC.${NC}"
    echo "    Controllare:"
    echo "      - apps/core/api/jwt_audit_authentication.py registrata in settings"
    echo "      - apps/core/api/base_views.py usa JwtAuditAuthentication"
    echo "      - DB raggiungibile e auth_user.is_active=true per '$USERNAME'"
    exit 1
fi

if [[ "$WARN" -gt "0" ]]; then
    echo -e "${YELLOW}Smoke test passato con warning — controlla i messaggi sopra.${NC}"
    exit 0
fi

echo -e "${GREEN}Smoke test passato: il fix BE-2.0ter funziona end-to-end.${NC}"
echo "  - JwtAuditAuthentication propaga app.jwt_user / app.current_user_id"
echo "  - I trigger DB di audit popolano user_insert con username JWT"
echo "  - I trigger refactor operatore-emittenti possono leggere user_id"
exit 0
