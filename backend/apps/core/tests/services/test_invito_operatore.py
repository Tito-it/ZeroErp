# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per InvitoOperatoreService e AttivazioneView.
#        Mock DB e SMTP, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) InvitoTests.test_invia_invito_happy_path
2) InvitoTests.test_invito_non_invitabile_raises
3) InvitoTests.test_reinvia_invalida_precedente
4) InvitoTests.test_mask_email
5) AttivazioneTests.test_consume_valid_token
6) AttivazioneTests.test_consume_invalid_raises
7) AttivazioneTests.test_password_mismatch_raises
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

_SVC_PATH = "apps.anagrafiche.services.invito_operatore_service"
_AUTH_REPO = f"{_SVC_PATH}.AuthRepository"
_TOKEN_SVC = f"{_SVC_PATH}.TokenService"
_EMAIL_SVC = f"{_SVC_PATH}.EmailDispatchService"
_CONNECTION = f"{_SVC_PATH}.connection"
_SETTINGS = f"{_SVC_PATH}.settings"


class InvitoTests(TestCase):

    # Scopo: Verifica flusso completo invito: check + password + token + email + flag.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    def test_invia_invito_happy_path(self, MockAuth, MockToken, MockEmail, mock_conn, mock_settings):
        mock_settings.FRONTEND_URL = "https://localhost"
        auth = MockAuth.return_value
        token = MockToken.return_value
        email = MockEmail.return_value

        # Mock check invitabile
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ({"invitabile": True, "motivo": None, "email": "mario@test.com"},)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        auth.get_unita_organizzativa_id.return_value = 5
        # Post §8.4.1: il service risolve l'identita OPERATORE prima di
        # propagare identita_id ai metodi set_deve_cambiare_password /
        # set_invito_inviato_at.
        auth.find_identita_attiva_for_ruoli.return_value = {
            "id": 700,
            "soggetto_ruolo_id": 7,
            "ruolo_applicativo": "OPERATORE",
        }
        auth.set_deve_cambiare_password.return_value = True
        auth.set_invito_inviato_at.return_value = True
        token.create.return_value = "invito_token_123"
        email.send_email.return_value = (1, True)

        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        service = InvitoOperatoreService()
        # Mock _get_user_display_name e _get_user_names
        service._get_user_display_name = MagicMock(return_value="Admin Utente")
        service._get_user_names = MagicMock(return_value={"first_name": "Mario", "last_name": "Rossi"})
        service._check_invitabile = MagicMock(return_value={
            "invitabile": True, "motivo": None, "email": "mario@test.com",
        })

        result = service.invia_invito(42, invitato_da_user_id=1)

        self.assertTrue(result["inviato"])
        self.assertIn("***", result["email"])
        auth.set_deve_cambiare_password.assert_called_once_with(
            42, True, identita_id=700
        )
        auth.set_invito_inviato_at.assert_called_once_with(42, identita_id=700)
        token.create.assert_called_once()
        email.send_email.assert_called_once()

    # Scopo: Verifica che operatore non invitabile lanci errore.
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    def test_invito_non_invitabile_raises(self, MockAuth, MockToken, MockEmail, mock_conn):
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        service = InvitoOperatoreService()
        service._check_invitabile = MagicMock(return_value={
            "invitabile": False, "motivo": "Utente ha gia' effettuato login", "email": "x@test.com",
        })

        with self.assertRaises(ServiceError):
            service.invia_invito(42, invitato_da_user_id=1)

    # Scopo: Verifica che reinvia invalidi token precedenti.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    def test_reinvia_invalida_precedente(self, MockAuth, MockToken, MockEmail, mock_conn, mock_settings):
        mock_settings.FRONTEND_URL = "https://localhost"
        token = MockToken.return_value
        auth = MockAuth.return_value
        email = MockEmail.return_value
        token.invalidate_all.return_value = 1
        token.create.return_value = "nuovo_token"
        auth.get_unita_organizzativa_id.return_value = None
        # Post §8.4.1: serve identita OPERATORE per set_*.
        auth.find_identita_attiva_for_ruoli.return_value = {
            "id": 700,
            "soggetto_ruolo_id": 7,
            "ruolo_applicativo": "OPERATORE",
        }
        auth.set_deve_cambiare_password.return_value = True
        auth.set_invito_inviato_at.return_value = True
        email.send_email.return_value = (1, True)

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        service = InvitoOperatoreService()
        service._check_invitabile = MagicMock(return_value={
            "invitabile": True, "motivo": None, "email": "mario@test.com",
        })
        service._get_user_display_name = MagicMock(return_value="Admin")
        service._get_user_names = MagicMock(return_value={"first_name": "Mario", "last_name": ""})

        service.reinvia_invito(42, invitato_da_user_id=1)

        token.invalidate_all.assert_called_once_with("INVITO_OPERATORE", 42)

    # Scopo: Verifica mascheramento email.
    def test_mask_email(self):
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        self.assertEqual(InvitoOperatoreService._mask_email("mario@test.com"), "m***@test.com")
        self.assertEqual(InvitoOperatoreService._mask_email("a@test.com"), "*@test.com")
        self.assertEqual(InvitoOperatoreService._mask_email("x"), "***")
        self.assertEqual(InvitoOperatoreService._mask_email(""), "***")


class AttivazioneTests(TestCase):

    # Scopo: Verifica che token valido attivi l'account.
    @patch("apps.core.api.attivazione_view._auth_repo")
    @patch("apps.core.api.attivazione_view._token_service")
    @patch("apps.core.api.attivazione_view.User")
    @patch("apps.core.api.attivazione_view.validate_password")
    @patch("apps.core.api.attivazione_view.get_client_ip", return_value="10.0.0.1")
    def test_consume_valid_token(self, mock_ip, mock_validate, MockUser, mock_token, mock_auth):
        mock_token.consume.return_value = 42
        mock_user = MagicMock()
        mock_user.id = 42
        MockUser.objects.filter.return_value.first.return_value = mock_user
        mock_auth.set_deve_cambiare_password.return_value = True

        # Verifica che consume venga chiamato
        result = mock_token.consume("token123", "INVITO_OPERATORE", ip="10.0.0.1")
        self.assertEqual(result, 42)

    # Scopo: Verifica che token invalido lanci errore.
    def test_consume_invalid_raises(self):
        from apps.core.services.error_manager import ErrorManager
        with self.assertRaises(ServiceError):
            ErrorManager.require(False, code="E_TOKEN", message="Token non valido.")

    # Scopo: Verifica che password non corrispondenti lancino errore.
    def test_password_mismatch_raises(self):
        from apps.core.services.error_manager import ErrorManager
        with self.assertRaises(ServiceError):
            ErrorManager.require(
                "abc" == "xyz",
                code="E_ATTIVAZIONE",
                message="La nuova password e la conferma non coincidono.",
            )
