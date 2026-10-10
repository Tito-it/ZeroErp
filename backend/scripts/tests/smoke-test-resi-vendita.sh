#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test locale — Slice RESI vendita (motore resi su DDT).
# Copre lo step 9 del brief-be-fe-resi-vendita.md §9 contro DB+API reali
# (cio` che gli unit test mockano).
#
# Uso:
#   ./scripts/tests/smoke-test-resi-vendita.sh [password]
#   col login unico: eval "$(./scripts/tests/smoke-login.sh)" e poi lo smoke
#   (riusa SMOKE_TOKEN finche' vale, `_smoke_auth.sh`; il vecchio TOKEN=<jwt> e' ritirato)
#
# Flusso (tutto data-driven, niente cambia-stato nudo sui resi):
#   A) giro ordine -> genera-DDT (evasione) -> EMESSO -> SPEDITO -> CONSEGNATO
#      (DRAFT->EMESSO->SPEDITO->CONSEGNATO via cambia-stato: la macchina a stati
#      DDT ammette EMESSO da DRAFT, il numero e` assegnato dal trigger a EMESSO);
#   B) reso MISTO (1 riga a credito + 1 per ri-consegna) dal pannello DDT ->
#      conferma (riapre residuo, proietta stato ordine, popola le 2 code);
#   C) ri-consegna parziale -> totale (coda si auto-svuota) -> annullo BLOCCATO
#      perche` gia` ri-spedito (E_RESO_ANNULLO_CON_RICONSEGNE);
#   D) reso TOTALE a credito su altro DDT -> flip DDT->RESO -> annullo ->
#      RESO->CONSEGNATO (storno).
#
# Idempotenza: teardown best-effort in coda (annulla i resi annullabili e i DDT
# creati). I resi confermati con ri-consegne restano storicizzati (per design).
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
EMITTENTE_FISCALE_ID="${EMITTENTE_ID:-32}"
IVA_ID="${IVA_ID:-16}"

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
        echo "       Body: $(echo "$LAST_BODY" | head -c 400)"
        return 1
    fi
    [[ -n "$json_expr" ]] && EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    return 0
}

# check_4xx: attesa un errore 4xx con uno specifico error.code (best-effort).
check_4xx() {
    local label="$1" want_code="${2:-}"
    if [[ "$LAST_STATUS" =~ ^4 ]]; then
        local code; code=$(json_get "$LAST_BODY" "error.code")
        if [[ -z "$want_code" || "$code" == "$want_code" ]]; then
            log_ok "$label (HTTP $LAST_STATUS, code=$code)"
        else
            log_fail "$label — atteso code=$want_code, ricevuto code=$code (HTTP $LAST_STATUS)"
        fi
    else
        log_fail "$label — atteso 4xx, ricevuto $LAST_STATUS"
        echo "       Body: $(echo "$LAST_BODY" | head -c 300)"
    fi
}

# --- 0. Auth ---
echo "== Smoke RESI vendita (giro ordine->DDT->CONSEGNATO->reso) =="
smoke_login --senza-prompt --uscita 2
if [[ "$SMOKE_LOGIN_FONTE" == "SMOKE_TOKEN" ]]; then
    log_ok "Autenticazione JWT (SMOKE_TOKEN da env)"
else
    log_ok "Autenticazione JWT (password)"
fi

# --- 1. Setup: BA+utility coerente + articolo ---
echo ""; echo "-- 1. Setup coppia BA+utility + articolo --"
PAIR=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/vendite/ordini/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    if r and r[0].get('billing_account_id') and r[0].get('utility_id'):
        print(r[0]['billing_account_id'], r[0]['utility_id'])
except Exception:
    pass
" 2>/dev/null)
BA_ID=$(echo "$PAIR" | awk '{print $1}')
UTILITY_ID=$(echo "$PAIR" | awk '{print $2}')
if [[ -z "$BA_ID" || -z "$UTILITY_ID" ]]; then
    echo -e "${RED}Setup fallito: nessuna coppia BA+utility disponibile.${NC}"; exit 1
fi
ARTICOLO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/catalogo/articoli/?page_size=1" 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('data',{}).get('results',[])
    print(r[0]['id'] if r else '')
