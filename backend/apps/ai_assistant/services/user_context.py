# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper per risolvere il contesto utente nei tool AI.
#        Centralizza la risoluzione di emittente_fiscale_id e
#        altri dati di contesto dall'utente autenticato.
#        Riutilizzabile da tutti i tool senza duplicazione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager


# Scopo: Recupera l'emittente_fiscale_id dal profilo utente.
#        Catena di fallback: attributo diretto → profilo DB → primo emittente.
#        Usato dai tool AI che necessitano del contesto emittente.
def get_emittente_fiscale_id(request: Any) -> int:
    user = request.user

    # Fast path: attributo diretto (se arricchito dal middleware)
    if hasattr(user, "emittente_fiscale_id"):
        return user.emittente_fiscale_id

    from apps.core.db.core_repository import CoreRepository

    repo = CoreRepository()

    # Fallback 1: profilo utente
    profile = repo.get_user_profile(user.id)
    if profile and profile.get("emittente_fiscale_id"):
        return int(profile["emittente_fiscale_id"])

    # Fallback 2: primo emittente associato
    emittenti = repo.get_user_emittenti(user.id)
    if emittenti:
        return int(emittenti[0]["id"])

    ErrorManager.raise_error(
        code="E_PRATICA_VALIDATION",
        message="Impossibile determinare l'emittente fiscale dell'operatore.",
        detail="L'operatore non ha emittenti fiscali associati.",
    )
    raise AssertionError("unreachable")
