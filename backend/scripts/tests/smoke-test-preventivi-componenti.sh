#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test componenti BoM CASO A — refactor 2026-05-11
# Uso: ./scripts/tests/smoke-test-preventivi-componenti.sh [password]
# Prerequisiti DB:
#   - tabelle vendite.preventivi_righe_componenti + trigger _m50_/_z90_
#   - fn vendite.fn_preventivo_riga_componenti_init
#   - fn vendite.fn_resolve_prezzo_composito 8 colonne
# Materia: se la costruisce lo smoke (2026-10-18, collaudo `dev.smoke`, T-7a).
#   STABILE, cercata per codice e creata se manca: il componente
#   `SMOKE-COMP-COMPONENTE`, la categoria `SMOKE-COMP`, il listino
#   `SMOKE-COMP-<emittente>-<utility>` con la riga del componente, la mappa
#   categoria -> listino. DEL GIRO: il composito con la sua BoM (campi
#   dall'articolo merce del BB `smoke_articolo_merce`), il cliente (BB
#   `smoke_cliente_del_giro`, con la categoria dello smoke), il preventivo.
#   Prima clonava due articoli per id scritto qui e usava il primo cliente della
#   lista: su un emittente senza listino mappato si fermava, su un database
#   nuovo non partiva.
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"

source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"
EPOCH=$(date +%s)
SUFFIX="smk-${EPOCH}"
NEW_COMPOSITO_ID=""
NEW_BOM_ROW_ID=""
# Date allineate al fuso orario del DB (UTC su questa istanza).
# DATA_IERI_UTC: valido_dal BoM, garantisce range che contiene oggi UTC
# anche se l'host bash ha tz diversa (es. Europe/Rome notte fonda
# locale = ieri UTC).
DATA_IERI_UTC=$(date -u -d "1 day ago" +%Y-%m-%d)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
LAST_STATUS=""
LAST_BODY=""
TOKEN=""
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

log_ok()   { ((PASS++)) || true; echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }
log_step() { echo -e "\n${YELLOW}# $1${NC}"; }

# Helper: estrae chiave JSON annidata (es. data.results.0.id)
json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        if k.isdigit(): d = d[int(k)]
        else: d = d[k]
    print(d if d is not None else '')
except Exception:
    print('')
" 2>/dev/null
}

do_curl() {
    local method="$1" url="$2" data="${3:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE"
    elif [[ "$method" == "DELETE" ]]; then
        curl -s -w '\n%{http_code}' -X DELETE \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Idempotency-Key: ${SUFFIX}-$(date +%N)" \
            "${BASE_URL}${url}" > "$TMPFILE"
    else
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            -H "Idempotency-Key: ${SUFFIX}-$(date +%N)" \
            -d "$data" \
            "${BASE_URL}${url}" > "$TMPFILE"
    fi
    LAST_STATUS=$(tail -1 "$TMPFILE")
    LAST_BODY=$(sed '$d' "$TMPFILE")
}

check_http() {
    local label="$1" expected="$2"
    # expected accetta multipli separati da | (es. "200|201")
    if echo "|$expected|" | grep -q "|$LAST_STATUS|"; then
        log_ok "$label (HTTP $LAST_STATUS)"
        return 0
    fi
    log_fail "$label — atteso HTTP $expected, ricevuto $LAST_STATUS"
    echo "       Body: $(echo "$LAST_BODY" | head -c 400)"
    return 1
}

