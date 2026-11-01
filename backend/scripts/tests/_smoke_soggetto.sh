# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Un SOGGETTO NUOVO per gli smoke, in un posto solo: un privato con
#        codice fiscale generato, contatto e indirizzi RES + DOMFISC, creato
#        dall'API come lo crea l'operatore.
#        ⭐ Nasce il 2026-10-15 (regola del 2, ok Tid). Prima la creazione stava
#        solo in `smoke-test-soggetti.sh`; il secondo consumatore e'
#        `smoke-test-contratti-addebito-standard.sh`, che vuole un cliente suo
#        per ogni giro: dal 2026-10-14 un soggetto ha UN cliente manuale per
#        utility e azienda (`E_CLIENTE_STESSA_CHIAVE`, C-1/C-2 di
#        brief-db-cliente-manuale-uno-per-soggetto-e-utility), quindi un
#        cliente nuovo vuole un soggetto nuovo.
# Uso (dopo `source .../_smoke_auth.sh` e `smoke_login`):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_soggetto.sh"
#   smoke_tipo_privato                 # -> TIPO_PRIVATO_ID
#   smoke_indirizzo_dettaglio          # -> IND_DET_ID
#   smoke_soggetto_privato "Contratto" # -> SOGG_ID (+ le variabili sotto)
#   if [[ -z "$SOGG_ID" ]]; then ... messaggio dello smoke ... fi
# Vuole: BASE_URL, TOKEN.
# Imposta (oltre a SOGG_ID): SOGG_CF, SMOKE_TS, SMOKE_BDATE, COMUNE_NASCITA_ID,
#        TIPO_PRIVATO_ID, TIPO_CONTATTO_ID, TIPO_CONTATTO_2_ID, IND_DET_ID, e
#        SOGG_LAST_STATUS / SOGG_LAST_BODY della POST (per il `check` dello
#        smoke che la vuole provare).
# Note: ⭐ Il NOME e' un parametro di proposito: il codice fiscale si genera da
#       nome, cognome e data di nascita (derivata dal timestamp), e due smoke
#       che girano nello stesso secondo con lo stesso nome avrebbero lo stesso
#       CF — il secondo prenderebbe un 409 che non ha niente a che fare con il
#       suo test.
#       ⛔ Il tipo «persona fisica privato» si legge dal lookup per
#       `codice_interno` (`PR`), non come id scritto a mano (era `1`).
#       Fallimento = SOGG_ID VUOTO e ritorno 0, col motivo su stderr: il
#       messaggio e la scelta (fermarsi o saltare) sono dello smoke.
#       ⛔ Imposta variabili dello smoke: si chiama diretto, mai in `$(...)`.
# ------------------------------------------------------------

# Scopo: GET autenticata, corpo su stdout.
_smoke_sogg_get() {
    curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}$1" 2>/dev/null
}

# Scopo: legge un campo da un JSON (percorso a punti, indici numerici).
_smoke_sogg_json() {
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in sys.argv[1].split('.'):
        d = d[int(k)] if k.isdigit() else d[k]
    print('' if d is None else d)
except Exception:
    print('')
" "$1" 2>/dev/null
}

# Scopo: un indirizzo_dettaglio_id da dare al soggetto: uno esistente, o uno
#        nuovo su una via di Milano (comune con stradario sicuro).
smoke_indirizzo_dettaglio() {
    [[ -n "${IND_DET_ID:-}" ]] && return 0
    IND_DET_ID=$(_smoke_sogg_get "/api/v1/anagrafiche/indirizzi/?limit=1" \
        | _smoke_sogg_json "data.results.0.indirizzo_dettaglio_id")
    [[ -n "$IND_DET_ID" ]] && return 0

    local comune strad
    comune=$(_smoke_sogg_get "/api/v1/core/lookup/comuni/?search=MILANO&limit=1" \
        | _smoke_sogg_json "data.results.0.id")
    [[ -n "$comune" ]] && strad=$(_smoke_sogg_get \
        "/api/v1/core/search/stradario/?comune_id=${comune}&search=via&limit=1" \
        | _smoke_sogg_json "data.results.0.stradario_id")
    if [[ -n "${strad:-}" ]]; then
        IND_DET_ID=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"stradario_id\":${strad},\"civico\":$((RANDOM % 900 + 100))}" \
            "${BASE_URL}/api/v1/anagrafiche/indirizzi/" 2>/dev/null \
            | _smoke_sogg_json "data.indirizzo_dettaglio_id")
    fi
    [[ -z "$IND_DET_ID" ]] && echo "  [_smoke_soggetto] nessun indirizzo esistente e nessuno creabile (comune/stradario)" >&2
    return 0
}

