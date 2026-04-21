# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli endpoint stub shop (§8.4.4/§8.4.5). PR-C portera' il
#        MVP reale; per ora verifichiamo che lo stub risponda 501 con
#        codice errore dedicato E_SHOP_NON_DISPONIBILE e non tocchi DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ShopActivateStubTests.test_get_ritorna_501_con_codice_dedicato
2) ShopRegisterCheckEmailStubTests.test_post_ritorna_501_con_codice_dedicato
"""

import json
from unittest import TestCase

from django.test import RequestFactory


class ShopActivateStubTests(TestCase):

    # Scopo: GET /api/v1/shop/activate/<token>/ → 501 E_SHOP_NON_DISPONIBILE.
    # Il token nella path e' ignorato (stub): verifica che la view non
    # consulti DB e ritorni immediatamente lo stub.
    def test_get_ritorna_501_con_codice_dedicato(self):
        from apps.shop.api.views import ShopActivateView
        factory = RequestFactory()
        request = factory.get("/api/v1/shop/activate/whatever/")

        response = ShopActivateView().get(request, token="whatever")
        self.assertEqual(response.status_code, 501)
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_SHOP_NON_DISPONIBILE")
        self.assertIn("PR-C", body["error"]["message"])


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
