# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API elenco lotti fatturazione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeLottiListApiTests.test_list_lotti_ok
2) VenditeLottiListApiTests.test_list_lotti_v1_requires_jwt
3) VenditeLottiListApiTests.test_list_lotti_filtro_competenza_mese
4) VenditeLottiListApiTests.test_list_lotti_filtro_utility_id
5) VenditeLottiListApiTests.test_list_lotti_filtro_stato_lotto
6) VenditeLottiListApiTests.test_list_lotti_filtro_area_geografica_id
7) VenditeLottiListApiTests.test_list_lotti_filtro_tipo_doc_fiscale_id
8) VenditeLottiListApiTests.test_list_lotti_filtro_emittente_soggetto_ruolo_id
9) VenditeLottiListApiTests.test_list_lotti_paginazione_parametri
10) VenditeLottiListApiTests.test_list_lotti_page_size_invalido
11) VenditeLottiListApiTests.test_list_lotti_page_invalida
12) VenditeLottiListApiTests.test_list_lotti_senza_filtri_lista_vuota_ok
13) VenditeLottiListApiTests.test_list_lotti_scope_emittente_non_superuser
14) VenditeLottiListApiTests.test_list_lotti_scope_emittente_superuser
"""

from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client, SimpleTestCase


_LOTTO_ROW = {
    "id": 42,
    "codice": "LOT-2026-001",
    "competenza_mese": "2026-02-01",
    "tipo_lotto": "MASSIVO",
    "utility_id": 1,
    "utility_descrizione": "Energia Elettrica",
    "stato_lotto": "DRAFT",
    "stato_operativo": "APERTO",
    "stato_doc_fiscale_id": 3,
    "stato_doc_fiscale_descrizione": "Fattura emessa",
    "tipo_doc_fiscale_id": 1,
    "tipo_doc_fiscale_descrizione": "Fattura",
    "area_geografica_id": 2,
    "area_geografica_descrizione": "Nord",
    "emittente_soggetto_ruolo_id": 7,
    "data_insert": "2026-02-18T10:00:00+01:00",
    "user_insert": "zeroerp",
}

_LIST_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [_LOTTO_ROW],
}


class VenditeLottiListApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        cache.clear()
        self.client = Client()

    # Scopo: Verifica il caso `test_list_lotti_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"][0]["id"], 42)
        self.assertEqual(data["results"][0]["codice"], "LOT-2026-001")

    # Scopo: Verifica il caso `test_list_lotti_v1_requires_jwt`.
    def test_list_lotti_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_list_lotti_filtro_competenza_mese`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_competenza_mese(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?competenza_mese=2026-02-01")
        mocked_list.assert_called_once()
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 2, 1))

    # Scopo: Verifica il caso `test_list_lotti_filtro_utility_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_utility_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?utility_id=5")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["utility_id"], 5)

    # Scopo: Verifica il caso `test_list_lotti_filtro_stato_lotto`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_stato_lotto(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?stato_lotto=DRAFT")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["stato_lotto"], "DRAFT")

    # Scopo: Verifica il caso `test_list_lotti_filtro_area_geografica_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_area_geografica_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?area_geografica_id=2")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["area_geografica_id"], 2)

    # Scopo: Verifica il caso `test_list_lotti_filtro_tipo_doc_fiscale_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_tipo_doc_fiscale_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?tipo_doc_fiscale_id=1")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["tipo_doc_fiscale_id"], 1)

    # Scopo: Verifica il caso `test_list_lotti_filtro_emittente_soggetto_ruolo_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_emittente_soggetto_ruolo_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?emittente_soggetto_ruolo_id=10")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 10)

    # Scopo: Verifica il caso `test_list_lotti_paginazione_parametri`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_paginazione_parametri(self, mocked_list, _mock_auth):
        mocked_list.return_value = {**_LIST_RESPONSE, "page": 2, "page_size": 10}
        self.client.get("/api/v1/vendite/lotti/?page=2&page_size=10")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 10)

    # Scopo: Verifica il caso `test_list_lotti_page_size_invalido`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_lotti_page_size_invalido(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/lotti/?page_size=999")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VENDITE_VALIDATION")

    # Scopo: Verifica il caso `test_list_lotti_page_invalida`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_lotti_page_invalida(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/lotti/?page=0")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VENDITE_VALIDATION")

    # Scopo: Verifica il caso `test_list_lotti_senza_filtri_lista_vuota_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_senza_filtri_lista_vuota_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "count": 0,
            "page": 1,
            "page_size": 50,
            "total_pages": 0,
            "results": [],
        }
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["competenza_mese"])
        self.assertIsNone(kwargs["utility_id"])
        self.assertIsNone(kwargs["stato_lotto"])
        self.assertIsNone(kwargs["area_geografica_id"])
        self.assertIsNone(kwargs["tipo_doc_fiscale_id"])
        self.assertIsNone(kwargs["emittente_soggetto_ruolo_id"])

    # Scopo: Utente non superuser passa auth_user_id al service.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_scope_emittente_non_superuser(self, mocked_list, mock_auth, _mock_perm):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)

    # Scopo: Superuser passa auth_user_id=None (nessun filtro scope).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_scope_emittente_superuser(self, mocked_list, mock_auth):
        user = Mock()
        user.id = 1
        user.is_superuser = True
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/")
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["auth_user_id"])