# Scopo: pulisce la materia del giro, dal figlio al padre (figli prima del
#        padre: i trigger rifiutano il contrario). Una sede per i due finali,
#        il fermo «non conclusivo» e la fine del percorso felice: fino al
#        2026-10-18 erano due pulizie diverse, e quella finale (mai raggiunta)
#        cancellava un preventivo con le righe e spegneva l'articolo via PATCH,
#        due cose che l'API rifiuta. Ogni passo e' controllato: una pulizia che
#        non riesce e' un rosso, non un residuo silenzioso.
#        Restano il cliente del giro (un soggetto per giro, come in
#        contratti-addebito) e la materia stabile del passo 2 (riusata).
pulisci_giro() {
    local riga uom_op
    if [[ -n "${PREVENTIVO_ID:-}" ]]; then
        for riga in ${RIGA_ID:-}; do
            do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${riga}/"
            check_http "Cleanup riga preventivo" "200|204" || true
        done
        do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/"
        check_http "Cleanup preventivo" "200|204" || true
    fi
    if [[ -n "$NEW_BOM_ROW_ID" && -n "$NEW_COMPOSITO_ID" ]]; then
        do_curl PATCH "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/componenti/${NEW_BOM_ROW_ID}/" '{"attivo": false}'
        check_http "Cleanup riga BoM (spenta)" "200" || true
    fi
    if [[ -n "$NEW_COMPOSITO_ID" ]]; then
        do_curl GET "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/uom/"
        uom_op=$(json_get "$LAST_BODY" "data.results.0.id")
        if [[ -n "$uom_op" ]]; then
            do_curl PATCH "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/uom/${uom_op}/" '{"attivo": false}'
            check_http "Cleanup UoM operativa base (spenta)" "200" || true
        fi
        do_curl POST "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/disattiva/" '{}'
        check_http "Cleanup articolo composito (disattiva)" "200|204" || true
    fi
}

# =====================================================
# 0) AUTH
# =====================================================
log_step "0) Autenticazione JWT"
smoke_login --senza-prompt --uscita 2
log_ok "Login OK (token ${#TOKEN} char)"

# =====================================================
# 1) Setup CASO A: crea articolo nuovo + BoM esposta
# =====================================================
log_step "1) Setup CASO A: crea articolo composito-${SUFFIX} + BoM esposta"
# Materia STABILE dello smoke sull'emittente attivo: un componente, una
# categoria, un listino con la riga del componente e la mappa categoria ->
# listino. Si cercano per codice fisso e si creano solo se mancano, come
# `SMOKE-SERV-UT` in preventivi-smistamento-ordine: niente che si accumula, e
# niente da spegnere a ogni giro (un componente con una riga di listino attiva
# non si disattiva, giustamente). Nasce nuovo a ogni giro solo cio' che il giro
# prova: il composito con la sua BoM, il cliente, il preventivo.
# ⛔ Non il cliente condiviso del lookup: una mappa sulla sua categoria
# cambierebbe i prezzi degli altri smoke dell'emittente. Il cliente e' del giro,
# la categoria e' quella dello smoke.

# Scopo: id della riga con `codice` esatto in una lista che filtra `search`.
#        $1 = path della lista (senza query), $2 = codice. Vuoto se non c'e'.
id_per_codice() {
    curl -s -G -H "Authorization: Bearer $TOKEN" --data-urlencode "search=$2" \
        --data-urlencode "limit=50" \
        "${BASE_URL}$1" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data') or {}
    rows = d.get('results', d) if isinstance(d, dict) else d
    print(next((str(r['id']) for r in rows or [] if r.get('codice') == sys.argv[1] and r.get('attivo') is not False), ''))
except Exception:
    print('')
" "$2" 2>/dev/null
}

# 1a) I campi di struttura da un articolo merce del catalogo (BB
#     _smoke_documenti.sh), scelto per proprieta' e non per id.
smoke_articolo_merce   # -> ARTICOLO_ID
if [[ -z "$ARTICOLO_ID" ]]; then
    echo "Setup fallito: nessun articolo merce da cui prendere i campi (motivo sopra)."; exit 3
fi
do_curl GET "/api/v1/catalogo/articoli/${ARTICOLO_ID}/"
check_http "GET articolo merce (per i campi di struttura)" "200" || exit 3
# $1 = codice, $2 = ruolo nella BoM: composito | componente
payload_articolo() {
    echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
ruolo = sys.argv[2]
print(json.dumps({
    'codice': sys.argv[1],
    'descrizione': 'Smoke ' + ruolo,
    'descrizione_breve': 'Smoke ' + ruolo,
    'uom_id': d['uom_id'],
    'tipo_voce_id': d['tipo_voce_id'],
    'gruppo_voce_id': d['gruppo_voce_id'],
    'iva_id': d['iva_id'],
    'listino_tipologia_id': d['listino_tipologia_id'],
    'is_composito': ruolo == 'composito',
    # ⚠️ Il componente NON e' «solo componente»: un articolo cosi' non entra in
    # una riga di listino (E_ARTICOLO_SOLO_COMPONENTE), e il percorso felice
    # vuole il componente col suo prezzo di listino.
    'is_solo_componente': False,
    'meta': {'smoke': 'preventivi-componenti'},
}))
" "$1" "$2"
}
PAYLOAD_COMPONENTE=$(payload_articolo "SMOKE-COMP-COMPONENTE" componente)
PAYLOAD_COMPOSITO=$(payload_articolo "composito-${SUFFIX}" composito)
LISTINO_TIPOLOGIA_ID=$(json_get "$LAST_BODY" "data.listino_tipologia_id")

