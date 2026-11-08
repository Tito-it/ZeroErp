# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: La QUERY DIRETTA al database degli smoke bash, in un posto solo:
#        `manage-env.sh dbshell` (psql col ruolo dell'applicazione), output
#        senza intestazioni e senza righe vuote.
#        Regola del 2 (2026-11-08, ok Tid): era `db_query` in tre smoke
#        (-jwt-audit-guc, -rls-emittente-operatore, -audit-logging), e le tre
#        copie si comportavano in due modi diversi, sbagliati tutti e due:
#          · con `2>/dev/null ... || true` un errore del DB (connessione,
#            permessi, SQL) diventava «nessuna riga», e lo smoke lo riportava
#            come un'asserzione falsa («Impossibile risolvere auth_user.id»);
#          · senza `|| true`, sotto `pipefail` era il contrario: una query con
#            zero righe chiudeva lo smoke senza una parola (il `grep` vuoto
#            esce con 1).
# Uso (dopo `_smoke_auth.sh`):
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_db.sh"
#   USER_ID=$(smoke_db_query "SELECT id FROM auth_user WHERE username = 'x'" | tail -1)
# Ritorna: 0 con le righe su stdout (anche nessuna: zero righe e' un dato, e
#        la decisione resta dello smoke); il codice di psql, non zero, se la
#        query fallisce, con la causa su stderr. Sotto `set -euo pipefail`
#        un'assegnazione `X=$(smoke_db_query ...)` allora ferma lo smoke, e il
#        runner (`scripts/smoke-baseline.sh`) lo classifica ERRORE, non
#        ASSERZIONE.
# ⚠️ Gira col ruolo dell'applicazione e SENZA il contesto dell'operatore: una
#    tabella con RLS torna vuota, e lo zero non e' un dato. Per quelle si passa
#    da `manage-env.sh shell` col contesto, non da qui.
# ⛔ Lo stderr di `manage-env.sh` porta anche il log di Django (righe
#    «<data> INFO ...»): si scarta quello, mai il messaggio di psql.
# ------------------------------------------------------------

_SMOKE_DB_BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

smoke_db_query() {
    local sql="$1" errore out rc=0
    errore=$(mktemp)
    out=$("${_SMOKE_DB_BACKEND_DIR}/manage-env.sh" dbshell -- \
            -X -q -t -A -v ON_ERROR_STOP=1 -c "$sql" 2>"$errore") || rc=$?
    if (( rc != 0 )); then
        # La causa e' il messaggio di psql; la riga `CommandError` di Django che
        # lo segue ripete solo il comando, e si mostra solo se e' l'unica.
        local causa
        causa=$(grep -vE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[^ ]+ (DEBUG|INFO|WARNING) ' "$errore" || true)
        local senza_comando
        senza_comando=$(printf '%s\n' "$causa" | sed '/^CommandError:/,$d')
        if [[ -n "$senza_comando" ]]; then causa="$senza_comando"; fi
        {
            echo "ERRORE DB (smoke_db_query, rc=$rc): $(printf '%s' "$sql" | tr -s ' \n' ' ' | cut -c1-120)"
            printf '%s\n' "$causa" | head -8 | sed 's/^/    /'
        } >&2
        rm -f "$errore"
        return "$rc"
    fi
    rm -f "$errore"
    # `|| true`: zero righe fa uscire `grep` con 1, ed e' un esito, non un errore.
    printf '%s\n' "$out" | grep -v '^$' || true
}
