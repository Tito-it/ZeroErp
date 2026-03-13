#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale per API Amm. Software (amministrazione utenti)
# Uso: ./scripts/smoke-test-amm-software.sh [password]
# Richiede utente ADMIN (ruolo_sistema = ADMIN)
# ------------------------------------------------------------
# Indice test (0..15):
#  0) Autenticazione JWT
#  1) Lookup qualifiche attive (via core/lookup-codici)
#  2) Lookup unita' organizzative
#  3) Lookup aree funzionali
#  4) Lookup azioni processo
#  5) Lookup emittenti fiscali
#  6) Lista utenti (GET)
#  7) Lista utenti con filtro ruolo_sistema
#  8) Lista utenti con paginazione
#  9) Dettaglio utente corrente
# 10) Override aree (GET) utente corrente
# 11) Override azioni (GET) utente corrente
# 12) Lista reparti
# 13) Lookup tipi soggetto dettaglio (Sprint 3)
# 14) Matrice indirizzi per tipo PR (Sprint 3)
# 15) Autocomplete comuni (Sprint 3)
# 16) Search stradario (Sprint 3)
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
echo " Smoke test API Amm. Software"
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

# Estrai user_id dal token
USER_ID=$(echo "$TOKEN" | cut -d. -f2 | python3 -c "
import sys, base64, json
payload = sys.stdin.read().strip()
padding = 4 - len(payload) % 4
decoded = base64.urlsafe_b64decode(payload + '=' * padding)
print(json.loads(decoded).get('user_id', ''))
" 2>/dev/null)

log_ok "JWT ottenuto per '$USERNAME' (user_id=$USER_ID)"

# ================================================================
# LOOKUP
# ================================================================
echo ""
echo "-- 1. Lookup qualifiche (via core/lookup-codici) --"

do_curl GET "/api/v1/core/lookup/codici/?rel=config.qualifiche"
check "GET lookup qualifiche (core)" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    results = d.get('results', [])
    print(f'  --- qualifiche attive: {len(results)}')
    for q in results[:5]:
        print(f'      id={q[\"id\"]} {q.get(\"descrizione\",\"?\")}')
    if len(results) > 5:
        print(f'      ... e altre {len(results)-5}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 2. Lookup UO ---
echo ""
echo "-- 2. Lookup unita' organizzative --"

do_curl GET "/api/v1/amm-software/lookup/unita-organizzative/"
check "GET lookup UO" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- unita organizzative: {len(results)}')
    for uo in results[:5]:
        print(f'      id={uo[\"id\"]} {uo[\"nome\"]}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 3. Lookup aree funzionali ---
echo ""
echo "-- 3. Lookup aree funzionali --"

do_curl GET "/api/v1/amm-software/lookup/aree-funzionali/"
check "GET lookup aree funzionali" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- aree funzionali: {len(results)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 4. Lookup azioni processo ---
echo ""
echo "-- 4. Lookup azioni processo --"

do_curl GET "/api/v1/amm-software/lookup/azioni-processo/"
check "GET lookup azioni processo" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- azioni processo: {len(results)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 5. Lookup emittenti fiscali ---
echo ""
echo "-- 5. Lookup emittenti fiscali --"

do_curl GET "/api/v1/amm-software/lookup/emittenti-fiscali/"
check "GET lookup emittenti fiscali" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- emittenti fiscali: {len(results)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# LISTA UTENTI
# ================================================================
echo ""
echo "-- 6. Lista utenti --"

do_curl GET "/api/v1/amm-software/utenti/"
check "GET lista utenti" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    results = d.get('results', [])
    count = d.get('count', len(results))
    print(f'  --- utenti totali: {count}')
    for u in results[:3]:
        print(f'      {u.get(\"username\",\"?\")} ({u.get(\"first_name\",\"\")} {u.get(\"last_name\",\"\")}) ruolo={u.get(\"ruolo_sistema\",\"?\")}')
    if len(results) > 3:
        print(f'      ... e altri {count-3}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 7. Filtro ruolo ---
echo ""
echo "-- 7. Lista utenti filtro ruolo_sistema --"

do_curl GET "/api/v1/amm-software/utenti/?ruolo_sistema=ADMIN"
check "GET utenti filtro ADMIN" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    count = d.get('count', len(d.get('results', [])))
    print(f'  --- utenti ADMIN: {count}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 8. Paginazione ---
echo ""
echo "-- 8. Lista utenti paginazione --"

do_curl GET "/api/v1/amm-software/utenti/?limit=2&offset=0"
check "GET utenti limit=2 offset=0" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    results = d.get('results', [])
    count = d.get('count', '?')
    print(f'  --- pagina 1: {len(results)} record (totale: {count})')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# DETTAGLIO UTENTE
# ================================================================
echo ""
echo "-- 9. Dettaglio utente corrente --"

do_curl GET "/api/v1/amm-software/utenti/${USER_ID}/"
check "GET dettaglio utente $USER_ID" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    print(f'  --- username: {d.get(\"username\",\"?\")}')
    print(f'  --- ruolo: {d.get(\"ruolo_sistema\",\"?\")}')
    print(f'  --- UO: {d.get(\"unita_organizzativa_nome\",\"?\")}')
    print(f'  --- attivo: {d.get(\"is_active\",\"?\")}')
    print(f'  --- override_aree: {d.get(\"override_aree_count\",0)}, override_azioni: {d.get(\"override_azioni_count\",0)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# OVERRIDE PERMESSI (GET solo — non modifichiamo dati in smoke test)
# ================================================================
echo ""
echo "-- 10. Override aree (GET) --"

do_curl GET "/api/v1/amm-software/utenti/${USER_ID}/override-aree/"
check "GET override aree utente $USER_ID" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- override aree: {len(results)}')
    for a in results:
        print(f'      {a.get(\"area_codice\",\"?\")} = {a.get(\"livello\",\"?\")}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 11. Override azioni (GET) ---
echo ""
echo "-- 11. Override azioni (GET) --"

do_curl GET "/api/v1/amm-software/utenti/${USER_ID}/override-azioni/"
check "GET override azioni utente $USER_ID" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- override azioni: {len(results)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# REPARTI
# ================================================================
echo ""
echo "-- 12. Lista reparti --"

do_curl GET "/api/v1/amm-software/reparti/"
check "GET lista reparti" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- reparti: {len(results)}')
    for r in results[:5]:
        profilo = 'configurato' if r.get('has_profilo') else 'da configurare'
        print(f'      {r.get(\"nome\",\"?\")} [{profilo}] operatori={r.get(\"operatori_count\",0)}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
# ENDPOINT CORE — Sprint 3 (tipi soggetto, matrice indirizzi, comuni)
# ================================================================
echo ""
echo "-- 13. Lookup tipi soggetto dettaglio --"

do_curl GET "/api/v1/core/lookup/tipi-soggetto-dettaglio/"
check "GET tipi soggetto dettaglio" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- tipi soggetto dettaglio: {len(results)}')
    for t in results:
        print(f'      id={t[\"id\"]} {t[\"codice_interno\"]} natura={t.get(\"natura_soggetto\",\"?\")} dati_soc={t.get(\"dati_societari_policy\",\"?\")}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 14. Matrice indirizzi per tipo PR (id=1) ---
echo ""
echo "-- 14. Matrice indirizzi per tipo PR --"

do_curl GET "/api/v1/core/lookup/tipi-soggetto-dettaglio/1/indirizzi/"
check "GET matrice indirizzi PR" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- tipi indirizzo per PR: {len(results)}')
    for i in results:
        obbl = '*' if i.get('obbligatorio') else ' '
        fb = f' (fallback: {i.get(\"fallback_codice\",\"-\")})' if i.get('fallback_codice') else ''
        print(f'      {obbl} {i.get(\"codice\",\"?\")} - {i.get(\"descrizione\",\"?\")}{fb}')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 15. Autocomplete comuni ---
echo ""
echo "-- 15. Autocomplete comuni --"

do_curl GET "/api/v1/core/lookup/comuni/?search=ROMA&limit=5"
check "GET autocomplete comuni (search=ROMA)" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    results = d.get('results', [])
    count = d.get('count', '?')
    print(f'  --- comuni trovati: {count} (mostrati: {len(results)})')
    for c in results:
        print(f'      id={c[\"id\"]} {c[\"descrizione\"]} ({c.get(\"provincia_sigla\",\"?\")})')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# --- 16. Search stradario ---
echo ""
echo "-- 16. Search stradario --"

do_curl GET "/api/v1/core/search/stradario/?comune_id=1&search=via&limit=5"
check "GET search stradario (comune_id=1, search=via)" 200

echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)['data']['results']
    print(f'  --- vie trovate: {len(results)}')
    for v in results[:5]:
        print(f'      id={v[\"stradario_id\"]} {v.get(\"indirizzo_normalizzato\",v.get(\"via_completa\",\"?\"))} ({v.get(\"provincia_sigla\",\"?\")})')
except Exception as e:
    print(f'  --- errore parsing: {e}')
" 2>/dev/null

# ================================================================
echo ""
echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