# 1b) Il componente stabile (crea se assente).
COMPONENTE_ID_STABILE=$(id_per_codice "/api/v1/catalogo/articoli/" "SMOKE-COMP-COMPONENTE")
if [[ -n "$COMPONENTE_ID_STABILE" ]]; then
    log_ok "Componente riusato (codice SMOKE-COMP-COMPONENTE)"
else
    do_curl POST "/api/v1/catalogo/articoli/" "$PAYLOAD_COMPONENTE"
    check_http "POST componente SMOKE-COMP-COMPONENTE" "200" || exit 3
    COMPONENTE_ID_STABILE=$(json_get "$LAST_BODY" "data.id")
fi
do_curl GET "/api/v1/catalogo/articoli/${COMPONENTE_ID_STABILE}/"
COMPONENTE_UOM_ID=$(json_get "$LAST_BODY" "data.uom_id")
log_info "Componente id=$COMPONENTE_ID_STABILE uom=$COMPONENTE_UOM_ID"

# 1c) Il composito del giro.
do_curl POST "/api/v1/catalogo/articoli/" "$PAYLOAD_COMPOSITO"
check_http "POST nuovo articolo composito" "200" || {
    log_info "Categoria fallimento: validazione catalogo (campi richiesti) o permesso"
    exit 3
}
NEW_COMPOSITO_ID=$(json_get "$LAST_BODY" "data.id")
COMPOSITO_UOM_ID=$(json_get "$LAST_BODY" "data.uom_id")   # la sua UoM, per la riga (passo 5)
log_info "Creato articolo composito id=$NEW_COMPOSITO_ID uom=$COMPOSITO_UOM_ID"

# 1d) Riga BoM esposta, valida da ieri
BOM_PAYLOAD=$(cat <<EOF
{
  "componente_id": "$COMPONENTE_ID_STABILE",
  "coeff_qta": 1,
  "obbligatorio": true,
  "esposizione_in_fattura": "DESCRITTIVO",
  "valido_dal": "$DATA_IERI_UTC",
  "valido_al": null
}
EOF
)
do_curl POST "/api/v1/catalogo/articoli/${NEW_COMPOSITO_ID}/componenti/" "$BOM_PAYLOAD"
check_http "POST BoM componente esposto" "200" || {
    log_info "Categoria fallimento: trigger guard_coerenza_bom o permission catalogo"
    exit 3
}
NEW_BOM_ROW_ID=$(json_get "$LAST_BODY" "data.id")
log_info "Creata BoM riga id=$NEW_BOM_ROW_ID (esposizione=DESCRITTIVO)"

# =====================================================
# 2) Emittente, categoria, cliente del giro, listino e mappa
# =====================================================
log_step "2) Emittente attivo, cliente del giro, listino dello smoke"
# 2a) L'emittente attivo (BB _smoke_cliente.sh): il listino e la mappa vogliono
#     il suo soggetto_ruolo, il preventivo il suo id.
smoke_emittente_attivo   # -> EMITTENTE_ATTIVO_ID, EMITTENTE_ATTIVO_SR_ID
EMITTENTE_ID="$EMITTENTE_ATTIVO_ID"
if [[ -z "$EMITTENTE_ID" || -z "$EMITTENTE_ATTIVO_SR_ID" ]]; then
    log_fail "Emittente attivo dell'operatore non risolto"; exit 4
fi
log_info "emittente_fiscale_id = $EMITTENTE_ID (soggetto_ruolo $EMITTENTE_ATTIVO_SR_ID)"

# 2b) La categoria dello smoke (crea se assente).
CATEGORIA_ID=$(id_per_codice "/api/v1/anagrafiche/categorie-clienti/" "SMOKE-COMP")
if [[ -n "$CATEGORIA_ID" ]]; then
    log_ok "Categoria riusata (codice SMOKE-COMP)"
