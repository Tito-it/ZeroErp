# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API serbatoio pre-commessa (Situazione aperta v2:
#        riepilogo area×fase + documenti).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashboardApertoApiTests.test_riepilogo_ok
2) DashboardApertoApiTests.test_riepilogo_requires_jwt
3) DashboardApertoDocumentiApiTests.test_documenti_ok
4) DashboardApertoDocumentiApiTests.test_documenti_requires_jwt
5) DashboardApertoDocumentiApiTests.test_documenti_filtri_lowercase_normalizzati
6) DashboardApertoDocumentiApiTests.test_documenti_filtri_assenti_default
7) DashboardApertoDocumentiApiTests.test_documenti_ritardo_giorni
8) DashboardApertoDocumentiApiTests.test_documenti_paginazione_parametri
9) DashboardApertoDocumentiApiTests.test_documenti_ordinamento_parametri
10) DashboardApertoDocumentiApiTests.test_documenti_scope_db_side_no_auth_user
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova

# v2: perimetro aperti-non-chiusi lato vista -> niente n_aperti/valore_transitato.
_RIEPILOGO_RESPONSE = {
    "aree": [
        {
            "area": "PREVENTIVO",
            "n_documenti": 5,
            "valore_totale": "2000.50",
            "fasi": [{"fase": "APERTO", "n_documenti": 3, "valore_totale": "1500.00"}],
        }
    ],
    "fasi": ["APERTO", "IN_ATTESA", "IN_CORSO"],
}

# v2: via i campi transitato/is_aperto; dentro anzianita_giorni (derivata BE).
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
            "fase": "IN_CORSO",
            "stato_codice_interno": "ACCETTATO",
            "stato_codice": "ACC",
            "valore_totale": "1450.00",
            "unita_totali": 2,
            "anzianita_giorni": 57,
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
        self.assertEqual(area["area"], "PREVENTIVO")
        self.assertEqual(area["n_documenti"], 5)
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
        response = self.client.get(f"{self._URL}?area=PREVENTIVO&fase=IN_CORSO")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        # Passthrough dei campi FE-critici della lista (fase/stato alimentano
        # tag e raggruppamento; anzianita_giorni la colonna "aperto da N gg";
        # data_riferimento l'ordine e il tooltip).
        self.assertEqual(row["fase"], "IN_CORSO")
        self.assertEqual(row["stato_codice_interno"], "ACCETTATO")
        self.assertEqual(row["anzianita_giorni"], 57)
        self.assertEqual(row["data_riferimento"], "2026-05-12")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["area"], "PREVENTIVO")
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
        self.client.get(f"{self._URL}?area=offerta_commerciale&fase=in_corso")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["area"], "OFFERTA_COMMERCIALE")
        self.assertEqual(kwargs["fase"], "IN_CORSO")

    # Scopo: Filtri assenti -> None al service (tutte le aree/fasi); anche
    #        ritardo_giorni assente passa None: nessuna soglia, drill-down
    #        completo coerente con le card fotografia (DL-17).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_filtri_assenti_default(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertIsNone(kwargs["area"])
        self.assertIsNone(kwargs["fase"])
        self.assertIsNone(kwargs["ritardo_giorni"])

    # Scopo: ritardo_giorni ("aperti da oltre N giorni", DL-17) inoltrato al
    #        service (filtro del SOLO drill-down).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_ritardo_giorni(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?ritardo_giorni=60")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["ritardo_giorni"], 60)

    # Scopo: page/page_size vengono inoltrati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_paginazione_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?limit=10&offset=20")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 20)

    # Scopo: order_by/order_dir (ordinamento colonne, convenzione standard)
    #        inoltrati al service; la whitelist/validazione e' definizione unica
    #        del service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_ordinamento_parametri(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(f"{self._URL}?order_by=cliente_display&order_dir=asc")
        kwargs = mocked_fn.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "cliente_display")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: Lo scope emittente e' interamente DB-side (RLS invoker): la view
    #        NON passa auth_user_id.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views_dashboard_aperto.fn_dash_aperto_documenti")
    def test_documenti_scope_db_side_no_auth_user(self, mocked_fn, mock_auth, _mock_perm):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_fn.return_value = _DOCUMENTI_RESPONSE
        self.client.get(self._URL)
        kwargs = mocked_fn.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)