# Scopo: l'id del tipo «persona fisica privato», per codice_interno (PR).
smoke_tipo_privato() {
    [[ -n "${TIPO_PRIVATO_ID:-}" ]] && return 0
    TIPO_PRIVATO_ID=$(_smoke_sogg_get "/api/v1/core/lookup/tipi-soggetto-dettaglio/" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)['data']['results']
    print(next((t['id'] for t in r if t['codice_interno'] == 'PR'), ''))
except Exception:
    print('')" 2>/dev/null)
    [[ -z "$TIPO_PRIVATO_ID" ]] && echo "  [_smoke_soggetto] tipo soggetto PR non trovato nel lookup" >&2
    return 0
}

# Scopo: crea un privato nuovo. $1 = nome (default «Soggetto»), vedi Note.
smoke_soggetto_privato() {
    local nome="${1:-Soggetto}"
    SOGG_ID=""; SOGG_CF=""; SOGG_LAST_STATUS=""; SOGG_LAST_BODY=""

    smoke_indirizzo_dettaglio
    if [[ -z "$IND_DET_ID" ]]; then
        echo "  [_smoke_soggetto] senza indirizzo il soggetto non nasce (RES + DOMFISC obbligatori)" >&2
        return 0
    fi

    smoke_tipo_privato
    local contatti
    contatti=$(_smoke_sogg_get "/api/v1/core/lookup/codici/?rel=config.tipi_contatti&limit=2")
    # Il contatto del soggetto lo pretende (`E_CONTATTO_INCOMPLETO`): il primo
    # della lista, come il drawer. Il secondo serve a chi aggiunge un contatto:
    # (soggetto, tipo) e' unico.
    TIPO_CONTATTO_ID=$(echo "$contatti" | _smoke_sogg_json "data.results.0.id")
    TIPO_CONTATTO_2_ID=$(echo "$contatti" | _smoke_sogg_json "data.results.1.id")
    COMUNE_NASCITA_ID=$(_smoke_sogg_get "/api/v1/core/lookup/comuni/?search=CORRIDONIA&limit=1" \
        | _smoke_sogg_json "data.results.0.id")
    if [[ -z "$TIPO_PRIVATO_ID" || -z "$TIPO_CONTATTO_ID" || -z "$COMUNE_NASCITA_ID" ]]; then
        echo "  [_smoke_soggetto] manca un ingrediente: tipo PR='${TIPO_PRIVATO_ID}' tipo contatto='${TIPO_CONTATTO_ID}' comune nascita='${COMUNE_NASCITA_ID}'" >&2
        return 0
    fi

    # Data di nascita dal timestamp (anno 1950-2049, giorno 01-28): un CF
    # diverso a ogni giro.
    SMOKE_TS=$(date +%s)
    SMOKE_BDATE="$((1950 + SMOKE_TS % 100))-$(printf '%02d' $((SMOKE_TS / 100 % 12 + 1)))-$(printf '%02d' $((SMOKE_TS / 1200 % 28 + 1)))"
    SOGG_CF=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
        -d "{\"cognome\":\"SmokeTest\",\"nome\":\"${nome}\",\"data_nascita\":\"${SMOKE_BDATE}\",\"sesso\":\"M\",\"comune_nascita_id\":${COMUNE_NASCITA_ID}}" \
        "${BASE_URL}/api/v1/anagrafiche/soggetti/genera-cf/" 2>/dev/null \
        | _smoke_sogg_json "data.codice_fiscale")
    if [[ -z "$SOGG_CF" ]]; then
        echo "  [_smoke_soggetto] generazione del codice fiscale fallita" >&2
        return 0
    fi

    local tmp
    tmp=$(mktemp)
    curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"tipo_soggetto_dettaglio_id\": ${TIPO_PRIVATO_ID},
            \"cognome\": \"SmokeTest\",
            \"nome\": \"${nome}${SMOKE_TS}\",
            \"codice_fiscale\": \"${SOGG_CF}\",
            \"sesso\": \"M\",
            \"contatto\": {\"tipo_contatto_id\": ${TIPO_CONTATTO_ID},
                \"nominativo\": \"SmokeTest ${nome}\",
                \"email\": \"smoke${SMOKE_TS}${nome,,}@test.it\",
                \"telefono\": \"0123456789\"
            },
            \"indirizzi\": [
                {\"tipo_indirizzo_codice_interno\": \"RES\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}},
                {\"tipo_indirizzo_codice_interno\": \"DOMFISC\", \"indirizzo_dettaglio_id\": ${IND_DET_ID}}
            ],
            \"auto_clone\": true
        }" \
        "${BASE_URL}/api/v1/anagrafiche/soggetti/" > "$tmp" 2>/dev/null
    SOGG_LAST_STATUS=$(tail -1 "$tmp")
    SOGG_LAST_BODY=$(sed '$d' "$tmp")
    rm -f "$tmp"
    if [[ "$SOGG_LAST_STATUS" == "200" ]]; then
        SOGG_ID=$(echo "$SOGG_LAST_BODY" | _smoke_sogg_json "data.id")
    else
        echo "  [_smoke_soggetto] POST soggetto: HTTP ${SOGG_LAST_STATUS} — $(echo "$SOGG_LAST_BODY" | head -c 300)" >&2
    fi
    return 0
}
