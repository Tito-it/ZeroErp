# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API reset singola fattura lotto DRAFT.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeResetLottoFatturaDraftApiTests.test_reset_lotto_fattura_draft_ok
2) VenditeResetLottoFatturaDraftApiTests.test_reset_lotto_fattura_draft_requires_idempotency_key
3) VenditeResetLottoFatturaDraftApiTests.test_reset_lotto_fattura_draft_v1_requires_jwt
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase


class VenditeResetLottoFatturaDraftApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        self.client = Client()

    # Scopo: Verifica il caso `test_reset_lotto_fattura_draft_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_reset_lotto_fattura_draft")
    def test_reset_lotto_fattura_draft_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = {
            "updated_attivita": 1,
            "deleted_fatture": 1,
            "deleted_righe": 1,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once_with(lotto_id=10, fattura_id=22)

    # Scopo: Verifica il caso `test_reset_lotto_fattura_draft_requires_idempotency_key`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_reset_lotto_fattura_draft_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    # Scopo: Verifica il caso `test_reset_lotto_fattura_draft_v1_requires_jwt`.
    def test_reset_lotto_fattura_draft_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 401)
