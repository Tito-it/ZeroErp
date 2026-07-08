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
#   oppure  SMOKE_TOKEN=<jwt> ./...   (salta il login)
# Richiede: server BE attivo, .env.systemd (env DB per manage.py), utente 'tid'.
# ------------------------------------------------------------
set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
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
from django.db import connection
def _guc(c):
    c.execute("""SELECT idg.id, idg.soggetto_ruolo_id, au.id FROM anagrafiche.identita_digitali idg
                 JOIN auth_user au ON au.id=idg.auth_user_id
                 WHERE au.username='tid' AND idg.ruolo_applicativo='OPERATORE' AND idg.attivo IS TRUE LIMIT 1""")
    idid, srid, uid = c.fetchone()
    for k, v in [("app.current_user_id",str(uid)),("app.current_identita_id",str(idid)),
                 ("app.soggetto_ruolo_id",str(srid)),("app.ruolo_applicativo","OPERATORE"),("app.jwt_user","tid")]:
        c.execute("SELECT set_config(%s,%s,false)", [k, v])
PY

# --- 0. Token ---
echo ""; echo "-- 0. Autenticazione --"
if [[ -n "${SMOKE_TOKEN:-}" ]]; then
    TOKEN="$SMOKE_TOKEN"; log_ok "Token da SMOKE_TOKEN"
else
    PASSWORD="${1:-${SMOKE_PASSWORD:-}}"
    if [[ -z "$PASSWORD" ]]; then echo -n "Password per 'tid': "; read -rs PASSWORD; echo ""; fi
    TOKEN="$(curl -s -H "Content-Type: application/json" \
        -d "{\"username\":\"tid\",\"password\":\"$PASSWORD\"}" \
        "${BASE_URL}/api/v1/admin/token/" | "$PY" -c "import sys,json;print(json.load(sys.stdin).get('access',''))" 2>/dev/null)"
    [[ -z "$TOKEN" ]] && { echo -e "${RED}Auth fallita${NC}"; exit 1; }
    log_ok "Login JWT"
fi

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
    c.execute("SELECT id FROM config.stati_doc_preventivi WHERE codice_interno='EMESSO'"); emesso=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE'"); da_eseg=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO'"); in_corso=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO'"); completato=c.fetchone()[0]
    c.execute("SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA'"); aperta=c.fetchone()[0]
    c.execute("SELECT id FROM config.sorgenti WHERE codice_interno='PREVENTIVO' AND attivo LIMIT 1"); src=c.fetchone()[0]
    c.execute("""SELECT priorita_id, emittente_fiscale_id, soggetto_id, definizione_id FROM pratiche.pratiche
                 WHERE tipo_prestazione_id=9004 AND soggetto_id IS NOT NULL AND definizione_id=7 ORDER BY id DESC LIMIT 1""")
    priorita, emitt, sogg, defin = c.fetchone()
    c.execute("""SELECT istanza_utility_id, utility_id, valuta_id, emittente_fiscale_id FROM vendite.preventivi
                 WHERE utility_id IS NOT NULL AND istanza_utility_id IS NOT NULL ORDER BY id DESC LIMIT 1""")
    istanza, utility, valuta, pemitt = c.fetchone()
    c.execute("""INSERT INTO vendite.preventivi (numero, rev, istanza_utility_id, utility_id, validita_dal, validita_al,
                   valuta_id, stato_doc_preventivo_id, data, fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
                 VALUES (%s,0,%s,%s,DATE '2026-07-01',DATE '2026-07-31',%s,%s,DATE '2026-07-01',false,false,
                   '{"test_scope":"smoke_guida"}'::jsonb,%s) RETURNING id,(uid)::text""",
              [f"SMOKE_GUIDA-{uuid.uuid4().hex[:10]}", istanza, utility, valuta, emesso, pemitt])
    prev_id, prev_uid = c.fetchone()
    c.execute("""INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id,
                   priorita_id, definizione_id, descrizione) VALUES (%s,9004,%s,%s,%s,%s,'SMOKE_GUIDA E2E') RETURNING id""",
              [emitt, sogg, aperta, priorita, defin])
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
