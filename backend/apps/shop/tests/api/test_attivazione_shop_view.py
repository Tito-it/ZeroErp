# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AttivazioneShopValidateView + AttivazioneShopView
#        (B1 §13.7 admin-driven). Mock DB + TokenService. Compatibile CI.
#        Pattern simmetrico a apps/portale/tests/api/test_attivazione_portale_view.py.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ValidateShopTests.test_token_invito_returns_requires_password_true
2) ValidateShopTests.test_token_cross_returns_requires_password_false
3) ValidateShopTests.test_token_invalido_returns_valid_false
4) AttivaShopTests.test_flow_invito_happy_path
5) AttivaShopTests.test_flow_cross_happy_path_no_password
6) AttivaShopTests.test_token_mancante_solleva
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import RequestFactory


_VIEWS_PATH = "apps.shop.api.views_attivazione"
_INVITO = "INVITO_SHOP"
_CROSS = "ATTIVAZIONE_SHOP_CROSS"


def _resolved(auth_user_id: int, identita_id: int | None, token_type: str):
    """Scopo: Tupla ritornata da `resolve_shop_token` per i test."""
    meta = {"identita_id": identita_id} if identita_id is not None else {}
    return (auth_user_id, meta, token_type)


class ValidateShopTests(TestCase):

    # Scopo: Token INVITO_SHOP valido -> requires_password=true.
    @patch(f"{_VIEWS_PATH}.resolve_shop_token")
    def test_token_invito_returns_requires_password_true(self, mock_resolve):
        mock_resolve.return_value = _resolved(10, 600, _INVITO)
        from apps.shop.api.views_attivazione import AttivazioneShopValidateView

        response = AttivazioneShopValidateView().get(MagicMock(), token="tk")
        body = json.loads(response.content)["data"]
        self.assertTrue(body["valid"])
        self.assertEqual(body["token_type"], _INVITO)
        self.assertTrue(body["requires_password"])

    # Scopo: Token CROSS valido -> requires_password=false (one-click).
    @patch(f"{_VIEWS_PATH}.resolve_shop_token")
    def test_token_cross_returns_requires_password_false(self, mock_resolve):
        mock_resolve.return_value = _resolved(10, 600, _CROSS)
        from apps.shop.api.views_attivazione import AttivazioneShopValidateView

        response = AttivazioneShopValidateView().get(MagicMock(), token="tk")
        body = json.loads(response.content)["data"]
        self.assertTrue(body["valid"])
        self.assertEqual(body["token_type"], _CROSS)
        self.assertFalse(body["requires_password"])

    # Scopo: Token sconosciuto/scaduto -> messaggio generico, no enumeration.
    @patch(f"{_VIEWS_PATH}.resolve_shop_token")
    def test_token_invalido_returns_valid_false(self, mock_resolve):
        mock_resolve.return_value = None
        from apps.shop.api.views_attivazione import AttivazioneShopValidateView

        response = AttivazioneShopValidateView().get(MagicMock(), token="x")
        body = json.loads(response.content)["data"]
        self.assertFalse(body["valid"])
        self.assertIn("message", body)
        self.assertNotIn("token_type", body)


class AttivaShopTests(TestCase):

    def _post(self, payload: dict):
        factory = RequestFactory()
        body = json.dumps(payload).encode("utf-8")
        return factory.post(
            "/api/v1/shop/attivazione/conferma/",
            data=body,
            content_type="application/json",
        )

    # Scopo: Flow INVITO_SHOP happy path: consume token + apply password +
    # attivazione dell'identita' (nasce disattivata anche qui, M-3).
    @patch(f"{_VIEWS_PATH}._portale_repo")
    @patch(f"{_VIEWS_PATH}.apply_new_password")
    @patch(f"{_VIEWS_PATH}.transaction.atomic")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}._token_service")
    @patch(f"{_VIEWS_PATH}.resolve_shop_token")
    def test_flow_invito_happy_path(
        self, mock_resolve, mock_token_svc, MockUser,
        mock_atomic, mock_apply, mock_repo,
    ):
        mock_resolve.return_value = _resolved(10, 600, _INVITO)
        mock_repo.riattiva_identita.return_value = True
        MockUser.objects.filter.return_value.first.return_value = MagicMock(id=10)
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

        from apps.shop.api.views_attivazione import AttivazioneShopView
        request = self._post({
            "token": "tk_shop",
            "new_password": "Strong#Password1",
            "new_password_confirm": "Strong#Password1",
        })
        # Bypass policy validate (validatore Django ha bisogno di settings).
        with patch(f"{_VIEWS_PATH}.validate_password"):
            response = AttivazioneShopView().post(request)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)["data"]
        self.assertEqual(body["token_type"], _INVITO)
        self.assertIn("attivato", body["message"].lower())
        mock_token_svc.consume.assert_called_once_with(
            "tk_shop", _INVITO, ip="127.0.0.1"
        )
        mock_apply.assert_called_once()
        mock_repo.riattiva_identita.assert_called_once_with(600)

    # Scopo: Flow CROSS happy path: consume + riattiva, no password.
    @patch(f"{_VIEWS_PATH}._portale_repo")
    @patch(f"{_VIEWS_PATH}.transaction.atomic")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}._token_service")
    @patch(f"{_VIEWS_PATH}.resolve_shop_token")
    def test_flow_cross_happy_path_no_password(
        self, mock_resolve, mock_token_svc, MockUser, mock_atomic, mock_repo
    ):
        mock_resolve.return_value = _resolved(10, 600, _CROSS)
        MockUser.objects.filter.return_value.first.return_value = MagicMock(id=10)
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)
        mock_repo.riattiva_identita.return_value = True

        from apps.shop.api.views_attivazione import AttivazioneShopView
        request = self._post({"token": "tk_cross"})
        response = AttivazioneShopView().post(request)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)["data"]
        self.assertEqual(body["token_type"], _CROSS)
        mock_token_svc.consume.assert_called_once_with(
            "tk_cross", _CROSS, ip="127.0.0.1"
        )
        mock_repo.riattiva_identita.assert_called_once_with(600)

    # Scopo: Token mancante nel payload -> 400 E_ATTIVAZIONE_SHOP.
    def test_token_mancante_solleva(self):
        from apps.shop.api.views_attivazione import AttivazioneShopView
        request = self._post({})
        response = AttivazioneShopView().post(request)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_SHOP")
