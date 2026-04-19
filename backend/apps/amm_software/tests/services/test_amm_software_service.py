# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AmmSoftwareService — validazione, orchestrazione,
#        cache invalidation. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_create_operatore_ok — happy path
 2) test_create_operatore_missing_cognome — campo obbligatorio mancante
 3) test_create_operatore_missing_password — password vuota
 4) test_create_operatore_missing_qualifica — qualifica mancante
 5) test_create_operatore_password_hashed — password non in chiaro
 6) test_get_operatore_ok — dettaglio operatore
 7) test_get_operatore_not_found — id inesistente
 8) test_update_operatore_ok — aggiorna e invalida cache
 9) test_update_operatore_not_found — id inesistente
 9a) test_update_operatore_contract_nuovo_super_attivo — traduzione contract multi-face
 9b) test_update_operatore_contract_legacy — retrocompat ruolo_sistema
10) test_disabilita_operatore_ok — disabilita e invalida cache + blacklist
11) test_disabilita_operatore_not_found — id inesistente
12) test_put_override_aree_invalidates_cache — invalida cache dopo save
13) test_put_override_azioni_invalidates_cache — invalida cache dopo save
14) test_put_emittenti_scope_invalidates_cache — invalida cache dopo save
15) test_put_profilo_reparto_invalidates_department — invalida cache reparto
"""

from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from apps.core.services.service_errors import ServiceError

REPO = "apps.amm_software.services.amm_software_service.AmmSoftwareRepository"
INVALIDATE_USER = "apps.amm_software.services.amm_software_service.invalidate_user"
INVALIDATE_DEPT = "apps.amm_software.services.amm_software_service.invalidate_department"
BLACKLIST = "apps.amm_software.services.amm_software_service._blacklist_user_tokens"
MAKE_PW = "apps.amm_software.services.amm_software_service.make_password"


class TestCreateOperatore(TestCase):
    """Test AmmSoftwareService.create_operatore()."""

    @patch(MAKE_PW, return_value="hashed_pw")
    @patch(REPO)
    def test_create_operatore_ok(self, mock_repo_cls, mock_pw):
        """Happy path: crea operatore, password hashata."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = 1
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "username": "test"}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        result = AmmSoftwareService().create_operatore({
            "cognome": "Rossi", "nome": "Mario", "codice_fiscale": "RSSMRA80A01H501Z",
            "username": "mrossi", "email": "m@test.it", "password": "secret123",
            "qualifica_id": 1,
        })
        self.assertEqual(result["auth_user_id"], 1)
        mock_repo.crea_operatore.assert_called_once()
        # Verifica password hashata
        self.assertEqual(mock_repo.crea_operatore.call_args.kwargs["password_hash"], "hashed_pw")

    @patch(REPO)
    def test_create_operatore_missing_cognome(self, mock_repo_cls):
        """Cognome vuoto -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "", "nome": "Mario", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "pw", "qualifica_id": 1,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(REPO)
    def test_create_operatore_missing_password(self, mock_repo_cls):
        """Password vuota -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "R", "nome": "M", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "", "qualifica_id": 1,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(REPO)
    def test_create_operatore_missing_qualifica(self, mock_repo_cls):
        """Qualifica None -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "R", "nome": "M", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "pw", "qualifica_id": None,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(MAKE_PW, return_value="hashed")
    @patch(REPO)
    def test_create_operatore_password_hashed(self, mock_repo_cls, mock_pw):
        """Verifica che make_password venga chiamato con la password raw."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = 1
        mock_repo.get_operatore_detail.return_value = {}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().create_operatore({
            "cognome": "R", "nome": "M", "codice_fiscale": "CF",
            "username": "u", "email": "e@t.it", "password": "mypassword", "qualifica_id": 1,
        })
        mock_pw.assert_called_once_with("mypassword")


class TestGetOperatore(TestCase):
    """Test AmmSoftwareService.get_operatore()."""

    @patch(REPO)
    def test_get_operatore_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        result = AmmSoftwareService().get_operatore(1)
        self.assertEqual(result["auth_user_id"], 1)

    @patch(REPO)
    def test_get_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_operatore(999)
        self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")


class TestUpdateOperatore(TestCase):
    """Test AmmSoftwareService.update_operatore()."""

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_ok(self, mock_repo_cls, mock_invalidate):
        """Aggiorna e invalida cache."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"email": "new@test.it"})
        mock_repo.update_operatore.assert_called_once()
        mock_invalidate.assert_called_once_with(1)

    @patch(REPO)
    def test_update_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().update_operatore(999, {"email": "x"})

    # Scopo: Contract nuovo multi-face: payload {is_super_admin, attivo}
    # viene tradotto in ruolo_sistema legacy per il repository. Copre i 4
    # casi della matrice (ADMIN / OPERATIVO / DISABILITATO / NO-OP).
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_contract_nuovo_super_attivo(
        self, mock_repo_cls, _mock_invalidate
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        # Caso 1: super=true, attivo=true  -> ADMIN
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": True}
        )
        self.assertEqual(
            mock_repo.update_operatore.call_args.kwargs["ruolo_sistema"], "ADMIN"
        )
        self.assertTrue(mock_repo.update_operatore.call_args.kwargs["attivo"])

        # Caso 2: super=false, attivo=true -> OPERATIVO
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": False, "attivo": True}
        )
        self.assertEqual(
            mock_repo.update_operatore.call_args.kwargs["ruolo_sistema"], "OPERATIVO"
        )

        # Caso 3: super=*, attivo=false -> DISABILITATO
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": False}
        )
        self.assertEqual(
            mock_repo.update_operatore.call_args.kwargs["ruolo_sistema"],
            "DISABILITATO",
        )

        # Caso 4: super=true, attivo=None -> NO-OP (ruolo_sistema None)
        # Guard contro side-effect: riattivazione silenziosa.
        AmmSoftwareService().update_operatore(1, {"is_super_admin": True})
        self.assertIsNone(
            mock_repo.update_operatore.call_args.kwargs["ruolo_sistema"]
        )

    # Scopo: Se il payload usa ruolo_sistema legacy, passa through senza
    # traduzione. Retrocompat con FE pre-Stage B.
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_contract_legacy(self, mock_repo_cls, _mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"ruolo_sistema": "ADMIN"})
        self.assertEqual(
            mock_repo.update_operatore.call_args.kwargs["ruolo_sistema"], "ADMIN"
        )


class TestDisabilitaOperatore(TestCase):
    """Test AmmSoftwareService.disabilita_operatore()."""

    @patch(BLACKLIST)
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_disabilita_operatore_ok(self, mock_repo_cls, mock_invalidate, mock_blacklist):
        """Disabilita, invalida cache, blacklist token."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().disabilita_operatore(1)
        mock_repo.disabilita_operatore.assert_called_once_with(1)
        mock_invalidate.assert_called_once_with(1)
        mock_blacklist.assert_called_once_with(1)

    @patch(REPO)
    def test_disabilita_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().disabilita_operatore(999)


class TestOverrideCache(TestCase):
    """Test cache invalidation su override e profili."""

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_override_aree_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_override_aree.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_aree(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_override_azioni_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_override_azioni.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_azioni(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_emittenti_scope_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_emittenti_scope.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_emittenti_scope(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_DEPT)
    @patch(REPO)
    def test_put_profilo_reparto_invalidates_department(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_profilo_reparto.return_value = {}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_profilo_reparto(5, [], [])
        mock_invalidate.assert_called_once_with(5)
