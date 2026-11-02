# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API lookup utilities ammesse per tipo ruolo (core).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_lookup_utilities_per_ruolo_ef — GET utility ammesse per ruolo EF
 2) test_lookup_utilities_per_ruolo_fo — GET utility ammesse per ruolo FO
 3) test_lookup_utilities_per_ruolo_lista_vuota — Nessuna utility configurata
"""

from unittest.mock import Mock, patch

from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"


class LookupUtilitiesPerRuoloApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_lookup_utilities_per_ruolo_ef(self, mock_repo_cls, _auth):
        """GET /lookup/tipi-ruolo/EF/utilities/ → utility ammesse per emittente fiscale."""
        mock_repo_cls.return_value.list_utilities_per_ruolo.return_value = [
            {"id": 1, "codice": "EE", "descrizione": "Energia Elettrica"},
            {"id": 2, "codice": "GAS", "descrizione": "Gas Naturale"},
        ]
        resp = self.client.get("/api/v1/core/lookup/tipi-ruolo/EF/utilities/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 2)
        mock_repo_cls.return_value.list_utilities_per_ruolo.assert_called_once_with("EF")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_lookup_utilities_per_ruolo_fo(self, mock_repo_cls, _auth):
        """Stesso endpoint riusato per ruolo FORNITORE."""
        mock_repo_cls.return_value.list_utilities_per_ruolo.return_value = [
            {"id": 3, "codice": "TLC", "descrizione": "Telecomunicazioni"},
        ]
        resp = self.client.get("/api/v1/core/lookup/tipi-ruolo/FO/utilities/")
        self.assertEqual(resp.status_code, 200)
        mock_repo_cls.return_value.list_utilities_per_ruolo.assert_called_once_with("FO")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_lookup_utilities_per_ruolo_lista_vuota(self, mock_repo_cls, _auth):
        """Nessuna utility configurata per il ruolo → lista vuota (200)."""
        mock_repo_cls.return_value.list_utilities_per_ruolo.return_value = []
        resp = self.client.get("/api/v1/core/lookup/tipi-ruolo/CL/utilities/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["results"], [])
