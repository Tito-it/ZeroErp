# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API elenco fatture di un lotto.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  VenditeLottoFattureListApiTests.test_list_fatture_ok
2)  VenditeLottoFattureListApiTests.test_list_fatture_v1_requires_jwt
3)  VenditeLottoFattureListApiTests.test_list_fatture_filtro_stato_esecuzione
4)  VenditeLottoFattureListApiTests.test_list_fatture_sort_by_nominativo
5)  VenditeLottoFattureListApiTests.test_list_fatture_sort_by_totale_doc
6)  VenditeLottoFattureListApiTests.test_list_fatture_sort_dir_desc
7)  VenditeLottoFattureListApiTests.test_list_fatture_paginazione_parametri
8)  VenditeLottoFattureListApiTests.test_list_fatture_page_size_invalido
9)  VenditeLottoFattureListApiTests.test_list_fatture_page_invalida
12) VenditeLottoFattureListApiTests.test_list_fatture_sort_by_invalido
13) VenditeLottoFattureListApiTests.test_list_fatture_sort_dir_invalido
14) VenditeLottoFattureListApiTests.test_list_fatture_senza_filtri_lista_vuota_ok
15) VenditeLottoFattureListApiTests.test_list_fatture_scope_emittente_non_superuser
16) VenditeLottoFattureListApiTests.test_list_fatture_scope_emittente_superuser
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_FATTURA_ROW = {
    "id": 15,
    "lotto_id": 42,
    "fattura_id": 101,
    "stato_sdi_id": None,
    "stato_sdi_descrizione": None,
    "stato_doc_fiscale_id": 3,
    "stato_doc_fiscale_descrizione": "Fattura emessa",
    "stato_doc_fiscale_codice": "EMESSA",
    "stato_esecuzione": "OK",
    "numero": 234,
    "serie": None,
    "data": "2026-02-01",
    "billing_account_id": 8,
    "totale_doc": "1234.560000",
    "totale_a_pagare": "1234.560000",
    "soggetto_id": 55,
    "ragione_sociale_completa": "Mario Rossi Srl",
    "id_fiscale_univoco_cf_piva": "01234567890",
}

_LIST_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [_FATTURA_ROW],
}

_LOTTO_ID = 42


class VenditeLottoFattureListApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()
        self.url = f"/api/v1/vendite/lotti/{_LOTTO_ID}/fatture/"

    # Scopo: Verifica risposta 200 con payload corretto.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertEqual(payload["data"]["count"], 1)
        self.assertEqual(payload["data"]["results"][0]["fattura_id"], 101)

    # Scopo: Verifica che senza JWT risponda 401.
    def test_list_fatture_v1_requires_jwt(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica filtro stato_esecuzione passato correttamente al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_filtro_stato_esecuzione(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url, {"stato_esecuzione": "ERRORE"})
        mocked_list.assert_called_once()
        self.assertEqual(mocked_list.call_args.kwargs["stato_esecuzione"], "ERRORE")

    # Scopo: Verifica sort_by=nominativo passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_sort_by_nominativo(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url, {"sort_by": "nominativo"})
        mocked_list.assert_called_once()
        self.assertEqual(mocked_list.call_args.kwargs["sort_by"], "nominativo")

    # Scopo: Verifica sort_by=totale_doc passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_sort_by_totale_doc(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url, {"sort_by": "totale_doc"})
        mocked_list.assert_called_once()
        self.assertEqual(mocked_list.call_args.kwargs["sort_by"], "totale_doc")

    # Scopo: Verifica sort_dir=desc passato correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_sort_dir_desc(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url, {"sort_dir": "desc"})
        mocked_list.assert_called_once()
        self.assertEqual(mocked_list.call_args.kwargs["sort_dir"], "desc")

    # Scopo: Verifica parametri paginazione passati correttamente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_paginazione_parametri(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url, {"page": "3", "page_size": "25"})
        mocked_list.assert_called_once()
        self.assertEqual(mocked_list.call_args.kwargs["page"], 3)
        self.assertEqual(mocked_list.call_args.kwargs["page_size"], 25)

    # Scopo: Verifica che page_size non valido restituisca 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_fatture_page_size_invalido(self, _mock_auth):
        response = self.client.get(self.url, {"page_size": "999"})
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica che page non valida restituisca 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_fatture_page_invalida(self, _mock_auth):
        response = self.client.get(self.url, {"page": "0"})
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica che sort_by non valido restituisca 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_fatture_sort_by_invalido(self, _mock_auth):
        response = self.client.get(self.url, {"sort_by": "colonna_inesistente"})
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica che sort_dir non valido restituisca 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_fatture_sort_dir_invalido(self, _mock_auth):
        response = self.client.get(self.url, {"sort_dir": "sideways"})
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica che senza filtri opzionali il service riceva None per i filtri.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_senza_filtri_lista_vuota_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "count": 0,
            "page": 1,
            "page_size": 50,
            "total_pages": 0,
            "results": [],
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once()
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["stato_esecuzione"])
        self.assertNotIn("esclusa", kwargs)
        self.assertEqual(kwargs["lotto_id"], _LOTTO_ID)
        self.assertEqual(kwargs["sort_by"], "fattura_id")
        # La direzione assente resta assente: il verso lo decide il BB della
        # lista (date DESC), non un `"asc"` scritto nella view (2026-10-20, §6.1).
        self.assertIsNone(kwargs["sort_dir"])

    # Scopo: Utente non superuser passa auth_user_id al service.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_scope_emittente_non_superuser(self, mocked_list, mock_auth, _mock_perm):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url)
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)

    # Scopo: Superuser passa auth_user_id=None (nessun filtro scope).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotto_fatture")
    def test_list_fatture_scope_emittente_superuser(self, mocked_list, mock_auth):
        user = Mock()
        user.id = 1
        user.is_superuser = True
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url)
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["auth_user_id"])
