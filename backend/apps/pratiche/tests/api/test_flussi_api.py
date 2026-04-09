# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API flussi (lista, dettaglio, stato,
#        prerequisiti, canali, generazione cross-pratica).
#        Mock services e repository, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FlussiApiTests.test_get_lista_flussi_ok
2) FlussiApiTests.test_post_crea_flusso_ok
3) FlussiApiTests.test_get_dettaglio_flusso_ok
4) FlussiApiTests.test_get_dettaglio_flusso_ownership_mismatch
5) FlussiApiTests.test_post_stato_flusso_completamento_ok
6) FlussiApiTests.test_post_stato_flusso_avvio_ok
7) FlussiApiTests.test_post_stato_flusso_generico_ok
8) FlussiApiTests.test_get_prerequisiti_ok
9) FlussiApiTests.test_get_prerequisiti_senza_template
10) FlussiApiTests.test_get_canali_ok
11) FlussiApiTests.test_get_regole_generazione_ok
12) FlussiApiTests.test_post_genera_pratica_ok
13) FlussiApiTests.test_get_pratiche_generate_ok
14) FlussiApiTests.test_v1_richiede_jwt
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


def _mock_flusso_row(flusso_id: int = 1, *, pratica_id: int = 1, template_flusso_id: int | None = 10) -> dict:
    return {
        "id": flusso_id,
        "pratica_id": pratica_id,
        "template_flusso_id": template_flusso_id,
        "stato_id": 1,
        "flusso_padre_id": None,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "sequenza": 0,
        "esito": None,
        "note_esito": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test",
    }


class FlussiApiTests(JwtMockedApiTest):

    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Verifica GET lista flussi per pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_lista_flussi_ok(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.list_flussi.return_value = [_mock_flusso_row()]

        response = self.client.get("/api/v1/pratiche/1/flussi/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    # Scopo: Verifica POST creazione flusso con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_flusso")
    def test_post_crea_flusso_ok(self, mock_crea, _auth):
        mock_crea.return_value = 99

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/",
            data=json.dumps({"template_flusso_id": 10, "sequenza": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["flusso_id"], 99)

    # Scopo: Verifica GET dettaglio flusso con ownership corretta.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_dettaglio_flusso_ok(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["id"], 5)

    # Scopo: Verifica errore ownership quando flusso non appartiene alla pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_dettaglio_flusso_ownership_mismatch(self, MockRepo, _auth):
        repo = MockRepo.return_value
        # Flusso con pratica_id=999, ma URL chiede pratica 1.
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=999)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_FLUSSO_OWNERSHIP")

    # Scopo: Verifica POST completamento flusso con esito.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.completa_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_completamento_ok(self, MockRepo, mock_completa, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({
                "nuovo_stato": "COMPLETATO",
                "esito": "POSITIVO",
                "note_esito": "Tutto ok",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_completa.assert_called_once_with(
            5, esito="POSITIVO", note_esito="Tutto ok",
        )

    # Scopo: Verifica POST avvio flusso (IN_CORSO).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.avvia_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_avvio_ok(self, MockRepo, mock_avvia, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({"nuovo_stato": "IN_CORSO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_avvia.assert_called_once_with(5)

    # Scopo: Verifica POST transizione generica via service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.cambia_stato_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_generico_ok(self, MockRepo, mock_cambia, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({"nuovo_stato": "SOSPESO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_cambia.assert_called_once_with(5, "SOSPESO")

    # Scopo: Verifica GET prerequisiti flusso con template.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.verifica_prerequisiti")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_prerequisiti_ok(self, MockRepo, mock_prereq, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=10)

        prerequisiti = [
            {"prerequisito_id": 1, "codice": "DOC", "descrizione": "Doc", "soddisfatto": True},
        ]
        mock_prereq.return_value = prerequisiti

        response = self.client.get("/api/v1/pratiche/1/flussi/5/prerequisiti/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        self.assertTrue(body["data"]["results"][0]["soddisfatto"])

    # Scopo: Verifica GET prerequisiti senza template → lista vuota.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_prerequisiti_senza_template(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=None)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/prerequisiti/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["results"], [])

    # Scopo: Verifica GET canali flusso con template.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_canali_disponibili")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_canali_ok(self, MockRepo, mock_canali, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=10)

        canali = [{"id": 1, "codice": "WEB_CLIENTI", "descrizione": "Web", "codice_interno": "WEB_CLIENTI"}]
        mock_canali.return_value = canali

        response = self.client.get("/api/v1/pratiche/1/flussi/5/canali/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["results"]), 1)

    # Scopo: Verifica GET regole generazione per flusso.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.get_regole_applicabili")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_regole_generazione_ok(self, MockRepo, mock_regole, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_regole.return_value = [{"id": 1, "auto": False, "descrizione": "Regola"}]

        response = self.client.get("/api/v1/pratiche/1/flussi/5/regole-generazione/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["results"]), 1)

    # Scopo: Verifica POST generazione manuale pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.genera_pratica_manuale")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_genera_pratica_ok(self, MockRepo, mock_genera, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_genera.return_value = 200

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/genera/",
            data=json.dumps({"regola_id": 3}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["pratica_id"], 200)

    # Scopo: Verifica GET pratiche generate dal flusso.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.get_pratiche_generate")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_pratiche_generate_ok(self, MockRepo, mock_generate, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_generate.return_value = []

        response = self.client.get("/api/v1/pratiche/1/flussi/5/pratiche-generate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["results"], [])

    # Scopo: Verifica che endpoint V1 flussi richieda JWT.
    def test_v1_richiede_jwt(self):
        response = self.client.get("/api/v1/pratiche/1/flussi/")
        self.assertEqual(response.status_code, 401)
