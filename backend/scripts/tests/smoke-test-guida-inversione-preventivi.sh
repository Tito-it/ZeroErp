#!/usr/bin/env bash
# ------------------------------------------------------------
# Smoke test E2E — GUIDA (D4): inversione handler→proiezione su PREVENTIVI.
# Valida sul percorso HTTP REALE che «Accetta» in-pratica (endpoint da-pratica)
# porti il preventivo ad ACCETTATO e faccia AUTO-AVANZARE il milestone
# APPROVAZIONE_CLIENTE (step 9011) via il trigger DB `fn_reconcile_sorgente`.
#
# Perché serve oltre al pgTAP: il pgTAP gira come ruolo OWNER (tutti i privilegi)
# in transazione rollbackata; questo smoke gira come ruolo APP reale sul percorso
# HTTP → cattura problemi di GRANT/permessi invisibili al pgTAP.
#
# Setup/cleanup: direct-insert controllato (modello pgTAP) sullo step 9011 reale
# (tipo 9004, def 7), con la catena prerequisiti 9009→9010 completata a due-salti.
# Idempotente: marker 'SMOKE_GUIDA' + cleanup all'inizio e alla fine.
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

# Env DB per manage.py (gunicorn systemd li ha in .env.systemd).
set -a; . "$BACKEND_DIR/.env.systemd" 2>/dev/null || true; set +a

echo ""; echo "========================================="
echo " Smoke E2E — GUIDA inversione PREVENTIVI (step 9011)"
echo " Base: $BASE_URL"
echo "========================================="

# --- GUC operatore condiviso da tutti gli heredoc Python (RLS) ---
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

# --- Cleanup helper (inizio + fine) ---
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

# --- 1. Seed: pratica 9004 + preventivo EMESSO + flusso 9011 aperto + link ROOT ---
echo ""; echo "-- 1. Setup scenario (direct-insert su 9011) --"
SETUP_JSON="$("${MANAGE[@]}" 2>/dev/null <<PY | grep '^SETUP ' | sed 's/^SETUP //'
$GUC_PY
import json, uuid
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
    print("SETUP " + json.dumps({"pratica_id": prat_id, "preventivo_id": prev_id, "flusso_id": flusso_id}))
PY
)"
[[ -z "$SETUP_JSON" ]] && { log_fail "setup fallito (nessun SETUP output)"; exit 1; }
PRAT_ID="$(echo "$SETUP_JSON" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['pratica_id'])")"
PREV_ID="$(echo "$SETUP_JSON" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['preventivo_id'])")"
FLUSSO_ID="$(echo "$SETUP_JSON" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['flusso_id'])")"
log_ok "scenario creato (pratica=$PRAT_ID preventivo=$PREV_ID flusso9011=$FLUSSO_ID)"

# --- 2. Accetta in-pratica via HTTP (endpoint dell'inversione) ---
echo ""; echo "-- 2. Accetta in-pratica (da-pratica) --"
HTTP="$(curl -s -o /tmp/guida_accept.json -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"nuovo_stato":"ACCETTATO","fatturazione_immediata":true}' \
    "${BASE_URL}/api/v1/vendite/preventivi/da-pratica/${PRAT_ID}/stato/")"
if [[ "$HTTP" == "200" ]]; then log_ok "POST da-pratica ACCETTATO (HTTP 200)"
else log_fail "POST da-pratica — atteso 200, ricevuto $HTTP: $(head -c 300 /tmp/guida_accept.json)"; fi

# --- 3. Asserzioni E2E: preventivo ACCETTATO + milestone auto-avanzato ---
echo ""; echo "-- 3. Verifica proiezione --"
RES="$("${MANAGE[@]}" 2>/dev/null <<PY | grep '^RES '
$GUC_PY
import json
with connection.cursor() as c:
    _guc(c)
    c.execute("SELECT sd.codice_interno FROM vendite.preventivi pr JOIN config.stati_doc_preventivi sd ON sd.id=pr.stato_doc_preventivo_id WHERE pr.id=$PREV_ID")
    sp=c.fetchone(); c.execute("SELECT sf.codice_interno, f.esito FROM pratiche.flussi f JOIN config.stati_flussi_pratiche sf ON sf.id=f.stato_id WHERE f.id=$FLUSSO_ID")
    sf=c.fetchone()
    print("RES " + json.dumps({"preventivo": sp and sp[0], "flusso": sf and sf[0], "esito": sf and sf[1]}))
PY
)"
RES="${RES#RES }"
STATO_PREV="$(echo "$RES" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['preventivo'])" 2>/dev/null)"
STATO_FL="$(echo "$RES" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['flusso'])" 2>/dev/null)"
ESITO_FL="$(echo "$RES" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['esito'])" 2>/dev/null)"
log_info "preventivo=$STATO_PREV · flusso9011=$STATO_FL/$ESITO_FL"
[[ "$STATO_PREV" == "ACCETTATO" ]] && log_ok "preventivo ACCETTATO (documento sovrano)" || log_fail "preventivo atteso ACCETTATO, e' $STATO_PREV"
[[ "$STATO_FL" == "COMPLETATO" && "$ESITO_FL" == "POSITIVO" ]] \
    && log_ok "milestone 9011 auto-avanzato a COMPLETATO/POSITIVO (proiezione)" \
    || log_fail "milestone 9011 atteso COMPLETATO/POSITIVO, e' $STATO_FL/$ESITO_FL"

# --- Riepilogo ---
echo ""; echo "========================================="
echo -e " Risultato: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "========================================="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
