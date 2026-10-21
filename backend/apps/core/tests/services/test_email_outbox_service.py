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
11) ConfirmAndSendTests.test_la_mail_resta_dell_autore_e_dell_azienda_della_bozza
12) CancelDraftTests.test_gli_allegati_si_tolgono_prima_di_annullare
13) AttachmentTests.test_su_una_mail_non_in_bozza_risponde_col_codice_del_db
14) DeleteFileTests.test_un_percorso_fuori_radice_non_si_cancella
15) DeleteFileTests.test_riga_rifiutata_toglie_il_file_scritto
16) UpdateDraftTests.test_update_draft_chiave_estranea_rifiutata
17) UpdateDraftTests.test_update_draft_cc_non_lista_rifiutato
18) ConfirmAndSendTests.test_senza_account_la_bozza_resta_draft
19) CodiciNonTrovatoEStatoTests.test_bozza_inesistente_e_404_per_ogni_verbo
20) CodiciNonTrovatoEStatoTests.test_mail_non_in_bozza_e_409_per_i_tre_verbi
21) CodiciR7Tests.test_mail_piena_e_409_e_non_scrive_il_file
22) CodiciR7Tests.test_percorso_fuori_radice_e_500
23) CodiciR7Tests.test_template_non_configurato_e_500
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.email_outbox_service import EmailOutboxService, _delete_file
from apps.core.services.email_service import CANALE_CONSOLE, CANALE_SMTP
from apps.core.services.service_errors import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry

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
    "creato_da_user_id": 1, "emittente_fiscale_id": None,
    "contesto_json": {"nome": "Mario"},
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
            code="E_EMAIL_TEMPLATE_NON_CONFIGURATO",
            message="Nessun template email configurato per questo invio.",
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

        service = EmailOutboxService()
        service.update_draft(10, oggetto="Nuovo oggetto", destinatari_cc=["a@b.it"])

        repo.update_outbox.assert_called_once_with(
            10, oggetto="Nuovo oggetto", destinatari_cc=["a@b.it"],
        )

    # Scopo: ⛔ Una chiave estranea e' un 400 `E_OUTBOX`, non uno scarto
    #        silenzioso (2026-09-26): il repository non viene toccato.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_update_draft_chiave_estranea_rifiutata(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT

        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().update_draft(10, oggetto="X", stato="SENT")
        self.assertEqual(ctx.exception.code, "E_OUTBOX")
        self.assertIn("stato", ctx.exception.detail)
        repo.update_outbox.assert_not_called()
        # Anche `outbox_id` nel corpo e' una chiave estranea: prima era un
        # `TypeError` (500), perche' collideva col parametro del metodo.
        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().update_draft(10, outbox_id=11)
        self.assertEqual(ctx.exception.code, "E_OUTBOX")
        repo.update_outbox.assert_not_called()

    # Scopo: `destinatari_cc` non lista di stringhe: 400, non il 500 del cast
    #        `text[]` sul DB.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_update_draft_cc_non_lista_rifiutato(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT

        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().update_draft(10, destinatari_cc="a@b.it")
        self.assertEqual(ctx.exception.code, "E_OUTBOX")
        repo.update_outbox.assert_not_called()

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
        dispatch.account_di_invio.return_value = _MOCK_ACCOUNT
        repo.update_outbox_stato.return_value = True
        repo.update_log_outbox_link.return_value = None
        repo.copy_allegati_to_log.return_value = 0
        # send_raw ritorna (log_id, success)
        dispatch.send_raw.return_value = (99, True)
        # ⚠️ DICHIARATO e non lasciato al mock: dal 2026-09-11 l'esito della
        #    bozza dipende dal CANALE, e con un `MagicMock` qualunque il
        #    confronto con `CANALE_CONSOLE` e' falso **per caso** — cioe' questo
        #    test resterebbe verde anche se il ramo si invertisse.
        dispatch.canale_invio.return_value = CANALE_SMTP

        service = EmailOutboxService()
        service.confirm_and_send(10)

        # Verifica send_raw chiamato con dati dalla bozza
        dispatch.send_raw.assert_called_once()
        # Verifica outbox aggiornato: prima READY poi SENT
        calls = repo.update_outbox_stato.call_args_list
        self.assertEqual(calls[0][0], (10, "READY"))
        self.assertEqual(calls[1][0][1], "SENT")

    # Scopo: ⭐ In console mode la bozza NON e' «inviata».
    # ⛔ `send_raw` torna `True` anche quando la mail e' stata solo stampata:
    #    prendere quel booleano per una consegna scriveva `SENT` sull'outbox —
    #    la stessa bugia dell'`email_log`, una tabella piu' in la', e le due
    #    righe sono legate da `email_log_id` (brief §7.1).
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_in_console_mode_la_bozza_e_simulata(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        dispatch = MockDispatch.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        dispatch.account_di_invio.return_value = _MOCK_ACCOUNT
        repo.update_outbox_stato.return_value = True
        repo.copy_allegati_to_log.return_value = 0
        dispatch.send_raw.return_value = (99, True)
        dispatch.canale_invio.return_value = CANALE_CONSOLE

        EmailOutboxService().confirm_and_send(10)

        finale = repo.update_outbox_stato.call_args_list[1]
        self.assertEqual(finale[0][1], "SIMULATA")
        # ⛔ E nessuna data di consegna su una consegna che non c'e' stata.
        self.assertNotIn("inviato_at", finale[1])

    # Scopo: ⭐ La mail spedita porta l'AUTORE e l'AZIENDA della bozza, e i
    #        suoi allegati (brief-db-email-visibilita-per-ambito D-5, §8.4.2).
    # ⛔ L'autore e' `creato_da_user_id` della bozza, non chi conferma: un
    #    super admin che spedisce la bozza di un altro non ne diventa l'autore.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_la_mail_resta_dell_autore_e_dell_azienda_della_bozza(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        dispatch = MockDispatch.return_value
        allegati = [{"id": 5, "nome_file": "a.pdf", "mime_type": "application/pdf", "file_path": "x/a.pdf"}]
        repo.get_outbox.return_value = {
            **_MOCK_OUTBOX_DRAFT, "ambito": "OPERATORE", "creato_da_user_id": 42,
            "emittente_fiscale_id": 7, "allegati": allegati,
        }
        dispatch.account_di_invio.return_value = _MOCK_ACCOUNT
        dispatch.send_raw.return_value = (99, True)
        dispatch.canale_invio.return_value = CANALE_SMTP

        EmailOutboxService().confirm_and_send(10)

        kwargs = dispatch.send_raw.call_args.kwargs
        self.assertEqual(kwargs["creato_da_user_id"], 42)
        self.assertEqual(kwargs["emittente_fiscale_id"], 7)
        self.assertEqual(kwargs["allegati"], allegati)

    # Scopo: ⭐ Senza account email la bozza RESTA DRAFT (F-1, 2026-09-28).
    # ⛔ READY si committa subito e `cancel_draft` accetta solo DRAFT: con
    #    l'account cercato dopo READY la bozza restava bloccata, ne' rinviabile
    #    ne' annullabile. Il rifiuto deve arrivare prima di toccare lo stato.
    # ⭐ Il dispatcher qui e' VERO (finto solo il suo repository): si prova la
    #    regola di `account_di_invio`, non un rifiuto fabbricato dal mock.
    @patch("apps.core.services.email_service.EmailRepository")
    @patch(_REPO)
    def test_senza_account_la_bozza_resta_draft(self, MockRepo, MockDispatchRepo):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        MockDispatchRepo.return_value.resolve_account.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().confirm_and_send(10)

        # Manca un pezzo di configurazione: 500, non un dato errato (R-3).
        self.assertEqual(ctx.exception.code, "E_EMAIL_ACCOUNT_NON_CONFIGURATO")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 500)
        repo.update_outbox_stato.assert_not_called()
        MockDispatchRepo.return_value.insert_log.assert_not_called()

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

    # Scopo: ⛔ Le righe degli allegati si tolgono PRIMA di scrivere
    #        `CANCELLED`: dopo, il database non le lascia piu' toccare
    #        (`E_EMAIL_ALLEGATO_NON_BOZZA`). I file si cancellano dopo il commit.
    @patch("apps.core.services.email_outbox_service._delete_file")
    @patch("apps.core.services.email_outbox_service.transaction")
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_gli_allegati_si_tolgono_prima_di_annullare(self, MockRepo, MockDispatch, mock_tx, mock_delete):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        ordine: list[str] = []

        def _togli_righe(*_a):
            ordine.append("righe")
            return ["x/a.pdf"]

        repo.delete_allegati_by_outbox.side_effect = _togli_righe
        repo.update_outbox_stato.side_effect = lambda *a, **k: ordine.append("stato")
        dopo_il_commit = []
        mock_tx.on_commit.side_effect = dopo_il_commit.append

        EmailOutboxService().cancel_draft(10)

        self.assertEqual(ordine, ["righe", "stato"])
        mock_delete.assert_not_called()
        for callback in dopo_il_commit:
            callback()
        mock_delete.assert_called_once_with("x/a.pdf")


