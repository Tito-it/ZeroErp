# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per UserProfileView (GET /api/v1/core/me/).
#        Mock repository e permessi, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) UserProfileViewTests.test_get_profile_success
 2) UserProfileViewTests.test_get_profile_includes_emittente_null
 3) UserProfileViewTests.test_get_profile_repository_error_propagates
 4) UserProfileViewTests.test_is_admin_globale_admin_senza_emittente
 5) UserProfileViewTests.test_is_admin_globale_admin_con_emittente
 6) UserProfileViewTests.test_is_admin_globale_operativo
 7) UserProfileViewTests.test_profile_include_is_super_admin_e_ruolo_applicativo
 8) CoreRepositoryTests.test_get_user_profile_returns_jsonb
 9) CoreRepositoryTests.test_get_user_profile_null_result_raises_error
10) CoreRepositoryTests.test_get_user_profile_no_row_raises_error
11) IdentitaDelJwtTests.test_token_none_ritorna_none
12) IdentitaDelJwtTests.test_claim_assente_ritorna_none
13) IdentitaDelJwtTests.test_claim_presente_delega_al_repo
14) IdentitaDelJwtTests.test_profile_contiene_blocco_identita
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.core_repository import CoreRepository
from apps.core.services.service_errors import ServiceError


# --- Dati di test ---

_PROFILE_FULL = {
    "utente": {
        "auth_user_id": 1,
        "username": "mtitini",
        "first_name": "Michele",
        "last_name": "Titini",
        "email": "m@example.com",
    },
    "is_super_admin": True,
    "ruolo_applicativo": "OPERATORE",
    "risorse_umane": {
        "risorsa_umana_id": 5,
        "risorse_umane_auth_user_id": 3,
        "soggetto_ruolo_id": 12,
        "qualifica_id": 2,
        "qualifica_codice": "DEV",
        "qualifica_descrizione": "Sviluppatore",
        "unita_organizzativa_id": 3,
        "unita_organizzativa_codice": "IT",
        "unita_organizzativa_descrizione": "Information Technology",
        "valido_dal": "2024-01-01",
        "valido_al": None,
        "attivo": True,
    },
    "soggetto": {
        "soggetto_id": "019-uuid-abc",
        "soggetto_ruolo_id": 12,
        "tipo_ruolo_codice_interno": "RISORSA_UMANA",
        "ragione_sociale_completa": "Titini Michele",
        "cognome": "Titini",
        "nome": "Michele",
        "codice_fiscale": "TTNMCL70A15F205X",
        "partita_iva": None,
        "tipo_soggetto_id": "PF",
        "has_dati_societari": False,
    },
    "emittente": {
        "emittente_fiscale_id": 1,
        "emittente_codice": "EF01",
        "emittente_descrizione": "Emittente Principale",
        "user_emittente_fiscale_id": None,
        "ragione_sociale_completa": "Azienda SRL",
        "partita_iva": "01234567890",
        "tipo_soggetto_id": "PG",
        "has_dati_societari": True,
        "forma_giuridica_codice": "SRL",
        "codice_sdi": "ABCDEFG",
    },
}

_PROFILE_NO_EMITTENTE = {
    **_PROFILE_FULL,
    "emittente": None,
}

_REPO_PATH = "apps.core.api.me_view.CoreRepository"


