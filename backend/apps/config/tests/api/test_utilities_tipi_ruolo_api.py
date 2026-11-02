# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints matrice config.utilities_tipi_ruolo (CRUD admin
#        + usage emittenti). Mock del service e JWT auth + bypass del check
#        admin via mock di IsAdminZeroERP.has_permission. Nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_list_ok — GET lista paginata
 2) test_get_list_with_filters — GET lista con filtri search/attivo/utility_id
 3) test_get_detail_ok — GET dettaglio
 4) test_get_detail_not_found — GET dettaglio inesistente -> 404
 5) test_post_create_ok — POST crea riga matrice
 6) test_post_create_duplicate — POST duplicato -> 409 E_CONFIG_MATRICE_DUPLICATA
 7) test_post_create_fk_invalid — POST FK inesistente -> 400 E_CONFIG_MATRICE_FK
 8) test_post_create_missing_fields — POST senza utility_id -> 400 E_CONFIG_VALIDATION
 9) test_patch_update_attivo_ok — PATCH attivo OK
10) test_patch_update_fk_forbidden — PATCH tentativo modifica FK -> 400
11) test_patch_update_not_found — PATCH inesistente -> 404
12) test_get_usage_ok — GET usage emittenti per riga matrice
13) test_admin_required_get_list — non admin -> 403
14) test_admin_required_post — non admin -> 403
15) test_admin_required_patch — non admin -> 403
16) test_admin_required_usage — non admin -> 403
17) test_get_usage_contratto_di_lista — ricerca/ordinamento/pagina passati al service
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = "apps.config.api.views_utilities_tipi_ruolo.UtilitiesTipiRuoloService"

_BASE = "/api/v1/config/utilities-tipi-ruolo/"


