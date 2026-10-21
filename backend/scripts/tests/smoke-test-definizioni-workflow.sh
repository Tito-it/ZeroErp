#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test E2E — API Definizioni di workflow versionate (editor Fase 3).
# Esercita l'INTERA superficie che il FE consuma:
#   dettaglio → step CRUD (+riordino via sequenza) → figli per-nodo
#   (canali/handler-eventi/competenze) → archi (prerequisiti/formule-tempo/
#   regole-generazione) → guard negativi (codice duplicato, edizione congelata).
#
# Uso:  ./scripts/tests/smoke-test-definizioni-workflow.sh [password]
#   oppure, col login unico: eval "$(./scripts/tests/smoke-login.sh)" e poi lo smoke
#   (riusa SMOKE_TOKEN finche' vale, `_smoke_auth.sh`).
# Env:  BASE_URL (def http://127.0.0.1:8000), SMOKE_USER (vedi _smoke_auth.sh),
#       DEF_ID (BOZZA editabile, def 419), PUB_ID (PUBBLICATA, def 418).
# Richiede un utente SUPER_ADMIN. Idempotente: codici unici (timestamp) +
# cleanup finale; sweep best-effort degli step SMOKE_ residui all'avvio.
# ------------------------------------------------------------
set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
# Gli id si TROVANO nella lista (passo 1), non si cablano: fino al 2026-10-13
# erano 419 (BOZZA) e 418 (PUBBLICATA), e quel giorno il team DB ha pubblicato
# la 419 e ritirato la 418 — lo smoke si fermava al passo 2. Override da env.
DEF_ID="${DEF_ID:-}"
PUB_ID="${PUB_ID:-}"
TS="$(date +%s)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; LAST_STATUS=""; LAST_BODY=""
TMPFILE="$(mktemp)"; trap "rm -f $TMPFILE" EXIT

log_ok()   { PASS=$((PASS+1)); echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}FAIL${NC} $1"; [[ -n "${LAST_BODY:-}" ]] && echo "       Body: $(echo "$LAST_BODY" | head -c 300)"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

# Estrae un valore da JSON (stdin) valutando un'espressione Python controllata.
py() { python3 -c "import sys,json; d=json.load(sys.stdin); print(eval(sys.argv[1]))" "$1" 2>/dev/null; }

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    local args=(-s -w '\n%{http_code}' -X "$method" -H "Authorization: Bearer ${TOKEN:-none}")
    if [[ -n "$data" ]]; then args+=(-H "Content-Type: application/json" -d "$data"); fi
    curl "${args[@]}" "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    LAST_STATUS="$(tail -1 "$TMPFILE")"; LAST_BODY="$(sed '$d' "$TMPFILE")"
}

# check LABEL EXPECTED_STATUS  → PASS se lo status combacia
check() {
    if [[ "$LAST_STATUS" == "$2" ]]; then log_ok "$1 (HTTP $LAST_STATUS)"; return 0
    else log_fail "$1 — atteso HTTP $2, ricevuto $LAST_STATUS"; return 1; fi
}
# check_err LABEL EXPECTED_CODE_SUBSTR  → PASS se status>=400 e error.code contiene la substring
check_err() {
    local code; code="$(echo "$LAST_BODY" | py "d['error']['code']")"
    if [[ "$LAST_STATUS" -ge 400 && "$code" == *"$2"* ]]; then log_ok "$1 (HTTP $LAST_STATUS, $code)"; return 0
    else log_fail "$1 — atteso >=400 con '$2', ricevuto HTTP $LAST_STATUS ($code)"; return 1; fi
}
extract() { echo "$LAST_BODY" | py "$1"; }

echo ""; echo "========================================="
echo " Smoke E2E — Definizioni Workflow (editor Fase 3)"
echo " Base: $BASE_URL · definizioni: risolte dalla lista (passo 1)"
echo "========================================="

