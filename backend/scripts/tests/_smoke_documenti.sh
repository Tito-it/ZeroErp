# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: L'emissione di un documento di vendita negli smoke bash, in un posto
#        solo. Contratto (DRAFT -> ATTIVO), preventivo (BOZZA -> EMESSO) e bolla
#        (-> EMESSO) passano da `POST /api/v1/vendite/<documento>/<id>/emetti/`,
#        multipart: stato, documento e allegati in una transazione. Il cambio di
#        stato diretto verso quegli stati risponde 400 «Usare l'endpoint
#        /emetti/» (o, per una bolla che muove merce, E_DDT_STATO_SOLO_DA_VERBO).
#        Prima la stessa chiamata curl era copiata in ogni smoke che emetteva.
# Uso (dopo `source .../_smoke_auth.sh` e `smoke_login`):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_documenti.sh"
#   smoke_emetti contratti "$CONTRATTO_ID"   # o: preventivi, ddt
#   # -> LAST_STATUS, LAST_BODY (come il do_curl degli smoke)
#   # -> SMOKE_EMETTI_SENZA_MODELLO=1 se manca il modello di documento
#   smoke_chiudi_contratti "$BA_ID" COMMODITY   # i contratti vivi che lo smoke ha lasciato
#       Chiude, con le transizioni AMMESSE, i contratti ancora vivi del cliente
#       in quell'ambito creati dall'utente degli smoke ($USERNAME): DRAFT ->
#       ANNULLATO, ATTIVO -> CESSATO con valido_al = oggi (o, se inizia nel
#       futuro, il giorno in cui inizia: cessazione programmata). Il prezzo vede solo i
#       contratti ATTIVO (vendite.fn_get_contratto_attivo), quindi un contratto
#       cessato oggi smette subito di governare i prezzi degli altri smoke sullo
#       stesso cliente. Si chiama all'inizio (residui) e alla fine (i propri).
#       Fino al 2026-10-12 uno smoke lasciava il suo contratto ATTIVO (modalita'
#       C, senza listino) e un altro smoke, sullo stesso cliente, trovava
#       E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C; l'altro tentava un DELETE fisico
#       che falliva in silenzio.
#   smoke_articolo_merce                           # -> ARTICOLO_ID
#       Un articolo che puo' stare in un ORDINE o in una BOLLA: attivo, non
#       composito, con natura di vendita a destinazione ORDINE_VENDITA (la regola di
#       script.fn_check_articolo_riga, E_RIGA_NATURA_NON_AMMESSA: un servizio
#       non si spedisce). Fino al 2026-10-13 gli smoke prendevano «il primo
#       articolo del catalogo», e il giorno che era un servizio l'ordine veniva
#       rifiutato. Vuoto = nessuna merce nel catalogo (lo smoke si ferma).
# Vuole: BASE_URL, TOKEN.
# Note: ⚠️ Senza un modello di documento per quel documento e quell'emittente,
#       /emetti/ risponde 404 E_DOCUMENTI_NOT_FOUND: e' CONFIGURAZIONE
#       dell'ambiente, non un difetto. Il BB lo segnala
#       (SMOKE_EMETTI_SENZA_MODELLO=1) e lo smoke decide: dichiararsi non
#       conclusivo o saltare i passi a valle con un SKIP, mai contarlo verde.
#       ⛔ Imposta variabili dello smoke: si chiama diretto, mai in `$(...)`.
# ------------------------------------------------------------

smoke_emetti() {
    local documento="$1" id="$2" out
    out=$(mktemp)
    curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer ${TOKEN:-none}" \
        -F "x=" "${BASE_URL}/api/v1/vendite/${documento}/${id}/emetti/" > "$out" 2>/dev/null
    LAST_STATUS=$(tail -1 "$out"); LAST_BODY=$(sed '$d' "$out")
    rm -f "$out"
    SMOKE_EMETTI_SENZA_MODELLO=0
    if [[ "$LAST_STATUS" == "404" && "$LAST_BODY" == *E_DOCUMENTI_NOT_FOUND* ]]; then
        SMOKE_EMETTI_SENZA_MODELLO=1
        echo "  [_smoke_documenti] nessun modello di documento per ${documento} ${id} (E_DOCUMENTI_NOT_FOUND): configurazione dell'emittente" >&2
    fi
    return 0
}

