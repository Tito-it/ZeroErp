#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test E2E — GUIDA (D4): inversione handler→proiezione su PREVENTIVI.
# Valida sul percorso HTTP REALE che «Accetta»/«Rifiuta» in-pratica (endpoint
# da-pratica) cambino lo stato del preventivo e facciano AUTO-AVANZARE il
# milestone APPROVAZIONE_CLIENTE (step 9011) via il trigger `fn_reconcile_sorgente`.
# Copre entrambi i verdetti (binding G2 = NULL, inversione piena):
#   - Accetta → preventivo ACCETTATO → milestone COMPLETATO/POSITIVO
#   - Rifiuta → preventivo RIFIUTATO → milestone COMPLETATO/NEGATIVO
#
# Perché serve oltre al pgTAP: il pgTAP gira come ruolo OWNER (tutti i privilegi)
# in transazione rollbackata; questo smoke gira come ruolo APP reale sul percorso
# HTTP → cattura problemi di GRANT/permessi invisibili al pgTAP (es. i grant
# mancanti su reconcile_errori / template_flussi_avanzamento_proiezione, 2026-07-07).
#
# Setup/cleanup: direct-insert controllato (modello pgTAP) sullo step 9011 reale
# (tipo 9004, def 7), con la catena prerequisiti 9009→9010 completata a due-salti.
# Idempotente: marker 'SMOKE_GUIDA' + cleanup all'inizio e via trap EXIT.
#
# Uso:  ./scripts/tests/smoke-test-guida-inversione-preventivi.sh [password]
#   oppure, col login unico: eval "$(./scripts/tests/smoke-login.sh)" e poi lo smoke
#   (riusa SMOKE_TOKEN finche' vale, `_smoke_auth.sh`).
# Richiede: server BE attivo, .env.systemd (env DB per manage.py), l'utente degli
# smoke (SMOKE_USER) con un'identita' OPERATORE attiva.
# ------------------------------------------------------------
set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
# Login degli smoke (HTTPS come Nginx, secondo fattore, refresh, SMOKE_TOKEN): un BB.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
# Le GUC dei heredoc Python sono dello STESSO utente del login (letto da os.environ).
export SMOKE_GUC_USER="$USERNAME"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$BACKEND_DIR/.venv/bin/python"
MANAGE=("$PY" "$BACKEND_DIR/manage.py" "shell")

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0
log_ok()   { PASS=$((PASS+1)); echo -e "  ${GREEN}OK${NC}  $1"; }
log_fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${YELLOW}---${NC} $1"; }

set -a; . "$BACKEND_DIR/.env.systemd" 2>/dev/null || true; set +a

echo ""; echo "========================================="
echo " Smoke E2E — GUIDA inversione PREVENTIVI (step 9011)"
echo " Base: $BASE_URL"
echo "========================================="

# GUC operatore condiviso dagli heredoc Python (RLS: senza, le pratiche sono nascoste).
read -r -d '' GUC_PY <<'PY' || true
import os
from django.db import connection
def _guc(c):
    utente = os.environ["SMOKE_GUC_USER"]
    c.execute("""SELECT idg.id, idg.soggetto_ruolo_id, au.id FROM anagrafiche.identita_digitali idg
                 JOIN auth_user au ON au.id=idg.auth_user_id
                 WHERE au.username=%s AND idg.ruolo_applicativo='OPERATORE' AND idg.attivo IS TRUE LIMIT 1""", [utente])
    idid, srid, uid = c.fetchone()
    # ⛔ Anche l'emittente ATTIVO, lo stesso che il BE prende dal token: il seed
    # sceglie il preventivo-modello dentro il perimetro che vedra' l'API. Senza,
    # «l'ultimo preventivo» puo' essere di un altro emittente e la ricerca del
    # ROOT torna vuota (E_VENDITA_PREVENTIVO_NON_COLLEGATO, 2026-10-14).
    for k, v in [("app.current_user_id",str(uid)),("app.current_identita_id",str(idid)),
                 ("app.soggetto_ruolo_id",str(srid)),("app.ruolo_applicativo","OPERATORE"),("app.jwt_user",utente),
                 ("app.current_emittente_id",os.environ["SMOKE_GUC_EMITTENTE"])]:
        c.execute("SELECT set_config(%s,%s,false)", [k, v])
