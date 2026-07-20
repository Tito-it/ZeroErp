# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint documenti FATTURA (stampa/ristampa PDF),
#        motore `documenti`, sorgente FATTURA. Mock del layer DB/service
#        (nessun accesso DB, CI-compatible). Verifica auth, envelope, routing,
#        parametri passati a genera_documento, e che NON esista rotta emetti/
#        (la fattura non si emette da UI: la factory è istanziata senza emetti).
#
# Indice test (0..N):
#   0. genera_richiede_jwt — 401 senza Authorization
#   1. genera_ok_passa_parametri — 201 + kwargs corretti a genera_documento
#   2. lista_ok_envelope — 200 lista documenti generati per sorgente
#   3. emetti_route_assente — POST emetti/ → 404 (nessuna emissione FATTURA)
# ------------------------------------------------------------

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"

# Patch path per il flusso documentale fatture. VenditeRepository e
# DocumentGenerationService sono importati nel modulo della view; la
# DocumentiRepository vive nel helper condiviso `contesto_helpers`.
_DOC_GEN_SVC = "apps.vendite.api.fatture_documenti_views.DocumentGenerationService"
_DOC_REPO = "apps.documenti.api.contesto_helpers.DocumentiRepository"
_VEN_REPO = "apps.vendite.api.fatture_documenti_views.VenditeRepository"

_BASE = "/api/v1/vendite/fatture/"


class TestFattureDocumentiApi(JwtMockedApiTest):
    """Smoke test endpoint documenti FATTURA."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Patch request_log middleware: SimpleTestCase non ammette DB queries.
        self._req_log_patcher = patch(
            "apps.core.middleware.request_log_middleware.RequestLogMiddleware._insert_log",
            return_value=None,
        )
        self._req_log_patcher.start()
        self.addCleanup(self._req_log_patcher.stop)

    # 0. Senza JWT: 401.
    def test_genera_richiede_jwt(self) -> None:
        resp = self.client.post(f"{_BASE}42/documenti/genera/", data={})
        self.assertEqual(resp.status_code, 401)

    # 1. Genera OK: risolve contesto (entity + sorgente_tipo_id) e passa i
    #    parametri estratti dalla fattura a genera_documento.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_DOC_REPO)
    @patch(_VEN_REPO)
    def test_genera_ok_passa_parametri(
        self, repo_cls, doc_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        doc_repo_cls.return_value.get_sorgente_tipo_id_by_codice.return_value = {
            "id": 10, "codice": "FATTURA", "attivo": True,
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "fattura.pdf",
        }

        resp = self.client.post(
            f"{_BASE}42/documenti/genera/",
            data={}, content_type="application/json",
        )

        # handle_post_json ritorna 200 (l'@extend_schema dichiara 201 solo a
        # fini OpenAPI: mismatch doc/impl condiviso da tutti i domini factory).
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["nome_file"], "fattura.pdf")
        kwargs = doc_svc_cls.return_value.genera_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 10)
        self.assertEqual(kwargs["sorgente_id"], 42)
        self.assertEqual(
            kwargs["sorgente_uid"], "0190b000-0000-0000-0000-000000000042",
        )

    # 2. Lista documenti generati per la sorgente: 200 envelope paginato.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_DOC_REPO)
    @patch(_VEN_REPO)
    def test_lista_ok_envelope(
        self, repo_cls, doc_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        doc_repo_cls.return_value.get_sorgente_tipo_id_by_codice.return_value = {
            "id": 10, "codice": "FATTURA", "attivo": True,
        }
        doc_svc_cls.return_value.list_documenti_per_sorgente.return_value = {
            "items": [], "total": 0,
        }

        resp = self.client.get(f"{_BASE}42/documenti/")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["total"], 0)

    # 3. La rotta emetti/ NON esiste per FATTURA (nessuna emissione da UI):
    #    la factory è stata istanziata senza emetti_call → 404.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_emetti_route_assente(self, _auth) -> None:
        resp = self.client.post(f"{_BASE}42/emetti/", data={})
        self.assertEqual(resp.status_code, 404)
