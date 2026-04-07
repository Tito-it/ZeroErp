# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints emittenti fiscali (GET lista, GET dettaglio,
#        POST crea, PATCH update). Mock del service e JWT auth + bypass
#        del check admin via mock di IsAdminZeroERP.has_permission.
#        Nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_emittenti_list — GET lista paginata
 2) test_get_emittente_detail — GET dettaglio
 3) test_get_emittente_not_found — GET dettaglio inesistente
 4) test_post_emittente_ok — POST crea emittente
 5) test_post_emittente_missing_fields — POST senza campi obbligatori
 6) test_patch_emittente_ok — PATCH aggiorna campi editabili
 7) test_patch_emittente_not_found — PATCH emittente inesistente
 8) test_admin_required_get — utente non admin → 403 su GET lista
 9) test_admin_required_post — utente non admin → 403 su POST crea
 9b) test_ba_admin_required — utente non admin → 403 su sub-resource BA
 9c) test_utilities_admin_required — utente non admin → 403 su sub-resource Utilities
10) test_ba_list — GET lista mapping BA per emittente
11) test_ba_post_with_ba — POST crea mapping con billing_account_id specifico
12) test_ba_post_default — POST crea mapping default globale (senza ba_id)
13) test_ba_delete_ok — DELETE mapping
14) test_ba_delete_not_found — DELETE mapping inesistente
15) test_utilities_list — GET record utility per emittente
16) test_utilities_post_ok — POST crea record utility
17) test_utilities_post_missing_required — POST senza campi obbligatori
18) test_utilities_patch_ok — PATCH aggiorna record
19) test_utilities_delete_ok — DELETE record
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliService"
_BA_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliBillingAccountService"
_UT_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliUtilitiesService"