PY

# --- 0. Token ---
echo ""; echo "-- 0. Autenticazione --"
smoke_login
if [[ "$SMOKE_LOGIN_FONTE" == "SMOKE_TOKEN" ]]; then log_ok "Token da SMOKE_TOKEN"; else log_ok "Login JWT"; fi
# L'emittente attivo dell'operatore (BB `_smoke_cliente.sh`), per la GUC dei heredoc.
source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
smoke_emittente_attivo
if [[ -z "$EMITTENTE_ATTIVO_ID" ]]; then log_fail "Emittente attivo dell'operatore non risolto"; exit 1; fi
export SMOKE_GUC_EMITTENTE="$EMITTENTE_ATTIVO_ID"
log_ok "Emittente attivo: $EMITTENTE_ATTIVO_ID"
# Il cliente dei preventivi del seed: dal lookup (BB _smoke_cliente.sh), che
# restituisce solo i clienti dell'emittente attivo; la valuta dai default del
# form del preventivo per quel cliente. ⛔ Fino al 2026-10-18 la terna si
# copiava dall'«ultimo preventivo visibile»: su un emittente senza preventivi
# (l'emittente di prova di `dev.smoke`) il seed non partiva.
smoke_cliente_dal_lookup   # -> BA_ID, UTILITY_ID, ISTANZA_ID
SMOKE_SEED_VALUTA=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/v1/vendite/preventivi/form-defaults/?billing_account_id=${BA_ID:-0}" 2>/dev/null \
    | python3 -c "import sys, json; print((json.load(sys.stdin).get('data') or {}).get('valuta_id') or '')" 2>/dev/null)
if [[ -z "${BA_ID:-}" || -z "$SMOKE_SEED_VALUTA" ]]; then
    echo -e "${RED}Setup fallito: nessun cliente con utility e istanza (o senza valuta) per l'emittente attivo (motivo sopra). Stop.${NC}"
    exit 1
fi
export SMOKE_SEED_BA="$BA_ID" SMOKE_SEED_UTILITY="$UTILITY_ID" SMOKE_SEED_ISTANZA="$ISTANZA_ID" SMOKE_SEED_VALUTA
log_info "cliente del seed: BA=$BA_ID utility=$UTILITY_ID istanza=$ISTANZA_ID valuta=$SMOKE_SEED_VALUTA"

# --- Cleanup (inizio + trap) ---
cleanup() {
    "${MANAGE[@]}" >/dev/null 2>&1 <<PY
$GUC_PY
with connection.cursor() as c:
    _guc(c)
    sub = "(SELECT id FROM pratiche.pratiche WHERE descrizione LIKE 'SMOKE_GUIDA%')"
    c.execute(f"DELETE FROM pratiche.giornale WHERE pratica_id IN {sub}")
    c.execute(f"DELETE FROM pratiche.pratiche_sorgenti WHERE pratica_id IN {sub}")
    c.execute(f"DELETE FROM pratiche.flussi WHERE pratica_id IN {sub}")
    c.execute("DELETE FROM pratiche.pratiche WHERE descrizione LIKE 'SMOKE_GUIDA%'")
    c.execute("DELETE FROM vendite.preventivi WHERE numero LIKE 'SMOKE_GUIDA%'")
PY
}
trap cleanup EXIT
cleanup  # sweep residui pre-run

# seed → stampa "SEED <pratica_id> <preventivo_id> <flusso9011_id>". Crea pratica
# 9004 + preventivo EMESSO + catena prereq 9009→9010 completata + flusso 9011 aperto
# + link ROOT (flusso_id=9011). Ogni chiamata = uno scenario indipendente.
seed() {
    "${MANAGE[@]}" 2>/dev/null <<PY | grep '^SEED ' | sed 's/^SEED //'
$GUC_PY
import uuid
with connection.cursor() as c:
    _guc(c)
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE'"); da_eseg=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO'"); in_corso=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO'"); completato=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA'"); aperta=c.fetchone()[0]
    c.execute("SELECT id FROM config.sorgenti WHERE codice_interno='PREVENTIVO' AND attivo LIMIT 1"); src=c.fetchone()[0]
    # Priorita' per codice, come il default di `pratiche.fn_crea_pratica`. Prima
    # veniva da una pratica-modello 9004: con l'emittente attivo nelle GUC la
    # pratica-modello di un altro emittente e' invisibile, e il seed cadeva.
    c.execute("SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE'"); priorita=c.fetchone()[0]
    # Definizione e tipo prestazione dallo step 9011, l'ancora dello scenario:
    # la pratica deve stare nel percorso che contiene lo step (FK composta
    # `fk_template_flussi_definizione`). Niente id di definizione cablato.
    c.execute("SELECT definizione_id, tipo_prestazione_id FROM pratiche.template_flussi WHERE id=9011"); defin, tipo=c.fetchone()
    # Il preventivo nasce SEMPRE col suo cliente (billing_account_id NOT NULL,
    # brief-db-istanza-nasce-col-ba): la terna dal cliente del lookup, che e'
    # dell'emittente attivo (bash, sopra); l'emittente e' quello attivo.
    ba, istanza, utility, valuta = (int(os.environ[k]) for k in
        ("SMOKE_SEED_BA", "SMOKE_SEED_ISTANZA", "SMOKE_SEED_UTILITY", "SMOKE_SEED_VALUTA"))
    pemitt = int(os.environ["SMOKE_GUC_EMITTENTE"])
    # ⛔ La pratica e' COERENTE col preventivo: stesso emittente, e il suo
    # soggetto e' il cliente del preventivo. Fino al 2026-10-12 emittente e
    # soggetto venivano dalla pratica-modello, indipendente dal preventivo:
    # andavano d'accordo solo finche' il preventivo piu' recente era dello stesso
    # emittente (verde per sottrazione), e l'API rispondeva
    # E_VENDITA_PREVENTIVO_NON_COLLEGATO appena non lo era.
    c.execute("""SELECT sr.soggetto_id FROM anagrafiche.billing_account b
                 JOIN anagrafiche.soggetti_ruoli sr ON sr.id = b.soggetto_ruolo_id WHERE b.id = %s""", [ba])
    sogg = c.fetchone()[0]
    emitt = pemitt
    # Il preventivo NASCE in bozza (lo stato lo mette il DB, BB
    # `script.trgfn_doc_stato_iniziale`) e va a EMESSO per la matrice, sotto i
    # guard veri: brief-modello-documento-vendita N-1.
    c.execute("""INSERT INTO vendite.preventivi (numero, rev, billing_account_id, istanza_utility_id, utility_id, validita_dal, validita_al,
                   valuta_id, data, fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
                 VALUES (%s,0,%s,%s,%s,DATE '2026-07-01',DATE '2026-07-31',%s,DATE '2026-07-01',false,false,
                   '{"test_scope":"smoke_guida"}'::jsonb,%s) RETURNING id,(uid)::text""",
              [f"SMOKE_GUIDA-{uuid.uuid4().hex[:10]}", ba, istanza, utility, valuta, pemitt])
    prev_id, prev_uid = c.fetchone()
    c.execute("SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', %s, 'EMESSO')", [prev_id])
    c.execute("""INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id,
                   priorita_id, definizione_id, descrizione) VALUES (%s,%s,%s,%s,%s,%s,'SMOKE_GUIDA E2E') RETURNING id""",
              [emitt, tipo, sogg, aperta, priorita, defin])
    prat_id = c.fetchone()[0]
    for step in (9009, 9010):  # catena prereq: instanzia+completa (due-salti) prima di 9011
        c.execute("INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s,%s,%s) RETURNING id", [prat_id, step, da_eseg])
        fid=c.fetchone()[0]
        c.execute("UPDATE pratiche.flussi SET stato_id=%s WHERE id=%s", [in_corso, fid])
        c.execute("UPDATE pratiche.flussi SET stato_id=%s, esito='POSITIVO' WHERE id=%s", [completato, fid])
    c.execute("INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s,9011,%s) RETURNING id", [prat_id, da_eseg])
    flusso_id=c.fetchone()[0]
    c.execute("""INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
                 VALUES (%s,%s,%s,'ROOT',%s)""", [prat_id, src, prev_uid, flusso_id])
    print(f"SEED {prat_id} {prev_id} {flusso_id}")
