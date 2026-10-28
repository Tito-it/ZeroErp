#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Giro pratica PREVENTIVI 9004 BIVIO-PER-ESITO end-to-end
# (rev.3, brief-db-chiusura-pratica-nessun-lavoro-pendente).
# Uso: ./scripts/tests/smoke-test-pratica-preventivi-bivio.sh [password]
#      (oppure SMOKE_PASSWORD=... ; utente: SMOKE_USER, vedi _smoke_auth.sh)
#
# Copre contro DB+API reali il percorso del tipo unico PREVENTIVI (9004):
# RICHIESTA_CLIENTE(9009) -> PREVENTIVAZIONE(9010) -> APPROVAZIONE_CLIENTE(9011)
# -> SMISTAMENTO(9012) -> [ramo merce] CONFERMA_ORDINE(9013) -> INVIO_COMMESSA(9014).
#
# Due scenari (i due rami del bivio):
#  A) MISTO (merce + servizio): completa-smistamento => esito MERCE_PRESENTE =>
#     pratica RESTA APERTA; conferma ordine (auto-completa 9013) => push a commessa
#     (auto-completa 9014, terminale) => pratica SI CHIUDE.
#  B) TUTTO-SERVIZI: completa-smistamento => esito SOLO_SERVIZI => 9013/9014 ramo
#     morto => pratica SI CHIUDE subito.
#
# Prerequisiti dev: seed pratiche + bivio (changeset 20260701-*), tipo 9004,
# emittente valido (default 32, override EMITTENTE_ID), articolo merce a catalogo.
# L'articolo servizio SMOKE-SERV-UT viene riusato/creato via API.
# Auto-diagnosi: se /emetti/ fallisce per prerequisiti documentali i passi a valle
# vengono SALTATI con diagnosi. Nessun cleanup: pratiche/preventivi restano in
# stati terminali; articolo servizio riusato per codice fisso.
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_pratiche.sh"    # smoke_tipo_prestazione
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_emetti

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

# do_curl METHOD URL [DATA]. I POST portano sempre una Idempotency-Key unica
# (richiesta da completa-smistamento / push-commessa; innocua altrove).
do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        local idem="smoke-$(date +%s%N)-$RANDOM"
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -H "Idempotency-Key: $idem" \
            -d "$data" "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
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
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/" "{\"template_flusso_id\": ${template_id}}"
    if ! check "POST crea flusso $label" 200 "data.flusso_id"; then FLUSSO_ID=""; return 1; fi
    FLUSSO_ID="$EXTRACTED"; [[ -z "$FLUSSO_ID" ]] && FLUSSO_ID=$(json_get "$LAST_BODY" "data.id")
    log_info "flusso_id ($label) = $FLUSSO_ID"
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/stato/" '{"nuovo_stato": "IN_CORSO"}'
    check "POST avvia $label -> IN_CORSO" 200 || return 1
    return 0
}