class AttachmentTests(TestCase):

    # Scopo: Verifica upload allegato con MIME valido.
    @patch("apps.core.services.email_outbox_service._get_max_count", return_value=10)
    @patch("apps.core.services.email_outbox_service._get_max_size_bytes", return_value=10 * 1024 * 1024)
    @patch("apps.core.services.email_outbox_service.radice_allegati", return_value="/tmp/test_attachments")
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

    # Scopo: «Solo in bozza» e' una regola del database: il pre-check che la
    #        dice prima di scrivere il file usa il SUO codice, non `E_OUTBOX`.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_su_una_mail_non_in_bozza_risponde_col_codice_del_db(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = {**_MOCK_OUTBOX_DRAFT, "stato": "SENT"}

        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().add_attachment(
                outbox_id=10, file_name="a.pdf", file_content=b"x", mime_type="application/pdf",
            )
        self.assertEqual(ctx.exception.code, "E_EMAIL_ALLEGATO_NON_BOZZA")
        repo.create_allegato.assert_not_called()

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


class DeleteFileTests(TestCase):

    # Scopo: ⛔ Un `file_path` che esce dalla radice (assoluto o con `..`) non
    #        si cancella: con un `os.path.join` nudo un path assoluto scartava
    #        la radice e toglieva un file qualunque.
    @patch("apps.core.services.email_outbox_service.os.remove")
    def test_un_percorso_fuori_radice_non_si_cancella(self, mock_remove):
        with tempfile.TemporaryDirectory() as radice, \
                patch("apps.core.services.email_allegati_storage.radice_allegati", return_value=radice):
            _delete_file("/etc/passwd")
            _delete_file("../fuori.pdf")
            mock_remove.assert_not_called()

            _delete_file("2026/09/dentro.pdf")
            mock_remove.assert_called_once_with(os.path.join(radice, "2026", "09", "dentro.pdf"))

    # Scopo: ⚠️ Se il database rifiuta la riga dell'allegato, il file appena
    #        scritto su disco si toglie e l'errore risale.
    @patch("apps.core.services.email_outbox_service._delete_file")
    @patch("apps.core.services.email_outbox_service._get_max_count", return_value=10)
    @patch("apps.core.services.email_outbox_service._get_max_size_bytes", return_value=10 * 1024 * 1024)
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_riga_rifiutata_toglie_il_file_scritto(self, MockRepo, MockDispatch, _size, _count, mock_delete):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = _MOCK_OUTBOX_DRAFT
        repo.create_allegato.side_effect = ServiceError(code="E_EMAIL_ALLEGATO_NON_BOZZA", message="x")
        with tempfile.TemporaryDirectory() as radice, \
                patch("apps.core.services.email_outbox_service.radice_allegati", return_value=radice):
            with self.assertRaises(ServiceError):
                EmailOutboxService().add_attachment(
                    outbox_id=10, file_name="a.pdf", file_content=b"x", mime_type="application/pdf",
                )
        mock_delete.assert_called_once()
        self.assertTrue(mock_delete.call_args.args[0].endswith(".pdf"))


