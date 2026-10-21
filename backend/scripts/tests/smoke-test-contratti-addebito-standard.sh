#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Contratto ADDEBITO STANDARD (una-tantum, NON canone
# periodico) → push commessa (a-test-push-commesse-fatturazione.md §3b).
# Uso: ./scripts/tests/smoke-test-contratti-addebito-standard.sh [password]
#
# AMBITO: prova SOLO l'addebito standard del contratto — l'unica parte del
# push CONTRATTO oggi implementata. La fatturazione RICORRENTE (canone
# periodico / utilities gas-energia-acqua) NON è coperta: fn_list_contratti_da_pushare
# non genera la serie mensile (1 sola attività al mese di inizio), sviluppo
# rinviato (vedi §3a del doc).
#
# Copre contro DB+API reali:
#  - creazione contratto DRAFT (BA+utility+istanza coerenti, emittente esplicito)
#  - riga UNA_TANTUM/FISSA (addebito standard, qta+prezzo)
#  - /emetti/ → ATTIVO (prereq documentale gated: skip se template/emittente assente)
#  - push CONTRATTO (POST /commesse/push/run/, batch globale sorgente CONTRATTO)
#  - 1 commesse_attivita per riga, segment_key CONTRATTO:<uid>:R:<riga>:M:<YYYY-MM inizio>
#  - commessa emittibile (PRONTA_FATTURAZIONE + approvate >= 1)
#  - idempotenza push: re-run = nessun doppione (upsert su segment_key)
#
# NB: il push è un BATCH su TUTTI i contratti ATTIVI (l'API non isola un
# singolo contratto); lo smoke asserisce SOLO sul proprio contratto via
# segment_key. In un ambiente di sviluppo è accettabile.
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_emetti
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_soggetto.sh"
# Override esplicito emittente (opzionale). Se vuoto, si deriva dal documento
# sorgente del BA (vedi setup); ultimo fallback 32.
EMITTENTE_OVERRIDE="${EMITTENTE_ID:-}"

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
    local method="$1" url="$2" data="${3:-}" extra_hdr="${4:-}"
    local -a args=(-s -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN:-none}")
    [[ -n "$extra_hdr" ]] && args+=(-H "$extra_hdr")
    if [[ "$method" == "GET" ]]; then
        curl "${args[@]}" "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl "${args[@]}" -X "$method" -H "Content-Type: application/json" \
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

# --- 0. Auth ---
echo "== Smoke contratto addebito standard → commessa =="
smoke_login --senza-prompt --uscita 2
log_ok "Autenticazione JWT"

# --- 1. Setup: tripla BA+utility+istanza + articolo ---
echo ""; echo "-- 1. Setup tripla BA+utility+istanza + articolo --"
smoke_cliente_dal_lookup   # BB _smoke_cliente.sh: BA_ID, UTILITY_ID, ISTANZA_ID

# Emittente: mai un id scritto a mano. Col cliente dal lookup non si passa (vale
# l'emittente attivo, lo stesso del cliente: _smoke_cliente.sh); col ripiego su un
# documento esistente si prende il suo, coerente col suo BA. Override: EMITTENTE_ID.
EF_SRC=""
if [[ -z "$BA_ID" || -z "$ISTANZA_ID" ]]; then
    log_info "lookup BA vuoto/scope; provo a riusare un documento esistente (preventivi/ordini/contratti)"
    for SRC in preventivi ordini contratti; do
        PAIR=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${BASE_URL}/api/v1/vendite/${SRC}/?limit=20" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data',{}).get('results',[])
    # Preferisci una riga che espone anche l'emittente (coerente col BA → guard BA<->EF);
    # se nessuna lo espone, ripiega sulla prima riga BA+istanza valida (emittente vuoto: default del DB).
    cand = [r for r in rows if r.get('billing_account_id') and r.get('istanza_utility_id')]
    best = next((r for r in cand if r.get('emittente_fiscale_id')), cand[0] if cand else None)
    if best:
        print(best['billing_account_id'], best.get('utility_id') or '', best['istanza_utility_id'], best.get('emittente_fiscale_id') or '')
