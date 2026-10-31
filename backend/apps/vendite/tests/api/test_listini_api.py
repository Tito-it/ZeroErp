# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API vendite/listini.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeListiniApiTests.test_list_listini_ok
2) VenditeListiniApiTests.test_list_listini_v1_requires_jwt
3) VenditeListiniApiTests.test_list_listini_filters_and_pagination
4) VenditeListiniApiTests.test_create_listino_ok
5) VenditeListiniApiTests.test_get_listino_detail_ok
6) VenditeListiniApiTests.test_patch_listino_ok
7) VenditeListiniApiTests.test_list_versioni_ok
8) VenditeListiniApiTests.test_create_versione_ok
9) VenditeListiniApiTests.test_get_versione_ok
10) VenditeListiniApiTests.test_patch_versione_ok
11) VenditeListiniApiTests.test_change_versione_state_ok
11bis) VenditeListiniApiTests.test_programma_chiusura_versione_ok
12) VenditeListiniApiTests.test_list_righe_ok
13) VenditeListiniApiTests.test_create_riga_ok
14) VenditeListiniApiTests.test_patch_riga_ok
15) VenditeListiniApiTests.test_delete_riga_ok
16) VenditeListiniApiTests.test_list_associazioni_ok
17) VenditeListiniApiTests.test_create_associazione_ok
18) VenditeListiniApiTests.test_patch_associazione_ok
19) VenditeListiniApiTests.test_delete_associazione_ok
20) VenditeListiniApiTests.test_test_resolver_ok
21) VenditeListiniApiTests.test_list_listini_invalid_attivo
22) VenditeListiniApiTests.test_list_listini_filter_tipologia_id
23) VenditeListiniApiTests.test_tipologie_per_utility_ok
24) VenditeListiniApiTests.test_tipologie_per_utility_missing_param
25) VenditeListiniApiTests.test_list_listini_filtro_in_scadenza
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_LISTINO_DETAIL = {
    "id": 10,
    "codice": "LIST-UTILITY",
    "descrizione": "Listino Utility Base",
    "utility_id": 1,
    "attivo": True,
    "versioni_count": 1,
    "versioni": [],
}

_LIST_LISTINI_RESULTS = [
    {
        "id": 10,
        "codice": "LIST-UTILITY",
        "descrizione": "Listino Utility Base",
        "utility_id": 1,
        "attivo": True,
        "versioni_count": 1,
    }
]
_LIST_LISTINI_TOTAL = 1

_VERSIONE_DETAIL = {
    "id": 101,
    "listino_id": 10,
    "codice_versione": "2026-Q2",
    "valido_dal": "2026-04-01",
    "valido_al": None,
    "stato": "BOZZA",
    "attivo": True,
    "righe_count": 1,
}

