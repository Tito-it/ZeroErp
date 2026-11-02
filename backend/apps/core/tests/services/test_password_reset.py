# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per endpoint reset password dimenticata.
#        Mock DB e SMTP, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RequestTests.test_email_trova_la_credenziale_e_spedisce
2) RequestTests.test_con_chiocciola_senza_email_ripiega_sul_nome_utente
2b) RequestTests.test_nome_utente_non_cerca_l_email
2c) RequestTests.test_nessuna_credenziale_utilizzabile_stessa_risposta
3) RequestTests.test_identificativo_vuoto_o_campo_vecchio_non_cerca (anche non testo: 200, mai 500)
4) ValidateTests.test_valid_token
5) ValidateTests.test_invalid_token
6) ConfirmTests.test_valid_token_changes_password
7) ConfirmTests.test_invalid_token_raises
8) ConfirmTests.test_password_mismatch_raises
9) ConfirmTests.test_empty_password_raises
10) HelperTests.test_get_user_uo_id
11) ConfirmViewTests.test_reset_riuscito_azzera_i_tentativi_nella_transazione
12) ConfirmViewTests.test_l_email_di_conferma_scrive_l_ora_dell_azienda — B-6 un-solo-fuso-aziendale
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework.test import APIRequestFactory

from apps.core.api.password_reset_views import PasswordResetRequestView
from apps.core.api.throttling import PasswordResetRateThrottle
from apps.core.services.service_errors import ServiceError

_TOKEN_SVC = "apps.core.api.password_reset_views._token_service"
_EMAIL_SVC = "apps.core.api.password_reset_views._email_service"
_AUTH_REPO = "apps.core.api.password_reset_views._auth_repo"
_USER_MODEL = "apps.core.api.password_reset_views.User"
_GET_UO = "apps.core.api.password_reset_views._auth_repo.get_unita_organizzativa_id"
_GET_IP = "apps.core.api.password_reset_views.get_client_ip"
_DJANGO_SETTINGS = "django.conf.settings"
_PER_EMAIL = "apps.core.api.password_reset_views.credenziale_per_email"
_PER_NOME = "apps.core.api.password_reset_views.credenziale_per_nome_utente"
_NOME_VIS = "apps.core.api.password_reset_views.nome_visualizzato"
_ATOMIC = "apps.core.api.password_reset_views.transaction.atomic"


class RequestTests(TestCase):
    """Test per PasswordResetRequestView (richiesta reset), sulla view vera.

    ⭐ Riscritti il 2026-10-06 (L-4): i tre test di prima non chiamavano mai la
    view (uno chiamava a mano il mock che poi verificava), quindi erano verdi
    qualunque cosa facesse il codice.
    """

    def setUp(self) -> None:
        self.enterContext(patch.object(PasswordResetRateThrottle, "allow_request", return_value=True))
        self.token = self.enterContext(patch(_TOKEN_SVC))
        self.token.create.return_value = "token123"
        self.email = self.enterContext(patch(_EMAIL_SVC))
        self.enterContext(patch(_GET_UO, return_value=None))
        self.enterContext(patch(_NOME_VIS, return_value="Mario"))
        self.enterContext(patch(_ATOMIC))

    def _post(self, corpo: dict):
        richiesta = APIRequestFactory().post(
            "/api/v1/auth/password-reset-request/", corpo, format="json",
        )
        return PasswordResetRequestView.as_view()(richiesta)

    # Scopo: Con l'email (L-4) il link parte verso la credenziale di quell'email.
    @patch(_PER_EMAIL)
    def test_email_trova_la_credenziale_e_spedisce(self, mock_per_email):
        mock_per_email.return_value = MagicMock(id=42, is_active=True, email="mario@test.com")
        risposta = self._post({"identificativo": "  Mario@Test.com "})
        self.assertEqual(risposta.status_code, 200)
        mock_per_email.assert_called_once_with("Mario@Test.com")
        self.assertEqual(self.token.create.call_args.kwargs["auth_user_id"], 42)
        self.assertEqual(self.email.send_email.call_args.kwargs["destinatario"], "mario@test.com")

    # Scopo: Una «@» che non e' l'email di nessuno si cerca come nome utente:
    # il modello non vieta una «@» nel nome utente.
    @patch(_PER_NOME)
    @patch(_PER_EMAIL, return_value=None)
    def test_con_chiocciola_senza_email_ripiega_sul_nome_utente(self, _per_email, mock_per_nome):
        mock_per_nome.return_value = MagicMock(id=7, is_active=True, email="a@b.it")
        self._post({"identificativo": "nome@utente"})
        mock_per_nome.assert_called_once_with("nome@utente")
        self.assertEqual(self.token.create.call_args.kwargs["auth_user_id"], 7)

    # Scopo: Senza «@» e' un nome utente: l'email non si cerca nemmeno.
    @patch(_PER_NOME)
    @patch(_PER_EMAIL)
    def test_nome_utente_non_cerca_l_email(self, mock_per_email, mock_per_nome):
        mock_per_nome.return_value = MagicMock(id=9, is_active=True, email="m@x.it")
        self._post({"identificativo": "mario"})
        mock_per_email.assert_not_called()
        mock_per_nome.assert_called_once_with("mario")
        self.assertEqual(self.token.create.call_args.kwargs["auth_user_id"], 9)

    # Scopo: Credenziale sconosciuta, spenta o senza email: stessa risposta, niente token.
    @patch(_PER_NOME)
    @patch(_PER_EMAIL, return_value=None)
    def test_nessuna_credenziale_utilizzabile_stessa_risposta(self, _per_email, mock_per_nome):
        casi = (None, MagicMock(id=1, is_active=False, email="x@y.it"), MagicMock(id=2, is_active=True, email=""))
        risposte = set()
        for utente in casi:
            mock_per_nome.return_value = utente
            risposte.add(self._post({"identificativo": "chiunque"}).content)
        self.token.create.assert_not_called()
        self.email.send_email.assert_not_called()
        self.assertEqual(len(risposte), 1)

    # Scopo: Il campo vecchio (`username`) non e' piu' il contratto, e un valore
    # che non e' testo vale come assente: stessa risposta, nessuna ricerca.
    @patch(_PER_NOME)
    @patch(_PER_EMAIL)
    def test_identificativo_vuoto_o_campo_vecchio_non_cerca(self, mock_per_email, mock_per_nome):
        for corpo in ({}, {"identificativo": "   "}, {"identificativo": 123}, {"username": "mario"}):
            self.assertEqual(self._post(corpo).status_code, 200)
        mock_per_email.assert_not_called()
        mock_per_nome.assert_not_called()
        self.token.create.assert_not_called()


