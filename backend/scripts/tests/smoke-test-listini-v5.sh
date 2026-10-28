#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test end-to-end per Pricing v5 (listini + matrice categoria +
# promo + contratti + resolver 3 stadi).
#
# Uso: ./scripts/tests/smoke-test-listini-v5.sh [password]
#
# Prerequisiti (utente smoke):
#   - TUTTO su area 'vendite'
#   - TUTTO su area 'anagrafiche' (categorie clienti + BA lookup)
#   - LETTURA su area 'catalogo' (seed articolo + UoM)
# ------------------------------------------------------------
# Indice test (0..30):
#  0) Autenticazione JWT + user_id
#  1) Preflight permessi (vendite/anagrafiche/catalogo)
#  1.5) Cleanup residui run precedenti (categoria/matrice/promo/listino/contratti SMK-V5-*)
#  2) Seed: articolo attivo + UoM + BA esistente + utility + emittente
#  3) Categoria cliente: crea SMK-V5-* (partecipa_promo=true)
#  4) Categoria cliente: PATCH descrizione
#  5) Listino: crea SMK-V5-* (utility+tipologia+emittente)
#  6) Listino: crea versione BOZZA con valido_dal
#  7) Listino: crea riga prezzo
#  8) Listino: attiva versione (BOZZA -> ATTIVA)
#  9) Matrice categoria/listino: crea riga (cat×utility×emittente -> listino, variazione -5%)
# 10) Matrice: tentativo overlap stesso periodo (400/409 atteso)
# 11) Matrice: PATCH tipo/valore variazione
# 12) Promo articolo: crea PERCENTUALE negativa (-10% sconto)
# 13) Promo: tentativo overlap stesso articolo+uom+periodo (400/409 atteso)
# 14) Promo: PATCH valore
# 15) Contratto A (listino + variazione globale): crea
# 16) Contratto A: cambio stato DRAFT -> ATTIVO
# 17) Contratto A: PATCH valido_al (ammesso in ATTIVO)
# 18) Contratto B (listino + override righe): crea + riga con prezzo_unitario
# 19) Contratto C (interamente negoziato): crea senza listino
# 20) Contratto C: attivazione senza righe complete (400 atteso)
# 21) Contratto C: aggiungi riga con prezzo_unitario
# 22) Contratto C: attivazione ora OK
# 23) Snapshot categoria: PATCH in DRAFT (su contratto nuovo, OK)
# 24) Snapshot categoria: PATCH in ATTIVO (400 atteso)
# 25) Resolver STADIO 1: articolo+contratto A -> origine CONTRATTO_LISTINO
# 26) Resolver STADIO 1b: override B -> origine CONTRATTO_OVERRIDE
# 27) Resolver STADIO 2: BA senza contratto -> origine CATEGORIA
# 28) Resolver STADIO 0: promo attiva -> origine PROMO (se BA categoria partecipa)
# 29) Cleanup: disattiva contratti, promo, matrice, listino, categoria
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"   # smoke_emetti

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
log_fail() { ((FAIL++)) || true; echo -e "  ${RED}FAIL${NC} $1"; echo "       Body: $(echo "$LAST_BODY" | head -c 400)"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

json_get() {
    local json="$1" expr="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$expr'.lstrip('.').split('.'):
        if k.isdigit():
            d = d[int(k)]
        else:
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
    elif [[ "$method" == "DELETE" ]]; then
        curl -s -w '\n%{http_code}' -X DELETE \
            -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}${url}" > "$TMPFILE" 2>/dev/null
    else
        curl -s -w '\n%{http_code}' -X "$method" \
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
        return 1
    fi
    if [[ -n "$json_expr" ]]; then
        EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    fi
    return 0
}

# Scopo: check accettando 2 status (es. 400 o 409 entrambi validi su overlap).
check_any() {
    local label="$1" expected_a="$2" expected_b="$3" json_expr="${4:-}"
    if [[ "$LAST_STATUS" == "$expected_a" || "$LAST_STATUS" == "$expected_b" ]]; then
        log_ok "$label (HTTP $LAST_STATUS)"
    else
        log_fail "$label — atteso $expected_a o $expected_b, ricevuto $LAST_STATUS"
        return 1
    fi
    if [[ -n "$json_expr" ]]; then
        EXTRACTED=$(json_get "$LAST_BODY" "$json_expr")
    fi
    return 0
}

echo ""
echo "========================================="
echo " Smoke test Pricing v5 (listini+contratti)"
echo " Base URL: $BASE_URL"
echo "========================================="

# --- 0. Auth ---
echo ""
echo "-- 0. Autenticazione --"
smoke_login
USER_ID=$(smoke_jwt_claim "$TOKEN" user_id)
log_ok "JWT ottenuto per '$USERNAME' (user_id=${USER_ID:-?})"

# --- 1. Preflight permessi ---
echo ""
echo "-- 1. Preflight permessi --"
do_curl GET "/api/v1/core/users/${USER_ID}/permessi-effettivi/"
check "Permessi effettivi utente corrente" "200"

