# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AttivazionePortaleValidateView + AttivazionePortaleView
#        + ProfileActivateShopView stub. Mock DB + TokenService. Compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  ValidateViewTests.test_token_invito_returns_requires_password_true
2)  ValidateViewTests.test_token_cross_returns_requires_password_false
3)  ValidateViewTests.test_token_invalido_returns_valid_false
4)  AttivaViewTests.test_flow_invito_happy_path
5)  AttivaViewTests.test_flow_invito_senza_password_solleva
6)  AttivaViewTests.test_flow_cross_happy_path_no_password_richiesta
7)  AttivaViewTests.test_flow_cross_ignora_password_in_payload
8)  AttivaViewTests.test_flow_cross_riattiva_fallita_solleva_e_rollback
9)  AttivaViewTests.test_token_mancante_solleva
10) AttivaViewTests.test_token_invalido_solleva
11) AttivaViewTests.test_password_mismatch_flow_invito_solleva
12) AttivaViewTests.test_meta_senza_identita_id_solleva
13) ProfileActivateShopStubTests.test_stub_ritorna_501
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import RequestFactory


_VIEWS_PATH = "apps.portale.api.views"
_INVITO = "INVITO_PORTALE"
_CROSS = "ATTIVAZIONE_PORTALE_CROSS"


def _resolved(auth_user_id: int, identita_id: int | None, token_type: str):
    """Scopo: Costruisce la tupla ritornata da `resolve_portale_token`
    per i test. Centralizza lo shape evitando drift con la signature."""
    meta = {"identita_id": identita_id} if identita_id is not None else {}
    return (auth_user_id, meta, token_type)


class ValidateViewTests(TestCase):

    # Scopo: Token INVITO valido → il FE deve mostrare il form password.
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_token_invito_returns_requires_password_true(self, mock_resolve):
        mock_resolve.return_value = _resolved(10, 500, _INVITO)
        from apps.portale.api.views import AttivazionePortaleValidateView

        response = AttivazionePortaleValidateView().get(MagicMock(), token="tk")
        body = json.loads(response.content)["data"]
        self.assertTrue(body["valid"])
        self.assertEqual(body["token_type"], _INVITO)
        self.assertTrue(body["requires_password"])

    # Scopo: Token CROSS valido → il FE deve mostrare conferma un-click.
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_token_cross_returns_requires_password_false(self, mock_resolve):
        mock_resolve.return_value = _resolved(10, 500, _CROSS)
        from apps.portale.api.views import AttivazionePortaleValidateView

        response = AttivazionePortaleValidateView().get(MagicMock(), token="tk")
        body = json.loads(response.content)["data"]
        self.assertTrue(body["valid"])
        self.assertEqual(body["token_type"], _CROSS)
        self.assertFalse(body["requires_password"])

    # Scopo: Token sconosciuto/scaduto → messaggio generico, no enumeration.
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_token_invalido_returns_valid_false(self, mock_resolve):
        mock_resolve.return_value = None
        from apps.portale.api.views import AttivazionePortaleValidateView

        response = AttivazionePortaleValidateView().get(MagicMock(), token="x")
        body = json.loads(response.content)["data"]
        self.assertFalse(body["valid"])
        self.assertIn("message", body)
        self.assertNotIn("token_type", body)


