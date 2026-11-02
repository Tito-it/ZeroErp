# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per InvitoPortaleService.
#        Mock DB + SMTP + repository. Compatibile CI senza DB reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  InvitoPortaleTests.test_invia_invito_cliente_happy_path
2)  InvitoPortaleTests.test_invia_invito_cliente_not_found — 404 E_CLIENTE_NON_TROVATO (E-4)
2b) InvitoPortaleTests.test_invia_invito_fornitore_not_found — 404 E_FORNITORE_NON_TROVATO (E-4)
3)  InvitoPortaleTests.test_invia_invito_fornitore_happy_path
4)  InvitoPortaleTests.test_email_vuota_solleva
5)  InvitoPortaleTests.test_reinvia_invalida_precedente
5b) InvitoPortaleTests.test_reinvio_a_chi_non_ha_mai_attivato_resta_invito (M-3)
6)  InvitoPortaleTests.test_invia_invito_riusa_auth_user_esistente_flow_cross
7)  InvitoPortaleTests.test_cross_non_riattiva_identita_disattivata
8)  InvitoPortaleTests.test_identita_gia_attiva_solleva
9)  InvitoPortaleTests.test_identita_collegata_altro_auth_user_solleva
11) InvitoPortaleTests.test_build_display_name_pg_e_pf
12) InvitoShopCustomerTests.test_invia_invito_shop_happy_path_invito
12b) InvitoShopCustomerTests.test_email_non_partita_risponde_inviato_false (F-3)
13) InvitoShopCustomerTests.test_invia_invito_shop_cross_path
14) InvitoShopCustomerTests.test_reinvia_invito_shop_invalida_entrambi_token
15) GetStatoAccessiTests.test_cliente_include_portale_e_shop
16) GetStatoAccessiTests.test_fornitore_solo_portale
17) GetStatoAccessiTests.test_cliente_not_found_solleva
18) DisattivaVesteTests.test_disattiva_cliente_portale_attivo_invalida_token — anche sessioni della veste e cache
19) DisattivaVesteTests.test_disattiva_cliente_nessuna_identita_noop
20) DisattivaVesteTests.test_disattiva_fornitore_portale
21) DisattivaVesteTests.test_disattiva_cliente_identita_gia_disattiva_idempotente
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

_SVC_PATH = "apps.portale.services.invito_portale_service"
_REPO = f"{_SVC_PATH}.PortaleRepository"
_AUTH_REPO = f"{_SVC_PATH}.AuthRepository"
# Token, email, link e firma sono del building block `invito_veste` (L-3):
# il service lo costruisce, e i suoi collaboratori si fingono li'.
_BB = "apps.core.services.invito_veste"
_TOKEN_SVC = f"{_BB}.TokenService"
# Le chiusure della veste spenta stanno nel BB (`InvitoVeste.chiudi_veste_spenta`).
_BLOCCA = f"{_BB}.blocca_token_sessioni"
_INVALIDATE = f"{_BB}.invalidate_user"
_EMAIL_SVC = f"{_BB}.EmailDispatchService"
_SETTINGS = f"{_BB}.settings"