except Exception:
    pass
" 2>/dev/null)
        if [[ -n "$PAIR" ]]; then
            BA_ID=$(echo "$PAIR" | awk '{print $1}')
            UTILITY_ID=$(echo "$PAIR" | awk '{print $2}')
            ISTANZA_ID=$(echo "$PAIR" | awk '{print $3}')
            EF_SRC=$(echo "$PAIR" | awk '{print $4}')
            log_info "tripla+emittente da '$SRC' (emittente_fiscale_id=$EF_SRC)"
            break
        fi
    done
fi
if [[ -z "$BA_ID" || -z "$ISTANZA_ID" ]]; then
    echo -e "${RED}Setup fallito: nessuna tripla BA+utility+istanza disponibile.${NC}"; exit 1
fi
log_info "billing_account_id=$BA_ID utility_id=$UTILITY_ID istanza_utility_id=$ISTANZA_ID"

ARTICOLO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?limit=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(r[0]['id'] if r else '')
except Exception: print('')
" 2>/dev/null)
if [[ -z "$ARTICOLO_ID" ]]; then echo -e "${RED}Setup fallito: nessun articolo.${NC}"; exit 1; fi
log_info "articolo_id = $ARTICOLO_ID"

OGGI=$(date +%F)
MESE_INIZIO=$(date +%Y-%m)   # date_trunc('month', valido_dal) → YYYY-MM atteso nel segment_key

# --- 2. Crea contratto DRAFT ---
echo ""; echo "-- 2. Crea contratto DRAFT --"
# ambito: COMMODITY|COMMERCIO (override via SMOKE_AMBITO). NB: l'anti-overlap su
# (BA, istanza, utility, ambito) nel periodo di validità può far fallire la create
# se esiste già un contratto sovrapposto — in quel caso l'errore è parlante.
AMBITO="${SMOKE_AMBITO:-COMMODITY}"
# ⭐ I contratti di questo smoke non restano vivi: il prezzo di OGNI documento
# del cliente di prova passa dal contratto ATTIVO, e uno lasciato acceso (modalita'
# C, senza listino) fa fallire gli altri smoke sullo stesso cliente. Si chiudono
# i residui ora e i propri all'uscita, qualunque sia (BB _smoke_documenti.sh).
smoke_chiudi_contratti "$BA_ID" "$AMBITO"   # residui sul cliente condiviso

# ⭐ Un CLIENTE PROPRIO per ogni giro. Il contratto non puo' sovrapporsi a un
# altro sulla chiave (cliente, istanza, utility, ambito) nel periodo, e il
# vincolo non guarda lo stato: un contratto cessato OGGI occupa ancora oggi.
# Sul cliente condiviso, due giri nello stesso giorno si scontravano
# (E_VENDITE_CONTRATTO_OVERLAP) e il contratto attivo governava i prezzi degli
# altri smoke. La creazione manuale di un cliente apre ogni volta istanza e BA
# nuovi: il contratto vive li', isolato.
# ⭐ E un SOGGETTO PROPRIO per ogni giro (2026-10-15): dal 2026-10-14 un
# soggetto ha UN cliente manuale per utility e azienda (E_CLIENTE_STESSA_CHIAVE,
# brief-db-cliente-manuale-uno-per-soggetto-e-utility C-1/C-2). Prima il
# cliente nasceva sul soggetto del primo cliente della lista: dal secondo giro
# il DB lo rifiutava, giustamente. Soggetto e cliente li crea il BB
# `smoke_cliente_del_giro` (_smoke_cliente.sh), dall'API.
smoke_cliente_del_giro "Contratto" "" "${UTILITY_ID:-}"
if [[ -z "$SOGG_ID" ]]; then
    echo -e "${RED}Setup fallito: impossibile creare il soggetto del giro (motivo sopra). Stop.${NC}"; exit 1
