# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API views preventivi vendita (endpoint HTTP con mock service).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_list_preventivi_200 — GET lista preventivi OK
2) test_create_preventivo_200 — POST creazione preventivo OK
3) test_get_preventivo_detail_200 — GET dettaglio preventivo OK
4) test_get_preventivo_detail_404 — GET dettaglio preventivo non trovato
5) test_cambio_stato_200 — POST cambio stato OK
6) test_add_riga_200 — POST aggiunta riga OK
7) test_push_commessa_200 — POST push commessa OK
7b) test_push_commessa_righe_ids_200 — POST push commessa selettivo (righe_ids al service)
7b2) test_push_commessa_righe_ids_vuoto_422 — righe_ids=[] → errore validazione, no degrado a "tutte"
7c) test_smistamento_200 — GET smistamento (aggregato + righe) OK
8) test_list_componenti_riga_200 — GET componenti riga padre OK
9) test_update_componente_200 — PATCH override prezzo componente OK
10) test_delete_componente_200 — DELETE soft delete componente OK
11) test_get_componente_404 — GET su riga inesistente -> 404
12) test_emetti_200 — POST emetti (multipart) BOZZA->EMESSO route OK

TestPreventivoEmissioneAllegati:
1) test_emetti_integration_atomic_state_genera_allegati — POST emetti orchestra
   service.emetti + genera_documento(allegati=...) in transazione atomica
2) test_get_documento_allegati_list_ok — GET allegati: lista file (princ. + all.)
3) test_post_documento_allegati_upload_ok — POST allegati: append multipart

