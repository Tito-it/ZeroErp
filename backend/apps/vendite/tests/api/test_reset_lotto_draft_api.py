"""
Indice test eseguiti:
1) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_ok
2) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_requires_idempotency_key
3) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_v1_requires_jwt
4) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_post_permission_allowed
5) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_post_permission_denied
"""

import json
from unittest.mock import patch, Mock

from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


class VenditeResetLottoDraftApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Verifica il caso `test_reset_lotto_draft_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
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

    # Scopo: Verifica il caso `test_reset_lotto_draft_requires_idempotency_key`.
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

    # Scopo: Verifica il caso `test_reset_lotto_draft_v1_requires_jwt`.
    def test_reset_lotto_draft_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-reset-2"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica che post_permission="reset_lotto_draft" consenta l'accesso con azione abilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
    def test_reset_lotto_draft_post_permission_allowed(
        self, mocked_service, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_service.return_value = {
            "updated_lotti": 1, "updated_attivita": 0,
            "deleted_fatture": 0, "deleted_righe": 0,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "reset_lotto_draft")

    # Scopo: Verifica che post_permission="reset_lotto_draft" neghi l'accesso con azione disabilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    def test_reset_lotto_draft_post_permission_denied(
        self, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "reset_lotto_draft")
