# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli endpoint stub shop (§8.4.4/§8.4.5). PR-C portera' il
#        MVP reale; per ora verifichiamo che lo stub risponda 501 con
#        codice errore dedicato E_SHOP_NON_DISPONIBILE e non tocchi DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ShopRegisterCheckEmailStubTests.test_post_ritorna_501_con_codice_dedicato

Nota: ShopActivateView stub (§8.4.4) rimosso in B1 §13.7 — sostituito da
AttivazioneShopValidateView + AttivazioneShopView reali. Vedi
`test_attivazione_shop_view.py`.
"""

import json
from unittest import TestCase

from django.test import RequestFactory


class ShopRegisterCheckEmailStubTests(TestCase):

    # Scopo: POST /api/v1/shop/register/check-email/ → 501 E_SHOP_NON_DISPONIBILE.
    def test_post_ritorna_501_con_codice_dedicato(self):
        from apps.shop.api.views import ShopRegisterCheckEmailView
        factory = RequestFactory()
        body = json.dumps({"email": "guest@test.example"}).encode("utf-8")
        request = factory.post(
            "/api/v1/shop/register/check-email/",
            data=body,
            content_type="application/json",
        )

        response = ShopRegisterCheckEmailView().post(request)
        self.assertEqual(response.status_code, 501)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"]["code"], "E_SHOP_NON_DISPONIBILE")
