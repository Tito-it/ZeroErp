#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test E2E — Contratti overlap + ANNULLATO + UX messaggi
# Sessione 2026-05-21.
#
# Copre i 4 fix incrociati BE/DB/FE:
#  - DB: EXCLUDE partial ex_contratti_no_overlap WHERE NOT is_abortito_snapshot
#    (migrations 20260521-01..03), permette ricreare contratto su quadrupla di
#    un ANNULLATO precedente.
#  - BE contratti_service: nuovo message user-friendly su E_VENDITE_CONTRATTO_OVERLAP;
#    aggiunta entry `ex_contratti_no_overlap` in _UNIQUE_CONSTRAINTS per
#    resilienza al rinaming DB.
#  - BE lookup_service: registrata policy E_LOOKUP_STRUTTURA_TABELLA_INVALIDA
#    + traduzione P0001 da dbops.fn_get_lookup_codici (errore di config,
#    non riprodotto qui — coperto da unit test).
#  - FE ContrattoDrawer: rimosso pre-fill tipo_variazione_globale che produceva
#    coppia incoerente in edit; canSave estesa al check coppia anche in edit.
#    Quel bug FE mascherava E_VENDITE_CONTRATTO_OVERLAP con "Payload contratto
#    non valido" — il test #6 qui verifica il path BE che il FE prima
#    inavvertitamente eccitava.
#
# Uso:
#   ./scripts/tests/smoke-test-contratti-overlap-annullato-20260521.sh [password]
#
# Env richiesto per i test CREATE/UPDATE (#5-#10):
#   SMOKE_BA_ID                 - billing_account_id valido (in scope user)
#   SMOKE_ISTANZA_UTILITY_ID    - istanza_utility_id coerente col BA
#   SMOKE_UTILITY_ID            - utility_id coerente con istanza
#   SMOKE_LISTINO_ID            - (opzionale) listino_id con versione ATTIVA
# Se mancanti -> i test write vengono skippati (non e' un fail).
#
# Suffisso unico via SMOKE_TAG nel meta del contratto (cleanup idempotente).
# ------------------------------------------------------------
# Indice test (0..10):
#  0) Autenticazione JWT
#  1) Cleanup proattivo — annulla contratti smoke residui (meta.smoke_tag)
#  2) Lista contratti — read-only smoke
#  3) GET contratto inesistente — 404 atteso
#  4) Lookup codici — rel non whitelistata -> 400 E_CORE_VALIDATION
#  5) CREATE contratto C1 DRAFT (richiede env)
#  6) PATCH C1 coppia variazione incoerente -> 400 E_VENDITE_VALIDATION
#     (regression del bug FE pre-fix: tipo presente senza valore)
#  7) PATCH C1 coppia variazione coerente null/null -> 200 OK
#  8) CREATE C2 stessa quadrupla di C1 DRAFT -> 409 E_VENDITE_CONTRATTO_OVERLAP
#     con message user-friendly nuovo
#  9) ANNULLA C1 (cambio stato -> ANNULLATO) -> 200 OK
# 10) CREATE C3 stessa quadrupla di C1 ANNULLATO -> 201 OK
#     (verifica EXCLUDE partial DB: is_abortito_snapshot=true esclude C1)
# 11) Cleanup finale — annulla C3
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_errori.sh"   # smoke_check_codice
SMOKE_TAG="${SMOKE_TAG:-smoke-overlap-annullato-$(date +%Y%m%d-%H%M%S)}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
EXTRACTED=""
LAST_STATUS=""
LAST_BODY=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}   $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_skip() { ((SKIP++)) || true; echo -e "  ${YELLOW}SKIP${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC}  $1"; }

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