# brief-db-codici-non-trovato-email-e-permessi §2 e §4: le condizioni che
# `E_OUTBOX` accumulava escono col loro codice, e lo status lo dice la classe.
class CodiciNonTrovatoEStatoTests(TestCase):

    # Scopo: Bozza inesistente (o fuori perimetro RLS: il repository risponde
    #        None uguale) → 404 `E_EMAIL_BOZZA_NOT_FOUND` da ogni verbo e dalla
    #        lettura: la sede e' una sola, `get_bozza`.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_bozza_inesistente_e_404_per_ogni_verbo(self, MockRepo, MockDispatch):
        MockRepo.return_value.get_outbox.return_value = None
        service = EmailOutboxService()
        verbi = {
            "get_bozza": lambda: service.get_bozza(10),
            "update_draft": lambda: service.update_draft(10, oggetto="x"),
            "confirm_and_send": lambda: service.confirm_and_send(10),
            "cancel_draft": lambda: service.cancel_draft(10),
            "add_attachment": lambda: service.add_attachment(
                outbox_id=10, file_name="a.pdf", file_content=b"x",
                mime_type="application/pdf",
            ),
        }
        for nome, chiama in verbi.items():
            with self.subTest(verbo=nome):
                with self.assertRaises(ServiceError) as ctx:
                    chiama()
                self.assertEqual(ctx.exception.code, "E_EMAIL_BOZZA_NOT_FOUND")
                self.assertEqual(
                    ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404,
                )

    # Scopo: Mail che non e' piu' in bozza → 409 `E_EMAIL_NON_BOZZA` da
    #        modifica, invio e annullo, prima di scrivere qualunque cosa.
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_mail_non_in_bozza_e_409_per_i_tre_verbi(self, MockRepo, MockDispatch):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = {**_MOCK_OUTBOX_DRAFT, "stato": "SENT"}
        service = EmailOutboxService()
        verbi = {
            "update_draft": lambda: service.update_draft(10, oggetto="x"),
            "confirm_and_send": lambda: service.confirm_and_send(10),
            "cancel_draft": lambda: service.cancel_draft(10),
        }
        for nome, chiama in verbi.items():
            with self.subTest(verbo=nome):
                with self.assertRaises(ServiceError) as ctx:
                    chiama()
                self.assertEqual(ctx.exception.code, "E_EMAIL_NON_BOZZA")
                self.assertEqual(
                    ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 409,
                )
        repo.update_outbox.assert_not_called()
        repo.update_outbox_stato.assert_not_called()