PY
}

# stato(prev_id, flusso_id) → "STATO_PREV STATO_FLUSSO ESITO_FLUSSO"
stato() {
    "${MANAGE[@]}" 2>/dev/null <<PY | grep '^STATO ' | sed 's/^STATO //'
$GUC_PY
with connection.cursor() as c:
    _guc(c)
    c.execute("SELECT sd.codice_interno FROM vendite.preventivi pr JOIN config.stati_doc_preventivi sd ON sd.id=pr.stato_doc_preventivo_id WHERE pr.id=$1")
    sp=(c.fetchone() or ['?'])[0]
    c.execute("SELECT sf.codice_interno, COALESCE(f.esito,'-') FROM pratiche.flussi f JOIN config.stati_flussi_pratiche sf ON sf.id=f.stato_id WHERE f.id=$2")
    sf=c.fetchone() or ['?','-']
    print(f"STATO {sp} {sf[0]} {sf[1]}")
PY
}

# scenario LABEL NUOVO_STATO PAYLOAD_EXTRA_JSON EXP_PREV EXP_ESITO
scenario() {
    local label="$1" nuovo="$2" extra="$3" exp_prev="$4" exp_esito="$5"
    echo ""; echo "-- $label (da-pratica → $nuovo) --"
    read -r prat prev flusso < <(seed)
    [[ -z "${prat:-}" ]] && { log_fail "$label: seed fallito"; return; }
    log_info "scenario: pratica=$prat preventivo=$prev flusso9011=$flusso"
    local http
    http="$(curl -s -o /tmp/guida_$label.json -w '%{http_code}' -X POST \
        -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
        -d "{\"nuovo_stato\":\"$nuovo\"$extra}" \
        "${BASE_URL}/api/v1/vendite/preventivi/da-pratica/${prat}/stato/")"
    [[ "$http" == "200" ]] && log_ok "$label: POST da-pratica (HTTP 200)" \
        || log_fail "$label: POST da-pratica — atteso 200, ricevuto $http: $(head -c 250 /tmp/guida_$label.json)"
    read -r sp sf se < <(stato "$prev" "$flusso")
    log_info "$label: preventivo=$sp · flusso9011=$sf/$se"
    [[ "$sp" == "$exp_prev" ]] && log_ok "$label: preventivo $exp_prev (documento sovrano)" \
        || log_fail "$label: preventivo atteso $exp_prev, e' $sp"
    [[ "$sf" == "COMPLETATO" && "$se" == "$exp_esito" ]] \
        && log_ok "$label: milestone 9011 auto-avanzato COMPLETATO/$exp_esito (proiezione)" \
        || log_fail "$label: milestone atteso COMPLETATO/$exp_esito, e' $sf/$se"
}

scenario "Accetta" "ACCETTATO" ',"fatturazione_immediata":true' "ACCETTATO" "POSITIVO"
scenario "Rifiuta" "RIFIUTATO" "" "RIFIUTATO" "NEGATIVO"

echo ""; echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