# Diagnostica categoria fallimento prima del fix (pattern memo
# feedback_smoke_test_idempotenti): in caso di FAIL, dump succinto di
# status + code + message per evitare wild goose chase su tutto il body.
diag_fail() {
    local code msg
    code=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try: print(json.load(sys.stdin).get('error',{}).get('code','-'))
except: print('-')" 2>/dev/null)
    msg=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try: print(json.load(sys.stdin).get('error',{}).get('message','-'))
except: print('-')" 2>/dev/null)
    echo "       status=$LAST_STATUS code=$code"
    echo "       message=$msg"
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    local args=(-s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}")
    if [[ "$method" != "GET" ]]; then
        args+=(-H "Content-Type: application/json")
        if [[ "$method" == "POST" || "$method" == "PATCH" || "$method" == "DELETE" ]]; then
            args+=(-H "Idempotency-Key: ${SMOKE_TAG}-$(date +%N)")
        fi
        args+=(-X "$method")
        [[ -n "$data" ]] && args+=(-d "$data")
    fi
    curl "${args[@]}" "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

check_status() {
    local label="$1" expected="$2" json_expr="${3:-}"
    if [[ "$LAST_STATUS" == "$expected" ]]; then
        log_ok "$label (HTTP $LAST_STATUS)"
        [[ -n "$json_expr" ]] && EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
        return 0
    fi
    log_fail "$label — atteso HTTP $expected, ricevuto $LAST_STATUS"
    diag_fail
    return 1
}

# ================================================================
echo ""
echo "==========================================================="
echo " Smoke E2E — Contratti overlap + ANNULLATO + UX messages"
echo " Base URL: $BASE_URL"
echo " Tag univoco: $SMOKE_TAG"
echo "==========================================================="

# --- 0. Autenticazione JWT ---
echo ""
echo "-- 0. Autenticazione --"
smoke_login
log_ok "JWT ottenuto per '$USERNAME'"

# ================================================================
# 1. Cleanup proattivo — annulla contratti smoke residui
# ================================================================
# Pattern memo feedback_smoke_test_idempotenti: cleanup all'inizio per
# garantire idempotenza. Cerca DRAFT con meta.smoke_tag che inizia per
# "smoke-" sulla quadrupla che useremo, e li annulla. Necessario per
# permettere al test #5 (CREATE C1) di non sbattere contro residui di
# run precedenti che non sono arrivati al cleanup finale (es. run
# interrotto, FAIL prima del test #11).
echo ""
echo "-- 1. Cleanup proattivo contratti smoke residui --"
if [[ -n "${SMOKE_BA_ID:-}" && -n "${SMOKE_ISTANZA_UTILITY_ID:-}" && -n "${SMOKE_UTILITY_ID:-}" ]]; then
    # Nota: il BE usa `limit` come query param; `page_size` e' un 400
    # (cf. parse_list_params in apps/core/api/payload_validators.py).
    do_curl GET "/api/v1/vendite/contratti/?billing_account_id=${SMOKE_BA_ID}&limit=200"
    if [[ "$LAST_STATUS" == "200" ]]; then
        TOTALE_BA=$(json_get "$LAST_BODY" ".data.count")
        log_info "contratti del BA=${SMOKE_BA_ID}: ${TOTALE_BA:-?}"
        # Default: annulla solo DRAFT con meta.smoke_tag che inizia per "smoke-"
        # (safe: tocca solo contratti smoke conclamati).
        # Con SMOKE_FORCE_CLEANUP=1: annulla TUTTI i DRAFT sulla quadrupla
        # (utile per BA dedicati a smoke dove ogni DRAFT residuo e' un detrito
        # di run precedenti — usare solo su BA test dedicato).
        # stato DRAFT: match su `stato_codice == 'DRAFT'` quando proiettato,
        # fallback su `stato_doc_contratto_id == 1` (seed id stabile).
        IDS_RESIDUI=$(echo "$LAST_BODY" | FORCE="${SMOKE_FORCE_CLEANUP:-0}" python3 -c "
import sys, json, os
force = os.environ.get('FORCE', '0') == '1'
try:
    d = json.load(sys.stdin)
    for r in d['data']['results']:
        is_draft = (r.get('stato_codice') == 'DRAFT'
                    or r.get('stato_doc_contratto_id') == 1)
        if (r.get('istanza_utility_id') == ${SMOKE_ISTANZA_UTILITY_ID}
            and r.get('utility_id') == ${SMOKE_UTILITY_ID}
            and is_draft):
            if force:
                print(r['id'])
                continue
            meta = r.get('meta') or {}
            if isinstance(meta, str):
                try: meta = json.loads(meta)
                except: meta = {}
            if str(meta.get('smoke_tag', '')).startswith('smoke-'):
                print(r['id'])
except Exception as e:
    print(f'PARSE_ERROR: {e}', file=sys.stderr)
" 2>&1)
        count=0
        for rid in $IDS_RESIDUI; do
            do_curl POST "/api/v1/vendite/contratti/${rid}/cambia-stato/" '{"codice_interno":"ANNULLATO"}'
            if [[ "$LAST_STATUS" == "200" ]]; then
                count=$((count+1))
                log_info "annullato residuo id=$rid"
            else
                log_info "annullamento residuo id=$rid fallito (HTTP $LAST_STATUS)"
            fi
        done
        log_info "contratti smoke residui annullati: $count"
    else
        log_skip "cleanup saltato (lista contratti HTTP $LAST_STATUS)"
    fi
else
    log_info "cleanup mirato skip — env quadrupla non set"
fi

# ================================================================
# 2. Lista contratti — verifica endpoint base
# ================================================================
echo ""
echo "-- 2. Lista contratti (read-only) --"
do_curl GET "/api/v1/vendite/contratti/?limit=5"
check_status "GET lista contratti" 200 ".data.count" || true
log_info "contratti totali: ${EXTRACTED:-?}"

# ================================================================
# 3. GET contratto inesistente — 404 atteso
# ================================================================
echo ""
echo "-- 3. GET contratto inesistente --"
do_curl GET "/api/v1/vendite/contratti/999999999/"
smoke_check_codice "GET contratto 999999999" 404 "E_VENDITE_NOT_FOUND" || true

# ================================================================
# 4. Lookup codici — rel non whitelistata
# ================================================================
# Coerenza con fix #3 (E_LOOKUP_STRUTTURA_TABELLA_INVALIDA): qui testiamo
# il path della whitelist BE (E_CORE_VALIDATION), che e' la guardia
# applicativa che blocca prima di chiamare la fn DB. La fn DB con
# struttura invalida (E_LOOKUP_STRUTTURA_TABELLA_INVALIDA) e' coperta
# da unit test — non e' riproducibile via API senza inserire una rel
# spuria nella whitelist a runtime.
echo ""
echo "-- 4. Lookup rel non whitelistata --"
do_curl GET "/api/v1/core/lookup/codici/?rel=schema.tabella_inesistente"
smoke_check_codice "GET lookup rel non whitelistata" 400 "E_CORE_VALIDATION" || true

# ================================================================
# Test CREATE/UPDATE/ANNULLA — richiedono env setup
# ================================================================
SETUP_OK=true
for var in SMOKE_BA_ID SMOKE_ISTANZA_UTILITY_ID SMOKE_UTILITY_ID; do
    if [[ -z "${!var:-}" ]]; then
        SETUP_OK=false
        break
    fi
done

if ! $SETUP_OK; then
    echo ""
    echo "-- 5..11. SKIP test CREATE/UPDATE/ANNULLA --"
    log_skip "Env mancante: SMOKE_BA_ID / SMOKE_ISTANZA_UTILITY_ID / SMOKE_UTILITY_ID"
    log_info "Per abilitare: export SMOKE_BA_ID=... SMOKE_ISTANZA_UTILITY_ID=... SMOKE_UTILITY_ID=..."
else
    AMBITO="${SMOKE_AMBITO:-COMMODITY}"
    OGGI=$(date +%Y-%m-%d)
    META_TAG="{\"smoke_tag\":\"$SMOKE_TAG\"}"

    # ================================================================
    # 5. CREATE C1 DRAFT
    # ================================================================
    echo ""
    echo "-- 5. CREATE C1 DRAFT --"
    PAYLOAD_C1=$(cat <<EOF
{
    "billing_account_id": $SMOKE_BA_ID,
    "istanza_utility_id": $SMOKE_ISTANZA_UTILITY_ID,
    "utility_id": $SMOKE_UTILITY_ID,
    "ambito": "$AMBITO",
    "valido_dal": "$OGGI",
    "data": "$OGGI",
    "meta": $META_TAG
}
EOF
)
    do_curl POST "/api/v1/vendite/contratti/" "$PAYLOAD_C1"
    if check_status "POST create C1" 200 ".data.id"; then
        C1_ID="$EXTRACTED"
        log_info "C1 creato id=$C1_ID"
    else
        # Causa probabile: la quadrupla e' gia' occupata da un contratto non
        # abortito (smoke precedente non pulito). Diagnosi parlante prima
        # del fix invece di rilanciare tutto lo smoke.
        if [[ "$LAST_STATUS" == "409" ]]; then
            log_info "Quadrupla gia' occupata. Rilancia con SMOKE_TAG diverso o cleanup manuale."
        fi
        C1_ID=""
    fi

    # ================================================================
    # 6. PATCH C1 coppia variazione INCOERENTE -> 400
    # ================================================================
    # Regression test del bug FE pre-fix: prima di oggi
    # `onListinoChange` settava `tipo_variazione_globale='PERCENTUALE'`
    # senza valore, producendo coppia incoerente che il BE rifiutava
    # con generico "Payload contratto non valido". Qui verifichiamo che
    # il path BE continui a rifiutare correttamente (defense-in-depth
    # — il FE ora non manda piu' la coppia incoerente, ma il BE deve
    # restare guard).
    if [[ -n "$C1_ID" ]]; then
        echo ""
        echo "-- 6. PATCH C1 coppia tipo-senza-valore -> 400 atteso --"
        do_curl PATCH "/api/v1/vendite/contratti/${C1_ID}/" \
            '{"tipo_variazione_globale":"PERCENTUALE","valore_variazione_globale":null}'
        smoke_check_codice "PATCH coppia incoerente" 400 "E_VENDITE_VALIDATION" || true
    fi

    # ================================================================
    # 7. PATCH C1 coppia coerente null/null -> 200
    # ================================================================
    if [[ -n "$C1_ID" ]]; then
        echo ""
        echo "-- 7. PATCH C1 coppia null/null -> 200 atteso --"
        do_curl PATCH "/api/v1/vendite/contratti/${C1_ID}/" \
            '{"tipo_variazione_globale":null,"valore_variazione_globale":null}'
        check_status "PATCH coppia null/null" 200 || true
    fi

    # ================================================================
    # 8. CREATE C2 stessa quadrupla -> 409 E_VENDITE_CONTRATTO_OVERLAP
    # ================================================================
    # Verifica che il messaggio sia user-friendly (non quello vecchio).
    if [[ -n "$C1_ID" ]]; then
        echo ""
        echo "-- 8. CREATE C2 stessa quadrupla -> 409 overlap atteso --"
        do_curl POST "/api/v1/vendite/contratti/" "$PAYLOAD_C1"
        if smoke_check_codice "CREATE C2 overlap" 409 "E_VENDITE_CONTRATTO_OVERLAP"; then
            MSG=$(json_get "$LAST_BODY" ".error.message")
            # Verifica che il message contenga il phrasing user-friendly
            # ("punto di fornitura") e NON il vecchio gergo tecnico
            # ("combinazione cliente/istanza/utility/ambito").
            if echo "$MSG" | grep -qi "punto di fornitura"; then
                log_ok "message user-friendly contiene 'punto di fornitura'"
            else
                log_fail "message non e' quello nuovo. Ricevuto: $MSG"
            fi
            if echo "$MSG" | grep -qi "combinazione cliente/istanza/utility/ambito"; then
                log_fail "message contiene ancora il vecchio gergo tecnico"
            fi
        fi
    fi

    # ================================================================
    # 9. ANNULLA C1 (DRAFT -> ANNULLATO)
    # ================================================================
    if [[ -n "$C1_ID" ]]; then
        echo ""
        echo "-- 9. POST cambio stato C1 -> ANNULLATO --"
        do_curl POST "/api/v1/vendite/contratti/${C1_ID}/cambia-stato/" \
            '{"codice_interno":"ANNULLATO"}'
        check_status "POST annulla C1" 200 || true
    fi

    # ================================================================
    # 10. CREATE C3 stessa quadrupla di C1 ANNULLATO -> 201
    # ================================================================
    # E' il fix DB partial EXCLUDE: contratti con is_abortito_snapshot=true
    # non partecipano al check overlap.
    if [[ -n "$C1_ID" ]]; then
        echo ""
        echo "-- 10. CREATE C3 stessa quadrupla del ANNULLATO -> 201 atteso --"
        do_curl POST "/api/v1/vendite/contratti/" "$PAYLOAD_C1"
        if check_status "CREATE C3 dopo annullamento C1" 200 ".data.id"; then
            C3_ID="$EXTRACTED"
            log_info "C3 creato id=$C3_ID (fix EXCLUDE partial OK)"
        else
            C3_ID=""
            # Diagnostica categoria fallimento: se torna 409 overlap, la
            # migration 20260521-01..03 non e' attiva o il trigger
            # is_abortito_snapshot non funziona.
            if [[ "$LAST_STATUS" == "409" ]]; then
                log_info "Possibile causa: migration 20260521-01..03 non applicata,"
                log_info "oppure trigger sync is_abortito_snapshot non aggiornato."
            fi
        fi

        # ================================================================
        # 11. Cleanup finale — annulla C3 (no DELETE su contratti)
        # ================================================================
        if [[ -n "${C3_ID:-}" ]]; then
            echo ""
            echo "-- 11. Cleanup finale: annulla C3 --"
            do_curl POST "/api/v1/vendite/contratti/${C3_ID}/cambia-stato/" \
                '{"codice_interno":"ANNULLATO"}'
            check_status "POST annulla C3 cleanup" 200 || true
        fi
    fi
fi

# ================================================================
echo ""
echo "==========================================================="
echo " Risultato finale"
echo "==========================================================="
echo -e " PASS:  ${GREEN}${PASS}${NC}"
echo -e " FAIL:  ${RED}${FAIL}${NC}"
echo -e " SKIP:  ${YELLOW}${SKIP}${NC}"
echo "==========================================================="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
