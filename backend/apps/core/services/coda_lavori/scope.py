# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Derivazione della `scope_key` canonica dei job OPERATORE su
#        `dbops.coda_lavori`. Fonte UNICA del formato (estratta 2026-07-21
#        dalla `_scope_key_fatturazione` di vendite, regola del 2: la stessa
#        derivazione serve ora anche a polling/liste/badge della UI code —
#        brief-be-fe-gestione-code-lavori-stampa I-1, nessuna seconda logica
#        di scope).
# ------------------------------------------------------------

from __future__ import annotations

# Chiave dello scope "vede tutto" (whitelist emittenti None = admin globale).
SCOPE_KEY_ALL = "ALL"


# Scopo: Chiave canonica dello SCOPE emittente di un job — "ALL" per l'admin
#        globale (whitelist None), altrimenti gli emittenti autorizzati
#        ORDINATI e joinati. Ha DUE ruoli, per costruzione coerenti:
#        (1) componente-scope della chiave di BUSINESS dei job (dedup dei job
#        VIVI — stesso scope+parametri → stesso job); (2) token di OWNERSHIP
#        di polling/liste/azioni — chi condivide la STESSA scope_key condivide
#        job e visibilità. È sicuro: un operatore può ricevere via dedup solo
#        un job con la PROPRIA scope_key, quindi l'ownership scope-based non
#        allarga la visibilità oltre ciò a cui è già autorizzato.
def scope_key_da_emittenti(emittente_ids: list[int] | None) -> str:
    if emittente_ids is None:
        return SCOPE_KEY_ALL
    return ",".join(str(e) for e in sorted(emittente_ids))