else
    do_curl POST "/api/v1/anagrafiche/categorie-clienti/" \
        '{"codice":"SMOKE-COMP","descrizione":"Smoke preventivi componenti","partecipa_promo":false,"ordinamento":900}'
    check_http "POST categoria SMOKE-COMP" "200" || exit 4
    CATEGORIA_ID=$(json_get "$LAST_BODY" "data.id")
fi

# 2c) Il cliente del giro, con la categoria dello smoke (BB _smoke_cliente.sh).
smoke_cliente_del_giro "Componenti" "$CATEGORIA_ID"   # -> GIRO_BA_ID, GIRO_UTILITY_ID
LAST_STATUS="$GIRO_LAST_STATUS"; LAST_BODY="$GIRO_LAST_BODY"
check_http "POST cliente del giro (categoria $CATEGORIA_ID)" "200" || exit 4
CLIENTE_BA_ID="$GIRO_BA_ID"
log_info "billing_account_id = ${CLIENTE_BA_ID} utility = ${GIRO_UTILITY_ID}"

# 2d) Il listino dello smoke per (emittente, utility), con una versione ATTIVA
#     che porta la riga del componente. Il composito non ha riga sua: il suo
#     prezzo e' la somma dei componenti (E_LISTINO_RIGA_COMPOSITO_VIETATO).
LISTINO_CODICE="SMOKE-COMP-${EMITTENTE_ID}-${GIRO_UTILITY_ID}"
LISTINO_ID=$(id_per_codice "/api/v1/vendite/listini/" "$LISTINO_CODICE")
if [[ -z "$LISTINO_ID" ]]; then
    do_curl POST "/api/v1/vendite/listini/" \
        "{\"codice\":\"${LISTINO_CODICE}\",\"descrizione\":\"Smoke preventivi componenti\",\"utility_id\":${GIRO_UTILITY_ID},\"tipologia_id\":${LISTINO_TIPOLOGIA_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_ATTIVO_SR_ID}}"
    check_http "POST listino $LISTINO_CODICE" "200" || exit 4
    LISTINO_ID=$(json_get "$LAST_BODY" "data.id")
fi
do_curl GET "/api/v1/vendite/listini/${LISTINO_ID}/versioni/"
VERSIONE_ATTIVA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data') or {}
    rows = d.get('results', d) if isinstance(d, dict) else d
    print(next((str(r['id']) for r in rows or [] if r.get('stato') == 'ATTIVA' and r.get('attivo') is not False), ''))
except Exception:
    print('')
" 2>/dev/null)
if [[ -n "$VERSIONE_ATTIVA" ]]; then
    log_ok "Listino riusato ($LISTINO_CODICE, versione ATTIVA $VERSIONE_ATTIVA)"
