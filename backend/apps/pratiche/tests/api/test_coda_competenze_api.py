# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API coda lavoro, prendi in carico, competenze flussi.
#        Mock services, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) CodaLavoroApiTests.test_get_coda_lavoro_ok
 2) CodaLavoroApiTests.test_get_coda_lavoro_senza_emittente
 3) PrendiInCaricoApiTests.test_post_prendi_in_carico_ok
 4) CompetenzeFlussiApiTests.test_get_lista_competenze_ok
 5) CompetenzeFlussiApiTests.test_post_crea_competenza_ok
 6) CompetenzeFlussiApiTests.test_delete_competenza_ok
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


def _mock_user():
    """Mock user — Mock() di default ha is_superuser truthy → bypass permission."""
    return Mock()


def _mock_coda_row():
    return {
        "livello": "ASSEGNATO",
        "flusso_id": 10,
        "pratica_id": 1,
        "pratica_codice": "PRA-0000001",
        "pratica_descrizione": "Test",
        "priorita_codice": "NORMALE",
        "tipo_prestazione_codice": "MANUTENZIONE",
        "template_flusso_codice": "VALUTAZIONE",
        "template_flusso_desc": "Valutazione",
        "stato_flusso_codice_interno": "DA_ESEGUIRE", "stato_flusso_codice": "DA_ESEGUIRE",
        "sequenza": 10,
        "data_scadenza": None,
        "risorsa_assegnata": None,
    }


# ================================================================== #
# Coda lavoro                                                          #
# ================================================================== #


class CodaLavoroApiTests(JwtMockedApiTest):

    def setUp(self):
        super().setUp()
        self.client = ClientApi()
        self.url = "/api/v1/pratiche/coda-lavoro/"

    @patch(f"{_VIEWS}.pratiche_service.get_coda_lavoro", return_value=[_mock_coda_row()])
    @patch("apps.pratiche.api.views.get_risorsa_umana_id", return_value=100)
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_get_coda_lavoro_ok(self, _auth, _risorsa, _service):
        # Scopo: verifica GET coda lavoro con risultati.
        resp = self.client.get(f"{self.url}?emittente_fiscale_id=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)

    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_get_coda_lavoro_senza_emittente(self, _auth):
        # Scopo: verifica errore senza emittente_fiscale_id.
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [400, 422])


# ================================================================== #
# Prendi in carico                                                     #
# ================================================================== #


class PrendiInCaricoApiTests(JwtMockedApiTest):

    def setUp(self):
        super().setUp()
        self.client = ClientApi()
        self.url = "/api/v1/pratiche/flussi/10/prendi-in-carico/"

    @patch(f"{_VIEWS}.pratiche_service.prendi_in_carico", return_value=True)
    @patch("apps.pratiche.api.views.get_risorsa_umana_id", return_value=100)
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_post_prendi_in_carico_ok(self, _auth, _risorsa, _service):
        # Scopo: verifica POST prendi in carico riuscito.
        resp = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertTrue(data["assegnato"])


# ================================================================== #
# Competenze flussi                                                    #
# ================================================================== #


class CompetenzeFlussiApiTests(JwtMockedApiTest):

    def setUp(self):
        super().setUp()
        self.client = ClientApi()
        self.url_list = "/api/v1/pratiche/competenze-flussi/"

    @patch(f"{_VIEWS}.pratiche_service.get_competenze_flussi", return_value=[{
        "id": 1, "template_flusso_id": 5, "unita_organizzativa_id": 3,
        "risorsa_umana_id": 100, "attivo": True,
        "template_flusso_codice": "VAL", "template_flusso_descrizione": "Valutazione",
        "unita_organizzativa_descrizione": "Tecnico", "risorsa_umana_display": "Rossi",
    }])
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_get_lista_competenze_ok(self, _auth, _service):
        # Scopo: verifica GET lista competenze.
        resp = self.client.get(self.url_list)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("results", data)

    @patch(f"{_VIEWS}.pratiche_service.crea_competenza_flusso", return_value=42)
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_post_crea_competenza_ok(self, _auth, _service):
        # Scopo: verifica POST creazione competenza.
        resp = self.client.post(
            self.url_list,
            data=json.dumps({
                "template_flusso_id": 5,
                "unita_organizzativa_id": 3,
                "risorsa_umana_id": 100,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["competenza_id"], 42)

    @patch(f"{_VIEWS}.pratiche_service.elimina_competenza_flusso")
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_delete_competenza_ok(self, _auth, _service):
        # Scopo: verifica DELETE competenza.
        resp = self.client.delete("/api/v1/pratiche/competenze-flussi/42/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertTrue(data["deleted"])