# --- 0. Auth ---
echo ""; echo "-- 0. Autenticazione --"
smoke_login
if [[ "$SMOKE_LOGIN_FONTE" == "SMOKE_TOKEN" ]]; then log_ok "Token da SMOKE_TOKEN"; else log_ok "Login JWT"; fi

D="/api/v1/pratiche/definizioni"

# --- 1. Lista edizioni ---
echo ""; echo "-- 1. Lista --"
do_curl GET "$D/"; check "GET lista definizioni" 200 && \
    { N="$(extract "len(d['data']['results'])")"; log_info "edizioni: $N"; }
# La bozza da modificare: la prima di un emittente (le edizioni del preset non
# hanno emittente). La pubblicata per il guard «congelata»: di un emittente se
# c'e', altrimenti del preset.
[[ -z "$DEF_ID" ]] && DEF_ID="$(extract "next((r['id'] for r in d['data']['results'] if r.get('stato')=='BOZZA' and r.get('emittente_fiscale_id')), '')")"
[[ -z "$PUB_ID" ]] && PUB_ID="$(extract "next((r['id'] for r in sorted(d['data']['results'], key=lambda r: r.get('emittente_fiscale_id') is None) if r.get('stato')=='PUBBLICATA'), '')")"
if [[ -z "$DEF_ID" && -n "$PUB_ID" ]]; then
    # Nessuna bozza: se ne apre una dalla pubblicata (nuova versione). Resta
    # bozza (lo smoke toglie i suoi step alla fine) e il giro dopo la riusa.
    do_curl POST "$D/$PUB_ID/nuova-versione/" '{}'
    check "POST nuova versione (bozza da modificare)" 200 && DEF_ID="$(extract "d['data'].get('id') or d['data'].get('definizione_id') or ''")"
fi
log_info "bozza DEF_ID=${DEF_ID:-?} · pubblicata PUB_ID=${PUB_ID:-?}"
[[ -z "$DEF_ID" ]] && { echo -e "${RED}Nessuna bozza di definizione disponibile ne' creabile. Stop.${NC}"; exit 1; }

# --- 2. Dettaglio BOZZA target ---
echo ""; echo "-- 2. Dettaglio (BOZZA $DEF_ID) --"
do_curl GET "$D/$DEF_ID/"; if ! check "GET dettaglio $DEF_ID" 200; then
    echo -e "${RED}Impossibile procedere senza dettaglio.${NC}"; exit 1; fi
STATO="$(extract "d['data']['definizione']['stato']")"
TIPO_ID="$(extract "d['data']['definizione']['tipo_prestazione_id']")"
log_info "stato=$STATO tipo_prestazione_id=$TIPO_ID"
if [[ "$STATO" != "BOZZA" ]]; then
    echo -e "${RED}DEF_ID=$DEF_ID non è BOZZA ($STATO): editing non testabile. Imposta DEF_ID a una BOZZA.${NC}"; exit 1; fi

# --- 2b. Cleanup-first: rimuovi step SMOKE_ residui da run precedenti ---
for sid in $(extract "' '.join(str(s['id']) for s in d['data']['steps'] if s['codice'].startswith('SMOKE_'))"); do
    do_curl DELETE "$D/$DEF_ID/steps/$sid/"; log_info "cleanup step residuo $sid → HTTP $LAST_STATUS"
done

# --- 3. Lookup per i payload (best-effort) ---
echo ""; echo "-- 3. Lookup ausiliari --"
do_curl GET "/api/v1/core/lookup/codici/?rel=config.canali_pratiche"
CANALE_ID="$(extract "d['data']['results'][0]['id']")"; log_info "canale_id=$CANALE_ID"
do_curl GET "/api/v1/core/lookup/codici/?rel=pratiche.handler_flussi"
HANDLER_ID="$(extract "d['data']['results'][0]['id']")"; log_info "handler_id=$HANDLER_ID"
do_curl GET "/api/v1/core/lookup/codici/?rel=config.unita_organizzative"
UNITA_ID="$(extract "d['data']['results'][0]['id']")"; log_info "unita_id=$UNITA_ID"
do_curl GET "/api/v1/amm-software/operatori/?limit=200"
RISORSA_ID="$(extract "next((o['risorsa_umana_id'] for o in d['data']['results'] if o.get('risorsa_umana_id')), '')")"
log_info "risorsa_umana_id=$RISORSA_ID"

