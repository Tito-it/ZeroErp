# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API dashboard fatturazione (matrice mensile + fermi).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashboardFatturazioneApiTests.test_mensile_ok
2) DashboardFatturazioneApiTests.test_mensile_requires_jwt
3) DashboardFatturazioneApiTests.test_mensile_anno_default_corrente
4) DashboardFatturazioneApiTests.test_mensile_anno_esplicito
5) DashboardFatturazioneApiTests.test_mensile_anno_non_numerico_400
6) DashboardFatturazioneFermiApiTests.test_fermi_ok
7) DashboardFatturazioneFermiApiTests.test_fermi_requires_jwt
8) DashboardFatturazioneFermiApiTests.test_fermi_competenza_mese_obbligatoria
9) DashboardFatturazioneFermiApiTests.test_fermi_competenza_malformata_400
10) DashboardFatturazioneFermiApiTests.test_fermi_area_lowercase_normalizzata
11) DashboardFatturazioneFermiApiTests.test_fermi_paginazione_parametri
12) DashboardFatturazioneFermiApiTests.test_fermi_scope_db_side_no_auth_user
"""

from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_MENSILE_RESPONSE = {
    "anno": 2026,
    "mesi": [
        {
            "competenza_mese": "2026-01-01",
            "aree": [
                {
                    "area": "PREVENTIVI",
                    "valore_totale": "1000",
                    "valore_transitato": "800",
                    "n_documenti": 3,
                    "n_transitati": 2,
                    "n_fermi": 1,
                    "n_abortiti": 0,
                }
            ],
        }
    ],
}

_FERMI_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
        {
            "documento_id": 42,
            "documento_uid": "abc-uid",
            "codice": "PRV0000123",
            "cliente_display": "Rossi Impianti SRL",
            "valore_totale": "1450",
            "valore_transitato": "0",
            "unita_totali": 2,
            "unita_transitate": 0,
            "motivo_fermo": "RIGA_RESIDUA",
            "stato_codice_interno": "ACCETTATO",
            "stato_codice": "ACC",
            "fase": "IN_CORSO",
        }
    ],
}


class DashboardFatturazioneApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Verifica il caso `test_mensile_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_mensile")
    def test_mensile_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _MENSILE_RESPONSE
        response = self.client.get("/api/v1/vendite/dashboard-fatturazione/?anno=2026")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["anno"], 2026)
        self.assertEqual(data["mesi"][0]["competenza_mese"], "2026-01-01")
        self.assertEqual(data["mesi"][0]["aree"][0]["area"], "PREVENTIVI")

    # Scopo: Verifica il caso `test_mensile_requires_jwt`.
    def test_mensile_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/dashboard-fatturazione/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Senza parametro anno il default e' l'anno corrente.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_mensile")
    def test_mensile_anno_default_corrente(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _MENSILE_RESPONSE
        self.client.get("/api/v1/vendite/dashboard-fatturazione/")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["anno"], date.today().year)

    # Scopo: Il parametro anno esplicito viene inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_mensile")
    def test_mensile_anno_esplicito(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _MENSILE_RESPONSE
        self.client.get("/api/v1/vendite/dashboard-fatturazione/?anno=2025")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["anno"], 2025)

    # Scopo: Anno non numerico -> 400 (qp_int_strict).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_mensile_anno_non_numerico_400(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/dashboard-fatturazione/?anno=abc")
        self.assertEqual(response.status_code, 400)


class DashboardFatturazioneFermiApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-fatturazione/fermi/"

    # Scopo: Verifica il caso `test_fermi_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_fermi")
    def test_fermi_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _FERMI_RESPONSE
        response = self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&area=PREVENTIVI"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        self.assertEqual(row["codice"], "PRV0000123")
        # Passthrough dei campi FE-critici del drill-down (guardia contratto:
        # cliente_display alimenta la colonna Cliente, motivo/stato la severity).
        self.assertEqual(row["cliente_display"], "Rossi Impianti SRL")
        self.assertEqual(row["motivo_fermo"], "RIGA_RESIDUA")
        self.assertEqual(row["stato_codice_interno"], "ACCETTATO")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        self.assertEqual(kwargs["area"], "PREVENTIVI")

    # Scopo: Verifica il caso `test_fermi_requires_jwt`.
    def test_fermi_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: competenza_mese mancante -> 400 E_VENDITE_VALIDATION.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_fermi_competenza_mese_obbligatoria(self, _mock_auth):
        response = self.client.get(f"{self._URL}?area=PREVENTIVI")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VENDITE_VALIDATION")

    # Scopo: competenza_mese malformata -> 400 (qp_iso_date_optional).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_fermi_competenza_malformata_400(self, _mock_auth):
        response = self.client.get(
            f"{self._URL}?competenza_mese=maggio&area=PREVENTIVI"
        )
        self.assertEqual(response.status_code, 400)

    # Scopo: area minuscola viene normalizzata a maiuscolo prima del service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_fermi")
    def test_fermi_area_lowercase_normalizzata(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _FERMI_RESPONSE
        self.client.get(f"{self._URL}?competenza_mese=2026-05-01&area=commesse")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["area"], "COMMESSE")

    # Scopo: page/page_size vengono inoltrati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_fermi")
    def test_fermi_paginazione_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _FERMI_RESPONSE
        self.client.get(
            f"{self._URL}?competenza_mese=2026-05-01&area=ORDINI&page=2&page_size=10"
        )
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 10)

    # Scopo: Lo scope emittente e' interamente DB-side (RLS + filtro GUC nel
    #        resolver commesse, 20260703-60): la view NON passa auth_user_id.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views_dashboard_fatturazione.fn_dash_fatturazione_fermi")
    def test_fermi_scope_db_side_no_auth_user(self, mocked_fn, mock_auth, _mock_perm):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_fn.return_value = _FERMI_RESPONSE
        self.client.get(f"{self._URL}?competenza_mese=2026-05-01&area=COMMESSE")
        kwargs = mocked_fn.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)