# brief-db-codici-non-trovato-email-e-permessi R-7 (§12.2): le tre condizioni
# rimaste sotto gli accumulatori escono col loro codice, e lo status lo dice
# la classe.
class CodiciR7Tests(TestCase):

    # Scopo: Mail che ha gia' il massimo degli allegati → 409
    #        `E_EMAIL_ALLEGATI_LIMITE` (e' uno stato, non un campo), prima di
    #        scrivere il file su storage.
    @patch("apps.core.services.email_outbox_service._get_max_count", return_value=1)
    @patch("apps.core.services.email_outbox_service._get_max_size_bytes", return_value=10 * 1024 * 1024)
    @patch("apps.core.services.email_outbox_service.os.makedirs")
    @patch(_DISPATCH)
    @patch(_REPO)
    def test_mail_piena_e_409_e_non_scrive_il_file(self, MockRepo, MockDispatch, mock_makedirs, _size, _count):
        repo = MockRepo.return_value
        repo.get_outbox.return_value = {**_MOCK_OUTBOX_DRAFT, "allegati": [{"id": 1}]}

        with self.assertRaises(ServiceError) as ctx:
            EmailOutboxService().add_attachment(
                outbox_id=10, file_name="a.pdf", file_content=b"x", mime_type="application/pdf",
            )
        self.assertEqual(ctx.exception.code, "E_EMAIL_ALLEGATI_LIMITE")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 409)
        mock_makedirs.assert_not_called()
        repo.create_allegato.assert_not_called()

    # Scopo: Un `file_path` che esce dalla radice (viene dal database, non da
    #        una persona) → 500 `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO`.
    def test_percorso_fuori_radice_e_500(self):
        from apps.core.services.email_allegati_storage import percorso_allegato

        with tempfile.TemporaryDirectory() as radice, \
                patch("apps.core.services.email_allegati_storage.radice_allegati", return_value=radice):
            with self.assertRaises(ServiceError) as ctx:
                percorso_allegato("../fuori.pdf")
        self.assertEqual(ctx.exception.code, "E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 500)

    # Scopo: Nessun template per l'invio, dopo il ripiego → 500
    #        `E_EMAIL_TEMPLATE_NON_CONFIGURATO`, sia dalla preparazione della
    #        bozza sia da una mail di sistema: e' la stessa risoluzione.
    @patch("apps.core.services.email_service.EmailRepository")
    def test_template_non_configurato_e_500(self, MockDispatchRepo):
        from apps.core.services.email_service import EmailDispatchService

        MockDispatchRepo.return_value.resolve_template.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            EmailDispatchService().resolve_and_render(codice_template="INESISTENTE", variabili={})
        self.assertEqual(ctx.exception.code, "E_EMAIL_TEMPLATE_NON_CONFIGURATO")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 500)
        MockDispatchRepo.return_value.resolve_account.assert_not_called()
