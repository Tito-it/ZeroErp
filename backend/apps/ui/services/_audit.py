# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper privati riusati dai service admin del modulo `ui`.
#        Tipico esempio: estrazione username per audit fields delle
#        scritture admin (`user_insert` / `user_update`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any


# Scopo: Estrae l'username dell'utente corrente per popolare i campi di
#        audit (`user_insert` / `user_update`). Fallback `'system'` se
#        l'utente e' anonimo, None, o privo di `username` (es. token
#        S2S, scenari di test). Centralizzato qui per evitare drift
#        tra i service del modulo: cambiamenti alla policy audit
#        impattano un punto solo.
def user_label(user: Any) -> str:
    if user is None:
        return "system"
    username = getattr(user, "username", None)
    return str(username) if username else "system"