completa_flusso_generico() {  # flusso_id label esito
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/flussi/${1}/stato/" \
        "{\"nuovo_stato\": \"COMPLETATO\", \"esito\": \"${3}\"}"
    check "POST completa ${2} (${3})" 200
}

pratica_stato() {
    do_curl GET "/api/v1/pratiche/${PRATICA_ID}/"
    json_get "$LAST_BODY" "data.stato_codice_interno"
}

# --- 0. Auth ---
echo "== Smoke pratica PREVENTIVI 9004 — BIVIO-PER-ESITO =="
smoke_login --senza-prompt --uscita 2
log_ok "Autenticazione JWT"
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

# --- 1. Setup: tripla BA+utility + articoli ---
echo ""; echo "-- 1. Setup: tripla BA (lookup, o preventivo esistente) + articolo merce + servizio --"
# Il cliente dal BB (_smoke_cliente.sh); il preventivo esistente e' il ripiego.
# Nessun emittente nel payload del preventivo: vale quello attivo, lo stesso del
# cliente del lookup.
smoke_cliente_dal_lookup
PREV_PAYLOAD=""
[[ -n "$BA_ID" ]] && PREV_PAYLOAD="{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}, \"istanza_utility_id\": ${ISTANZA_ID}}"
[[ -z "$PREV_PAYLOAD" ]] && PREV_PAYLOAD=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/vendite/preventivi/?limit=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    x = r[0] if r else {}
    p = {k: x[k] for k in ('billing_account_id','utility_id','istanza_utility_id') if x.get(k)}
    print(json.dumps(p) if p else '')
except Exception: print('')
" 2>/dev/null)
[[ -z "$PREV_PAYLOAD" ]] && { echo -e "${RED}Setup fallito: nessun cliente (lookup) e nessun preventivo da cui derivare la tripla BA.${NC}"; exit 1; }
log_info "payload preventivo base = $PREV_PAYLOAD"

smoke_articolo_merce   # BB _smoke_documenti.sh: una MERCE (va in un ordine/bolla)
[[ -z "$ARTICOLO_ID" ]] && { echo -e "${RED}Setup fallito: catalogo vuoto.${NC}"; exit 1; }
log_info "articolo merce = $ARTICOLO_ID"

SERV_CODICE="SMOKE-SERV-UT"
SERV_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?search=${SERV_CODICE}&limit=5" 2>/dev/null | python3 -c "
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
    check "POST crea articolo servizio" 200 "data.id" && SERV_ID="$EXTRACTED" || SERV_ID=""
fi
[[ -z "$SERV_ID" ]] && { echo -e "${RED}Setup fallito: articolo servizio non disponibile.${NC}"; exit 1; }
log_ok "articolo servizio = $SERV_ID"

# ============================================================
#  run_scenario NOME CON_MERCE CON_SERVIZIO ESITO_ATTESO CHIUSURA_A_SMISTAMENTO
# ============================================================
run_scenario() {
    local NOME="$1" CON_MERCE="$2" CON_SERV="$3" ESITO_ATT="$4" CHIUDE_SMIST="$5"
    echo ""; echo "############ SCENARIO: $NOME (esito atteso: $ESITO_ATT) ############"

    # 2. Pratica 9004 -> APERTA
    do_curl POST "/api/v1/pratiche/" "{\"emittente_fiscale_id\": $EMITTENTE_FISCALE_ID, \"tipo_prestazione_id\": $TIPO_PRESTAZIONE_ID, \"priorita_id\": $PRIORITA_ID, \"descrizione\": \"Smoke bivio $NOME\"}"
    check "POST crea pratica 9004" 200 "data.pratica_id" || return 1
    PRATICA_ID="$EXTRACTED"; log_info "pratica_id = $PRATICA_ID"
    do_curl POST "/api/v1/pratiche/${PRATICA_ID}/stato/" '{"nuovo_stato": "APERTA"}'; check "pratica -> APERTA" 200 || true

    # 3. Percorso
    do_curl GET "/api/v1/pratiche/${PRATICA_ID}/percorso/"; check "GET percorso" 200 || true
    local T_RICH T_PREV T_APPR T_SMIST T_CONF T_INVIO
    T_RICH=$(percorso_template_id "RICHIESTA_CLIENTE"); T_PREV=$(percorso_template_id "PREVENTIVAZIONE")
    T_APPR=$(percorso_template_id "APPROVAZIONE_CLIENTE"); T_SMIST=$(percorso_template_id "SMISTAMENTO")
    T_CONF=$(percorso_template_id "CONFERMA_ORDINE"); T_INVIO=$(percorso_template_id "INVIO_COMMESSA")
    if [[ -z "$T_RICH" || -z "$T_PREV" || -z "$T_APPR" || -z "$T_SMIST" || -z "$T_CONF" || -z "$T_INVIO" ]]; then
        log_fail "Percorso 9004 incompleto (RICH=$T_RICH PREV=$T_PREV APPR=$T_APPR SMIST=$T_SMIST CONF=$T_CONF INVIO=$T_INVIO)"
        echo "       Body: $(echo "$LAST_BODY" | head -c 400)"; return 1
    fi
    log_ok "Percorso 9004 completo (6 step della catena bivio)"

    # 4. RICHIESTA_CLIENTE
    crea_e_avvia_flusso "$T_RICH" "RICHIESTA_CLIENTE" && completa_flusso_generico "$FLUSSO_ID" "RICHIESTA_CLIENTE" "POSITIVO" || true

    # 5. PREVENTIVAZIONE: preventivo + righe (merce/servizio secondo scenario) + emetti
    crea_e_avvia_flusso "$T_PREV" "PREVENTIVAZIONE" || return 1
    local F_PREV="$FLUSSO_ID"
    do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
    check "POST crea preventivo" 200 "data.id" || return 1
    PREV_ID="$EXTRACTED"; log_info "preventivo_id = $PREV_ID"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/collega-pratica/" "{\"pratica_id\": ${PRATICA_ID}}"
    check "POST collega-pratica (ROOT)" 200 || true
    if [[ "$CON_MERCE" == "1" ]]; then
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
            "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"2\", \"prezzo_unitario\": \"100.00\"}"
        check "POST riga merce" 200 || true
    fi
    if [[ "$CON_SERV" == "1" ]]; then
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
            "{\"articolo_id\": \"$SERV_ID\", \"qta_operativa\": \"1\", \"prezzo_unitario\": \"50.00\"}"
        check "POST riga servizio" 200 || true
    fi
    # EMESSO via multipart (prereq documentale template/emittente)
    smoke_emetti preventivi "${PREV_ID}"   # BB _smoke_documenti.sh
    if [[ "$LAST_STATUS" != "200" ]]; then
        log_skip "EMESSO HTTP $LAST_STATUS — prereq documentale assente, salto lo scenario"
        log_info "Body: $(echo "$LAST_BODY" | head -c 200)"; return 0
    fi
    log_ok "POST /emetti/ -> EMESSO"
    completa_flusso_generico "$F_PREV" "PREVENTIVAZIONE" "POSITIVO" || true

    # 6. APPROVAZIONE_CLIENTE: il DOCUMENTO e' sovrano (GUIDA D4, inversione
    #    handler -> proiezione). Si accetta il preventivo dalla pratica, e il
    #    passo della pratica avanza da solo (trigger pratiche.fn_reconcile_sorgente).
    #    Fino al 2026-10-13 lo smoke completava il flusso e aspettava che
    #    l'handler `vendita.accetta_preventivo` accettasse il preventivo: la
    #    direzione vecchia, con un handler che il backend ha ritirato.
    crea_e_avvia_flusso "$T_APPR" "APPROVAZIONE_CLIENTE" || return 1
    F_APPR="$FLUSSO_ID"
    do_curl POST "/api/v1/vendite/preventivi/da-pratica/${PRATICA_ID}/stato/" \
        '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
    check "POST accetta preventivo da-pratica" 200 || return 1
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/"
    [[ "$(json_get "$LAST_BODY" "data.stato_codice_interno")" == "ACCETTATO" ]] \
        && log_ok "preventivo ACCETTATO (documento sovrano)" || { log_fail "preventivo non ACCETTATO"; return 1; }
    do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${F_APPR}/"
    local sf se
    sf=$(json_get "$LAST_BODY" "data.stato_codice_interno"); se=$(json_get "$LAST_BODY" "data.esito")
    [[ "$sf" == "COMPLETATO" && "$se" == "POSITIVO" ]] \
        && log_ok "APPROVAZIONE_CLIENTE auto-avanzato COMPLETATO/POSITIVO (proiezione)" \
        || log_fail "APPROVAZIONE_CLIENTE atteso COMPLETATO/POSITIVO, e' ${sf:-?}/${se:-?}"

    # 7. SMISTAMENTO: crea flusso, split (genera-ordine / push-commessa), completa-smistamento
    crea_e_avvia_flusso "$T_SMIST" "SMISTAMENTO" || return 1
    if [[ "$CON_MERCE" == "1" ]]; then
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/genera-ordine/" "{}"
        check "POST genera-ordine (merce)" 200 || true
    fi
    if [[ "$CON_SERV" == "1" ]]; then
        do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/push-commessa/" "{}"
        check "POST push-commessa (servizi)" 200 || true
    fi
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/completa-smistamento/" "{}"
    check "POST completa-smistamento" 200 "data.esito" || return 1
    local ESITO="$EXTRACTED"
    [[ "$ESITO" == "$ESITO_ATT" ]] && log_ok "esito di ramo = $ESITO (atteso $ESITO_ATT)" \
        || log_fail "esito atteso $ESITO_ATT, ricevuto '$ESITO'"

    # 8. Divergenza per ramo
    local ST
    if [[ "$CHIUDE_SMIST" == "1" ]]; then
        # Ramo servizi: la pratica deve chiudersi subito.
        ST=$(pratica_stato)
        [[ "$ST" == "CHIUSA" ]] && log_ok "ramo SERVIZI: pratica CHIUSA subito (9013/9014 ramo morto)" \
            || log_fail "ramo SERVIZI: pratica attesa CHIUSA, trovata '$ST'"
        return 0
    fi

    # Ramo merce: pratica resta APERTA, poi 9013 (conferma) + 9014 (push) la chiudono.
    ST=$(pratica_stato)
    [[ "$ST" == "APERTA" ]] && log_ok "ramo MERCE: pratica RESTA APERTA (9013/9014 dovuti)" \
        || log_fail "ramo MERCE: pratica attesa APERTA, trovata '$ST'"

    do_curl GET "/api/v1/vendite/ordini/per-pratica/?pratica_id=${PRATICA_ID}"
    local ORDINE_ID; ORDINE_ID=$(json_get "$LAST_BODY" "data.ordine_id")
    [[ -n "$ORDINE_ID" && "$ORDINE_ID" != "None" ]] && log_ok "ordine agganciato alla pratica (id=$ORDINE_ID)" \
        || { log_fail "nessun ordine COLLEGATO alla pratica (handler post_smistamento)"; return 1; }

    # 9013 CONFERMA_ORDINE: crea+avvia flusso, poi conferma ordine (auto-completa 9013).
    # ⭐ La conferma passa da «Emetti» (multipart): `POST /conferma/` e'
    #    ritirato dal 2026-10-25 (Z-2, brief-modello-documento-vendita §9.6).
    crea_e_avvia_flusso "$T_CONF" "CONFERMA_ORDINE" || return 1
    smoke_emetti ordini "${ORDINE_ID}"   # BB _smoke_documenti.sh
    if [[ "$SMOKE_EMETTI_SENZA_MODELLO" == "1" ]]; then
        log_skip "conferma ordine: nessun modello di documento per l'ordine, salto 9013/9014"
        return 0
    fi
    check "POST emetti ordine -> CONFERMATO (auto-completa 9013)" 200 || true
    do_curl GET "/api/v1/pratiche/${PRATICA_ID}/flussi/${FLUSSO_ID}/"
    [[ "$(json_get "$LAST_BODY" "data.stato_codice_interno")" == "COMPLETATO" ]] \
        && log_ok "flusso CONFERMA_ORDINE COMPLETATO (auto su conferma)" || log_fail "CONFERMA_ORDINE non COMPLETATO"

    # 9014 INVIO_COMMESSA: crea+avvia flusso, poi push ordine->commessa (auto-completa 9014, terminale)
    crea_e_avvia_flusso "$T_INVIO" "INVIO_COMMESSA" || return 1
    do_curl POST "/api/v1/vendite/ordini/${ORDINE_ID}/push/" "{}"
    check "POST push ordine->commessa (auto-completa 9014)" 200 || true

    # 10. Chiusura della pratica (auto, motore data-driven)
    ST=$(pratica_stato)
    [[ "$ST" == "CHIUSA" ]] && log_ok "ramo MERCE: pratica SI CHIUDE a INVIO_COMMESSA (nessun lavoro pendente)" \
        || log_fail "ramo MERCE: pratica attesa CHIUSA dopo push, trovata '$ST'"
    return 0
}

# --- Scenari ---
run_scenario "MISTO/MERCE"  1 1 "MERCE_PRESENTE" 0 || true
run_scenario "TUTTO-SERVIZI" 0 1 "SOLO_SERVIZI"  1 || true

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
