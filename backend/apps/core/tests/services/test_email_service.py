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

⭐ SmtpNonConfiguratoTests — il canale a TRE esiti (2026-09-11). I test 1..10
   coprono il console mode con `DEBUG = True`, cioe' lo sviluppo dichiarato:
   nessuno copriva l'ALTRO caso che ci finiva dentro — un account rimasto col
   placeholder su un host con `DEBUG = False` — ed e' il difetto per cui questa
   classe esiste.
11) test_il_canale_distingue_i_tre_casi
12) test_col_placeholder_fuori_da_debug_non_e_console_mode
13) test_una_mail_non_spedita_si_registra_FAILED_col_motivo
14) test_la_mail_non_spedita_non_viene_nemmeno_stampata
15) test_il_test_connessione_non_risponde_OK_a_chi_non_puo_spedire
16) test_il_rilancio_non_ritenta_contro_un_account_non_configurato
17) test_smtp_non_configurato_riconosce_i_tre_host
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.email_service import (
    CANALE_CONSOLE,
    CANALE_NON_CONFIGURATO,
    CANALE_SMTP,
    SMTP_PLACEHOLDER_HOST,
    EmailDispatchService,
    smtp_non_configurato,
)
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

def _account(host: str, *, codice: str = "SISTEMA") -> dict:
    return {
        "id": 1, "codice": codice, "smtp_host": host,
        "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
        "smtp_username": "", "smtp_password_encrypted": "x",
        "email_from": "test@example.com", "email_reply_to": None,
    }