fi
log_info "soggetto del giro: $SOGG_ID (CF $SOGG_CF)"
LAST_STATUS="$GIRO_LAST_STATUS"; LAST_BODY="$GIRO_LAST_BODY"
if ! check "POST cliente proprio del giro" 200 "data.billing_account_id"; then
    echo -e "${RED}Setup fallito: impossibile creare il cliente del giro. Stop.${NC}"; exit 1
fi
BA_ID="$GIRO_BA_ID"
ISTANZA_ID="$GIRO_ISTANZA_ID"
UTILITY_ID="$GIRO_UTILITY_ID"
EF_SRC=""   # l'emittente e' quello attivo, lo stesso del nuovo cliente
log_info "cliente del giro: BA=$BA_ID istanza=$ISTANZA_ID utility=$UTILITY_ID"
trap 'smoke_chiudi_contratti "$BA_ID" "$AMBITO"; rm -f "$TMPFILE"' EXIT
# Emittente coerente col BA: override esplicito → emittente del doc sorgente →
# nessuno (default del DB: l'emittente attivo, lo stesso del cliente del lookup).
EMITTENTE_FISCALE_ID="${EMITTENTE_OVERRIDE:-${EF_SRC:-}}"
EMITTENTE_JSON=""
[[ -n "$EMITTENTE_FISCALE_ID" ]] && EMITTENTE_JSON=", \"emittente_fiscale_id\": ${EMITTENTE_FISCALE_ID}"
CREATE_PAYLOAD="{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID:-null}, \"istanza_utility_id\": ${ISTANZA_ID}, \"ambito\": \"${AMBITO}\"${EMITTENTE_JSON}, \"valido_dal\": \"${OGGI}\", \"data\": \"${OGGI}\"}"
log_info "payload create = $CREATE_PAYLOAD"
do_curl POST "/api/v1/vendite/contratti/" "$CREATE_PAYLOAD"
if ! check "POST crea contratto" 200 "data.id"; then
    echo -e "${RED}Setup fallito: impossibile creare contratto. Stop.${NC}"; exit 1
fi
CONTRATTO_ID="$EXTRACTED"
do_curl GET "/api/v1/vendite/contratti/${CONTRATTO_ID}/"
CONTRATTO_UID=$(json_get "$LAST_BODY" "data.uid")
log_info "contratto_id=$CONTRATTO_ID uid=$CONTRATTO_UID"
# Fix analisi-fix-transazioni #2: numero + INSERT testata (+utility) sono ora una
# sola fn madre atomica (vendite.fn_create_contratto). Il numero e' generato DENTRO
# la fn (fn_generate_codice): se e' valorizzato, il percorso atomico ha funzionato.
CONTRATTO_NUMERO=$(json_get "$LAST_BODY" "data.numero")
if [[ -n "$CONTRATTO_NUMERO" && "$CONTRATTO_NUMERO" != "None" && "$CONTRATTO_NUMERO" != "null" ]]; then
    log_ok "Numero generato dalla fn madre atomica: $CONTRATTO_NUMERO (fix #2)"
else
    log_fail "Numero contratto non valorizzato (atteso da fn_create_contratto)"
fi

# --- 3. Riga addebito standard (AGGIUNTA, UNA_TANTUM / FISSA) ---
# Contratto SENZA listino → ogni riga è tipo_eccezione=AGGIUNTA (prezzo proprio).
# Niente iva_id: non è un campo della riga contratto (l'IVA è a valle).
echo ""; echo "-- 3. Aggiungi riga addebito standard (AGGIUNTA, UNA_TANTUM/FISSA) --"
do_curl POST "/api/v1/vendite/contratti/${CONTRATTO_ID}/righe/" \
    "{\"articolo_id\": \"$ARTICOLO_ID\", \"tipo_eccezione\": \"AGGIUNTA\", \"tipo_erogazione\": \"UNA_TANTUM\", \"fonte_quantita_attesa\": \"FISSA\", \"quantita\": \"1\", \"qta_operativa\": \"1\", \"prezzo_unitario\": \"120.00\"}"
if check "POST riga contratto" 200 "data.id"; then
    RIGA_ID="$EXTRACTED"
else
    RIGA_ID=""  # EXTRACTED stale: non riusarlo