class TestEmittentiFiscaliGetApi(SimpleTestCase):
    """Test endpoint GET emittenti fiscali."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_emittenti_list(self, mock_svc_cls, _perm, _auth):
        """GET /anagrafiche/emittenti-fiscali/ — lista paginata."""
        mock_svc_cls.return_value.list_emittenti_fiscali.return_value = (
            [{"id": 1, "codice": "EF-001", "descrizione": "Sede principale"}], 1
        )
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_emittente_detail(self, mock_svc_cls, _perm, _auth):
        """GET /anagrafiche/emittenti-fiscali/{id}/ — dettaglio."""
        mock_svc_cls.return_value.get_emittente.return_value = {
            "id": 1, "codice": "EF-001", "descrizione": "Sede principale",
        }
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["codice"], "EF-001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_emittente_not_found(self, mock_svc_cls, _perm, _auth):
        """GET emittente inesistente → errore."""
        mock_svc_cls.return_value.get_emittente.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Emittente fiscale non trovato.",
        )
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/999/")
        self.assertIn(resp.status_code, (400, 404, 422))


class TestEmittentiFiscaliPostApi(SimpleTestCase):
    """Test endpoint POST emittenti fiscali."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_emittente_ok(self, mock_svc_cls, _perm, _auth):
        """POST /anagrafiche/emittenti-fiscali/ — crea emittente."""
        mock_svc_cls.return_value.crea_emittente.return_value = {
            "id": 1, "soggetto_ruolo_id": 50,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/",
            data=json.dumps({
                "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
                "codice": "EF-001",
                "descrizione": "Sede principale",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_emittente_missing_fields(self, mock_svc_cls, _perm, _auth):
        """POST senza codice/descrizione → errore validazione dal service."""
        mock_svc_cls.return_value.crea_emittente.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE", message="Codice emittente obbligatorio.",
        )
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/",
            data=json.dumps({
                "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_VALIDAZIONE")


class TestEmittentiFiscaliPatchApi(SimpleTestCase):
    """Test endpoint PATCH emittenti fiscali."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_emittente_ok(self, mock_svc_cls, _perm, _auth):
        """PATCH /anagrafiche/emittenti-fiscali/{id}/ — aggiorna campi editabili."""
        mock_svc_cls.return_value.update_emittente.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/emittenti-fiscali/1/",
            data=json.dumps({"descrizione": "Nuova descrizione", "split_payment_default": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_emittente_not_found(self, mock_svc_cls, _perm, _auth):
        """PATCH emittente inesistente → errore."""
        mock_svc_cls.return_value.update_emittente.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Emittente fiscale non trovato.",
        )
        resp = self.client.patch(
            "/api/v1/anagrafiche/emittenti-fiscali/999/",
            data=json.dumps({"descrizione": "X"}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_NOT_FOUND")


class TestEmittentiFiscaliAdminRequired(SimpleTestCase):
    """Verifica che gli endpoint richiedano effettivamente ruolo ADMIN."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_get(self, _perm, _auth):
        """Utente non admin → 403 su GET lista."""
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/")
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_post(self, _perm, _auth):
        """Utente non admin → 403 su POST crea."""
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/",
            data=json.dumps({
                "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
                "codice": "EF-001",
                "descrizione": "Test",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_ba_admin_required(self, _perm, _auth):
        """Utente non admin → 403 sui sub-resource BA."""
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/")
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_utilities_admin_required(self, _perm, _auth):
        """Utente non admin → 403 sui sub-resource Utilities."""
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/utilities/")
        self.assertEqual(resp.status_code, 403)


class TestEmittentiFiscaliBillingAccountApi(SimpleTestCase):
    """Test sub-resource mapping BA -> emittente."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_list(self, mock_svc_cls, _perm, _auth):
        """GET /emittenti-fiscali/<id>/billing-account/ — lista mapping."""
        mock_svc_cls.return_value.list_mapping.return_value = [
            {"id": 1, "billing_account_id": None, "is_default": True},
            {"id": 2, "billing_account_id": 5, "is_default": False},
        ]
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 2)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_post_with_ba(self, mock_svc_cls, _perm, _auth):
        """POST mapping con billing_account_id specifico."""
        mock_svc_cls.return_value.crea_mapping.return_value = {
            "id": 10, "emittente_id": 1, "billing_account_id": 5, "is_default": False,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/",
            data=json.dumps({"billing_account_id": 5}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["data"]["is_default"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_post_default(self, mock_svc_cls, _perm, _auth):
        """POST mapping default globale (senza billing_account_id)."""
        mock_svc_cls.return_value.crea_mapping.return_value = {
            "id": 10, "emittente_id": 1, "billing_account_id": None, "is_default": True,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["is_default"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_delete_ok(self, mock_svc_cls, _perm, _auth):
        """DELETE mapping."""
        mock_svc_cls.return_value.elimina_mapping.return_value = {"deleted": True}
        resp = self.client.delete("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/10/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["deleted"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_delete_not_found(self, mock_svc_cls, _perm, _auth):
        """DELETE mapping inesistente → errore."""
        mock_svc_cls.return_value.elimina_mapping.side_effect = ServiceError(
            code="E_ANAG_NOT_FOUND", message="Mapping non trovato.",
        )
        resp = self.client.delete("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/999/")
        self.assertIn(resp.status_code, (400, 404, 422))


class TestEmittentiFiscaliUtilitiesApi(SimpleTestCase):
    """Test sub-resource utilities per emittente."""

    def setUp(self) -> None:
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_list(self, mock_svc_cls, _perm, _auth):
        """GET /emittenti-fiscali/<id>/utilities/ — lista record."""
        mock_svc_cls.return_value.list_records.return_value = [
            {"id": 1, "utility_id": 1, "utility_codice": "EE", "attivo": True},
        ]
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/utilities/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_post_ok(self, mock_svc_cls, _perm, _auth):
        """POST crea record utility con campi obbligatori."""
        mock_svc_cls.return_value.crea_record.return_value = {"id": 10}
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/1/utilities/",
            data=json.dumps({
                "utility_id": 1,
                "arrotondamento_importi_dec": 2,
                "metodo_arrotondamento_importi": "HALF_UP",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 10)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_post_missing_required(self, mock_svc_cls, _perm, _auth):
        """POST senza utility_id → errore validazione."""
        mock_svc_cls.return_value.crea_record.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE", message="utility_id obbligatorio.",
        )
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/1/utilities/",
            data=json.dumps({"arrotondamento_importi_dec": 2}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_patch_ok(self, mock_svc_cls, _perm, _auth):
        """PATCH aggiorna record."""
        mock_svc_cls.return_value.aggiorna_record.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/emittenti-fiscali/1/utilities/5/",
            data=json.dumps({"attivo": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_delete_ok(self, mock_svc_cls, _perm, _auth):
        """DELETE record."""
        mock_svc_cls.return_value.elimina_record.return_value = {"deleted": True}
        resp = self.client.delete("/api/v1/anagrafiche/emittenti-fiscali/1/utilities/5/")
        self.assertEqual(resp.status_code, 200)
