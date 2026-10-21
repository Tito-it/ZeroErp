# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints contratti v5 (F2-BE-06).
#        Mock service + JWT mockata. Nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_contratti_ok
 2) test_list_contratti_filters
 3) test_list_contratti_requires_jwt
 4) test_get_detail_ok
 5) test_post_create_ok
 6) test_post_create_validation_error
 7) test_post_create_overlap_409
 8) test_patch_update_ok
 9) test_patch_immutabile_rifiutato
10) test_post_cambia_stato_ok
11) test_post_cambia_stato_modalita_c_tradotto
12) test_post_emetti_ok — POST emetti (multipart) DRAFT->ATTIVO route OK
13) test_post_riga_ok
14) test_patch_riga_ok
15) test_delete_riga_ok
16) test_post_utility_ok
17) test_patch_utility_ok
18) test_post_documento_anteprima_ok
19) test_get_documenti_list_ok

TestEmissioneAllegatiContratto (refactor 2026-05-28):
20) test_emetti_integration_atomic_state_genera_allegati — POST emetti orchestra
    service.emetti + genera_documento(allegati=...) in transazione atomica
21) test_get_documento_allegati_list_ok — GET allegati: lista file (princ. + all.)
22) test_post_documento_allegati_upload_ok — POST allegati: append multipart
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_contratti.ContrattiService"
# ContrattiService importata anche da contratti_documenti_views per il flusso
# emissione (ApiContrattoEmetti.post). Patcha qui per i test integration.
_SVC_VIEW_DOC = "apps.vendite.api.contratti_documenti_views.ContrattiService"
_DOC_SVC = "apps.vendite.api.contratti_documenti_views.DocumentGenerationService"
# transaction.atomic patch path per la view emetti (refactor 2026-05-28):
# l'integration test non apre una vera transazione DB (SimpleTestCase).
_VIEW_ATOMIC = "apps.documenti.api.sorgente_documenti_views.transaction.atomic"
# DocumentiRepository ora vive solo nel helper condiviso `contesto_helpers`
# (refactor 2026-05-28): il patch deve puntare lì per mockare la risoluzione
# del sorgente_tipo. ContrattiRepository resta importato in
# contratti_documenti_views perche' fetcha il contratto prima del helper.
_SORGENTI_REPO = "apps.documenti.api.contesto_helpers.SorgentiRepository"
_CONTRATTI_REPO = "apps.vendite.api.contratti_documenti_views.ContrattiRepository"
_BASE = "/api/v1/vendite/contratti/"


class _BaseApiTest(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = ClientApi()


class TestList(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_contratti_ok(self, svc_cls, _auth):
        svc_cls.return_value.list_contratti.return_value = (
            [{"id": 1, "numero": "CNT0000001"}], 1,
        )
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["numero"], "CNT0000001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_contratti_filters(self, svc_cls, _auth):
        svc_cls.return_value.list_contratti.return_value = ([], 0)
        self.client.get(
            _BASE
            + "?billing_account_id=10&stato_doc_contratto_id=1&utility_id=3"
            + "&ambito=COMMODITY&listino_id=100&data_da=2025-01-01&data_a=2026-12-31"
            + "&search=CNT&order_by=numero&order_dir=asc&limit=10&offset=20"
        )
        kwargs = svc_cls.return_value.list_contratti.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 10)
        self.assertEqual(kwargs["stato_doc_contratto_id"], 1)
        self.assertEqual(kwargs["utility_id"], 3)
        self.assertEqual(kwargs["ambito"], "COMMODITY")
        self.assertEqual(kwargs["listino_id"], 100)
        self.assertEqual(str(kwargs["data_da"]), "2025-01-01")
        self.assertEqual(str(kwargs["data_a"]), "2026-12-31")
        self.assertEqual(kwargs["search"], "CNT")
        self.assertEqual(kwargs["order_by"], "numero")
        self.assertEqual(kwargs["order_dir"], "asc")
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 20)

    def test_list_contratti_requires_jwt(self):
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)


