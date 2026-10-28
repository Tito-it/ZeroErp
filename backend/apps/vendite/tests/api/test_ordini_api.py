# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint ordini di vendita (scheletro CRUD + lista
#        DEF-8 + export + conferma + push). Mock del service layer (funzioni
#        modulo), nessun accesso DB (CI-compatible). Verifica envelope, auth,
#        validazione formato export, overflow cap, routing.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt — 401 senza Authorization header
 2) test_list_ok_envelope — 200 envelope paginato (mock service)
 3) test_create_ok — 200 create ordine (mock service)
 4) test_conferma_senza_emetti_ritirata — 404: `/conferma/` ritirata (Z-2)
 5) test_push_ok — 200 push singolo a commessa (mock service)
 5b) test_cambia_stato_ok — 200 transizione generica (mock service)
 6) test_riepilogo_iva_ok — 200 riepilogo IVA aggregato (mock service)
 7) test_export_formato_invalido — 400 E_UI_EXPORT_FORMAT_INVALID
 8) test_export_overflow_cap — 422 E_UI_EXPORT_LIMIT_EXCEEDED su >cap righe
 9) test_emetti_route_ok — POST emetti (multipart) DRAFT->CONFERMATO route OK
10) test_emetti_integration_atomic_conferma_genera_allegati — POST emetti
    orchestra conferma + genera_documento(allegati=...) in transazione atomica
11) test_emetti_e_cambia_stato_dichiarano_il_passaggio — l'azione dalla riga
    del passaggio; «Emetti» con lo stato di emissione dal vocabolario
