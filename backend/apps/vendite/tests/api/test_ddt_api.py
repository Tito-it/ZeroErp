# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint DDT di vendita (CRUD testata + righe, emetti,
#        cambio stato data-driven, push singolo a commessa) + endpoint di
#        evasione lato ordine (genera-ddt). Mock del service layer (funzioni
#        modulo), nessun accesso DB (CI-compatible). Verifica envelope, auth,
#        routing e propagazione parametri al service. Clone di test_ordini_api.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt        — 401 senza Authorization header
 2) test_list_ok_envelope         — 200 envelope paginato (mock service)
 3) test_create_ok                — 200 create DDT BOZZA (mock service)
 4) test_emetti_ok                — 200 emetti DRAFT->EMESSO (mock service)
 5) test_cambia_stato_ok          — 200 transizione generica (mock service)
 6) test_push_ok                  — 200 push singolo a commessa (mock service)
 7) test_patch_ddt_ok             — 200 PATCH testata (mock service)
 8) test_patch_riga_ok            — 200 PATCH riga (mock service)
 9) test_genera_ddt_da_ordine_ok  — 200 POST /ordini/<id>/genera-ddt/ (mock service)
10) test_genera_ddt_righe_selettive — righe evasione parziale propagate al service
"""

from unittest.mock import ANY, Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.ddt_service"

_BASE = "/api/v1/vendite/ddt/"
_ORD_BASE = "/api/v1/vendite/ordini/"


class TestDdtApi(JwtMockedApiTest):
    """Smoke test endpoint DDT di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ddt_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "DDT0001",
              "destinatario_denominazione": "Rossi SRL",
              "stato_codice_interno": "DRAFT"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "DDT0001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {"id": 7, "uid": "u-7", "numero": None}
        resp = self.client.post(
            _BASE, data={"billing_account_id": 3, "utility_id": 1},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        mock_crea.assert_called_once()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.emetti")
    def test_emetti_ok(self, mock_emetti, _auth) -> None:
        mock_emetti.return_value = {"id": 7, "numero": "DDT0007",
                                    "stato_codice": "EMESSO"}
        resp = self.client.post(
            f"{_BASE}7/emetti/", content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato_codice"], "EMESSO")
        mock_emetti.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.cambia_stato")
    def test_cambia_stato_ok(self, mock_cs, _auth) -> None:
        mock_cs.return_value = {"ddt_id": 7, "stato": "SPEDITO"}
        resp = self.client.post(
            f"{_BASE}7/cambia-stato/", data={"stato_codice": "SPEDITO"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "SPEDITO")
        mock_cs.assert_called_once_with(7, "SPEDITO")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.push_a_commessa")
    def test_push_ok(self, mock_push, _auth) -> None:
        mock_push.return_value = {"ddt_id": 7, "stato": "COMPLETATO"}
        resp = self.client.post(f"{_BASE}7/push/", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "COMPLETATO")
        # user propagato dal JWT (username dell'utente autenticato).
        mock_push.assert_called_once_with(7, user=ANY)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_ddt")
    def test_patch_ddt_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (DRF ha gia' parsato il body JSON).
        mock_upd.return_value = {"ddt_id": 7, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/", data={"data": "2026-06-10"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1]["data"], "2026-06-10")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_riga")
    def test_patch_riga_ok(self, mock_upd, _auth) -> None:
        mock_upd.return_value = {"ddt_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"quantita": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1], 3)


class TestOrdineGeneraDdtApi(JwtMockedApiTest):
    """Endpoint di evasione lato ordine: POST /ordini/<id>/genera-ddt/.

    Vive nel dominio SORGENTE (ordine) ma delega a `ddt_service.crea_ddt_da_ordine`
    (import locale nella view). Mock del service, nessun accesso DB.
    """

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt_da_ordine")
    def test_genera_ddt_da_ordine_ok(self, mock_gen, _auth) -> None:
        mock_gen.return_value = {"ddt_id": 42, "numero": None, "ordine_id": 7}
        resp = self.client.post(
            f"{_ORD_BASE}7/genera-ddt/", data={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["ddt_id"], 42)
        # Body vuoto -> None = evade tutto il residuo.
        mock_gen.assert_called_once_with(7, None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt_da_ordine")
    def test_genera_ddt_righe_selettive(self, mock_gen, _auth) -> None:
        # Evasione parziale: le righe {ordine_riga_id, qta_da_evadere} arrivano
        # normalizzate al service (unita' operativa).
        mock_gen.return_value = {"ddt_id": 43, "numero": None, "ordine_id": 7}
        resp = self.client.post(
            f"{_ORD_BASE}7/genera-ddt/",
            data={"righe": [{"ordine_riga_id": 11, "qta_da_evadere": "2"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_gen.assert_called_once_with(
            7, [{"ordine_riga_id": 11, "qta_da_evadere": "2"}],
        )
