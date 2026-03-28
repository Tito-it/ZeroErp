# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints matrice indirizzi per ruolo.
#        Mock del service e JWT auth, nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_list — GET lista paginata
 2) test_get_detail — GET dettaglio
 3) test_post_ok — POST crea regola
 4) test_patch_ok — PATCH aggiorna
 5) test_patch_not_found — PATCH inesistente
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_matrice_indirizzi.MatriceIndirizziService"


class TestMatriceIndirizziGetApi(SimpleTestCase):

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_list(self, mock_svc_cls, _auth):
        """GET /anagrafiche/matrice-indirizzi-ruolo/ — lista."""
        mock_svc_cls.return_value.list_regole.return_value = ([{"id": 1}], 1)
        resp = self.client.get("/api/v1/anagrafiche/matrice-indirizzi-ruolo/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["count"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_detail(self, mock_svc_cls, _auth):
        """GET /anagrafiche/matrice-indirizzi-ruolo/{id}/ — dettaglio."""
        mock_svc_cls.return_value.get_regola.return_value = {"id": 1, "obbligatorio": True}
        resp = self.client.get("/api/v1/anagrafiche/matrice-indirizzi-ruolo/1/")
        self.assertEqual(resp.status_code, 200)


class TestMatriceIndirizziPostApi(SimpleTestCase):

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_ok(self, mock_svc_cls, _auth):
        """POST /anagrafiche/matrice-indirizzi-ruolo/ — crea."""
        mock_svc_cls.return_value.crea_regola.return_value = {"id": 10}
        resp = self.client.post(
            "/api/v1/anagrafiche/matrice-indirizzi-ruolo/",
            data=json.dumps({"tipo_ruolo_id": 2, "tipo_indirizzo_id": 8}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 10)


class TestMatriceIndirizziPatchApi(SimpleTestCase):

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/matrice-indirizzi-ruolo/{id}/ — aggiorna."""
        mock_svc_cls.return_value.update_regola.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/matrice-indirizzi-ruolo/1/",
            data=json.dumps({"obbligatorio": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_not_found(self, mock_svc_cls, _auth):
        """PATCH inesistente."""
        mock_svc_cls.return_value.update_regola.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Regola non trovata.",
        )
        resp = self.client.patch(
            "/api/v1/anagrafiche/matrice-indirizzi-ruolo/999/",
            data=json.dumps({"obbligatorio": False}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
