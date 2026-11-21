# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
8b) TestConnectionTests.test_account_inesistente_e_404
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

⭐ AutoreEAllegatiTests — la mail che non e' di sistema, e i suoi file
   (brief-db-email-visibilita-per-ambito D-5 e §8.4.2, 2026-09-25).
18) test_send_raw_scrive_autore_ed_emittente_sul_log
19) test_la_mail_parte_con_gli_allegati
20) test_un_allegato_che_non_si_legge_ferma_l_invio
21) test_il_rilancio_rilegge_gli_allegati_dal_log

⭐ CredenzialiRifiutateTests — il rifiuto che il server nasconde chiudendo
   (2026-11-17). Gmail risponde 535 al primo metodo di autenticazione e chiude
   la connessione al secondo: `smtplib` lasciava uscire la chiusura, e il
   giornale e il drawer dicevano «Connection unexpectedly closed». Server SMTP
   FINTO su socket locale, che si comporta come Gmail: senza un server vero il
   difetto non si vede (un mock di `login` non attraversa `smtplib`).
22) test_il_test_connessione_dice_credenziali_rifiutate
23) test_l_invio_scrive_sul_log_credenziali_rifiutate
24) test_su_gmail_il_messaggio_indica_la_password_per_le_app
25) test_una_chiusura_senza_rifiuto_resta_una_chiusura