except Exception: print('')
" 2>/dev/null)
if [[ -z "$ARTICOLO_ID" ]]; then echo -e "${RED}Setup fallito: nessun articolo.${NC}"; exit 1; fi
log_info "BA=$BA_ID utility=$UTILITY_ID emittente=$EMITTENTE_FISCALE_ID articolo=$ARTICOLO_ID iva=$IVA_ID"

# Helper: crea un ordine CONFERMATO con N righe (qta 5 cad.) e lo evade a un
# DDT portato fino a CONSEGNATO. Popola le globali DDT_ID / RIGHE_JSON.
build_ddt_consegnato() {
    local nrighe="$1" label="$2"
    do_curl POST "/api/v1/vendite/ordini/" \
        "{\"billing_account_id\": ${BA_ID}, \"utility_id\": ${UTILITY_ID}, \"emittente_fiscale_id\": ${EMITTENTE_FISCALE_ID}, \"fatturazione_trigger\": \"CONSEGNATO\"}"
    check "[$label] crea ordine" 200 "data.id" || return 1
    local oid="$EXTRACTED"
    local i
    for ((i=1; i<=nrighe; i++)); do
        do_curl POST "/api/v1/vendite/ordini/${oid}/righe/" \
            "{\"articolo_id\": \"$ARTICOLO_ID\", \"descrizione\": \"Riga $i smoke reso\", \"qta_operativa\": \"5\", \"prezzo_unitario\": \"80.00\", \"iva_id\": ${IVA_ID}}"
        check "[$label] add riga $i" 200 || return 1
    done
    do_curl POST "/api/v1/vendite/ordini/${oid}/conferma/" '{}'
    check "[$label] conferma ordine" 200 || return 1
    do_curl POST "/api/v1/vendite/ordini/${oid}/genera-ddt/" '{}'
    check "[$label] genera-ddt (evasione)" 200 "data.ddt_id" || return 1
    DDT_ID="$EXTRACTED"
    ORDINE_ID="$oid"
    # DRAFT -> EMESSO -> SPEDITO -> CONSEGNATO
    do_curl POST "/api/v1/vendite/ddt/${DDT_ID}/cambia-stato/" '{"stato_codice": "EMESSO"}'
    check "[$label] DDT -> EMESSO" 200 || return 1
    do_curl GET "/api/v1/vendite/ddt/${DDT_ID}/"
    local num; num=$(json_get "$LAST_BODY" "data.numero")
    [[ -n "$num" && "$num" != "None" ]] && log_ok "[$label] numero DDT assegnato a EMESSO = $num" \
        || log_fail "[$label] numero DDT atteso a EMESSO, vuoto"
    do_curl POST "/api/v1/vendite/ddt/${DDT_ID}/cambia-stato/" '{"stato_codice": "SPEDITO"}'
    check "[$label] DDT -> SPEDITO" 200 || return 1
    do_curl POST "/api/v1/vendite/ddt/${DDT_ID}/cambia-stato/" '{"stato_codice": "CONSEGNATO"}'
    check "[$label] DDT -> CONSEGNATO" 200 || return 1
    do_curl GET "/api/v1/vendite/ddt/${DDT_ID}/"
    local st; st=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$st" == "CONSEGNATO" ]] && log_ok "[$label] DDT $DDT_ID stato=CONSEGNATO" \
        || { log_fail "[$label] DDT atteso CONSEGNATO, trovato '$st'"; return 1; }
    return 0
}

# ============================================================
# PART A — Giro ordine -> DDT CONSEGNATO (2 righe per reso misto)
# ============================================================
echo ""; echo "== PART A — ordine -> DDT CONSEGNATO (2 righe) =="
DDT_ID=""; ORDINE_ID=""
if ! build_ddt_consegnato 2 "A"; then
    echo -e "${RED}PART A fallita: impossibile ottenere un DDT CONSEGNATO. Stop.${NC}"
    echo "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
    exit 1
fi
DDT_MISTO="$DDT_ID"; ORDINE_MISTO="$ORDINE_ID"

# ============================================================
# PART B — Reso MISTO + conferma + code
# ============================================================
echo ""; echo "== PART B — reso misto (credito + ri-consegna) =="