class InvitoPortaleTests(TestCase):

    # Scopo: Flusso invito cliente: auth_user nuovo + identita creata
    # disattivata + token INVITO + email inviata + timestamp aggiornato.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_cliente_happy_path(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
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
        MockAuth.return_value.find_auth_user_id_per_email.return_value = None  # utente nuovo
        repo.create_auth_user_portale.return_value = 200
        MockAuth.return_value.auth_user_ha_password.return_value = False  # segnaposto `!`
        repo.find_identita_portale.return_value = None  # identita nuova
        repo.create_identita_portale.return_value = 500

        auth = MockAuth.return_value
        auth.set_deve_cambiare_password.return_value = True
        auth.set_invito_inviato_at.return_value = True

        token = MockToken.return_value
        token.create.return_value = "tk_abc"

        MockEmail.return_value.send_email.return_value = (1, True)


        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

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
        # Flow INVITO (email nuova): identita creata DISATTIVATA — si attiva
        # al consumo del token (M-3) — e nessuna password temporanea.
        create_kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertFalse(create_kwargs["attivo"])
        # Il cambio password obbligatorio e\' della credenziale (D-7), non della veste.
        self.assertNotIn("deve_cambiare_password", create_kwargs)
        token_kwargs = token.create.call_args.kwargs
        self.assertEqual(token_kwargs["tipo"], "INVITO_PORTALE")
        self.assertEqual(token_kwargs["meta"]["identita_id"], 500)
        MockEmail.return_value.send_email.assert_called_once()
        auth.set_deve_cambiare_password.assert_not_called()
        auth.set_invito_inviato_at.assert_called_once_with(200, identita_id=500)

    # Scopo: cliente inesistente -> 404 E_CLIENTE_NON_TROVATO (E-4: prima
    # E_INVITO_PORTALE, cioe' 400), nessun side-effect.
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
        self.assertEqual(ctx.exception.code, "E_CLIENTE_NON_TROVATO")

    # Scopo: fornitore inesistente -> 404 E_FORNITORE_NON_TROVATO (E-4).
    @patch(_REPO)
    def test_invia_invito_fornitore_not_found(self, MockRepo):
        MockRepo.return_value.get_fornitore_info.return_value = None
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        with self.assertRaises(ServiceError) as ctx:
            InvitoPortaleService().invia_invito_fornitore(
                fornitore_id=999,
                email="a@b.it",
                invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_FORNITORE_NON_TROVATO")

    # Scopo: Flusso invito fornitore — stesso scheletro, ruolo FORNITORE_PORTALE.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_fornitore_happy_path(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
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
        MockAuth.return_value.find_auth_user_id_per_email.return_value = None
        repo.create_auth_user_portale.return_value = 201
        MockAuth.return_value.auth_user_ha_password.return_value = False
        repo.find_identita_portale.return_value = None
        repo.create_identita_portale.return_value = 501

        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_xyz"
        MockEmail.return_value.send_email.return_value = (1, True)


        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

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
        self.assertFalse(kwargs["attivo"])
        # Il cambio password obbligatorio e\' della credenziale (D-7), non della veste.
        self.assertNotIn("deve_cambiare_password", kwargs)

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
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_reinvia_invalida_precedente(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
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
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 200
        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "new_tk"
        MockEmail.return_value.send_email.return_value = (1, True)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        svc.reinvia_invito_cliente(
            cliente_id=42,
            email="admin@acme.test",
            invitato_da_user_id=1,
        )
        # Il reinvio invalida i token della VESTE (identita 500), entrambi i
        # tipi della porta: l'invito precedente puo' essere nato in uno dei
        # due flussi. Per veste e non per credenziale: cliente e fornitore
        # portale condividono i tipi.
        MockToken.return_value.invalidate_for_identita.assert_called_once_with(
            ("INVITO_PORTALE", "ATTIVAZIONE_PORTALE_CROSS"), 200, 500,
        )
        MockToken.return_value.invalidate_all.assert_not_called()

    # Scopo: M-3 — reinvio a chi NON ha mai attivato: l'auth_user esiste
    # (l'ha creato il primo invito) ma ha ancora il segnaposto, e l'identita'
    # e' disattivata. Deve restare nel flow INVITO — token INVITO_PORTALE,
    # scelta della password — e non cadere nel CROSS. Fino al 2026-09-24 il
    # flusso si sceglieva da «l'auth_user e' stato appena creato» e questo
    # reinvio era impossibile.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_reinvio_a_chi_non_ha_mai_attivato_resta_invito(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 200  # creato dal primo invito
        MockAuth.return_value.auth_user_ha_password.return_value = False  # mai attivato
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 200,
            "attivo": False,
            "invito_inviato_at": None,
        }
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_re"
        MockEmail.return_value.send_email.return_value = (1, True)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        result = svc.reinvia_invito_cliente(
            cliente_id=42,
            email="admin@acme.test",
            invitato_da_user_id=1,
        )

        self.assertFalse(result["is_cross"])
        self.assertFalse(result["nuovo_utente"])
        self.assertEqual(
            MockToken.return_value.create.call_args.kwargs["tipo"], "INVITO_PORTALE"
        )
        MockAuth.return_value.auth_user_ha_password.assert_called_once_with(200)
        # L'identita' resta disattivata: la attiva il consumo del token.
        repo.riattiva_identita.assert_not_called()
        repo.create_auth_user_portale.assert_not_called()

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
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_riusa_auth_user_esistente_flow_cross(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999  # auth_user gia' esistente
        MockAuth.return_value.auth_user_ha_password.return_value = True  # ... con una password vera
        repo.find_identita_portale.return_value = None  # ma identita CLIENTE_PORTALE nuova
        repo.create_identita_portale.return_value = 501

        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_cross"
        MockEmail.return_value.send_email.return_value = (1, True)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

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
        # Il cambio password obbligatorio e\' della credenziale (D-7), non della veste.
        self.assertNotIn("deve_cambiare_password", create_kwargs)

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
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_cross_non_riattiva_identita_disattivata(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999  # esistente → flow CROSS
        MockAuth.return_value.auth_user_ha_password.return_value = True
        # Identita CROSS gia' creata in passato ma disattivata (invito
        # scaduto o revoca admin): riattivazione deve avvenire SOLO con
        # consumo del token CROSS.
        repo.find_identita_portale.return_value = {
            "identita_id": 501,
            "auth_user_id": 999,
            "attivo": False,
            "invito_inviato_at": None,
        }
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_cross_reinv"
        MockEmail.return_value.send_email.return_value = (1, True)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

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
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_identita_gia_attiva_solleva(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-42",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "u",
            "ragione_sociale": "ACME",
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999  # email esistente → CROSS
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 999,
            "attivo": True,  # ← gia' attiva
            "invito_inviato_at": None,
        }

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

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
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_identita_collegata_altro_auth_user_solleva(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
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
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999
        repo.find_identita_portale.return_value = {
            "identita_id": 500,
            "auth_user_id": 888,
            "attivo": False,
            "invito_inviato_at": None,
        }

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito_cliente(
                cliente_id=42,
                email="existing@acme.test",
                invitato_da_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_INVITO_PORTALE")
        repo.create_identita_portale.assert_not_called()

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


# ── Shop customer (B1 §13.7 admin-driven) ─────────────────────────


class InvitoShopCustomerTests(TestCase):
    """Test invia/reinvia invito SHOP_CUSTOMER. Stessa pipeline interna
    di CLIENTE_PORTALE ma config veste diversa (token tipo, template,
    link path)."""

    # Scopo: Flow INVITO email nuova -> identita SHOP_CUSTOMER disattivata +
    # token INVITO_SHOP + template INVITO_SHOP + link /attivazione-shop.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_shop_happy_path_invito(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-000123",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "uuid-1",
            "ragione_sociale": "ACME Shop",
            "cognome": None, "nome": None, "codice_fiscale": None,
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = None
        repo.create_auth_user_portale.return_value = 300
        MockAuth.return_value.auth_user_ha_password.return_value = False
        repo.find_identita_portale.return_value = None
        repo.create_identita_portale.return_value = 600

        MockAuth.return_value.set_deve_cambiare_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_shop_new"
        MockEmail.return_value.send_email.return_value = (1, True)


        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        result = svc.invia_invito_shop_customer(
            cliente_id=42,
            email="shopper@acme.test",
            invitato_da_user_id=1,
        )

        self.assertTrue(result["inviato"])
        self.assertEqual(result["auth_user_id"], 300)
        self.assertEqual(result["identita_id"], 600)
        self.assertTrue(result["nuovo_utente"])
        self.assertFalse(result["is_cross"])
        # Veste creata con ruolo SHOP_CUSTOMER, DISATTIVATA (flow INVITO:
        # la attiva il consumo del token, M-3).
        kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertEqual(kwargs["ruolo_applicativo"], "SHOP_CUSTOMER")
        self.assertFalse(kwargs["attivo"])
        # Il cambio password obbligatorio e\' della credenziale (D-7), non della veste.
        self.assertNotIn("deve_cambiare_password", kwargs)
        # Token tipo + template + link path mappati su veste shop.
        token_kwargs = MockToken.return_value.create.call_args.kwargs
        self.assertEqual(token_kwargs["tipo"], "INVITO_SHOP")
        self.assertEqual(token_kwargs["meta"]["identita_id"], 600)
        email_kwargs = MockEmail.return_value.send_email.call_args.kwargs
        self.assertEqual(email_kwargs["codice_template"], "INVITO_SHOP")
        self.assertIn("/attivazione-shop/tk_shop_new", email_kwargs["variabili"]["link"])

    # Scopo: ⭐ F-3 — l'email che non parte (SMTP fallito, canale non
    # configurato: `send_email` torna `False` senza eccezione) risponde
    # `inviato: false`: la veste e il token ci sono, ma l'invito non e'
    # arrivato, e `invito_inviato_at` non si scrive. Vale per cliente,
    # fornitore e shop: la strada e' `_invia_invito_common`.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_email_non_partita_risponde_inviato_false(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-000123",
            "soggetto_ruolo_id": 100,
            "soggetto_id": "uuid-1",
            "ragione_sociale": "ACME Shop",
            "cognome": None, "nome": None, "codice_fiscale": None,
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = None
        repo.create_auth_user_portale.return_value = 300
        MockAuth.return_value.auth_user_ha_password.return_value = False
        repo.find_identita_portale.return_value = None
        repo.create_identita_portale.return_value = 600
        MockToken.return_value.create.return_value = "tk_shop_new"
        MockEmail.return_value.send_email.return_value = (1, False)

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        with self.assertLogs("security", level="ERROR"):
            result = InvitoPortaleService().invia_invito_shop_customer(
                cliente_id=42,
                email="shopper@acme.test",
                invitato_da_user_id=1,
            )

        self.assertIs(result["inviato"], False)
        self.assertEqual(result["identita_id"], 600)
        MockAuth.return_value.set_invito_inviato_at.assert_not_called()

    # Scopo: Flow CROSS email esistente (operatore o altra veste) ->
    # identita SHOP_CUSTOMER disattivata + token ATTIVAZIONE_SHOP_CROSS.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_invia_invito_shop_cross_path(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 42,
            "ba_codice": "BA-000999",
            "soggetto_ruolo_id": 200,
            "soggetto_id": "uuid-2",
            "ragione_sociale": "Cross Shop",
            "cognome": None, "nome": None, "codice_fiscale": None,
        }
        # Email gia' nota: l'auth_user esiste come operatore o altra veste.
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999
        MockAuth.return_value.auth_user_ha_password.return_value = True
        repo.find_identita_portale.return_value = None  # nessuna SHOP ancora
        repo.create_identita_portale.return_value = 700

        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_shop_cross"
        MockEmail.return_value.send_email.return_value = (1, True)


        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        result = svc.invia_invito_shop_customer(
            cliente_id=42,
            email="tid@example.com",
            invitato_da_user_id=1,
        )

        self.assertTrue(result["inviato"])
        self.assertEqual(result["auth_user_id"], 999)
        self.assertFalse(result["nuovo_utente"])
        self.assertTrue(result["is_cross"])
        # Identita CROSS: attivo=false, no password temp, no flag deve_cambiare.
        kwargs = repo.create_identita_portale.call_args.kwargs
        self.assertEqual(kwargs["ruolo_applicativo"], "SHOP_CUSTOMER")
        self.assertFalse(kwargs["attivo"])
        # Il cambio password obbligatorio e\' della credenziale (D-7), non della veste.
        self.assertNotIn("deve_cambiare_password", kwargs)
        # Token CROSS, no UPDATE password (auth.set_deve_cambiare_password mai
        # chiamato in flow CROSS).
        token_kwargs = MockToken.return_value.create.call_args.kwargs
        self.assertEqual(token_kwargs["tipo"], "ATTIVAZIONE_SHOP_CROSS")
        MockAuth.return_value.set_deve_cambiare_password.assert_not_called()

    # Scopo: Reinvio invalida entrambi i token shop (INVITO_SHOP +
    # ATTIVAZIONE_SHOP_CROSS) per l'auth_user prima di rigenerare.
    @patch(_SETTINGS)
    @patch(_EMAIL_SVC)
    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_reinvia_invito_shop_invalida_entrambi_token(
        self, MockRepo, MockAuth, MockToken, MockEmail, mock_settings
    ):
        mock_settings.FRONTEND_URL = "https://localhost"
        repo = MockRepo.return_value
        info = {
            "billing_account_id": 42, "ba_codice": "BA-X",
            "soggetto_ruolo_id": 100, "soggetto_id": "u",
            "ragione_sociale": "Shop", "cognome": None, "nome": None,
            "codice_fiscale": None,
        }
        repo.get_cliente_info.return_value = info
        # Identita SHOP_CUSTOMER disattivata (caso reinvio dopo token scaduto).
        repo.find_identita_portale.return_value = {
            "identita_id": 700, "auth_user_id": 999,
            "attivo": False, "invito_inviato_at": None,
        }
        MockAuth.return_value.find_auth_user_id_per_email.return_value = 999
        # Flow CROSS: la credenziale ha una password vera. Riprende l'identita
        # gia' presente e la lascia disattivata (la attiva il token).
        MockAuth.return_value.auth_user_ha_password.return_value = True
        MockAuth.return_value.set_invito_inviato_at.return_value = True
        MockToken.return_value.create.return_value = "tk_re"
        MockEmail.return_value.send_email.return_value = (1, True)


        from apps.portale.services.invito_portale_service import InvitoPortaleService
        svc = InvitoPortaleService()

        svc.reinvia_invito_shop_customer(
            cliente_id=42,
            email="tid@example.com",
            invitato_da_user_id=1,
        )

        # Entrambi i tipi della porta shop, sulla sola veste.
        args = MockToken.return_value.invalidate_for_identita.call_args.args
        self.assertEqual(args[0], ("INVITO_SHOP", "ATTIVAZIONE_SHOP_CROSS"))


# ── Stato + disattivazione veste (§6.2.4 + §6.2.6) ────────────────


class GetStatoAccessiTests(TestCase):
    """Test aggregazione stato accessi per cliente + fornitore."""

    @patch(_REPO)
    def test_cliente_include_portale_e_shop(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 1, "ba_codice": "X",
            "soggetto_ruolo_id": 100, "soggetto_id": "u",
            "ragione_sociale": "X", "cognome": None, "nome": None,
            "codice_fiscale": None,
        }
        repo.get_stato_identita.side_effect = [
            {"stato": "ATTIVO", "identita_id": 500, "auth_user_id": 10,
             "invito_inviato_at": None, "token_scade_at": None},
            {"stato": "NESSUNO", "identita_id": None, "auth_user_id": None,
             "invito_inviato_at": None, "token_scade_at": None},
        ]
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().get_stato_accessi_cliente(1)
        self.assertEqual(result["portale"]["stato"], "ATTIVO")
        self.assertEqual(result["shop"]["stato"], "NESSUNO")
        # Due chiamate: una per CLIENTE_PORTALE, una per SHOP_CUSTOMER.
        calls = repo.get_stato_identita.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[1], "CLIENTE_PORTALE")
        self.assertEqual(calls[1].args[1], "SHOP_CUSTOMER")

    @patch(_REPO)
    def test_fornitore_solo_portale(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_fornitore_info.return_value = {
            "fornitore_id": 77, "soggetto_ruolo_id": 101,
            "soggetto_id": "u", "ragione_sociale": "F",
            "cognome": None, "nome": None,
            "codice_fiscale": None, "pec_email": None,
        }
        repo.get_stato_identita.return_value = {
            "stato": "PENDING", "identita_id": 501, "auth_user_id": 20,
            "invito_inviato_at": "2026-04-21", "token_scade_at": "2026-04-24",
        }
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().get_stato_accessi_fornitore(77)
        self.assertEqual(result["portale"]["stato"], "PENDING")
        self.assertNotIn("shop", result)  # fornitori no shop

    @patch(_REPO)
    def test_cliente_not_found_solleva(self, MockRepo):
        MockRepo.return_value.get_cliente_info.return_value = None
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        with self.assertRaises(ServiceError) as ctx:
            InvitoPortaleService().get_stato_accessi_cliente(999)
        self.assertEqual(ctx.exception.code, "E_CLIENTE_NON_TROVATO")


class DisattivaVesteTests(TestCase):
    """Test soft-revoke veste cliente + fornitore."""

    # ⛔ Sessioni e cache si chiudono anche qui (A-5, D-5): senza questi mock
    #    la blacklist andrebbe sul DB di sviluppo, e il test resterebbe verde.
    def setUp(self):
        for nome, attr in ((_BLOCCA, "mock_blocca"), (_INVALIDATE, "mock_invalidate")):
            patcher = patch(nome)
            setattr(self, attr, patcher.start())
            self.addCleanup(patcher.stop)

    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_disattiva_cliente_portale_attivo_invalida_token(
        self, MockRepo, _MockAuth, MockToken
    ):
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 1, "ba_codice": "X",
            "soggetto_ruolo_id": 100, "soggetto_id": "u",
            "ragione_sociale": "X", "cognome": None, "nome": None,
            "codice_fiscale": None,
        }
        repo.find_identita_portale.return_value = {
            "identita_id": 500, "auth_user_id": 10, "attivo": True,
            "invito_inviato_at": None,
        }
        repo.disattiva_identita.return_value = True

        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().disattiva_veste_cliente(
            cliente_id=1,
            ruolo_applicativo="CLIENTE_PORTALE",
            disattivato_da_user_id=999,
        )
        self.assertTrue(result["disattivato"])
        self.assertEqual(result["stato"], "DISATTIVO")
        self.assertEqual(result["identita_id"], 500)
        repo.disattiva_identita.assert_called_once_with(500)
        # I token della veste (entrambi i tipi della porta) invalidati.
        MockToken.return_value.invalidate_for_identita.assert_called_once_with(
            ("INVITO_PORTALE", "ATTIVAZIONE_PORTALE_CROSS"), 10, 500,
        )
        # D-5: le sessioni della SOLA veste spenta; A-5: la cache.
        self.mock_blocca.assert_called_once_with(10, identita_id=500)
        self.mock_invalidate.assert_called_once_with(10)

    @patch(_REPO)
    def test_disattiva_cliente_nessuna_identita_noop(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 1, "ba_codice": "X",
            "soggetto_ruolo_id": 100, "soggetto_id": "u",
            "ragione_sociale": "X", "cognome": None, "nome": None,
            "codice_fiscale": None,
        }
        repo.find_identita_portale.return_value = None
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().disattiva_veste_cliente(
            cliente_id=1,
            ruolo_applicativo="CLIENTE_PORTALE",
            disattivato_da_user_id=999,
        )
        self.assertFalse(result["disattivato"])
        self.assertEqual(result["stato"], "NESSUNO")
        repo.disattiva_identita.assert_not_called()
        self.mock_blocca.assert_not_called()

    @patch(_TOKEN_SVC)
    @patch(_AUTH_REPO)
    @patch(_REPO)
    def test_disattiva_fornitore_portale(
        self, MockRepo, _MockAuth, MockToken
    ):
        repo = MockRepo.return_value
        repo.get_fornitore_info.return_value = {
            "fornitore_id": 77, "soggetto_ruolo_id": 101,
            "soggetto_id": "u", "ragione_sociale": "F",
            "cognome": None, "nome": None,
            "codice_fiscale": None, "pec_email": None,
        }
        repo.find_identita_portale.return_value = {
            "identita_id": 600, "auth_user_id": 20, "attivo": True,
            "invito_inviato_at": None,
        }
        repo.disattiva_identita.return_value = True
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().disattiva_veste_fornitore(
            fornitore_id=77, disattivato_da_user_id=999,
        )
        self.assertTrue(result["disattivato"])
        self.assertEqual(result["identita_id"], 600)
        self.mock_blocca.assert_called_once_with(20, identita_id=600)

    @patch(_TOKEN_SVC)
    @patch(_REPO)
    def test_disattiva_cliente_identita_gia_disattiva_idempotente(
        self, MockRepo, MockToken
    ):
        repo = MockRepo.return_value
        repo.get_cliente_info.return_value = {
            "billing_account_id": 1, "ba_codice": "X",
            "soggetto_ruolo_id": 100, "soggetto_id": "u",
            "ragione_sociale": "X", "cognome": None, "nome": None,
            "codice_fiscale": None,
        }
        # Identita gia' disattiva (attivo=false): no UPDATE fisico ma
        # comunque invalida eventuali token residui (best-effort cleanup).
        repo.find_identita_portale.return_value = {
            "identita_id": 500, "auth_user_id": 10, "attivo": False,
            "invito_inviato_at": None,
        }
        from apps.portale.services.invito_portale_service import InvitoPortaleService
        result = InvitoPortaleService().disattiva_veste_cliente(
            cliente_id=1,
            ruolo_applicativo="CLIENTE_PORTALE",
            disattivato_da_user_id=999,
        )
        # was_active=False -> disattivato=False (nessun UPDATE), ma stato
        # finale DISATTIVO riportato coerentemente al caller.
        self.assertFalse(result["disattivato"])
        self.assertEqual(result["stato"], "DISATTIVO")
        repo.disattiva_identita.assert_not_called()
        # Best-effort cleanup: i token portale residui vengono comunque
        # invalidati (idempotente lato BE, no-op se non ce n'erano).
        MockToken.return_value.invalidate_for_identita.assert_called_once_with(
            ("INVITO_PORTALE", "ATTIVAZIONE_PORTALE_CROSS"), 10, 500,
        )
        # Anche su una veste gia' spenta: chiude le sessioni rimaste vive.
        self.mock_blocca.assert_called_once_with(10, identita_id=500)
