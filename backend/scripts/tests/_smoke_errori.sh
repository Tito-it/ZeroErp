# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Il RIFIUTO atteso negli smoke bash, in un posto solo: lo status HTTP
#        E il codice d'errore dell'envelope (`error.code`), tutti e due. Uno
#        status giusto con un codice sbagliato e' un'altra regola che rifiuta
#        (un 400 del backend al posto del 400 del verbo del DB), e passa per
#        verde se si guarda solo lo status.
#        Regola del 2 (2026-10-29, ok Tid): era scritto in tre funzioni
#        (`check_codice` di smoke-test-core, `check_error_code` di
#        -ui-personalizzazioni-liste e di -contratti-overlap-annullato-20260521,
#        con firme e ritorni diversi) e inline (`check … ".error.code"` + `if`
#        sul codice) in -listini-v5, -catalogo-phase3, -catalogo-crud, -core.
# Uso (dopo il `do_curl` dello smoke):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_errori.sh"
#   smoke_check_codice "Elimina la ATTIVA" 409 E_LISTINO_VERSIONE_NON_ELIMINABILE
#   smoke_check_codice "..." 404 E_X || true     # per proseguire comunque
# Ritorna: 0 se status e codice sono quelli attesi (una riga log_ok), 1
#        altrimenti (una riga log_fail con status, codice e messaggio ricevuti).
#        ⚠️ Con `set -e` un 1 ferma lo smoke, come `check` sullo status: chi
#        vuole proseguire lo dice con `|| true`.
# Vuole: LAST_STATUS, LAST_BODY (il `do_curl` degli smoke); `log_ok`,
#        `log_fail` dello smoke (contano PASS e FAIL).
# Note: ⭐ Codice e messaggio li legge da se', senza il `json_get` dello smoke:
#       gli smoke ne hanno varianti diverse (con e senza indici di lista).
# ------------------------------------------------------------

# Scopo: un campo di `error` dell'envelope in LAST_BODY; vuoto se manca.
_smoke_errore_campo() {
    echo "$LAST_BODY" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('error', {}).get('$1') or '')
except Exception:
    print('')
" 2>/dev/null
}

smoke_check_codice() {
    local label="$1" atteso="$2" codice="$3" ricevuto
    ricevuto=$(_smoke_errore_campo code)
    if [[ "$LAST_STATUS" == "$atteso" && "$ricevuto" == "$codice" ]]; then
        log_ok "$label (HTTP $LAST_STATUS, $codice)"
        return 0
    fi
    log_fail "$label — atteso HTTP $atteso $codice, ricevuto HTTP $LAST_STATUS ${ricevuto:-<nessun codice>}"
    echo "       message=$(_smoke_errore_campo message)"
    return 1
}
