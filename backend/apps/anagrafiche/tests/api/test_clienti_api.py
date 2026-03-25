# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints clienti (PATCH update).
#        Mock del service e JWT auth, nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_patch_cliente_ok — PATCH aggiorna campi editabili
 2) test_patch_cliente_not_found — PATCH cliente inesistente
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_clienti.ClientiService"


class TestClientiPatchApi(SimpleTestCase):
    """Test endpoint PATCH clienti."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_cliente_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/clienti/{id}/ — aggiorna campi editabili."""
        mock_svc_cls.return_value.update_cliente.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/clienti/1/",
            data=json.dumps({"iva_id": 5, "cliente_pa": "S"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_cliente_not_found(self, mock_svc_cls, _auth):
        """PATCH cliente inesistente → errore."""
        mock_svc_cls.return_value.update_cliente.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Cliente non trovato.",
        )
        resp = self.client.patch(
            "/api/v1/anagrafiche/clienti/999/",
            data=json.dumps({"iva_id": 5}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_NOT_FOUND")
