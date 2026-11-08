# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API pratiche (lista, dettaglio, creazione,
#        aggiornamento, stato, assegnazione, giornale).
#        Mock services, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) PraticheApiTests.test_get_lista_pratiche_ok
 2) PraticheApiTests.test_get_lista_pratiche_con_search
 3) PraticheApiTests.test_get_lista_pratiche_errore_senza_emittente
 4) PraticheApiTests.test_post_crea_pratica_ok
 5) PraticheApiTests.test_post_crea_pratica_con_contesto
 6) PraticheApiTests.test_post_crea_pratica_invalid_json
 7) PraticheApiTests.test_get_dettaglio_pratica_ok
 8) PraticheApiTests.test_get_dettaglio_pratica_display_fields
 9) PraticheApiTests.test_get_dettaglio_pratica_non_trovata
10) PraticheApiTests.test_patch_aggiorna_pratica_ok
11) PraticheApiTests.test_post_stato_pratica_ok
12) PraticheApiTests.test_post_assegnazione_pratica_ok
13) PraticheApiTests.test_get_giornale_pratica_ok
14) PraticheApiTests.test_v1_richiede_jwt
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


def _mock_pratica_row(pratica_id: int = 1) -> dict:
    return {
        "id": pratica_id,
        "emittente_fiscale_id": 10,
        "tipo_prestazione_id": 5,
        "soggetto_id": None,
        "soggetto_ruolo_id": None,
        "istanza_utility_id": None,
        "stato_id": 1,
        "priorita_id": 2,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "pratica_padre_id": None,
        "flusso_origine_id": None,
        "canale_origine_id": None,
        "codice": "PRA-0000001",
        "descrizione": "Test",
        "data_apertura": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test",
        "tipo_prestazione_codice": "MANUTENZIONE",
        "tipo_prestazione_descrizione": "Manutenzione",
        "stato_codice_interno": "BOZZA",
        "stato_descrizione": "Bozza",
        "priorita_codice_interno": "NORMALE",
        "priorita_descrizione": "Normale",
        "soggetto_display": None,
        "risorsa_umana_display": None,
        "unita_organizzativa_descrizione": None,
    }


class PraticheApiTests(JwtMockedApiTest):

    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Scopo: Verifica GET lista pratiche con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.cerca_pratiche")
    def test_get_lista_pratiche_ok(self, mock_cerca, _auth):
        mock_cerca.return_value = ([_mock_pratica_row()], 1)

        response = self.client.get(
            "/api/v1/pratiche/?emittente_fiscale_id=10",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(len(body["data"]["results"]), 1)

    # Scopo: Verifica che il parametro search venga passato al service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.cerca_pratiche")
    def test_get_lista_pratiche_con_search(self, mock_cerca, _auth):
        mock_cerca.return_value = ([_mock_pratica_row()], 1)

        response = self.client.get(
            "/api/v1/pratiche/?emittente_fiscale_id=10&search=PRA-000",
        )
        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_cerca.call_args[1]
        self.assertEqual(call_kwargs["search"], "PRA-000")

    # Scopo: Verifica errore senza emittente_fiscale_id.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_get_lista_pratiche_errore_senza_emittente(self, _auth):
        response = self.client.get("/api/v1/pratiche/")
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica POST creazione pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_pratica")
    def test_post_crea_pratica_ok(self, mock_crea, _auth):
        mock_crea.return_value = 42

        response = self.client.post(
            "/api/v1/pratiche/",
            data=json.dumps({
                "emittente_fiscale_id": 10,
                "tipo_prestazione_id": 5,
                "priorita_id": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["pratica_id"], 42)
        self.assertEqual(body["data"]["status"], "ok")

    # Scopo: Verifica POST creazione con contesto anagrafico (soggetto + ruolo + istanza).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_pratica")
    def test_post_crea_pratica_con_contesto(self, mock_crea, _auth):
        mock_crea.return_value = 50

        response = self.client.post(
            "/api/v1/pratiche/",
            data=json.dumps({
                "emittente_fiscale_id": 10,
                "tipo_prestazione_id": 5,
                "priorita_id": 2,
                "soggetto_id": "aaa-bbb-ccc",
                "soggetto_ruolo_id": 100,
                "istanza_utility_id": 200,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_crea.call_args[1]
        self.assertEqual(call_kwargs["soggetto_ruolo_id"], 100)
        self.assertEqual(call_kwargs["istanza_utility_id"], 200)

    # Scopo: Verifica errore con JSON non valido.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_post_crea_pratica_invalid_json(self, _auth):
        response = self.client.post(
            "/api/v1/pratiche/",
            data="{invalid",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica GET dettaglio pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository", autospec=True)
    def test_get_dettaglio_pratica_ok(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = _mock_pratica_row(1)

        response = self.client.get("/api/v1/pratiche/1/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["id"], 1)

    # Scopo: Verifica che il dettaglio pratica contenga i campi display.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository", autospec=True)
    def test_get_dettaglio_pratica_display_fields(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = _mock_pratica_row(1)

        response = self.client.get("/api/v1/pratiche/1/")
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["stato_codice_interno"], "BOZZA")
        self.assertEqual(body["stato_descrizione"], "Bozza")
        self.assertEqual(body["priorita_codice_interno"], "NORMALE")
        self.assertEqual(body["tipo_prestazione_codice"], "MANUTENZIONE")
        self.assertIn("soggetto_display", body)
        self.assertIn("risorsa_umana_display", body)

    # Scopo: Verifica errore dettaglio pratica non trovata.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository", autospec=True)
    def test_get_dettaglio_pratica_non_trovata(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = None

        response = self.client.get("/api/v1/pratiche/999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_PRATICA_NOT_FOUND")

    # Scopo: Verifica PATCH aggiornamento pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.aggiorna_pratica")
    def test_patch_aggiorna_pratica_ok(self, mock_aggiorna, _auth):
        response = self.client.patch(
            "/api/v1/pratiche/1/",
            data=json.dumps({"descrizione": "Aggiornata"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_aggiorna.assert_called_once()

    # Scopo: Verifica POST cambio stato pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.cambia_stato_pratica")
    def test_post_stato_pratica_ok(self, mock_stato, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/stato/",
            data=json.dumps({"nuovo_stato": "APERTA"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_stato.assert_called_once_with(1, "APERTA")

    # Scopo: Verifica POST assegnazione pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.assegna_pratica")
    def test_post_assegnazione_pratica_ok(self, mock_assegna, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/assegnazione/",
            data=json.dumps({"risorsa_umana_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_assegna.assert_called_once()

    # Scopo: Verifica GET giornale pratica con tx_id nei risultati.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_giornale")
    def test_get_giornale_pratica_ok(self, mock_giornale, _auth):
        giornale_row = {
            "id": 1, "pratica_id": 1, "flusso_id": None,
            "azione": "PRATICA_CREATA", "origine": "SISTEMA",
            "dettaglio": {}, "tx_id": "tx-001",
            "data_insert": "2026-03-04T10:00:00+00:00", "user_insert": "sys",
        }
        mock_giornale.return_value = ([giornale_row], 1)

        response = self.client.get("/api/v1/pratiche/1/giornale/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["tx_id"], "tx-001")

    # Scopo: Verifica che gli endpoint V1 richiedano autenticazione JWT.
    def test_v1_richiede_jwt(self):
        response = self.client.get("/api/v1/pratiche/?emittente_fiscale_id=10")
        self.assertEqual(response.status_code, 401)