smoke_chiudi_contratti() {
    local ba="$1" ambito="$2" righe oggi id stato n=0 ko=0 out
    [[ -z "$ba" || -z "$ambito" ]] && return 0
    oggi=$(date +%F)
    righe=$(curl -s -H "Authorization: Bearer ${TOKEN:-none}" \
        "${BASE_URL}/api/v1/vendite/contratti/?billing_account_id=${ba}&limit=500" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    for r in rows:
        if (r.get('ambito') != sys.argv[1] or r.get('user_insert') != sys.argv[2]
                or r.get('stato_codice_interno') not in ('DRAFT', 'ATTIVO')):
            continue
        dal, al = r.get('valido_dal') or '', r.get('valido_al') or ''
        # un ATTIVO gia' chiuso il giorno in cui inizia non va ritoccato
        if r['stato_codice_interno'] == 'ATTIVO' and al and al == dal:
            continue
        print(r['id'], r['stato_codice_interno'], dal)
except Exception:
    pass
" "$ambito" "${USERNAME:-smoke}" 2>/dev/null)
    out=$(mktemp)
    while read -r id stato dal; do
        [[ -z "$id" ]] && continue
        if [[ "$stato" == "DRAFT" ]]; then
            # Una bozza senza legami si annulla senza dichiarazione: la
            # dichiarazione, quando serve, e' un intero POSITIVO.
            body='{"codice_interno": "ANNULLATO"}'
        elif [[ "$dal" > "$oggi" ]]; then
            # Inizia nel futuro: la fine non puo' precedere l'inizio
            # (E_DATA_AL_MINORE_DAL). Si chiude il giorno in cui inizia
            # (cessazione programmata): oggi non governa nessun prezzo.
            body="{\"codice_interno\": \"CESSATO\", \"valido_al\": \"${dal}\"}"
        else
            body="{\"codice_interno\": \"CESSATO\", \"valido_al\": \"${oggi}\"}"
        fi
        curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer ${TOKEN:-none}" \
            -H "Content-Type: application/json" -d "$body" \
            "${BASE_URL}/api/v1/vendite/contratti/${id}/cambia-stato/" > "$out" 2>/dev/null
        if [[ "$(tail -1 "$out")" == "200" ]]; then
            n=$((n + 1))
        else
            ko=$((ko + 1))
            echo "  [_smoke_documenti] contratto ${id} (${stato}) non chiuso: $(sed '$d' "$out" | head -c 200)" >&2
        fi
    done <<< "$righe"
    rm -f "$out"
    echo "  [_smoke_documenti] contratti ${ambito} del cliente ${ba} chiusi: ${n}$( ((ko > 0)) && echo ", NON chiusi: ${ko}")" >&2
    return 0
}

smoke_articolo_merce() {
    local offset righe
    ARTICOLO_ID=""
    # `limit`/`offset`: la lista ignora `page`/`page_size`.
    for offset in $(seq 0 100 3000); do
        righe=$(curl -s -H "Authorization: Bearer ${TOKEN:-none}" \
            "${BASE_URL}/api/v1/catalogo/articoli/?attivo=true&limit=100&offset=${offset}" 2>/dev/null)
        ARTICOLO_ID=$(echo "$righe" | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    r = next((x for x in rows if x.get('natura_vendita_destinazione_tipo') == 'ORDINE_VENDITA'
              and not x.get('is_composito') and x.get('attivo') is not False), None)
    print(r['id'] if r else ('' if len(rows) == 100 else 'FINE'))
except Exception:
    print('FINE')
" 2>/dev/null)
        [[ "$ARTICOLO_ID" == "FINE" ]] && { ARTICOLO_ID=""; break; }
        [[ -n "$ARTICOLO_ID" ]] && break
    done
    [[ -z "$ARTICOLO_ID" ]] && echo "  [_smoke_documenti] nessun articolo merce (natura a destinazione ORDINE_VENDITA) nel catalogo" >&2
    return 0
}
