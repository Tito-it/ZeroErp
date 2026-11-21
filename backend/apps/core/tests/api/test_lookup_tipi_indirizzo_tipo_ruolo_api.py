# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API del picker dei tipi di indirizzo per un ruolo da assegnare
#        (`lookup/tipi-ruolo/<codice>/indirizzi/`): il soggetto a cui il ruolo
#        si assegna arriva in query string (R-1 di brief-db-fornitore-privato-
#        indirizzi, 2026-11-17). Il binding sul DB vero lo prova
#        `apps/anagrafiche/tests/db/test_tipi_indirizzo_proponibili_db.py`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_senza_soggetto — soggetto non scelto: al repository arriva `None`
 2) test_col_soggetto — l'uuid arriva normalizzato al repository
 3) test_soggetto_non_uuid — 400 `E_VALIDATION_INPUT`, il repository non si chiama
"""

from unittest.mock import Mock, patch

from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_URL = "/api/v1/core/lookup/tipi-ruolo/FO/indirizzi/"
_SOGGETTO = "019a2b3c-4d5e-7f60-8a9b-0c1d2e3f4a5b"


class LookupTipiIndirizzoTipoRuoloApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO, autospec=True)
    def test_senza_soggetto(self, mock_repo_cls, _auth):
        mock_repo_cls.return_value.list_tipi_indirizzo_proponibili_tipo_ruolo.return_value = []
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200)
        mock_repo_cls.return_value.list_tipi_indirizzo_proponibili_tipo_ruolo.assert_called_once_with(
            "FO", None,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO, autospec=True)
    def test_col_soggetto(self, mock_repo_cls, _auth):
        mock_repo_cls.return_value.list_tipi_indirizzo_proponibili_tipo_ruolo.return_value = []
        resp = self.client.get(_URL, {"soggetto_id": f" {_SOGGETTO.upper()} "})
        self.assertEqual(resp.status_code, 200)
        mock_repo_cls.return_value.list_tipi_indirizzo_proponibili_tipo_ruolo.assert_called_once_with(
            "FO", _SOGGETTO,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO, autospec=True)
    def test_soggetto_non_uuid(self, mock_repo_cls, _auth):
        resp = self.client.get(_URL, {"soggetto_id": "banana"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        mock_repo_cls.return_value.list_tipi_indirizzo_proponibili_tipo_ruolo.assert_not_called()
