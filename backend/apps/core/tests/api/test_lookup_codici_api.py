# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API lookup codici generica (core).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  CoreLookupCodiciApiTests.test_lookup_ok
2)  CoreLookupCodiciApiTests.test_lookup_v1_requires_jwt
3)  CoreLookupCodiciApiTests.test_lookup_rel_non_consentita
4)  CoreLookupCodiciApiTests.test_lookup_rel_mancante
5)  CoreLookupCodiciApiTests.test_lookup_filtro_search
6)  CoreLookupCodiciApiTests.test_lookup_order_col_codice
7)  CoreLookupCodiciApiTests.test_lookup_order_dir_desc
8)  CoreLookupCodiciApiTests.test_lookup_attivo_only_false
9)  CoreLookupCodiciApiTests.test_lookup_paginazione_parametri
10) CoreLookupCodiciApiTests.test_lookup_page_size_invalido
11) CoreLookupCodiciApiTests.test_lookup_page_invalida
12) CoreLookupCodiciApiTests.test_lookup_order_col_invalido
13) CoreLookupCodiciApiTests.test_lookup_order_dir_invalido
14) CoreLookupCodiciApiTests.test_lookup_lista_vuota_ok
15) CoreLookupCodiciApiTests.test_lookup_page_non_numerica
16) CoreLookupCodiciApiTests.test_lookup_page_size_non_numerica
17) (spostato sul DB vero: test_config_panel_registro_db, la lista e' in config.tabelle_gestibili)
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_CODICE_ROW = {"id": 1, "codice": "SDI_OK", "descrizione": "Consegnato"}

_LIST_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [_CODICE_ROW],
}

_URL = "/api/v1/core/lookup/codici/"


class CoreLookupCodiciApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Verifica il caso `test_lookup_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        response = self.client.get(_URL + "?rel=config.stati_sdi")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codice"], "SDI_OK")

    # Scopo: Verifica il caso `test_lookup_v1_requires_jwt`.
    def test_lookup_v1_requires_jwt(self):
        response = self.client.get(_URL + "?rel=config.stati_sdi")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_lookup_rel_non_consentita`: rel fuori whitelist → 400.
    @patch("apps.core.db.dbops_repository.TabelleGestibiliRepository.voce", return_value=None)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_rel_non_consentita(self, _mock_auth, _voce):
        response = self.client.get(_URL + "?rel=public.users")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_CORE_VALIDATION")


    # Scopo: Verifica il caso `test_lookup_rel_mancante`: rel vuota → 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_rel_mancante(self, _mock_auth):
        response = self.client.get(_URL)
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_CORE_VALIDATION")

    # Scopo: Verifica il caso `test_lookup_filtro_search`: search passato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_filtro_search(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(_URL + "?rel=config.stati_sdi&search=cons")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["search"], "cons")

    # Scopo: Verifica il caso `test_lookup_order_col_codice`: order_col=codice passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_order_col_codice(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(_URL + "?rel=config.stati_sdi&order_col=codice")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["order_col"], "codice")

    # Scopo: Verifica il caso `test_lookup_order_dir_desc`: order_dir=desc passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_order_dir_desc(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(_URL + "?rel=config.stati_sdi&order_dir=desc")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: Verifica il caso `test_lookup_attivo_only_false`: attivo_only=false passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_attivo_only_false(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(_URL + "?rel=config.stati_sdi&attivo_only=false")
        kwargs = mocked_list.call_args.kwargs
        self.assertFalse(kwargs["attivo_only"])

    # Scopo: Verifica il caso `test_lookup_paginazione_parametri`: la finestra
    #        arriva come `limit`/`offset` (dal 2026-10-21 un dialetto solo).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_paginazione_parametri(self, mocked_list, _mock_auth):
        mocked_list.return_value = {**_LIST_RESPONSE, "page": 2, "page_size": 10}
        self.client.get(_URL + "?rel=config.stati_sdi&limit=10&offset=10")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)

    # Scopo: Verifica il caso `test_lookup_page_size_invalido`: `page_size` non e'
    #        piu' un parametro della lookup (dal 2026-10-21): 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_page_size_invalido(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&page_size=10")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica il caso `test_lookup_page_invalida`: `page` non e' piu' un
    #        parametro della lookup (dal 2026-10-21): 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_page_invalida(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&page=2")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica il caso `test_lookup_order_col_invalido`: order_col non ammesso → 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_order_col_invalido(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&order_col=nome")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_CORE_VALIDATION")

    # Scopo: Verifica il caso `test_lookup_order_dir_invalido`: order_dir non ammesso → 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_order_dir_invalido(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&order_dir=up")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_CORE_VALIDATION")

    # Scopo: Verifica il caso `test_lookup_lista_vuota_ok`: risultato vuoto → 200 con count=0.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.views.fn_list_lookup_codici")
    def test_lookup_lista_vuota_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "count": 0,
            "page": 1,
            "page_size": 50,
            "total_pages": 0,
            "results": [],
        }
        response = self.client.get(_URL + "?rel=config.stati_sdi&search=xyz")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["search"], "xyz")
        self.assertIsNone(kwargs.get("__nonexistent__"))

    # Scopo: Verifica che page=abc (non numerico) restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_page_non_numerica(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&page=abc")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica che page_size=abc (non numerico) restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_page_size_non_numerica(self, _mock_auth):
        response = self.client.get(_URL + "?rel=config.stati_sdi&page_size=abc")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")
