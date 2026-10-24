# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API sospensione/riattivazione pratiche e flussi.
#        Mock services, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SospensioniApiTests.test_post_sospendi_pratica_ok
2) SospensioniApiTests.test_post_sospendi_pratica_errore_motivo_mancante
3) SospensioniApiTests.test_post_riattiva_pratica_ok
4) SospensioniApiTests.test_post_sospendi_flusso_ok
5) SospensioniApiTests.test_post_sospendi_flusso_errore_motivo_mancante
6) SospensioniApiTests.test_post_riattiva_flusso_ok
7) SospensioniApiTests.test_get_sospensioni_pratica_ok
8) SospensioniApiTests.test_get_calcoli_tempo_pratica_ok
9) SospensioniApiTests.test_v1_sospendi_richiede_jwt
10) SospensioniApiTests.test_post_sospendi_pratica_con_data_riattivazione
11) SospensioniApiTests.test_get_calcoli_tempo_con_stato_tempo
12) SospensioniApiTests.test_get_formule_tempo_ok
13) SospensioniApiTests.test_get_formule_tempo_senza_tipo_prestazione
14) SospensioniApiTests.test_istante_senza_offset_e_un_400 — B-7 un-solo-fuso-aziendale
"""

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


class SospensioniApiTests(JwtMockedApiTest):

    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # -- SOSPENDI PRATICA ------------------------------------------------

    # Scopo: Verifica POST sospensione pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_pratica")
    def test_post_sospendi_pratica_ok(self, mock_sospendi, _auth):
        mock_sospendi.return_value = 100

        response = self.client.post(
            "/api/v1/pratiche/1/sospendi/",
            data=json.dumps({"motivo": "Attesa documenti"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["sospensione_id"], 100)
        self.assertEqual(body["data"]["status"], "ok")
        mock_sospendi.assert_called_once_with(
            1, "Attesa documenti",
            data_riattivazione_prevista=None,
            data_inizio=None,
        )

    # Scopo: Verifica errore senza motivo (il service valida e rifiuta).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_pratica",
           side_effect=ServiceError(code="E_PRATICA_VALIDATION", message="motivo obbligatorio"))
    def test_post_sospendi_pratica_errore_motivo_mancante(self, _mock, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/sospendi/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica POST sospensione pratica con data_riattivazione_prevista.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_pratica")
    def test_post_sospendi_pratica_con_data_riattivazione(self, mock_sospendi, _auth):
        mock_sospendi.return_value = 101

        response = self.client.post(
            "/api/v1/pratiche/1/sospendi/",
            data=json.dumps({
                "motivo": "Attesa tecnico",
                "data_riattivazione_prevista": "2026-03-15",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["sospensione_id"], 101)
        mock_sospendi.assert_called_once_with(
            1, "Attesa tecnico",
            data_riattivazione_prevista="2026-03-15",
            data_inizio=None,
        )

    # Scopo: Verifica che data_inizio manuale (ISO) sia inoltrata al service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_pratica")
    def test_post_sospendi_pratica_con_data_inizio(self, mock_sospendi, _auth):
        mock_sospendi.return_value = 102

        response = self.client.post(
            "/api/v1/pratiche/1/sospendi/",
            data=json.dumps({
                "motivo": "Retroattiva",
                "data_inizio": "2026-06-20T09:30:00+00:00",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # L'istante arriva al service come istante (con il suo offset), non
        # come stringa da far interpretare alla sessione.
        mock_sospendi.assert_called_once_with(
            1, "Retroattiva",
            data_riattivazione_prevista=None,
            data_inizio=datetime(2026, 6, 20, 9, 30, tzinfo=UTC),
        )

    # Scopo: B-7. Un istante senza offset si rifiuta (400), sia in sospensione
    # sia in riattivazione: PostgreSQL lo leggerebbe nel fuso della sessione.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.riattiva_pratica")
    @patch(f"{_VIEWS}.pratiche_service.sospendi_pratica")
    def test_istante_senza_offset_e_un_400(self, mock_sospendi, mock_riattiva, _auth):
        for url, corpo in (
            ("/api/v1/pratiche/1/sospendi/", {"motivo": "x", "data_inizio": "2026-06-20T09:30:00"}),
            ("/api/v1/pratiche/1/riattiva/", {"data_fine": "2026-06-20T09:30:00"}),
            ("/api/v1/pratiche/1/riattiva/", {"data_fine": "ieri"}),
        ):
            with self.subTest(url=url, corpo=corpo):
                response = self.client.post(url, data=json.dumps(corpo), content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")
        mock_sospendi.assert_not_called()
        mock_riattiva.assert_not_called()

    # -- RIATTIVA PRATICA ------------------------------------------------

    # Scopo: Verifica POST riattivazione pratica con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.riattiva_pratica")
    def test_post_riattiva_pratica_ok(self, mock_riattiva, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/riattiva/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["status"], "ok")
        mock_riattiva.assert_called_once_with(1, data_fine=None)

    # -- SOSPENDI FLUSSO -------------------------------------------------

    # Scopo: Verifica POST sospensione flusso con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_flusso")
    def test_post_sospendi_flusso_ok(self, mock_sospendi, _auth):
        mock_sospendi.return_value = 200

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/10/sospendi/",
            data=json.dumps({"motivo": "Attesa tecnico"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["sospensione_id"], 200)
        mock_sospendi.assert_called_once_with(
            1, 10, "Attesa tecnico",
            data_riattivazione_prevista=None,
        )

    # Scopo: Verifica errore sospensione flusso senza motivo (il service valida e rifiuta).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.sospendi_flusso",
           side_effect=ServiceError(code="E_FLUSSO_VALIDATION", message="motivo obbligatorio"))
    def test_post_sospendi_flusso_errore_motivo_mancante(self, _mock, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/flussi/10/sospendi/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # -- RIATTIVA FLUSSO -------------------------------------------------

    # Scopo: Verifica POST riattivazione flusso con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.riattiva_flusso")
    def test_post_riattiva_flusso_ok(self, mock_riattiva, _auth):
        response = self.client.post(
            "/api/v1/pratiche/1/flussi/10/riattiva/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["status"], "ok")
        mock_riattiva.assert_called_once_with(1, 10)

    # -- LETTURA SOSPENSIONI / CALCOLI TEMPO -----------------------------

    # Scopo: Verifica GET lista sospensioni pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_sospensioni")
    def test_get_sospensioni_pratica_ok(self, mock_sosp, _auth):
        mock_sosp.return_value = [{
            "id": 1, "pratica_id": 1, "flusso_id": None,
            "data_inizio": "2026-03-06T10:00:00+00:00", "data_fine": None,
            "data_riattivazione_prevista": None, "motivo": "Test",
            "data_insert": "2026-03-06", "user_insert": "test",
            "data_update": None, "user_update": None,
        }]

        response = self.client.get("/api/v1/pratiche/1/sospensioni/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    # Scopo: Verifica GET lista calcoli tempo pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_calcoli_tempo")
    def test_get_calcoli_tempo_pratica_ok(self, mock_calc, _auth):
        mock_calc.return_value = [{
            "id": 1, "pratica_id": 1, "flusso_da_id": 10, "flusso_a_id": 20,
            "formula_tempo_id": 5, "data_inizio_calcolo": "2026-03-06",
            "data_fine_calcolo": None, "giorni_lordi": None,
            "giorni_sospensione": None, "giorni_netti": None,
            "giorni_formula": 30, "sforato": None,
        }]

        response = self.client.get("/api/v1/pratiche/1/calcoli-tempo/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    # -- CALCOLI TEMPO CON STATO_TEMPO ------------------------------------

    # Scopo: Verifica che GET calcoli-tempo restituisca i campi stato_tempo e giorni_rimanenti.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_calcoli_tempo")
    def test_get_calcoli_tempo_con_stato_tempo(self, mock_calc, _auth):
        mock_calc.return_value = [{
            "id": 1, "pratica_id": 1, "flusso_da_id": 10, "flusso_a_id": 20,
            "formula_tempo_id": 5, "data_inizio_calcolo": "2026-03-06",
            "data_fine_calcolo": "2026-03-16", "giorni_lordi": 10,
            "giorni_sospensione": 2, "giorni_netti": 8,
            "giorni_formula": 15, "sforato": False,
            "giorni_rimanenti": 7, "stato_tempo": "OK",
        }]

        response = self.client.get("/api/v1/pratiche/1/calcoli-tempo/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        result = body["data"]["results"][0]
        self.assertEqual(result["stato_tempo"], "OK")
        self.assertEqual(result["giorni_rimanenti"], 7)

    # -- FORMULE TEMPO ---------------------------------------------------

    # Scopo: Verifica GET formule tempo con tipo_prestazione_id valido.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_formule_tempo")
    def test_get_formule_tempo_ok(self, mock_formule, _auth):
        mock_formule.return_value = [{
            "id": 1, "tipo_prestazione_id": 26,
            "template_flusso_da_id": 5, "template_flusso_a_id": 10,
            "giorni_esecuzione": 15, "giorni_warning": 12, "giorni_critico": 14,
            "attivo": True, "descrizione": "Test", "meta": {},
        }]

        response = self.client.get("/api/v1/pratiche/formule-tempo/?tipo_prestazione_id=26")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        self.assertEqual(body["data"]["results"][0]["giorni_esecuzione"], 15)
        mock_formule.assert_called_once_with(26)

    # Scopo: Verifica errore GET formule tempo senza tipo_prestazione_id.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_get_formule_tempo_senza_tipo_prestazione(self, _auth):
        response = self.client.get("/api/v1/pratiche/formule-tempo/")
        self.assertEqual(response.status_code, 400)

    # -- JWT PROTECTION --------------------------------------------------

    # Scopo: Verifica che endpoint V1 sospendi richieda autenticazione JWT.
    def test_v1_sospendi_richiede_jwt(self):
        response = self.client.post(
            "/api/v1/pratiche/1/sospendi/",
            data=json.dumps({"motivo": "test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
