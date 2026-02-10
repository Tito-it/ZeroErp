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

from unittest.mock import patch

from django.test import TestCase

from apps.core.tests.api.auth_helpers import mock_api_auth


class VenditeResetLottoFatturaDraftApiTests(TestCase):
    @patch("apps.vendite.api.views.fn_reset_lotto_fattura_draft")
    def test_reset_lotto_fattura_draft_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = {
            "updated_attivita": 1,
            "deleted_fatture": 1,
            "deleted_righe": 1,
        }
        response = self.client.post(
            "/api/vendite/lotti/10/fatture/22/reset-draft/",
            data={},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key",
        )
        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once_with(lotto_id=10, fattura_id=22)

    def test_reset_lotto_fattura_draft_requires_idempotency_key(self):
        response = self.client.post(
            "/api/vendite/lotti/10/fatture/22/reset-draft/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    def test_reset_lotto_fattura_draft_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data={},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key",
        )
        self.assertEqual(response.status_code, 401)

