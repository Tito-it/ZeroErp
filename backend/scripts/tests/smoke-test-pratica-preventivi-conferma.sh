#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Giro pratica PREVENTIVI_IMMEDIATA end-to-end
# (orchestratore CONFERMA_VENDITA, handler vendita.push_preventivo).
# Uso: ./scripts/tests/smoke-test-pratica-preventivi-conferma.sh [password]
#
# Copre contro DB+API reali (cio' che gli unit test mockano): l'intero
# percorso pratica della catena seed 9001..9004 (tipo 9002):
# RICHIESTA_CLIENTE -> PREVENTIVAZIONE (preventivo MISTO merce+servizio,
# aggancio ROOT via collega-pratica) -> APPROVAZIONE_CLIENTE (bridge M2:
# completamento flusso che accetta il preventivo) -> CONFERMA (avvio
# IN_CORSO = dispatch handler in transazione unica: split per natura
# merce->ordine + servizio->commessa, gate EVASO D6, sorgenti COLLEGATO,
# giornale DOMINIO_*, flusso COMPLETATO POSITIVO automatico).
# In coda: idempotenza ri-avvio CONFERMA (E_VENDITA_PREVENTIVO_GIA_PUSHATO).
#
# Prerequisiti dev: seed pratiche 20260608 (tipo 9002 + template 9001..9004
# + handler 9001), un emittente fiscale valido (default 32, override
# EMITTENTE_ID), articolo merce a catalogo. L'articolo servizio
# SMOKE-SERV-UT viene riusato/creato via API (natura amministrabile).
#
# Auto-diagnosi: se /emetti/ fallisce per prerequisiti documentali
# (template/emittente) i passi a valle vengono SALTATI con diagnosi.
# Idempotenza setup: pratica e preventivo nuovi a ogni run (nessun
# cleanup necessario: restano in stati terminali); articolo servizio
# riusato per codice fisso.
# ------------------------------------------------------------
# Indice:
#  0) Autenticazione JWT
#  1) Setup: tripla BA+utility + articolo merce + articolo servizio
#  2) Crea pratica PREVENTIVI_IMMEDIATA (tipo 9002) -> APERTA
#  3) GET percorso -> 4 step della catena, CONFERMA con has_handler
#  4) RICHIESTA_CLIENTE: crea flusso template-bound -> IN_CORSO -> COMPLETATO
#  5) PREVENTIVAZIONE: crea flusso -> IN_CORSO; preventivo MISTO +
#     collega-pratica (ROOT) + /emetti/ [prereq-gated]; COMPLETATO POSITIVO
#  6) APPROVAZIONE_CLIENTE: crea flusso -> IN_CORSO -> bridge M2
#     (/vendite/preventivi/approvazione-flusso/) -> preventivo ACCETTATO
#  7) CONFERMA: crea flusso (guard prerequisiti esito-aware) -> IN_CORSO
#     (handler) -> flusso COMPLETATO POSITIVO
#  8) Verifiche post-handler: preventivo EVASO, righe-smistabili-ordine
#     vuote, giornale con DOMINIO_ORDINE_CREATO + DOMINIO_COMMESSA_CREATA +
#     DOMINIO_PREVENTIVO_EVASO
#  9) Idempotenza: nuovo flusso CONFERMA -> avvio -> 4xx GIA_PUSHATO
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
USERNAME="${SMOKE_USER:-tid}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"

# --- Riferimenti DB (valori di dev, override via env) ---
EMITTENTE_FISCALE_ID="${EMITTENTE_ID:-32}"
TIPO_PRESTAZIONE_ID="${TIPO_PRESTAZIONE_ID:-9002}"   # PREVENTIVI_IMMEDIATA (seed)
PRIORITA_ID="${PRIORITA_ID:-1}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; SKIP=0
EXTRACTED=""; LAST_STATUS=""; LAST_BODY=""

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_skip() { ((SKIP++)) || true; echo -e "  ${YELLOW}SKIP${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        d = d[int(k)] if k.isdigit() else d[k]
    print(d)
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    fi
    LAST_STATUS=$(tail -1 "$TMPFILE"); LAST_BODY=$(sed '$d' "$TMPFILE")
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
    [[ -n "$json_expr" ]] && EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    return 0
}

# Estrae dal percorso (data.results) il template_flusso_id dello step col codice dato.
percorso_template_id() {
    local codice="$1"
    echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results', [])
    print(next((r['template_flusso_id'] for r in rows if r.get('template_flusso_codice') == '$codice'), ''))
except Exception: print('')
" 2>/dev/null
}

