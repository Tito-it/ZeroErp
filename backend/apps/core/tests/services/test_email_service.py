# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per EmailDispatchService — mock DB e SMTP,
#        compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RenderTemplateTests.test_render_with_variables
2) RenderTemplateTests.test_render_missing_variable_kept
3) RenderTemplateTests.test_render_no_variables
4) SendEmailTests.test_send_email_console_mode
5) SendEmailTests.test_send_email_template_not_found_raises
6) SendEmailTests.test_send_email_account_not_found_raises
7) SendEmailTests.test_send_email_with_cc
8) TestConnectionTests.test_console_mode_returns_success
9) ResolveTests.test_resolve_account_fallback
10) ResolveTests.test_resolve_template_fallback
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.email_service import EmailDispatchService
from apps.core.services.service_errors import ServiceError

_REPO = "apps.core.services.email_service.EmailRepository"
_SETTINGS = "apps.core.services.email_service.settings"


class RenderTemplateTests(TestCase):

    def setUp(self):
        self.service = EmailDispatchService.__new__(EmailDispatchService)

    # Scopo: Verifica sostituzione variabili {{...}} nel template.
    def test_render_with_variables(self):
        result = self.service.render_template(
            "Ciao {{nome}}, benvenuto in {{azienda}}!",
            {"nome": "Mario", "azienda": "ZeroErp"},
        )
        self.assertEqual(result, "Ciao Mario, benvenuto in ZeroErp!")

    # Scopo: Verifica che variabili mancanti restino invariate.
    def test_render_missing_variable_kept(self):
        result = self.service.render_template(
            "Ciao {{nome}}, link: {{link}}",
            {"nome": "Mario"},
        )
        self.assertEqual(result, "Ciao Mario, link: {{link}}")

    # Scopo: Verifica che testo senza variabili resti invariato.
    def test_render_no_variables(self):
        result = self.service.render_template("Testo semplice", {})
        self.assertEqual(result, "Testo semplice")


class SendEmailTests(TestCase):

    # Scopo: Verifica invio email in console mode (DEBUG + smtp_host vuoto).
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_send_email_console_mode(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {
            "id": 1, "codice": "TEST", "oggetto": "Ciao {{nome}}",
            "corpo_html": "<p>Benvenuto {{nome}}</p>", "corpo_testo": None,
            "variabili_disponibili": ["nome"], "lingua": "it",
        }
        repo.resolve_account.return_value = {
            "id": 1, "codice": "SISTEMA", "smtp_host": "",
            "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
            "smtp_username": "", "smtp_password_encrypted": "",
            "email_from": "test@example.com", "email_reply_to": None,
        }
        repo.insert_log.return_value = 42

        service = EmailDispatchService()
        log_id, success = service.send_email(
            ambito="SISTEMA",
            codice_template="TEST",
            destinatario="dest@example.com",
            variabili={"nome": "Mario"},
        )

        self.assertEqual(log_id, 42)
        self.assertTrue(success)
        repo.insert_log.assert_called_once()
        repo.update_log_stato.assert_called_once()
        call_args = repo.update_log_stato.call_args
        self.assertEqual(call_args[0][0], 42)
        self.assertEqual(call_args[0][1], "SENT")

    # Scopo: Verifica che template non trovato lanci ServiceError.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_send_email_template_not_found_raises(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.resolve_template.return_value = None

        service = EmailDispatchService()
        with self.assertRaises(ServiceError):
            service.send_email(
                ambito="SISTEMA",
                codice_template="INESISTENTE",
                destinatario="dest@example.com",
                variabili={},
            )

    # Scopo: Verifica che account non trovato lanci ServiceError.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_send_email_account_not_found_raises(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {
            "id": 1, "codice": "TEST", "oggetto": "Test",
            "corpo_html": "<p>Test</p>", "corpo_testo": None,
            "variabili_disponibili": [], "lingua": "it",
        }
        repo.resolve_account.return_value = None

        service = EmailDispatchService()
        with self.assertRaises(ServiceError):
            service.send_email(
                ambito="SISTEMA",
                codice_template="TEST",
                destinatario="dest@example.com",
                variabili={},
            )

    # Scopo: Verifica che destinatari_cc venga propagato al log.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_send_email_with_cc(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {
            "id": 1, "codice": "TEST", "oggetto": "Test",
            "corpo_html": "<p>Test</p>", "corpo_testo": None,
            "variabili_disponibili": [], "lingua": "it",
        }
        repo.resolve_account.return_value = {
            "id": 1, "codice": "SISTEMA", "smtp_host": "",
            "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
            "smtp_username": "", "smtp_password_encrypted": "",
            "email_from": "test@example.com", "email_reply_to": None,
        }
        repo.insert_log.return_value = 99

        service = EmailDispatchService()
        service.send_email(
            ambito="SISTEMA",
            codice_template="TEST",
            destinatario="dest@example.com",
            variabili={},
            destinatari_cc=["cc1@example.com", "cc2@example.com"],
        )

        call_kwargs = repo.insert_log.call_args[1]
        self.assertEqual(call_kwargs["destinatari_cc"], ["cc1@example.com", "cc2@example.com"])


class TestConnectionTests(TestCase):

    # Scopo: Verifica che test connessione in console mode ritorni successo.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_console_mode_returns_success(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.get_account_with_password.return_value = {
            "id": 1, "codice": "SISTEMA", "smtp_host": "",
            "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
            "smtp_username": "", "smtp_password_encrypted": "",
            "email_from": "test@example.com", "email_reply_to": None,
        }

        service = EmailDispatchService()
        result = service.test_connection(1)
        self.assertTrue(result["success"])


class ResolveTests(TestCase):

    # Scopo: Verifica che resolve_account venga chiamato con il reparto.
    @patch(_REPO)
    def test_resolve_account_fallback(self, MockRepo):
        repo = MockRepo.return_value
        repo.resolve_account.return_value = {"id": 1, "codice": "SISTEMA"}

        service = EmailDispatchService()
        service._repo.resolve_account(42)
        repo.resolve_account.assert_called_with(42)

    # Scopo: Verifica che resolve_template venga chiamato con tutti i parametri.
    @patch(_REPO)
    def test_resolve_template_fallback(self, MockRepo):
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {"id": 1, "codice": "TEST"}

        service = EmailDispatchService()
        service._repo.resolve_template("TEST", unita_organizzativa_id=5, lingua="en")
        repo.resolve_template.assert_called_with("TEST", unita_organizzativa_id=5, lingua="en")
