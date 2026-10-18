# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Il cliente di prova degli smoke, in un posto solo: un billing account
#        visibile all'operatore con utility e istanza, preso dal lookup BA.
#        Prima lo stesso blocco (curl + python + awk) era copiato in ogni smoke
#        che crea un documento, con il prefisso «BA» scritto a mano.
# Uso (dopo `source .../_smoke_auth.sh` e `smoke_login`):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_cliente.sh"
#   smoke_cliente_dal_lookup     # -> BA_ID, UTILITY_ID, ISTANZA_ID, BA_LOOKUP_RAW
#   if [[ -z "$BA_ID" ]]; then ... ripiego dello smoke ... fi
# Vuole: BASE_URL, TOKEN.
# Note: ⭐ Il lookup vuole `q` di almeno 2 caratteri (E_ANAG_VALIDAZIONE): si
#       cerca per il PREFISSO dei codici cliente, letto dalla configurazione
#       (`GET /api/v1/core/lookup/sistema-codici/`, `config.sistema_codici`,
#       riga anagrafiche.billing_account.codice), non scritto qui.
#       Nessun cliente adatto (o prefisso non configurato) = variabili VUOTE e
#       ritorno 0: il ripiego (un documento esistente) e il messaggio d'errore
#       sono dello smoke, che sa di quale documento ha bisogno. Il motivo lo
#       dice qui, su stderr. ⛔ Imposta variabili dello smoke: si chiama
#       diretto, mai dentro `$(...)`.
#       ⭐ L'EMITTENTE e il cliente vanno d'accordo per costruzione, ed e' per
#       questo che lo smoke non deve passarlo: il lookup restituisce solo i
#       clienti dell'emittente ATTIVO dell'operatore
#       (`script.fn_get_emittenti_scope_sr_ids`), e un documento senza emittente
#       nel payload prende l'emittente di lavoro, cioe' lo stesso attivo
#       (`script.trgfn_default_emittente_fiscale`). Un id scritto a mano (era
#       `32`) rompe l'accordo: `E_DOC_EMITTENTE_BA_INCOERENTE`.
#   smoke_emittente_attivo       # -> EMITTENTE_ATTIVO_ID, EMITTENTE_ATTIVO_SR_ID
#       Per chi l'emittente lo deve PASSARE (la pratica lo vuole nel payload, le
#       liste delle pratiche come filtro, il listino come soggetto_ruolo): quello
#       attivo dell'operatore, da `GET /api/v1/core/me/` (`emittente_attivo`).
#       ⚠️ Non il campo `emittente` della stessa risposta: e' un'altra cosa, e da
#       li' veniva il `32`. ⛔ Nemmeno «il primo» della lista
#       `/anagrafiche/emittenti-fiscali/`: al super admin la lista li mostra
#       TUTTI, e il guard di scrittura accetta solo quello attivo
#       (`script.fn_check_user_emittente_scope`, regola 2, vale anche per il
#       super admin). Era verde finche' il primo coincideva con l'attivo
#       (2026-10-18, collaudo `dev.smoke`: E_SCOPE_EMITTENTE ed
#       E_DOC_EMITTENTE_BA_INCOERENTE).
#       EMITTENTE_ID, se impostato, vince (override esplicito): il suo
#       soggetto_ruolo si legge dalla lista. Vuoto = nessun emittente attivo:
#       lo smoke si ferma col suo messaggio.
#   smoke_cliente_del_giro [nome] [categoria_id] [utility_preferita]
#                                # -> GIRO_BA_ID, GIRO_ISTANZA_ID, GIRO_UTILITY_ID,
#                                #    GIRO_LAST_STATUS, GIRO_LAST_BODY
#       Un CLIENTE NUOVO per il giro: soggetto nuovo (BB `_smoke_soggetto.sh`,
#       `nome` va nel codice fiscale), utility manuale, `POST /anagrafiche/
#       clienti/` con un indirizzo DOMFISC (i tipi obbligatori mancanti li
#       clona il service). Nasce sull'emittente attivo, come ogni documento
#       senza emittente nel payload.
#       ⭐ Serve a chi non deve toccare il cliente condiviso: un contratto
#       attivo sul cliente del lookup governa i prezzi degli altri smoke, e
#       una mappa categoria -> listino sulla sua categoria li cambierebbe.
#       `categoria_id` vuota = la prima del lookup; `utility_preferita` vince
#       se e' tra le manuali. Nasce il 2026-10-18 (regola del 2, ok Tid): prima
#       stava in `smoke-test-contratti-addebito-standard.sh`, il secondo
#       consumatore e' `smoke-test-preventivi-componenti.sh` (una categoria sua
#       mappata sul suo listino).
#       Fallimento = GIRO_BA_ID vuoto e ritorno 0, col motivo su stderr; la
#       risposta della POST resta in GIRO_LAST_STATUS / GIRO_LAST_BODY per lo
#       smoke che la vuole provare.
# ------------------------------------------------------------

