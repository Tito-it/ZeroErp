# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint attivazione della veste operatore invitata:
#        1. GET  /attivazione-validate/{token}/ — verifica token invito
#        2. POST /attivazione/ — consuma il token e accende la veste
#        Le view sono il building block `attivazione_veste_views` sulla porta
#        OPERATORE: stessa regola di portale e shop (L-3). Dal 2026-09-25
#        l'attivazione ACCENDE la veste (prima nasceva gia' attiva, A-3) e
#        chi ha gia' una password attiva con un clic.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.attivazione_veste_views import (
    AttivazioneVesteValidateView,
    AttivazioneVesteView,
)
from apps.core.services.invito_veste import PORTA_OPERATORE


class AttivazioneValidateView(AttivazioneVesteValidateView):
    """GET: verifica se un token invito operatore e' ancora valido (senza consumarlo)."""

    porta = PORTA_OPERATORE


class AttivazioneView(AttivazioneVesteView):
    """POST: attivazione della veste operatore con il token dell'invito."""

    porta = PORTA_OPERATORE
    messaggio_con_password = "Account attivato con successo. Effettua il login con la nuova password."  # noqa: S105 — testo del messaggio, non una password
    messaggio_cross = "Accesso operatore attivato. Effettua il login con le tue credenziali esistenti."
