# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per EmailOutboxService — mock DB,
#        compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PrepareDraftTests.test_prepare_draft_creates_outbox
2) PrepareDraftTests.test_prepare_draft_template_not_found
3) UpdateDraftTests.test_update_draft_modifies_fields
4) UpdateDraftTests.test_update_non_draft_raises
5) ConfirmAndSendTests.test_confirm_and_send_happy_path
6) ConfirmAndSendTests.test_confirm_non_draft_raises
7) CancelDraftTests.test_cancel_draft_happy_path
8) AttachmentTests.test_add_attachment_valid
9) AttachmentTests.test_add_attachment_invalid_mime
10) AttachmentTests.test_remove_attachment
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.email_outbox_service import EmailOutboxService
from apps.core.services.service_errors import ServiceError

_REPO = "apps.core.services.email_outbox_service.EmailRepository"
_DISPATCH = "apps.core.services.email_outbox_service.EmailDispatchService"

_MOCK_TEMPLATE = {
    "id": 1, "codice": "TEST", "oggetto": "Ciao {{nome}}",
    "corpo_html": "<p>Benvenuto {{nome}}</p>", "corpo_testo": "Benvenuto {{nome}}",
    "variabili_disponibili": ["nome"], "lingua": "it",
}

_MOCK_ACCOUNT = {
    "id": 1, "codice": "SISTEMA", "smtp_host": "",
    "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
    "smtp_username": "", "smtp_password_encrypted": "",
    "email_from": "test@example.com", "email_reply_to": None,
}

_MOCK_OUTBOX_DRAFT = {
    "id": 10, "stato": "DRAFT", "destinatario": "dest@test.com",
    "oggetto": "Ciao Mario", "corpo_html": "<p>Benvenuto Mario</p>",
    "corpo_testo": "Benvenuto Mario", "destinatari_cc": None,
    "email_account_id": 1, "email_template_id": 1,
    "ambito": "SISTEMA", "unita_organizzativa_id": None,
    "pratica_id": None, "auth_user_id": None,
    "creato_da_user_id": 1, "contesto_json": {"nome": "Mario"},
    "allegati": [],
}


class PrepareDraftTests(TestCase):

    # Scopo: Verifica che prepare_draft crei una bozza con corpo renderizzato.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_prepare_draft_creates_outbox(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        dispatch = MockDispatch.return_value
        repo.create_outbox.return_value = 10
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        # resolve_and_render ritorna (template, account, oggetto, corpo_html, corpo_testo)
        dispatch.resolve_and_render.return_value = (
            _MOCK_TEMPLATE, _MOCK_ACCOUNT,
            "Ciao Mario", "<p>Benvenuto Mario</p>", "Benvenuto Mario",
        )

        service = EmailOutboxService()
        result = service.prepare_draft(
            codice_template="TEST",
            destinatario="dest@test.com",
            variabili={"nome": "Mario"},
            # ⛔ `ambito` non ha piu' un default (2026-09-05): su quella colonna
            #    il database decide chi puo' leggere, e un valore di ripiego non
            #    puo' fare da cancello.
            ambito="OPERATORE",
            emittente_fiscale_id=7,
        )

        self.assertEqual(result["id"], 10)
        repo.create_outbox.assert_called_once()
        dispatch.resolve_and_render.assert_called_once()
        # ⭐ L'azienda arriva fino all'INSERT. Senza, la riga non sarebbe di
        #    nessuno: il CHECK del database la rifiuta, e la policy RLS non
        #    avrebbe su cosa filtrare.
        kwargs = repo.create_outbox.call_args.kwargs
        self.assertEqual(kwargs["ambito"], "OPERATORE")
        self.assertEqual(kwargs["emittente_fiscale_id"], 7)

    # ⛔ Il contratto: chi crea una bozza DEVE dire di che cosa e'. Il test
    #    guarda la FIRMA e non una chiamata, perche' e' li' che il default
    #    tornerebbe — reintrodurlo non romperebbe nessuna chiamata esistente, e
    #    passerebbe inosservato.
    def test_ambito_non_ha_un_default(self):
        import inspect

        firma = inspect.signature(EmailOutboxService.prepare_draft)
        self.assertIs(
            firma.parameters["ambito"].default, inspect.Parameter.empty,
            "`ambito` ha di nuovo un default: «non dichiarato» e «di sistema» "
            "tornerebbero a essere lo stesso valore, e la policy di lettura "
            "classificherebbe come segreta ogni bozza a cui manca un campo.",
        )

    # Scopo: Verifica che template non trovato lanci ServiceError.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_prepare_draft_template_not_found(self, MockRepo, MockDispatch):
        dispatch = MockDispatch.return_value
        # resolve_and_render lancia ServiceError se template non trovato
        dispatch.resolve_and_render.side_effect = ServiceError(
            code="E_OUTBOX", message="Template 'INESISTENTE' non trovato.",
        )

        service = EmailOutboxService()
        with self.assertRaises(ServiceError):
            service.prepare_draft(
                codice_template="INESISTENTE",
                destinatario="dest@test.com",
                variabili={},
                ambito="SISTEMA",
            )


