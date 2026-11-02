# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API Lente 2 Backlog (riepilogo classi + documenti).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashboardBacklogApiTests.test_riepilogo_ok
2) DashboardBacklogApiTests.test_riepilogo_requires_jwt
3) DashboardBacklogDocumentiApiTests.test_documenti_ok
4) DashboardBacklogDocumentiApiTests.test_documenti_requires_jwt
5) DashboardBacklogDocumentiApiTests.test_documenti_filtri_lowercase_normalizzati
6) DashboardBacklogDocumentiApiTests.test_documenti_filtri_assenti_none
7) DashboardBacklogDocumentiApiTests.test_documenti_paginazione_parametri
8) DashboardBacklogDocumentiApiTests.test_documenti_ordinamento_parametri
9) DashboardBacklogDocumentiApiTests.test_documenti_scope_db_side_no_auth_user
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova

_RIEPILOGO_RESPONSE = {
    "classi": [
        {
            "classe": "RECUPERABILE",
            "n_documenti": 5,
            "valore_fermo_tot": "2000.50",
            "unita_ferme_tot": 7,
            "anzianita_max_giorni": 90,
            "aree": [{"area": "PREVENTIVO", "n_documenti": 3}],
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
            "area": "PREVENTIVO",
            "documento_id": 42,
            "codice": "PRV0000123",
            "cliente_display": "Rossi Impianti SRL",
            "valore_fermo": "1450.00",
            "unita_ferme": 2,
            "motivo_fermo": "RIGA_RESIDUA",
            "classe": "RECUPERABILE",
            "azione": "smista le righe",
            "data_riferimento": "2026-05-12",
            "anzianita_giorni": 55,
            "stato_codice_interno": "ACCETTATO",
            "stato_codice": "ACC",
        }
    ],
}


class DashboardBacklogApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-backlog/"

    # Scopo: Verifica il caso `test_riepilogo_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_riepilogo")
    def test_riepilogo_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _RIEPILOGO_RESPONSE
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        classe = data["classi"][0]
        # Passthrough dei campi FE-critici dei contatori di testata.
        self.assertEqual(classe["classe"], "RECUPERABILE")
        self.assertEqual(classe["valore_fermo_tot"], "2000.50")
        self.assertEqual(classe["anzianita_max_giorni"], 90)

    # Scopo: Verifica il caso `test_riepilogo_requires_jwt`.
    def test_riepilogo_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)


class DashboardBacklogDocumentiApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/dashboard-backlog/documenti/"

    # Scopo: Verifica il caso `test_documenti_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_ok(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        response = self.client.get(f"{self._URL}?classe=RECUPERABILE&area=PREVENTIVO")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        # Passthrough dei campi FE-critici della lista (classe/motivo/azione
        # alimentano colore, decodifica e hint; anzianita' l'ordinamento).
        self.assertEqual(row["motivo_fermo"], "RIGA_RESIDUA")
        self.assertEqual(row["classe"], "RECUPERABILE")
        self.assertEqual(row["azione"], "smista le righe")
        self.assertEqual(row["anzianita_giorni"], 55)
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["classe"], "RECUPERABILE")
        self.assertEqual(kwargs["area"], "PREVENTIVO")

    # Scopo: Verifica il caso `test_documenti_requires_jwt`.
    def test_documenti_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: classe/area minuscole vengono normalizzate a maiuscolo.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_filtri_lowercase_normalizzati(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?classe=anomalia&area=offerta_commerciale")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["classe"], "ANOMALIA")
        self.assertEqual(kwargs["area"], "OFFERTA_COMMERCIALE")

    # Scopo: Filtri assenti -> None al service (tutte le classi/aree).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_filtri_assenti_none(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertIsNone(kwargs["classe"])
        self.assertIsNone(kwargs["area"])

    # Scopo: page/page_size vengono inoltrati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_paginazione_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?limit=10&offset=20")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 20)

    # Scopo: order_by/order_dir (ordinamento colonne) inoltrati al service;
    #        whitelist/validazione = definizione unica del service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_ordinamento_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?order_by=valore_fermo&order_dir=desc")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "valore_fermo")
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: Lo scope emittente e' interamente DB-side (RLS invoker + GUC):
    #        la view NON passa auth_user_id.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views_dashboard_backlog.fn_dash_backlog_documenti")
    def test_documenti_scope_db_side_no_auth_user(self, mocked_fn, mock_auth, _mock_perm):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)
