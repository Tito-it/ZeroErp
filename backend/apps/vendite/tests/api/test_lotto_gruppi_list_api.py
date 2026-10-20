# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API dell'elenco DOCUMENTI PRESI IN CARICO da un lotto — quelli
#        che una fattura non sono mai diventati compresi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeLottoGruppiListApiTests.test_list_gruppi_ok
2) VenditeLottoGruppiListApiTests.test_list_gruppi_richiede_jwt
3) VenditeLottoGruppiListApiTests.test_filtro_e_ordinamento_inoltrati
4) VenditeLottoGruppiListApiTests.test_order_dir_senza_colonna_non_annulla_il_default
5) VenditeLottoGruppiListApiTests.test_envelope_lista_standard
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_GRUPPO_ROW = {
    "gruppo_key": "ORDINE_VENDITA:01a06ce4-b46a-7a49-a72f-c07c29de47bb",
    "stato_esecuzione": "ERRORE",
    "errore_codice": "E_PULL_COMMESSA",
    "errore_messaggio": "ROOT source mancante per commessa 34137",
    "errore_quando": "2026-09-06T17:12:00+00:00",
    "riferimento": "ORD0036005",
    "tipo_gruppo": "ORDINE_VENDITA",
    "documento_apribile": True,
    "documento_id": 43927,
    "commessa_id": 34137,
    "commessa_codice": "CMM-PGTAPEF202-2026-000000004",
    "commesse_n": 1,
}

_LIST_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [_GRUPPO_ROW],
}

_LOTTO_ID = 10657


class VenditeLottoGruppiListApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()
        self.url = f"/api/v1/vendite/lotti/{_LOTTO_ID}/gruppi/"

    # 1) La rotta esiste e consegna la riga com'e'.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_gruppi")
    def test_list_gruppi_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        dati = response.json()["data"]
        self.assertEqual(dati["count"], 1)
        self.assertEqual(dati["results"][0]["riferimento"], "ORD0036005")
        self.assertEqual(dati["results"][0]["stato_esecuzione"], "ERRORE")

    # 2) Nessun accesso anonimo: e' una lista di dominio come le altre.
    def test_list_gruppi_richiede_jwt(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (401, 403))

    # 3) Filtro e ordinamento arrivano al service senza essere reinterpretati.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_gruppi")
    def test_filtro_e_ordinamento_inoltrati(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(
            self.url, {"stato_esecuzione": "ERRORE", "order_by": "riferimento",
                       "order_dir": "desc", "page": "2", "page_size": "10"},
        )
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["stato_esecuzione"], "ERRORE")
        self.assertEqual(kwargs["order_by"], "riferimento")
        self.assertEqual(kwargs["order_dir"], "desc")
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 10)

    # 4) ⚠️ IL VERSO GREZZO, non un default scritto nella view. Il repository ha
    #    un ordine di default suo — i FALLITI in cima — che si accende solo su
    #    `order_by` assente: una view che manda `"asc"` a vuoto lo annullerebbe,
    #    ed e' il difetto muto descritto in api.md (§parse_list_params).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_gruppi")
    def test_order_dir_senza_colonna_non_annulla_il_default(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get(self.url)
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])

    # 5) L'envelope è quello standard delle liste, e NIENTE ALTRO. ⛔ Il flag
    #    `perimetro_dichiarato` è sparito col problema che risolveva (rev DB
    #    2026-09-07): la lista legge anche gli esiti, che ci sono su entrambi i
    #    tipi di giro, quindi zero righe ha un significato solo. Il test guarda
    #    che non sia rimasto: un campo che non discrimina più niente è peggio di
    #    un campo assente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_gruppi")
    def test_envelope_lista_standard(self, mocked_list, _mock_auth):
        mocked_list.return_value = {**_LIST_RESPONSE, "count": 0, "results": []}
        dati = self.client.get(self.url).json()["data"]
        self.assertEqual(
            sorted(dati), ["count", "page", "page_size", "results", "total_pages"],
        )
