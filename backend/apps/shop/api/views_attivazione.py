# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint attivazione shop customer (B1 §13.7 admin-driven). Sono il
#        building block `attivazione_veste_views` sulla porta SHOP: token
#        INVITO_SHOP / ATTIVAZIONE_SHOP_CROSS, codice E_ATTIVAZIONE_SHOP.
#        Flusso con password (credenziale senza password vera) o con un clic.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.attivazione_veste_views import (
    AttivazioneVesteValidateView,
    AttivazioneVesteView,
)
from apps.core.services.invito_veste import PORTA_SHOP


class AttivazioneShopValidateView(AttivazioneVesteValidateView):
    """GET: verifica se un token attivazione shop e' ancora valido (no consume)."""

    porta = PORTA_SHOP


class AttivazioneShopView(AttivazioneVesteView):
    """POST: attivazione shop (con password o con un clic)."""

    porta = PORTA_SHOP
    messaggio_con_password = "Account shop attivato con successo. Effettua il login con la nuova password."  # noqa: S105 — testo del messaggio, non una password
    messaggio_cross = "Accesso shop attivato. Effettua il login con le tue credenziali esistenti."
