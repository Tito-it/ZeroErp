# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints categorie_clienti_listini (CRUD admin).
#        Mock del service + admin auth mockata. Nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_list_ok                     — GET lista
 2) test_get_list_with_filters           — filtri dimensionali passati al service
 3) test_get_detail_ok                   — GET dettaglio
 4) test_post_create_ok                  — POST minimo valido
 5) test_post_create_validation_error    — ServiceError validazione -> 400
 6) test_post_create_overlap_409         — ServiceError E_ANAG_MATRICE_OVERLAP -> 409
 7) test_patch_update_ok                 — PATCH mutabile
 8) test_patch_immutable_rifiutato       — PATCH FK dimensionale -> 400
 9) test_admin_required_get              — non admin -> 403
10) test_admin_required_post             — non admin -> 403
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = (
    "apps.anagrafiche.api.views_categorie_clienti_listini."
    "CategorieClientiListiniService"
)

_BASE = "/api/v1/anagrafiche/categorie-clienti-listini/"


class _BaseApiTest(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza
        #    questa riga il budget consumato dai test che girano prima
        #    arriva qui, e le richieste rispondono 429 invece del loro
        #    codice. Il difetto non e' del test che fallisce — e' di quello
        #    che non pulisce, e si vede solo in suite completa.
        cache.clear()


class TestGet(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_matrice.return_value = (
            [{"id": 1, "categoria_codice": "STANDARD", "listino_codice": "LST01"}], 1,
        )
        # Fase 4: la view inietta non_editable_fields nell'envelope.
        mock_svc_cls.return_value.get_non_editable_fields.return_value = [
            "categoria_cliente_id", "classe_utenza_id",
            "emittente_soggetto_ruolo_id", "utility_id",
        ]
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertIn("non_editable_fields", body["data"])
        self.assertIn("categoria_cliente_id", body["data"]["non_editable_fields"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_with_filters(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_matrice.return_value = ([], 0)
        mock_svc_cls.return_value.get_non_editable_fields.return_value = []
        resp = self.client.get(
            _BASE
            + "?categoria_cliente_id=1&utility_id=2&listino_id=4&valid_at=2026-06-01"
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_matrice.call_args.kwargs
        self.assertEqual(kwargs["categoria_cliente_id"], 1)
        self.assertEqual(kwargs["utility_id"], 2)
        self.assertEqual(kwargs["listino_id"], 4)
        self.assertEqual(str(kwargs["valid_at"]), "2026-06-01")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_detail_ok(self, mock_svc_cls, _perm, _auth):
        # Fase 4: il service inietta non_editable_fields direttamente nel detail.
        mock_svc_cls.return_value.get_matrice.return_value = {
            "id": 7,
            "non_editable_fields": [
                "categoria_cliente_id", "classe_utenza_id",
                "emittente_soggetto_ruolo_id", "utility_id",
            ],
        }
        resp = self.client.get(_BASE + "7/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        self.assertIn("non_editable_fields", resp.json()["data"])


class TestPost(_BaseApiTest):
    _OK_PAYLOAD = {
        "categoria_cliente_id": 1,
        "utility_id": 2,
        "emittente_soggetto_ruolo_id": 3,
        "listino_id": 4,
        "valido_dal": "2026-01-01",
    }

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_matrice.return_value = {"id": 10}
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK_PAYLOAD),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 10)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_validation_error(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_matrice.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE",
            message="Campo 'categoria_cliente_id' obbligatorio.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps({"utility_id": 2}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_VALIDAZIONE")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_overlap_409(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_matrice.side_effect = ServiceError(
            code="E_ANAG_MATRICE_OVERLAP",
            message="Riga sovrapposta.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK_PAYLOAD),
            content_type="application/json",
        )
        # E_ANAG_MATRICE_OVERLAP policy: http 409.
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_MATRICE_OVERLAP")


class TestPatch(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_update_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.update_matrice.return_value = {"id": 5}
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"listino_id": 99}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_immutable_rifiutato(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.update_matrice.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE",
            message="Le dimensioni della matrice sono immutabili.",
        )
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"categoria_cliente_id": 7}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_VALIDAZIONE")


class TestAuth(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_get(self, _perm, _auth):
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_post(self, _perm, _auth):
        resp = self.client.post(
            _BASE, data=json.dumps({}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)
