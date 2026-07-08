# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API Situazione aperta (riepilogo area×fase + documenti).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashboardApertoApiTests.test_riepilogo_ok
2) DashboardApertoApiTests.test_riepilogo_requires_jwt
3) DashboardApertoDocumentiApiTests.test_documenti_ok
4) DashboardApertoDocumentiApiTests.test_documenti_requires_jwt
5) DashboardApertoDocumentiApiTests.test_documenti_filtri_lowercase_normalizzati
6) DashboardApertoDocumentiApiTests.test_documenti_filtri_assenti_default
7) DashboardApertoDocumentiApiTests.test_documenti_solo_aperti_false
8) DashboardApertoDocumentiApiTests.test_documenti_paginazione_parametri
9) DashboardApertoDocumentiApiTests.test_documenti_scope_db_side_no_auth_user
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_RIEPILOGO_RESPONSE = {
    "aree": [
        {
            "area": "PREVENTIVI",
            "n_documenti": 5,
            "n_aperti": 4,
            "valore_totale": "2000.50",
            "valore_transitato": "300.00",
            "fasi": [{"fase": "APERTO", "n_documenti": 3, "n_aperti": 3}],
        }
    ]
}

_DOCUMENTI_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
        {
            "area": "PREVENTIVI",
            "documento_id": 42,
            "codice": "PRV0000123",
            "cliente_display": "Rossi Impianti SRL",
            "fase": "IN_CORSO",
            "stato_codice_interno": "ACCETTATO",
            "stato_codice": "ACC",
            "valore_totale": "1450.00",
            "valore_transitato": "0",
            "unita_totali": 2,
            "unita_transitate": 0,
            "is_transitato": False,
            "is_aperto": True,
            "motivo_fermo": "RIGA_RESIDUA",
            "data_riferimento": "2026-05-12",
        }
    ],
}


class DashboardApertoApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-aperto/"

    # Scopo: Verifica il caso `test_riepilogo_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_riepilogo")
    def test_riepilogo_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _RIEPILOGO_RESPONSE
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        area = data["aree"][0]
        # Passthrough dei campi FE-critici delle card (totali + griglia fasi).
        self.assertEqual(area["area"], "PREVENTIVI")
        self.assertEqual(area["n_aperti"], 4)
        self.assertEqual(area["valore_totale"], "2000.50")
        self.assertEqual(area["fasi"][0]["fase"], "APERTO")

    # Scopo: Verifica il caso `test_riepilogo_requires_jwt`.
    def test_riepilogo_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)


class DashboardApertoDocumentiApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-aperto/documenti/"

    # Scopo: Verifica il caso `test_documenti_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        response = self.client.get(f"{self._URL}?area=PREVENTIVI&fase=IN_CORSO")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        # Passthrough dei campi FE-critici della lista (fase/stato alimentano
        # tag e raggruppamento; is_aperto la resa; data_riferimento l'ordine).
        self.assertEqual(row["fase"], "IN_CORSO")
        self.assertEqual(row["stato_codice_interno"], "ACCETTATO")
        self.assertTrue(row["is_aperto"])
        self.assertEqual(row["data_riferimento"], "2026-05-12")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["area"], "PREVENTIVI")
        self.assertEqual(kwargs["fase"], "IN_CORSO")

    # Scopo: Verifica il caso `test_documenti_requires_jwt`.
    def test_documenti_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: area/fase minuscole vengono normalizzate a maiuscolo.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_filtri_lowercase_normalizzati(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?area=offerte&fase=chiuso")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["area"], "OFFERTE")
        self.assertEqual(kwargs["fase"], "CHIUSO")

    # Scopo: Filtri assenti -> None al service (tutte le aree/fasi); anche
    #        solo_aperti passa None: il default di pagina (True) e' UNICA
    #        definizione nel service, la view non lo duplica.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_filtri_assenti_default(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertIsNone(kwargs["area"])
        self.assertIsNone(kwargs["fase"])
        self.assertIsNone(kwargs["solo_aperti"])

    # Scopo: solo_aperti=false (fotografia completa) inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_solo_aperti_false(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?solo_aperti=false")
        kwargs = mocked_fn.call_args.kwargs
        self.assertFalse(kwargs["solo_aperti"])

    # Scopo: page/page_size vengono inoltrati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_paginazione_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?page=3&page_size=10")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["page"], 3)
        self.assertEqual(kwargs["page_size"], 10)

    # Scopo: Lo scope emittente e' interamente DB-side (RLS invoker): la view
    #        NON passa auth_user_id.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_scope_db_side_no_auth_user(self, mocked_fn, mock_auth, _mock_perm):
        user = Mock()
        user.id = 42
        user.is_superuser = False
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)