class AttivaViewTests(TestCase):

    def _post(self, payload: dict):
        factory = RequestFactory()
        body = json.dumps(payload).encode("utf-8")
        return factory.post(
            "/api/v1/portale/attivazione/conferma/",
            data=body,
            content_type="application/json",
        )

    # Scopo: Flow INVITO — consume token INVITO + apply_new_password.
    @patch(f"{_VIEWS_PATH}.apply_new_password")
    @patch(f"{_VIEWS_PATH}.validate_password")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    @patch(f"{_VIEWS_PATH}._token_service")
    def test_flow_invito_happy_path(
        self, mock_token, mock_resolve, MockUser, mock_validate_pw, mock_apply_pw
    ):
        mock_resolve.return_value = _resolved(42, 500, _INVITO)
        mock_user = MagicMock(spec=["id", "username"])
        mock_user.id = 42
        MockUser.objects.filter.return_value.first.return_value = mock_user
        mock_validate_pw.return_value = None
        mock_token.consume.return_value = None

        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({
                "token": "tk_invito",
                "new_password": "Str0ngPass!",
                "new_password_confirm": "Str0ngPass!",
            })
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)["data"]
        self.assertEqual(body["token_type"], _INVITO)
        # Consume con tipo INVITO + apply_new_password con identita_id=500.
        mock_token.consume.assert_called_once()
        args, kwargs = mock_token.consume.call_args
        self.assertEqual(args[1], _INVITO)
        mock_apply_pw.assert_called_once()
        call_kwargs = mock_apply_pw.call_args.kwargs
        self.assertEqual(call_kwargs["identita_id"], 500)
        self.assertFalse(call_kwargs["blacklist_tokens"])

    # Scopo: Flow INVITO senza password nel payload → errore.
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_flow_invito_senza_password_solleva(self, mock_resolve, MockUser):
        mock_resolve.return_value = _resolved(42, 500, _INVITO)
        mock_user = MagicMock()
        mock_user.id = 42
        MockUser.objects.filter.return_value.first.return_value = mock_user

        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({"token": "tk_invito"})
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")

    # Scopo: Flow CROSS — consume token CROSS + riattiva identita, NO password.
    @patch(f"{_VIEWS_PATH}.apply_new_password")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}._portale_repo")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    @patch(f"{_VIEWS_PATH}._token_service")
    def test_flow_cross_happy_path_no_password_richiesta(
        self, mock_token, mock_resolve, mock_repo, MockUser, mock_apply_pw
    ):
        mock_resolve.return_value = _resolved(42, 500, _CROSS)
        mock_user = MagicMock(spec=["id", "username"])
        mock_user.id = 42
        MockUser.objects.filter.return_value.first.return_value = mock_user
        mock_repo.riattiva_identita.return_value = True
        mock_token.consume.return_value = None

        from apps.portale.api.views import AttivazionePortaleView
        # Payload privo di password: valido nel flow CROSS.
        response = AttivazionePortaleView().post(
            self._post({"token": "tk_cross"})
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)["data"]
        self.assertEqual(body["token_type"], _CROSS)
        # Consume con tipo CROSS + riattiva identita_id=500 + NO apply_new_password.
        args, _ = mock_token.consume.call_args
        self.assertEqual(args[1], _CROSS)
        mock_repo.riattiva_identita.assert_called_once_with(500)
        mock_apply_pw.assert_not_called()

    # Scopo: Flow CROSS con riattiva_identita=False (identita rimossa tra
    # emissione invito e consume) → errore + rollback consume token.
    # Il test verifica che (a) l'HTTP e' errore E_ATTIVAZIONE_PORTALE,
    # (b) consume e' stato chiamato DENTRO la transazione che rollbacca
    # (il mock registra la call ma semanticamente lo stato DB sarebbe
    # invariato — qui il mock non simula il rollback, verifichiamo solo
    # che il branch errore si attivi invece di un 200 silente).
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}._portale_repo")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    @patch(f"{_VIEWS_PATH}._token_service")
    def test_flow_cross_riattiva_fallita_solleva_e_rollback(
        self, mock_token, mock_resolve, mock_repo, MockUser
    ):
        mock_resolve.return_value = _resolved(42, 500, _CROSS)
        MockUser.objects.filter.return_value.first.return_value = MagicMock()
        mock_repo.riattiva_identita.return_value = False  # identita rimossa
        mock_token.consume.return_value = None

        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({"token": "tk_stale"})
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")
        # consume e' chiamato (dentro la transaction.atomic che rollbacca);
        # il test documenta il flusso — il rollback reale e' responsabilita'
        # di Django/DB, non mockabile senza DB reale.
        mock_token.consume.assert_called_once()

    # Scopo: Flow CROSS ignora new_password anche se inviata (difesa: no
    # sovrascrittura password operativa).
    @patch(f"{_VIEWS_PATH}.apply_new_password")
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}._portale_repo")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    @patch(f"{_VIEWS_PATH}._token_service")
    def test_flow_cross_ignora_password_in_payload(
        self, mock_token, mock_resolve, mock_repo, MockUser, mock_apply_pw
    ):
        mock_resolve.return_value = _resolved(42, 500, _CROSS)
        mock_user = MagicMock(spec=["id", "username"])
        MockUser.objects.filter.return_value.first.return_value = mock_user
        mock_repo.riattiva_identita.return_value = True
        mock_token.consume.return_value = None

        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({
                "token": "tk_cross",
                "new_password": "FakePw!",  # ignorato
                "new_password_confirm": "FakePw!",
            })
        )
        self.assertEqual(response.status_code, 200)
        mock_apply_pw.assert_not_called()

    def test_token_mancante_solleva(self):
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(self._post({}))
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")

    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_token_invalido_solleva(self, mock_resolve):
        mock_resolve.return_value = None
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({"token": "bad"})
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")

    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_password_mismatch_flow_invito_solleva(self, mock_resolve, MockUser):
        mock_resolve.return_value = _resolved(42, 500, _INVITO)
        MockUser.objects.filter.return_value.first.return_value = MagicMock()
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

    # Scopo: Token senza identita_id nel meta (scenario legacy o corrotto)
    # → errore esplicito, non crash silente su set/UPDATE a vuoto.
    @patch(f"{_VIEWS_PATH}.User")
    @patch(f"{_VIEWS_PATH}.resolve_portale_token")
    def test_meta_senza_identita_id_solleva(self, mock_resolve, MockUser):
        mock_resolve.return_value = _resolved(42, None, _INVITO)
        MockUser.objects.filter.return_value.first.return_value = MagicMock()
        from apps.portale.api.views import AttivazionePortaleView
        response = AttivazionePortaleView().post(
            self._post({
                "token": "tk_legacy",
                "new_password": "Str0ngPass!",
                "new_password_confirm": "Str0ngPass!",
            })
        )
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_PORTALE")


class ProfileActivateShopStubTests(TestCase):
    """§8.4.3 stub autenticato portale → 501 E_SHOP_NON_DISPONIBILE."""

    def _post(self, payload: dict):
        factory = RequestFactory()
        body = json.dumps(payload).encode("utf-8")
        return factory.post(
            "/api/v1/portale/profile/activate-shop/",
            data=body,
            content_type="application/json",
        )

    def test_stub_ritorna_501(self):
        # Aggiramento auth chain: chiamiamo direttamente il handler.
        # L'infrastruttura PortaleBasePermission e' testata altrove.
        from apps.portale.api.views import ProfileActivateShopView
        response = ProfileActivateShopView().post(self._post({}))
        self.assertEqual(response.status_code, 501)
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_SHOP_NON_DISPONIBILE")
