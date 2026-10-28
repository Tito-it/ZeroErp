# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API Lente 1 Competenza (aggregata + attivita' + errori).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashboardCompetenzaApiTests.test_mensile_ok
2) DashboardCompetenzaApiTests.test_mensile_requires_jwt
3) DashboardCompetenzaApiTests.test_mensile_anno_default_corrente
4) DashboardCompetenzaApiTests.test_mensile_anno_non_numerico_400
5) DashboardCompetenzaAttivitaApiTests.test_attivita_ok
6) DashboardCompetenzaAttivitaApiTests.test_attivita_requires_jwt
7) DashboardCompetenzaAttivitaApiTests.test_attivita_competenza_mese_obbligatoria
8) DashboardCompetenzaAttivitaApiTests.test_attivita_competenza_malformata_400
9) DashboardCompetenzaAttivitaApiTests.test_attivita_stadio_lowercase_normalizzato
10) DashboardCompetenzaAttivitaApiTests.test_attivita_solo_ritardo_e_paginazione
10a) DashboardCompetenzaAttivitaApiTests.test_attivita_ordinamento_parametri
11) DashboardCompetenzaAttivitaApiTests.test_attivita_scope_db_side_no_auth_user
11a) DashboardCompetenzaCommesseApiTests.test_commesse_ok (DEC-4)
11b) DashboardCompetenzaCommesseApiTests.test_commesse_requires_jwt
11c) DashboardCompetenzaCommesseApiTests.test_commesse_competenza_obbligatoria
11d) DashboardCompetenzaCommesseApiTests.test_commesse_normalizza_e_ordina
12) DashboardCompetenzaErroriApiTests.test_errori_ok
13) DashboardCompetenzaErroriApiTests.test_errori_requires_jwt
14) DashboardCompetenzaErroriApiTests.test_errori_competenza_opzionale
"""

from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova

_MENSILE_RESPONSE = {
    "anno": 2026,
    "mesi": [
        {
            "competenza_mese": "2026-01-01",
            "stadi": [
                {
                    "stadio": "FATTURATA",
                    "n_attivita": 3,
                    "valore": "1000.00",
                    "valore_fatturato": "990.00",
                    "n_in_ritardo": 1,
                    "valore_in_ritardo": "100.00",
                    "stati_fattura": [
                        {
                            "stato_fattura_codice_interno": "DRAFT",
                            "stato_fattura_codice": "DRAFT",
                            "tipo_movimento": "NORMALE",
                            "n_attivita": 3,
                            "valore": "1000.00",
                            "valore_fatturato": "990.00",
                            "n_in_ritardo": 1,
                            "valore_in_ritardo": "100.00",
                        }
                    ],
                }
            ],
            "n_errori": 1,
        }
    ],
}

_ATTIVITA_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
        {
            "commessa_attivita_id": 7,
            "commessa_codice": "CMS0000042",
            "cliente_display": "Rossi Impianti SRL",
            "articolo_codice": "ART-001",
            "stadio": "FATTURATA",
            "valore": "1000.00",
            "valore_fatturato": "990.00",
            "emessa_in_ritardo": True,
            "stato_fattura_codice_interno": "DRAFT",
        }
    ],
}

_ERRORI_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
        {
            "tipo_evento": "TASK_ERRORE",
            "competenza_mese": "2026-05-01",
            "lotto_codice": "LOT0000009",
            "error_code": "E_PIPELINE_TASK",
            "messaggio": "boom",
        }
    ],
}


class DashboardCompetenzaApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-competenza/"

    # Scopo: Verifica il caso `test_mensile_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_mensile")
    def test_mensile_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _MENSILE_RESPONSE
        response = self.client.get(f"{self._URL}?anno=2026")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["anno"], 2026)
        mese = data["mesi"][0]
        self.assertEqual(mese["competenza_mese"], "2026-01-01")
        self.assertEqual(mese["n_errori"], 1)
        # Passthrough dei campi FE-critici (breakdown 3a + misura DB-6).
        fatturata = mese["stadi"][0]
        self.assertEqual(fatturata["valore_fatturato"], "990.00")
        self.assertEqual(
            fatturata["stati_fattura"][0]["stato_fattura_codice_interno"], "DRAFT"
        )
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["anno"], 2026)

    # Scopo: Verifica il caso `test_mensile_requires_jwt`.
    def test_mensile_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: Senza parametro anno il default e' l'anno corrente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_mensile")
    def test_mensile_anno_default_corrente(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _MENSILE_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["anno"], oggi_aziendale().year)

    # Scopo: Anno non numerico -> 400 (qp_int_strict).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_mensile_anno_non_numerico_400(self, _mock_auth):
        response = self.client.get(f"{self._URL}?anno=abc")
        self.assertEqual(response.status_code, 400)


class DashboardCompetenzaAttivitaApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-competenza/attivita/"

    # Scopo: Verifica il caso `test_attivita_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_attivita")
    def test_attivita_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ATTIVITA_RESPONSE
        response = self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&stadio=FATTURATA"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        # Passthrough dei campi FE-critici del drill-down (cliente, articolo
        # decodificato, misura fatturato DB-6, flag recupero tardivo).
        self.assertEqual(row["cliente_display"], "Rossi Impianti SRL")
        self.assertEqual(row["articolo_codice"], "ART-001")
        self.assertEqual(row["valore_fatturato"], "990.00")
        self.assertTrue(row["emessa_in_ritardo"])
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        self.assertEqual(kwargs["stadio"], "FATTURATA")
        self.assertFalse(kwargs["solo_ritardo"])

    # Scopo: Verifica il caso `test_attivita_requires_jwt`.
    def test_attivita_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: competenza_mese mancante -> 400 E_VENDITE_VALIDATION.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_attivita_competenza_mese_obbligatoria(self, _mock_auth):
        response = self.client.get(f"{self._URL}?stadio=FATTURATA")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VENDITE_VALIDATION")

    # Scopo: competenza_mese malformata -> 400 (qp_iso_date_optional).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_attivita_competenza_malformata_400(self, _mock_auth):
        response = self.client.get(f"{self._URL}?competenza_mese=maggio")
        self.assertEqual(response.status_code, 400)

    # Scopo: stadio minuscolo viene normalizzato a maiuscolo prima del service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_attivita")
    def test_attivita_stadio_lowercase_normalizzato(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ATTIVITA_RESPONSE
        self.client.get(f"{self._URL}?competenza_mese=2026-05-01&stadio=da_emettere")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["stadio"], "DA_EMETTERE")

    # Scopo: solo_ritardo/page/page_size vengono inoltrati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_attivita")
    def test_attivita_solo_ritardo_e_paginazione(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ATTIVITA_RESPONSE
        self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&solo_ritardo=true&limit=10&offset=10"
        )
        kwargs = mocked_fn.call_args.kwargs
        self.assertTrue(kwargs["solo_ritardo"])
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)

    # Scopo: order_by/order_dir (ordinamento colonne) inoltrati al service;
    #        whitelist/validazione = definizione unica del service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_attivita")
    def test_attivita_ordinamento_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ATTIVITA_RESPONSE
        self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&order_by=data_attivita&order_dir=desc"
        )
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "data_attivita")
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: Lo scope emittente e' interamente DB-side (GUC fail-closed nella
    #        vista): la view NON passa auth_user_id.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_attivita")
    def test_attivita_scope_db_side_no_auth_user(self, mocked_fn, mock_auth, _mock_perm):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_fn.return_value = _ATTIVITA_RESPONSE
        self.client.get(f"{self._URL}?competenza_mese=2026-05-01")
        kwargs = mocked_fn.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)


class DashboardCompetenzaCommesseApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-competenza/commesse/"

    # Scopo: drill-down aggregato OK — passthrough parametri e riga per commessa.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_commesse")
    def test_commesse_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{
                "commessa_id": 7, "commessa_codice": "COMM-0007",
                "cliente_display": "Rossi Impianti SRL", "n_attivita": 4,
                "n_in_ritardo": 1, "valore_tot": "3960.00",
                "valore_fatturato_tot": "0.00",
                "data_attivita_min": "2026-05-02", "data_attivita_max": "2026-05-28",
            }],
        }
        response = self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&stadio=DA_EMETTERE"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        self.assertEqual(row["commessa_codice"], "COMM-0007")
        self.assertEqual(row["n_attivita"], 4)
        self.assertEqual(row["valore_tot"], "3960.00")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        self.assertEqual(kwargs["stadio"], "DA_EMETTERE")

    # Scopo: senza JWT -> 401.
    def test_commesse_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: competenza_mese mancante -> 400 E_VENDITE_VALIDATION.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_commesse_competenza_obbligatoria(self, _mock_auth):
        response = self.client.get(f"{self._URL}?stadio=DA_EMETTERE")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VENDITE_VALIDATION")

    # Scopo: stadio minuscolo normalizzato + order_by/order_dir inoltrati.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_commesse")
    def test_commesse_normalizza_e_ordina(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = {
            "count": 0, "page": 1, "page_size": 50, "total_pages": 0, "results": [],
        }
        self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&stadio=da_emettere"
            "&order_by=valore_tot&order_dir=desc"
        )
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["stadio"], "DA_EMETTERE")
        self.assertEqual(kwargs["order_by"], "valore_tot")
        self.assertEqual(kwargs["order_dir"], "desc")


class DashboardCompetenzaErroriApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-competenza/errori/"

    # Scopo: Verifica il caso `test_errori_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_errori")
    def test_errori_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ERRORI_RESPONSE
        response = self.client.get(f"{self._URL}?competenza_mese=2026-05-01")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["tipo_evento"], "TASK_ERRORE")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))

    # Scopo: Verifica il caso `test_errori_requires_jwt`.
    def test_errori_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: Senza competenza_mese il service riceve None (tutti i mesi).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_errori")
    def test_errori_competenza_opzionale(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ERRORI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertIsNone(kwargs["competenza_mese"])

    # Scopo: order_by/order_dir propagati al service (8° lotto liste, 2026-08-03).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_competenza.fn_dash_competenza_errori")
    def test_errori_ordinamento_propagato(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ERRORI_RESPONSE
        self.client.get(f"{self._URL}?order_by=data_evento&order_dir=asc")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "data_evento")
        self.assertEqual(kwargs["order_dir"], "asc")