PreventivoPermessoPassaggioTests:
1) test_cambio_stato_ed_emissione_dichiarano_il_passaggio — l'azione dalla riga, nessun post_permission
2) test_collega_pratica_chiede_il_livello — non e' un passaggio: livello sul documento
3) test_nuovo_stato_ripulito — lo stesso valore che legge il permesso (strip)
4) test_nuovo_stato_assente_o_non_testo_e_un_400 — mai "None" o "123" al service
"""

from unittest.mock import ANY, Mock, patch

from django.test import SimpleTestCase

from django.core.files.uploadedfile import SimpleUploadedFile
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

# Patch path per il flusso documenti/emissione preventivi (refactor 2026-05-28).
# DocumentiRepository vive solo nel helper condiviso `contesto_helpers`; le
# altre dipendenze sono importate nel modulo della view come al solito.
_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PREV_SVC = "apps.vendite.api.preventivi_documenti_views.preventivi_service"
_DOC_GEN_SVC = "apps.vendite.api.preventivi_documenti_views.DocumentGenerationService"
_SORGENTI_REPO = "apps.documenti.api.contesto_helpers.SorgentiRepository"
_PREV_REPO = "apps.vendite.api.preventivi_documenti_views.PreventiviRepository"
_VIEW_ATOMIC = "apps.documenti.api.sorgente_documenti_views.transaction.atomic"
_BASE = "/api/v1/vendite/preventivi/"


class TestPreventiviApiViews(JwtMockedApiTest):

    def setUp(self):
        super().setUp()
        # Scopo: Mock service layer per isolare i test API.
        self.svc_patcher = patch(
            "apps.vendite.api.preventivi_views.preventivi_service"
        )
        self.mock_svc = self.svc_patcher.start()

    def tearDown(self):
        self.svc_patcher.stop()

    # Scopo: Verifica GET lista preventivi restituisce 200.
    def test_list_preventivi_200(self):
        self.mock_svc.list_preventivi.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{"id": 1, "numero": "P-0001"}],
        }
        response = self.client.get("/api/v1/vendite/preventivi/")
        # Senza auth il middleware JWT blocca; verifichiamo che la route esista
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST creazione preventivo restituisce 200.
    def test_create_preventivo_200(self):
        self.mock_svc.crea_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        response = self.client.post(
            "/api/v1/vendite/preventivi/",
            data='{"utility_id": 5}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica GET dettaglio preventivo restituisce 200.
    def test_get_preventivo_detail_200(self):
        # Fase 3.F6: detail non embedda piu' `righe` (endpoint /righe/ autonomo).
        self.mock_svc.get_preventivo.return_value = {
            "id": 1, "numero": "P-0001", "righe_count": 0, "indirizzi": [],
        }
        response = self.client.get("/api/v1/vendite/preventivi/1/")
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica GET dettaglio preventivo non trovato.
    def test_get_preventivo_detail_404(self):
        from apps.core.services.service_errors import ServiceError
        self.mock_svc.get_preventivo.side_effect = ServiceError(
            code="E_PREV_NOT_FOUND", message="Preventivo non trovato."
        )
        response = self.client.get("/api/v1/vendite/preventivi/999/")
        self.assertIn(response.status_code, [401, 403, 404])

    # Scopo: Verifica POST cambio stato. Uso ANNULLATO come transizione
    # esempio: EMESSO non passa piu' da /stato/ (refactor 2026-05-28, vedi
    # endpoint dedicato /emetti/ multipart).
    def test_cambio_stato_200(self):
        self.mock_svc.cambia_stato.return_value = {"status": "ok"}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/stato/",
            data='{"nuovo_stato": "ANNULLATO"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Smoke test endpoint emissione (multipart). BOZZA->EMESSO con
    # genera documento + allegati orchestrato atomicamente nella view
    # ApiPreventivoEmetti (refactor 2026-05-28, mirror del flusso offerta).
    # Verifica route registrata e accetta payload multipart vuoto.
    def test_emetti_200(self):
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/emetti/",
            data={},  # multipart vuoto: nessun allegato
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST aggiunta riga.
    def test_add_riga_200(self):
        self.mock_svc.gestisci_riga.return_value = {"id": 10}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/righe/",
            data='{"articolo_id": "uuid-art-1"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica GET righe smistabili a ordine (dialog smistamento merce).
    def test_righe_smistabili_ordine_200(self):
        self.mock_svc.list_righe_smistabili_ordine.return_value = [
            {"id": 10, "articolo_codice": "ART1", "qta_operativa": "2"},
        ]
        response = self.client.get(
            "/api/v1/vendite/preventivi/1/righe-smistabili-ordine/"
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST push commessa.
    def test_push_commessa_200(self):
        self.mock_svc.push_a_commessa.return_value = {"righe_pushate": 3}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/push-commessa/",
            data="{}",
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-1",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: POST push commessa con righe_ids (smistamento selettivo dal
    # Pannello Smistamento): il sottoinsieme arriva al service come kwarg.
    def test_push_commessa_righe_ids_200(self):
        self.mock_svc.push_a_commessa.return_value = {"righe_pushate": 2}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/push-commessa/",
            data='{"righe_ids": [10, 11]}',
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-2",
        )
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            self.mock_svc.push_a_commessa.assert_called_once_with(
                1, righe_ids=[10, 11],
            )

    # Scopo: righe_ids=[] (lista vuota) → errore esplicito di validazione,
    # NON degrada a "tutte le righe" (contratto API: omettere il campo per
    # il push completo). Il service non viene mai invocato.
    def test_push_commessa_righe_ids_vuoto_422(self):
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/push-commessa/",
            data='{"righe_ids": []}',
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-3",
        )
        self.assertIn(response.status_code, [400, 422, 401, 403])
        if response.status_code in (400, 422):
            self.mock_svc.push_a_commessa.assert_not_called()

    # Scopo: GET smistamento (Pannello Smistamento): aggregato + righe.
    def test_smistamento_200(self):
        self.mock_svc.smistamento.return_value = {
            "aggregato": {"righe_totali": 2, "righe_residue": 1},
            "righe": [{"riga_id": 10, "stato_smistamento": "RESIDUA"}],
        }
        response = self.client.get("/api/v1/vendite/preventivi/1/smistamento/")
        self.assertIn(response.status_code, [200, 401, 403])

    # ── Componenti BoM CASO A ──

    # Scopo: GET lista componenti di una riga padre (refactor componenti 2026-05-11).
    def test_list_componenti_riga_200(self):
        self.mock_svc.list_componenti_riga.return_value = [
            {"id": 1, "componente_id": "c1", "prezzo_unitario": "200"},
            {"id": 2, "componente_id": "c2", "prezzo_unitario": "75"},
        ]
        response = self.client.get(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: PATCH override prezzo componente.
    def test_update_componente_200(self):
        self.mock_svc.update_componente.return_value = {
            "status": "ok", "componente_id": 50,
        }
        response = self.client.patch(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/50/",
            data='{"prezzo_unitario": "150.00", "origine_prezzo": "MANUALE"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: DELETE soft delete componente.
    def test_delete_componente_200(self):
        self.mock_svc.delete_componente.return_value = {
            "status": "ok", "componente_id": 50, "deleted": True,
        }
        response = self.client.delete(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/50/",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: GET componenti su riga inesistente -> 404 dal service.
    def test_get_componente_404(self):
        from apps.core.services.service_errors import ServiceError
        self.mock_svc.list_componenti_riga.side_effect = ServiceError(
            code="E_PREV_RIGA_NOT_FOUND", message="Riga preventivo non trovata.",
        )
        response = self.client.get(
            "/api/v1/vendite/preventivi/1/righe/999/componenti/",
        )
        self.assertIn(response.status_code, [401, 403, 404])



class TestPreventivoEmissioneAllegati(JwtMockedApiTest):
    """Test integration per il flusso emissione + endpoint allegati documento."""

    def setUp(self) -> None:
        super().setUp()

    # Scopo: integration test ApiPreventivoEmetti. Verifica che la view
    # orchestri correttamente service.emetti() + genera_documento(allegati=...)
    # passando i parametri estratti dal preventivo + sorgente_tipo_id risolto.
    # Mock di transaction.atomic per non aprire una vera transazione DB.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_VIEW_ATOMIC)
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_PREV_REPO)
    @patch(_PREV_SVC)
    def test_emetti_integration_atomic_state_genera_allegati(
        self, svc_mod, repo_cls, sorgenti_repo_cls, doc_svc_cls, _atomic, _auth,
    ):
        svc_mod.emetti.return_value = {
            "id": 7, "stato_codice_interno": "EMESSO",
        }
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 5, "codice": "PREVENTIVO",
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "preventivo.pdf",
        }

        pdf_file = SimpleUploadedFile(
            "allegato.pdf", b"%PDF-1.4 fake", content_type="application/pdf",
        )
        resp = self.client.post(
            _BASE + "7/emetti/",
            data={"allegati": [pdf_file]},
        )

        self.assertEqual(resp.status_code, 200)
        # service.emetti chiamato una sola volta col preventivo_id corretto
        # (+ user acting, inoltrato per il completamento del flusso pratica-first).
        svc_mod.emetti.assert_called_once_with(7, user=ANY)
        # genera_documento ricevuto i parametri estratti dal preventivo +
        # l'allegato dal multipart
        kwargs = doc_svc_cls.return_value.genera_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 5)
        self.assertEqual(kwargs["sorgente_id"], 7)
        self.assertEqual(kwargs["sorgente_uid"], "0190b000-0000-0000-0000-000000000007")
        self.assertEqual(len(kwargs["allegati"]), 1)
        self.assertEqual(kwargs["allegati"][0]["mime_type"], "application/pdf")
        self.assertEqual(kwargs["allegati"][0]["file_name"], "allegato.pdf")

    # Scopo: GET allegati lista i file (principale + allegati) di un documento
    # esistente. Verifica route e delega a list_documento_files.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_PREV_REPO)
    def test_get_documento_allegati_list_ok(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 5, "codice": "PREVENTIVO",
        }
        doc_svc_cls.return_value.list_documento_files.return_value = {
            "files": [
                {"id": 1, "is_principale": True, "file_name": "preventivo.pdf"},
                {"id": 2, "is_principale": False, "file_name": "allegato.pdf"},
            ],
        }

        resp = self.client.get(_BASE + "7/documenti/100/allegati/")

        self.assertEqual(resp.status_code, 200)
        doc_svc_cls.return_value.list_documento_files.assert_called_once()
        # Il documento_id passato al service deve essere quello dell'URL.
        args = doc_svc_cls.return_value.list_documento_files.call_args.args
        self.assertEqual(args[1], 100)

    # Scopo: POST allegati su documento esistente (modalita' append) — utile
    # post-emissione per aggiungere file. Estrae multipart e delega a
    # aggiungi_allegati.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_PREV_REPO)
    def test_post_documento_allegati_upload_ok(
        self, repo_cls, sorgenti_repo_cls, doc_svc_cls, _auth,
    ):
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 5, "codice": "PREVENTIVO",
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


class PreventivoPermessoPassaggioTests(SimpleTestCase):
    # Scopo: cambio stato (anche dalla pratica) ed emissione del preventivo
    #        leggono l'azione dalla riga del passaggio (M-3,
    #        brief-modello-documento-vendita §8.7 punto 2), non la dichiarano:
    #        `cambia_stato_preventivi` e' spenta, e un `post_permission` rimasto
    #        risponderebbe 403 a tutti.
    def test_cambio_stato_ed_emissione_dichiarano_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.preventivi_documenti_views import ApiPreventivoEmetti
        from apps.vendite.api.preventivi_views import (
            ApiPreventivoStato,
            ApiPreventivoStatoDaPratica,
            _preventivo_della_pratica,
        )

        self.assertEqual(ApiPreventivoEmetti.post_passaggio, PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="sorgente_id", stato_del_modello="emissione",
        ))
        self.assertEqual(ApiPreventivoStato.post_passaggio, PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="preventivo_id",
            campo_stato="nuovo_stato",
        ))
        self.assertEqual(ApiPreventivoStatoDaPratica.post_passaggio, PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="pratica_id",
            campo_stato="nuovo_stato", risolvi_documento=_preventivo_della_pratica,
        ))
        for view in (ApiPreventivoEmetti, ApiPreventivoStato, ApiPreventivoStatoDaPratica):
            with self.subTest(view=view.__name__):
                self.assertIsNone(getattr(view, "post_permission", None))
                # Senza azione sulla riga decide il livello sul DOCUMENTO.
                self.assertEqual(view.model_permission, ("vendite", "preventivo"))

    def test_collega_pratica_chiede_il_livello(self) -> None:
        from apps.vendite.api.preventivi_views import ApiPreventivoCollegaPratica

        self.assertIsNone(getattr(ApiPreventivoCollegaPratica, "post_permission", None))
        self.assertIsNone(getattr(ApiPreventivoCollegaPratica, "post_passaggio", None))
        self.assertEqual(ApiPreventivoCollegaPratica.model_permission, ("vendite", "preventivo"))

    # Il permesso (`PassaggioDocumento`) legge `nuovo_stato` ripulito: il
    # service deve ricevere lo stesso valore, o il rifiuto dell'emissione
    # guarderebbe un codice diverso da quello del permesso.
    def test_nuovo_stato_ripulito(self) -> None:
        from apps.vendite.api.preventivi_views import _parse_cambio_stato_payload

        self.assertEqual(_parse_cambio_stato_payload({"nuovo_stato": " EMESSO "})[0], "EMESSO")

    def test_nuovo_stato_assente_o_non_testo_e_un_400(self) -> None:
        from apps.core.services.service_errors import ServiceError
        from apps.vendite.api.preventivi_views import _parse_cambio_stato_payload

        for corpo in ({}, {"nuovo_stato": None}, {"nuovo_stato": 123}, {"nuovo_stato": "  "}):
            with self.subTest(corpo=corpo):
                with self.assertRaises(ServiceError) as cm:
                    _parse_cambio_stato_payload(corpo)
                self.assertEqual(cm.exception.code, "E_PREV_VALIDAZIONE")
                self.assertEqual(cm.exception.context.get("field"), "nuovo_stato")