class UpdateDraftTests(TestCase):

    # Scopo: Verifica modifica campi di una bozza DRAFT.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_update_draft_modifies_fields(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        repo.update_outbox.return_value = True
        # Mock _OUTBOX_UPDATE_COLS referenziato dal service
        MockRepo._OUTBOX_UPDATE_COLS = frozenset({"oggetto", "corpo_html", "corpo_testo", "destinatario", "destinatari_cc"})

        service = EmailOutboxService()
        service.update_draft(10, oggetto="Nuovo oggetto")

        repo.update_outbox.assert_called_once()

    # Scopo: Verifica che modificare una bozza non-DRAFT lanci errore.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_update_non_draft_raises(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = {**_MOCK_OUTBOX_DRAFT, "stato": "SENT"}

        service = EmailOutboxService()
        with self.assertRaises(ServiceError):
            service.update_draft(10, oggetto="Modifica")


class ConfirmAndSendTests(TestCase):

    # Scopo: Verifica il flusso completo DRAFT → READY → SENT con log creato.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_confirm_and_send_happy_path(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        dispatch = MockDispatch.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        repo.resolve_account.return_value = _MOCK_ACCOUNT
        repo.update_outbox_stato.return_value = True
        repo.update_log_outbox_link.return_value = None
        repo.copy_allegati_to_log.return_value = 0
        # send_raw ritorna (log_id, success)
        dispatch.send_raw.return_value = (99, True)

        service = EmailOutboxService()
        service.confirm_and_send(10)

        # Verifica send_raw chiamato con dati dalla bozza
        dispatch.send_raw.assert_called_once()
        # Verifica outbox aggiornato: prima READY poi SENT
        calls = repo.update_outbox_stato.call_args_list
        self.assertEqual(calls[0][0], (10, "READY"))
        self.assertEqual(calls[1][0][1], "SENT")

    # Scopo: Verifica che conferma di bozza non-DRAFT lanci errore.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_confirm_non_draft_raises(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = {**_MOCK_OUTBOX_DRAFT, "stato": "CANCELLED"}

        service = EmailOutboxService()
        with self.assertRaises(ServiceError):
            service.confirm_and_send(10)


class CancelDraftTests(TestCase):

    # Scopo: Verifica annullamento bozza DRAFT → CANCELLED.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_cancel_draft_happy_path(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        repo.update_outbox_stato.return_value = True

        service = EmailOutboxService()
        service.cancel_draft(10)

        repo.update_outbox_stato.assert_called_once_with(10, "CANCELLED")


class AttachmentTests(TestCase):

    # Scopo: Verifica upload allegato con MIME valido.
    @patch("apps.core.services.email_outbox_service._get_max_count", return_value=10)
    @patch("apps.core.services.email_outbox_service._get_max_size_bytes", return_value=10 * 1024 * 1024)
    @patch("apps.core.services.email_outbox_service._get_attachments_root", return_value="/tmp/test_attachments")
    @patch("apps.core.services.email_outbox_service.os.makedirs")
    @patch("builtins.open", create=True)
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_add_attachment_valid(self, MockRepo, MockDispatch, mock_open, mock_makedirs, mock_root, mock_size, mock_count):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        repo.create_allegato.return_value = 1
        repo.get_allegato.return_value = {"id": 1, "nome_file": "test.pdf"}
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        service = EmailOutboxService()
        result = service.add_attachment(
            outbox_id=10,
            file_name="test.pdf",
            file_content=b"PDF content",
            mime_type="application/pdf",
        )

        self.assertEqual(result["id"], 1)
        repo.create_allegato.assert_called_once()

    # Scopo: Verifica che MIME non consentito lanci errore.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_add_attachment_invalid_mime(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT

        service = EmailOutboxService()
        with self.assertRaises(ServiceError):
            service.add_attachment(
                outbox_id=10,
                file_name="virus.exe",
                file_content=b"EXE content",
                mime_type="application/x-msdownload",
            )

    # Scopo: Verifica rimozione allegato.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_remove_attachment(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.delete_allegato.return_value = "/some/path.pdf"

        service = EmailOutboxService()
        result = service.remove_attachment(1)
        self.assertTrue(result)
        repo.delete_allegato.assert_called_once_with(1)