⭐ RilancioAccountTests — l'account segue l'invio (R5 del brief del seed, §16.16).
26) test_ogni_esito_del_rilancio_scrive_l_account
27) test_il_log_dell_invio_porta_l_account_che_spedisce
"""

import socket
import threading
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.email_service import (
    CANALE_CONSOLE,
    CANALE_NON_CONFIGURATO,
    CANALE_SMTP,
    SMTP_PLACEHOLDER_HOST,
    EmailDispatchService,
    descrivi_errore_smtp,
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
    @patch(_REPO, autospec=True)
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
        # ⭐ `SIMULATA` dal 2026-09-11: stampata a video, non consegnata. Questa
        #    riga asseriva `SENT`, ed era il difetto reso in un test.
        self.assertEqual(call_args[0][1], "SIMULATA")
        # ⛔ E `inviato_at` NON si passa: e' l'unica colonna che data una
        #    consegna: scriverla sposterebbe la bugia di una casella invece di
        #    toglierla (brief-db-stato-email-console-non-e-inviata §7.1).
        self.assertNotIn("inviato_at", call_args[1])

    # Scopo: Verifica che template non trovato lanci ServiceError.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_send_email_template_not_found_raises(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.resolve_template.return_value = None

        service = EmailDispatchService()
        with self.assertRaises(ServiceError) as ctx:
            service.send_email(
                ambito="SISTEMA",
                codice_template="INESISTENTE",
                destinatario="dest@example.com",
                variabili={},
            )
        # Manca la configurazione, come per l'account: 500 (R-7 di
        # brief-db-codici-non-trovato-email-e-permessi).
        self.assertEqual(ctx.exception.code, "E_EMAIL_TEMPLATE_NON_CONFIGURATO")

    # Scopo: Verifica che account non trovato lanci ServiceError.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
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
        with self.assertRaises(ServiceError) as ctx:
            service.send_email(
                ambito="SISTEMA",
                codice_template="TEST",
                destinatario="dest@example.com",
                variabili={},
            )
        # Manca la configurazione: 500, lo stesso codice dell'invio di una
        # bozza (brief-db-codici-non-trovato-email-e-permessi §12).
        self.assertEqual(ctx.exception.code, "E_EMAIL_ACCOUNT_NON_CONFIGURATO")

    # Scopo: Verifica che destinatari_cc venga propagato al log.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
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
    @patch(_REPO, autospec=True)
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

    # Scopo: Account inesistente → 404 col codice dell'account, non il 400
    #        generico `E_EMAIL`: l'id lo sceglie l'amministratore.
    @patch(_REPO, autospec=True)
    def test_account_inesistente_e_404(self, MockRepo):
        MockRepo.return_value.get_account_with_password.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            EmailDispatchService().test_connection(9)
        self.assertEqual(ctx.exception.code, "E_EMAIL_ACCOUNT_NOT_FOUND")


class ResolveTests(TestCase):

    # Scopo: Verifica che resolve_account venga chiamato con il reparto.
    @patch(_REPO, autospec=True)
    def test_resolve_account_fallback(self, MockRepo):
        repo = MockRepo.return_value
        repo.resolve_account.return_value = {"id": 1, "codice": "SISTEMA"}

        service = EmailDispatchService()
        service._repo.resolve_account(42)
        repo.resolve_account.assert_called_with(42)

    # Scopo: Verifica che resolve_template venga chiamato con tutti i parametri.
    @patch(_REPO, autospec=True)
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
    @patch(_REPO, autospec=True)
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
    @patch(_REPO, autospec=True)
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
    @patch(_REPO, autospec=True)
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
    @patch(_REPO, autospec=True)
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


class AutoreEAllegatiTests(TestCase):

    _ACCOUNT_SMTP = {
        "id": 1, "codice": "AZ", "smtp_host": "smtp.azienda.test",
        "smtp_port": 587, "smtp_use_tls": False, "smtp_use_ssl": False,
        "smtp_username": "u", "smtp_password_encrypted": "cifrata",
        "email_from": "da@azienda.test", "email_reply_to": None,
    }

    # Scopo: invia con SMTP finto e torna il messaggio consegnato al server.
    def _spedisci(self, service, allegati):
        with patch("apps.core.services.email_service.crypto_service.decrypt", return_value="pw"), \
                patch("apps.core.services.email_service.smtplib.SMTP") as smtp:
            esito = service._send_smtp(
                self._ACCOUNT_SMTP, "a@cliente.test", None, "Offerta",
                "<p>x</p>", "x", 99, "OPERATORE", allegati,
            )
        inviati = smtp.return_value.sendmail.call_args_list
        return esito, (inviati[0][0][2] if inviati else None)

    # 18. ⛔ Fuori da SISTEMA il log vuole l'azienda E l'autore: senza, il
    #     database rifiuta la riga (`chk_email_log_ambito_emittente`,
    #     `chk_email_log_operatore_creatore`). Fino al 2026-09-25 non arrivava
    #     nessuna delle due.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_send_raw_scrive_autore_ed_emittente_sul_log(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.insert_log.return_value = 5
        EmailDispatchService().send_raw(
            account=_account(""), destinatario="a@b.test", oggetto="o",
            corpo_html="<p>x</p>", ambito="OPERATORE",
            emittente_fiscale_id=7, creato_da_user_id=42,
        )
        kwargs = repo.insert_log.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 7)
        self.assertEqual(kwargs["creato_da_user_id"], 42)

    # 19. ⛔ Fino al 2026-09-25 la mail partiva SENZA gli allegati salvati.
    @patch(_REPO, autospec=True)
    def test_la_mail_parte_con_gli_allegati(self, MockRepo):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as radice, \
                patch("apps.core.services.email_allegati_storage.radice_allegati", return_value=radice):
            Path(radice, "a.pdf").write_bytes(b"%PDF-contenuto")
            esito, messaggio = self._spedisci(
                EmailDispatchService(),
                [{"nome_file": "offerta.pdf", "mime_type": "application/pdf", "file_path": "a.pdf"}],
            )
        self.assertTrue(esito)
        self.assertIn("multipart/mixed", messaggio)
        self.assertIn('filename="offerta.pdf"', messaggio)
        self.assertIn("application/pdf", messaggio)

    # 20. Un allegato che non si legge: la mail NON parte senza, e il log lo dice.
    @patch(_REPO, autospec=True)
    def test_un_allegato_che_non_si_legge_ferma_l_invio(self, MockRepo):
        import tempfile

        with tempfile.TemporaryDirectory() as radice, \
                patch("apps.core.services.email_allegati_storage.radice_allegati", return_value=radice):
            esito, messaggio = self._spedisci(
                EmailDispatchService(),
                [{"nome_file": "sparito.pdf", "mime_type": "application/pdf", "file_path": "sparito.pdf"}],
            )
        self.assertFalse(esito)
        self.assertIsNone(messaggio, "la mail e' partita senza l'allegato promesso")
        self.assertEqual(MockRepo.return_value.update_log_stato.call_args[0][1], "FAILED")

    # 21. Il rilancio di una mail fallita: gli allegati sono gia' agganciati al
    #     LOG, e da li' si rileggono.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_il_rilancio_rilegge_gli_allegati_dal_log(self, MockRepo, mock_settings):
        mock_settings.DEBUG = False
        repo = MockRepo.return_value
        allegati = [{"nome_file": "a.pdf", "mime_type": "application/pdf", "file_path": "a.pdf"}]
        repo.list_allegati_by_log.return_value = allegati
        service = EmailDispatchService()
        with patch.object(service, "_send_smtp", return_value=True) as smtp:
            service.retry_log_entry(
                99, self._ACCOUNT_SMTP,
                {"ambito": "OPERATORE", "destinatario": "d@x.it", "oggetto": "o"},
            )
        repo.list_allegati_by_log.assert_called_once_with(99)
        self.assertEqual(smtp.call_args[0][-1], allegati)


# Scopo: Un server SMTP minimo su 127.0.0.1, in un thread, che risponde come
#        Gmail a una password sbagliata: `535` ad AUTH PLAIN, chiusura ad
#        AUTH LOGIN. Con `rifiuta=False` chiude gia' al primo AUTH, senza
#        rifiuto: e' il caso di una caduta vera.
class _ServerSmtpFinto:

    def __init__(self, *, rifiuta: bool = True) -> None:
        self._rifiuta = rifiuta
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.porta = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._servi, daemon=True)
        self._thread.start()

    def _servi(self) -> None:
        conn, _ = self._sock.accept()
        with conn, conn.makefile("rb") as righe:
            conn.sendall(b"220 finto ESMTP\r\n")
            for riga in righe:
                comando = riga.decode().strip().upper()
                if comando.startswith(("EHLO", "HELO")):
                    conn.sendall(b"250-finto\r\n250 AUTH LOGIN PLAIN\r\n")
                elif comando.startswith("AUTH PLAIN") and self._rifiuta:
                    conn.sendall(
                        b"535-5.7.8 Username and Password not accepted.\r\n"
                        b"535 5.7.8 BadCredentials - gsmtp\r\n"
                    )
                else:
                    return  # chiude: AUTH LOGIN, o qualsiasi altra cosa

    def chiudi(self) -> None:
        self._thread.join(timeout=5)
        self._sock.close()


class CredenzialiRifiutateTests(TestCase):

    _RIFIUTO = "Credenziali SMTP rifiutate dal server (535 5.7.8 Username and Password not accepted."

    def _account(self, porta: int, host: str = "127.0.0.1") -> dict:
        return {
            "id": 1, "codice": "SISTEMA", "smtp_host": host, "smtp_port": porta,
            "smtp_use_tls": False, "smtp_use_ssl": False,
            "smtp_username": "u@azienda.test", "smtp_password_encrypted": "cifrata",
            "email_from": "u@azienda.test", "email_reply_to": None,
        }

    def _prova_connessione(self, server: _ServerSmtpFinto, MockRepo, mock_settings) -> str:
        mock_settings.DEBUG = False
        MockRepo.return_value.get_account_with_password.return_value = self._account(server.porta)
        with patch("apps.core.services.email_service.crypto_service.decrypt", return_value="pw"):
            esito = EmailDispatchService().test_connection(1)
        server.chiudi()
        self.assertFalse(esito["success"])
        return esito["message"]

    # 22. Il drawer: prima «Errore SMTP: Connection unexpectedly closed».
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_il_test_connessione_dice_credenziali_rifiutate(self, MockRepo, mock_settings):
        messaggio = self._prova_connessione(_ServerSmtpFinto(), MockRepo, mock_settings)
        self.assertTrue(messaggio.startswith(self._RIFIUTO), messaggio)
        self.assertNotIn("Connection unexpectedly closed", messaggio)

    # 23. Il giornale delle email: lo stesso rifiuto su `email_log.errore`.
    @patch(_REPO, autospec=True)
    def test_l_invio_scrive_sul_log_credenziali_rifiutate(self, MockRepo):
        server = _ServerSmtpFinto()
        with patch("apps.core.services.email_service.crypto_service.decrypt", return_value="pw"):
            esito = EmailDispatchService()._send_smtp(
                self._account(server.porta), "a@cliente.test", None, "o",
                "<p>x</p>", "x", 99, "SISTEMA",
            )
        server.chiudi()
        self.assertFalse(esito)
        kwargs = MockRepo.return_value.update_log_stato.call_args.kwargs
        self.assertTrue(kwargs["errore"].startswith(self._RIFIUTO), kwargs["errore"])

    # 24. Il suggerimento su Gmail c'e' solo su Gmail: altrove sarebbe rumore.
    def test_su_gmail_il_messaggio_indica_la_password_per_le_app(self):
        import smtplib
        exc = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted.")
        self.assertIn("password per le app", descrivi_errore_smtp(exc, self._account(587, "smtp.gmail.com")))
        self.assertNotIn("password per le app", descrivi_errore_smtp(exc, self._account(587, "smtp.azienda.test")))

    # 25. ⚠️ Il rimedio non trasforma ogni chiusura in «password sbagliata»:
    #     senza un rifiuto prima, la chiusura resta quello che e'.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_una_chiusura_senza_rifiuto_resta_una_chiusura(self, MockRepo, mock_settings):
        messaggio = self._prova_connessione(_ServerSmtpFinto(rifiuta=False), MockRepo, mock_settings)
        self.assertIn("Connection unexpectedly closed", messaggio)
        self.assertNotIn("Credenziali", messaggio)


class RilancioAccountTests(TestCase):
    """⭐ L'account segue l'invio (brief-db-seed-primo-impianto-non-si-riscrive
    §16.16, R5): ogni esito del rilancio scrive sul log l'account con cui la
    mail e' ripartita, che puo' non essere quello con cui era stata preparata.
    """

    # 26. I tre esiti del rilancio — non configurato, stampata, fallita —
    #     portano tutti l'account del tentativo.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_ogni_esito_del_rilancio_scrive_l_account(self, MockRepo, mock_settings):
        repo = MockRepo.return_value
        repo.list_allegati_by_log.return_value = []
        log = {"ambito": "SISTEMA", "destinatario": "d@x.it", "oggetto": "o",
               "corpo_inviato_html": "<p>x</p>"}
        casi = (
            ("non configurato", False, SMTP_PLACEHOLDER_HOST, "x", "FAILED"),
            ("stampata", True, "", "x", "SIMULATA"),
            ("senza password", False, "smtp.azienda.test", None, "FAILED"),
        )
        for nome, debug, host, password, stato in casi:
            with self.subTest(nome):
                repo.reset_mock()
                mock_settings.DEBUG = debug
                account = {**_account(host), "id": 7, "smtp_password_encrypted": password}
                EmailDispatchService().retry_log_entry(99, account, log)
                args, kwargs = repo.update_log_stato.call_args
                self.assertEqual(args[1], stato)
                self.assertEqual(kwargs["email_account_id"], 7)

    # 27. ⛔ Anche il primo invio: il log nasce con l'account che spedisce.
    #     Fino al 2026-11-20 `send_raw` lo riceveva anche come parametro a
    #     parte, e due fonti per lo stesso dato possono divergere.
    @patch(_SETTINGS)
    @patch(_REPO, autospec=True)
    def test_il_log_dell_invio_porta_l_account_che_spedisce(self, MockRepo, mock_settings):
        mock_settings.DEBUG = True
        repo = MockRepo.return_value
        repo.insert_log.return_value = 5
        EmailDispatchService().send_raw(
            account={**_account(""), "id": 7}, destinatario="a@b.test", oggetto="o",
            corpo_html="<p>x</p>", ambito="SISTEMA",
        )
        self.assertEqual(repo.insert_log.call_args.kwargs["email_account_id"], 7)
        self.assertEqual(repo.update_log_stato.call_args.kwargs["email_account_id"], 7)
