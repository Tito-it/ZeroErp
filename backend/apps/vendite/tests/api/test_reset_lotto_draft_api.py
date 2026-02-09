"""
Indice test eseguiti:
1) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_ok
2) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_requires_idempotency_key
3) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_v1_requires_jwt
"""

import json
from unittest.mock import patch, Mock

from django.test import Client, SimpleTestCase


class VenditeResetLottoDraftApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_reset_lotto_draft")
    def test_reset_lotto_draft_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = {
            "updated_lotti": 1,
            "updated_attivita": 2,
            "deleted_fatture": 3,
            "deleted_righe": 4,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-reset-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated_lotti"], 1)
        mocked_service.assert_called_once_with(lotto_id=123)

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_reset_lotto_draft_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    def test_reset_lotto_draft_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-reset-2"},
        )
        self.assertEqual(response.status_code, 401)