class TestDetailGet(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_detail_ok(self, svc_cls, _auth):
        svc_cls.return_value.get_contratto.return_value = {
            "id": 7,
            "numero": "CNT0000007",
            "righe": [],
            "utility": None,
        }
        resp = self.client.get(_BASE + "7/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)


class TestDocumentiContratto(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_CONTRATTI_REPO)
    def test_post_documento_anteprima_ok(self, repo_cls, sorgenti_repo_cls, svc_cls, _auth):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4,
            "codice": "CONTRATTO",
        }
        svc_cls.return_value.anteprima_documento.return_value = {
            "pdf_bytes": b"%PDF",
            "nome_file": "contratto-CNT0000007.pdf",
            "size_bytes": 4,
            "mime_type": "application/pdf",
        }

        resp = self.client.post(
            _BASE + "7/documenti/anteprima/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        kwargs = svc_cls.return_value.anteprima_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 4)
        self.assertEqual(kwargs["sorgente_id"], 7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_CONTRATTI_REPO)
    def test_get_documenti_list_ok(self, repo_cls, sorgenti_repo_cls, svc_cls, _auth):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4,
            "codice": "CONTRATTO",
        }
        svc_cls.return_value.list_documenti_per_sorgente.return_value = {
            "results": [{"id": 1, "nome_file": "contratto.pdf"}],
            "total_count": 1,
        }

        # Contratto di lista standard (lista `documenti.documenti_sorgente`,
        # 2026-09-27): `limit`/`offset` + ordinamento + ricerca, envelope
        # `paginated_envelope` con `count`.
        resp = self.client.get(
            _BASE + "7/documenti/?limit=10&offset=10&order_by=titolo&order_dir=asc&search=contr",
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 10)
        self.assertEqual(body["count"], 1)
        kwargs = svc_cls.return_value.list_documenti_per_sorgente.call_args.kwargs
        self.assertEqual(kwargs["sorgente_tipo_id"], 4)
        self.assertEqual(kwargs["sorgente_uid"], "0190b000-0000-0000-0000-000000000007")
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 10))
        self.assertEqual((kwargs["order_by"], kwargs["order_dir"]), ("titolo", "asc"))
        self.assertEqual(kwargs["search"], "contr")


