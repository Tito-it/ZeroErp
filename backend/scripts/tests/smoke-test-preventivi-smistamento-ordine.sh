#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Smistamento MERCE preventivo → ordine (modello split D8).
# Uso: ./scripts/tests/smoke-test-preventivi-smistamento-ordine.sh [password]
#
# Copre i due rami dello split per natura end-to-end contro DB+API reali (ciò
# che gli unit test mockano):
#  - MERCE→ORDINE: vista vw_preventivi_righe_smistabili_ordine, endpoint
#    righe-smistabili-ordine + genera-ordine (fn_push_preventivo_a_ordine),
#    idempotenza di riga, picker degli articoli della riga (sede unica);
#  - SERVIZIO→COMMESSA su preventivo MISTO (2026-06-10): articolo servizio
#    creato via API (natura_vendita_id amministrabile, opzione A), push-commessa
#    natura-aware (il servizio non appare tra le righe-smistabili-ordine), gate
#    EVASO D6 (resta ACCETTATO con residuo merce; EVASO solo a smistamento
#    completo), idempotenza re-push.
#
#  - multi-sorgente (passo 14, 2026-06-11): secondo preventivo servizio-only
#    stesse dimensioni → confluisce nella STESSA commessa (auto-ruolo
#    COLLEGATO + skip PRONTA idempotente).
#
# NON coperto qui:
#  - il giro pratica end-to-end (tipo PREVENTIVI, bivio per esito) → smoke
#    dedicato smoke-test-pratica-preventivi-bivio.sh. Il vecchio orchestratore
#    CONFERMA_VENDITA (tipo PREVENTIVI_IMMEDIATA, obsoleto dal 2026-06-30) e il
#    suo smoke sono ritirati (2026-10-12).
#
# Auto-diagnosi: se EMESSO/ACCETTATO falliscono per prerequisiti documentali
# (template/emittente), i passi split vengono SALTATI con diagnosi, non crashano.
# Idempotenza setup: l'articolo servizio è riusato per codice fisso
# (SMOKE-SERV-UT), creato solo se assente — nessun residuo che si accumula.
# ------------------------------------------------------------
# Indice:
#  0) Autenticazione JWT
#  1) (ritirato il 2026-10-14: era il filtro libero `escludi_destinazione`; la
#     prova del picker e' ora il passo 2-bis)
#  2) Crea preventivo BOZZA + riga merce
#  2-bis) Picker della riga sulla sede unica (?documento=PREVENTIVO): l'articolo
#     che il guard ha appena accettato e' fra gli AMMESSI (motivo null)
#  3) Porta ad ACCETTATO (emetti multipart + accetta con modalita) [prereq-gated]
#  4) GET righe-smistabili-ordine → la riga merce compare
#  5) POST genera-ordine {righe_ids} → ordine creato (ordine_id + numero)
#  6) GET righe-smistabili-ordine → vuota (riga ora allocata: idempotenza)
#  7) POST genera-ordine di nuovo → errore "nessuna riga ordine" (idempotenza)
#  8) Crea/riusa articolo SERVIZIO_UNA_TANTUM (natura_vendita_id=2 via API)
#  9) Crea preventivo MISTO (riga merce + riga servizio) → ACCETTATO
# 10) GET righe-smistabili-ordine → SOLO la riga merce (servizio escluso)
# 11) POST push-commessa → COMPLETATO + commesse_ids; stato resta ACCETTATO
#     (gate EVASO D6: residuo merce)
# 12) POST genera-ordine → merce smistata
# 13) Stato EVASO a smistamento completo (gate D6: nessun residuo, scatta a
#     genera-ordine) + re-push su EVASO bloccato 4xx (idempotenza via stato terminale)
# 14) Multi-sorgente: secondo preventivo servizio-only stesse dimensioni →
#     push → CONFLUISCE nella STESSA commessa (auto-ruolo COLLEGATO, skip
#     PRONTA idempotente), nessun errore
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_emetti

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

