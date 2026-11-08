# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   4. ristampa_richiede_jwt — 401 senza Authorization
#   5. ristampa_ok_stream_pdf_inline — 200 + bytes + header fedeltà a 1
#   6. ristampa_pdf_hash_diverso_header_a_zero — fedele nel contenuto, non nei byte
# ------------------------------------------------------------

from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"

# Patch path per il flusso documentale fatture. VenditeRepository e
# DocumentGenerationService sono importati nel modulo della view; la
# DocumentiRepository vive nel helper condiviso `contesto_helpers`.
_DOC_GEN_SVC = "apps.vendite.api.fatture_documenti_views.DocumentGenerationService"
_SORGENTI_REPO = "apps.documenti.api.contesto_helpers.SorgentiRepository"
_VEN_REPO = "apps.vendite.api.fatture_documenti_views.VenditeRepository"

_BASE = "/api/v1/vendite/fatture/"


class TestFattureDocumentiApi(JwtMockedApiTest):
    """Smoke test endpoint documenti FATTURA."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # 0. Senza JWT: 401.
    def test_genera_richiede_jwt(self) -> None:
        resp = self.client.post(f"{_BASE}42/documenti/genera/", data={})
        self.assertEqual(resp.status_code, 401)

    # 1. Genera OK: risolve contesto (entity + sorgente_tipo_id) e passa i
    #    parametri estratti dalla fattura a genera_documento.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO, autospec=True)
    @patch(_VEN_REPO, autospec=True)
    def test_genera_ok_passa_parametri(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 10, "codice": "FATTURA",
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
        # Giro D.1: la view passa l'id, la chiave della stampa la sceglie il DB.
        self.assertNotIn("sorgente_uid", kwargs)

    # 2. Lista documenti generati per la sorgente: 200 envelope paginato.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO, autospec=True)
    @patch(_VEN_REPO, autospec=True)
    def test_lista_ok_envelope(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 10, "codice": "FATTURA",
        }
        doc_svc_cls.return_value.list_documenti_per_sorgente.return_value = {
            "results": [], "total_count": 0,
        }

        resp = self.client.get(f"{_BASE}42/documenti/")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        # Envelope di lista standard (`paginated_envelope`, 2026-09-27).
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["results"], [])

    # 3. La rotta emetti/ NON esiste per FATTURA (nessuna emissione da UI):
    #    la factory è stata istanziata senza emetti_call → 404.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_emetti_route_assente(self, _auth) -> None:
        resp = self.client.post(f"{_BASE}42/emetti/", data={})
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------ #
    # Ristampa fedele (percorso 3) — brief-ristampa-fedele-documenti      #
    # ------------------------------------------------------------------ #

    # 4. Senza JWT: 401 (come tutti gli endpoint documentali).
    def test_ristampa_richiede_jwt(self) -> None:
        resp = self.client.get(f"{_BASE}42/documenti/100/ristampa/")
        self.assertEqual(resp.status_code, 401)

    # 5. Ristampa OK: stream PDF `inline` + verdetto di fedeltà nell'header.
    #    Sulla FATTURA è il percorso che conta di più: è un documento fiscale,
    #    e riemetterlo non è un'opzione.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO, autospec=True)
    @patch(_VEN_REPO, autospec=True)
    def test_ristampa_ok_stream_pdf_inline(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 10, "codice": "FATTURA",
        }
        doc_svc_cls.return_value.ristampa_fedele.return_value = {
            "pdf_bytes": b"%PDF-1.4 storico",
            "nome_file": "fattura-2025-1.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 16,
            "pdf_hash_match": True,
        }

        resp = self.client.get(f"{_BASE}42/documenti/100/ristampa/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"%PDF-1.4 storico")
        self.assertEqual(resp["Content-Type"], "application/pdf")
        # `inline`: è una consultazione, non un salvataggio (come l'anteprima).
        self.assertIn("inline", resp["Content-Disposition"])
        self.assertIn("fattura-2025-1.pdf", resp["Content-Disposition"])
        # Il verdetto di fedeltà viaggia in header perché il corpo è il PDF.
        self.assertEqual(resp["X-Ristampa-Pdf-Hash-Match"], "1")
        # Il documento_id arriva al service dal path.
        args = doc_svc_cls.return_value.ristampa_fedele.call_args.args
        self.assertEqual(args[1], 100)

    # 6. Byte diversi dall'originale (renderer non deterministico): NON è un
    #    errore — decisione §8.2 «fedele nel contenuto, non nei byte». Il PDF
    #    esce 200 e l'header lo DICHIARA, così la UI può avvisare.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO, autospec=True)
    @patch(_VEN_REPO, autospec=True)
    def test_ristampa_pdf_hash_diverso_header_a_zero(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ) -> None:
        repo_cls.return_value.get_fattura_for_documento_generation.return_value = {
            "id": 42,
            "uid": "0190b000-0000-0000-0000-000000000042",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 10, "codice": "FATTURA",
        }
        doc_svc_cls.return_value.ristampa_fedele.return_value = {
            "pdf_bytes": b"%PDF-1.4 storico",
            "nome_file": "fattura-2025-1.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 16,
            "pdf_hash_match": False,
        }

        resp = self.client.get(f"{_BASE}42/documenti/100/ristampa/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Ristampa-Pdf-Hash-Match"], "0")