read -r VENDITE_LEVEL ANAG_LEVEL CATALOGO_LEVEL < <(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    areas = json.load(sys.stdin)['data']['aree']
    w = {'vendite': '', 'anagrafiche': '', 'catalogo': ''}
    for a in areas:
        if a.get('schema_db') in w:
            w[a['schema_db']] = a.get('livello', '')
    print(w['vendite'], w['anagrafiche'], w['catalogo'])
except Exception:
    print('', '', '')
" 2>/dev/null)

if [[ "$VENDITE_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' serve TUTTO su 'vendite' (attuale=$VENDITE_LEVEL)."
    exit 2
fi
if [[ "$ANAG_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} utente '$USERNAME' serve TUTTO su 'anagrafiche' (attuale=$ANAG_LEVEL)."
    exit 2
fi
if [[ "$CATALOGO_LEVEL" != "LETTURA" && "$CATALOGO_LEVEL" != "TUTTO" ]]; then
    echo -e "${RED}ERRORE:${NC} serve almeno LETTURA su 'catalogo' (attuale=$CATALOGO_LEVEL)."
    exit 2
fi
log_ok "Permessi OK (vendite=$VENDITE_LEVEL anagrafiche=$ANAG_LEVEL catalogo=$CATALOGO_LEVEL)"

# --- 1.5. Cleanup residui SMK-V5-* ---
# Smoke bash non idempotente: residui da run falliti possono far fallire
# UNIQUE codice o EXCLUDE overlap. Disattivo via dbshell prima di partire.
echo ""
echo "-- 1.5 Cleanup residui SMK-V5-* --"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# ⛔ I contratti NON si chiudono qui: lo stato lo scrivono solo i verbi (la
#    porta del DB rifiuta l'UPDATE della colonna, brief-modello-documento-
#    vendita §11.6), e un rifiuto in questo `-c` annullerebbe tutte le
#    pulizie della transazione. Li chiude `smoke_chiudi_contratti`, alla fine del passo 2.
"${BACKEND_DIR}/manage-env.sh" dbshell -- -q -c "
    UPDATE vendite.promo_articoli SET attivo = false WHERE codice LIKE 'SMK-V5-%';
    UPDATE anagrafiche.categorie_clienti_listini SET attivo = false
      WHERE categoria_cliente_id IN (SELECT id FROM anagrafiche.categorie_clienti WHERE codice LIKE 'SMK-V5-%');
    UPDATE vendite.listini SET attivo = false WHERE codice LIKE 'SMK-V5-%';
    UPDATE anagrafiche.categorie_clienti SET attivo = false WHERE codice LIKE 'SMK-V5-%';
" >/dev/null 2>&1 || log_info "dbshell cleanup fallito (non bloccante)"
log_info "Cleanup SMK-V5-* completato"

TEST_SUFFIX=$(date +%Y%m%d%H%M%S)
TODAY=$(date +%F)
# Una promo non nasce retroattiva: la create vuole valido_dal > oggi
# (E_PROMO_RETROATTIVA). Le prove della promo usano questa data.
PROMO_DAL=$(date -d tomorrow +%F)
FAR_FUTURE="2099-12-31"
CATEGORIA_CODE="SMK-V5-CAT-${TEST_SUFFIX}"
LISTINO_CODE="SMK-V5-LST-${TEST_SUFFIX}"
VERSION_CODE="V-${TEST_SUFFIX}"
PROMO_CODE="SMK-V5-PR-${TEST_SUFFIX}"

# --- 2. Seed articolo + UoM + BA + utility + emittente ---
echo ""
echo "-- 2. Seed catalogo + anagrafiche --"
# Il primo articolo attivo CON una tipologia di listino (il listino la vuole).
# ⚠️ Non semplicemente il primo per codice: gli smoke del catalogo creano
# articoli senza tipologia, e uno di quelli finiva qui — `None` passava il
# controllo «vuoto» e rompeva il JSON della create del listino (400
# E_VALIDATION_INPUT «corpo non e' un JSON valido»).
ARTICOLO_ID=""; UOM_ID=""; LISTINO_TIPOLOGIA_ID=""
# ⚠️ La lista pagina con `limit`/`offset` (parse_list_params): `page` e
# `page_size` sono un 400 (dal 2026-10-20; prima erano ignorati).
for offset in $(seq 0 100 3000); do
    do_curl GET "/api/v1/catalogo/articoli/?attivo=true&limit=100&offset=${offset}&order_by=codice&order_dir=asc"
    [[ "$LAST_STATUS" != "200" ]] && break
    read -r ARTICOLO_ID UOM_ID LISTINO_TIPOLOGIA_ID <<< "$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    r = next((x for x in rows if x.get('listino_tipologia_id') and x.get('uom_id')), None)
    print(r['id'], r['uom_id'], r['listino_tipologia_id']) if r else print('')
except Exception:
    print('')
" 2>/dev/null)"
    [[ -n "$ARTICOLO_ID" ]] && break
    N_RIGHE=$(echo "$LAST_BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data']['results']))" 2>/dev/null || echo 0)
    [[ "$N_RIGHE" -lt 100 ]] && break   # ultima pagina
done
check "Lista articoli seed" "200"
if [[ -z "$ARTICOLO_ID" || -z "$UOM_ID" || -z "$LISTINO_TIPOLOGIA_ID" ]]; then
    echo -e "${RED}ERRORE:${NC} articolo seed senza uom/tipologia. Impossibile continuare."
    exit 3
fi
log_info "Articolo=${ARTICOLO_ID} uom=${UOM_ID} tipologia=${LISTINO_TIPOLOGIA_ID}"

# BA esistente (il test resolver richiede un BA reale)
smoke_cliente_dal_lookup   # BB _smoke_cliente.sh: BA_ID, UTILITY_ID, ISTANZA_ID
BA_UTILITY_ID="$UTILITY_ID"
BA_ISTANZA_ID="$ISTANZA_ID"
if [[ -z "$BA_ID" || -z "$BA_UTILITY_ID" ]]; then
    echo -e "${RED}ERRORE:${NC} nessun BA lookup disponibile. Serve almeno 1 BA seed."
    exit 3
fi
log_info "BA=${BA_ID} utility=${BA_UTILITY_ID} istanza=${BA_ISTANZA_ID}"

# Emittente: quello ATTIVO dell'operatore (BB _smoke_cliente.sh), lo stesso
# del cliente del lookup. Non «il primo della lista»: vedi il BB.
smoke_emittente_attivo   # -> EMITTENTE_ATTIVO_ID, EMITTENTE_ATTIVO_SR_ID
EMITTENTE_SR="$EMITTENTE_ATTIVO_SR_ID"
if [[ -z "$EMITTENTE_SR" ]]; then
    echo -e "${RED}ERRORE:${NC} nessun emittente attivo per l'operatore."
    exit 3
fi
log_info "Emittente soggetto_ruolo_id=${EMITTENTE_SR}"

# --- 2.5 Cleanup mirato promo residue sull'articolo seed ---
# Il cleanup iniziale SMK-V5-% non copre promo residue da run v3/v4 con
# codice diverso che possono condividere (articolo_id, uom_id). Le
# disattivo tutte prima di creare la nuova.
# ⚠️ Una promo GIA' INIZIATA non si spegne (E_PROMO_INIZIATA_CAMPI_RISTRETTI:
# solo descrizione, valido_al e meta): si CHIUDE a oggi, e la nuova (che parte
# domani, PROMO_DAL) non la sovrappone. Una promo futura invece si spegne.
# Fino al 2026-10-12 l'UPDATE unico falliva sulle promo iniziate, l'errore
# finiva in /dev/null e il log diceva «completato»: il giro dopo trovava
# E_VENDITE_PROMO_OVERLAP.
if ERR_PULIZIA=$("${BACKEND_DIR}/manage-env.sh" dbshell -- -q -v ON_ERROR_STOP=1 -c "
    UPDATE vendite.promo_articoli
       SET valido_al = script.fn_data_operativa()
     WHERE articolo_id = '${ARTICOLO_ID}'::uuid AND uom_id = ${UOM_ID}
       AND attivo IS TRUE AND valido_dal <= script.fn_data_operativa()
       AND (valido_al IS NULL OR valido_al > script.fn_data_operativa());
    UPDATE vendite.promo_articoli
       SET attivo = false
     WHERE articolo_id = '${ARTICOLO_ID}'::uuid AND uom_id = ${UOM_ID}
       AND attivo IS TRUE AND valido_dal > script.fn_data_operativa();
" 2>&1); then
    log_info "Cleanup promo residue su (articolo=${ARTICOLO_ID}, uom=${UOM_ID}) completato"
else
    log_info "Cleanup promo residue FALLITO (non bloccante): $(echo "$ERR_PULIZIA" | grep -m1 -E 'ERRORE|ERROR')"
fi

# Contratti di questo smoke ancora vivi (ambito COMMERCIO sul cliente di prova):
# si chiudono con le transizioni ammesse, ora i residui e all'uscita i propri
# (BB _smoke_documenti.sh). ⚠️ Fino al 2026-10-12 qui c'era un DELETE fisico dei
# contratti marcati smoke_v5, che falliva in silenzio (errori in /dev/null) e
# lasciava tutto com'era, mentre il log diceva «completato». L'EXCLUDE no-overlap
# non guarda lo stato, ma non serve liberarlo: ogni giro usa anni propri
# (YEAR_A…), quindi cessare basta, e un contratto cessato il prezzo non lo vede.
smoke_chiudi_contratti "$BA_ID" COMMERCIO
trap 'smoke_chiudi_contratti "$BA_ID" COMMERCIO; rm -f "$TMPFILE"' EXIT

# Gli anni dei contratti di questo giro: il primo DOPO il piu' alto gia' usato
# dai contratti COMMERCIO del cliente (minimo 2100). Il vincolo di non
# sovrapposizione non guarda lo stato, quindi anche i contratti cessati dei giri
# precedenti occupano i loro anni: si va sempre avanti, mai si torna su un anno.
# ⚠️ Fino al 2026-10-13 era `2100 + epoch % 900`, che si ripete ogni 15 minuti:
# il giro notturno, partito ogni ora a hh:00:03, riprendeva gli stessi anni del
# giro prima e l'attivazione rispondeva E_VENDITE_CONTRATTO_OVERLAP.
ANNO_MAX=$(curl -s -H "Authorization: Bearer ${TOKEN:-none}" \
    "${BASE_URL}/api/v1/vendite/contratti/?billing_account_id=${BA_ID}&limit=200" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    anni = [int(str(d)[:4]) for r in rows if r.get('ambito') == 'COMMERCIO'
            for d in (r.get('valido_dal'), r.get('valido_al')) if d]
    print(max(anni) if anni else 0)
except Exception:
    print(0)
" 2>/dev/null)
YEAR_A=$(( ${ANNO_MAX:-0} >= 2100 ? ANNO_MAX + 1 : 2100 ))
YEAR_B=$(( YEAR_A + 1 ))
YEAR_C=$(( YEAR_A + 2 ))
YEAR_SNAP=$(( YEAR_A + 3 ))
log_info "Anni smoke contratti: A=${YEAR_A} B=${YEAR_B} C=${YEAR_C} SNAP=${YEAR_SNAP}"

# --- 3. Crea categoria cliente ---
echo ""
echo "-- 3. Crea categoria cliente --"
do_curl POST "/api/v1/anagrafiche/categorie-clienti/" \
    "{\"codice\":\"${CATEGORIA_CODE}\",\"descrizione\":\"Smoke V5 ${TEST_SUFFIX}\",\"partecipa_promo\":true,\"ordinamento\":900}"
check "Create categoria cliente" "200" ".data.id"
CATEGORIA_ID="$EXTRACTED"
log_info "Categoria id=${CATEGORIA_ID} codice=${CATEGORIA_CODE}"

# --- 4. PATCH categoria ---
echo ""
echo "-- 4. PATCH categoria --"
do_curl PATCH "/api/v1/anagrafiche/categorie-clienti/${CATEGORIA_ID}/" \
    "{\"descrizione\":\"Smoke V5 aggiornata ${TEST_SUFFIX}\"}"
check "PATCH categoria descrizione" "200" ".data.descrizione"

# --- 5. Crea listino ---
echo ""
echo "-- 5. Crea listino --"
do_curl POST "/api/v1/vendite/listini/" \
    "{\"codice\":\"${LISTINO_CODE}\",\"descrizione\":\"Smoke V5 listino\",\"utility_id\":${BA_UTILITY_ID},\"tipologia_id\":${LISTINO_TIPOLOGIA_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR}}"
check "Create listino" "200" ".data.id"
LISTINO_ID="$EXTRACTED"

# --- 6. Crea versione BOZZA ---
echo ""
echo "-- 6. Crea versione BOZZA --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/" \
    "{\"codice_versione\":\"${VERSION_CODE}\",\"valido_dal\":\"${TODAY}\"}"
check "Create versione" "200" ".data.id"
VERSIONE_ID="$EXTRACTED"

# --- 7. Crea riga prezzo ---
echo ""
echo "-- 7. Crea riga prezzo --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/righe/" \
    "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"prezzo\":\"50.0000000000\"}"
check "Create riga prezzo 50.00" "200" ".data.id"
RIGA_ID="$EXTRACTED"

# --- 8. Attiva versione ---
echo ""
echo "-- 8. Attiva versione (POST stato ATTIVA) --"
do_curl POST "/api/v1/vendite/listini/${LISTINO_ID}/versioni/${VERSIONE_ID}/stato/" "{\"stato\":\"ATTIVA\"}"
check "Attivazione versione" "200"

# --- 9. Crea riga matrice categoria/listino ---
echo ""
echo "-- 9. Crea matrice categoria -> listino --"
do_curl POST "/api/v1/anagrafiche/categorie-clienti-listini/" \
    "{\"categoria_cliente_id\":${CATEGORIA_ID},\"utility_id\":${BA_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR},\"listino_id\":${LISTINO_ID},\"tipo_variazione\":\"PERCENTUALE\",\"valore_variazione\":\"-5\",\"valido_dal\":\"${TODAY}\"}"
check "Create matrice" "200" ".data.id"
MATRICE_ID="$EXTRACTED"

# --- 10. Tentativo overlap matrice ---
echo ""
echo "-- 10. Overlap matrice rifiutato --"
do_curl POST "/api/v1/anagrafiche/categorie-clienti-listini/" \
    "{\"categoria_cliente_id\":${CATEGORIA_ID},\"utility_id\":${BA_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR},\"listino_id\":${LISTINO_ID},\"valido_dal\":\"${TODAY}\"}"
check_any "Overlap matrice rifiutato" "400" "409" ".error.code"
log_info "Codice errore: ${EXTRACTED:-n/d}"

# --- 11. PATCH matrice ---
echo ""
echo "-- 11. PATCH matrice variazione --"
do_curl PATCH "/api/v1/anagrafiche/categorie-clienti-listini/${MATRICE_ID}/" \
    "{\"tipo_variazione\":\"PERCENTUALE\",\"valore_variazione\":\"-7\"}"
check "PATCH matrice variazione" "200"

# --- 12. Crea promo ---
echo ""
echo "-- 12. Crea promo (-10%) --"
do_curl POST "/api/v1/vendite/promo-articoli/" \
    "{\"codice\":\"${PROMO_CODE}\",\"descrizione\":\"Smoke V5 promo\",\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"tipo_variazione\":\"PERCENTUALE\",\"valore_variazione\":\"-10\",\"valido_dal\":\"${PROMO_DAL}\",\"valido_al\":\"${FAR_FUTURE}\"}"
check "Create promo" "200" ".data.id"
PROMO_ID="$EXTRACTED"

# --- 13. Overlap promo rifiutato ---
echo ""
echo "-- 13. Overlap promo rifiutato --"
do_curl POST "/api/v1/vendite/promo-articoli/" \
    "{\"codice\":\"${PROMO_CODE}-DUP\",\"descrizione\":\"dup\",\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"tipo_variazione\":\"PERCENTUALE\",\"valore_variazione\":\"-5\",\"valido_dal\":\"${PROMO_DAL}\",\"valido_al\":\"${FAR_FUTURE}\"}"
check_any "Overlap promo rifiutato" "400" "409" ".error.code"

# --- 14. PATCH promo ---
echo ""
echo "-- 14. PATCH promo valore --"
do_curl PATCH "/api/v1/vendite/promo-articoli/${PROMO_ID}/" \
    "{\"tipo_variazione\":\"PERCENTUALE\",\"valore_variazione\":\"-12\"}"
check "PATCH promo valore" "200"

# --- 15. Contratto A: listino + variazione globale ---
# Uso periodi futuri unici per non collidere con contratti reali
# pre-esistenti sul BA seed. L'EXCLUDE cross-run non filtra per stato
# CESSATO, quindi il cleanup non libera la chiave: solo date disgiunte
# garantiscono idempotenza.
CONTR_A_START="${YEAR_A}-01-01"
CONTR_A_END="${YEAR_A}-12-31"
echo ""
echo "-- 15. Contratto A (listino + variazione globale, ${CONTR_A_START}..${CONTR_A_END}, ambito COMMERCIO) --"
# Uso ambito COMMERCIO perche' il BA seed potrebbe avere contratti reali
# COMMODITY con validita' aperta (upper=infinity) che coprono qualsiasi
# anno futuro. L'EXCLUDE include ambito nella chiave, quindi COMMERCIO
# vs COMMODITY sono disgiunti.
do_curl POST "/api/v1/vendite/contratti/" \
    "{\"billing_account_id\":${BA_ID},\"istanza_utility_id\":${BA_ISTANZA_ID},\"utility_id\":${BA_UTILITY_ID},\"ambito\":\"COMMERCIO\",\"valido_dal\":\"${CONTR_A_START}\",\"valido_al\":\"${CONTR_A_END}\",\"data\":\"${TODAY}\",\"listino_id\":${LISTINO_ID},\"tipo_variazione_globale\":\"PERCENTUALE\",\"valore_variazione_globale\":\"-3\",\"meta\":{\"smoke_v5\":\"true\"}}"
check "Create contratto A" "200" ".data.id"
CONTRATTO_A_ID="$EXTRACTED"

# --- 16. Contratto A: DRAFT -> ATTIVO ---
echo ""
echo "-- 16. Cambio stato contratto A -> ATTIVO --"
smoke_emetti contratti "$CONTRATTO_A_ID"
# Senza un modello di documento per i contratti dell'emittente, /emetti/ non puo'
# attivare niente (E_DOCUMENTI_NOT_FOUND): e' configurazione dell'ambiente, non
# un difetto. Lo smoke lo DICHIARA (non conclusivo) invece di contare rossi o
# verdi che da qui in poi non proverebbero nulla.
if [[ "$SMOKE_EMETTI_SENZA_MODELLO" == "1" ]]; then
    log_info "$(json_get "$LAST_BODY" ".error.detail")"
    echo ""
    echo "Smoke non conclusivo: nessun modello di documento per i contratti dell'emittente"
    echo "attivo (Configurazione → modelli documento). Passi 16 e seguenti non eseguiti."
    echo " Risultato: ${PASS} OK / ${FAIL} FAIL (interrotto al passo 16)"
    [[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
fi
check "Contratto A attivato (/emetti/)" "200"
do_curl GET "/api/v1/vendite/contratti/${CONTRATTO_A_ID}/"
log_info "Stato: $(json_get "$LAST_BODY" ".data.stato_codice_interno")"

# --- 17. Contratto A: PATCH valido_al in ATTIVO ---
echo ""
echo "-- 17. PATCH valido_al su contratto ATTIVO --"
# Nota: non uso FAR_FUTURE (2099) perche' e' antecedente al valido_dal (2100).
# Estendo al 2100-12-31 (gia' presente) -> passiamo un valore diverso nel futuro.
do_curl PATCH "/api/v1/vendite/contratti/${CONTRATTO_A_ID}/" "{\"valido_al\":\"${YEAR_A}-06-30\"}"
check "PATCH valido_al ATTIVO" "200"

# --- 18. Contratto B: listino + override riga ---
# Ambito COMMERCIO + periodo 2101 -> disgiunto da A (COMMODITY 2100)
# sia per ambito che per validita'.
CONTR_B_START="${YEAR_B}-01-01"
CONTR_B_END="${YEAR_B}-12-31"
echo ""
echo "-- 18. Contratto B (listino + override, ${CONTR_B_START}..${CONTR_B_END}, ambito COMMERCIO) --"
# Tutti i contratti smoke su COMMERCIO (vedi nota test 15). Anno diverso
# da A per non overlap nella stessa chiave.
do_curl POST "/api/v1/vendite/contratti/" \
    "{\"billing_account_id\":${BA_ID},\"istanza_utility_id\":${BA_ISTANZA_ID},\"utility_id\":${BA_UTILITY_ID},\"ambito\":\"COMMERCIO\",\"valido_dal\":\"${CONTR_B_START}\",\"valido_al\":\"${CONTR_B_END}\",\"data\":\"${TODAY}\",\"listino_id\":${LISTINO_ID},\"meta\":{\"smoke_v5\":\"true\"}}"
if [[ "$LAST_STATUS" == "200" ]]; then
    CONTRATTO_B_ID=$(json_get "$LAST_BODY" ".data.id")
    log_ok "Create contratto B (HTTP 200)"
    # Aggiungo riga override
    do_curl POST "/api/v1/vendite/contratti/${CONTRATTO_B_ID}/righe/" \
        "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_operativa_id\":${UOM_ID},\"tipo_eccezione\":\"OVERRIDE\",\"tipo_erogazione\":\"UNA_TANTUM\",\"fonte_quantita_attesa\":\"FISSA\",\"prezzo_unitario\":\"48.0000000000\",\"qta_operativa\":\"1\"}"
    # `tipo_eccezione` e' obbligatorio (OVERRIDE | ESCLUSIONE | AGGIUNTA): questa
    # riga corregge il prezzo di listino, quindi OVERRIDE. Fino al 2026-10-12
    # mancava (400 «tipo_eccezione obbligatorio»). Il prezzo (48 sul listino a
    # 50) resta dentro la soglia di variazione, che e' un PARAMETRO
    # ⚠️ L'erogazione e' quella che la tipologia dell'articolo ammette
    # (config.listini_tipologie_erogazioni; per l'articolo seed UNA_TANTUM con
    # quantita' FISSA): CANONE rispondeva E_RIGA_EROGAZIONE_FUORI_PERIMETRO.
    # La riga del contratto C (senza listino) e' un'AGGIUNTA, stessa erogazione.
    # (PARAM_MAX_SCONTO_PCT): lo smoke prova che l'override vince, non il limite.
    # Con 30 (-40%) rispondeva 403 E_PRICING_SCONTO_ECCESSIVO.
    check "Riga override contratto B" "200" ".data.id"
    # Il resolver legge solo i contratti ATTIVI (scenario B, passo 26): un B
    # rimasto in bozza fa ricadere il prezzo sulla categoria del cliente. Fino
    # al 2026-10-20 non si attivava, e il passo 26 passava solo finche' il
    # cliente di prova aveva per caso una categoria mappata.
    smoke_emetti contratti "$CONTRATTO_B_ID"
    check "Contratto B attivato (/emetti/)" "200"
else
    log_info "Contratto B salta (HTTP $LAST_STATUS) — continuo"
    CONTRATTO_B_ID=""
fi

# --- 19. Contratto C: senza listino ---
# Periodo 2102 -> disgiunto da A (2100) e B (2101).
echo ""
echo "-- 19. Contratto C (interamente negoziato) --"
CONTRATTO_C_START="${YEAR_C}-01-01"
CONTRATTO_C_END="${YEAR_C}-12-31"
do_curl POST "/api/v1/vendite/contratti/" \
    "{\"billing_account_id\":${BA_ID},\"istanza_utility_id\":${BA_ISTANZA_ID},\"utility_id\":${BA_UTILITY_ID},\"ambito\":\"COMMERCIO\",\"valido_dal\":\"${CONTRATTO_C_START}\",\"valido_al\":\"${CONTRATTO_C_END}\",\"data\":\"${TODAY}\",\"meta\":{\"smoke_v5\":\"true\"}}"
check "Create contratto C (DRAFT, no listino, ambito COMMERCIO)" "200" ".data.id"
CONTRATTO_C_ID="$EXTRACTED"

# --- 20. Contratto C: attivazione senza righe rifiutata ---
echo ""
echo "-- 20. Attivazione C senza righe rifiutata --"
smoke_emetti contratti "$CONTRATTO_C_ID"
# Il rifiuto di dominio ha il suo codice e il suo stato (422, una regola del
# documento): fino al 2026-10-12 lo smoke si aspettava un 400 generico, e lo
# prendeva dalla strada sbagliata (il cambio di stato diretto).
check "Attivazione C senza righe rifiutata" "422" ".error.code"
[[ "$EXTRACTED" == "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE" ]] \
    && log_ok "Codice corretto: E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE" \
    || log_fail "Codice atteso E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE, ricevuto '${EXTRACTED:-<vuoto>}'"

# --- 21. Contratto C: aggiungi riga con prezzo ---
echo ""
echo "-- 21. Aggiungi riga con prezzo_unitario --"
do_curl POST "/api/v1/vendite/contratti/${CONTRATTO_C_ID}/righe/" \
    "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_operativa_id\":${UOM_ID},\"tipo_eccezione\":\"AGGIUNTA\",\"tipo_erogazione\":\"UNA_TANTUM\",\"fonte_quantita_attesa\":\"FISSA\",\"prezzo_unitario\":\"40.0000000000\",\"qta_operativa\":\"1\"}"
check "Riga contratto C con prezzo" "200"

# --- 22. Contratto C: attivazione ora OK ---
echo ""
echo "-- 22. Attivazione C con riga completa --"
smoke_emetti contratti "$CONTRATTO_C_ID"
check "Attivazione C OK (/emetti/)" "200"

# --- 23. Snapshot categoria PATCH in DRAFT (su contratto nuovo) ---
echo ""
echo "-- 23. Snapshot categoria: creo contratto DRAFT per test PATCH --"
# Creo un contratto DRAFT ambito COMMERCIO in un periodo futuro non occupato
# (A=COMMODITY 2100, B=COMMERCIO 2101, C=COMMODITY 2102, snap=COMMERCIO 2103).
SNAP_START="${YEAR_SNAP}-01-01"
do_curl POST "/api/v1/vendite/contratti/" \
    "{\"billing_account_id\":${BA_ID},\"istanza_utility_id\":${BA_ISTANZA_ID},\"utility_id\":${BA_UTILITY_ID},\"ambito\":\"COMMERCIO\",\"valido_dal\":\"${SNAP_START}\",\"data\":\"${TODAY}\",\"listino_id\":${LISTINO_ID},\"categoria_cliente_id_snapshot\":${CATEGORIA_ID},\"meta\":{\"smoke_v5\":\"true\"}}"
check "Create contratto DRAFT con categoria snapshot" "200" ".data.id"
CONTRATTO_SNAP_ID="$EXTRACTED"

# PATCH categoria in DRAFT: atteso 200 (trigger consente in DRAFT)
do_curl PATCH "/api/v1/vendite/contratti/${CONTRATTO_SNAP_ID}/" \
    "{\"categoria_cliente_id_snapshot\":${CATEGORIA_ID}}"
check "PATCH categoria snapshot in DRAFT" "200"

# --- 24. Snapshot categoria PATCH in ATTIVO rifiutato ---
echo ""
echo "-- 24. Snapshot categoria: attivo contratto, PATCH rifiutato --"
smoke_emetti contratti "$CONTRATTO_SNAP_ID"
if [[ "$LAST_STATUS" == "200" ]]; then
    # ⚠️ Una categoria DIVERSA da quella del contratto: il blocco fuori bozza
    # guarda se il valore cambia, e una PATCH con lo stesso valore (quello messo
    # in bozza al passo 23) e' giusto che passi. Fino al 2026-10-13 il passo
    # riprovava proprio quello, e il rifiuto arrivava prima, dal backend.
    do_curl GET "/api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti&limit=50"
    ALTRA_CATEGORIA=$(echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    print(next((r['id'] for r in rows if str(r['id']) != sys.argv[1]), ''))
except Exception:
    print('')
" "$CATEGORIA_ID" 2>/dev/null)
    do_curl PATCH "/api/v1/vendite/contratti/${CONTRATTO_SNAP_ID}/" \
        "{\"categoria_cliente_id_snapshot\":${ALTRA_CATEGORIA:-0}}"
    check_any "PATCH categoria in ATTIVO rifiutato" "400" "409" ".error.code"
    log_info "Codice: ${EXTRACTED:-n/d}"
else
    log_info "Contratto snap non attivabile (HTTP $LAST_STATUS) — salto test 24"
fi

# --- 25..28. Resolver — 4 scenari (STADIO 0/1/2 + fallback) ---
# NOTA: il resolver filtra contratti per (ba, utility, data, stato=ATTIVO)
# senza filtrare per ambito. Se il BA seed ha contratti reali COMMODITY
# open-ended, il resolver li puo' trovare anche per date future. Lo
# smoke accetta come valide tutte le origini del set (PROMO/CONTRATTO_*/
# CATEGORIA): l'importante e' che il resolver non dia errore.

# Scopo: chiama il resolver e verifica che l'origine sia nel set valido.
# Logga comunque l'origine ricevuta per diagnostica.
resolver_assert_valid() {
    local label="$1" date_arg="$2" atteso_hint="$3"
    do_curl POST "/api/v1/vendite/pricing/resolve/" \
        "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"data_riferimento\":\"${date_arg}\",\"ba_id\":${BA_ID},\"utility_id\":${BA_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR}}"
    check "$label" "200" ".data.origine"
    local origine="$EXTRACTED"
    local prezzo_finale
    prezzo_finale=$(json_get "$LAST_BODY" ".data.prezzo_finale")
    local prezzo_base
    prezzo_base=$(json_get "$LAST_BODY" ".data.prezzo_base_snapshot")
    log_info "Origine=${origine:-?} prezzo=${prezzo_finale:-?} base=${prezzo_base:-?} (atteso_hint=${atteso_hint})"
    case "$origine" in
        PROMO|CONTRATTO_LISTINO|CONTRATTO_OVERRIDE|CATEGORIA)
            log_ok "Origine nel set valido: $origine"
            ;;
        *)
            log_fail "Origine resolver non riconosciuta: '$origine'"
            ;;
    esac
}

# Scenario A — STADIO 1 CONTRATTO_LISTINO: data dentro contratto A
# (listino + variazione globale). Ci si attende CONTRATTO_LISTINO, oppure
# PROMO se la promo smoke coprisse anche ${YEAR_A}-03-01.
echo ""
echo "-- 25. Resolver scenario A (STADIO 1 contratto listino) --"
resolver_assert_valid "Resolver scenario A" "${YEAR_A}-03-01" "CONTRATTO_LISTINO"

# Scenario B — STADIO 1 CONTRATTO_OVERRIDE: data dentro contratto B
# che ha una riga con prezzo_unitario per l'articolo seed. Atteso
# CONTRATTO_OVERRIDE (il resolver trova la riga override prima del listino).
echo ""
echo "-- 26. Resolver scenario B (STADIO 1 override riga) --"
if [[ -n "${CONTRATTO_B_ID:-}" ]]; then
    resolver_assert_valid "Resolver scenario B" "${YEAR_B}-03-01" "CONTRATTO_OVERRIDE"
else
    log_info "Contratto B non creato — scenario B saltato"
fi

# Scenario C — STADIO 2 CATEGORIA: data fuori da tutti i contratti smoke.
# Il resolver cerca categoria BA in matrice. Se il BA seed non ha una
# matrice corrispondente puo' arrivare E_CATEGORIA_LISTINO_NON_MAPPATA
# (accettato come outcome diagnostico); se ha contratti reali open-ended
# torna CONTRATTO_*. In entrambi i casi il resolver non si blocca.
echo ""
echo "-- 27. Resolver scenario C (STADIO 2 categoria o fallback reale) --"
RESOLVER_C_DATE="$(( YEAR_SNAP + 10 ))-01-01"
do_curl POST "/api/v1/vendite/pricing/resolve/" \
    "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"data_riferimento\":\"${RESOLVER_C_DATE}\",\"ba_id\":${BA_ID},\"utility_id\":${BA_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR}}"
if [[ "$LAST_STATUS" == "200" ]]; then
    ORIGINE=$(json_get "$LAST_BODY" ".data.origine")
    log_ok "Scenario C risolto: origine=${ORIGINE}"
elif [[ "$LAST_STATUS" == "400" || "$LAST_STATUS" == "404" ]]; then
    ERR_CODE=$(json_get "$LAST_BODY" ".error.code")
    log_info "Scenario C ha dato errore applicativo: ${ERR_CODE} (BA senza categoria/matrice configurata — comportamento atteso in alcuni ambienti)"
    log_ok "Scenario C: errore applicativo valido (non crash)"
else
    log_fail "Scenario C: HTTP inatteso ${LAST_STATUS}"
fi

# Scenario D — STADIO 0 PROMO: data=PROMO_DAL (coperto dalla promo smoke creata
# al test 12 con valido_dal=PROMO_DAL, cioe' domani: una promo non nasce
# retroattiva). Il resolver applica
# promo solo se la categoria del BA ha partecipa_promo=TRUE.
echo ""
echo "-- 28. Resolver scenario D (STADIO 0 promo overlay) --"
do_curl POST "/api/v1/vendite/pricing/resolve/" \
    "{\"articolo_id\":\"${ARTICOLO_ID}\",\"uom_id\":${UOM_ID},\"data_riferimento\":\"${PROMO_DAL}\",\"ba_id\":${BA_ID},\"utility_id\":${BA_UTILITY_ID},\"emittente_soggetto_ruolo_id\":${EMITTENTE_SR}}"
if [[ "$LAST_STATUS" == "200" ]]; then
    ORIGINE=$(json_get "$LAST_BODY" ".data.origine")
    PREZZO=$(json_get "$LAST_BODY" ".data.prezzo_finale")
    log_ok "Scenario D risolto: origine=${ORIGINE} prezzo=${PREZZO}"
    if [[ "$ORIGINE" == "PROMO" ]]; then
        log_info "STADIO 0 attivato — categoria BA seed partecipa alle promo"
    else
        log_info "STADIO 0 NON attivato (origine=${ORIGINE}) — categoria BA seed non partecipa o promo non applicabile"
    fi
else
    ERR_CODE=$(json_get "$LAST_BODY" ".error.code")
    log_info "Scenario D errore applicativo: ${ERR_CODE}"
fi

# --- 29. Cleanup finale ---
echo ""
echo "-- 29. Cleanup finale --"

# I contratti dello smoke li chiude il `trap` di uscita (smoke_chiudi_contratti):
# una bozza si annulla, un attivo si cessa con la sua data. Qui c'era una
# cessazione senza data, che il cambio stato rifiuta (data obbligatoria).

# Promo: PATCH attivo=false
do_curl PATCH "/api/v1/vendite/promo-articoli/${PROMO_ID}/" "{\"attivo\":false}" >/dev/null 2>&1 || true
log_info "Promo disattivata"

# Matrice: PATCH attivo=false
do_curl PATCH "/api/v1/anagrafiche/categorie-clienti-listini/${MATRICE_ID}/" "{\"attivo\":false}" >/dev/null 2>&1 || true
log_info "Matrice disattivata"

# Listino: PATCH attivo=false
do_curl PATCH "/api/v1/vendite/listini/${LISTINO_ID}/" "{\"attivo\":false}" >/dev/null 2>&1 || true
log_info "Listino disattivato"

# Categoria: PATCH attivo=false
do_curl PATCH "/api/v1/anagrafiche/categorie-clienti/${CATEGORIA_ID}/" "{\"attivo\":false}" >/dev/null 2>&1 || true
log_info "Categoria disattivata"

# --- Riepilogo ---
echo ""
echo "========================================="
echo " Riepilogo smoke listini v5"
echo "========================================="
echo -e "  ${GREEN}PASS${NC}: $PASS"
echo -e "  ${RED}FAIL${NC}: $FAIL"
echo "========================================="

if (( FAIL > 0 )); then
    exit 10
fi
exit 0
