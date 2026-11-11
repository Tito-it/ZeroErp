# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API catalogo Fasi 1-3 (read + CRUD articolo + sottorisorse).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CatalogoApiTests.test_list_articoli_ok
2) CatalogoApiTests.test_list_articoli_requires_jwt
3) CatalogoApiTests.test_list_articoli_parametri
4) CatalogoApiTests.test_list_articoli_invalid_limit_e_400
5) CatalogoApiTests.test_list_articoli_search_corta_non_e_un_errore
6) CatalogoApiTests.test_list_articoli_invalid_tipo_voce_id
7) CatalogoApiTests.test_get_articolo_ok
8) CatalogoApiTests.test_get_articolo_not_found
9) CatalogoApiTests.test_lookup_articoli_ok
10) CatalogoApiTests.test_lookup_articoli_invalid_limit
10a) CatalogoApiTests.test_lookup_articoli_documento_va_alla_sede_unica
10b) CatalogoApiTests.test_lookup_articoli_documento_rifiuta_i_filtri_liberi
10c) CatalogoApiTests.test_lookup_articoli_padre_non_uuid
10c-bis) CatalogoApiTests.test_lookup_articoli_filtri_ritirati
10d) CatalogoApiTests.test_patch_articolo_porta_la_correzione_di_struttura
11) CatalogoApiTests.test_create_articolo_ok
14) CatalogoApiTests.test_create_articolo_validation_error
15) CatalogoApiTests.test_patch_articolo_ok
16) CatalogoApiTests.test_patch_articolo_not_found
17) CatalogoApiTests.test_disattiva_articolo_ok
18) CatalogoApiTests.test_get_articolo_uom_list_ok
19) CatalogoApiTests.test_post_articolo_uom_ok
20) CatalogoApiTests.test_patch_articolo_uom_not_found
21) CatalogoApiTests.test_get_articolo_componenti_ok
22) CatalogoApiTests.test_post_articolo_componente_ok
23) CatalogoApiTests.test_get_articolo_note_ok
24) CatalogoApiTests.test_post_articolo_nota_ok
25) CatalogoApiTests.test_patch_nota_not_found
25b) CatalogoApiTests.test_note_legame_di_un_altro_articolo_404
25c) CatalogoApiTests.test_note_di_catalogo_senza_cancello_di_perimetro
25d) NoteCatalogoSchemaTests.test_target_riga_id_solo_dove_ci_sono_righe
27) CatalogoApiTests.test_get_articolo_componenti_capability_ok
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.services.partitioned_note_service import PartitionedNoteService
from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_LIST_RESULTS = [{"id": 1, "codice": "ART-001", "descrizione": "Articolo demo"}]
_LIST_TOTAL = 1

_ARTICOLO_UUID = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
_MISSING_ARTICOLO_UUID = "00000000-0000-0000-0000-000000000000"

_DETAIL_RESPONSE = {
    "id": _ARTICOLO_UUID,
    "codice": "ART-001",
    "descrizione": "Articolo demo",
    "uom_codice": "PZ",
}

_LOOKUP_RESPONSE = {
    "count": 1,
    "results": [{"id": 1, "codice": "ART-001", "descrizione": "Articolo demo"}],
}

_COMPONENTE_UUID = "11111111-2222-3333-4444-555555555555"


class CatalogoApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune dei test API catalogo.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = ClientApi()

    # Scopo: Lista articoli base -> 200 con envelope paginato.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_articoli")
    def test_list_articoli_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_RESULTS, _LIST_TOTAL)

        response = self.client.get("/api/v1/catalogo/articoli/")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codice"], "ART-001")

    # Scopo: JWT assente -> 401.
    def test_list_articoli_requires_jwt(self):
        response = self.client.get("/api/v1/catalogo/articoli/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Query params correttamente passati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_articoli")
    def test_list_articoli_parametri(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_RESULTS, _LIST_TOTAL)

        self.client.get(
            "/api/v1/catalogo/articoli/"
            "?search=art&limit=10&offset=10&attivo=false&order_by=codice&order_dir=desc"
        )

        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["search"], "art")
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 10)
        self.assertFalse(kwargs["attivo"])
        self.assertEqual(kwargs["order_by"], "codice")
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: ⛔ limit/offset non numerici → 400, non il ripiego muto sul
    #        default (decisione Tid 2026-10-21, BB `pagina_da_query`): il
    #        ripiego dava la prima pagina a chi ne aveva chiesta un'altra.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_articoli")
    def test_list_articoli_invalid_limit_e_400(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_RESULTS, _LIST_TOTAL)
        for qs in ("limit=abc", "offset=xyz"):
            with self.subTest(qs=qs):
                response = self.client.get(f"/api/v1/catalogo/articoli/?{qs}")
                self.assertEqual(response.status_code, 400)
        mocked_list.assert_not_called()

    # Scopo: search corta -> 200, il termine arriva al repository (sotto la
    #        soglia del catalogo lo ignora il BB). ⛔ Nessun 400 sotto soglia
    #        (brief-db-be-fe-ricerca-soglia-per-lista §6 a, Tid 2026-09-26).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_articoli")
    def test_list_articoli_search_corta_non_e_un_errore(self, mocked_list, _mock_auth):
        mocked_list.return_value = (_LIST_RESULTS, _LIST_TOTAL)
        response = self.client.get("/api/v1/catalogo/articoli/?search=ab")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_list.call_args.kwargs["search"], "ab")

    # Scopo: filtro integer non numerico -> 400 validazione input, non silenzioso fallback.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_list_articoli_invalid_tipo_voce_id(self, _mock_auth):
        response = self.client.get("/api/v1/catalogo/articoli/?tipo_voce_id=abc")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")

    # Scopo: Dettaglio articolo -> 200 con dict dati.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_get_articolo")
    def test_get_articolo_ok(self, mocked_get, _mock_auth):
        mocked_get.return_value = _DETAIL_RESPONSE

        response = self.client.get(f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["uom_codice"], "PZ")

    # Scopo: articolo non trovato -> mapping policy 404 del nuovo codice catalogo.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_get_articolo")
    def test_get_articolo_not_found(self, mocked_get, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_get.side_effect = ServiceError(
            code="E_CATALOGO_ARTICOLO_NOT_FOUND",
            message="Articolo non trovato.",
        )

        response = self.client.get(f"/api/v1/catalogo/articoli/{_MISSING_ARTICOLO_UUID}/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_ARTICOLO_NOT_FOUND")

    # Scopo: Lookup articoli -> 200 con count e filtri passati.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli")
    def test_lookup_articoli_ok(self, mocked_lookup, _mock_auth):
        mocked_lookup.return_value = _LOOKUP_RESPONSE

        response = self.client.get("/api/v1/catalogo/articoli/lookup/?search=art&limit=15&attivo=true")

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_lookup.call_args.kwargs
        self.assertEqual(kwargs["search"], "art")
        self.assertEqual(kwargs["limit"], 15)
        self.assertTrue(kwargs["attivo"])

    # Scopo: con `documento` il lookup va alla sede unica del picker
    # (`fn_lookup_articoli_ammessi`) col contesto normalizzato, e la ricerca
    # libera non viene chiamata (brief-db-articoli-ammessi-per-documento §9.6).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli")
    @patch("apps.catalogo.api.views.fn_lookup_articoli_ammessi")
    def test_lookup_articoli_documento_va_alla_sede_unica(self, mocked_ammessi, mocked_lookup, _mock_auth):
        mocked_ammessi.return_value = _LOOKUP_RESPONSE

        response = self.client.get(
            "/api/v1/catalogo/articoli/lookup/?search=art&documento=contratto"
            "&documento_id=5&tipo_eccezione=aggiunta"
        )

        self.assertEqual(response.status_code, 200)
        mocked_lookup.assert_not_called()
        kwargs = mocked_ammessi.call_args.kwargs
        self.assertEqual(kwargs["documento"], "CONTRATTO")
        self.assertEqual(kwargs["documento_id"], 5)
        self.assertEqual(kwargs["tipo_eccezione"], "AGGIUNTA")
        self.assertIsNone(kwargs["articolo_padre_id"])
        self.assertEqual(kwargs["search"], "art")

    # Scopo: ⛔ accanto a `documento` nessun filtro libero: la regola della riga
    # la dice il DB, e un filtro in piu' nasconderebbe un articolo ammesso.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli_ammessi")
    def test_lookup_articoli_documento_rifiuta_i_filtri_liberi(self, mocked_ammessi, _mock_auth):
        for filtro in ("attivo=true", "is_composito=false", "gestito_a_magazzino=true", "solo_oneri=true"):
            with self.subTest(filtro=filtro):
                response = self.client.get(
                    f"/api/v1/catalogo/articoli/lookup/?documento=PREVENTIVO&documento_id=1&{filtro}"
                )
                self.assertEqual(response.status_code, 400)
        mocked_ammessi.assert_not_called()

    # Scopo: i filtri ritirati (`is_solo_componente`, `escludi_destinazione`)
    # sono un 400 che li nomina, con o senza `documento`: ignorati, il
    # chiamante crederebbe di filtrare e riceverebbe tutto.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli")
    @patch("apps.catalogo.api.views.fn_lookup_articoli_ammessi")
    def test_lookup_articoli_filtri_ritirati(self, mocked_ammessi, mocked_lookup, _mock_auth):
        for query in (
            "search=art&is_solo_componente=false",
            "search=art&escludi_destinazione=CONTRATTO",
            "documento=PREVENTIVO&documento_id=1&escludi_destinazione=CONTRATTO",
        ):
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/catalogo/articoli/lookup/?{query}")
                self.assertEqual(response.status_code, 400)
                self.assertIn("_ritirato", response.json()["error"]["message"])
        mocked_lookup.assert_not_called()
        mocked_ammessi.assert_not_called()

    # Scopo: un padre di distinta che non e' un UUID e' un 400, non il cast a
    # `uuid` del DB (che sarebbe un 500).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli_ammessi")
    def test_lookup_articoli_padre_non_uuid(self, mocked_ammessi, _mock_auth):
        response = self.client.get(
            "/api/v1/catalogo/articoli/lookup/?documento=ARTICOLO&articolo_padre_id=abc"
        )

        self.assertEqual(response.status_code, 400)
        mocked_ammessi.assert_not_called()

    # Scopo: la correzione di struttura viaggia nel PATCH dell'articolo (R-BE-1,
    # 2026-10-18): il corpo arriva intero al service, `correzione_struttura`
    # compreso; l'endpoint dedicato `…/struttura/` non c'e' piu'. Il permesso
    # (SUPER_ADMIN) lo giudica il verbo del DB (`E_PERMESSO_NEGATO`, provato su
    # DB vero in tests/db/test_articoli_ammessi_db.py).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_update_articolo")
    def test_patch_articolo_porta_la_correzione_di_struttura(self, mocked_update, _mock_auth):
        mocked_update.return_value = _DETAIL_RESPONSE
        corpo = {"descrizione": "Nuova", "correzione_struttura": {"requires_lotto": True}}

        response = self.client.patch(
            f"/api/v1/catalogo/articoli/{_COMPONENTE_UUID}/",
            data=corpo, content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        articolo_id, payload = mocked_update.call_args.args
        self.assertEqual(str(articolo_id), _COMPONENTE_UUID)
        self.assertEqual(payload, corpo)
        response = self.client.post(
            f"/api/v1/catalogo/articoli/{_COMPONENTE_UUID}/struttura/",
            data={"campi": {"requires_lotto": True}}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    # Scopo: limit lookup articoli fuori range -> 400 dal service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_lookup_articoli")
    def test_lookup_articoli_invalid_limit(self, mocked_lookup, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_lookup.side_effect = ServiceError(
            code="E_CATALOGO_VALIDATION",
            message="Parametri lookup non validi.",
        )

        response = self.client.get("/api/v1/catalogo/articoli/lookup/?search=art&limit=0")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_VALIDATION")

    # Nota: il lookup UoM usa l'endpoint generico /core/lookup/codici/?rel=catalogo.unita_misura
    # I test del lookup generico sono in apps.core.tests.api.test_lookup_codici_api

    # Scopo: POST create articolo -> 200 e payload inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_create_articolo")
    def test_create_articolo_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = _DETAIL_RESPONSE

        response = self.client.post(
            "/api/v1/catalogo/articoli/",
            data=json.dumps({"codice": "ART-001", "descrizione": "Articolo demo"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["codice"], "ART-001")
        self.assertEqual(
            mocked_create.call_args.args[0],
            {"codice": "ART-001", "descrizione": "Articolo demo"},
        )

    # Scopo: errore validazione create -> 400 con policy catalogo.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_create_articolo")
    def test_create_articolo_validation_error(self, mocked_create, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_create.side_effect = ServiceError(
            code="E_CATALOGO_VALIDATION",
            message="codice obbligatorio.",
        )

        response = self.client.post(
            "/api/v1/catalogo/articoli/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_VALIDATION")

    # Scopo: PATCH articolo -> 200 e inoltro payload al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_update_articolo")
    def test_patch_articolo_ok(self, mocked_update, _mock_auth):
        mocked_update.return_value = {**_DETAIL_RESPONSE, "descrizione": "Articolo aggiornato"}

        response = self.client.patch(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/",
            data=json.dumps({"descrizione": "Articolo aggiornato", "descrizione_breve": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["descrizione"], "Articolo aggiornato")
        self.assertEqual(str(mocked_update.call_args.args[0]), _ARTICOLO_UUID)
        self.assertEqual(
            mocked_update.call_args.args[1],
            {"descrizione": "Articolo aggiornato", "descrizione_breve": ""},
        )

    # Scopo: articolo inesistente su PATCH -> 404 coerente con policy not found.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_update_articolo")
    def test_patch_articolo_not_found(self, mocked_update, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_update.side_effect = ServiceError(
            code="E_CATALOGO_ARTICOLO_NOT_FOUND",
            message="Articolo non trovato.",
        )

        response = self.client.patch(
            f"/api/v1/catalogo/articoli/{_MISSING_ARTICOLO_UUID}/",
            data=json.dumps({"descrizione": "x"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_ARTICOLO_NOT_FOUND")

    # Scopo: disattivazione articolo -> 200 con articolo aggiornato.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_disattiva_articolo")
    def test_disattiva_articolo_ok(self, mocked_disable, _mock_auth):
        mocked_disable.return_value = {**_DETAIL_RESPONSE, "attivo": False}

        response = self.client.post(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/disattiva/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["attivo"])
        self.assertEqual(str(mocked_disable.call_args.args[0]), _ARTICOLO_UUID)

    # Scopo: GET UoM articolo -> 200, la pagina della lista `catalogo.articolo_uom`
    #        (dal 2026-10-31) coi campi non modificabili accanto alla busta;
    #        ricerca e ordinamento arrivano al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_uom_operative_pagina")
    def test_get_articolo_uom_list_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = ([{"id": 11, "uom_codice": "PZ"}], 1, ["uom_id"])

        response = self.client.get(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/uom/?search=p&order_by=uom_codice&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual((data["count"], data["results"][0]["uom_codice"]), (1, "PZ"))
        self.assertEqual(data["non_editable_fields"], ["uom_id"])
        self.assertEqual(str(mocked_list.call_args.args[0]), _ARTICOLO_UUID)
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual((kwargs["search"], kwargs["order_by"], kwargs["limit"]), ("p", "uom_codice", 10))

    # Scopo: POST UoM articolo -> 200 e payload inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_create_uom_operativa")
    def test_post_articolo_uom_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = {"id": 11, "uom_id": 3, "uom_codice": "PZ"}

        response = self.client.post(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/uom/",
            data=json.dumps({"uom_id": 3, "factor_to_base": "1"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], 11)
        self.assertEqual(str(mocked_create.call_args.args[0]), _ARTICOLO_UUID)
        self.assertEqual(mocked_create.call_args.args[1], {"uom_id": 3, "factor_to_base": "1"})

    # Scopo: PATCH UoM assente -> 404 via policy catalogo.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_update_uom_operativa")
    def test_patch_articolo_uom_not_found(self, mocked_update, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_update.side_effect = ServiceError(
            code="E_CATALOGO_UOM_NOT_FOUND",
            message="UoM operativa non trovata.",
        )

        response = self.client.patch(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/uom/99/",
            data=json.dumps({"factor_to_base": "2"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_UOM_NOT_FOUND")

    # Scopo: GET componenti articolo -> 200 con envelope count/results.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_componenti")
    def test_get_articolo_componenti_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {"count": 1, "results": [{"id": _COMPONENTE_UUID, "coeff_qta": 1}]}

        response = self.client.get(f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/componenti/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)
        self.assertEqual(str(mocked_list.call_args.args[0]), _ARTICOLO_UUID)

    # Scopo: I campi capability di chiusura riga (Fase 2 refactor catalogo)
    # devono attraversare envelope/serializer senza filtri.
    # Naming italiano coerente con la vista catalogo.vw_articoli_componenti_dettaglio.
    # La copertura della logica SQL CASE WHEN e' lato pgTAP (team DB).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_list_componenti")
    def test_get_articolo_componenti_capability_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "count": 2,
            "results": [
                {
                    "id": _COMPONENTE_UUID,
                    "valido_al": None,
                    "puo_chiudersi": True,
                    "data_min_chiusura": "2026-04-01",
                    "data_default_chiusura": "2026-04-28",
                    "motivo_non_chiudibile": None,
                },
                {
                    "id": "11111111-2222-3333-4444-555555555556",
                    "valido_al": "2026-03-31",
                    "puo_chiudersi": False,
                    "data_min_chiusura": None,
                    "data_default_chiusura": None,
                    "motivo_non_chiudibile": "RIGA_GIA_CHIUSA",
                },
            ],
        }

        response = self.client.get(f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/componenti/")

        self.assertEqual(response.status_code, 200)
        rows = response.json()["data"]["results"]
        # Riga aperta: capability popolate con date valorizzate.
        self.assertTrue(rows[0]["puo_chiudersi"])
        self.assertEqual(rows[0]["data_min_chiusura"], "2026-04-01")
        self.assertEqual(rows[0]["data_default_chiusura"], "2026-04-28")
        self.assertIsNone(rows[0]["motivo_non_chiudibile"])
        # Riga chiusa: blocco autodocumentante (date NULL + motivo).
        self.assertFalse(rows[1]["puo_chiudersi"])
        self.assertIsNone(rows[1]["data_min_chiusura"])
        self.assertIsNone(rows[1]["data_default_chiusura"])
        self.assertEqual(rows[1]["motivo_non_chiudibile"], "RIGA_GIA_CHIUSA")

    # Scopo: POST componente articolo -> 200 e payload inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.views.fn_create_componente")
    def test_post_articolo_componente_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = {"id": _COMPONENTE_UUID, "coeff_qta": 1}

        response = self.client.post(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/componenti/",
            data=json.dumps(
                {
                    "componente_id": _ARTICOLO_UUID,
                    "coeff_qta": "1",
                    "valido_dal": "2026-01-01",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], _COMPONENTE_UUID)
        self.assertEqual(str(mocked_create.call_args.args[0]), _ARTICOLO_UUID)

    # Scopo: GET note articolo -> 200 con envelope count/results. Dal
    #        2026-11-11 le note di catalogo passano dal BB delle note
    #        (`make_note_views` + `PartitionedNoteService`): la chiave del
    #        padre arriva al service come la da' il percorso (UUID).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch.object(PartitionedNoteService, "list_note", autospec=True)
    def test_get_articolo_note_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = ([{"id": 5, "testo": "Demo"}], 1)

        response = self.client.get(f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/note/?search=dem")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["results"][0]["id"], 5)
        self.assertEqual(response.json()["data"]["count"], 1)
        self.assertEqual(mocked_list.call_args.kwargs["search"], "dem")
        self.assertEqual(str(mocked_list.call_args.kwargs["target_id"]), _ARTICOLO_UUID)

    # Scopo: POST nota articolo -> 200 e payload inoltrato al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch.object(PartitionedNoteService, "crea_nota", autospec=True)
    def test_post_articolo_nota_ok(self, mocked_create, _mock_auth):
        mocked_create.return_value = {"id": 5, "testo": "Demo"}

        response = self.client.post(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/note/",
            data=json.dumps({"testo": "Demo"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], 5)
        self.assertEqual(str(mocked_create.call_args.kwargs["target_id"]), _ARTICOLO_UUID)
        self.assertEqual(mocked_create.call_args.kwargs["payload"], {"testo": "Demo"})

    # Scopo: PATCH nota assente -> 404. Il dettaglio sta sotto il padre
    #        (`…/articoli/<id>/note/<note_id>/`): la rotta a parte
    #        `/catalogo/note/<id>/` e' ritirata il 2026-11-11.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch.object(PartitionedNoteService, "aggiorna_nota", autospec=True)
    def test_patch_nota_not_found(self, mocked_update, _mock_auth):
        from apps.core.services.service_errors import ServiceError

        mocked_update.side_effect = ServiceError(code="E_NOTA_NOT_FOUND", message="Nota non trovata.")

        response = self.client.patch(
            f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/note/999/",
            data=json.dumps({"testo": "Aggiornata"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "E_NOTA_NOT_FOUND")
        self.assertEqual(mocked_update.call_args.kwargs["note_id"], 999)
        self.assertEqual(self.client.patch("/api/v1/catalogo/note/999/", data="{}", content_type="application/json").status_code, 404)

    # Scopo: ⛔ un legame che non e' dell'articolo dell'URL e' un 404 su OGNI
    #        verbo delle sue note (cancello del padre di `make_note_views`), e
    #        il service delle note non parte (2026-10-21, §B8 di
    #        brief-be-verifica-documentazione-api; dal 2026-11-11 sul BB).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.catalogo.api.note_views.fn_verifica_componente_dell_articolo", autospec=True)
    @patch.object(PartitionedNoteService, "list_note", autospec=True)
    @patch.object(PartitionedNoteService, "crea_nota", autospec=True)
    @patch.object(PartitionedNoteService, "aggiorna_nota", autospec=True)
    @patch.object(PartitionedNoteService, "elimina_nota", autospec=True)
    def test_note_legame_di_un_altro_articolo_404(
        self, m_elimina, m_aggiorna, m_crea, m_list, mocked_cancello, _mock_auth,
    ):
        from apps.core.services.service_errors import ServiceError

        mocked_cancello.side_effect = ServiceError(
            code="E_CATALOGO_COMPONENTE_NOT_FOUND", message="Componente non trovato.",
        )
        base = f"/api/v1/catalogo/articoli/{_ARTICOLO_UUID}/componenti/{_COMPONENTE_UUID}/note/"
        for nome, chiama in (
            ("GET", lambda: self.client.get(base)),
            ("POST", lambda: self.client.post(base, data=json.dumps({"testo": "x"}), content_type="application/json")),
            ("PATCH", lambda: self.client.patch(f"{base}7/", data=json.dumps({"testo": "x"}), content_type="application/json")),
            ("DELETE", lambda: self.client.delete(f"{base}7/")),
        ):
            with self.subTest(nome):
                response = chiama()
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "E_CATALOGO_COMPONENTE_NOT_FOUND")
        for metodo in (m_list, m_crea, m_aggiorna, m_elimina):
            metodo.assert_not_called()

    # Scopo: `catalogo.note` e' una lista GLOBALE: le view delle sue note non
    #        hanno il cancello di perimetro (`perimetro_emittente=False`),
    #        quelle di vendita si'. La ricerca resta della lista della sede.
    def test_note_di_catalogo_senza_cancello_di_perimetro(self):
        from apps.catalogo.api.note_views import ApiArticoloNoteList, ApiComponenteNoteList
        from apps.catalogo.db.note_repositories import NOTE_REPO_ARTICOLO
        from apps.vendite.api.note_views import ApiPreventivoNoteList

        for vista in (ApiArticoloNoteList, ApiComponenteNoteList):
            with self.subTest(vista.__name__):
                self.assertIsNone(vista.lista_codice)
                self.assertIsNone(vista.lista_emittente_param)
        self.assertEqual(ApiPreventivoNoteList.lista_codice, "vendite.note")
        self.assertEqual(NOTE_REPO_ARTICOLO.lista_codice, "catalogo.note")


class NoteCatalogoSchemaTests(JwtMockedApiTest):
    # Scopo: ⛔ lo schema OpenAPI non promette cio' che il service rifiuta. Una
    #        nota di catalogo non ha righe (`supports_riga` falso): niente
    #        filtro ne' campo `target_riga_id`, che sarebbero sempre un 400.
    #        Le note di vendita li hanno (presidio del ramo opposto).
    def test_target_riga_id_solo_dove_ci_sono_righe(self):
        from drf_spectacular.generators import SchemaGenerator

        schema = SchemaGenerator().get_schema(request=None, public=True)
        percorsi = schema["paths"]

        def parametri(percorso: str) -> set[str]:
            return {p["name"] for p in percorsi[percorso]["get"].get("parameters", [])}

        def campi_post(percorso: str) -> set[str]:
            ref = percorsi[percorso]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            return set(schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"])

        catalogo = (
            "/api/v1/catalogo/articoli/{articolo_id}/note/",
            "/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/note/",
        )
        for percorso in catalogo:
            with self.subTest(percorso):
                self.assertNotIn("target_riga_id", parametri(percorso))
                self.assertNotIn("target_riga_id", campi_post(percorso))
        vendita = "/api/v1/vendite/preventivi/{preventivo_id}/note/"
        self.assertIn("target_riga_id", parametri(vendita))
        self.assertIn("target_riga_id", campi_post(vendita))