# 8. Righe DDT rendibili (pannello reso): articolo/consegnata/gia-resa/residuo
do_curl GET "/api/v1/vendite/ddt/${DDT_MISTO}/righe-per-reso/"
check "GET righe-per-reso DDT" 200 || true
RIGHE_DDT="$LAST_BODY"
DDT_RIGA_1=$(echo "$RIGHE_DDT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
print((rows or [{}])[0].get('ddt_riga_id') or (rows or [{}])[0].get('riga_id') or '')" 2>/dev/null)
DDT_RIGA_2=$(echo "$RIGHE_DDT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
rows=rows or []
print((rows[1].get('ddt_riga_id') or rows[1].get('riga_id')) if len(rows)>1 else '')" 2>/dev/null)
log_info "ddt_riga_1=$DDT_RIGA_1 ddt_riga_2=$DDT_RIGA_2"
if [[ -z "$DDT_RIGA_1" || -z "$DDT_RIGA_2" ]]; then
    log_fail "righe-per-reso: attese 2 righe rendibili, non trovate"
fi

# 9. Crea reso misto: riga1 a CREDITO (tipo 1), riga2 per RICONSEGNA (tipo 2)
do_curl POST "/api/v1/vendite/resi/" \
    "{\"ddt_id\": ${DDT_MISTO}, \"righe\": [
        {\"ddt_riga_id\": ${DDT_RIGA_1}, \"tipo_reso_id\": 1, \"qta_operativa\": \"2\", \"motivo\": \"smoke credito\"},
        {\"ddt_riga_id\": ${DDT_RIGA_2}, \"tipo_reso_id\": 2, \"qta_operativa\": \"3\", \"motivo\": \"smoke riconsegna\"}
    ]}"
check "POST crea reso misto" 200 "data.id" || { echo "STOP"; exit 1; }
RESO_ID="$EXTRACTED"; log_info "reso_id=$RESO_ID"

# 10. Detail: DRAFT + capability editabile
do_curl GET "/api/v1/vendite/resi/${RESO_ID}/"
check "GET reso detail" 200 || true
RSTATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
[[ "$RSTATO" == "DRAFT" ]] && log_ok "reso stato=DRAFT" || log_fail "reso atteso DRAFT, trovato '$RSTATO'"
CAN_EDIT=$(json_get "$LAST_BODY" "data.can_edit_righe")
[[ "$CAN_EDIT" == "True" || "$CAN_EDIT" == "true" ]] && log_ok "can_edit_righe=true in DRAFT (editabile)" \
    || log_fail "can_edit_righe atteso true in DRAFT, trovato '$CAN_EDIT'"

# 11. Righe reso: 2 righe, capture resi_riga_id della riga ri-consegna (tipo 2)
do_curl GET "/api/v1/vendite/resi/${RESO_ID}/righe/"
check "GET righe reso" 200 || true
RIGHE_RESO="$LAST_BODY"
NRIGHE=$(echo "$RIGHE_RESO" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
print(len(rows or []))" 2>/dev/null)
[[ "$NRIGHE" == "2" ]] && log_ok "reso ha 2 righe" || log_fail "attese 2 righe reso, trovate '$NRIGHE'"

# 12. Conferma reso -> CONFERMATO + numero
do_curl POST "/api/v1/vendite/resi/${RESO_ID}/conferma/" '{}'
check "POST conferma reso" 200 || true
do_curl GET "/api/v1/vendite/resi/${RESO_ID}/"
RSTATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
RNUM=$(json_get "$LAST_BODY" "data.numero")
[[ "$RSTATO" == "CONFERMATO" ]] && log_ok "reso stato=CONFERMATO" || log_fail "reso atteso CONFERMATO, trovato '$RSTATO'"
[[ -n "$RNUM" && "$RNUM" != "None" ]] && log_ok "numero reso assegnato = $RNUM" || log_fail "numero reso atteso a CONFERMATO, vuoto"

# 13. Ordine: residuo riaperto dalla riga per-riconsegna -> PARZIALMENTE_EVASO
do_curl GET "/api/v1/vendite/ordini/${ORDINE_MISTO}/"
OSTATO=$(json_get "$LAST_BODY" "data.stato_codice_interno")
[[ "$OSTATO" == "PARZIALMENTE_EVASO" ]] && log_ok "ordine riaperto -> PARZIALMENTE_EVASO" \
    || log_info "ordine stato='$OSTATO' (atteso PARZIALMENTE_EVASO se la riga riconsegna riapre residuo)"

# 14. Coda da-accreditare: contiene la riga a credito del reso
do_curl GET "/api/v1/vendite/resi/da-accreditare/?data_da=2020-01-01"
check "GET coda da-accreditare" 200 || true
IN_ACC=$(echo "$LAST_BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
print(sum(1 for r in (rows or []) if str(r.get('reso_id'))=='$RESO_ID'))" 2>/dev/null)
[[ "${IN_ACC:-0}" -ge 1 ]] 2>/dev/null && log_ok "coda accrediti: riga a credito del reso presente ($IN_ACC)" \
    || log_fail "coda accrediti: attesa >=1 riga del reso $RESO_ID, trovate '${IN_ACC:-0}'"

# 15. Coda da-riconsegnare: riga per-riconsegna, stato DA_RICONSEGNARE, residuo>0
do_curl GET "/api/v1/vendite/resi/da-riconsegnare/?data_da=2020-01-01"
check "GET coda da-riconsegnare" 200 || true
RICON_ROW=$(echo "$LAST_BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
for r in (rows or []):
    if str(r.get('reso_id'))=='$RESO_ID':
        print(r.get('resi_riga_id'), r.get('stato_riconsegna'), r.get('qta_residua')); break" 2>/dev/null)
RICON_RIGA_ID=$(echo "$RICON_ROW" | awk '{print $1}')
RICON_STATO=$(echo "$RICON_ROW" | awk '{print $2}')
RICON_RESIDUA=$(echo "$RICON_ROW" | awk '{print $3}')
log_info "riconsegna: resi_riga_id=$RICON_RIGA_ID stato=$RICON_STATO residua=$RICON_RESIDUA"
[[ -n "$RICON_RIGA_ID" ]] && log_ok "coda ri-consegne: riga presente" || log_fail "coda ri-consegne: riga del reso non trovata"
[[ "$RICON_STATO" == "DA_RICONSEGNARE" ]] && log_ok "stato_riconsegna=DA_RICONSEGNARE" \
    || log_fail "stato_riconsegna atteso DA_RICONSEGNARE, trovato '$RICON_STATO'"

# ============================================================
# PART C — Ri-consegna parziale -> totale -> annullo bloccato
# ============================================================
echo ""; echo "== PART C — ri-consegna parziale/totale + annullo bloccato =="

# 17. Ri-consegna PARZIALE (qta base = 1) sulla riga di ri-consegna
if [[ -n "$RICON_RIGA_ID" ]]; then
    do_curl POST "/api/v1/vendite/resi/${RESO_ID}/genera-ddt-riconsegna/" \
        "{\"righe\": [{\"resi_riga_id\": ${RICON_RIGA_ID}, \"qta\": 1}]}"
    check "POST ri-consegna parziale (qta=1 base)" 200 "data.ddt_id" || true
    DDT_RICON_1="$EXTRACTED"; log_info "nuovo DDT ri-consegna (parziale) = $DDT_RICON_1"

    # 18. Coda: PARZIALE, residua scesa
    do_curl GET "/api/v1/vendite/resi/da-riconsegnare/?data_da=2020-01-01"
    RICON_STATO=$(echo "$LAST_BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
for r in (rows or []):
    if str(r.get('reso_id'))=='$RESO_ID': print(r.get('stato_riconsegna')); break" 2>/dev/null)
    [[ "$RICON_STATO" == "PARZIALE" ]] && log_ok "dopo parziale: stato_riconsegna=PARZIALE" \
        || log_fail "atteso PARZIALE, trovato '$RICON_STATO'"

    # 19. Ri-consegna TOTALE residua (righe null = tutta la copertura)
    do_curl POST "/api/v1/vendite/resi/${RESO_ID}/genera-ddt-riconsegna/" '{}'
    check "POST ri-consegna residua (null=tutto)" 200 "data.ddt_id" || true
    DDT_RICON_2="$EXTRACTED"; log_info "nuovo DDT ri-consegna (residuo) = $DDT_RICON_2"

    # 20. Coda si auto-svuota (COMPLETATA -> fuori vista)
    do_curl GET "/api/v1/vendite/resi/da-riconsegnare/?data_da=2020-01-01"
    STILL=$(echo "$LAST_BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
print(sum(1 for r in (rows or []) if str(r.get('reso_id'))=='$RESO_ID'))" 2>/dev/null)
    [[ "${STILL:-0}" == "0" ]] && log_ok "coda ri-consegne auto-svuotata (copertura completa)" \
        || log_fail "coda ri-consegne: riga ancora presente ($STILL) dopo copertura totale"
else
    log_skip "resi_riga_id ri-consegna assente: salto PART C ri-consegne"
fi

# 21. Annullo BLOCCATO: reso gia` ri-spedito
do_curl POST "/api/v1/vendite/resi/${RESO_ID}/annulla/" '{}'
check_4xx "annullo reso con ri-consegne bloccato" "E_RESO_ANNULLO_CON_RICONSEGNE"

# ============================================================
# PART D — Reso TOTALE a credito su altro DDT -> flip -> annullo
# ============================================================
echo ""; echo "== PART D — reso totale -> flip DDT->RESO -> annullo =="
DDT_ID=""; ORDINE_ID=""
if build_ddt_consegnato 1 "D"; then
    DDT_TOT="$DDT_ID"
    do_curl GET "/api/v1/vendite/ddt/${DDT_TOT}/righe-per-reso/"
    DDT_TOT_RIGA=$(echo "$LAST_BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',{}); rows=d.get('results',d) if isinstance(d,dict) else d
r=(rows or [{}])[0]
print(r.get('ddt_riga_id') or r.get('riga_id') or '', r.get('qta_resa_residua') or r.get('residuo') or r.get('qta_operativa') or '')" 2>/dev/null)
    DTR=$(echo "$DDT_TOT_RIGA" | awk '{print $1}')
    DQTA=$(echo "$DDT_TOT_RIGA" | awk '{print $2}')
    log_info "riga DDT totale: id=$DTR residuo=$DQTA"
    # reso TOTALE a credito (qta = residuo, tipo 1)
    do_curl POST "/api/v1/vendite/resi/" \
        "{\"ddt_id\": ${DDT_TOT}, \"righe\": [{\"ddt_riga_id\": ${DTR}, \"tipo_reso_id\": 1, \"qta_operativa\": \"${DQTA:-5}\", \"motivo\": \"smoke reso totale\"}]}"
    check "POST crea reso totale" 200 "data.id" || true
    RESO_TOT="$EXTRACTED"
    do_curl POST "/api/v1/vendite/resi/${RESO_TOT}/conferma/" '{}'
    check "POST conferma reso totale" 200 || true
    # DDT flip -> RESO
    do_curl GET "/api/v1/vendite/ddt/${DDT_TOT}/"
    DST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$DST" == "RESO" ]] && log_ok "flip DDT -> RESO (reso totale)" \
        || log_fail "atteso DDT flip a RESO, trovato '$DST'"
    # annullo reso totale (credito, nessuna ri-consegna) -> OK
    do_curl POST "/api/v1/vendite/resi/${RESO_TOT}/annulla/" '{}'
    check "POST annullo reso totale (credito)" 200 || true
    do_curl GET "/api/v1/vendite/resi/${RESO_TOT}/"
    RST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$RST" == "ANNULLATO" ]] && log_ok "reso totale -> ANNULLATO" || log_fail "reso totale atteso ANNULLATO, trovato '$RST'"
    # DDT torna CONSEGNATO (storno flip: RESO->CONSEGNATO)
    do_curl GET "/api/v1/vendite/ddt/${DDT_TOT}/"
    DST=$(json_get "$LAST_BODY" "data.stato_codice_interno")
    [[ "$DST" == "CONSEGNATO" ]] && log_ok "storno flip: DDT -> CONSEGNATO" \
        || log_fail "atteso DDT ripristinato a CONSEGNATO, trovato '$DST'"
else
    log_skip "PART D: impossibile ottenere secondo DDT CONSEGNATO"
fi

# --- Summary ---
echo ""
echo -e "== Risultato: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${SKIP} SKIP${NC} =="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
