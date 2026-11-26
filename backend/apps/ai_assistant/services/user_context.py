# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.services.permissions_resolver import PermissionResolver


# Scopo: l'emittente su cui LEGGE un tool: quello di chi agisce
#        (`PermissionResolver.get_emittente_for_user`: l'emittente attivo
#        validato, poi quello del permesso). La modalita' «tutti gli emittenti»
#        l'ha gia' fermata il cancello del gemello (`AITool.cancello_del_gemello`);
#        qui resta solo l'operatore senza emittente assegnato, che non ha niente
#        da leggere: lo si dice, invece di cercare su un emittente a caso.
# ⚠️ Chi SCRIVE non passa di qui: usa il BB `emittente_per_scrivere`
#    (`apps.core.services.perimetro_emittente`), come gli endpoint.
# ⛔ Fino al 2026-11-25 una catena sua (attributo dell'utente → profilo →
#    primo degli emittenti visibili): il profilo risponde il gestore globale a chi
#    non ha una riga di permesso, cioe' al super admin anche con un altro
#    emittente scelto (E1-2 di brief-be-fe-BB-audit §6.1).
def emittente_di_lettura(request: Any) -> int:
    emittente_id = PermissionResolver.get_emittente_for_user(request.user)
    ErrorManager.require(
        emittente_id is not None,
        code="E_PRATICA_VALIDATION",
        message="Impossibile determinare l'emittente fiscale dell'operatore.",
        detail="L'operatore non ha emittenti fiscali associati.",
        function_name="ai_assistant.user_context.emittente_di_lettura",
    )
    assert emittente_id is not None
    return emittente_id