fi
log_info "riga_id = $RIGA_ID"

# --- 4. Emetti → ATTIVO (prereq documentale gated) ---
echo ""; echo "-- 4. /emetti/ → ATTIVO (skip se prereq documentale assente) --"
smoke_emetti contratti "$CONTRATTO_ID"   # BB _smoke_documenti.sh
ATTIVO_OK=0
if [[ "$LAST_STATUS" == "200" ]]; then
    log_ok "POST /emetti/ → ATTIVO"
    do_curl GET "/api/v1/vendite/contratti/${CONTRATTO_ID}/"
    # Logica su stato_codice_interno (immutabile); il display sarebbe stato_descrizione.
    ST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$ST" == "ATTIVO" ]] && { log_ok "stato = ATTIVO"; ATTIVO_OK=1; } \
        || log_fail "stato atteso ATTIVO, trovato '$ST'"
else
    log_skip "EMESSO/ATTIVO HTTP $LAST_STATUS — prereq documentale assente, salto push"
    log_info "Body: $(echo "$LAST_BODY" | head -c 200)"
fi

# Funzione: cerca la nostra attività (segment_key CONTRATTO:<uid>:R:<riga>:M:...) tra
# le commesse passate in $@ e stampa "commessa_id|segment_key|competenza_mese".
trova_attivita() {
    local uid="$1"; shift
    for cid in "$@"; do
        [[ -z "$cid" || "$cid" == "None" ]] && continue
        do_curl GET "/api/v1/vendite/commesse/${cid}/attivita/?limit=200"
        local found
        found=$(echo "$LAST_BODY" | python3 -c "
import sys, json
uid='$uid'; cid='$cid'
try:
    rows = json.load(sys.stdin).get('data',{}).get('results',[])
    for a in rows:
        sk = a.get('segment_key') or ''
        if sk.startswith('CONTRATTO:'+uid+':'):
            print(cid+'|'+sk+'|'+str(a.get('competenza_mese') or '')); break
except Exception:
    pass
" 2>/dev/null)
        [[ -n "$found" ]] && { echo "$found"; return 0; }
    done
    return 1
}

if [[ "$ATTIVO_OK" == "1" ]]; then
    # --- 5. Push CONTRATTO (batch sorgente) ---
    echo ""; echo "-- 5. Push CONTRATTO (POST /commesse/push/run/) --"
    do_curl POST "/api/v1/vendite/commesse/push/run/" \
        '{"source_types": ["CONTRATTO"]}' "Idempotency-Key: smoke-contr-$(date +%s%N)"
    PUSH_OK=0
    if check "POST push CONTRATTO" 200 "data.stato"; then
        COMMESSE_IDS=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    print(' '.join(str(x) for x in json.load(sys.stdin).get('data',{}).get('commesse_ids',[])))
except Exception: pass
" 2>/dev/null)
        log_info "commesse_ids = ${COMMESSE_IDS:-<vuoto>}"
        PUSH_OK=1
    fi

    # --- 6. Verifica attività con segment_key del nostro contratto ---
    echo ""; echo "-- 6. Attività con segment_key CONTRATTO:<uid>:R:<riga>:M:<mese-inizio> --"
    COMMESSA_ID=""; SEG=""; COMPETENZA=""
    if [[ "$PUSH_OK" == "1" ]]; then
        HIT=$(trova_attivita "$CONTRATTO_UID" $COMMESSE_IDS || true)
        if [[ -n "$HIT" ]]; then
            COMMESSA_ID="${HIT%%|*}"; rest="${HIT#*|}"; SEG="${rest%%|*}"; COMPETENZA="${rest##*|}"
            log_ok "attività trovata (commessa=$COMMESSA_ID)"
            log_info "segment_key = $SEG ; competenza_mese = $COMPETENZA"
            if [[ "$SEG" == "CONTRATTO:${CONTRATTO_UID}:R:${RIGA_ID}:M:${MESE_INIZIO}" ]]; then
                log_ok "segment_key atteso (riga $RIGA_ID, mese-inizio $MESE_INIZIO)"
            else
                log_fail "segment_key inatteso: atteso CONTRATTO:${CONTRATTO_UID}:R:${RIGA_ID}:M:${MESE_INIZIO}"
            fi
            [[ "$COMPETENZA" == "${MESE_INIZIO}-01" ]] \
                && log_ok "competenza_mese = ${MESE_INIZIO}-01 (mese inizio contratto)" \
                || log_info "competenza_mese = $COMPETENZA (atteso ${MESE_INIZIO}-01)"
        else
            log_fail "nessuna attività con segment_key CONTRATTO:${CONTRATTO_UID}: nelle commesse pushate"
        fi
    else
        log_skip "push non OK: salto verifica attività"
    fi

    # --- 7. Commessa emittibile ---
    echo ""; echo "-- 7. Commessa emittibile (PRONTA_FATTURAZIONE + approvate) --"
    if [[ -n "$COMMESSA_ID" ]]; then
        do_curl GET "/api/v1/vendite/commesse/${COMMESSA_ID}/stato/"
        if check "GET stato commessa" 200; then
            C_STATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
            C_APPROVATE=$(json_get "$LAST_BODY" "data.total_approvate")
            [[ "$C_STATO" == "PRONTA_FATTURAZIONE" ]] \
                && log_ok "commessa $COMMESSA_ID = PRONTA_FATTURAZIONE" \
                || log_fail "commessa attesa PRONTA_FATTURAZIONE, trovata '$C_STATO'"
            [[ -n "$C_APPROVATE" && "$C_APPROVATE" -ge 1 ]] 2>/dev/null \
                && log_ok "attività approvate = $C_APPROVATE (>=1)" \
                || log_fail "attese >=1 attività approvate, trovate '$C_APPROVATE'"
        fi
    else
        log_skip "commessa non identificata: salto emittibilità"
    fi

    # --- 8. Idempotenza push: re-run = nessun doppione ---
    echo ""; echo "-- 8. Re-push CONTRATTO (attesa: nessun doppione, upsert segment_key) --"
    if [[ -n "$COMMESSA_ID" ]]; then
        # conteggio attività col nostro segment_key PRIMA
        do_curl GET "/api/v1/vendite/commesse/${COMMESSA_ID}/attivita/?limit=200"
        N_PRE=$(echo "$LAST_BODY" | python3 -c "
import sys, json
sk='$SEG'
try:
    print(sum(1 for a in json.load(sys.stdin).get('data',{}).get('results',[]) if (a.get('segment_key') or '')==sk))
except Exception: print(0)
" 2>/dev/null)
        do_curl POST "/api/v1/vendite/commesse/push/run/" \
            '{"source_types": ["CONTRATTO"]}' "Idempotency-Key: smoke-contr-repush-$(date +%s%N)"
        check "POST re-push CONTRATTO" 200 || true
        do_curl GET "/api/v1/vendite/commesse/${COMMESSA_ID}/attivita/?limit=200"
        N_POST=$(echo "$LAST_BODY" | python3 -c "
import sys, json
sk='$SEG'
try:
    print(sum(1 for a in json.load(sys.stdin).get('data',{}).get('results',[]) if (a.get('segment_key') or '')==sk))
except Exception: print(0)
" 2>/dev/null)
        log_info "attività con segment_key: pre=$N_PRE post=$N_POST"
        [[ "$N_PRE" == "$N_POST" && "$N_POST" == "1" ]] \
            && log_ok "idempotente: 1 sola attività per segment_key (nessun doppione)" \
            || log_fail "doppione/anomalia: pre=$N_PRE post=$N_POST (atteso 1=1)"
    else
        log_skip "commessa non identificata: salto idempotenza"
    fi
else
    log_skip "contratto non ATTIVO: salto push + verifiche"
fi

# --- Nota copertura ---
echo ""
log_info "RICORRENTE (canone periodico/utilities) NON coperto: fn_list_contratti_da_pushare"
log_info "non genera la serie mensile (1 attività al mese-inizio). Vedi §3a del doc."

# --- Summary ---
echo ""
echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
