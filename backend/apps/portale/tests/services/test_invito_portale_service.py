# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per InvitoPortaleService.
#        Mock DB + SMTP + repository. Compatibile CI senza DB reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) InvitoPortaleTests.test_invia_invito_cliente_happy_path
2) InvitoPortaleTests.test_invia_invito_cliente_not_found
3) InvitoPortaleTests.test_invia_invito_fornitore_happy_path
4) InvitoPortaleTests.test_email_vuota_solleva
5) InvitoPortaleTests.test_reinvia_invalida_precedente
6) InvitoPortaleTests.test_invia_invito_riusa_auth_user_esistente
7) InvitoPortaleTests.test_mask_email
8) InvitoPortaleTests.test_build_display_name_pg_e_pf
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

_SVC_PATH = "apps.portale.services.invito_portale_service"
_REPO = f"{_SVC_PATH}.PortaleRepository"
_AUTH_REPO = f"{_SVC_PATH}.AuthRepository"
_TOKEN_SVC = f"{_SVC_PATH}.TokenService"
_EMAIL_SVC = f"{_SVC_PATH}.EmailDispatchService"
_CONNECTION = f"{_SVC_PATH}.connection"
_SETTINGS = f"{_SVC_PATH}.settings"


def _mock_cursor_ctx(mock_conn):
    """Scopo: Installa un context manager cursore mockato su `connection`."""
    cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return cursor


