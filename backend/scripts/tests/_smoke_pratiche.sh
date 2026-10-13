# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Il template di flusso di una pratica, per gli smoke bash, in un posto
#        solo. Un flusso nasce SEMPRE da un template del percorso della pratica
#        (`template_flusso_id` obbligatorio, E_FLUSSO_VALIDATION): lo si legge da
#        `GET /api/v1/pratiche/<id>/percorso/`. Prima lo faceva solo uno smoke
#        (funzione locale, poi ritirato col suo flusso), e smoke-test-pratiche e
#        -sospensioni creavano il flusso senza.
# Uso (dopo `source .../_smoke_auth.sh` e `smoke_login`):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_pratiche.sh"
#   smoke_template_percorso "$PRATICA_ID" PREVENTIVAZIONE   # -> TEMPLATE_FLUSSO_ID
#   smoke_template_percorso "$PRATICA_ID"                   # il primo del percorso
#   smoke_tipo_prestazione PREVENTIVI                       # -> TIPO_PRESTAZIONE_ID
#       Il tipo di prestazione PER CODICE (lookup generico), mai per id: gli id
#       cablati negli smoke (26, 9002) erano un dato di dbdev senza percorso e un
#       tipo obsoleto dal 2026-06-30. TIPO_PRESTAZIONE_ID gia' impostato vince
#       (override esplicito).
# Vuole: BASE_URL, TOKEN.
# Note: vuoto = percorso senza quel template (o senza template): il motivo su
#       stderr, la decisione allo smoke. ⛔ Si chiama diretto, mai in `$(...)`.
# ------------------------------------------------------------

smoke_template_percorso() {
    local pratica_id="$1" codice="${2:-}"
    TEMPLATE_FLUSSO_ID=$(curl -s -H "Authorization: Bearer ${TOKEN:-none}" \
        "${BASE_URL}/api/v1/pratiche/${pratica_id}/percorso/" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results', [])
    codice = sys.argv[1]
    r = next((x for x in rows if not codice or x.get('template_flusso_codice') == codice), None)
    print(r['template_flusso_id'] if r else '')
except Exception:
    print('')
" "$codice" 2>/dev/null)
    if [[ -z "$TEMPLATE_FLUSSO_ID" ]]; then
        echo "  [_smoke_pratiche] percorso della pratica ${pratica_id}: nessun template${codice:+ '$codice'}" >&2
    fi
    return 0
}

smoke_tipo_prestazione() {
    local codice="$1"
    [[ -n "${TIPO_PRESTAZIONE_ID:-}" ]] && return 0
    TIPO_PRESTAZIONE_ID=$(curl -s -H "Authorization: Bearer ${TOKEN:-none}" \
        "${BASE_URL}/api/v1/core/lookup/codici/?rel=pratiche.tipi_prestazione&limit=100" 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin).get('data', {}).get('results') or []
    r = next((x for x in rows if x.get('codice_stabile') == sys.argv[1]), None)
    print(r['id'] if r else '')
except Exception:
    print('')
" "$codice" 2>/dev/null)
    if [[ -z "$TIPO_PRESTAZIONE_ID" ]]; then
        echo "  [_smoke_pratiche] tipo di prestazione '${codice}' non trovato nel lookup" >&2
    fi
    return 0
}