# --- 4. Step: create x2 ---
echo ""; echo "-- 4. Step create --"
CODE_A="SMOKE_A_$TS"; CODE_B="SMOKE_B_$TS"
do_curl POST "$D/$DEF_ID/steps/" "{\"codice\":\"$CODE_A\",\"descrizione\":\"Smoke A\",\"sequenza\":910}"
check "POST step A" 200; STEP_A="$(extract "d['data']['step_id']")"; log_info "STEP_A=$STEP_A"
do_curl POST "$D/$DEF_ID/steps/" "{\"codice\":\"$CODE_B\",\"descrizione\":\"Smoke B\",\"sequenza\":920}"
check "POST step B" 200; STEP_B="$(extract "d['data']['step_id']")"; log_info "STEP_B=$STEP_B"

# --- 5. Step: patch (descrizione + riordino sequenza) ---
echo ""; echo "-- 5. Step patch/riordino --"
do_curl PATCH "$D/$DEF_ID/steps/$STEP_A/" "{\"descrizione\":\"Smoke A mod\",\"sequenza\":905}"
check "PATCH step A (campi core + sequenza)" 200

# --- 6. Figli: canali ---
echo ""; echo "-- 6. Figli: canali --"
if [[ -n "$CANALE_ID" ]]; then
    do_curl POST "$D/$DEF_ID/steps/$STEP_A/canali/" "{\"canale_id\":$CANALE_ID,\"attivo\":true}"
    check "POST canale" 200; CID="$(extract "d['data']['id']")"
    do_curl PATCH "$D/$DEF_ID/steps/$STEP_A/canali/$CID/" "{\"attivo\":false}"; check "PATCH canale (toggle attivo)" 200
    do_curl DELETE "$D/$DEF_ID/steps/$STEP_A/canali/$CID/"; check "DELETE canale" 200
else log_info "salto canali (nessun canale in lookup)"; fi

# --- 7. Figli: handler-eventi ---
echo ""; echo "-- 7. Figli: handler-eventi --"
if [[ -n "$HANDLER_ID" ]]; then
    do_curl POST "$D/$DEF_ID/steps/$STEP_A/handler-eventi/" "{\"evento\":\"COMPLETATO\",\"handler_id\":$HANDLER_ID,\"esito_richiesto\":\"POSITIVO\",\"sequenza\":0,\"attivo\":true}"
    check "POST handler-evento" 200; HID="$(extract "d['data']['id']")"
    do_curl DELETE "$D/$DEF_ID/steps/$STEP_A/handler-eventi/$HID/"; check "DELETE handler-evento" 200
else log_info "salto handler-eventi (nessun handler in lookup)"; fi

# --- 8. Figli: competenze ---
echo ""; echo "-- 8. Figli: competenze --"
if [[ -n "$UNITA_ID" && -n "$RISORSA_ID" ]]; then
    do_curl POST "$D/$DEF_ID/steps/$STEP_A/competenze/" "{\"unita_organizzativa_id\":$UNITA_ID,\"risorsa_umana_id\":$RISORSA_ID,\"attivo\":true}"
    check "POST competenza" 200; COMPID="$(extract "d['data']['id']")"
    do_curl DELETE "$D/$DEF_ID/steps/$STEP_A/competenze/$COMPID/"; check "DELETE competenza" 200
else log_info "salto competenze (unita/risorsa non risolti)"; fi

# --- 9. Archi: prerequisiti (B richiede A) ---
echo ""; echo "-- 9. Archi: prerequisiti --"
do_curl POST "$D/$DEF_ID/archi/prerequisiti/" "{\"template_flusso_id\":$STEP_B,\"prerequisito_id\":$STEP_A,\"esito_richiesto\":\"POSITIVO\"}"
check "POST prerequisito" 200; PID="$(extract "d['data']['id']")"
do_curl DELETE "$D/$DEF_ID/archi/prerequisiti/$PID/"; check "DELETE prerequisito" 200