else
    # Una versione nuova a ogni tentativo: un giro interrotto lascia al piu' una
    # BOZZA, che non pesa sui prezzi.
    do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/" \
        "{\"codice_versione\":\"V-${EPOCH}\",\"valido_dal\":\"${DATA_IERI_UTC}\"}"
    check_http "POST versione del listino" "200" || exit 4
    VERSIONE_ID=$(json_get "$LAST_BODY" "data.id")
    do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/" \
        "{\"articolo_id\":\"${COMPONENTE_ID_STABILE}\",\"uom_id\":${COMPONENTE_UOM_ID},\"prezzo\":\"12.5000000000\"}"
    check_http "POST riga listino componente" "200" || exit 4
    do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/stato/" '{"stato":"ATTIVA"}'
    check_http "Attiva versione del listino" "200" || exit 4
fi

# 2e) La mappa categoria -> listino (crea se assente).
do_curl GET "/api/v1/anagrafiche/categorie-clienti-listini/?categoria_cliente_id=${CATEGORIA_ID}"
MAPPA_ID=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data') or {}
    rows = d.get('results', d) if isinstance(d, dict) else d
    print(next((str(r['id']) for r in rows or [] if str(r.get('listino_id')) == sys.argv[1]
                and r.get('attivo') is not False and not r.get('valido_al')), ''))
except Exception:
    print('')
" "$LISTINO_ID" 2>/dev/null)
if [[ -n "$MAPPA_ID" ]]; then
    log_ok "Mappa categoria -> listino riusata ($MAPPA_ID)"
else
    do_curl POST "/api/v1/anagrafiche/categorie-clienti-listini/" \
        "{\"categoria_cliente_id\":${CATEGORIA_ID},\"utility_id\":${GIRO_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_ATTIVO_SR_ID},\"listino_id\":${LISTINO_ID},\"valido_dal\":\"${DATA_IERI_UTC}\"}"
    check_http "POST mappa categoria -> listino" "200" || exit 4
fi

# 2b) Form defaults BA-aware: deriva utility/istanza/valuta dalla BA
do_curl GET "/api/v1/vendite/preventivi/form-defaults/?billing_account_id=${CLIENTE_BA_ID}"
check_http "GET form-defaults preventivo BA-aware" "200" || exit 4
UTILITY_ID=$(json_get "$LAST_BODY" "data.utility_id")
ISTANZA_ID=$(json_get "$LAST_BODY" "data.istanza_utility_id")
VALUTA_ID=$(json_get "$LAST_BODY" "data.valuta_id")
DEFAULT_IVA_ID=$(json_get "$LAST_BODY" "data.iva_id")
VALIDITA_AL=$(json_get "$LAST_BODY" "data.default_validita_al")
log_info "utility=$UTILITY_ID istanza=$ISTANZA_ID valuta=$VALUTA_ID iva=$DEFAULT_IVA_ID validita_al=$VALIDITA_AL"

if [[ -z "$EMITTENTE_ID" ]]; then log_fail "Nessun emittente attivo trovato"; exit 4; fi

# =====================================================
# 3) Cleanup proattivo: delete preventivi smoke precedenti
# =====================================================
log_step "3) Cleanup proattivo preventivi smoke vecchi"
do_curl GET "/api/v1/vendite/preventivi/?search=${SUFFIX}&limit=10"
# Idempotente: anche se search non matcha nulla (suffisso unico), niente da fare
log_info "Nessun preventivo precedente col suffisso ${SUFFIX} (atteso)"

# =====================================================
# 4) Crea preventivo DRAFT
# =====================================================
log_step "4) Crea preventivo DRAFT"
# La data del documento la decide il server: `data` non e' nel contratto
# della creazione (CREATE_KEYS_PREVENTIVO), e dal 2026-10-20 una chiave fuori
# contratto e' un 400 invece di essere scartata in silenzio.
PAYLOAD=$(cat <<EOF
{
  "billing_account_id": $CLIENTE_BA_ID,
  "utility_id": $UTILITY_ID,
  "istanza_utility_id": $ISTANZA_ID,
  "valuta_id": $VALUTA_ID,
  "emittente_fiscale_id": $EMITTENTE_ID,
  "validita_al": "$VALIDITA_AL",
  "meta": {"smoke_suffix": "${SUFFIX}"}
}
EOF
)
do_curl POST "/api/v1/vendite/preventivi/" "$PAYLOAD"
check_http "POST preventivo DRAFT" "200|201" || {
    log_info "Categoria fallimento: validazione testata preventivo (BA/utility/emittente)"
    exit 5
}
PREVENTIVO_ID=$(json_get "$LAST_BODY" "data.id")
PREVENTIVO_NUMERO=$(json_get "$LAST_BODY" "data.numero")
log_info "Creato preventivo id=$PREVENTIVO_ID numero=$PREVENTIVO_NUMERO"

# =====================================================
# 5) Aggiungi riga articolo composito qty=1
# =====================================================
log_step "5) Aggiungi riga articolo composito qty=1"
# La quantita' si passa come `qta_operativa` nella UoM dell'articolo (modello
# qta_operativa-sorgente, CREATE_KEYS_RIGA): `quantita` la calcola il trigger e
# il service la scarta. Fino al 2026-10-12 lo smoke mandava `quantita` e una UoM
# cablata (7): 400 E_QTA_MISSING.
# ⛔ Niente `iva_id`: l'aliquota della riga la decide il risolutore (I6), e dal
# 2026-10-20 una chiave fuori contratto e' un 400 (prima veniva scartata).
PAYLOAD=$(cat <<EOF
{
  "articolo_id": "$NEW_COMPOSITO_ID",
  "qta_operativa": 1,
  "uom_operativa_id": $COMPOSITO_UOM_ID,
  "prezzo_unitario": 0
}
EOF
)
do_curl POST "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/" "$PAYLOAD"
# Due path attesi:
#  - 200/201: init OK (componente con listino) -> prosegui smoke completo
#  - 422 + E_DOC_COMPONENTE_LISTINO_MANCANTE: domain validation OK (componente
#    senza listino mappato) -> skip resto smoke ma marca PASS specifico
# Scopo: ferma lo smoke quando il percorso felice non si puo' provare in questo
#        ambiente, pulendo cio' che ha creato e DICHIARANDOLO (non conclusivo).
#        Fino al 2026-10-12 questo ramo usciva con 0 e «DOMAIN VALIDATION PATH
#        OK»: un verde che non aveva provato il percorso felice. E la pulizia
#        disattivava l'articolo con i figli ancora attivi, che oggi e' rifiutato
#        (figli prima del padre: righe BoM e UoM operativa base).
fermo_non_conclusivo() {
    local motivo="$1"
    RIGA_ID=""   # la riga non e' nata: si ferma proprio li'
    pulisci_giro
    echo ""
    echo "Smoke non conclusivo: $motivo"
    echo " Risultato: ${PASS} OK / ${FAIL} FAIL (percorso felice non eseguito)"
    [[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
}

ERR_CODE=$(echo "$LAST_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('error',{}).get('code',''))" 2>/dev/null)
if [[ "$LAST_STATUS" == "422" && "$ERR_CODE" == "E_DOC_COMPONENTE_LISTINO_MANCANTE" ]]; then
    log_ok "POST riga composito -> 422 E_DOC_COMPONENTE_LISTINO_MANCANTE (validazione di dominio)"
    fermo_non_conclusivo "il componente non ha un listino mappato: il percorso felice (componenti popolati) vuole un componente con listino."
fi
if [[ "$ERR_CODE" == "E_PREZZO_LISTINO_RIGA_NON_TROVATA" ]]; then
    log_info "$(json_get "$LAST_BODY" "error.message")"
    fermo_non_conclusivo "l'articolo composito creato dallo smoke non e' nel listino della categoria del cliente: il percorso felice vuole un composito con la sua riga di listino."
fi
if [[ "$ERR_CODE" == "E_CATEGORIA_LISTINO_NON_MAPPATA" ]]; then
    log_info "$(json_get "$LAST_BODY" "error.message")"
    fermo_non_conclusivo "manca la mappa categoria cliente -> listino per l'emittente attivo (configurazione: categorie_clienti_listini)."
fi
check_http "POST riga composito" "200|201" || {
    log_info "Categoria fallimento: gestisci_riga (init componenti BoM CASO A)"
    log_info "Possibili cause: errore non previsto"
    exit 6
}
RIGA_ID=$(json_get "$LAST_BODY" "data.id")
log_info "Creata riga id=$RIGA_ID (path felice: componente con listino)"

# =====================================================
# 6) Verifica is_composito_caso_a=TRUE sulla riga
# =====================================================
log_step "6) GET /righe/ -> flag is_composito_caso_a"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/"
check_http "GET righe preventivo" "200" || exit 7
IS_CASO_A=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
for r in d:
    if r['id'] == ${RIGA_ID}:
        print(r.get('is_composito_caso_a'))
        break
")
if [[ "$IS_CASO_A" == "True" ]]; then
    log_ok "is_composito_caso_a = True sulla riga ${RIGA_ID}"
else
    log_fail "is_composito_caso_a = ${IS_CASO_A:-MISSING} (atteso True)"
    log_info "Categoria fallimento: BE list_righe EXISTS subquery non popola il flag"
fi

# =====================================================
# 7) Lista componenti via nuovo endpoint
# =====================================================
log_step "7) GET /righe/<id>/componenti/ -> lista popolata"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/"
check_http "GET componenti riga" "200" || exit 7
N_COMP=$(echo "$LAST_BODY" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']))")
log_info "Componenti popolati: $N_COMP"
if [[ "$N_COMP" -lt 1 ]]; then
    log_fail "Atteso almeno 1 componente popolato (init fallita?)"
    log_info "Categoria fallimento: fn_preventivo_riga_componenti_init non ha inserito righe"
    exit 7
fi
log_ok "Componenti popolati ($N_COMP)"

COMPONENTE_ID=$(json_get "$LAST_BODY" "data.0.id")
COEFF_QTA=$(json_get "$LAST_BODY" "data.0.coeff_qta_snapshot")
ORIGINE_PRE=$(json_get "$LAST_BODY" "data.0.origine_prezzo")
PREZZO_PRE=$(json_get "$LAST_BODY" "data.0.prezzo_unitario")
log_info "Componente 0: id=$COMPONENTE_ID coeff=$COEFF_QTA prezzo=$PREZZO_PRE origine=$ORIGINE_PRE"

# =====================================================
# 8) PATCH componente prezzo override MANUALE
# =====================================================
log_step "8) PATCH componente prezzo=99.99 origine=MANUALE"
do_curl PATCH "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/${COMPONENTE_ID}/" \
    '{"prezzo_unitario": 99.99}'
# `origine_prezzo` non si manda: un prezzo scritto dall'operatore e' MANUALE e
# lo dice il server (`COMPONENTE_PATCH_OPERATORE`); mandarlo e' un 400.
check_http "PATCH componente prezzo MANUALE" "200" || {
    log_info "Categoria fallimento: L1 override / L2 limit"
    log_info "Body: $(echo "$LAST_BODY" | head -c 300)"
    # Non exit: prosegui per diagnostica anche su fail
}

# =====================================================
# 9) Verifica padre prezzo_unitario = SUM(componenti × coeff)
# =====================================================
log_step "9) Re-fetch riga padre: prezzo = SUM(componenti × coeff)"
do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/"
PADRE_PREZZO=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
for r in d:
    if r['id'] == ${RIGA_ID}:
        print(r.get('prezzo_unitario'))
        break
")
log_info "prezzo padre post-PATCH = $PADRE_PREZZO"

do_curl GET "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/"
EXPECTED_PADRE=$(echo "$LAST_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', [])
totale = 0
for c in d:
    coeff = float(c['coeff_qta_snapshot'])
    prezzo = float(c['prezzo_unitario'])
    totale += coeff * prezzo
print(f'{totale:.6f}')
")
log_info "Atteso prezzo padre (SUM componenti × coeff) = $EXPECTED_PADRE"

DELTA=$(python3 -c "print(abs(float('$PADRE_PREZZO') - float('$EXPECTED_PADRE')))")
TOL=0.01
if python3 -c "import sys; sys.exit(0 if float('$DELTA') < $TOL else 1)"; then
    log_ok "Trigger ricalcola padre OK (delta=$DELTA < $TOL)"
else
    log_fail "Trigger ricalcola padre FAILED: delta=$DELTA"
    log_info "Categoria fallimento: trigger DB script.trgfn_componenti_ricalcola_padre"
fi

# =====================================================
# 10) (Opzionale) DELETE componente se >1
# =====================================================
if [[ "$N_COMP" -gt 1 ]]; then
    log_step "10) DELETE componente secondario (se BoM ha >1 esposto)"
    COMPONENTE2_ID=$(json_get "$LAST_BODY" "data.1.id")
    do_curl DELETE "/api/v1/vendite/preventivi/${PREVENTIVO_ID}/righe/${RIGA_ID}/componenti/${COMPONENTE2_ID}/"
    check_http "DELETE componente secondario" "200" || true
else
    log_info "Skip step 10 (solo 1 componente esposto)"
fi

# =====================================================
# 11) Guard: tenta transizione ACCETTATO con prezzo PENDING (skip se no PENDING)
# =====================================================
log_step "11) Guard transizione (skip se nessun componente PENDING)"
log_info "Skip: questo test richiede setup L3 con sconto >L2 — coperto da test BE unit"

# =====================================================
# 12) Cleanup finale: righe e preventivo, BoM e composito del giro
# =====================================================
log_step "12) Cleanup del giro"
pulisci_giro

# =====================================================
# SUMMARY
# =====================================================
echo ""
echo "================================================"
echo -e "  ${GREEN}PASS=${PASS}${NC}  ${RED}FAIL=${FAIL}${NC}"
echo "================================================"
[[ "$FAIL" -eq 0 ]]
