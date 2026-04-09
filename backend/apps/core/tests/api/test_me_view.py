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
7) CoreRepositoryTests.test_get_user_profile_returns_jsonb
8) CoreRepositoryTests.test_get_user_profile_null_result_raises_error
9) CoreRepositoryTests.test_get_user_profile_no_row_raises_error
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
    "ruolo_sistema": "ADMIN",
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

        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            mock_resp.return_value = MagicMock(status_code=200)
            view.get(request)

        profile_arg = mock_resp.call_args[0][0]
        self.assertIsNone(profile_arg["emittente"])
        self.assertIn("is_admin_globale", profile_arg)

    # Scopo: ADMIN senza riga in user_emittenti_fiscali → is_admin_globale=True.
    # Caso "admin globale" del refactor operatore-emittenti (Q1).
    @patch(_REPO_PATH)
    def test_is_admin_globale_admin_senza_emittente(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        # Profilo ADMIN con emittente del gestore globale (cascata 4b di
        # fn_get_user_profile) ma user_emittente_fiscale_id NULL.
        profile = dict(_PROFILE_FULL)
        profile["ruolo_sistema"] = "ADMIN"
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": None}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertTrue(mock_resp.call_args[0][0]["is_admin_globale"])

    # Scopo: ADMIN con riga in user_emittenti_fiscali → is_admin_globale=False.
    # Caso "admin di emittente" del refactor.
    @patch(_REPO_PATH)
    def test_is_admin_globale_admin_con_emittente(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        profile = dict(_PROFILE_FULL)
        profile["ruolo_sistema"] = "ADMIN"
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": 42}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertFalse(mock_resp.call_args[0][0]["is_admin_globale"])

    # Scopo: OPERATIVO non e' mai admin (anche senza riga in user_emittenti_fiscali).
    @patch(_REPO_PATH)
    def test_is_admin_globale_operativo(self, MockRepo):
        from apps.core.api.me_view import UserProfileView

        profile = dict(_PROFILE_FULL)
        profile["ruolo_sistema"] = "OPERATIVO"
        profile["emittente"] = {**profile["emittente"], "user_emittente_fiscale_id": None}
        mock_repo = MagicMock()
        mock_repo.get_user_profile.return_value = profile
        MockRepo.return_value = mock_repo

        request = MagicMock(); request.user = MagicMock(); request.user.id = 1
        view = UserProfileView()
        with patch("apps.core.api.me_view.success_response") as mock_resp:
            view.get(request)
        self.assertFalse(mock_resp.call_args[0][0]["is_admin_globale"])

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

        view = UserProfileView()
        with self.assertRaises(ServiceError) as ctx:
            view.get(request)

        self.assertEqual(ctx.exception.code, "E_CORE_PROFILE_NOT_FOUND")


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
