# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API elenco lotti fatturazione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeLottiListApiTests.test_list_lotti_ok
2) VenditeLottiListApiTests.test_list_lotti_v1_requires_jwt
3) VenditeLottiListApiTests.test_list_lotti_filtro_competenza_mese
4) VenditeLottiListApiTests.test_list_lotti_filtro_utility_id
5) VenditeLottiListApiTests.test_list_lotti_filtro_stato_lotto
6) VenditeLottiListApiTests.test_list_lotti_filtro_area_geografica_id
7) VenditeLottiListApiTests.test_list_lotti_filtro_tipo_doc_fiscale_id
8) VenditeLottiListApiTests.test_list_lotti_filtro_emittente_soggetto_ruolo_id
9) VenditeLottiListApiTests.test_list_lotti_paginazione_parametri
10) VenditeLottiListApiTests.test_list_lotti_page_size_invalido
11) VenditeLottiListApiTests.test_list_lotti_page_invalida
12) VenditeLottiListApiTests.test_list_lotti_senza_filtri_lista_vuota_ok
13) VenditeLottiListApiTests.test_list_lotti_scope_emittente_non_superuser
14) VenditeLottiListApiTests.test_list_lotti_scope_emittente_superuser
15) VenditeLottoDetailApiTests.test_get_lotto_detail_ok
16) VenditeLottoDetailApiTests.test_get_lotto_detail_requires_jwt
17) VenditeLottoDetailApiTests.test_get_lotto_detail_not_found
18) VenditeLottoDetailApiTests.test_get_lotto_detail_scope_non_superuser
"""

from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


_LOTTO_ROW = {
    "id": 42,
    "codice": "LOT-2026-001",
    "competenza_mese": "2026-02-01",
    "tipo_lotto": "MASSIVO",
    "utility_id": 1,
    "utility_descrizione": "Energia Elettrica",
    "stato_lotto": "DRAFT",
    "stato_operativo": "APERTO",
    "stato_doc_fiscale_id": 3,
    "stato_doc_fiscale_descrizione": "Fattura emessa",
    "tipo_doc_fiscale_id": 1,
    "tipo_doc_fiscale_descrizione": "Fattura",
    "area_geografica_id": 2,
    "area_geografica_descrizione": "Nord",
    "emittente_soggetto_ruolo_id": 7,
    "data_insert": "2026-02-18T10:00:00+01:00",
    "user_insert": "zeroerp",
}

_LIST_RESPONSE = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [_LOTTO_ROW],
}


class VenditeLottiListApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Verifica il caso `test_list_lotti_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"][0]["id"], 42)
        self.assertEqual(data["results"][0]["codice"], "LOT-2026-001")

    # Scopo: Verifica il caso `test_list_lotti_v1_requires_jwt`.
    def test_list_lotti_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_list_lotti_filtro_competenza_mese`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_competenza_mese(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?competenza_mese=2026-02-01")
        mocked_list.assert_called_once()
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 2, 1))

    # Scopo: Verifica il caso `test_list_lotti_filtro_utility_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_utility_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?utility_id=5")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["utility_id"], 5)

    # Scopo: Verifica il caso `test_list_lotti_filtro_stato_lotto`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_stato_lotto(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?stato_lotto=DRAFT")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["stato_lotto"], "DRAFT")

    # Scopo: Verifica il caso `test_list_lotti_filtro_area_geografica_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_area_geografica_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?area_geografica_id=2")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["area_geografica_id"], 2)

    # Scopo: Verifica il caso `test_list_lotti_filtro_tipo_doc_fiscale_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_tipo_doc_fiscale_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?tipo_doc_fiscale_id=1")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["tipo_doc_fiscale_id"], 1)

    # Scopo: Verifica il caso `test_list_lotti_filtro_emittente_soggetto_ruolo_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_filtro_emittente_soggetto_ruolo_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/?emittente_soggetto_ruolo_id=10")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 10)

    # Scopo: Verifica il caso `test_list_lotti_paginazione_parametri`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_paginazione_parametri(self, mocked_list, _mock_auth):
        mocked_list.return_value = {**_LIST_RESPONSE, "page": 2, "page_size": 10}
        self.client.get("/api/v1/vendite/lotti/?limit=10&offset=10")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)

    # Scopo: Verifica il caso `test_list_lotti_page_size_invalido`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_lotti_page_size_invalido(self, _mock_auth):
        # Dal 2026-10-21 la lista pagina con `limit`/`offset`: `page_size` e' un 400.
        response = self.client.get("/api/v1/vendite/lotti/?page_size=10")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica il caso `test_list_lotti_page_invalida`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_lotti_page_invalida(self, _mock_auth):
        # `page` non e' piu' un parametro, e un `limit` illeggibile e' un 400.
        for qs in ("page=2", "limit=abc"):
            with self.subTest(qs=qs):
                response = self.client.get(f"/api/v1/vendite/lotti/?{qs}")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica il caso `test_list_lotti_senza_filtri_lista_vuota_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_senza_filtri_lista_vuota_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "count": 0,
            "page": 1,
            "page_size": 50,
            "total_pages": 0,
            "results": [],
        }
        response = self.client.get("/api/v1/vendite/lotti/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["competenza_mese"])
        self.assertIsNone(kwargs["utility_id"])
        self.assertIsNone(kwargs["stato_lotto"])
        self.assertIsNone(kwargs["area_geografica_id"])
        self.assertIsNone(kwargs["tipo_doc_fiscale_id"])
        self.assertIsNone(kwargs["emittente_soggetto_ruolo_id"])

    # Scopo: Utente non superuser passa auth_user_id al service.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_scope_emittente_non_superuser(self, mocked_list, mock_auth, _mock_perm):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/")
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)

    # Scopo: Superuser passa auth_user_id=None (nessun filtro scope).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_list_lotti")
    def test_list_lotti_scope_emittente_superuser(self, mocked_list, mock_auth):
        user = Mock()
        user.id = 1
        user.is_superuser = True
        user.is_authenticated = True
        mock_auth.return_value = (user, None)
        mocked_list.return_value = _LIST_RESPONSE
        self.client.get("/api/v1/vendite/lotti/")
        kwargs = mocked_list.call_args.kwargs
        self.assertIsNone(kwargs["auth_user_id"])


class VenditeLottoDetailApiTests(JwtMockedApiTest):
    """Dettaglio testata singolo lotto (cockpit Fase B, B-1)."""

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: dettaglio ok → 200 con la testata del lotto.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto")
    def test_get_lotto_detail_ok(self, mocked_get, _mock_auth):
        mocked_get.return_value = _LOTTO_ROW
        response = self.client.get("/api/v1/vendite/lotti/42/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["codice"], "LOT-2026-001")
        mocked_get.assert_called_once()
        self.assertEqual(mocked_get.call_args.kwargs["lotto_id"], 42)

    # Scopo: endpoint richiede JWT.
    def test_get_lotto_detail_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/lotti/42/")
        self.assertEqual(response.status_code, 401)

    # Scopo: lotto inesistente/fuori scope → 404 E_LOTTO_NON_TROVATO.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto")
    def test_get_lotto_detail_not_found(self, mocked_get, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_get.side_effect = ServiceError(code="E_LOTTO_NON_TROVATO", message="Lotto non trovato.")
        response = self.client.get("/api/v1/vendite/lotti/999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_LOTTO_NON_TROVATO")

    # Scopo: scope emittente — auth_user_id passato al service per non-superuser.
    @patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_get_lotto")
    def test_get_lotto_detail_scope_non_superuser(self, mocked_get, mock_auth, _mock_perm):
        user = operatore_di_prova(user_id=77)
        mock_auth.return_value = (user, None)
        mocked_get.return_value = _LOTTO_ROW
        self.client.get("/api/v1/vendite/lotti/42/")
        self.assertEqual(mocked_get.call_args.kwargs["auth_user_id"], 77)