"""

from unittest.mock import ANY, Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.ordini_service"

# Patch path per il flusso emissione documentale ordini (§6 brief-ordini-stampa).
# DocumentiRepository vive nel helper condiviso `contesto_helpers`; le altre
# dipendenze sono importate nel modulo della view documentale.
_DOC_VIEW_SVC = "apps.vendite.api.ordini_documenti_views.ordini_service"
_DOC_GEN_SVC = "apps.vendite.api.ordini_documenti_views.DocumentGenerationService"
_SORGENTI_REPO = "apps.documenti.api.contesto_helpers.SorgentiRepository"
_ORD_REPO = "apps.vendite.api.ordini_documenti_views.OrdiniRepository"
_VIEW_ATOMIC = "apps.documenti.api.sorgente_documenti_views.transaction.atomic"

_BASE = "/api/v1/vendite/ordini/"


class TestOrdiniApi(JwtMockedApiTest):
    """Smoke test endpoint ordini di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ordini_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "ORD0001", "ragione_sociale_completa": "Rossi SRL",
              "stato_codice_interno": "DRAFT"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "ORD0001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ordine")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {"id": 7, "uid": "u-7", "numero": "ORD0007"}
        resp = self.client.post(
            _BASE, data={"billing_account_id": 3, "utility_id": 1},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["numero"], "ORD0007")
        mock_crea.assert_called_once()

    # Z-2 (brief-modello-documento-vendita §9.6 C-4): la conferma senza PDF e'
    # ritirata, l'ordine si conferma solo da «Emetti». La rotta non c'e' piu'.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.conferma")
    def test_conferma_senza_emetti_ritirata(self, mock_conf, _auth) -> None:
        resp = self.client.post(f"{_BASE}7/conferma/", content_type="application/json")
        self.assertEqual(resp.status_code, 404)
        mock_conf.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.push_a_commessa")
    def test_push_ok(self, mock_push, _auth) -> None:
        mock_push.return_value = {"ordine_id": 7, "stato": "COMPLETATO"}
        resp = self.client.post(f"{_BASE}7/push/", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "COMPLETATO")
        mock_push.assert_called_once_with(7, user=ANY)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.cambia_stato")
    def test_cambia_stato_ok(self, mock_cs, _auth) -> None:
        mock_cs.return_value = {"ordine_id": 7, "stato": "ANNULLATO"}
        resp = self.client.post(
            f"{_BASE}7/cambia-stato/", data={"stato_codice": "ANNULLATO"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "ANNULLATO")
        mock_cs.assert_called_once_with(7, "ANNULLATO", legami_confermati=None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_riepilogo_iva")
    def test_riepilogo_iva_ok(self, mock_riep, _auth) -> None:
        mock_riep.return_value = [
            {"ordine_id": 7, "iva_id": 1, "iva_codice": "22",
             "iva_aliquota": "22.00", "imponibile": "100.00",
             "imposta": "22.00", "totale_riga": "122.00"},
        ]
        resp = self.client.get(f"{_BASE}7/riepilogo-iva/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["iva_aliquota"], "22.00")
        mock_riep.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_ordine")
    def test_patch_ordine_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (non handle_post_json): body JSON gia' parsato
        # da DRF deve arrivare al service.
        mock_upd.return_value = {"ordine_id": 7, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/", data={"data": "2026-06-10"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1]["data"], "2026-06-10")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_riga")
    def test_patch_riga_ok(self, mock_upd, _auth) -> None:
        mock_upd.return_value = {"ordine_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"quantita": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_BASE}export/?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ordini_rows")
    def test_export_overflow_cap(self, mock_list, _auth) -> None:
        mock_list.return_value = ([], 50_000)
        resp = self.client.get(f"{_BASE}export/?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )
        # Regressione bug cap-200: l'export deve alzare il cap oltre 200
        # (max_limit), altrimenti il file uscirebbe troncato in silenzio.
        self.assertGreater(mock_list.call_args.kwargs["max_limit"], 200)


class TestOrdineEmissione(JwtMockedApiTest):
    """Test flusso emissione ordine (DRAFT->CONFERMATO + genera PDF + allegati).

    Mirror di `TestPreventivoEmissioneAllegati`: l'endpoint `emetti/` clona
    `ApiPreventivoEmetti` riusando il service di dominio `ordini_service.conferma`
    al posto di `preventivi_service.emetti`.
    """

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Scopo: smoke test route emissione (multipart). Verifica che la route
    # `emetti/` sia registrata e accetti un payload multipart vuoto.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_VIEW_ATOMIC)
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_ORD_REPO)
    @patch(_DOC_VIEW_SVC)
    def test_emetti_route_ok(
        self, svc_mod, repo_cls, sorgenti_repo_cls, doc_svc_cls, _atomic, _auth,
    ) -> None:
        svc_mod.conferma.return_value = {"ordine_id": 7, "stato": "CONFERMATO"}
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4, "codice": "ORDINE_VENDITA",
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "ordine.pdf",
        }
        resp = self.client.post(f"{_BASE}7/emetti/", data={})
        self.assertEqual(resp.status_code, 200)

    # Scopo: integration test ApiOrdineEmetti. Verifica che la view orchestri
    # conferma() + genera_documento(allegati=...) passando i parametri estratti
    # dall'ordine + sorgente_tipo_id risolto. Mock di transaction.atomic per non
    # aprire una vera transazione DB.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_VIEW_ATOMIC)
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_ORD_REPO)
    @patch(_DOC_VIEW_SVC)
    def test_emetti_integration_atomic_conferma_genera_allegati(
        self, svc_mod, repo_cls, sorgenti_repo_cls, doc_svc_cls, _atomic, _auth,
    ) -> None:
        svc_mod.conferma.return_value = {
            "ordine_id": 7, "stato_precedente": "DRAFT", "stato": "CONFERMATO",
        }
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 4, "codice": "ORDINE_VENDITA",
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "ordine.pdf",
        }

        pdf_file = SimpleUploadedFile(
            "allegato.pdf", b"%PDF-1.4 fake", content_type="application/pdf",
        )
        resp = self.client.post(
            f"{_BASE}7/emetti/", data={"allegati": [pdf_file]},
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["ordine"]["stato"], "CONFERMATO")
        self.assertEqual(body["documento"]["nome_file"], "ordine.pdf")
        # conferma chiamata una sola volta con l'ordine_id corretto e l'utente
        # della richiesta (chiude lo step della pratica)
        svc_mod.conferma.assert_called_once_with(7, user=ANY)
        # genera_documento riceve i parametri estratti dall'ordine + l'allegato
        kwargs = doc_svc_cls.return_value.genera_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 4)
        self.assertEqual(kwargs["sorgente_id"], 7)
        self.assertEqual(
            kwargs["sorgente_uid"], "0190b000-0000-0000-0000-000000000007",
        )
        self.assertEqual(len(kwargs["allegati"]), 1)
        self.assertEqual(kwargs["allegati"][0]["mime_type"], "application/pdf")
        self.assertEqual(kwargs["allegati"][0]["file_name"], "allegato.pdf")


class OrdinePassaggioPermessoTests(SimpleTestCase):
    # Scopo: «Emetti» e il cambio stato dell'ordine leggono l'azione dalla riga
    #        del passaggio (M-3, brief-modello-documento-vendita §9.6 C-5), non
    #        la dichiarano: nessun `post_permission` accanto. «Emetti» chiede
    #        lo stato di emissione al vocabolario a ogni richiesta (§8.11 B-2).
    def test_emetti_e_cambia_stato_dichiarano_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.ordini_documenti_views import ApiOrdineEmetti
        from apps.vendite.api.views_ordini import ApiOrdineCambiaStato

        self.assertEqual(ApiOrdineEmetti.post_passaggio, PassaggioDocumento(
            testata="vendite.ordini", documento_kwarg="sorgente_id", stato_del_modello="emissione",
        ))
        self.assertEqual(ApiOrdineCambiaStato.post_passaggio, PassaggioDocumento(
            testata="vendite.ordini", documento_kwarg="ordine_id",
        ))
        for view in (ApiOrdineEmetti, ApiOrdineCambiaStato):
            with self.subTest(view=view.__name__):
                self.assertIsNone(getattr(view, "post_permission", None))
