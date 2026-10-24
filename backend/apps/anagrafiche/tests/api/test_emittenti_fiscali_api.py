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
 4) test_post_emittente_ok — POST crea emittente (forza attivo=false)
 4b) test_post_emittente_soggetto_no_piva — POST con soggetto senza P.IVA -> 400
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
14b) test_ba_summary_ok — GET summary mapping (has_default + count_specifici)
14c) test_ba_summary_empty — GET summary su emittente senza mapping
15) test_utilities_list — GET record utility per emittente
16) test_utilities_post_ok — POST crea record utility
17) test_utilities_post_missing_required — POST senza campi obbligatori
18) test_utilities_patch_ok — PATCH aggiorna record
19) test_utilities_delete_ok — DELETE record
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliService"
_BA_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliBillingAccountService"
_UT_SVC = "apps.anagrafiche.api.views_emittenti_fiscali.EmittentiFiscaliUtilitiesService"


class TestEmittentiFiscaliGetApi(JwtMockedApiTest):
    """Test endpoint GET emittenti fiscali."""

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
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_emittenti_list(self, mock_svc_cls, _perm, _auth):
        """GET /anagrafiche/emittenti-fiscali/ — lista paginata."""
        mock_svc_cls.return_value.list_emittenti_fiscali.return_value = (
            [{"id": 1, "codice": "EF-001", "ragione_sociale_completa": "Acme SRL"}], 1
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
            "id": 1, "codice": "EF-001", "ragione_sociale_completa": "Acme SRL",
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


class TestEmittentiFiscaliPostApi(JwtMockedApiTest):
    """Test endpoint POST emittenti fiscali."""

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
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_emittente_soggetto_no_piva(self, mock_svc_cls, _perm, _auth):
        """POST con soggetto senza P.IVA → 400 E_ANAG_VALIDAZIONE."""
        mock_svc_cls.return_value.crea_emittente.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE",
            message="L'emittente fiscale richiede un soggetto con Partita IVA.",
        )
        resp = self.client.post(
            "/api/v1/anagrafiche/emittenti-fiscali/",
            data=json.dumps({
                "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
                "codice": "EF-002",
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_VALIDAZIONE")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_emittente_missing_fields(self, mock_svc_cls, _perm, _auth):
        """POST senza codice → errore validazione dal service."""
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


class TestEmittentiFiscaliPatchApi(JwtMockedApiTest):
    """Test endpoint PATCH emittenti fiscali."""

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
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_emittente_ok(self, mock_svc_cls, _perm, _auth):
        """PATCH /anagrafiche/emittenti-fiscali/{id}/ — aggiorna campi editabili."""
        mock_svc_cls.return_value.update_emittente.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/emittenti-fiscali/1/",
            data=json.dumps({"regime_fiscale_rf": "RF01", "attivo": True}),
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
            data=json.dumps({"regime_fiscale_rf": "RF01"}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_NOT_FOUND")


class TestEmittentiFiscaliAdminRequired(JwtMockedApiTest):
    """Verifica che gli endpoint richiedano effettivamente ruolo ADMIN."""

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


class TestEmittentiFiscaliBillingAccountApi(JwtMockedApiTest):
    """Test sub-resource mapping BA -> emittente."""

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
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_list(self, mock_svc_cls, _perm, _auth):
        """GET /emittenti-fiscali/<id>/billing-account/ — lista mapping."""
        mock_svc_cls.return_value.list_mapping.return_value = (
            [
                {"id": 1, "billing_account_id": None, "is_default": True},
                {"id": 2, "billing_account_id": 5, "is_default": False},
            ],
            2,
        )
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 2)
        self.assertEqual(body["data"]["count"], 2)

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

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_summary_ok(self, mock_svc_cls, _perm, _auth):
        """GET /billing-account/summary/ — riepilogo mapping (has_default + count_specifici)."""
        mock_svc_cls.return_value.summary_mapping.return_value = {
            "has_default": True,
            "count_specifici": 7,
        }
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/summary/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["has_default"])
        self.assertEqual(body["data"]["count_specifici"], 7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_BA_SVC)
    def test_ba_summary_empty(self, mock_svc_cls, _perm, _auth):
        """GET summary su emittente senza mapping → has_default=false, count=0."""
        mock_svc_cls.return_value.summary_mapping.return_value = {
            "has_default": False,
            "count_specifici": 0,
        }
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/2/billing-account/summary/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["data"]["has_default"])
        self.assertEqual(body["data"]["count_specifici"], 0)


class TestEmittentiFiscaliUtilitiesApi(JwtMockedApiTest):
    """Test sub-resource utilities per emittente."""

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
    @patch(_PERM, return_value=True)
    @patch(_UT_SVC)
    def test_utilities_list(self, mock_svc_cls, _perm, _auth):
        """GET /emittenti-fiscali/<id>/utilities/ — matrice slot/override.

        Ritorna sempre tutte le utility ammesse per ruolo EF: alcune configurate
        (record_id valorizzato), altre no (record_id null, campi override null).
        """
        mock_svc_cls.return_value.list_records.return_value = [
            {
                "utility_id": 1, "utility_codice": "EE", "utility_descrizione": "Energia",
                "record_id": 100,
                "minimo_soglia_min": 0.5, "minimo_soglia_max": None,
                "arrotondamento_importi_dec": 2, "metodo_arrotondamento_importi": "HALF_UP",
                "record_attivo": True,
                "record_data_insert": None, "record_data_update": None,
            },
            {
                "utility_id": 2, "utility_codice": "GAS", "utility_descrizione": "Gas",
                "record_id": None,
                "minimo_soglia_min": None, "minimo_soglia_max": None,
                "arrotondamento_importi_dec": None, "metodo_arrotondamento_importi": None,
                "record_attivo": None,
                "record_data_insert": None, "record_data_update": None,
            },
        ]
        resp = self.client.get("/api/v1/anagrafiche/emittenti-fiscali/1/utilities/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        results = body["data"]["results"]
        self.assertEqual(len(results), 2)
        # Riga configurata
        self.assertEqual(results[0]["record_id"], 100)
        self.assertEqual(results[0]["metodo_arrotondamento_importi"], "HALF_UP")
        # Riga non configurata (slot vuoto)
        self.assertIsNone(results[1]["record_id"])
        self.assertIsNone(results[1]["metodo_arrotondamento_importi"])

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
