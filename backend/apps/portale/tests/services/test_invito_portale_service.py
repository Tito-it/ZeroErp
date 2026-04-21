# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per InvitoPortaleService.
#        Mock DB + SMTP + repository. Compatibile CI senza DB reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  InvitoPortaleTests.test_invia_invito_cliente_happy_path
2)  InvitoPortaleTests.test_invia_invito_cliente_not_found
3)  InvitoPortaleTests.test_invia_invito_fornitore_happy_path
4)  InvitoPortaleTests.test_email_vuota_solleva
5)  InvitoPortaleTests.test_reinvia_invalida_precedente
6)  InvitoPortaleTests.test_invia_invito_riusa_auth_user_esistente_flow_cross
7)  InvitoPortaleTests.test_cross_non_riattiva_identita_disattivata
8)  InvitoPortaleTests.test_identita_gia_attiva_solleva
9)  InvitoPortaleTests.test_identita_collegata_altro_auth_user_solleva
10) InvitoPortaleTests.test_mask_email
11) InvitoPortaleTests.test_build_display_name_pg_e_pf
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
        self.assertEqual(result["identita_id"], 500)
        self.assertTrue(result["nuovo_utente"])
        self.assertFalse(result["is_cross"])
        self.assertIn("***", result["email"])
        repo.create_auth_user_portale.assert_called_once()
        # Flow INVITO (email nuova): identita creata attivo=true +
        # deve_cambiare_password=true, token INVITO_PORTALE standard.
        create_kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertTrue(create_kwargs["attivo"])
        self.assertTrue(create_kwargs["deve_cambiare_password"])
        token_kwargs = token.create.call_args.kwargs
        self.assertEqual(token_kwargs["tipo"], "INVITO_PORTALE")
        self.assertEqual(token_kwargs["meta"]["identita_id"], 500)
        MockEmail.return_value.send_email.assert_called_once()
        auth.set_deve_cambiare_password.assert_called_once_with(
            200, True, identita_id=500
        )
        auth.set_invito_inviato_at.assert_called_once_with(200, identita_id=500)

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
        self.assertEqual(result["identita_id"], 501)
        self.assertFalse(result["is_cross"])
        # Verifica il ruolo_applicativo + attivo passati alla creazione identita.
        kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertEqual(kwargs["ruolo_applicativo"], "FORNITORE_PORTALE")
        self.assertTrue(kwargs["attivo"])
        self.assertTrue(kwargs["deve_cambiare_password"])

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
        # Identita gia' esistente ma disattivata (invito scaduto o revoca
        # — caso legittimo di reinvio). Post §8.4.1 guard: il reinvio su
        # identita attiva e' vietato (l'utente ha gia' accesso).
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 200,
            "attivo": False,
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
        # Post §8.4.1: reinvio invalida entrambi i tipi (INVITO + CROSS)
        # per coprire il caso in cui l'invito precedente sia stato creato
        # con uno dei due flow (auth_user nuovo vs esistente).
        invalidate_calls = [
            c.args for c in MockToken.return_value.invalidate_all.call_args_list
        ]
        self.assertIn(("INVITO_PORTALE", 200), invalidate_calls)
        self.assertIn(("ATTIVAZIONE_PORTALE_CROSS", 200), invalidate_calls)

    # Scopo: Se email esiste gia' in auth_user (operatore o altra veste
    # portale), il service entra nel flow CROSS §8.4.1:
    #  - NON crea un nuovo auth_user (l'utente ce l'ha gia')
    #  - Crea una 2a identita portale con `attivo=false` e
    #    `deve_cambiare_password=false`
    #  - Genera token tipo `ATTIVAZIONE_PORTALE_CROSS` (non INVITO_PORTALE)
    #  - NON setta password temporanea (l'utente usa la sua password
    #    esistente)
    #  - NON chiama `set_deve_cambiare_password` (niente cambio pw forzato
    #    in attivazione cross)
    #  - L'attivazione (§8.4.2) attiva l'identita senza chiedere password.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_riusa_auth_user_esistente_flow_cross(
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
        repo.find_auth_user_by_email.return_value = 999  # auth_user gia' esistente
        repo.find_identita_portale.return_value = None  # ma identita CLIENTE_PORTALE nuova
        repo.create_identita_portale.return_value = 501

        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_cross"
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

        # Contract di ritorno flag cross + nuovo_utente False
        self.assertEqual(result["auth_user_id"], 999)
        self.assertEqual(result["identita_id"], 501)
        self.assertFalse(result["nuovo_utente"])
        self.assertTrue(result["is_cross"])

        # NO auth_user creato
        repo.create_auth_user_portale.assert_not_called()

        # Identita creata disattivata + senza flag cambio password
        create_kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertFalse(create_kwargs["attivo"])
        self.assertFalse(create_kwargs["deve_cambiare_password"])

        # Token tipo CROSS (non INVITO_PORTALE)
        token_kwargs = MockToken.return_value.create.call_args.kwargs
        self.assertEqual(token_kwargs["tipo"], "ATTIVAZIONE_PORTALE_CROSS")
        self.assertEqual(token_kwargs["meta"]["identita_id"], 501)

        # Nessun reset flag (flow cross salta completamente quella riga)
        MockAuth.return_value.set_deve_cambiare_password.assert_not_called()

        # Timestamp invito settato sulla nuova identita CROSS
        MockAuth.return_value.set_invito_inviato_at.assert_called_once_with(
            999, identita_id=501
        )

    # Scopo: Flow CROSS + identita gia' esistente ma disattivata.
    # Il service NON deve riattivarla: l'attivazione della veste avviene
    # al consumo del token ATTIVAZIONE_PORTALE_CROSS (§8.4.2). Il test
    # verifica che nessun UPDATE di riattivazione venga emesso.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_cross_non_riattiva_identita_disattivata(
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
        repo.find_auth_user_by_email.return_value = 999  # esistente → flow CROSS
        # Identita CROSS gia' creata in passato ma disattivata (invito
        # scaduto o revoca admin): riattivazione deve avvenire SOLO con
        # consumo del token CROSS.
        repo.find_identita_portale.return_value = {
            "identita_id": 501,
            "auth_user_id": 999,
            "attivo": False,
            "invito_inviato_at": None,
            "deve_cambiare_password": False,
        }
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_cross_reinv"
        MockEmail.return_value.send_email.return_value = (1, True)
        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin")

        svc.invia_invito_cliente(
            cliente_id=42,
            email="existing@acme.test",
            invitato_da_user_id=1,
        )

        # Verifica diretta sul repository: la riattiva_identita NON deve
        # essere chiamata per il flow CROSS (l'attivazione e' delegata al
        # consumo del token CROSS in §8.4.2).
        repo.riattiva_identita.assert_not_called()

    # Scopo: Guard §8.4.1 BUG1. Se per (soggetto_ruolo, ruolo_applicativo)
    # esiste gia' un'identita ATTIVA, il primo invito (e il reinvio) devono
    # fallire con E_INVITO_PORTALE. Semantica: l'utente ha gia' accesso al
    # portale, un nuovo invito non ha senso; per credenziali usa il reset
    # password self-service.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_identita_gia_attiva_solleva(
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
        repo.find_auth_user_by_email.return_value = 999  # email esistente → CROSS
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 999,
            "attivo": True,  # ← gia' attiva
            "invito_inviato_at": None,
            "deve_cambiare_password": False,
        }
        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin")

        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito_cliente(
                cliente_id=42,
                email="existing@acme.test",
                invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_INVITO_PORTALE")
        # Nessun token emesso, nessuna identita creata.
        repo.create_identita_portale.assert_not_called()
        MockToken.return_value.create.assert_not_called()

    # Scopo: Guard §8.4.1 FRAG4. Se l'identita portale per quel
    # soggetto_ruolo e' collegata a un auth_user DIVERSO da quello
    # risolto via email (stato incoerente: soggetto_ruolo riassegnato a
    # altro holder o bug di migrazione), il service NON deve ignorare la
    # divergenza — richiede intervento manuale.
    @patch(_SETTINGS)
    @patch(_CONNECTION)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_identita_collegata_altro_auth_user_solleva(
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
        # auth_user risolto via email = 999 ma identita esistente punta
        # ad auth_user = 888 (incoerenza).
        repo.find_auth_user_by_email.return_value = 999
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 888,
            "attivo": False,
            "invito_inviato_at": None,
            "deve_cambiare_password": False,
        }
        _mock_cursor_ctx(mock_conn)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()
        svc._get_display_name_of = MagicMock(return_value="Admin")

        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito_cliente(
                cliente_id=42,
                email="existing@acme.test",
                invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_INVITO_PORTALE")
        repo.create_identita_portale.assert_not_called()

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
