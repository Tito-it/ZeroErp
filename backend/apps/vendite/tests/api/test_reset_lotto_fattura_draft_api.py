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
4) VenditeResetLottoFatturaDraftApiTests.test_reset_lotto_fattura_draft_post_permission_allowed
5) VenditeResetLottoFatturaDraftApiTests.test_reset_lotto_fattura_draft_post_permission_denied
"""

import json
from unittest.mock import Mock, patch

from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


class VenditeResetLottoFatturaDraftApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Percorso felice — i QUATTRO contatori arrivano interi nell'envelope.
    #        `riemesse_attivita` (DB 2026-08-04, slice 6-B) è quello che il
    #        drawer mostra nel toast di esito: se cade qui, l'operatore legge
    #        «0 righe di commessa» su un'operazione che ne ha rimesse in coda.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_elimina_fattura_da_lotto")
    def test_reset_lotto_fattura_draft_ok(self, mocked_service, _mock_auth):
        # Valori distinti fra loro: con quattro `1` uno scambio di chiavi
        # lungo il passaggio service → envelope passerebbe inosservato.
        mocked_service.return_value = {
            "updated_attivita": 1,
            "deleted_fatture": 1,
            "deleted_righe": 3,
            "riemesse_attivita": 2,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["updated_attivita"], 1)
        self.assertEqual(data["deleted_fatture"], 1)
        self.assertEqual(data["deleted_righe"], 3)
        self.assertEqual(data["riemesse_attivita"], 2)
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

    # Scopo: Verifica che post_permission="reset_lotto_fattura_draft" consenta l'accesso con azione abilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_elimina_fattura_da_lotto")
    def test_reset_lotto_fattura_draft_post_permission_allowed(
        self, mocked_service, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_service.return_value = {
            "updated_attivita": 1, "deleted_fatture": 1, "deleted_righe": 1,
            "riemesse_attivita": 0,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "reset_lotto_fattura_draft")

    # Scopo: Verifica che post_permission="reset_lotto_fattura_draft" neghi l'accesso con azione disabilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    def test_reset_lotto_fattura_draft_post_permission_denied(
        self, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        response = self.client.post(
            "/api/v1/vendite/lotti/10/fatture/22/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "reset_lotto_fattura_draft")
