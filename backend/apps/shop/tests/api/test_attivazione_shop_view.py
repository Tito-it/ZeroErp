# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del cablaggio delle view di attivazione shop sulla porta SHOP.
#        Il comportamento (forma, conferma, veste accesa) e' del building
#        block invito_veste e si prova una volta sola in
#        apps/core/tests/services/test_invito_veste.py: qui c'erano le copie
#        dei test del portale, come le view erano copie delle sue.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CablaggioTests.test_view_sulla_porta_shop
"""

from unittest import TestCase


class CablaggioTests(TestCase):

    # Scopo: Le view pubbliche dello shop sono il BB sulla porta SHOP.
    def test_view_sulla_porta_shop(self):
        from apps.core.services.invito_veste import PORTA_SHOP
        from apps.shop.api.views_attivazione import (
            AttivazioneShopValidateView,
            AttivazioneShopView,
        )

        self.assertIs(AttivazioneShopValidateView.porta, PORTA_SHOP)
        self.assertIs(AttivazioneShopView.porta, PORTA_SHOP)