class VenditeListiniApiTests(JwtMockedApiTest):
    # Scopo: Prepara contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = ClientApi()

    # Scopo: Serializza payload JSON per richieste POST/PATCH.
    def _json(self, payload: dict) -> str:
        return json.dumps(payload)

    # Scopo: Verifica il caso `test_list_listini_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_listini")
    def test_list_listini_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_LISTINI_RESULTS, _LIST_LISTINI_TOTAL)
        response = self.client.get("/api/v1/vendite/listini/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codice"], "LIST-UTILITY")

    # Scopo: Verifica che l'endpoint richieda JWT.
    def test_list_listini_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/listini/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica parsing filtri/paginazione della lista listini.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_listini")
    def test_list_listini_filters_and_pagination(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_LISTINI_RESULTS, _LIST_LISTINI_TOTAL)
        self.client.get(
            "/api/v1/vendite/listini/?utility_id=1&attivo=true&search=lis&limit=10&offset=10&order_by=codice&order_dir=desc"
        )
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["utility_id"], 1)
        self.assertTrue(kwargs["attivo"])
        self.assertEqual(kwargs["search"], "lis")
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)
        self.assertEqual(kwargs["order_by"], "codice")
        self.assertEqual(kwargs["order_dir"], "desc")
        # Senza il parametro la regola delle scadenze non filtra.
        self.assertIsNone(kwargs["in_scadenza"])

    # Scopo: Verifica create listino via POST JSON.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_create_listino")
    def test_create_listino_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = _LISTINO_DETAIL
        response = self.client.post(
            "/api/v1/vendite/listini/",
            data=self._json({"codice": "LIST-UTILITY", "descrizione": "Listino Utility Base", "utility_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], 10)
        mocked_create.assert_called_once()

    # Scopo: Verifica dettaglio listino.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_get_listino_dettaglio")
    def test_get_listino_detail_ok(self, mocked_detail, _mock_auth):
        mocked_detail.return_value = _LISTINO_DETAIL
        response = self.client.get("/api/v1/vendite/listini/10/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["codice"], "LIST-UTILITY")

    # Scopo: Verifica patch listino via handle_post_json.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_update_listino")
    def test_patch_listino_ok(self, mocked_update, _mock_auth):
        mocked_update.return_value = {**_LISTINO_DETAIL, "descrizione": "Nuova descrizione"}
        response = self.client.patch(
            "/api/v1/vendite/listini/10/",
            data=self._json({"descrizione": "Nuova descrizione"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["descrizione"], "Nuova descrizione")
        self.assertEqual(mocked_update.call_args.args[0], 10)

    # Scopo: la lista versioni e' una pagina (lista `vendite.listini_versioni`,
    #        dal 2026-10-31): ricerca, pagina e ordinamento arrivano al service,
    #        con `valido_dal` come ordinamento di partenza.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_versioni")
    def test_list_versioni_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = ([{"id": 1}], 1)
        response = self.client.get("/api/v1/vendite/listini/10/versioni/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)
        self.assertEqual(mocked_list.call_args.args, (10,))
        self.assertEqual(mocked_list.call_args.kwargs["order_by"], "valido_dal")
        self.client.get(
            "/api/v1/vendite/listini/10/versioni/?search=2026&limit=10&offset=10"
            "&order_by=giorni_alla_scadenza&order_dir=asc"
        )
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(
            (kwargs["search"], kwargs["limit"], kwargs["offset"], kwargs["order_by"], kwargs["order_dir"]),
            ("2026", 10, 10, "giorni_alla_scadenza", "asc"),
        )

    # Scopo: Verifica create versione.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_create_versione")
    def test_create_versione_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = _VERSIONE_DETAIL
        response = self.client.post(
            "/api/v1/vendite/listini/10/versioni/",
            data=self._json({"codice_versione": "2026-Q2", "valido_dal": "2026-04-01"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], 101)

    # Scopo: Verifica dettaglio versione.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_get_versione")
    def test_get_versione_ok(self, mocked_get, _mock_auth):
        mocked_get.return_value = _VERSIONE_DETAIL
        response = self.client.get("/api/v1/vendite/listini/10/versioni/101/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["codice_versione"], "2026-Q2")

    # Scopo: Verifica patch versione (il routing: la fine di una ATTIVA la
    #        rifiuta il DB, C-4 = a, e si cambia dalla rotta `chiusura/`).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_update_versione")
    def test_patch_versione_ok(self, mocked_update, _mock_auth):
        mocked_update.return_value = {**_VERSIONE_DETAIL, "valido_al": "2026-12-31"}
        response = self.client.patch(
            "/api/v1/vendite/listini/10/versioni/101/",
            data=self._json({"valido_al": "2026-12-31"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["valido_al"], "2026-12-31")

    # Scopo: Verifica cambio stato versione.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_change_versione_state")
    def test_change_versione_state_ok(self, mocked_state, _mock_auth):
        mocked_state.return_value = {**_VERSIONE_DETAIL, "stato": "ATTIVA"}
        response = self.client.post(
            "/api/v1/vendite/listini/10/versioni/101/stato/",
            data=self._json({"stato": "ATTIVA"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["stato"], "ATTIVA")

    # Scopo: «Chiudi» ha la sua rotta (§16.16, BE-C2): il corpo arriva al
    #        service com'e', compreso `valido_al` null (toglie la chiusura).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_programma_chiusura_versione")
    def test_programma_chiusura_versione_ok(self, mocked_chiusura, _mock_auth):
        mocked_chiusura.return_value = {**_VERSIONE_DETAIL, "valido_al": None}
        response = self.client.post(
            "/api/v1/vendite/listini/10/versioni/101/chiusura/",
            data=self._json({"valido_al": None}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mocked_chiusura.assert_called_once_with(10, 101, {"valido_al": None})
        # Il permesso del PATCH che sostituisce (`change`), non quello di una
        # creazione (`add`, il default della POST).
        from apps.core.api.permissions import ZeroERPPermission
        from apps.vendite.api.views_listini import ApiListinoVersioneChiusura

        self.assertEqual(
            ZeroERPPermission.tipo_accesso(ApiListinoVersioneChiusura, method="POST"), "change",
        )

    # Scopo: Verifica lista righe paginata.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_righe")
    def test_list_righe_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = ([{"id": 1}], 1)
        response = self.client.get("/api/v1/vendite/listini/10/versioni/101/righe/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)

    # Scopo: Verifica create riga.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_create_riga")
    def test_create_riga_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = {"id": 1001, "prezzo": "12.5000000000"}
        response = self.client.post(
            "/api/v1/vendite/listini/10/versioni/101/righe/",
            data=self._json(
                {
                    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                    "uom_id": 1,
                    "prezzo": "12.5000000000",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], 1001)

    # Scopo: Verifica patch riga.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_update_riga")
    def test_patch_riga_ok(self, mocked_update, _mock_auth):
        mocked_update.return_value = {"id": 1001, "prezzo": "9.9900000000"}
        response = self.client.patch(
            "/api/v1/vendite/listini/10/versioni/101/righe/1001/",
            data=self._json({"prezzo": "9.9900000000"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["prezzo"], "9.9900000000")

    # Scopo: Verifica delete riga.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_delete_riga")
    def test_delete_riga_ok(self, mocked_delete, _mock_auth):
        mocked_delete.return_value = {"deleted": True, "id": 1001}
        response = self.client.delete("/api/v1/vendite/listini/10/versioni/101/righe/1001/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["deleted"])

    # F2-BE-13: rimossi test associazioni e test-prezzo (endpoint eliminati).
    # Associazioni: modello v5 non usa piu' `listini_associazioni`.
    # Test resolver prezzo: ora via `PricingService.resolve_prezzo`.

    # Scopo: Verifica validazione rigorosa del filtro bool `attivo`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_listini_invalid_attivo(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/listini/?attivo=forse")
        self.assertEqual(response.status_code, 400)

    # Scopo: Verifica che il filtro tipologia_id sia propagato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_listini")
    def test_list_listini_filter_tipologia_id(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_LISTINI_RESULTS, _LIST_LISTINI_TOTAL)
        response = self.client.get("/api/v1/vendite/listini/?tipologia_id=3")
        self.assertEqual(response.status_code, 200)
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["tipologia_id"], 3)

    # Scopo: Verifica che l'endpoint tipologie-per-utility restituisca le
    #        tipologie in envelope standard success_response({"results": [...]}).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_tipologie_per_utility")
    def test_tipologie_per_utility_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = [
            {"id": 1, "codice": "CONSUMO", "descrizione": "Consumi"},
            {"id": 2, "codice": "QUOTA_FISSA", "descrizione": "Quote fisse"},
        ]
        response = self.client.get(
            "/api/v1/vendite/listini/tipologie-per-utility/?utility_id=1"
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["data"]["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["codice"], "CONSUMO")
        mocked_list.assert_called_once_with(1)

    # Scopo: Verifica che tipologie-per-utility rifiuti utility_id mancante
    #        con codice errore semantico corretto (obbligatorio, non "positivo").
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_tipologie_per_utility_missing_param(self, _mock_auth):
        response = self.client.get(
            "/api/v1/vendite/listini/tipologie-per-utility/"
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        # Envelope standard: {"error": {"code": ..., "message": ..., "detail": ...}}.
        # Il detail deve riportare "obbligatorio", non "positivo".
        err = body.get("error", {})
        self.assertEqual(err.get("code"), "E_VENDITE_VALIDATION")
        self.assertIn("obbligatorio", (err.get("detail") or "").lower())

    # Scopo: Verifica che tipologie-per-utility rifiuti utility_id stringa vuota.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_tipologie_per_utility_empty_param(self, _mock_auth):
        response = self.client.get(
            "/api/v1/vendite/listini/tipologie-per-utility/?utility_id="
        )
        self.assertEqual(response.status_code, 400)

    # Scopo: il filtro del badge delle scadenze (D-1): `in_scadenza` arriva al
    #        service come booleano; un valore che non e' booleano e' un 400.
    #        ⛔ Fino al 2026-10-31 il badge aveva il suo endpoint
    #        (`alert-scadenze/`, ritirato) con N passato dal client.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views_listini.fn_list_listini")
    def test_list_listini_filtro_in_scadenza(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_LISTINI_RESULTS, _LIST_LISTINI_TOTAL)
        response = self.client.get("/api/v1/vendite/listini/?in_scadenza=true")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_list.call_args.kwargs["in_scadenza"])
        response = self.client.get("/api/v1/vendite/listini/?in_scadenza=forse")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/v1/vendite/listini/alert-scadenze/")
        self.assertNotEqual(response.status_code, 200)