smoke_cliente_dal_lookup() {
    BA_ID=""; UTILITY_ID=""; ISTANZA_ID=""; BA_LOOKUP_RAW=""

    local prefisso
    prefisso=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/core/lookup/sistema-codici/?schema=anagrafiche&tabella=billing_account&colonna=codice" \
        2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data') or {}
    print(d.get('prefisso') or '' if d.get('auto') else '')
except Exception:
    print('')
" 2>/dev/null)
    if [[ ${#prefisso} -lt 2 ]]; then
        echo "  [_smoke_cliente] prefisso dei codici cliente non configurato o sotto i 2 caratteri ('${prefisso}'): niente lookup" >&2
        return 0
    fi

    BA_LOOKUP_RAW=$(curl -s -G -H "Authorization: Bearer $TOKEN" \
        --data-urlencode "q=${prefisso}" --data-urlencode "limit=50" \
        "${BASE_URL}/api/v1/anagrafiche/billing-account/lookup/" 2>/dev/null)
    local terna
    terna=$(echo "$BA_LOOKUP_RAW" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data', {})
    rows = d.get('results', d) if isinstance(d, dict) else d
    for r in (rows or []):
        if r.get('utility_id') and r.get('istanza_utility_id'):
            print(r['id'], r['utility_id'], r['istanza_utility_id']); break
except Exception:
    pass
" 2>/dev/null)
    if [[ -z "$terna" ]]; then
        echo "  [_smoke_cliente] lookup per '${prefisso}': nessun cliente con utility e istanza visibile all'operatore" >&2
        return 0
    fi
    read -r BA_ID UTILITY_ID ISTANZA_ID <<< "$terna"
    return 0
}

smoke_emittente_attivo() {
    EMITTENTE_ATTIVO_ID=""; EMITTENTE_ATTIVO_SR_ID=""
    local coppia
    if [[ -n "${EMITTENTE_ID:-}" ]]; then
        coppia=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${BASE_URL}/api/v1/anagrafiche/emittenti-fiscali/?page_size=200" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = (json.load(sys.stdin).get('data') or {}).get('results') or []
    r = next((x for x in rows if str(x.get('id')) == '${EMITTENTE_ID}'), None)
    print(r['id'], r.get('soggetto_ruolo_id') or '') if r else print('')
except Exception:
    print('')
" 2>/dev/null)
    else
        coppia=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${BASE_URL}/api/v1/core/me/" 2>/dev/null | python3 -c "
import sys, json
try:
    a = (json.load(sys.stdin).get('data') or {}).get('emittente_attivo') or {}
    print(a.get('emittente_fiscale_id') or '', a.get('soggetto_ruolo_id') or '')
except Exception:
    print('')
" 2>/dev/null)
    fi
    read -r EMITTENTE_ATTIVO_ID EMITTENTE_ATTIVO_SR_ID <<< "$coppia"
    if [[ -z "$EMITTENTE_ATTIVO_ID" ]]; then
        if [[ -n "${EMITTENTE_ID:-}" ]]; then
            echo "  [_smoke_cliente] EMITTENTE_ID=${EMITTENTE_ID} non e' tra gli emittenti visibili all'operatore" >&2
        else
            echo "  [_smoke_cliente] l'operatore non ha un emittente attivo (GET /core/me/, emittente_attivo)" >&2
        fi
    fi
    return 0
}

smoke_cliente_del_giro() {
    local nome="${1:-Cliente}" categoria="${2:-}" preferita="${3:-}" tmp
    GIRO_BA_ID=""; GIRO_ISTANZA_ID=""; GIRO_UTILITY_ID=""; GIRO_LAST_STATUS=""; GIRO_LAST_BODY=""
    if ! declare -F smoke_soggetto_privato >/dev/null; then
        source "$(dirname "${BASH_SOURCE[0]}")/_smoke_soggetto.sh"
    fi

    smoke_soggetto_privato "$nome"
    if [[ -z "$SOGG_ID" ]]; then
        echo "  [_smoke_cliente] il soggetto del giro non e' nato (motivo sopra)" >&2
        return 0
    fi
    GIRO_UTILITY_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/anagrafiche/utilities/manual-lookup/" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data')
    rows = d.get('results', d) if isinstance(d, dict) else d
    ids = [str(r.get('id') or r.get('utility_id')) for r in (rows or [])]
    print(sys.argv[1] if sys.argv[1] in ids else (ids[0] if ids else ''))
except Exception:
    print('')
" "$preferita" 2>/dev/null)
    if [[ -z "$categoria" ]]; then
        categoria=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${BASE_URL}/api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti&limit=1" 2>/dev/null \
            | python3 -c "
import sys, json
try:
    print(((json.load(sys.stdin).get('data') or {}).get('results') or [{}])[0].get('id') or '')
except Exception:
    print('')
" 2>/dev/null)
    fi

    tmp=$(mktemp)
    curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"soggetto_id\": \"${SOGG_ID}\", \"utility_id\": ${GIRO_UTILITY_ID:-null}, \"ba_categoria_cliente_id\": ${categoria:-null}, \"indirizzi\": [{\"tipo_indirizzo_codice\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}]}" \
        "${BASE_URL}/api/v1/anagrafiche/clienti/" > "$tmp" 2>/dev/null
    GIRO_LAST_STATUS=$(tail -1 "$tmp")
    GIRO_LAST_BODY=$(sed '$d' "$tmp")
    rm -f "$tmp"
    read -r GIRO_BA_ID GIRO_ISTANZA_ID <<< "$(echo "$GIRO_LAST_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin).get('data') or {}
    print(d.get('billing_account_id') or '', d.get('istanza_utility_id') or '')
except Exception:
    print('')
" 2>/dev/null)"
    if [[ -z "$GIRO_BA_ID" ]]; then
        echo "  [_smoke_cliente] POST cliente del giro: HTTP ${GIRO_LAST_STATUS} — $(echo "$GIRO_LAST_BODY" | head -c 300)" >&2
    fi
    return 0
}

