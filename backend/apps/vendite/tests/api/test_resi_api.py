# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint resi di vendita (CRUD testata + righe,
#        conferma/annullo, DDT di ri-consegna, code di lavoro) + endpoint
#        righe-per-reso lato DDT. Mock del service layer (funzioni modulo),
#        nessun accesso DB (CI-compatible). Verifica envelope, auth, routing e
#        propagazione parametri al service. Clone di test_ddt_api.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt          — 401 senza Authorization header
 2) test_list_ok_envelope           — 200 envelope paginato (mock service)
 3) test_create_ok                  — 200 create reso da DDT (mock service)
 4) test_conferma_ok                — 200 conferma (fn madre, mock service)
 5) test_annulla_ok                 — 200 annullo (fn madre, mock service)
 6) test_riconsegna_ok_totale       — 200 body vuoto -> righe None (tutta la copertura)
 7) test_riconsegna_righe_parziali  — righe {resi_riga_id, qta} propagate al service
 8) test_patch_reso_ok              — 200 PATCH testata (mock service)
 9) test_righe_get_ok               — 200 lista righe (mock service)
10) test_patch_riga_ok              — 200 PATCH riga (mock service)
11) test_delete_riga_ok             — 200 DELETE riga (mock service)
12) test_da_accreditare_ok          — 200 coda accrediti (mock service)
13) test_da_riconsegnare_ok         — 200 coda ri-consegne (mock service)
14) test_ddt_righe_per_reso_ok      — 200 GET /ddt/<id>/righe-per-reso/ (mock)
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.resi_service"

_BASE = "/api/v1/vendite/resi/"
_DDT_BASE = "/api/v1/vendite/ddt/"


class TestResiApi(JwtMockedApiTest):
    """Smoke test endpoint resi di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_resi_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "RESO0001",
              "destinatario_denominazione": "Rossi SRL",
              "stato_codice_interno": "DRAFT",
              "ddt_origine_numero": "DDT0001"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "RESO0001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_reso")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {
            "id": 7, "uid": "u-7", "numero": None, "righe_ids": [71],
        }
        resp = self.client.post(
            _BASE,
            data={"ddt_id": 30,
                  "righe": [{"ddt_riga_id": 11, "tipo_reso_id": 1,
                             "qta_operativa": "3"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        payload = mock_crea.call_args[0][0]
        self.assertEqual(payload["ddt_id"], 30)
        self.assertEqual(payload["righe"][0]["ddt_riga_id"], 11)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.conferma_reso")
    def test_conferma_ok(self, mock_conf, _auth) -> None:
        mock_conf.return_value = {
            "reso_id": 7, "stato_precedente": "DRAFT", "stato": "CONFERMATO",
        }
        resp = self.client.post(
            f"{_BASE}7/conferma/", data={}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "CONFERMATO")
        mock_conf.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.annulla_reso")
    def test_annulla_ok(self, mock_ann, _auth) -> None:
        mock_ann.return_value = {
            "reso_id": 7, "stato_precedente": "CONFERMATO", "stato": "ANNULLATO",
        }
        resp = self.client.post(
            f"{_BASE}7/annulla/", data={}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "ANNULLATO")
        mock_ann.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.genera_ddt_riconsegna")
    def test_riconsegna_ok_totale(self, mock_ric, _auth) -> None:
        mock_ric.return_value = {"reso_id": 7, "ddt_id": 42, "numero": None}
        resp = self.client.post(
            f"{_BASE}7/genera-ddt-riconsegna/", data={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["ddt_id"], 42)
        # Body vuoto -> righe None = tutta la copertura residua, data None.
        mock_ric.assert_called_once_with(7, None, None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.genera_ddt_riconsegna")
    def test_riconsegna_righe_parziali(self, mock_ric, _auth) -> None:
        # Ri-spedizione parziale: righe {resi_riga_id, qta} (unita' BASE)
        # propagate al service cosi' come arrivano.
        mock_ric.return_value = {"reso_id": 7, "ddt_id": 43, "numero": None}
        resp = self.client.post(
            f"{_BASE}7/genera-ddt-riconsegna/",
            data={"righe": [{"resi_riga_id": 71, "qta": "3"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_ric.assert_called_once_with(
            7, [{"resi_riga_id": 71, "qta": "3"}], None,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_reso")
    def test_patch_reso_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (DRF ha gia' parsato il body JSON).
        mock_upd.return_value = {"reso_id": 7, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/", data={"data": "2026-07-13"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1]["data"], "2026-07-13")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_righe")
    def test_righe_get_ok(self, mock_righe, _auth) -> None:
        mock_righe.return_value = [
            {"id": 71, "reso_id": 7, "quantita": "3",
             "tipo_reso_codice_interno": "RESO_PER_RICONSEGNA",
             "stato_riconsegna": "DA_RICONSEGNARE", "qta_residua": "3"},
        ]
        resp = self.client.get(f"{_BASE}7/righe/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data[0]["stato_riconsegna"], "DA_RICONSEGNARE")
        mock_righe.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_riga")
    def test_patch_riga_ok(self, mock_upd, _auth) -> None:
        mock_upd.return_value = {"reso_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"qta_operativa": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.elimina_riga")
    def test_delete_riga_ok(self, mock_del, _auth) -> None:
        mock_del.return_value = {"reso_id": 7, "riga_id": 3, "deleted": True}
        resp = self.client.delete(f"{_BASE}7/righe/3/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])
        mock_del.assert_called_once_with(7, 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_accreditare")
    def test_da_accreditare_ok(self, mock_coda, _auth) -> None:
        mock_coda.return_value = (
            [{"resi_riga_id": 71, "reso_id": 7, "reso_numero": "RESO0001",
              "quantita": "3"}],
            1,
        )
        resp = self.client.get(
            f"{_BASE}da-accreditare/"
            "?billing_account_id=3&search=rossi&order_by=descrizione&order_dir=asc",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        # Filtro BA + search + sort propagati al service (path LIST).
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 3)
        self.assertEqual(kwargs["search"], "rossi")
        self.assertEqual(kwargs["order_by"], "descrizione")
        self.assertEqual(kwargs["order_dir"], "asc")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_riconsegnare")
    def test_da_riconsegnare_ok(self, mock_coda, _auth) -> None:
        mock_coda.return_value = (
            [{"resi_riga_id": 71, "reso_id": 7, "qta_resa": "5",
              "qta_riconsegnata": "2", "qta_residua": "3",
              "stato_riconsegna": "PARZIALE"}],
            1,
        )
        resp = self.client.get(
            f"{_BASE}da-riconsegnare/?search=acme&order_by=qta_residua&order_dir=desc",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["results"][0]["stato_riconsegna"], "PARZIALE")
        # search + sort propagati al service (path LIST).
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["search"], "acme")
        self.assertEqual(kwargs["order_by"], "qta_residua")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_righe_ddt_per_reso")
    def test_ddt_righe_per_reso_ok(self, mock_righe, _auth) -> None:
        # Endpoint lato dominio DDT (sorgente): alimenta il pannello
        # "crea reso" del drawer DDT.
        mock_righe.return_value = [
            {"ddt_riga_id": 11, "qta_consegnata": "10", "qta_gia_resa": "2",
             "qta_resa_residua": "8"},
        ]
        resp = self.client.get(f"{_DDT_BASE}30/righe-per-reso/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data[0]["qta_resa_residua"], "8")
        mock_righe.assert_called_once_with(30)