# --- 10. Archi: formule-tempo (A→B, critico<warning<esecuzione) ---
echo ""; echo "-- 10. Archi: formule-tempo --"
do_curl POST "$D/$DEF_ID/archi/formule-tempo/" "{\"template_flusso_da_id\":$STEP_A,\"template_flusso_a_id\":$STEP_B,\"giorni_critico\":1,\"giorni_warning\":2,\"giorni_esecuzione\":3,\"attivo\":true}"
check "POST formula-tempo" 200; FID="$(extract "d['data']['id']")"
do_curl DELETE "$D/$DEF_ID/archi/formule-tempo/$FID/"; check "DELETE formula-tempo" 200

# --- 11. Archi: regole-generazione (origine A → tipo dest = tipo dell'edizione) ---
echo ""; echo "-- 11. Archi: regole-generazione --"
do_curl POST "$D/$DEF_ID/archi/regole-generazione/" "{\"template_flusso_origine_id\":$STEP_A,\"tipo_prestazione_dest_id\":$TIPO_ID,\"auto\":false,\"attivo\":true}"
check "POST regola-generazione" 200; RID="$(extract "d['data']['id']")"
do_curl DELETE "$D/$DEF_ID/archi/regole-generazione/$RID/"; check "DELETE regola-generazione" 200

# --- 12. Guard negativi ---
echo ""; echo "-- 12. Guard negativi --"
# 12a. codice step duplicato → E_TEMPLATE_CODICE_DUPLICATO
do_curl POST "$D/$DEF_ID/steps/" "{\"codice\":\"$CODE_A\",\"descrizione\":\"dup\"}"
check_err "POST step codice duplicato rifiutato" "DUPLICATO" || true
# 12b. editing STRUTTURALE di edizione PUBBLICATA congelata → TEMPLATE_DEFINIZIONE_CONGELATA.
#      NB: la sola `descrizione` resta correggibile anche su edizioni emesse → qui si
#      patcha un campo strutturale (`sequenza`) per innescare il guard.
do_curl GET "$D/$PUB_ID/"
PUB_STEP="$(extract "d['data']['steps'][0]['id'] if d['data']['steps'] else ''")"
if [[ "$LAST_STATUS" == "200" && -n "$PUB_STEP" ]]; then
    do_curl PATCH "$D/$PUB_ID/steps/$PUB_STEP/" "{\"sequenza\":999}"
    # Il guard di dominio DEVE presentarsi come banner 4xx (non 500): asserzione
    # stretta per catturare una regressione della registrazione in error_policies.py.
    ECODE="$(echo "$LAST_BODY" | py "d['error']['code']")"
    if [[ "$LAST_STATUS" -ge 400 && "$LAST_STATUS" -lt 500 && "$ECODE" == *CONGELATA* ]]; then
        log_ok "PATCH strutturale su edizione congelata → banner 4xx (HTTP $LAST_STATUS, $ECODE)"
    else
        log_fail "PATCH congelata — atteso 4xx con CONGELATA, ricevuto HTTP $LAST_STATUS ($ECODE)"
    fi
else log_info "salto guard congelata (PUB_ID=$PUB_ID senza step o non accessibile)"; fi
# 12c. dettaglio id inesistente → 404 E_DEFINIZIONE_NOT_FOUND
do_curl GET "$D/999999999/"; check_err "GET dettaglio id inesistente → 404" "NOT_FOUND" || true

# --- 13. Cleanup step di test ---
echo ""; echo "-- 13. Cleanup --"
do_curl DELETE "$D/$DEF_ID/steps/$STEP_B/"; check "DELETE step B" 200
do_curl DELETE "$D/$DEF_ID/steps/$STEP_A/"; check "DELETE step A" 200

# --- Riepilogo ---
echo ""; echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