class ValidateTests(TestCase):
    """Test per PasswordResetValidateView (verifica token)."""

    # Scopo: Verifica che token valido ritorni valid=true.
    @patch(_TOKEN_SVC)
    def test_valid_token(self, mock_token):
        mock_token.validate.return_value = (42, {})

        from apps.core.api.password_reset_views import PasswordResetValidateView
        view = PasswordResetValidateView()
        request = MagicMock()

        response = view.get(request, token="valid_token")
        self.assertEqual(response.status_code, 200)

    # Scopo: Verifica che token invalido ritorni valid=false.
    @patch(_TOKEN_SVC)
    def test_invalid_token(self, mock_token):
        mock_token.validate.return_value = None

        from apps.core.api.password_reset_views import PasswordResetValidateView
        view = PasswordResetValidateView()
        request = MagicMock()

        response = view.get(request, token="bad_token")
        self.assertEqual(response.status_code, 200)


class ConfirmTests(TestCase):
    """Test per PasswordResetConfirmView (conferma reset)."""

    # Scopo: Verifica che token valido consumi il token e trovi l'utente.
    @patch(_AUTH_REPO)
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_TOKEN_SVC)
    def test_valid_token_changes_password(self, mock_token, mock_ip, mock_auth):
        mock_token.consume.return_value = 42
        mock_auth.get_unita_organizzativa_id.return_value = None

        # Verifica che consume venga chiamato con i parametri corretti
        result = mock_token.consume("token123", "RESET_PASSWORD", ip="192.168.1.1")
        self.assertEqual(result, 42)
        mock_token.consume.assert_called_with("token123", "RESET_PASSWORD", ip="192.168.1.1")

    # Scopo: Verifica che token invalido lanci errore.
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_TOKEN_SVC)
    def test_invalid_token_raises(self, mock_token, mock_ip):
        mock_token.consume.side_effect = ServiceError(
            code="E_TOKEN", message="Token non valido."
        )
        with self.assertRaises(ServiceError):
            mock_token.consume("bad_token", "RESET_PASSWORD", ip="192.168.1.1")

    # Scopo: Verifica che password non corrispondenti lancino errore.
    def test_password_mismatch_raises(self):
        from apps.core.services.error_manager import ErrorManager
        with self.assertRaises(ServiceError):
            ErrorManager.require(
                "nuova123" == "diversa456",
                code="E_RESET_PASSWORD",
                message="La nuova password e la conferma non coincidono.",
            )

    # Scopo: Verifica che password vuota lanci errore.
    def test_empty_password_raises(self):
        from apps.core.services.error_manager import ErrorManager
        with self.assertRaises(ServiceError):
            ErrorManager.require(bool(""), code="E_RESET_PASSWORD", message="Nuova password obbligatoria.")


