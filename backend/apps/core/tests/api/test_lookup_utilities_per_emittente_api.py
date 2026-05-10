# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API lookup utilities-per-emittente. Verifica:
#        - utente con emittente: repo chiamato con quell'id + ruolo
#        - super-admin senza emittente: repo chiamato con None (non
#          lista vuota — fix 2026-05-10).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_emittente_valorizzato_chiama_repo
 2) test_emittente_valorizzato_con_ruolo
 3) test_super_admin_senza_emittente_carica_tutte
 4) test_super_admin_senza_emittente_con_ruolo
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_PARAM_SVC = "apps.core.services.parameter_service.ParameterService"


class LookupUtilitiesPerEmittenteApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(id=42), None))
    @patch(_PARAM_SVC)
    @patch(_REPO)
    def test_emittente_valorizzato_chiama_repo(
        self, mock_repo_cls, mock_param_cls, _auth,
    ):
        """Utente con emittente fiscale -> repo chiamato con (id, None)."""
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 7
        mock_repo_cls.return_value.list_utilities_per_emittente.return_value = [
            {"id": 1, "codice": "EE", "codice_interno": "ENERGIA", "descrizione": "Energia"},
        ]
        resp = self.client.get("/api/v1/core/lookup/utilities-per-emittente/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        mock_repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            7, None,
        )

    @patch(_AUTH, return_value=(Mock(id=42), None))
    @patch(_PARAM_SVC)
    @patch(_REPO)
    def test_emittente_valorizzato_con_ruolo(
        self, mock_repo_cls, mock_param_cls, _auth,
    ):
        """Utente con emittente + ?ruolo=CL -> repo chiamato con (id, 'CL')."""
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 7
        mock_repo_cls.return_value.list_utilities_per_emittente.return_value = []
        resp = self.client.get(
            "/api/v1/core/lookup/utilities-per-emittente/?ruolo=cl",
        )
        self.assertEqual(resp.status_code, 200)
        # `cl` lower normalizzato a 'CL'.
        mock_repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            7, "CL",
        )

    @patch(_AUTH, return_value=(Mock(id=99), None))
    @patch(_PARAM_SVC)
    @patch(_REPO)
    def test_super_admin_senza_emittente_carica_tutte(
        self, mock_repo_cls, mock_param_cls, _auth,
    ):
        """Super-admin senza emittente -> repo chiamato con (None, None).
        NON deve ritornare [] in early exit.
        Fix 2026-05-10: prima la view ritornava lista vuota, ora delega
        al repo che applica solo il filtro per ruolo EF.
        """
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = None
        mock_repo_cls.return_value.list_utilities_per_emittente.return_value = [
            {"id": 1, "codice": "EE", "codice_interno": "ENERGIA", "descrizione": "Energia"},
            {"id": 2, "codice": "GAS", "codice_interno": "GAS", "descrizione": "Gas"},
            {"id": 3, "codice": "TLC", "codice_interno": "FONIA", "descrizione": "Fonia"},
        ]
        resp = self.client.get("/api/v1/core/lookup/utilities-per-emittente/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 3)
        mock_repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            None, None,
        )

    @patch(_AUTH, return_value=(Mock(id=99), None))
    @patch(_PARAM_SVC)
    @patch(_REPO)
    def test_super_admin_senza_emittente_con_ruolo(
        self, mock_repo_cls, mock_param_cls, _auth,
    ):
        """Super-admin senza emittente + ?ruolo=FO -> repo (None, 'FO').
        Filtro per ruolo soggetto resta applicabile anche senza EF.
        """
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = None
        mock_repo_cls.return_value.list_utilities_per_emittente.return_value = [
            {"id": 3, "codice": "TLC", "codice_interno": "FONIA", "descrizione": "Fonia"},
        ]
        resp = self.client.get(
            "/api/v1/core/lookup/utilities-per-emittente/?ruolo=FO",
        )
        self.assertEqual(resp.status_code, 200)
        mock_repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            None, "FO",
        )
