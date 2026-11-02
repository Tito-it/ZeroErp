# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test API documenti read-only. Mocka JWT auth +
#        TemplateService per verificare il routing, l'envelope
#        success_response, l'envelope paginato e la propagazione
#        dei query params al service.
#
# Indice test (0..N):
#   0. list_templates_requires_jwt
#   1. list_templates_ok_envelope_paginated
#   2. list_templates_propagates_filters_to_service
#   3. detail_template_ok
#   4. detail_template_404_when_service_raises_not_found
#   5. versioni_list_ok (envelope standard + parametri di lista)
#   5-bis. versioni_list_senza_ordine_lascia_decidere_il_repository
#   6. versione_detail_ok
#   7. post_template_201_happy_path
#   8. post_template_validation_error_400
#   9. post_template_requires_jwt
#  10. patch_template_200_happy_path
#  11. patch_template_404_when_service_raises_not_found
#  12. post_versione_201_happy_path
#  13. patch_versione_blocked_409_pubblicata
#  14. delete_versione_200_happy_path
#  15. clona_versione_200_happy_path
#  16. pubblica_versione_200_happy_path
#  16-bis. personalizza_template_routing_e_payload
#  17. asset_list_requires_jwt
#  18. asset_list_ok_envelope_paginated
#  19. asset_upload_requires_file_field
#  20. asset_upload_happy_path_multipart
#  21. asset_patch_metadati_happy_path
#  22. asset_download_file_binary_happy_path
#  22-bis. asset_miniatura_inline_con_etag_e_no_cache
#  22-ter. asset_miniatura_304_quando_il_client_ha_lo_stesso_etag
#  23. le liste nei drawer dichiarano codice e parametro dell'emittente
#  24. context_builders_requires_jwt
#  25. context_builders_legge_il_registro_nell_envelope_results
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_TEMPLATE_DETAIL = {
    "id": 1,
    "codice": "TPL-PREV-001",
    "codice_interno": "TPL_PREV_001",
    "descrizione": "Template preventivo standard",
    "is_default": True,
    "attivo": True,
    "tipo_documento_output_id": 1,
    "tipo_documento_output_codice": "PDF_FINALE",
    "tipo_documento_output_descrizione": "PDF finale",
    "sorgente_tipo_id": 10,
    "sorgente_tipo_codice": "PREVENTIVO",
    "sorgente_tipo_descrizione": "Preventivo vendita",
    "context_builder_code": "PREVENTIVO",
    "file_name_pattern": "preventivo-{numero}.pdf",
    "emittente_fiscale_id": 5,
    "emittente_fiscale_codice": "EF-001",
    "emittente_ragione_sociale": "Acme SRL",
    "data_insert": "2026-04-29T00:00:00+02:00",
    "data_update": "2026-04-29T00:00:00+02:00",
}

_VERSIONE_DETAIL = {
    "id": 11,
    "template_documento_id": 1,
    "versione": 1,
    "stato": "PUBBLICATA",
    "titolo": "v1 standard",
    "formato_template": "HTML",
    "render_engine_id": 1,
    "render_engine_codice": "WEASYPRINT",
    "render_engine_descrizione": "WeasyPrint",
    "page_format": "A4",
    "page_orientation": "PORTRAIT",
    "valido_dal": "2026-05-01",
    "valido_al": None,
    "attivo": True,
    "html_template": "<html><body>{{ numero }}</body></html>",
    "css_template": None,
    "markdown_template": None,
}


class DocumentiApiSmokeTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # 24. JWT assente -> 401.
    def test_context_builders_requires_jwt(self) -> None:
        resp = self.client.get("/api/v1/documenti/context-builders/")
        self.assertEqual(resp.status_code, 401)

    # 25. ⭐ La tendina del template legge il REGISTRO, nell'envelope
    #     `{"results": [...]}` dei lookup (api.md: una lista nuda e' una
    #     schermata bianca senza errori). Il registro e' quello vero: le app
    #     registrano i builder al `ready()`.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    def test_context_builders_legge_il_registro_nell_envelope_results(
        self, _mock_auth
    ) -> None:
        from apps.documenti.services.context_builders.registry import (
            builder_registrati,
        )

        resp = self.client.get("/api/v1/documenti/context-builders/")

        self.assertEqual(resp.status_code, 200)
        results = resp.json()["data"]["results"]
        self.assertEqual(results, builder_registrati())
        codici = [r["codice"] for r in results]
        self.assertIn("FATTURA", codici)
        self.assertEqual(codici, sorted(codici))
        for r in results:
            self.assertIsInstance(r["versione_contesto"], int)

    # 0. JWT assente -> 401.
    def test_list_templates_requires_jwt(self) -> None:
        resp = self.client.get("/api/v1/documenti/templates/")
        self.assertEqual(resp.status_code, 401)

    # 1. lista OK con envelope paginato.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_list_templates_ok_envelope_paginated(
        self, mocked_service_cls, _mock_auth
    ) -> None:
        instance = mocked_service_cls.return_value
        instance.list_templates.return_value = {
            "results": [_TEMPLATE_DETAIL],
            "total_count": 1,
        }

        resp = self.client.get("/api/v1/documenti/templates/")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codice"], "TPL-PREV-001")

    # 2. query params filtri propagati al service.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_list_templates_propagates_filters_to_service(
        self, mocked_service_cls, _mock_auth
    ) -> None:
        instance = mocked_service_cls.return_value
        instance.list_templates.return_value = {"results": [], "total_count": 0}

        self.client.get(
            "/api/v1/documenti/templates/"
            "?attivo=true&tipo_documento_output_id=1&sorgente_tipo_id=10"
            "&emittente_fiscale_id=5&search=preventivo"
        )

        kwargs = instance.list_templates.call_args.kwargs
        self.assertEqual(kwargs["attivo"], True)
        self.assertEqual(kwargs["tipo_documento_output_id"], 1)
        self.assertEqual(kwargs["sorgente_tipo_id"], 10)
        self.assertEqual(kwargs["emittente_fiscale_id"], 5)
        self.assertEqual(kwargs["search"], "preventivo")

    # 3. dettaglio OK.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_detail_template_ok(self, mocked_service_cls, _mock_auth) -> None:
        mocked_service_cls.return_value.get_template.return_value = _TEMPLATE_DETAIL
        resp = self.client.get("/api/v1/documenti/templates/1/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["codice"], "TPL-PREV-001")

    # 4. dettaglio 404: ServiceError E_DOCUMENTI_NOT_FOUND -> 404 envelope errore.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_detail_template_404_when_service_raises_not_found(
        self, mocked_service_cls, _mock_auth
    ) -> None:
        mocked_service_cls.return_value.get_template.side_effect = ServiceError(
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
        )
        resp = self.client.get("/api/v1/documenti/templates/999/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_DOCUMENTI_NOT_FOUND")

    # 5. lista versioni OK.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_versioni_list_ok(self, mocked_service_cls, _mock_auth) -> None:
        mocked_service_cls.return_value.list_versioni.return_value = {
            "results": [_VERSIONE_DETAIL],
            "total_count": 1,
        }
        resp = self.client.get(
            "/api/v1/documenti/templates/1/versioni/"
            "?limit=10&offset=10&order_by=valido_al&order_dir=desc&search=fattura",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        results = data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["stato"], "PUBBLICATA")
        # Envelope di lista standard (`paginated_envelope`): `count`, non
        # `total_count` — e' cio' che legge lo store del frontend.
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 10)
        kwargs = mocked_service_cls.return_value.list_versioni.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "valido_al")
        self.assertEqual(kwargs["order_dir"], "desc")
        self.assertEqual(kwargs["search"], "fattura")
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 10))

    # 5-bis. senza `order_by` decide il repository (`versione DESC`): la view
    #        non inventa una chiave che arriverebbe senza verso.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_versioni_list_senza_ordine_lascia_decidere_il_repository(
        self, mocked_service_cls, _mock_auth,
    ) -> None:
        mocked_service_cls.return_value.list_versioni.return_value = {
            "results": [], "total_count": 0,
        }
        resp = self.client.get("/api/v1/documenti/templates/1/versioni/")
        self.assertEqual(resp.status_code, 200)
        kwargs = mocked_service_cls.return_value.list_versioni.call_args.kwargs
        self.assertFalse(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])

    # 6. dettaglio versione (incluso payload html).
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_versione_detail_ok(self, mocked_service_cls, _mock_auth) -> None:
        mocked_service_cls.return_value.get_versione.return_value = _VERSIONE_DETAIL
        resp = self.client.get("/api/v1/documenti/templates/1/versioni/11/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["versione"], 1)
        self.assertIn("{{ numero }}", data["html_template"])


class DocumentiApiWriteTests(JwtMockedApiTest):
    """Smoke test write endpoint (POST template, PATCH template) — Tranche E."""

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _CREATE_PAYLOAD = {
        "tipo_documento_output_id": 1,
        "sorgente_tipo_id": 10,
        "emittente_fiscale_id": 11,
        "codice": "TPL-PREV-001",
        "codice_interno": "TPL_PREV_001",
        "descrizione": "Template preventivo standard",
        "context_builder_code": "PREVENTIVO",
        "file_name_pattern": "preventivo-{numero}.pdf",
        "is_default": True,
    }

    # 7. POST happy path: 200 (handle_post_json ritorna 200, non 201) +
    #    body via service.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAdminService")
    def test_post_template_happy_path(self, mocked_admin_cls, _mock_auth) -> None:
        mocked_admin_cls.return_value.create_template.return_value = {
            "id": 42,
            "codice": "TPL-PREV-001",
        }
        resp = self.client.post(
            "/api/v1/documenti/templates/",
            headers={"Idempotency-Key": "doc-312"},
            data=self._CREATE_PAYLOAD,
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["data"]["id"], 42)
        # service ricevuto user + payload.
        mocked_admin_cls.return_value.create_template.assert_called_once()
        args = mocked_admin_cls.return_value.create_template.call_args.args
        self.assertEqual(args[1]["codice"], "TPL-PREV-001")

    # 8. POST validation error: ServiceError -> 400 envelope errore.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAdminService")
    def test_post_template_validation_error_400(self, mocked_admin_cls, _mock_auth) -> None:
        mocked_admin_cls.return_value.create_template.side_effect = ServiceError(
            code="E_DOCUMENTI_VALIDATION",
            message="Esiste gia' un template con questo codice per emittente e sorgente.",
        )
        resp = self.client.post(
            "/api/v1/documenti/templates/",
            headers={"Idempotency-Key": "doc-335"},
            data=self._CREATE_PAYLOAD,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_DOCUMENTI_VALIDATION")

    # 9. POST senza JWT -> 401.
    def test_post_template_requires_jwt(self) -> None:
        resp = self.client.post(
            "/api/v1/documenti/templates/",
            headers={"Idempotency-Key": "doc-345"},
            data=self._CREATE_PAYLOAD,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    # 10. PATCH happy path.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAdminService")
    def test_patch_template_happy_path(self, mocked_admin_cls, _mock_auth) -> None:
        mocked_admin_cls.return_value.update_template.return_value = {
            "id": 42,
            "descrizione": "Aggiornata",
        }
        resp = self.client.patch(
            "/api/v1/documenti/templates/42/",
            data={"descrizione": "Aggiornata"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["descrizione"], "Aggiornata")
        mocked_admin_cls.return_value.update_template.assert_called_once()

    # 11. PATCH 404 da service.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAdminService")
    def test_patch_template_404_when_service_raises_not_found(
        self, mocked_admin_cls, _mock_auth
    ) -> None:
        mocked_admin_cls.return_value.update_template.side_effect = ServiceError(
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
        )
        resp = self.client.patch(
            "/api/v1/documenti/templates/999/",
            data={"descrizione": "x"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_DOCUMENTI_NOT_FOUND")


class DocumentiApiVersioniWriteTests(JwtMockedApiTest):
    """Smoke test write versioni (POST/PATCH/DELETE/clona/pubblica) — Tranche F."""

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _CREATE_VERSIONE_PAYLOAD = {
        "titolo": "v1 standard",
        "html_template": "<html><body>{{ numero }}</body></html>",
        "render_engine_id": 1,
    }

    # 12. POST versione happy path.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateVersioniAdminService")
    def test_post_versione_happy_path(self, mocked_svc_cls, _mock_auth) -> None:
        mocked_svc_cls.return_value.create_versione.return_value = {
            "id": 50, "versione": 5, "stato": "BOZZA",
        }
        resp = self.client.post(
            "/api/v1/documenti/templates/1/versioni/",
            headers={"Idempotency-Key": "doc-418"},
            data=self._CREATE_VERSIONE_PAYLOAD,
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["data"]["versione"], 5)
        self.assertEqual(resp.json()["data"]["stato"], "BOZZA")

    # 13. PATCH versione PUBBLICATA -> 409 (mappato dall'error policy).
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateVersioniAdminService")
    def test_patch_versione_blocked_409_pubblicata(
        self, mocked_svc_cls, _mock_auth
    ) -> None:
        mocked_svc_cls.return_value.update_versione.side_effect = ServiceError(
            code="E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE",
            message="Versione PUBBLICATA non modificabile.",
        )
        resp = self.client.patch(
            "/api/v1/documenti/templates/1/versioni/11/",
            data={"titolo": "Nuovo"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(
            resp.json()["error"]["code"], "E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE"
        )

    # 14. DELETE versione BOZZA OK.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateVersioniAdminService")
    def test_delete_versione_happy_path(self, mocked_svc_cls, _mock_auth) -> None:
        mocked_svc_cls.return_value.delete_versione.return_value = None
        resp = self.client.delete("/api/v1/documenti/templates/1/versioni/11/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])

    # 15. POST clona versione.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateVersioniAdminService")
    def test_clona_versione_happy_path(self, mocked_svc_cls, _mock_auth) -> None:
        mocked_svc_cls.return_value.clone_versione.return_value = {
            "id": 70, "versione": 7, "stato": "BOZZA",
        }
        resp = self.client.post(
            "/api/v1/documenti/templates/1/versioni/11/clona/",
            headers={"Idempotency-Key": "doc-472"},
            data={"titolo": "Clone v7"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["data"]["versione"], 7)

    # 16. POST pubblica versione.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateVersioniAdminService")
    def test_pubblica_versione_happy_path(self, mocked_svc_cls, _mock_auth) -> None:
        mocked_svc_cls.return_value.pubblica_versione.return_value = {
            "id": 11, "versione": 1, "stato": "PUBBLICATA",
            "valido_dal": "2026-06-01", "valido_al": None,
        }
        resp = self.client.post(
            "/api/v1/documenti/templates/1/versioni/11/pubblica/",
            headers={"Idempotency-Key": "doc-491"},
            data={"valido_dal": "2026-06-01"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["data"]["stato"], "PUBBLICATA")

    # 16-bis. POST personalizza: il verbo sul modello standard arriva al
    #         service con l'id del path e il corpo.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAdminService")
    def test_personalizza_template_routing_e_payload(self, mocked_svc_cls, _mock_auth) -> None:
        mocked_svc_cls.return_value.personalizza_template.return_value = {
            "id": 900, "standard": False, "emittente_fiscale_id": 11,
        }
        resp = self.client.post(
            "/api/v1/documenti/templates/2728/personalizza/",
            headers={"Idempotency-Key": "doc-510"},
            data={"emittente_fiscale_id": 11},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["data"]["id"], 900)
        args = mocked_svc_cls.return_value.personalizza_template.call_args.args
        self.assertEqual(args[1:], (2728, {"emittente_fiscale_id": 11}))


class DocumentiAssetApiTests(JwtMockedApiTest):
    """Smoke test asset endpoint (Tranche G)."""

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _ASSET_DETAIL = {
        "id": 50,
        "codice": "LOGO-ACME",
        "codice_interno": "LOGO_ACME",
        "descrizione": "Logo Acme SRL",
        "asset_tipo_id": 1,
        "asset_tipo_codice": "LOGO",
        "asset_tipo_descrizione": "Logo",
        "mime_type": "image/png",
        "file_name": "logo.png",
        "file_size_bytes": 9,
        "storage_key": "assets/5/abcd1234.png",
        "sha256": "a" * 64,
        "emittente_fiscale_id": 5,
        "emittente_fiscale_codice": "EF-001",
        "emittente_ragione_sociale": "Acme SRL",
        "valido_dal": "2026-05-01",
        "valido_al": None,
        "attivo": True,
        "data_insert": "2026-05-04T00:00:00+02:00",
        "data_update": "2026-05-04T00:00:00+02:00",
    }

    # 17. JWT mancante -> 401.
    def test_asset_list_requires_jwt(self) -> None:
        resp = self.client.get("/api/v1/documenti/asset/")
        self.assertEqual(resp.status_code, 401)

    # 18. lista asset paginata.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_asset_list_ok_envelope_paginated(
        self, mocked_reader_cls, _mock_auth
    ) -> None:
        mocked_reader_cls.return_value.list_asset.return_value = {
            "results": [self._ASSET_DETAIL],
            "total_count": 1,
        }
        resp = self.client.get("/api/v1/documenti/asset/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["sha256"], "a" * 64)

    # 19. upload senza campo `file` -> 400.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    def test_asset_upload_requires_file_field(self, _mock_auth) -> None:
        resp = self.client.post(
            "/api/v1/documenti/asset/",
            headers={"Idempotency-Key": "doc-582"},
            data={
                "codice": "LOGO",
                "codice_interno": "LOGO_X",
                "descrizione": "x",
                "asset_tipo_id": "1",
                "emittente_fiscale_id": "5",
            },
            # multipart automatico (no content_type)
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_DOCUMENTI_VALIDATION")

    # 20. upload happy path con file + metadati multipart.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAssetAdminService")
    def test_asset_upload_happy_path_multipart(
        self, mocked_admin_cls, _mock_auth
    ) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        mocked_admin_cls.return_value.upload_asset.return_value = self._ASSET_DETAIL

        uploaded = SimpleUploadedFile(
            "logo.png", b"FAKEBYTES", content_type="image/png"
        )
        resp = self.client.post(
            "/api/v1/documenti/asset/",
            headers={"Idempotency-Key": "doc-612"},
            data={
                "file": uploaded,
                "codice": "LOGO-ACME",
                "codice_interno": "LOGO_ACME",
                "descrizione": "Logo Acme SRL",
                "asset_tipo_id": "1",
                "emittente_fiscale_id": "5",
                "attivo": "true",
            },
            # multipart automatico
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["codice"], "LOGO-ACME")
        # service ricevuto: file_bytes + client_mime_type + client_file_name + metadati.
        kwargs = mocked_admin_cls.return_value.upload_asset.call_args.kwargs
        self.assertEqual(kwargs["file_bytes"], b"FAKEBYTES")
        self.assertEqual(kwargs["client_mime_type"], "image/png")
        self.assertEqual(kwargs["client_file_name"], "logo.png")
        self.assertEqual(kwargs["metadati"]["asset_tipo_id"], 1)
        self.assertEqual(kwargs["metadati"]["emittente_fiscale_id"], 5)
        self.assertEqual(kwargs["metadati"]["attivo"], True)

    # 20-bis. il flag `attivo` del multipart passa dal BB dei booleani del
    #         trasporto (A6): fuori vocabolario e' un 400 col campo, e il
    #         service non parte. Fino al 2026-10-21 «si» valeva false in
    #         silenzio, e l'asset nasceva spento.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAssetAdminService")
    def test_asset_upload_attivo_fuori_vocabolario_400(
        self, mocked_admin_cls, _mock_auth
    ) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        resp = self.client.post(
            "/api/v1/documenti/asset/",
            headers={"Idempotency-Key": "doc-attivo-si"},
            data={
                "file": SimpleUploadedFile("logo.png", b"X", content_type="image/png"),
                "codice": "LOGO", "codice_interno": "LOGO", "descrizione": "x",
                "asset_tipo_id": "1", "emittente_fiscale_id": "5",
                "attivo": "si",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        mocked_admin_cls.return_value.upload_asset.assert_not_called()

    # 21. PATCH metadati asset.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateAssetAdminService")
    def test_asset_patch_metadati_happy_path(
        self, mocked_admin_cls, _mock_auth
    ) -> None:
        mocked_admin_cls.return_value.update_asset_metadati.return_value = {
            **self._ASSET_DETAIL, "descrizione": "Aggiornato",
        }
        resp = self.client.patch(
            "/api/v1/documenti/asset/50/",
            data={"descrizione": "Aggiornato"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["descrizione"], "Aggiornato")

    # 22. Download binario asset: niente envelope JSON, header attachment.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_asset_download_file_binary_happy_path(
        self, mocked_reader_cls, _mock_auth
    ) -> None:
        mocked_reader_cls.return_value.download_asset.return_value = {
            "asset_id": 50,
            "file_bytes": b"FAKEBYTES",
            "file_name": "logo.png",
            "mime_type": "image/png",
            "size_bytes": 9,
        }

        resp = self.client.get("/api/v1/documenti/asset/50/file/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"FAKEBYTES")
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertIn('attachment; filename="logo.png"', resp["Content-Disposition"])
        self.assertEqual(resp["Content-Length"], "9")
        mocked_reader_cls.return_value.download_asset.assert_called_once()

    # 22-bis. Miniatura: inline (niente attachment), ETag e `private,
    #         no-cache` — il browser la riusa ma la rivalida sempre, cosi'
    #         lo scope si ricontrolla a ogni richiesta.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_asset_miniatura_inline_con_etag_e_no_cache(
        self, mocked_reader_cls, _mock_auth
    ) -> None:
        mocked_reader_cls.return_value.miniatura_asset.return_value = {
            "etag": '"abc-128"', "file_bytes": b"PNGMINI", "mime_type": "image/png",
        }

        resp = self.client.get("/api/v1/documenti/asset/50/miniatura/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"PNGMINI")
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertEqual(resp["ETag"], '"abc-128"')
        self.assertEqual(resp["Cache-Control"], "private, no-cache")
        self.assertNotIn("Content-Disposition", resp)
        _, kwargs = mocked_reader_cls.return_value.miniatura_asset.call_args
        self.assertEqual(kwargs["etag_noti"], [])

    # 22-ter. Il client porta l'ETag che ha in cache: la view lo passa al
    #         service (che controlla lo scope PRIMA) e risponde 304 vuoto.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(is_superuser=True), None),
    )
    @patch("apps.documenti.api.views.TemplateService")
    def test_asset_miniatura_304_quando_il_client_ha_lo_stesso_etag(
        self, mocked_reader_cls, _mock_auth
    ) -> None:
        mocked_reader_cls.return_value.miniatura_asset.return_value = {
            "etag": '"abc-128"', "file_bytes": None, "mime_type": None,
        }

        resp = self.client.get(
            "/api/v1/documenti/asset/50/miniatura/",
            HTTP_IF_NONE_MATCH='"abc-128"',
        )

        self.assertEqual(resp.status_code, 304)
        self.assertEqual(resp.content, b"")
        self.assertEqual(resp["ETag"], '"abc-128"')
        _, kwargs = mocked_reader_cls.return_value.miniatura_asset.call_args
        self.assertEqual(kwargs["etag_noti"], ['"abc-128"'])


class ListeNeiDrawerDichiaranoIlCancelloTests(SimpleTestCase):
    """Le due liste che si aprono DENTRO un documento (brief-db-liste-
    datatable-grezze righe 2 e 6) dichiarano il codice di catalogo e il
    parametro con cui ricevono l'emittente gia' fissato.

    ⚠️ Senza `lista_emittente_param` il cancello di perimetro rifiuterebbe
    (422) il super admin su «Tutti» dentro un drawer gia' aperto: le due liste
    a catalogo NON sono certificate multi-emittente.
    """

    # 23. la lista delle versioni e le SEI liste documenti della factory.
    def test_liste_nei_drawer_dichiarano_codice_e_parametro(self) -> None:
        from apps.documenti.api.views import ApiTemplateVersioniList
        from apps.vendite.api import (
            contratti_documenti_views,
            ddt_documenti_views,
            fatture_documenti_views,
            offerte_documenti_views,
            ordini_documenti_views,
            preventivi_documenti_views,
        )

        self.assertEqual(ApiTemplateVersioniList.lista_codice, "documenti.template_versioni")
        self.assertEqual(ApiTemplateVersioniList.lista_emittente_param, "emittente_fiscale_id")
        # ⭐ Una sola lista per gli otto domini: il codice lo scrive la
        #    factory, non il dominio (vedi `build_documenti_sorgente_views`).
        for view in (
            contratti_documenti_views.ApiContrattoDocumentiList,
            ddt_documenti_views.ApiDdtDocumentiList,
            fatture_documenti_views.ApiFatturaDocumentiList,
            offerte_documenti_views.ApiOffertaDocumentiList,
            ordini_documenti_views.ApiOrdineDocumentiList,
            preventivi_documenti_views.ApiPreventivoDocumentiList,
        ):
            with self.subTest(view=view.__qualname__):
                self.assertEqual(view.lista_codice, "documenti.documenti_sorgente")
                self.assertEqual(view.lista_emittente_param, "emittente_fiscale_id")
                self.assertTrue(view.is_search_endpoint)
