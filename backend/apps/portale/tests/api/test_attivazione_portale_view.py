# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AttivazionePortaleValidateView + AttivazionePortaleView.
#        Mock DB + TokenService + password validation. Compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ValidateViewTests.test_token_valido_returns_valid_true
2) ValidateViewTests.test_token_invalido_returns_valid_false
3) AttivaViewTests.test_attivazione_happy_path
4) AttivaViewTests.test_token_mancante_solleva
5) AttivaViewTests.test_password_mismatch_solleva
6) AttivaViewTests.test_token_invalido_solleva
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import RequestFactory


_VIEWS_PATH = "apps.portale.api.views"


class ValidateViewTests(TestCase):

    @patch(f"{_VIEWS_PATH}._token_service")
    def test_token_valido_returns_valid_true(self, mock_token):
        mock_token.validate.return_value = {"auth_user_id": 10}
        from apps.portale.api.views import AttivazionePortaleValidateView

        request = MagicMock()
        response = AttivazionePortaleValidateView().get(request, token="t123")
        body = json.loads(response.content)
        self.assertTrue(body["data"]["valid"])

    @patch(f"{_VIEWS_PATH}._token_service")
    def test_token_invalido_returns_valid_false(self, mock_token):
        mock_token.validate.return_value = None
        from apps.portale.api.views import AttivazionePortaleValidateView

        request = MagicMock()
        response = AttivazionePortaleValidateView().get(request, token="scaduto")
        body = json.loads(response.content)
        self.assertFalse(body["data"]["valid"])
        self.assertIn("message", body["data"])


class AttivaViewTests(TestCase):

    def _post(self, payload: dict):
        """Scopo: Crea HttpRequest Django con JSON body. `handle_post_json`
        accetta sia HttpRequest sia DRF Request; il primo evita di dover
        configurare DEFAULT_PARSER_CLASSES nei test unit.
        """
        factory = RequestFactory()
        body = json.dumps(payload).encode("utf-8")
        return factory.post(
            "/api/v1/portale/attivazione/conferma/",
            data=body,
            content_type="application/json",
        )

    @patch(f"{_VIEWS_PATH}.apply_new_password")
    @patch(f"{_VIEWS_PATH}.validate_password")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}.validate_and_extract_token")
    @patch(f"{_VIEWS_PATH}._token_service")
    def test_attivazione_happy_path(
        self,
        mock_token,
        mock_validate_extract,
        MockUser,
        mock_validate_pw,
        mock_apply_pw,
    ):
        mock_validate_extract.return_value = (42, {})
        mock_user_obj = MagicMock(spec=["id", "username"])
        mock_user_obj.id = 42
        MockUser.objects.filter.return_value.first.return_value = mock_user_obj
        mock_validate_pw.return_value = None  # password accettata
        mock_token.consume.return_value = None

        from apps.portale.api.views import AttivazionePortaleView

        response = AttivazionePortaleView().post(
            self._post({
                "token": "tk_valid",
                "new_password": "Str0ngPass!",
                "new_password_confirm": "Str0ngPass!",
            })
        )
        self.assertEqual(response.status_code, 200)
        mock_token.consume.assert_called_once()
        mock_apply_pw.assert_called_once()

    def test_token_mancante_solleva(self):
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({"new_password": "x", "new_password_confirm": "x"})
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")

    def test_password_mismatch_solleva(self):
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({
                "token": "tk",
                "new_password": "a",
                "new_password_confirm": "b",
            })
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")

    @patch(f"{_VIEWS_PATH}.validate_and_extract_token")
    def test_token_invalido_solleva(self, mock_validate_extract):
        from apps.core.services.service_errors import ServiceError
        mock_validate_extract.side_effect = ServiceError(
            code="E_ATTIVAZIONE_PORTALE",
            message="Token non valido, scaduto o gia' utilizzato.",
        )
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({
                "token": "bad",
                "new_password": "Str0ngPass!",
                "new_password_confirm": "Str0ngPass!",
            })
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")
