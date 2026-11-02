# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints fornitori (GET lista, GET dettaglio,
#        POST crea, PATCH update).
#        Mock del service e JWT auth, nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_fornitori_list — GET lista paginata
 2) test_get_fornitore_detail — GET dettaglio
 3) test_get_fornitore_not_found — GET dettaglio inesistente
 4) test_post_fornitore_ok — POST crea fornitore
 5) test_patch_fornitore_ok — PATCH aggiorna campi editabili
 6) test_patch_fornitore_not_found — PATCH fornitore inesistente
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_fornitori.FornitoriService"


class TestFornitoriGetApi(JwtMockedApiTest):
    """Test endpoint GET fornitori."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza
        #    questa riga il budget consumato dai test che girano prima
        #    arriva qui, e le richieste rispondono 429 invece del loro
        #    codice. Il difetto non e' del test che fallisce — e' di quello
        #    che non pulisce, e si vede solo in suite completa.
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_fornitori_list(self, mock_svc_cls, _auth):
        """GET /anagrafiche/fornitori/ — lista paginata."""
        mock_svc_cls.return_value.list_fornitori.return_value = (
            [{"id": 1, "codice": "FO-001"}], 1
        )
        resp = self.client.get("/api/v1/anagrafiche/fornitori/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_fornitore_detail(self, mock_svc_cls, _auth):
        """GET /anagrafiche/fornitori/{id}/ — dettaglio."""
        mock_svc_cls.return_value.get_fornitore.return_value = {"id": 1, "codice": "FO-001"}
        resp = self.client.get("/api/v1/anagrafiche/fornitori/1/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["codice"], "FO-001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_fornitore_not_found(self, mock_svc_cls, _auth):
        """GET fornitore inesistente → errore."""
        mock_svc_cls.return_value.get_fornitore.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Fornitore non trovato.",
        )
        resp = self.client.get("/api/v1/anagrafiche/fornitori/999/")
        self.assertIn(resp.status_code, (400, 404, 422))


class TestFornitoriPostApi(JwtMockedApiTest):
    """Test endpoint POST fornitori."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza
        #    questa riga il budget consumato dai test che girano prima
        #    arriva qui, e le richieste rispondono 429 invece del loro
        #    codice. Il difetto non e' del test che fallisce — e' di quello
        #    che non pulisce, e si vede solo in suite completa.
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_fornitore_ok(self, mock_svc_cls, _auth):
        """POST /anagrafiche/fornitori/ — crea fornitore."""
        mock_svc_cls.return_value.crea_fornitore.return_value = {
            "id": 1, "soggetto_ruolo_id": 50,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/fornitori/",
            data=json.dumps({"soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 1)


class TestFornitoriPatchApi(JwtMockedApiTest):
    """Test endpoint PATCH fornitori."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza
        #    questa riga il budget consumato dai test che girano prima
        #    arriva qui, e le richieste rispondono 429 invece del loro
        #    codice. Il difetto non e' del test che fallisce — e' di quello
        #    che non pulisce, e si vede solo in suite completa.
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_fornitore_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/fornitori/{id}/ — aggiorna campi editabili."""
        mock_svc_cls.return_value.update_fornitore.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/fornitori/1/",
            data=json.dumps({"rating": 90, "pec_email": "new@pec.it"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_fornitore_not_found(self, mock_svc_cls, _auth):
        """PATCH fornitore inesistente → errore."""
        mock_svc_cls.return_value.update_fornitore.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Fornitore non trovato.",
        )
        resp = self.client.patch(
            "/api/v1/anagrafiche/fornitori/999/",
            data=json.dumps({"rating": 50}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_NOT_FOUND")