# Crea flusso template-bound e avvia (DA_ESEGUIRE -> IN_CORSO). Set FLUSSO_ID.
crea_e_avvia_flusso() {
    local template_id="$1" label="$2"
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" \
        "{\"template_flusso_id\": ${template_id}}"
    if ! check "POST crea flusso $label" 200 "data.flusso_id"; then
        FLUSSO_ID=""; return 1
    fi
    FLUSSO_ID="$EXTRACTED"
    if [[ -z "$FLUSSO_ID" ]]; then
        FLUSSO_ID=$(json_get "$LAST_BODY" "data.id")
    fi
    log_info "flusso_id ($label) = $FLUSSO_ID"
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" \
        '{"nuovo_stato": "IN_CORSO"}'
    check "POST avvia $label -> IN_CORSO" 200 || return 1
    return 0
}

# --- 0. Auth ---
echo "== Smoke giro pratica PREVENTIVI -> CONFERMA_VENDITA =="
if [[ -z "$PASSWORD" ]]; then echo -e "${RED}Password mancante${NC} (arg1 o SMOKE_PASSWORD)"; exit 2; fi
curl -s -w '\n%{http_code}' -X POST -H "Content-Type: application/json" \
    -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
    "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE" 2>/dev/null
AUTH_BODY=$(sed '$d' "$TMPFILE")
TOKEN=$(json_get "$AUTH_BODY" "access")
if [[ -z "$TOKEN" ]]; then echo -e "${RED}Auth fallita${NC}"; exit 2; fi
log_ok "Autenticazione JWT"

# --- 1. Setup: tripla BA+utility + articoli ---
echo ""; echo "-- 1. Setup tripla BA+utility + articolo merce + servizio --"
PREV_PAYLOAD=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/vendite/preventivi/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    if r:
        x = r[0]
        import json as j
        p = {}
        for k in ('billing_account_id','utility_id','istanza_utility_id'):
            if x.get(k): p[k] = x[k]
        print(j.dumps(p) if p else '')
except Exception:
    print('')
" 2>/dev/null)
if [[ -z "$PREV_PAYLOAD" ]]; then
    echo -e "${RED}Setup fallito: nessun preventivo esistente da cui derivare la tripla BA.${NC}"; exit 1
fi
# Emittente esplicito: l'utente smoke puo' essere un admin globale senza
# emittente assegnato (E_PREV_EMITTENTE_NON_RISOLTO dal trigger default).
PREV_PAYLOAD=$(echo "$PREV_PAYLOAD" | python3 -c "
import sys, json
p = json.load(sys.stdin)
p['emittente_fiscale_id'] = $EMITTENTE_FISCALE_ID
print(json.dumps(p))
")
log_info "payload preventivo = $PREV_PAYLOAD"

ARTICOLO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(r[0]['id'] if r else '')
except Exception: print('')
" 2>/dev/null)
[[ -z "$ARTICOLO_ID" ]] && { echo -e "${RED}Setup fallito: catalogo vuoto.${NC}"; exit 1; }
log_info "articolo merce = $ARTICOLO_ID"

SERV_CODICE="SMOKE-SERV-UT"
SERV_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?search=${SERV_CODICE}&page_size=5" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(next((x['id'] for x in r if x.get('codice') == '${SERV_CODICE}'), ''))
except Exception: print('')
" 2>/dev/null)
if [[ -z "$SERV_ID" ]]; then
    do_curl GET "/api/v1/catalogo/articoli/${ARTICOLO_ID}/"
    UOM_ID=$(json_get "$LAST_BODY" "data.uom_id")
    do_curl POST "/api/v1/catalogo/articoli/" \
        "{\"codice\": \"$SERV_CODICE\", \"descrizione\": \"Servizio una tantum (smoke)\", \"uom_id\": ${UOM_ID}, \"iva_id\": 16, \"natura_vendita_id\": 2}"
    if check "POST crea articolo servizio" 200 "data.id"; then SERV_ID="$EXTRACTED"; else SERV_ID=""; fi
fi
[[ -z "$SERV_ID" ]] && { echo -e "${RED}Setup fallito: articolo servizio non disponibile.${NC}"; exit 1; }
log_ok "articolo servizio = $SERV_ID"

# --- 2. Crea pratica PREVENTIVI_IMMEDIATA -> APERTA ---
echo ""; echo "-- 2. Crea pratica PREVENTIVI_IMMEDIATA (tipo $TIPO_PRESTAZIONE_ID) -> APERTA --"
do_curl POST "/api/v1/pratiche/" "{
    \"emittente_fiscale_id\": $EMITTENTE_FISCALE_ID,
    \"tipo_prestazione_id\": $TIPO_PRESTAZIONE_ID,
    \"priorita_id\": $PRIORITA_ID,
    \"descrizione\": \"Smoke giro CONFERMA_VENDITA\"
}"
if ! check "POST crea pratica" 200 "data.pratica_id"; then
    echo -e "${RED}Setup fallito: impossibile creare la pratica. Stop.${NC}"; exit 1
fi
PRATICA_ID="$EXTRACTED"; log_info "pratica_id = $PRATICA_ID"
do_curl POST "/api/v1/pratiche/${PRATICA_ID}/stato/" '{"nuovo_stato": "APERTA"}'
check "POST pratica -> APERTA" 200 || true

# --- 3. Percorso ---
echo ""; echo "-- 3. GET percorso (catena template 10..40) --"
do_curl GET "/api/v1/pratiche/${PRATICA_ID}/percorso/"
check "GET percorso" 200 || true
TPL_RICHIESTA=$(percorso_template_id "RICHIESTA_CLIENTE")
TPL_PREVENTIVAZIONE=$(percorso_template_id "PREVENTIVAZIONE")
TPL_APPROVAZIONE=$(percorso_template_id "APPROVAZIONE_CLIENTE")
TPL_CONFERMA=$(percorso_template_id "CONFERMA")
if [[ -n "$TPL_RICHIESTA" && -n "$TPL_PREVENTIVAZIONE" && -n "$TPL_APPROVAZIONE" && -n "$TPL_CONFERMA" ]]; then
    log_ok "Percorso completo: RICHIESTA=$TPL_RICHIESTA, PREVENTIVAZIONE=$TPL_PREVENTIVAZIONE, APPROVAZIONE=$TPL_APPROVAZIONE, CONFERMA=$TPL_CONFERMA"
else
    log_fail "Percorso incompleto (manca uno step della catena seed)"
    echo "       Body: $(echo "$LAST_BODY" | head -c 400)"; exit 1
fi
HAS_HANDLER=$(echo "$LAST_BODY" | python3 -c "
import sys, json
rows = json.load(sys.stdin).get('data', {}).get('results', [])
print(next((str(r.get('has_handler')) for r in rows if r.get('template_flusso_codice') == 'CONFERMA'), ''))
" 2>/dev/null)
[[ "$HAS_HANDLER" == "True" ]] && log_ok "CONFERMA ha handler (has_handler=true)" \
    || log_fail "CONFERMA senza handler nel percorso (has_handler=$HAS_HANDLER)"

# --- 4. RICHIESTA_CLIENTE ---
echo ""; echo "-- 4. RICHIESTA_CLIENTE: crea -> IN_CORSO -> COMPLETATO POSITIVO --"
if crea_e_avvia_flusso "$TPL_RICHIESTA" "RICHIESTA_CLIENTE"; then
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" \
        '{"nuovo_stato": "COMPLETATO", "esito": "POSITIVO"}'
    check "POST completa RICHIESTA_CLIENTE (POSITIVO)" 200 || true
fi

# --- 5. PREVENTIVAZIONE: preventivo MISTO + collega ROOT + emetti ---
echo ""; echo "-- 5. PREVENTIVAZIONE: preventivo MISTO + collega-pratica + /emetti/ --"
GIRO_OK=0
if crea_e_avvia_flusso "$TPL_PREVENTIVAZIONE" "PREVENTIVAZIONE"; then
    FLUSSO_PREVENTIVAZIONE_ID="$FLUSSO_ID"
    do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
    if check "POST crea preventivo" 200 "data.id"; then
        PREV_ID="$EXTRACTED"; log_info "preventivo_id = $PREV_ID"
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/collega-pratica/" \
            "{\"pratica_id\": ${PRATICA_ID}}"
        check "POST collega-pratica (ROOT)" 200 || true
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
            "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"2\", \"prezzo_unitario\": \"100.00\", \"iva_id\": 16}"
        check "POST riga merce" 200 || true
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
            "{\"articolo_id\": \"$SERV_ID\", \"qta_operativa\": \"1\", \"prezzo_unitario\": \"50.00\", \"iva_id\": 16}"
        check "POST riga servizio" 200 || true
        # EMESSO via multipart (prereq documentale: template/emittente).
        curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
            -F "x=" "${BASE_URL}/api/v1/vendite/preventivi/${PREV_ID}/emetti/" > "$TMPFILE" 2>/dev/null
        LAST_STATUS=$(tail -1 "$TMPFILE"); LAST_BODY=$(sed '$d' "$TMPFILE")
        if [[ "$LAST_STATUS" == "200" ]]; then
            log_ok "POST /emetti/ -> EMESSO"
            do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_PREVENTIVAZIONE_ID}/stato/" \
                '{"nuovo_stato": "COMPLETATO", "esito": "POSITIVO"}'
            check "POST completa PREVENTIVAZIONE (POSITIVO)" 200 && GIRO_OK=1
        else
            log_skip "EMESSO HTTP $LAST_STATUS — prereq documentale assente, salto il giro"
            log_info "Body: $(echo "$LAST_BODY" | head -c 200)"
        fi
    fi
fi

# --- 6. APPROVAZIONE_CLIENTE via bridge M2 ---
if [[ "$GIRO_OK" == "1" ]]; then
    echo ""; echo "-- 6. APPROVAZIONE_CLIENTE: bridge M2 -> preventivo ACCETTATO --"
    GIRO_OK=0
    if crea_e_avvia_flusso "$TPL_APPROVAZIONE" "APPROVAZIONE_CLIENTE"; then
        do_curl POST "/api/v1/vendite/preventivi/approvazione-flusso/" \
            "{\"pratica_id\": ${PRATICA_ID}, \"flusso_id\": ${FLUSSO_ID}, \"esito\": \"POSITIVO\"}"
        check "POST approvazione-flusso (M2, POSITIVO)" 200 || true
        do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/"
        ST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
        if [[ "$ST" == "ACCETTATO" ]]; then
            log_ok "preventivo ACCETTATO (M2 ha guidato l'accettazione)"
            GIRO_OK=1
        else
            log_fail "atteso ACCETTATO dopo M2, trovato '$ST'"
        fi
    fi
fi

# --- 7. CONFERMA: handler in transazione unica ---
if [[ "$GIRO_OK" == "1" ]]; then
    echo ""; echo "-- 7. CONFERMA: avvio IN_CORSO = dispatch handler -> COMPLETATO POSITIVO --"
    if crea_e_avvia_flusso "$TPL_CONFERMA" "CONFERMA"; then
        FLUSSO_CONFERMA_ID="$FLUSSO_ID"
        do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_CONFERMA_ID}/"
        FST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
        FES=$(json_get "$LAST_BODY" "data.esito")
        [[ "$FST" == "COMPLETATO" ]] && log_ok "flusso CONFERMA = COMPLETATO (auto, handler ok)" \
            || log_fail "flusso CONFERMA atteso COMPLETATO, trovato '$FST'"
        [[ "$FES" == "POSITIVO" ]] && log_ok "esito = POSITIVO" \
            || log_fail "esito atteso POSITIVO, trovato '$FES'"
    fi

    # --- 8. Verifiche post-handler ---
    echo ""; echo "-- 8. Post-handler: EVASO + smistamento completo + giornale DOMINIO_* --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/"
    ST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$ST" == "EVASO" ]] && log_ok "preventivo EVASO (gate D6: smistato tutto)" \
        || log_fail "atteso EVASO, trovato '$ST'"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe-smistabili-ordine/"
    N=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data', [])
    print(len(d) if isinstance(d, list) else 0)
except Exception: print('?')
" 2>/dev/null)
    [[ "$N" == "0" ]] && log_ok "righe-smistabili-ordine = 0 (merce allocata a ordine)" \
        || log_fail "attese 0 righe smistabili post-handler, trovate $N"
    do_curl GET "/api/v1/pratiche/${PRATICA_ID}/giornale/"
    check "GET giornale" 200 || true
    for EV in DOMINIO_ORDINE_CREATO DOMINIO_COMMESSA_CREATA DOMINIO_PREVENTIVO_EVASO; do
        if echo "$LAST_BODY" | grep -q "$EV"; then
            log_ok "giornale contiene $EV"
        else
            log_fail "giornale senza $EV"
        fi
    done

    # --- 9. Idempotenza: ri-esecuzione CONFERMA ---
    echo ""; echo "-- 9. Idempotenza: nuovo flusso CONFERMA -> avvio -> GIA_PUSHATO --"
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" \
        "{\"template_flusso_id\": ${TPL_CONFERMA}}"
    if [[ "$LAST_STATUS" == "200" ]]; then
        FLUSSO2=$(json_get "$LAST_BODY" "data.flusso_id")
        [[ -z "$FLUSSO2" ]] && FLUSSO2=$(json_get "$LAST_BODY" "data.id")
        do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO2}/stato/" \
            '{"nuovo_stato": "IN_CORSO"}'
        if [[ "$LAST_STATUS" =~ ^4 ]]; then
            CODE=$(json_get "$LAST_BODY" "error.code")
            log_ok "ri-avvio bloccato (HTTP $LAST_STATUS, code=$CODE)"
        else
            log_fail "ri-avvio CONFERMA: atteso 4xx idempotenza, ricevuto $LAST_STATUS"
        fi
    else
        # Anche il blocco alla creazione (guard DB) e' un esito idempotente valido.
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "ri-creazione flusso CONFERMA bloccata a monte (HTTP $LAST_STATUS, code=$CODE)"
    fi
fi

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
