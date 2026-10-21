# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints anagrafiche.categorie_clienti (CRUD admin).
#        Mock del service + JWT auth + bypass admin check via mock di
#        IsAdminZeroERP.has_permission. Nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_list_ok — GET lista paginata
 2) test_get_list_with_filters — GET lista con filtri search/attivo/partecipa_promo
 3) test_get_detail_ok — GET dettaglio
 4) test_post_create_ok — POST crea categoria
 5) test_post_create_missing_codice — POST senza codice -> 400
 6) test_post_create_duplicate — POST duplicato -> E_ANAG_DUPLICATO
 7) test_patch_update_ok — PATCH OK
 8) test_patch_codice_forbidden — PATCH con codice -> 400 VALIDAZIONE
 9) test_admin_required_get — non admin -> 403
10) test_admin_required_post — non admin -> 403
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = "apps.anagrafiche.api.views_categorie_clienti.CategorieClientiService"

_BASE = "/api/v1/anagrafiche/categorie-clienti/"


class _BaseApiTest(JwtMockedApiTest):
    """Base test delle categorie clienti (gli effetti sul DB dei middleware li spegne `JwtMockedApiTest`)."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()


class TestCategorieClientiGet(_BaseApiTest):
    """Test endpoint GET lista e dettaglio categorie_clienti."""

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_categorie.return_value = (
            [{
                "id": 1, "codice": "STANDARD", "descrizione": "Cliente standard",
                "partecipa_promo": False, "ordinamento": 10, "attivo": True,
            }],
            1,
        )
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["codice"], "STANDARD")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_list_with_filters(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(
            _BASE + "?search=silv&attivo=true&partecipa_promo=true&order_by=codice&order_dir=desc"
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_categorie.call_args.kwargs
        self.assertEqual(kwargs["search"], "silv")
        self.assertTrue(kwargs["attivo"])
        self.assertTrue(kwargs["partecipa_promo"])
        self.assertEqual(kwargs["order_by"], "codice")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_get_detail_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.get_categoria.return_value = {
            "id": 3, "codice": "SILVER", "descrizione": "Cliente silver",
        }
        resp = self.client.get(_BASE + "3/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["codice"], "SILVER")


class TestCategorieClientiPost(_BaseApiTest):
    """Test endpoint POST create."""

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_categoria.return_value = {
            "id": 6, "codice": "VIP", "descrizione": "Cliente VIP",
            "partecipa_promo": True, "ordinamento": 60, "attivo": True,
        }
        payload = {
            "codice": "VIP",
            "descrizione": "Cliente VIP",
            "partecipa_promo": True,
            "ordinamento": 60,
        }
        resp = self.client.post(_BASE, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 6)
        mock_svc_cls.return_value.create_categoria.assert_called_once()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_missing_codice(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_categoria.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE",
            message="Campo 'codice' obbligatorio.",
        )
        resp = self.client.post(
            _BASE,
            data=json.dumps({"descrizione": "X"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_VALIDAZIONE")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_post_create_duplicate(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.create_categoria.side_effect = ServiceError(
            code="E_ANAG_DUPLICATO",
            message="Esiste gia' una categoria cliente con questo codice.",
        )
        resp = self.client.post(
            _BASE,
            data=json.dumps({"codice": "STANDARD", "descrizione": "X"}),
            content_type="application/json",
        )
        # error_policies mappa E_ANAG_DUPLICATO -> 409.
        self.assertIn(resp.status_code, (400, 409))
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_DUPLICATO")


class TestCategorieClientiPatch(_BaseApiTest):
    """Test endpoint PATCH update."""

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_update_ok(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.update_categoria.return_value = {
            "id": 3, "codice": "SILVER", "descrizione": "Silver v2",
        }
        resp = self.client.patch(
            _BASE + "3/",
            data=json.dumps({"descrizione": "Silver v2"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["descrizione"], "Silver v2")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_patch_codice_forbidden(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.update_categoria.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE",
            message="Il codice della categoria e' immutabile.",
        )
        resp = self.client.patch(
            _BASE + "3/",
            data=json.dumps({"codice": "NUOVO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_VALIDAZIONE")


class TestCategorieClientiAuth(_BaseApiTest):
    """Test permessi admin: senza permesso -> 403."""

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_get(self, _perm, _auth):
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 403)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=False)
    def test_admin_required_post(self, _perm, _auth):
        resp = self.client.post(
            _BASE,
            data=json.dumps({"codice": "X", "descrizione": "X"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class TestCategorieClientiBoolFilterParsing(_BaseApiTest):
    """Test edge case parsing dei filtri booleani lato view (qp_bool_optional).

    Blinda il comportamento: 'true'/'false' -> bool, vuoto -> None,
    'garbage' -> ValueError/400. Evita che una regressione nel parser renda
    silenziosamente inefficace un filtro attivo/partecipa_promo.
    """

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_filter_attivo_false_passa_come_false(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(_BASE + "?attivo=false")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_categorie.call_args.kwargs
        self.assertIs(kwargs["attivo"], False)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_filter_attivo_vuoto_passa_come_none(self, mock_svc_cls, _perm, _auth):
        # Contratto STRICT di apps.core.api.payload_validators.qp_bool_optional:
        # - chiave assente o valore vuoto ("") -> None (filtro non applicato)
        # - `true`/`false` -> bool (dal 2026-10-20 il solo vocabolario: §A6)
        # - valore non riconosciuto -> ValueError -> 400 (no coercion silenziosa)
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(_BASE + "?attivo=")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_categorie.call_args.kwargs
        self.assertIsNone(kwargs["attivo"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_filter_attivo_garbage_rifiutato_400(self, mock_svc_cls, _perm, _auth):
        # Strict: un valore non riconosciuto e' un errore client (400), non una
        # coercion silenziosa (regola del 2 core-be: famiglia qp_* opzionale strict).
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(_BASE + "?attivo=banana")
        self.assertEqual(resp.status_code, 400)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_filter_attivo_assente_passa_come_none(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_categorie.call_args.kwargs
        self.assertIsNone(kwargs["attivo"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM, return_value=True)
    @patch(_SVC)
    def test_filter_partecipa_promo_false_passa_come_false(self, mock_svc_cls, _perm, _auth):
        mock_svc_cls.return_value.list_categorie.return_value = ([], 0)
        resp = self.client.get(_BASE + "?partecipa_promo=false")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.list_categorie.call_args.kwargs
        self.assertIs(kwargs["partecipa_promo"], False)
