# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints clienti (PATCH update).
#        Mock del service e JWT auth, nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_patch_cliente_ok — PATCH aggiorna campi editabili
 2) test_patch_cliente_not_found — PATCH cliente inesistente
 3) test_get_clienti_propaga_scope_emittente — GET risolve scope via PermissionResolver
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_clienti.ClientiService"
_PERM = "apps.anagrafiche.api.views_clienti.PermissionResolver"


class TestClientiPatchApi(JwtMockedApiTest):
    """Test endpoint PATCH clienti."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza
        #    questa riga il budget consumato dai test che girano prima
        #    arriva qui, e le richieste rispondono 429 invece del loro
        #    codice. Il difetto non e' del test che fallisce — e' di quello
        #    che non pulisce, e si vede solo in suite completa.
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_cliente_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/clienti/{id}/ — aggiorna campi editabili."""
        mock_svc_cls.return_value.update_cliente.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/clienti/1/",
            data=json.dumps({"modalita_pagamento_id": 5, "garanzia_tipo": "F"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch(_SVC)
    def test_get_clienti_propaga_scope_emittente(
        self, mock_svc_cls, mock_perm, _auth,
    ):
        """GET /anagrafiche/clienti/ risolve emittente_ids via
        PermissionResolver e lo passa al service (refactor BE-3.5)."""
        mock_perm.get_emittenti_sr_ids.return_value = [11, 22]
        mock_svc_cls.return_value.list_clienti.return_value = ([], 0)
        resp = self.client.get("/api/v1/anagrafiche/clienti/")
        self.assertEqual(resp.status_code, 200)
        # Lo scope risolto dal PermissionResolver deve arrivare al service
        kwargs = mock_svc_cls.return_value.list_clienti.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids"], [11, 22])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_cliente_not_found(self, mock_svc_cls, _auth):
        """PATCH cliente inesistente → errore."""
        mock_svc_cls.return_value.update_cliente.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Cliente non trovato.",
        )
        resp = self.client.patch(
            "/api/v1/anagrafiche/clienti/999/",
            data=json.dumps({"modalita_pagamento_id": 5}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_NOT_FOUND")