class InvitoPortaleTests(TestCase):

    # Scopo: Flusso invito cliente: auth_user nuovo + identita creata +
    # password temp + token + email inviata + timestamp aggiornato.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_cliente_happy_path(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_conn, mock_settings
    ):
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-000123",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "uuid-1",
            "ragione_sociale": "ACME S.p.A.",
            "cognome": None,
            "nome": None,
            "codice_fiscale": None,
        }
        repo.find_auth_user_by_email.return_value = None  # utente nuovo
        repo.create_auth_user_portale.return_value = 200
        repo.find_identita_portale.return_value = None  # identita nuova
        repo.create_identita_portale.return_value = 500

        auth = MockAuth.return_value
        auth.set_deve_cambiare_password.return_value = True
        auth.set_invito_inviato_at.return_value = True

        token = MockToken.return_value
        token.create.return_value = "tk_abc"

        MockEmail.return_value.send_email.return_value = (1, True)

        _mock_cursor_ctx(mock_conn)  # UPDATE password + _get_display_name_of

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin Tid")

        result = svc.invia_invito_cliente(
            cliente_id=42,
            email="admin@acme.test",
            invitato_da_user_id=1,
        )

        self.assertTrue(result["inviato"])
        self.assertEqual(result["auth_user_id"], 200)
        self.assertTrue(result["nuovo_utente"])
        self.assertIn("***", result["email"])
        repo.create_auth_user_portale.assert_called_once()
        repo.create_identita_portale.assert_called_once()
        token.create.assert_called_once()
        MockEmail.return_value.send_email.assert_called_once()
        auth.set_deve_cambiare_password.assert_called_once_with(200, True)
        auth.set_invito_inviato_at.assert_called_once_with(200)

    # Scopo: BA inesistente -> ServiceError E_INVITO_PORTALE, nessun side-effect.
    @patch(_REPO)
    def test_invia_invito_cliente_not_found(self, MockRepo):
        MockRepo.return_value.get_cliente_info.return_value = None
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        with self.assertRaises(ServiceError) as ctx:
            InvitoPortaleService().invia_invito_cliente(
                cliente_id=999,
                email="a@b.it",
                invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_INVITO_PORTALE")

    # Scopo: Flusso invito fornitore — stesso scheletro, ruolo FORNITORE_PORTALE.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_fornitore_happy_path(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_conn, mock_settings
    ):
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        repo = MockRepo.return_value
        repo.get_fornitore_info.return_value = {
            "fornitore_id": 77,
            "soggetto_ruolo_id": 101,
            "soggetto_id": "uuid-2",
            "ragione_sociale": "Fornitore Test",
            "cognome": None,
            "nome": None,
            "codice_fiscale": None,
            "pec_email": "pec@fornitore.test",
        }
        repo.find_auth_user_by_email.return_value = None
        repo.create_auth_user_portale.return_value = 201
        repo.find_identita_portale.return_value = None
        repo.create_identita_portale.return_value = 501

        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_xyz"
        MockEmail.return_value.send_email.return_value = (1, True)

        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin Tid")

        result = svc.invia_invito_fornitore(
            fornitore_id=77,
            email="buyer@fornitore.test",
            invitato_da_user_id=1,
        )

        self.assertTrue(result["inviato"])
        self.assertEqual(result["auth_user_id"], 201)
        # Verifica il ruolo_applicativo passato alla creazione identita.
        kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertEqual(kwargs["ruolo_applicativo"], "FORNITORE_PORTALE")

    # Scopo: Email vuota -> errore immediato, nessuna query.
    @patch(_REPO)
    def test_email_vuota_solleva(self, MockRepo):
        MockRepo.return_value.get_cliente_info.return_value = {
            "billing_account_id": 1,
            "ba_codice": "BA-0001",
            "soggetto_ruolo_id": 1,
            "soggetto_id": "u",
            "ragione_sociale": "X",
        }
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        with self.assertRaises(ServiceError) as ctx:
            InvitoPortaleService().invia_invito_cliente(
                cliente_id=1, email="", invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_INVITO_PORTALE")

    # Scopo: Reinvio invalida token precedente prima di generare quello nuovo.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_reinvia_invalida_precedente(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_conn, mock_settings
    ):
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        # Identita gia' esistente con auth_user associato
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 200,
            "attivo": True,
            "invito_inviato_at": None,
            "deve_cambiare_password": False,
        }
        repo.find_auth_user_by_email.return_value = 200
        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "new_tk"
        MockEmail.return_value.send_email.return_value = (1, True)
        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin")

        svc.reinvia_invito_cliente(
            cliente_id=42,
            email="admin@acme.test",
            invitato_da_user_id=1,
        )
        MockToken.return_value.invalidate_all.assert_called_once_with(
            "INVITO_PORTALE", 200,
        )

    # Scopo: Se email esiste gia' in auth_user, non crea nuovo user; riusa id.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_riusa_auth_user_esistente(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_conn, mock_settings
    ):
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        repo.find_auth_user_by_email.return_value = 999  # existing
        repo.find_identita_portale.return_value = None
        repo.create_identita_portale.return_value = 501

        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk"
        MockEmail.return_value.send_email.return_value = (1, True)
        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin")

        result = svc.invia_invito_cliente(
            cliente_id=42,
            email="existing@acme.test",
            invitato_da_user_id=1,
        )
        self.assertEqual(result["auth_user_id"], 999)
        self.assertFalse(result["nuovo_utente"])
        repo.create_auth_user_portale.assert_not_called()

    # Scopo: Maschera email per la response.
    def test_mask_email(self) -> None:
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        self.assertEqual(
            InvitoPortaleService._mask_email("mario.rossi@acme.it"),
            "m***@acme.it",
        )
        self.assertEqual(
            InvitoPortaleService._mask_email("a@b.it"), "*@b.it",
        )
        self.assertEqual(InvitoPortaleService._mask_email(""), "***")

    # Scopo: Display name preferisce ragione_sociale; fallback PF cognome+nome.
    def test_build_display_name_pg_e_pf(self) -> None:
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        pg = {"ragione_sociale": "ACME S.p.A.", "cognome": None, "nome": None}
        self.assertEqual(InvitoPortaleService._build_display_name(pg), "ACME S.p.A.")
        pf = {"ragione_sociale": None, "cognome": "Rossi", "nome": "Mario"}
        self.assertEqual(InvitoPortaleService._build_display_name(pf), "Mario Rossi")
        empty = {"ragione_sociale": None, "cognome": None, "nome": None}
        self.assertEqual(
            InvitoPortaleService._build_display_name(empty),
            "cliente/fornitore",
        )
