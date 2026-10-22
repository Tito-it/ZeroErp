#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test RLS scope Emittente Fiscale — lato OPERATORE.
#
# Verifica end-to-end che, con la RLS attiva (Ondata 1+2), un operatore
# con whitelist EF veda SOLO i propri emittenti:
#   - la LISTA contratti restituisce solo righe del proprio emittente;
#   - il DETTAGLIO by-id di un contratto FUORI scope torna 404
#     (prova RLS-specifica: il getter `get_contratto` NON ha filtro
#      applicativo → senza RLS tornerebbe 200; con RLS → None → 404);
#   - controprova: il dettaglio di un contratto IN scope torna 200
#     (il 404 non è "tutto 404" da GUC mancante).
#
# Le chiamate HTTP sono di sola lettura (login + GET + refresh audit). Il
# setup scrive, una volta: i due contratti di prova della «materia» (sotto),
# riusati ai giri successivi → nessun cleanup necessario.
#
# Uso: ./scripts/tests/smoke-test-rls-emittente-operatore.sh
#   L'operatore e' `dev.emittente`, l'operatore ristretto del provisioning di
#   sviluppo (solo l'emittente di prova A in whitelist, senza secondo fattore;
#   brief-be-utenti-di-sviluppo §4.1, run-book §11). La password e'
#   DEV_EMITTENTE_PASSWORD di `env.sh`, che il runner carica: lo smoke non
#   gira piu' con SMOKE_USER, che e' `dev.smoke`, senza whitelist (fino al
#   2026-10-22 il runner lo lanciava cosi', e finiva sempre «non conclusivo»).
#
# ⭐ LA MATERIA SI COSTRUISCE, UNA VOLTA (brief-be-utenti-di-sviluppo §9.11):
#   un contratto sull'emittente in whitelist (lista e controprova 200) e uno
#   su un altro emittente di prova (il 404). Li assicura un setup in-process
#   come `dev.smoke` col builder del DB (`dbops.fn_pgtap_crea_contratto`),
#   cercati per cliente di prova e creati se mancano: materia STABILE, come
#   i `SMOKE-*` di preventivi-componenti. Le chiamate HTTP restano di sola
#   lettura. Prima il 404 voleva un id passato a mano, ed era sempre SALTATO.
#
# Variabili:
#   BASE_URL                     default http://127.0.0.1:8000
#   SMOKE_RLS_USER / SMOKE_RLS_PASSWORD  (opz.) un altro operatore CON riga in
#                                user_emittenti_fiscali
# ------------------------------------------------------------
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
# Utente DIVERSO dall'utente generale degli smoke: l'operatore ristretto del
# provisioning (vedi testata).
USERNAME="${SMOKE_RLS_USER:-dev.emittente}"
PASSWORD="${SMOKE_RLS_PASSWORD:-${DEV_EMITTENTE_PASSWORD:-}}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

TMPFILE=$(mktemp); trap 'rm -f "$TMPFILE"' EXIT