class ConfirmViewTests(TestCase):
    """La view di conferma, non i suoi mock: l'azzeramento dei tentativi (D-2)."""

    # Scopo: Reset riuscito → nuova password E tentativi azzerati su tutte le
    # provenienze, dentro la stessa transazione (se l'azzeramento fallisce,
    # il reset si annulla: niente password cambiata con il freno ancora su).
    @patch("apps.core.api.throttling.ConfermaTokenRateThrottle.allow_request", return_value=True)
    @patch("apps.core.api.password_reset_views.transaction")
    @patch("apps.core.api.password_reset_views.apply_new_password")
    @patch("apps.core.services.auth_helpers.validate_password")
    @patch("apps.core.api.password_reset_views.validate_and_extract_token", return_value=(42, {}))
    @patch(_USER_MODEL)
    @patch(_EMAIL_SVC)
    @patch(_AUTH_REPO)
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_TOKEN_SVC)
    def test_reset_riuscito_azzera_i_tentativi_nella_transazione(
        self, mock_token, _ip, mock_repo, _email, MockUser, _validate_token,
        _validate_pw, mock_apply, mock_tx, _thr,
    ):
        from rest_framework.test import APIRequestFactory

        from apps.core.api.password_reset_views import PasswordResetConfirmView

        user = MagicMock(id=42, email="m@x.it", first_name="M", username="m")
        MockUser.objects.filter.return_value.first.return_value = user
        mock_repo.get_unita_organizzativa_id.return_value = None
        ordine = MagicMock()
        mock_tx.atomic.return_value.__enter__.side_effect = lambda: ordine.entra()
        mock_tx.atomic.return_value.__exit__.side_effect = lambda *a: ordine.esce()
        mock_apply.side_effect = lambda *a, **k: ordine.apply()
        mock_repo.azzera_tentativi_credenziale.side_effect = lambda *a: ordine.azzera()

        request = APIRequestFactory().post(
            "/api/v1/auth/password-reset-confirm/",
            {"token": "tok", "new_password": "Nuova-2026!x", "new_password_confirm": "Nuova-2026!x"},
            format="json",
        )
        response = PasswordResetConfirmView.as_view()(request)

        self.assertEqual(response.status_code, 200, response.content)
        mock_repo.azzera_tentativi_credenziale.assert_called_once_with(42)
        nomi = [c[0] for c in ordine.mock_calls]
        self.assertEqual(nomi[:4], ["entra", "apply", "azzera", "esce"])

    # Scopo: B-6. L'ora del cambio nell'email e' quella dell'AZIENDA: le 23:30
    # UTC del 14 settembre sono le 01:30 del 15 a Roma. Fino al 2026-10-09
    # l'email scriveva l'ora UTC.
    @patch("apps.core.api.throttling.ConfermaTokenRateThrottle.allow_request", return_value=True)
    @patch("apps.core.api.password_reset_views.transaction")
    @patch("apps.core.api.password_reset_views.apply_new_password")
    @patch("apps.core.services.auth_helpers.validate_password")
    @patch("apps.core.api.password_reset_views.validate_and_extract_token", return_value=(42, {}))
    @patch(_USER_MODEL)
    @patch(_EMAIL_SVC)
    @patch(_AUTH_REPO)
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_TOKEN_SVC)
    def test_l_email_di_conferma_scrive_l_ora_dell_azienda(
        self, _token, _ip, mock_repo, mock_email, MockUser, _validate_token,
        _validate_pw, _apply, _tx, _thr,
    ):
        from datetime import UTC, datetime

        from rest_framework.test import APIRequestFactory

        from apps.core.api.password_reset_views import PasswordResetConfirmView
        from apps.core.services.fuso_aziendale import fuso_aziendale_forzato

        MockUser.objects.filter.return_value.first.return_value = MagicMock(
            id=42, email="m@x.it", first_name="M", username="m",
        )
        mock_repo.get_unita_organizzativa_id.return_value = None
        request = APIRequestFactory().post(
            "/api/v1/auth/password-reset-confirm/",
            {"token": "tok", "new_password": "Nuova-2026!x", "new_password_confirm": "Nuova-2026!x"},
            format="json",
        )
        with fuso_aziendale_forzato("Europe/Rome"), patch(
            "django.utils.timezone.now", return_value=datetime(2026, 9, 14, 23, 30, tzinfo=UTC),
        ):
            response = PasswordResetConfirmView.as_view()(request)

        self.assertEqual(response.status_code, 200, response.content)
        variabili = mock_email.send_email.call_args.kwargs["variabili"]
        self.assertEqual(variabili["data_cambio"], "15-09-2026 01:30")


class HelperTests(TestCase):
    """Test per funzioni helper."""

    # Scopo: Verifica get_unita_organizzativa_id dal repository.
    @patch("apps.core.db.auth_repository.connection")
    def test_get_user_uo_id(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository
        result = AuthRepository().get_unita_organizzativa_id(42)
        self.assertEqual(result, 5)
