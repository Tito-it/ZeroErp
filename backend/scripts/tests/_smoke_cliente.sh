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
#   smoke_emittente_attivo       # -> EMITTENTE_ATTIVO_ID
#       Per chi l'emittente lo deve PASSARE (la pratica lo vuole nel payload, le
#       liste delle pratiche come filtro): quello attivo dell'operatore, da
#       `GET /api/v1/core/me/` (`emittente_attivo`). ⚠️ Non il campo `emittente`
#       della stessa risposta: e' un'altra cosa, e da li' veniva il `32`.
#       EMITTENTE_ID, se impostato, vince (override esplicito). Vuoto = nessun
#       emittente attivo: lo smoke si ferma col suo messaggio.
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
    EMITTENTE_ATTIVO_ID="${EMITTENTE_ID:-}"
    [[ -n "$EMITTENTE_ATTIVO_ID" ]] && return 0
    EMITTENTE_ATTIVO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${BASE_URL}/api/v1/core/me/" 2>/dev/null | python3 -c "
import sys, json
try:
    a = (json.load(sys.stdin).get('data') or {}).get('emittente_attivo') or {}
    print(a.get('emittente_fiscale_id') or '')
except Exception:
    print('')
" 2>/dev/null)
    if [[ -z "$EMITTENTE_ATTIVO_ID" ]]; then
        echo "  [_smoke_cliente] l'operatore non ha un emittente attivo (GET /core/me/, emittente_attivo)" >&2
    fi
    return 0
}