class SmtpNonConfiguratoTests(TestCase):
    """⭐ Un account che NON puo' spedire non si legge come uno che ha spedito.

    ⛔ Il difetto che questi test presidiano e' costato una diagnosi sbagliata il
    2026-09-10: su un host con `DEBUG = False` e `smtp_host = smtp.example.com`
    il digest dei presidi risultava `SENT`, il pulsante «prova connessione»
    rispondeva OK, e la mail non era partita. Nessun test copriva quel ramo —
    tutti quelli sopra girano con `DEBUG = True`, dove il comportamento e' voluto.
    """

    # 11. La matrice: due variabili, tre esiti. ⚠️ Il caso che mancava e' l'ultima
    #     riga — l'unico in cui non si stampa e non si spedisce.
    @patch(_SETTINGS)
    def test_il_canale_distingue_i_tre_casi(self, mock_settings):
        service = EmailDispatchService.__new__(EmailDispatchService)
        casi = [
            (True, "smtp.gmail.com", CANALE_CONSOLE),
            (True, SMTP_PLACEHOLDER_HOST, CANALE_CONSOLE),
            (False, "smtp.gmail.com", CANALE_SMTP),
            (False, SMTP_PLACEHOLDER_HOST, CANALE_NON_CONFIGURATO),
            (False, "", CANALE_NON_CONFIGURATO),
        ]
        for debug, host, atteso in casi:
            with self.subTest(debug=debug, host=host):
                mock_settings.DEBUG = debug
                self.assertEqual(service.canale_invio(_account(host)), atteso)

    # 12. Il nome storico segue il canale, e su questo caso cambia risposta.
    @patch(_SETTINGS)
    def test_col_placeholder_fuori_da_debug_non_e_console_mode(self, mock_settings):
        mock_settings.DEBUG = False
        service = EmailDispatchService.__new__(EmailDispatchService)
        self.assertFalse(
            service.is_console_mode(_account(SMTP_PLACEHOLDER_HOST)),
            "col placeholder fuori da DEBUG rispondeva console mode, e da li' "
            "usciva un SENT su una mail mai partita.",
        )

    # 13. ⛔ IL CUORE: lo stato scritto e' `FAILED`, non `SENT`, e porta il motivo.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_una_mail_non_spedita_si_registra_FAILED_col_motivo(self, MockRepo, mock_settings):
        mock_settings.DEBUG = False
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {
            "id": 1, "codice": "TEST", "oggetto": "Ciao",
            "corpo_html": "<p>x</p>", "corpo_testo": None,
            "variabili_disponibili": [], "lingua": "it",
        }
        repo.resolve_account.return_value = _account(SMTP_PLACEHOLDER_HOST)
        repo.insert_log.return_value = 42

        log_id, success = EmailDispatchService().send_email(
            ambito="SISTEMA", codice_template="TEST",
            destinatario="dest@example.com", variabili={},
        )

        self.assertEqual(log_id, 42)
        self.assertFalse(success, "una mail non spedita non e' un successo")
        stato = repo.update_log_stato.call_args[0][1]
        self.assertEqual(stato, "FAILED")
        motivo = repo.update_log_stato.call_args[1]["errore"]
        # ⚠️ Il motivo deve dire DOVE si rimedia: chi lo legge sta guardando il
        #    giornale delle email, non il codice.
        self.assertIn(SMTP_PLACEHOLDER_HOST, motivo)
        self.assertIn("Email accounts", motivo)

    # 14. E non finisce nemmeno nel journal: stamparla direbbe «inviata» a chi
    #     legge i log del servizio.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_la_mail_non_spedita_non_viene_nemmeno_stampata(self, MockRepo, mock_settings):
        mock_settings.DEBUG = False
        repo = MockRepo.return_value
        repo.resolve_template.return_value = {
            "id": 1, "codice": "TEST", "oggetto": "Ciao",
            "corpo_html": "<p>x</p>", "corpo_testo": None,
            "variabili_disponibili": [], "lingua": "it",
        }
        repo.resolve_account.return_value = _account("")
        repo.insert_log.return_value = 7

        service = EmailDispatchService()
        with patch.object(service, "_send_console") as console:
            service.send_email(
                ambito="SISTEMA", codice_template="TEST",
                destinatario="dest@example.com", variabili={},
            )
        console.assert_not_called()

    # 15. ⛔ Il verde che ha ingannato una persona: «test connessione OK» su un
    #     account che non poteva spedire niente.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_il_test_connessione_non_risponde_OK_a_chi_non_puo_spedire(self, MockRepo, mock_settings):
        mock_settings.DEBUG = False
        MockRepo.return_value.get_account_with_password.return_value = _account(
            SMTP_PLACEHOLDER_HOST,
        )
        esito = EmailDispatchService().test_connection(1)
        self.assertFalse(esito["success"])
        self.assertIn("non configurato", esito["message"])
        # ⛔ E non racconta un invio che non c'e' stato: questo messaggio finisce
        #    in `meta.last_test_message` e lo legge un amministratore nel drawer.
        self.assertNotIn("spedita", esito["message"])
        self.assertIn("Email accounts", esito["message"])

    # 16. Ritentare contro un host che non esiste non e' un tentativo.
    @patch(_SETTINGS)
    @patch(_REPO)
    def test_il_rilancio_non_ritenta_contro_un_account_non_configurato(self, MockRepo, mock_settings):
        mock_settings.DEBUG = False
        repo = MockRepo.return_value
        service = EmailDispatchService()
        with patch.object(service, "_send_smtp") as smtp:
            esito = service.retry_log_entry(
                99, _account(SMTP_PLACEHOLDER_HOST),
                {"ambito": "SISTEMA", "destinatario": "d@x.it", "oggetto": "o"},
            )
        self.assertFalse(esito)
        smtp.assert_not_called()
        self.assertEqual(repo.update_log_stato.call_args[0][1], "FAILED")

    # 17. Il predicato condiviso — quello che `email_views` riscriveva a mano.
    def test_smtp_non_configurato_riconosce_i_tre_host(self):
        self.assertTrue(smtp_non_configurato({"smtp_host": ""}))
        self.assertTrue(smtp_non_configurato({"smtp_host": None}))
        self.assertTrue(smtp_non_configurato({"smtp_host": f"  {SMTP_PLACEHOLDER_HOST} "}))
        self.assertFalse(smtp_non_configurato({"smtp_host": "smtp.gmail.com"}))