# Conta gli elementi della lista in data (envelope { data: [...] }).
json_len() {
    echo "$1" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data', [])
    print(len(d) if isinstance(d, list) else 0)
except Exception:
    print(0)
" 2>/dev/null
}

do_curl() {
    # Arg 4 opzionale: header extra (es. "Idempotency-Key: ...").
    local method="$1" url="$2" data="${3:-}" extra_header="${4:-}"
    if [[ "$method" == "GET" ]]; then
        curl -s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' -X "$method" \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" \
            ${extra_header:+-H "$extra_header"} -d "$data" \
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

# --- 0. Auth ---
echo "== Smoke smistamento merce→ordine =="
smoke_login --senza-prompt --uscita 2
log_ok "Autenticazione JWT"

# --- 2. Crea preventivo + riga merce ---
echo ""; echo "-- 2. Crea preventivo BOZZA + riga merce --"
# Serve una tripla COERENTE (billing_account + utility + istanza). Fonte 1: lookup
# BA (espone utility_id + istanza_utility_id). Fonte 2 (fallback): un preventivo
# esistente (tripla già coerente per costruzione). La create deriva l'istanza dal
# BA e verifica la coerenza con utility.
smoke_cliente_dal_lookup   # BB _smoke_cliente.sh: BA_ID, UTILITY_ID, ISTANZA_ID

PREV_PAYLOAD=""
if [[ -n "$BA_ID" && -n "$UTILITY_ID" ]]; then
    log_info "fonte: lookup BA → billing_account_id = $BA_ID, utility_id = $UTILITY_ID"
    PREV_PAYLOAD="{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}}"
else
    # Fallback: riusa un preventivo esistente (BA+utility+istanza coerenti).
    log_info "lookup BA vuoto/scope; provo a riusare un preventivo esistente"
    PREV_PAYLOAD=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/preventivi/?limit=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    if r:
        x = r[0]
        ba, ut, iu = x.get('billing_account_id'), x.get('utility_id'), x.get('istanza_utility_id')
        import json as j
        p = {}
        if ba: p['billing_account_id'] = ba
        if ut: p['utility_id'] = ut
        if iu: p['istanza_utility_id'] = iu
        print(j.dumps(p) if ('billing_account_id' in p or 'istanza_utility_id' in p) else '')
except Exception:
    print('')
" 2>/dev/null)
fi

if [[ -z "$PREV_PAYLOAD" ]]; then
    echo -e "${RED}Setup fallito: nessuna tripla BA+utility+istanza disponibile.${NC}"
    log_info "Risposta lookup BA (grezza, primi 500 char):"
    echo "       $(echo "$BA_LOOKUP_RAW" | head -c 500)"
    log_info "Suggerimento: verifica che l'utente smoke abbia un emittente con almeno un BA valido (utility+istanza)."
    exit 1
fi
# ⛔ Nessun emittente nel payload: il trigger script.trgfn_default_emittente_fiscale
# mette l'emittente attivo dell'operatore, lo stesso del cliente del lookup
# (_smoke_cliente.sh). Fino al 2026-10-12 qui c'era un id cablato (32), che con un
# cliente di un'altra azienda risponde E_DOC_EMITTENTE_BA_INCOERENTE.
# Override solo se serve: EMITTENTE_ID.
if [[ -n "${EMITTENTE_ID:-}" ]]; then
PREV_PAYLOAD=$(echo "$PREV_PAYLOAD" | python3 -c "
import sys, json
p = json.load(sys.stdin)
p['emittente_fiscale_id'] = $EMITTENTE_ID
print(json.dumps(p))
" 2>/dev/null)
fi
log_info "payload create = $PREV_PAYLOAD"
do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
if ! check "POST crea preventivo" 200 "data.id"; then
    echo -e "${RED}Setup fallito: impossibile creare preventivo. Stop.${NC}"; exit 1
fi
PREV_ID="$EXTRACTED"; log_info "preventivo_id = $PREV_ID"

smoke_articolo_merce   # BB _smoke_documenti.sh: una MERCE (va in un ordine/bolla)
if [[ -z "$ARTICOLO_ID" ]]; then
    echo -e "${RED}Setup fallito: nessun articolo nel catalogo. Stop.${NC}"; exit 1
fi
log_info "articolo_id (merce) = $ARTICOLO_ID"
do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/righe/" \
    "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"10\", \"prezzo_unitario\": \"100.00\"}"
check "POST aggiungi riga merce" 200 "data.id" || true
RIGA_ID="$EXTRACTED"; log_info "riga_id = $RIGA_ID"

# --- 2-bis. Picker della riga sulla sede unica ---
# ⭐ Il picker e il guard fanno la STESSA domanda (catalogo.fn_articoli_ammessi,
#    brief-db-articoli-ammessi-per-documento §9.4): l'articolo che il guard ha
#    appena accettato sulla riga deve uscire AMMESSO (`motivo` null). Prima qui
#    c'era il filtro libero `escludi_destinazione`, ritirato: il BE lo ignorava
#    e il passo restava verde senza provare niente.
echo ""; echo "-- 2-bis. Picker riga preventivo (?documento=PREVENTIVO) --"
if [[ -n "$RIGA_ID" ]]; then
    do_curl GET "/api/v1/catalogo/articoli/${ARTICOLO_ID}/"
    ART_CODICE=$(json_get "$LAST_BODY" "data.codice")
    if [[ ${#ART_CODICE} -lt 3 ]]; then
        log_skip "picker: codice articolo '${ART_CODICE}' sotto i 3 caratteri della ricerca"
    else
        do_curl GET "/api/v1/catalogo/articoli/lookup/?documento=PREVENTIVO&documento_id=${PREV_ID}&search=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$ART_CODICE")&limit=50"
        if check "GET picker riga preventivo" 200; then
            ESITO=$(echo "$LAST_BODY" | python3 -c "
import sys, json
rows = json.load(sys.stdin).get('data', {}).get('results') or []
r = next((x for x in rows if str(x.get('id')) == '$ARTICOLO_ID'), None)
if r is None: print('ASSENTE')
elif 'motivo' not in r: print('SENZA_MOTIVO')
elif r['motivo'] is None: print('AMMESSO')
else: print('ESCLUSO:' + str(r['motivo'].get('reason')))
" 2>/dev/null)
            [[ "$ESITO" == "AMMESSO" ]] \
                && log_ok "picker: l'articolo della riga e' ammesso (motivo null), come per il guard" \
                || log_fail "picker: atteso AMMESSO per l'articolo della riga, trovato ${ESITO:-illeggibile}"
        fi
    fi
else
    log_skip "picker: la riga merce non e' stata creata, niente da confrontare"
fi

# --- 3. Porta ad ACCETTATO (prereq-gated: emetti + accetta) ---
echo ""; echo "-- 3. BOZZA → EMESSO (/emetti/) → ACCETTATO --"
SPLIT_OK=1
# EMESSO via endpoint multipart /emetti/ (allegati opzionali). Richiede
# template documento + emittente configurati: se manca, qui si diagnostica.
smoke_emetti preventivi "${PREV_ID}"   # BB _smoke_documenti.sh
if [[ "$LAST_STATUS" != "200" ]]; then
    log_skip "EMESSO (/emetti/) HTTP $LAST_STATUS — prereq documentale assente (template/emittente). Salto i passi split."
    log_info "Body: $(echo "$LAST_BODY" | head -c 200)"
    SPLIT_OK=0
else
    log_ok "POST /emetti/ → EMESSO"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/stato/" \
        '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
    if ! check "POST /stato/ → ACCETTATO (modalita IMMEDIATA)" 200; then SPLIT_OK=0; fi
fi

# --- 4..7. Smistamento merce → ordine (solo se ACCETTATO) ---
if [[ "$SPLIT_OK" == "1" ]]; then
    echo ""; echo "-- 4. GET righe-smistabili-ordine (attesa: la riga merce) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe-smistabili-ordine/"
    check "GET righe-smistabili-ordine" 200 || true
    N=$(json_len "$LAST_BODY")
    [[ "$N" -ge 1 ]] && log_ok "Righe smistabili = $N (>=1)" || log_fail "Attese >=1 righe smistabili, trovate $N"

    echo ""; echo "-- 5. POST genera-ordine {righe_ids} --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/genera-ordine/" \
        "{\"righe_ids\": [${RIGA_ID}]}"
    if check "POST genera-ordine" 200 "data.ordine_id"; then
        log_info "ordine_id = $EXTRACTED, numero = $(json_get "$LAST_BODY" "data.numero")"
    fi

    echo ""; echo "-- 6. GET righe-smistabili-ordine (attesa: vuota, riga allocata) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV_ID}/righe-smistabili-ordine/"
    check "GET righe-smistabili-ordine (post)" 200 || true
    N2=$(json_len "$LAST_BODY")
    [[ "$N2" -eq 0 ]] && log_ok "Righe smistabili = 0 (idempotenza di riga)" || log_fail "Attese 0 righe residue, trovate $N2"

    echo ""; echo "-- 7. POST genera-ordine di nuovo (attesa: errore nessuna riga) --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV_ID}/genera-ordine/" '{}'
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "Re-genera bloccato (HTTP $LAST_STATUS, code=$CODE)"
    else
        log_fail "Re-genera: atteso 4xx (nessuna riga merce residua), ricevuto $LAST_STATUS"
    fi
fi

# --- 8. Articolo SERVIZIO_UNA_TANTUM (riuso per codice fisso, crea se assente) ---
echo ""; echo "-- 8. Crea/riusa articolo servizio (natura SERVIZIO_UNA_TANTUM) --"
SERV_CODICE="SMOKE-SERV-UT"
SERV_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?search=${SERV_CODICE}&limit=5" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(next((x['id'] for x in r if x.get('codice') == '${SERV_CODICE}'), ''))
except Exception: print('')
" 2>/dev/null)
if [[ -n "$SERV_ID" ]]; then
    log_ok "articolo servizio riusato (codice $SERV_CODICE)"
else
    # uom_id obbligatoria: riusa quella dell'articolo merce (GET detail).
    do_curl GET "/api/v1/catalogo/articoli/${ARTICOLO_ID}/"
    UOM_ID=$(json_get "$LAST_BODY" "data.uom_id")
    if [[ -z "$UOM_ID" ]]; then
        log_fail "uom_id non ricavabile dall'articolo merce: impossibile creare il servizio"
    else
        do_curl POST "/api/v1/catalogo/articoli/" \
            "{\"codice\": \"$SERV_CODICE\", \"descrizione\": \"Servizio una tantum (smoke)\", \"uom_id\": ${UOM_ID}, \"iva_id\": 16, \"natura_vendita_id\": 2}"
        if check "POST crea articolo servizio (natura_vendita_id=2)" 200 "data.id"; then
            SERV_ID="$EXTRACTED"
        else
            SERV_ID=""  # EXTRACTED stale dal passo precedente: mai riusarlo
        fi
    fi
fi
log_info "articolo servizio id = $SERV_ID"

# --- 9..13. Preventivo MISTO: split servizio→commessa + gate EVASO ---
MISTO_OK=0
if [[ -n "$SERV_ID" && "$SPLIT_OK" == "1" ]]; then
    echo ""; echo "-- 9. Crea preventivo MISTO (merce + servizio) → ACCETTATO --"
    do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
    if check "POST crea preventivo misto" 200 "data.id"; then
        PREV2_ID="$EXTRACTED"; log_info "preventivo_id (misto) = $PREV2_ID"
        do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/righe/" \
            "{\"articolo_id\": \"$ARTICOLO_ID\", \"qta_operativa\": \"3\", \"prezzo_unitario\": \"100.00\"}"
        check "POST riga merce" 200 "data.id" || true
        RIGA_MERCE2_ID="$EXTRACTED"
        do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/righe/" \
            "{\"articolo_id\": \"$SERV_ID\", \"qta_operativa\": \"1\", \"prezzo_unitario\": \"50.00\"}"
        check "POST riga servizio" 200 "data.id" || true
        smoke_emetti preventivi "${PREV2_ID}"   # BB _smoke_documenti.sh
        if [[ "$LAST_STATUS" == "200" ]]; then
            log_ok "POST /emetti/ → EMESSO"
            do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/stato/" \
                '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
            if check "POST /stato/ → ACCETTATO" 200; then MISTO_OK=1; fi
        else
            log_skip "EMESSO (misto) HTTP $LAST_STATUS — salto i passi misto"
        fi
    fi
fi

if [[ "$MISTO_OK" == "1" ]]; then
    echo ""; echo "-- 10. righe-smistabili-ordine (attesa: SOLO la riga merce) --"
    do_curl GET "/api/v1/vendite/preventivi/${PREV2_ID}/righe-smistabili-ordine/"
    check "GET righe-smistabili-ordine (misto)" 200 || true
    NM=$(json_len "$LAST_BODY")
    [[ "$NM" -eq 1 ]] && log_ok "Righe smistabili = 1 (servizio escluso dal filtro natura)" \
        || log_fail "Attesa 1 riga smistabile (solo merce), trovate $NM"

    echo ""; echo "-- 11. push-commessa (attesa: COMPLETATO, stato resta ACCETTATO) --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/push-commessa/" '{}' \
        "Idempotency-Key: smoke-push-$(date +%s%N)"
    if check "POST push-commessa" 200 "data.stato"; then
        PUSH_STATO="$EXTRACTED"
        COMMESSE=$(json_get "$LAST_BODY" "data.commesse_ids.0")
        [[ "$PUSH_STATO" == "COMPLETATO" ]] && log_ok "push COMPLETATO" || log_fail "push atteso COMPLETATO, trovato '$PUSH_STATO'"
        [[ -n "$COMMESSE" ]] && log_ok "commessa creata (id=$COMMESSE)" || log_fail "commesse_ids vuoto nel report push"
    fi
    do_curl GET "/api/v1/vendite/preventivi/${PREV2_ID}/"
    ST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$ST" == "ACCETTATO" ]] && log_ok "stato = ACCETTATO (gate EVASO D6: residuo merce)" \
        || log_fail "gate EVASO violato: atteso ACCETTATO con residuo merce, trovato '$ST'"

    echo ""; echo "-- 12. genera-ordine (smista la merce residua) --"
    do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/genera-ordine/" '{}'
    if check "POST genera-ordine (misto)" 200 "data.ordine_id"; then
        log_info "ordine_id = $EXTRACTED"
    fi

    echo ""; echo "-- 13. EVASO a smistamento completo + re-push bloccato (stato terminale) --"
    # Smistati ENTRAMBI i rami (servizio→commessa step 11, merce→ordine step 12),
    # il gate EVASO scatta. Dal 2026-10-12 lo fa il DB in tutti e due gli invii
    # (`vendite.fn_preventivo_proietta_stato_smistamento`, D-10 di
    # brief-db-annullo-a-valle-riapre-a-monte): il preventivo e' gia' EVASO qui.
    do_curl GET "/api/v1/vendite/preventivi/${PREV2_ID}/"
    ST2=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$ST2" == "EVASO" ]] && log_ok "stato = EVASO (smistamento completo, gate D6 soddisfatto)" \
        || log_fail "atteso EVASO a smistamento completo, trovato '$ST2'"
    # Idempotenza via STATO TERMINALE: un re-push su EVASO e' bloccato dal guard
    # (E_PREV_STATO_TRANSIZIONE), come il re-push ordini su stato EVASO (smoke
    # ordini §9). Prima del fix DB gate-EVASO il preventivo restava ACCETTATO e
    # il re-push tornava 200: con EVASO al push l'idempotenza e' lo stato, non il replay.
    do_curl POST "/api/v1/vendite/preventivi/${PREV2_ID}/push-commessa/" '{}' \
        "Idempotency-Key: smoke-repush-$(date +%s%N)"
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        CODE=$(json_get "$LAST_BODY" "error.code")
        log_ok "re-push su EVASO bloccato (HTTP $LAST_STATUS, code=$CODE)"
    else
        log_fail "re-push su EVASO: atteso 4xx (stato terminale), ricevuto $LAST_STATUS"
    fi
elif [[ "$SPLIT_OK" == "1" ]]; then
    log_skip "Passi misto saltati (articolo servizio non disponibile)"
fi

# --- 14. Multi-sorgente: secondo preventivo → stessa commessa ---
if [[ "$MISTO_OK" == "1" && -n "${COMMESSE:-}" ]]; then
    echo ""; echo "-- 14. Multi-sorgente: 2° preventivo servizio-only → stessa commessa --"
    do_curl POST "/api/v1/vendite/preventivi/" "$PREV_PAYLOAD"
    if check "POST crea preventivo servizio-only" 200 "data.id"; then
        PREV3_ID="$EXTRACTED"
        do_curl POST "/api/v1/vendite/preventivi/${PREV3_ID}/righe/" \
            "{\"articolo_id\": \"$SERV_ID\", \"qta_operativa\": \"1\", \"prezzo_unitario\": \"30.00\"}"
        check "POST riga servizio" 200 || true
        smoke_emetti preventivi "${PREV3_ID}"   # BB _smoke_documenti.sh
        if [[ "$LAST_STATUS" == "200" ]]; then
            do_curl POST "/api/v1/vendite/preventivi/${PREV3_ID}/stato/" \
                '{"nuovo_stato": "ACCETTATO", "fatturazione_immediata": true}'
            check "POST → ACCETTATO" 200 || true
            do_curl POST "/api/v1/vendite/preventivi/${PREV3_ID}/push-commessa/" '{}' \
                "Idempotency-Key: smoke-multisorg-$(date +%s%N)"
            if check "POST push-commessa (2° preventivo)" 200 "data.stato"; then
                [[ "$EXTRACTED" == "COMPLETATO" ]] && log_ok "push COMPLETATO (skip PRONTA idempotente)" \
                    || log_fail "push atteso COMPLETATO, trovato '$EXTRACTED'"
                COMMESSA2=$(json_get "$LAST_BODY" "data.commesse_ids.0")
                if [[ -n "$COMMESSA2" && "$COMMESSA2" == "$COMMESSE" ]]; then
                    log_ok "CONFLUITO nella stessa commessa (id=$COMMESSA2, multi-sorgente)"
                else
                    log_fail "attesa commessa $COMMESSE (stesse dimensioni), trovata '$COMMESSA2'"
                fi
            fi
            do_curl GET "/api/v1/vendite/preventivi/${PREV3_ID}/"
            ST3=$(json_get "$LAST_BODY" "data.stato_codice_interno")
            [[ "$ST3" == "EVASO" ]] && log_ok "2° preventivo EVASO (solo servizi, no residuo)" \
                || log_fail "atteso EVASO, trovato '$ST3'"
        else
            log_skip "EMESSO (2° preventivo) HTTP $LAST_STATUS — salto multi-sorgente"
        fi
    fi
fi

# --- Nota copertura ---
echo ""
log_info "NON coperto qui: il giro pratica end-to-end → vedi smoke dedicato"
log_info "smoke-test-pratica-preventivi-bivio.sh (tipo PREVENTIVI, bivio per esito)."

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