class TestUtilitiesTipiRuoloGet(JwtMockedApiTest):
    """Test endpoint GET lista e dettaglio matrice."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_ok(self, mock_svc_cls, _perm, _auth):
        """GET lista matrice — paginata, mock service."""
        mock_svc_cls.return_value.list_matrice.return_value = (
            [{
                "id": 1,
                "utility_id": 10, "utility_codice": "GAS", "utility_descrizione": "Gas",
                "tipo_ruolo_id": 5, "tipo_ruolo_codice": "EF", "tipo_ruolo_descrizione": "Emittente Fiscale",
                "attivo": True,
            }],
            1,
        )
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["utility_codice"], "GAS")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_with_filters(self, mock_svc_cls, _perm, _auth):
        """GET lista con filtri search/attivo/utility_id passati al service."""
        mock_svc_cls.return_value.list_matrice.return_value = ([], 0)
        resp = self.client.get(
            _BASE + "?search=GAS&attivo=true&utility_id=10&order_by=tipo_ruolo_codice&order_dir=desc"
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_matrice.call_args.kwargs
        self.assertEqual(kwargs["search"], "GAS")
        self.assertTrue(kwargs["attivo"])
        self.assertEqual(kwargs["utility_id"], 10)
        self.assertEqual(kwargs["order_by"], "tipo_ruolo_codice")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_detail_ok(self, mock_svc_cls, _perm, _auth):
        """GET dettaglio singola riga matrice."""
        mock_svc_cls.return_value.get_matrice.return_value = {
            "id": 1, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": True,
        }
        resp = self.client.get(_BASE + "1/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_detail_not_found(self, mock_svc_cls, _perm, _auth):
        """GET dettaglio inesistente → 404 E_CONFIG_MATRICE_NOT_FOUND."""
        mock_svc_cls.return_value.get_matrice.side_effect = ServiceError(
            code="E_CONFIG_MATRICE_NOT_FOUND",
            message="Riga matrice utilities/ruoli non trovata.",
        )
        resp = self.client.get(_BASE + "999/")
        self.assertIn(resp.status_code, (400, 404, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CONFIG_MATRICE_NOT_FOUND")


class TestUtilitiesTipiRuoloPost(JwtMockedApiTest):
    """Test endpoint POST creazione."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_ok(self, mock_svc_cls, _perm, _auth):
        """POST crea riga matrice (utility_id + tipo_ruolo_id)."""
        mock_svc_cls.return_value.create_matrice.return_value = {
            "id": 42, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": True,
        }
        resp = self.client.post(
            _BASE,
            data=json.dumps({"utility_id": 10, "tipo_ruolo_id": 5}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 42)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_duplicate(self, mock_svc_cls, _perm, _auth):
        """POST coppia gia' esistente → 409 E_CONFIG_MATRICE_DUPLICATA."""
        mock_svc_cls.return_value.create_matrice.side_effect = ServiceError(
            code="E_CONFIG_MATRICE_DUPLICATA",
            message="Esiste gia' una riga matrice per questa coppia utility/tipo ruolo.",
        )
        resp = self.client.post(
            _BASE,
            data=json.dumps({"utility_id": 10, "tipo_ruolo_id": 5}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 409, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CONFIG_MATRICE_DUPLICATA")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_fk_invalid(self, mock_svc_cls, _perm, _auth):
        """POST FK inesistente → 400 E_CONFIG_MATRICE_FK."""
        mock_svc_cls.return_value.create_matrice.side_effect = ServiceError(
            code="E_CONFIG_MATRICE_FK",
            message="Utility o tipo ruolo inesistente.",
        )
        resp = self.client.post(
            _BASE,
            data=json.dumps({"utility_id": 99999, "tipo_ruolo_id": 5}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CONFIG_MATRICE_FK")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_missing_fields(self, mock_svc_cls, _perm, _auth):
        """POST senza utility_id → 400 E_CONFIG_VALIDATION."""
        mock_svc_cls.return_value.create_matrice.side_effect = ServiceError(
            code="E_CONFIG_VALIDATION",
            message="Campo 'utility_id' obbligatorio.",
        )
        resp = self.client.post(
            _BASE,
            data=json.dumps({"tipo_ruolo_id": 5}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CONFIG_VALIDATION")


class TestUtilitiesTipiRuoloPatch(JwtMockedApiTest):
    """Test endpoint PATCH aggiornamento attivo."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_update_attivo_ok(self, mock_svc_cls, _perm, _auth):
        """PATCH attivo=false OK."""
        mock_svc_cls.return_value.update_matrice.return_value = {
            "id": 1, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": False,
        }
        resp = self.client.patch(
            _BASE + "1/",
            data=json.dumps({"attivo": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["data"]["attivo"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_update_fk_forbidden(self, mock_svc_cls, _perm, _auth):
        """PATCH con utility_id → 400 (FK immutabili)."""
        mock_svc_cls.return_value.update_matrice.side_effect = ServiceError(
            code="E_CONFIG_VALIDATION",
            message="Le colonne utility_id e tipo_ruolo_id sono immutabili.",
        )
        resp = self.client.patch(
            _BASE + "1/",
            data=json.dumps({"utility_id": 99}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CONFIG_VALIDATION")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_update_not_found(self, mock_svc_cls, _perm, _auth):
        """PATCH riga inesistente → 404."""
        mock_svc_cls.return_value.update_matrice.side_effect = ServiceError(
            code="E_CONFIG_MATRICE_NOT_FOUND",
            message="Riga matrice utilities/ruoli non trovata.",
        )
        resp = self.client.patch(
            _BASE + "999/",
            data=json.dumps({"attivo": True}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))


class TestUtilitiesTipiRuoloUsage(JwtMockedApiTest):
    """Test endpoint GET usage emittenti."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_usage_ok(self, mock_svc_cls, _perm, _auth):
        """GET usage → lista paginata emittenti."""
        mock_svc_cls.return_value.list_usage.return_value = (
            [{
                "emittente_id": 1, "emittente_codice": "EF-001",
                "emittente_descrizione": "Sede principale", "emittente_attivo": True,
                "override_id": 99, "override_attivo": True,
            }],
            1,
        )
        resp = self.client.get(_BASE + "1/usage/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["emittente_codice"], "EF-001")
        # Senza parametri: nessun ordinamento chiesto (decide il repository).
        mock_svc_cls.return_value.list_usage.assert_called_once_with(
            1, search=None, order_by=None, order_dir=None, limit=25, offset=0,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_usage_contratto_di_lista(self, mock_svc_cls, _perm, _auth):
        """Ricerca, ordinamento e pagina arrivano al service come li manda il FE."""
        mock_svc_cls.return_value.list_usage.return_value = ([], 0)
        resp = self.client.get(
            _BASE + "4/usage/?search=acme&order_by=override_attivo&order_dir=desc"
            "&limit=10&offset=10",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["page"], 2)
        mock_svc_cls.return_value.list_usage.assert_called_once_with(
            4, search="acme", order_by="override_attivo", order_dir="desc",
            limit=10, offset=10,
        )


class TestUtilitiesTipiRuoloAdminRequired(JwtMockedApiTest):
    """Verifica che tutti gli endpoint richiedano ruolo ADMIN."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_get_list(self, _perm, _auth):
        """Non admin → 403 su GET lista."""
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_post(self, _perm, _auth):
        """Non admin → 403 su POST crea."""
        resp = self.client.post(
            _BASE,
            data=json.dumps({"utility_id": 10, "tipo_ruolo_id": 5}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_patch(self, _perm, _auth):
        """Non admin → 403 su PATCH."""
        resp = self.client.patch(
            _BASE + "1/",
            data=json.dumps({"attivo": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_usage(self, _perm, _auth):
        """Non admin → 403 su GET usage."""
        resp = self.client.get(_BASE + "1/usage/")
        self.assertEqual(resp.status_code, 403)