class UserProfileViewTests(TestCase):

    # Scopo: Verifica che GET /me/ restituisca il profilo completo con envelope data
    # e arricchito con is_admin_globale.
    @patch(_REPO_PATH)
    def test_get_profile_success(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        # Copia per evitare contaminazione fra test (la view fa mutate)
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = dict(_PROFILE_FULL)
        MockRepo.return_value = mock_repo

        request = MagicMock()
        request.user = MagicMock()
        request.user.id = 1
        request.user.is_authenticated = True
        request.auth = None  # §8.3.6: test-only, skip identita del JWT

        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            mock_resp.return_value = MagicMock(status_code=200)
            response = view.get(request)

        mock_repo.get_user_profile.assert_called_once_with(1)
        # success_response chiamata con profilo arricchito di is_admin_globale
        profile_arg = mock_resp.call_args[0][0]
        self.assertIn("is_admin_globale", profile_arg)
        self.assertEqual(response.status_code, 200)

    # Scopo: Verifica che il profilo senza emittente (null) funziona correttamente.
    @patch(_REPO_PATH)
    def test_get_profile_includes_emittente_null(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = dict(_PROFILE_NO_EMITTENTE)
        MockRepo.return_value = mock_repo

        request = MagicMock()
        request.user = MagicMock()
        request.user.id = 2
        request.auth = None

        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            mock_resp.return_value = MagicMock(status_code=200)
            view.get(request)

        profile_arg = mock_resp.call_args[0][0]
        self.assertIsNone(profile_arg["emittente"])
        self.assertIn("is_admin_globale", profile_arg)

    # Scopo: super admin senza riga in user_emittenti_fiscali →
    # is_admin_globale=True. Caso "admin globale" del refactor
    # operatore-emittenti (Q1).
    @patch(_REPO_PATH)
    def test_is_admin_globale_admin_senza_emittente(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        # Profilo super admin con emittente del gestore globale (cascata 4b
        # di fn_get_user_profile) ma user_emittente_fiscale_id NULL.
        profile = dict(_PROFILE_FULL)
        profile["is_super_admin"] = True
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": None}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1; request.auth = None
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertTrue(mock_resp.call_args[0][0]["is_admin_globale"])

    # Scopo: super admin con riga in user_emittenti_fiscali →
    # is_admin_globale=False. Caso "admin di emittente" del refactor.
    @patch(_REPO_PATH)
    def test_is_admin_globale_admin_con_emittente(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        profile = dict(_PROFILE_FULL)
        profile["is_super_admin"] = True
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": 42}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1; request.auth = None
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertFalse(mock_resp.call_args[0][0]["is_admin_globale"])

    # Scopo: non super admin non e' mai admin globale (anche senza riga
    # in user_emittenti_fiscali).
    @patch(_REPO_PATH)
    def test_is_admin_globale_operativo(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        profile = dict(_PROFILE_FULL)
        profile["is_super_admin"] = False
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": None}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1; request.auth = None
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertFalse(mock_resp.call_args[0][0]["is_admin_globale"])

    # Scopo: Fallback resolver — quando il profilo dal repo NON contiene
    # is_super_admin/ruolo_applicativo (scenari pre-migration o fn DB
    # vecchie), la view usa PermissionResolver. Single source of truth
    # multi-face nel BE (no ricostruzione legacy ruolo_sistema).
    @patch("apps.core.api.me_view.PermissionResolver")
    @patch(_REPO_PATH)
    def test_profile_fallback_resolver_se_campi_assenti(
        self, MockRepo, MockResolver
    ):
        from apps.core.api.me_view import UserProfileView

        # Profilo SENZA i campi multi-face (caso fallback).
        profile = dict(_PROFILE_FULL)
        profile.pop("is_super_admin", None)
        profile.pop("ruolo_applicativo", None)
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo
        MockResolver.is_super_admin.return_value = True
        MockResolver.get_ruolo_applicativo.return_value = "OPERATORE"

        request = MagicMock()
        request.user = MagicMock()
        request.user.id = 1
        request.auth = None

        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)

        profile_arg = mock_resp.call_args[0][0]
        self.assertTrue(profile_arg["is_super_admin"])
        self.assertEqual(profile_arg["ruolo_applicativo"], "OPERATORE")
        MockResolver.is_super_admin.assert_called_once_with(request.user)
        MockResolver.get_ruolo_applicativo.assert_called_once_with(request.user)

    # Scopo: Verifica che un errore dal repository si propaga correttamente.
    @patch(_REPO_PATH)
    def test_get_profile_repository_error_propagates(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        mock_repo = MagicMock()
        mock_repo.get_user_profile.side_effect = ServiceError(
            code="E_CORE_PROFILE_NOT_FOUND",
            message="Profilo utente non trovato.",
        )
        MockRepo.return_value = mock_repo

        request = MagicMock()
        request.user = MagicMock()
        request.user.id = 999
        request.auth = None

        view = UserProfileView()
        with self.assertRaises(ServiceError) as ctx:
            view.get(request)

        self.assertEqual(ctx.exception.code, "E_CORE_PROFILE_NOT_FOUND")


class IdentitaDelJwtTests(TestCase):
    """§8.3.6: /me/ espone il blocco `identita` del JWT corrente
    (non una delle N identita attive scelta a caso)."""

    def test_token_none_ritorna_none(self):
        """Senza token (es. test legacy con request.auth=None): None."""
        from apps.core.api.me_view import UserProfileView
        request = MagicMock()
        request.auth = None
        self.assertIsNone(UserProfileView._identita_del_jwt(request))

    def test_claim_assente_ritorna_none(self):
        """Token presente ma senza claim identita_id: None (difensivo —
        in produzione JwtAuditAuthentication §8.3.4 rifiuta gia' questi
        token con 401 E_JWT_SENZA_IDENTITA prima di arrivare qui)."""
        from apps.core.api.me_view import UserProfileView
        token = MagicMock()
        token.get = MagicMock(return_value=None)
        request = MagicMock()
        request.auth = token
        self.assertIsNone(UserProfileView._identita_del_jwt(request))

    @patch("apps.core.api.me_view.AuthRepository")
    def test_claim_presente_delega_al_repo(self, MockRepo):
        """Claim presente -> chiama get_identita_dettaglio con le
        credenziali del JWT (guard anti-tampering: filtra anche
        auth_user_id oltre a identita_id)."""
        from apps.core.api.me_view import UserProfileView
        mock_repo = MagicMock()
        mock_repo.get_identita_dettaglio.return_value = {
            "id": 7, "ruolo_applicativo": "OPERATORE",
        }
        MockRepo.return_value = mock_repo

        token = MagicMock()
        token.get = MagicMock(return_value=7)
        request = MagicMock()
        request.auth = token
        request.user = MagicMock(id=42)

        result = UserProfileView._identita_del_jwt(request)

        self.assertEqual(result, {"id": 7, "ruolo_applicativo": "OPERATORE"})
        mock_repo.get_identita_dettaglio.assert_called_once_with(
            identita_id=7, auth_user_id=42,
        )

    @patch(_REPO_PATH)
    @patch("apps.core.api.me_view.AuthRepository")
    def test_profile_contiene_blocco_identita(self, MockAuth, MockRepo):
        """End-to-end della view: il profilo ritornato contiene la chiave
        `identita` popolata dal repo auth."""
        from apps.core.api.me_view import UserProfileView

        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = dict(_PROFILE_FULL)
        MockRepo.return_value = mock_repo

        mock_auth = MagicMock()
        mock_auth.get_identita_dettaglio.return_value = {
            "id": 7, "ruolo_applicativo": "OPERATORE", "attivo": True,
        }
        MockAuth.return_value = mock_auth

        token = MagicMock()
        token.get = MagicMock(return_value=7)
        request = MagicMock()
        request.auth = token
        request.user = MagicMock(id=42)

        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)

        profile_arg = mock_resp.call_args[0][0]
        self.assertEqual(profile_arg["identita"]["id"], 7)
        self.assertEqual(profile_arg["identita"]["ruolo_applicativo"], "OPERATORE")


class CoreRepositoryTests(TestCase):

    # Scopo: Verifica che il repository restituisce il JSONB dalla funzione DB.
    @patch("apps.core.db.core_repository.connection")
    def test_get_user_profile_returns_jsonb(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (_PROFILE_FULL,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = CoreRepository()
        result = repo.get_user_profile(1)

        mock_cursor.execute.assert_called_once_with(
            "SELECT script.fn_get_user_profile(%s)", [1]
        )
        self.assertEqual(result, _PROFILE_FULL)

    # Scopo: Verifica che funzione DB che restituisce NULL genera ServiceError.
    @patch("apps.core.db.core_repository.connection")
    def test_get_user_profile_null_result_raises_error(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = CoreRepository()
        with self.assertRaises(ServiceError) as ctx:
            repo.get_user_profile(999)

        self.assertEqual(ctx.exception.code, "E_CORE_PROFILE_NOT_FOUND")

    # Scopo: Verifica che fetchone() senza righe genera ServiceError.
    @patch("apps.core.db.core_repository.connection")
    def test_get_user_profile_no_row_raises_error(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = CoreRepository()
        with self.assertRaises(ServiceError) as ctx:
            repo.get_user_profile(999)

        self.assertEqual(ctx.exception.code, "E_CORE_PROFILE_NOT_FOUND")