class TestPost(_BaseApiTest):
    _OK = {
        "billing_account_id": 10,
        "istanza_utility_id": 20,
        "utility_id": 3,
        "valido_dal": "2026-01-01",
        "listino_id": 100,
        "tipo_variazione_globale": "PERCENTUALE",
        "valore_variazione_globale": "10",
    }

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.return_value = {
            "id": 1,
            "numero": "CNT0000001",
        }
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_validation_error(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.side_effect = ServiceError(
            code="E_VENDITE_VALIDATION",
            message="Payload contratto non valido.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps({"billing_account_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VENDITE_VALIDATION")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_overlap_409(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.side_effect = ServiceError(
            code="E_CONTRATTO_OVERLAP_ESISTENTE",
            message="Contratto sovrapposto.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "E_CONTRATTO_OVERLAP_ESISTENTE")


class TestPatch(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_update_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_contratto.return_value = {"id": 5, "ambito": "COMMERCIO"}
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"ambito": "COMMERCIO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.update_contratto.call_args.args[0], 5)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_immutabile_rifiutato(self, svc_cls, _auth):
        svc_cls.return_value.update_contratto.side_effect = ServiceError(
            code="E_VENDITE_VALIDATION",
            message="Identificativi contratto non modificabili.",
        )
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"numero": "CNT9999999"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VENDITE_VALIDATION")


class TestCambiaStato(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_cambia_stato_ok(self, svc_cls, _auth):
        svc_cls.return_value.cambia_stato.return_value = {"id": 1, "stato_codice": "ATTIVO"}
        resp = self.client.post(
            _BASE + "1/cambia-stato/",
            data=json.dumps({"codice_interno": "ATTIVO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = svc_cls.return_value.cambia_stato.call_args.kwargs
        self.assertEqual(kwargs["codice_interno"], "ATTIVO")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_cambia_stato_negoziato_puro_tradotto(self, svc_cls, _auth):
        # Refactor modalita 2026-05-15: il codice E_CONTRATTO_NEGOZIATO_PURO_
        # SENZA_RIGHE sostituisce il vecchio E_CONTRATTO_MODALITA_C_SENZA_RIGHE.
        svc_cls.return_value.cambia_stato.side_effect = ServiceError(
            code="E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE",
            message="Contratto senza listino senza AGGIUNTA.",
        )
        resp = self.client.post(
            _BASE + "1/cambia-stato/",
            data=json.dumps({"codice_interno": "ATTIVO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"],
            "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE",
        )

    # Smoke endpoint emissione (multipart). DRAFT->ATTIVO con genera doc +
    # allegati orchestrato atomicamente in ApiContrattoEmetti (refactor
    # 2026-05-28). Verifica route registrata: senza auth -> 401, ma la
    # route esiste (non 404). Pattern mirror di test_emetti_200 preventivi.
    def test_post_emetti_ok(self):
        resp = self.client.post(
            _BASE + "1/emetti/",
            data={},  # multipart vuoto: nessun allegato
        )
        self.assertIn(resp.status_code, [200, 401, 403])


class TestRighe(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_riga.return_value = {"id": 99, "prezzo_unitario": "25"}
        resp = self.client.post(
            _BASE + "1/righe/",
            data=json.dumps({
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "prezzo_unitario": "25",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.create_riga.call_args.args[0], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_riga.return_value = {"id": 99, "prezzo_unitario": "30"}
        resp = self.client.patch(
            _BASE + "1/righe/99/",
            data=json.dumps({"prezzo_unitario": "30"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        # ⛔ Il contratto dell'URL arriva al service: e' quello su cui il service
        #    verifica che la riga sia sua (prima la view lo scartava).
        self.assertEqual(svc_cls.return_value.update_riga.call_args.args[:2], (1, 99))

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_delete_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.delete_riga.return_value = None
        resp = self.client.delete(_BASE + "1/righe/99/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 99)
        svc_cls.return_value.delete_riga.assert_called_once_with(1, 99)


class TestUtility(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_utility_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_utility.return_value = {"id": 5, "tipo_utenza_id": 2}
        resp = self.client.post(
            _BASE + "1/utility/",
            data=json.dumps({"tipo_utenza_id": 2, "classe_utenza_id": 7}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.create_utility.call_args.args[0], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_utility_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_utility.return_value = {"id": 5}
        resp = self.client.patch(
            _BASE + "1/utility/",
            data=json.dumps({"param_2_txt": "abc"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)


class TestEmissioneAllegatiContratto(_BaseApiTest):
    """Test integration per il flusso emissione + endpoint allegati documento."""

    # Scopo: integration test ApiContrattoEmetti. Verifica che la view
    # orchestri service.emetti() + genera_documento(allegati=...) passando i
    # parametri estratti dal contratto + sorgente_tipo_id risolto.
    # Mock di transaction.atomic per non aprire una vera transazione DB.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_VIEW_ATOMIC)
    @patch(_DOC_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_CONTRATTI_REPO)
    @patch(_SVC_VIEW_DOC)
    def test_emetti_integration_atomic_state_genera_allegati(
        self, svc_cls, repo_cls, sorgenti_repo_cls, doc_svc_cls, _atomic, _auth,
    ):
        svc_cls.return_value.emetti.return_value = {
            "id": 7, "stato_codice": "ATTIVO",
        }
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4, "codice": "CONTRATTO",
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "contratto.pdf",
        }

        pdf_file = SimpleUploadedFile(
            "allegato.pdf", b"%PDF-1.4 fake", content_type="application/pdf",
        )
        resp = self.client.post(
            _BASE + "7/emetti/",
            data={"allegati": [pdf_file]},
        )

        self.assertEqual(resp.status_code, 200)
        # service.emetti chiamato una sola volta col contratto_id corretto
        svc_cls.return_value.emetti.assert_called_once_with(7)
        # genera_documento ricevuto i parametri estratti dal contratto +
        # l'allegato dal multipart
        kwargs = doc_svc_cls.return_value.genera_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 4)
        self.assertEqual(kwargs["sorgente_id"], 7)
        self.assertEqual(kwargs["sorgente_uid"], "0190b000-0000-0000-0000-000000000007")
        self.assertEqual(len(kwargs["allegati"]), 1)
        self.assertEqual(kwargs["allegati"][0]["mime_type"], "application/pdf")
        self.assertEqual(kwargs["allegati"][0]["file_name"], "allegato.pdf")

    # Scopo: GET allegati lista i file (principale + allegati) di un documento
    # esistente. Verifica route e delega a list_documento_files.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_CONTRATTI_REPO)
    def test_get_documento_allegati_list_ok(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4, "codice": "CONTRATTO",
        }
        doc_svc_cls.return_value.list_documento_files.return_value = {
            "files": [
                {"id": 1, "is_principale": True, "file_name": "contratto.pdf"},
                {"id": 2, "is_principale": False, "file_name": "allegato.pdf"},
            ],
        }

        resp = self.client.get(_BASE + "7/documenti/100/allegati/")

        self.assertEqual(resp.status_code, 200)
        doc_svc_cls.return_value.list_documento_files.assert_called_once()
        args = doc_svc_cls.return_value.list_documento_files.call_args.args
        # args = (user, documento_id)
        self.assertEqual(args[1], 100)

    # Scopo: POST allegati su documento esistente (modalita' append) — utile
    # post-attivazione per aggiungere file. Estrae multipart e delega a
    # aggiungi_allegati.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_CONTRATTI_REPO)
    def test_post_documento_allegati_upload_ok(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4, "codice": "CONTRATTO",
        }
        doc_svc_cls.return_value.aggiungi_allegati.return_value = {
            "allegati": [{"id": 200, "file_name": "extra.pdf"}],
        }

        pdf_file = SimpleUploadedFile(
            "extra.pdf", b"%PDF-1.4 extra", content_type="application/pdf",
        )
        resp = self.client.post(
            _BASE + "7/documenti/100/allegati/",
            data={"allegati": [pdf_file]},
        )

        self.assertEqual(resp.status_code, 200)
        doc_svc_cls.return_value.aggiungi_allegati.assert_called_once()
        args = doc_svc_cls.return_value.aggiungi_allegati.call_args.args
        # args = (user, documento_id, allegati_list)
        self.assertEqual(args[1], 100)
        self.assertEqual(len(args[2]), 1)
        self.assertEqual(args[2][0]["mime_type"], "application/pdf")
        self.assertEqual(args[2][0]["file_name"], "extra.pdf")
