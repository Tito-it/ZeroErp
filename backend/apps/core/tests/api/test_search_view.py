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
 6) SearchUniversaleApiTests.test_search_tipo_ruolo_non_visibile — lo decide il DB, la view passa
 7) SearchUniversaleApiTests.test_search_paginazione
 8) SearchUniversaleApiTests.test_search_page_size_troppo_grande
 9) SearchUniversaleApiTests.test_search_risultati_vuoti
10) SearchUniversaleApiTests.test_search_scope_emittente
11) SearchUniversaleApiTests.test_search_order_by_valido
12) SearchUniversaleApiTests.test_search_order_by_invalido
13) SearchUniversaleApiTests.test_search_order_dir_invalido
14) SearchDetailApiTests.test_detail_ok
15) SearchDetailApiTests.test_detail_requires_jwt
16) SearchDetailApiTests.test_detail_tipo_ruolo_obbligatorio
17) SearchDetailApiTests.test_detail_tipo_ruolo_non_visibile — lo decide il DB, la view passa
18) SearchDetailApiTests.test_detail_not_found
19) SearchDetailApiTests.test_detail_scope_emittente
20) SearchDetailApiTests.test_detail_utility_id_fuori_integer_400 — vuoto = assente, oltre `integer` = 400
21) LookupTipiRuoliApiTests.test_lookup_tipi_ruoli_ok
22) LookupTipiRuoliApiTests.test_lookup_tipi_ruoli_requires_jwt
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_SEARCH_URL = "/api/v1/core/search/"
_DETAIL_URL = "/api/v1/core/search/11111111-1111-1111-1111-111111111111/detail/"

_SOGGETTO_ROW = {
    "soggetto_id": "11111111-1111-1111-1111-111111111111",
    "soggetto_ruolo_id": 100,
    "tipo_ruolo_id": 1,
    "soggetto_codice": "S-0042",
    "ragione_sociale_completa": "Rossi Mario",
    "id_fiscale_univoco": "RSSMRA80A01F205X",
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


class SearchUniversaleApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Verifica ricerca con risultati OK.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_ok(self, _mock_auth, mock_search):
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
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che senza tipo_ruolo_id restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_tipo_ruolo_obbligatorio(self, _mock_auth):
        response = self.client.get(_SEARCH_URL + "?q=rossi")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: ⛔ «Il ruolo e' ricercabile» lo decide il DB (Q-2 di
    #        brief-db-codici-non-trovato-email-e-permessi, 2026-10-10): la
    #        view non lo pre-controlla e passa il ruolo alla funzione, che
    #        risponde 404 `E_TIPO_RUOLO_NON_RICERCABILE` (provato sul DB vero
    #        in `core/tests/db/test_search_detail_non_trovato_db.py`). Un
    #        valore oltre `integer` resta un 400 prima del DB.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti", return_value=([], 0))
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_tipo_ruolo_non_visibile(self, _mock_auth, mock_search):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_search.call_args.kwargs["tipo_ruolo_id"], 3)
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=3000000000")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mock_search.call_count, 1)

    # Scopo: Verifica che page e page_size vengono passati correttamente.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_paginazione(self, _mock_auth, mock_search):
        mock_search.return_value = ([], 0)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&limit=10&offset=10")
        kwargs = mock_search.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)

    # Scopo: dal 2026-10-21 la ricerca pagina con `limit`/`offset`: `page_size`
    #        e' un 400, e cosi' un `limit` oltre il massimo (100): niente riduzione muta.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_page_size_troppo_grande(self, _mock_auth, mock_search):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&page_size=50")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&limit=200")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")
        mock_search.assert_not_called()

    # Scopo: Verifica risultati vuoti → 200 con count=0.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_risultati_vuoti(self, _mock_auth, mock_search):
        mock_search.return_value = ([], 0)
        response = self.client.get(_SEARCH_URL + "?q=zzzzz&tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    # Scopo: ⭐ Il perimetro lo fa la RLS (R-4, 2026-10-08): la view non
    #        calcola ne' passa piu' uno scope emittente al repository.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_scope_emittente(self, _mock_auth, mock_search):
        mock_search.return_value = ([_SOGGETTO_ROW], 1)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1")
        self.assertNotIn("emittente_ids", mock_search.call_args.kwargs)

    # Scopo: Verifica che order_by e order_dir vengono passati al repository.
    @patch("apps.core.api.search_view.SearchRepository.search_soggetti")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_order_by_valido(self, _mock_auth, mock_search):
        mock_search.return_value = ([_SOGGETTO_ROW], 1)
        self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&order_by=soggetto_codice&order_dir=DESC")
        kwargs = mock_search.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "soggetto_codice")
        self.assertEqual(kwargs["order_dir"], "DESC")

    # Scopo: Verifica che order_by con colonna non ammessa restituisce 400.
    # ⭐ `utility_list` e' una colonna VERA della risposta, ma non ordinabile
    #    dal 2026-10-10 (brief-db-ricerca-universale-tetto-10000 D-2): il 400
    #    educato arriva qui, non dal rifiuto del DB.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_order_by_invalido(self, _mock_auth):
        for colonna in ("colonna_inesistente", "utility_list"):
            with self.subTest(colonna=colonna):
                response = self.client.get(
                    _SEARCH_URL + f"?q=rossi&tipo_ruolo_id=1&order_by={colonna}"
                )
                self.assertEqual(response.status_code, 400)
                body = response.json()["error"]
                self.assertEqual(body["code"], "E_SEARCH_VALIDATION")

    # Scopo: Verifica che order_dir con valore non valido restituisce 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_search_order_dir_invalido(self, _mock_auth):
        response = self.client.get(_SEARCH_URL + "?q=rossi&tipo_ruolo_id=1&order_by=soggetto_codice&order_dir=RANDOM")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_VALIDATION")


class SearchDetailApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Verifica dettaglio soggetto con risultato OK.
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_ok(self, _mock_auth, mock_detail):
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

    # Scopo: ⛔ Come la lista: il ruolo ricercabile lo decide il DB, la view
    #        passa il valore (oltre `integer` resta un 400 prima del DB).
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail", return_value=_DETAIL_RESULT)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_tipo_ruolo_non_visibile(self, _mock_auth, mock_detail):
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=14")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_detail.call_args.kwargs["tipo_ruolo_id"], 14)
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=3000000000")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mock_detail.call_count, 1)

    # Scopo: Verifica che soggetto non trovato restituisce 404.
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail", return_value=None)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_not_found(self, _mock_auth, _mock_detail):
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_SEARCH_NOT_FOUND")

    # Scopo: ⭐ Come la lista: nel dettaglio il perimetro e' della RLS, e la
    #        view non passa uno scope emittente al repository.
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_scope_emittente(self, _mock_auth, mock_detail):
        mock_detail.return_value = _DETAIL_RESULT
        self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1")
        self.assertNotIn("emittente_ids", mock_detail.call_args.kwargs)

    # Scopo: `utility_id` va a `p_utility_id integer`: un valore oltre il tetto
    #        e' un 400 prima del DB (non un 500 da funzione non risolta), un
    #        valore vuoto e' «assente» (2026-10-09, BB `qp_int_optional`).
    @patch("apps.core.api.search_view.SearchRepository.get_search_detail")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_detail_utility_id_fuori_integer_400(self, _mock_auth, mock_detail):
        mock_detail.return_value = _DETAIL_RESULT
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1&utility_id=3000000000")
        self.assertEqual(response.status_code, 400)
        mock_detail.assert_not_called()
        response = self.client.get(_DETAIL_URL + "?tipo_ruolo_id=1&utility_id=%20")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(mock_detail.call_args.kwargs["utility_id"])


_LOOKUP_TIPI_RUOLI_URL = "/api/v1/core/lookup/tipi-ruoli/"

_TIPI_RUOLI_RESULT = [
    {"id": 1, "codice": "CLIENTE", "descrizione": "Cliente"},
    {"id": 2, "codice": "FORNITORE", "descrizione": "Fornitore"},
]


class LookupTipiRuoliApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
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