log_ok()   { PASS=$((PASS+1)); echo -e "  ${GREEN}OK${NC}    $1"; }
log_fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}FAIL${NC}  $1"; }
log_warn() { WARN=$((WARN+1)); echo -e "  ${YELLOW}WARN${NC}  $1"; }
log_info() { echo -e "  ${BLUE}info${NC}  $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Query DB su tabelle NON-RLS (auth_user, user_emittenti_fiscali,
# emittenti_fiscali). Gira come ruolo applicativo via dbshell: va bene
# perché queste tabelle non hanno RLS attiva.
db_query() {
    "${BACKEND_DIR}/manage-env.sh" dbshell -- -t -A -c "$1" 2>/dev/null | grep -v '^$' || true
}

# Parser UNICO della risposta lista (stdin → stdout). Gestisce envelope
# comuni ({data:{items:[]}}, {data:[]}, {results:[]}, ...) ed emette:
#   FIRST_ID=<id del primo elemento>   (riga singola, vuoto se assente)
#   EF=<emittente_fiscale_id>          (una riga per elemento)
# La logica envelope è scritta UNA VOLTA SOLA qui.
parse_lista() {
    python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("FIRST_ID="); sys.exit(0)
def rows(x):
    if isinstance(x, list): return x
    if isinstance(x, dict):
        for k in ("items","results","data","contratti"):
            if isinstance(x.get(k), list): return x[k]
        for v in x.values():
            r = rows(v)
            if r: return r
    return []
rs = rows(d)
ids = [r["id"] for r in rs if isinstance(r, dict) and r.get("id")]
print("FIRST_ID=" + (str(ids[0]) if ids else ""))
for r in rs:
    if isinstance(r, dict) and "emittente_fiscale_id" in r:
        print("EF=" + str(r["emittente_fiscale_id"]))
'
}

echo ""
echo "============================================================"
echo " Smoke RLS scope Emittente Fiscale — OPERATORE"
echo " Base URL: $BASE_URL   User: ${USERNAME:-<da impostare>}"
echo "============================================================"

if [[ -z "$PASSWORD" ]]; then
    echo -e "${RED}ERRORE: password di '$USERNAME' mancante (DEV_EMITTENTE_PASSWORD in env.sh: run-book §11).${NC}"
    exit 2
fi

# ---- Materia: un contratto dentro e uno fuori dal perimetro ----------
# In-process come `dev.smoke` (lo stesso contesto degli smoke Python), col
# builder del DB, sull'emittente che si sta guardando (`app.current_emittente_id`).
# ⚠️ Lo stderr del setup si tiene: un setup rotto non deve travestirsi da
#    «manca il secondo emittente» e far SALTARE il 404 senza dire perche'.
MATERIA_ERR=$(mktemp)
MATERIA=$(cd "$BACKEND_DIR" && SMOKE_RLS_USER="$USERNAME" ./manage-env.sh shell 2>"$MATERIA_ERR" <<'PY' | grep '^RLS_' || true
import os
from django.db import connection
from scripts.tests._smoke_contesto import apri_contesto_smoke

with connection.cursor() as cur:
    apri_contesto_smoke(cur)
    # Dentro: l'emittente in whitelist dell'operatore ristretto. Fuori: un
    # emittente di prova che non ha (riconosciuto dall'etichetta).
    cur.execute(
        """
        SELECT ef.id, (ef.id IN (SELECT u.emittente_fiscale_id
                                   FROM config.user_emittenti_fiscali u
                                   JOIN auth_user au ON au.id = u.auth_user_id
                                  WHERE au.username = %s)) AS dentro
          FROM anagrafiche.emittenti_fiscali ef
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
          JOIN dbops.soggetti_di_prova sp ON sp.soggetto_id = sr.soggetto_id
         WHERE ef.attivo
         ORDER BY ef.codice
        """,
        [os.environ["SMOKE_RLS_USER"]],
    )
    scelti = {}
    for ef_id, dentro in cur.fetchall():
        scelti.setdefault("IN" if dentro else "OUT", ef_id)
    for lato, ef_id in sorted(scelti.items()):
        cur.execute("SELECT set_config('app.current_emittente_id', %s, false)", [str(ef_id)])
        cur.execute(
            """
            SELECT ba.id
              FROM anagrafiche.billing_account ba
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
              JOIN dbops.soggetti_di_prova sp ON sp.soggetto_id = sr.soggetto_id
              JOIN anagrafiche.emittenti_fiscali_billing_account efba ON efba.billing_account_id = ba.id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
             WHERE ef.id = %s
             ORDER BY ba.codice LIMIT 1
            """,
            [ef_id],
        )
        ba = cur.fetchone()
        if ba is None:
            continue
        # ⚠️ Il contratto si cerca per BA **e** emittente: un BA puo' essere
        #    legato a piu' emittenti (emittenti_fiscali_billing_account), e un
        #    contratto del BA preso sull'altro lato renderebbe il 404 un 200
        #    — un «leak» falso.
        cur.execute(
            "SELECT id FROM vendite.contratti"
            " WHERE billing_account_id = %s AND emittente_fiscale_id = %s"
            " ORDER BY id LIMIT 1",
            [ba[0], ef_id],
        )
        k = cur.fetchone()
        if k is None:
            # DRAFT: al test basta che il contratto esista. Un ATTIVO lo
            # rifiuterebbe il modello se sullo stesso BA ce n'e' gia' uno
            # sovrapposto (dell'altro emittente), e vorrebbe un listino.
            cur.execute("SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('smoke rls', 'DRAFT', %s)", [ba[0]])
            k = cur.fetchone()
        print(f"RLS_{lato}_CONTRATTO_ID={k[0]}")
PY
)
OUT_OF_SCOPE_ID=$(printf '%s\n' "$MATERIA" | sed -n 's/^RLS_OUT_CONTRATTO_ID=//p')
if [[ -z "$MATERIA" ]] && grep -q 'Traceback' "$MATERIA_ERR"; then
    echo -e "${RED}ERRORE: setup della materia fallito:${NC}"
    tail -n 5 "$MATERIA_ERR" | sed 's/^/        /'
    rm -f "$MATERIA_ERR"
    exit 1
fi
rm -f "$MATERIA_ERR"

# ---- 0. Login -> token + auth_user_id -------------------------------
echo ""; echo "-- 0. Login JWT --"
# SMOKE_TOKEN di un altro utente non entra: il BB lo riusa solo se e' di USERNAME.
smoke_login
log_ok "JWT ottenuto"
USER_ID=$(db_query "SELECT id FROM auth_user WHERE username='$USERNAME' LIMIT 1" | tail -1)
if ! [[ "$USER_ID" =~ ^[0-9]+$ ]]; then
    log_fail "auth_user.id non risolto per '$USERNAME': DB non raggiungibile via dbshell o utente inesistente. Le query di setup non funzionano → smoke inattendibile."
    exit 1
fi
log_info "auth_user.id = $USER_ID"

# ---- 1. Whitelist EF dell'operatore (tabella NON-RLS) ---------------
echo ""; echo "-- 1. Whitelist emittente dell'operatore --"
OP_EF=$(db_query "SELECT emittente_fiscale_id FROM config.user_emittenti_fiscali WHERE auth_user_id=$USER_ID ORDER BY emittente_fiscale_id LIMIT 1" | tail -1)
if [[ -z "$OP_EF" ]]; then
    log_warn "L'utente '$USERNAME' NON ha whitelist (operatore globale): non si può testare l'isolamento. Usare un operatore con riga in config.user_emittenti_fiscali."
    echo ""; echo "============================================================"
    echo -e " ${YELLOW}Smoke non conclusivo: serve un operatore ristretto.${NC}"; exit 0
fi
log_ok "operatore ristretto all'emittente_fiscale_id = $OP_EF"

# ---- 2+3. Lista contratti (fetch UNICO) → filtro + controprova ------
echo ""; echo "-- 2. Lista contratti filtrata per emittente --"
curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/vendite/contratti/?data_da=2000-01-01" > "$TMPFILE"

# Parser UNICO sulla risposta lista: emette il primo id (FIRST_ID=) e
# tutti gli emittente_fiscale_id (EF=). Niente logica envelope duplicata.
PARSED=$(parse_lista < "$TMPFILE")
FIRST_ID=$(echo "$PARSED" | sed -n 's/^FIRST_ID=//p')
EMITTENTI=$(echo "$PARSED" | sed -n 's/^EF=//p')
N_TOT=$(echo "$EMITTENTI" | grep -cE '[0-9]' || true)
N_FUORI=$(echo "$EMITTENTI" | grep -vxE "[[:space:]]*$OP_EF[[:space:]]*" | grep -cE '[0-9]' || true)

if [[ "$N_TOT" -eq 0 ]]; then
    log_warn "lista vuota o senza campo emittente_fiscale_id. Diagnosi: (a) operatore senza contratti in scope; (b) GUC non propagati (R-GUC) → 0 righe; (c) la lista non espone emittente_fiscale_id."
elif [[ "$N_FUORI" -gt 0 ]]; then
    log_fail "$N_FUORI/$N_TOT contratti con emittente != $OP_EF → LEAK. Diagnosi: vista definer (manca security_invoker), RLS non ENABLE, o zeroerp_app è BYPASSRLS."
    echo "$EMITTENTI" | sort -u | sed 's/^/        EF visto: /'
else
    log_ok "tutti i $N_TOT contratti in lista hanno emittente=$OP_EF (filtro RLS attivo)"
fi

# ---- 3. Controprova: dettaglio IN scope → 200 (riusa FIRST_ID) ------
echo ""; echo "-- 3. Controprova: dettaglio contratto IN scope --"
if [[ -n "$FIRST_ID" ]]; then
    IN_STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/contratti/$FIRST_ID/")
    if [[ "$IN_STATUS" == "200" ]]; then
        log_ok "contratto in scope (id=$FIRST_ID) → HTTP 200"
    else
        log_fail "contratto in scope (id=$FIRST_ID) → HTTP $IN_STATUS (atteso 200: GUC non propagati?)"
    fi
else
    log_warn "nessun contratto in scope da usare come controprova 200"
fi

# ---- 4. Dettaglio FUORI scope -> 404 (prova RLS) --------------------
echo ""; echo "-- 4. Dettaglio contratto FUORI scope → 404 --"
if [[ -z "$OUT_OF_SCOPE_ID" ]]; then
    log_warn "nessun contratto fuori perimetro costruito (manca un secondo emittente di prova col suo cliente: rilancia il provisioning) → test 404 SALTATO."
    log_info "Per ricavarlo (come ruolo BYPASSRLS, es. titodb):"
    log_info "  SELECT id FROM vendite.contratti WHERE emittente_fiscale_id <> $OP_EF LIMIT 1;"
else
    OOS_STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/vendite/contratti/$OUT_OF_SCOPE_ID/")
    if [[ "$OOS_STATUS" == "404" ]]; then
        log_ok "contratto FUORI scope (id=$OUT_OF_SCOPE_ID) → HTTP 404 (RLS filtra → getter None → E_VENDITE_NOT_FOUND)"
    elif [[ "$OOS_STATUS" == "200" ]]; then
        log_fail "contratto FUORI scope (id=$OUT_OF_SCOPE_ID) → HTTP 200 → RLS NON filtra (leak!). Vedi diagnosi §2."
    else
        log_warn "contratto FUORI scope (id=$OUT_OF_SCOPE_ID) → HTTP $OOS_STATUS (atteso 404; verificare che l'id esista e sia di un altro EF)"
    fi
fi

# ---- Riepilogo ------------------------------------------------------
echo ""; echo "============================================================"
echo -e " Riepilogo: ${GREEN}${PASS} OK${NC}, ${RED}${FAIL} FAIL${NC}, ${YELLOW}${WARN} WARN${NC}"
echo "============================================================"
[[ "$FAIL" -gt 0 ]] && { echo -e "${RED}Smoke FALLITO: la RLS non sta isolando correttamente per emittente.${NC}"; exit 1; }
[[ "$WARN" -gt 0 ]] && { echo -e "${YELLOW}Smoke passato con warning — leggere i messaggi sopra.${NC}"; exit 0; }
echo -e "${GREEN}Smoke passato: l'operatore vede solo il proprio emittente (lista filtrata + 404 fuori scope).${NC}"
exit 0
