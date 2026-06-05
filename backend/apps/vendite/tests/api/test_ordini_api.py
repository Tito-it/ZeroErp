# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint ordini di vendita (scheletro CRUD + lista
#        DEF-8 + export + conferma + push). Mock del service layer (funzioni
#        modulo), nessun accesso DB (CI-compatible). Verifica envelope, auth,
#        validazione formato export, overflow cap, routing.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt — 401 senza Authorization header
 2) test_list_ok_envelope — 200 envelope paginato (mock service)
 3) test_create_ok — 200 create ordine (mock service)
 4) test_conferma_ok — 200 conferma (mock service)
 5) test_push_ok — 200 push singolo a commessa (mock service)
 6) test_riepilogo_iva_ok — 200 riepilogo IVA aggregato (mock service)
 7) test_export_formato_invalido — 400 E_UI_EXPORT_FORMAT_INVALID
 8) test_export_overflow_cap — 422 E_UI_EXPORT_LIMIT_EXCEEDED su >cap righe
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.ordini_service"

_BASE = "/api/v1/vendite/ordini/"


class TestOrdiniApi(JwtMockedApiTest):
    """Smoke test endpoint ordini di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ordini_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "ORD0001", "ragione_sociale_completa": "Rossi SRL",
              "stato_codice_interno": "DRAFT"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "ORD0001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ordine")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {"id": 7, "uid": "u-7", "numero": "ORD0007"}
        resp = self.client.post(
            _BASE, data={"billing_account_id": 3, "utility_id": 1},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["numero"], "ORD0007")
        mock_crea.assert_called_once()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.conferma")
    def test_conferma_ok(self, mock_conf, _auth) -> None:
        mock_conf.return_value = {"ordine_id": 7, "stato": "CONFERMATO"}
        resp = self.client.post(f"{_BASE}7/conferma/", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "CONFERMATO")
        mock_conf.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.push_a_commessa")
    def test_push_ok(self, mock_push, _auth) -> None:
        mock_push.return_value = {"ordine_id": 7, "stato": "COMPLETATO"}
        resp = self.client.post(f"{_BASE}7/push/", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "COMPLETATO")
        mock_push.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_riepilogo_iva")
    def test_riepilogo_iva_ok(self, mock_riep, _auth) -> None:
        mock_riep.return_value = [
            {"ordine_id": 7, "iva_id": 1, "iva_codice": "22",
             "iva_aliquota": "22.00", "imponibile": "100.00",
             "imposta": "22.00", "totale_riga": "122.00"},
        ]
        resp = self.client.get(f"{_BASE}7/riepilogo-iva/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["iva_aliquota"], "22.00")
        mock_riep.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_ordine")
    def test_patch_ordine_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (non handle_post_json): body JSON gia' parsato
        # da DRF deve arrivare al service.
        mock_upd.return_value = {"ordine_id": 7, "updated": True}
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
        mock_upd.return_value = {"ordine_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"quantita": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_BASE}export/?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ordini_rows")
    def test_export_overflow_cap(self, mock_list, _auth) -> None:
        mock_list.return_value = ([], 50_000)
        resp = self.client.get(f"{_BASE}export/?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )
