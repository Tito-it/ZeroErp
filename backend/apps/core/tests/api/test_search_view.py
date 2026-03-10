# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API ricerca universale soggetti e lookup (core).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) SearchUniversaleApiTests.test_search_ok
 2) SearchUniversaleApiTests.test_search_requires_jwt
 3) SearchUniversaleApiTests.test_search_q_obbligatorio
 4) SearchUniversaleApiTests.test_search_q_troppo_corto
 5) SearchUniversaleApiTests.test_search_tipo_ruolo_obbligatorio
 6) SearchUniversaleApiTests.test_search_tipo_ruolo_non_visibile
 7) SearchUniversaleApiTests.test_search_filtro_comune
 8) SearchUniversaleApiTests.test_search_paginazione
 9) SearchUniversaleApiTests.test_search_page_size_troppo_grande
10) SearchUniversaleApiTests.test_search_risultati_vuoti
11) SearchUniversaleApiTests.test_search_scope_emittente
12) SearchDetailApiTests.test_detail_ok
13) SearchDetailApiTests.test_detail_requires_jwt
14) SearchDetailApiTests.test_detail_tipo_ruolo_obbligatorio
15) SearchDetailApiTests.test_detail_tipo_ruolo_non_visibile
16) SearchDetailApiTests.test_detail_not_found
17) LookupTipiRuoliApiTests.test_lookup_tipi_ruoli_ok
18) LookupTipiRuoliApiTests.test_lookup_tipi_ruoli_requires_jwt
19) LookupComuniApiTests.test_lookup_comuni_ok
20) LookupComuniApiTests.test_lookup_comuni_requires_jwt
21) LookupComuniApiTests.test_lookup_comuni_q_troppo_corto
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client, SimpleTestCase


_SEARCH_URL = "/api/v1/core/search/"
_DETAIL_URL = "/api/v1/core/search/11111111-1111-1111-1111-111111111111/detail/"

_SOGGETTO_ROW = {
    "soggetto_id": "11111111-1111-1111-1111-111111111111",
    "soggetto_ruolo_id": 100,
    "tipo_ruolo_id": 1,
    "soggetto_codice": "S-0042",
    "ragione_sociale_completa": "Rossi Mario",
    "id_fiscale_univoco": "RSSMRA80A01F205X",
    "comune_id": 5,
    "comune_descrizione": "Bergamo",
    "utility_list": "GAS, EE",
}

_DETAIL_RESULT = {
    "tipo_ruolo": "CLIENTE",
    "soggetto_id": "11111111-1111-1111-1111-111111111111",
    "righe": [
        {
            "cliente_id": 10,
            "istanza": "IST-001",
            "utility": "GAS",
            "stato": "ATTIVO",
            "indirizzo": "Via Roma 12, Bergamo",
        }
    ],
}


class SearchUniversaleApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        cache.clear()
        self.client = Client()

    # Scopo: Verifica ricerca con risultati OK.
    @patch("apps.core.api.search_view.PermissionResolver.get_emittenti_ids", return_value=None)
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_ok(self, _mock_auth, mock_search, _mock_visibile, _mock_emittenti):
        mock_search.return_value = ([_SOGGETTO_ROW], 1)
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["ragione_sociale_completa"], "Rossi Mario")

    # Scopo: Verifica che senza JWT restituisce 401.
    def test_search_requires_jwt(self):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica che senza parametro q restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_q_obbligatorio(self, _mock_auth):
        response = self.client.get(_SEARCH_URL + "?tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che q con meno di 3 caratteri restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_q_troppo_corto(self, _mock_auth):
        response = self.client.get(_SEARCH_URL + "?q=ro&tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_VALIDATION")

    # Scopo: Verifica che senza tipo_ruolo_id restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_tipo_ruolo_obbligatorio(self, _mock_auth):
        response = self.client.get(_SEARCH_URL + "?q=rossi")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che tipo_ruolo_id non visibile restituisce 400.
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_tipo_ruolo_non_visibile(self, _mock_auth, _mock_visibile):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=3")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che comune_id viene passato al repository.
    @patch("apps.core.api.search_view.PermissionResolver.get_emittenti_ids", return_value=None)
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_filtro_comune(self, _mock_auth, mock_search, _mock_visibile, _mock_emittenti):
        mock_search.return_value = ([_SOGGETTO_ROW], 1)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&comune_id=5")
        kwargs = mock_search.call_args.kwargs
        self.assertEqual(kwargs["comune_id"], 5)

    # Scopo: Verifica che page e page_size vengono passati correttamente.
    @patch("apps.core.api.search_view.PermissionResolver.get_emittenti_ids", return_value=None)
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_paginazione(self, _mock_auth, mock_search, _mock_visibile, _mock_emittenti):
        mock_search.return_value = ([], 0)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&page=2&page_size=10")
        kwargs = mock_search.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)

    # Scopo: Verifica che page_size > 100 restituisce 400.
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_page_size_troppo_grande(self, _mock_auth, _mock_visibile):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&page_size=200")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica risultati vuoti → 200 con count=0.
    @patch("apps.core.api.search_view.PermissionResolver.get_emittenti_ids", return_value=None)
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_risultati_vuoti(self, _mock_auth, mock_search, _mock_visibile, _mock_emittenti):
        mock_search.return_value = ([], 0)
        response = self.client.get(_SEARCH_URL + "?q=zzzzz&tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    # Scopo: Verifica che emittente_ids viene passato al repository.
    @patch("apps.core.api.search_view.PermissionResolver.get_emittenti_ids", return_value=[7, 12])
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_scope_emittente(self, _mock_auth, mock_search, _mock_visibile, _mock_emittenti):
        mock_search.return_value = ([_SOGGETTO_ROW], 1)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1")
        kwargs = mock_search.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids"], [7, 12])


class SearchDetailApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        cache.clear()
        self.client = Client()

    # Scopo: Verifica dettaglio soggetto con risultato OK.
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_ok(self, _mock_auth, mock_detail, _mock_visibile):
        mock_detail.return_value = _DETAIL_RESULT
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["tipo_ruolo"], "CLIENTE")
        self.assertEqual(len(data["righe"]), 1)

    # Scopo: Verifica che senza JWT restituisce 401.
    def test_detail_requires_jwt(self):
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica che senza tipo_ruolo_id restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_tipo_ruolo_obbligatorio(self, _mock_auth):
        response = self.client.get(_DETAIL_URL)
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che tipo_ruolo_id non visibile restituisce 400.
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_tipo_ruolo_non_visibile(self, _mock_auth, _mock_visibile):
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=14")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che soggetto non trovato restituisce 404.
    @patch("apps.core.api.search_view.SearchRepository.is_tipo_ruolo_visibile", return_value=True)
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail", return_value=None)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_not_found(self, _mock_auth, _mock_detail, _mock_visibile):
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_NOT_FOUND")


_LOOKUP_TIPI_RUOLI_URL = "/api/v1/core/lookup/tipi-ruoli/"
_LOOKUP_COMUNI_URL = "/api/v1/core/lookup/comuni/"

_TIPI_RUOLI_RESULT = [
    {"id": 1, "codice": "CLIENTE", "descrizione": "Cliente"},
    {"id": 2, "codice": "FORNITORE", "descrizione": "Fornitore"},
]

_COMUNI_RESULT = [
    {"id": 5, "codice": "016024", "descrizione": "Bergamo"},
    {"id": 12, "codice": "016125", "descrizione": "Bergeggi"},
]


class LookupTipiRuoliApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        cache.clear()
        self.client = Client()

    # Scopo: Verifica lista tipi ruolo visibili OK.
    @patch("apps.core.api.search_view.SearchRepository.list_tipi_ruoli_visibili")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_tipi_ruoli_ok(self, _mock_auth, mock_list):
        mock_list.return_value = _TIPI_RUOLI_RESULT
        response = self.client.get(_LOOKUP_TIPI_RUOLI_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["codice"], "CLIENTE")

    # Scopo: Verifica che senza JWT restituisce 401.
    def test_lookup_tipi_ruoli_requires_jwt(self):
        response = self.client.get(_LOOKUP_TIPI_RUOLI_URL)
        self.assertEqual(response.status_code, 401)


class LookupComuniApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        cache.clear()
        self.client = Client()

    # Scopo: Verifica ricerca comuni OK.
    @patch("apps.core.api.search_view.SearchRepository.search_comuni")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_comuni_ok(self, _mock_auth, mock_search):
        mock_search.return_value = _COMUNI_RESULT
        response = self.client.get(_LOOKUP_COMUNI_URL + "?q=berg")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["results"]), 2)

    # Scopo: Verifica che senza JWT restituisce 401.
    def test_lookup_comuni_requires_jwt(self):
        response = self.client.get(_LOOKUP_COMUNI_URL + "?q=berg")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica che q con meno di 2 caratteri restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_lookup_comuni_q_troppo_corto(self, _mock_auth):
        response = self.client.get(_LOOKUP_COMUNI_URL + "?q=b")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")
