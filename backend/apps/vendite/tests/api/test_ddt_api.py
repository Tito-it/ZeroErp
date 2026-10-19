# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint DDT di vendita (CRUD testata + righe, emetti,
#        cambio stato data-driven, push singolo a commessa) + endpoint di
#        evasione lato ordine (genera-ddt). Mock del service layer (funzioni
#        modulo), nessun accesso DB (CI-compatible). Verifica envelope, auth,
#        routing e propagazione parametri al service. Clone di test_ordini_api.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt        — 401 senza Authorization header
 2) test_list_ok_envelope         — 200 envelope paginato (mock service)
 3) test_create_ok                — 200 create DDT BOZZA (mock service)
 4) test_emetti_ok                — 200 emetti multipart DRAFT->EMESSO + genera PDF (mock)
 5) test_cambia_stato_ok          — 200 transizione generica (mock service)
 6) test_push_ok                  — 200 push singolo a commessa (mock service)
 7) test_patch_ddt_ok             — 200 PATCH testata (mock service)
 8) test_patch_riga_ok            — 200 PATCH riga (mock service)
 9) test_genera_ddt_da_ordine_ok  — 200 POST /ordini/<id>/genera-ddt/ (mock service)
10) test_genera_ddt_righe_selettive — righe evasione parziale propagate al service
11) test_riepilogo_iva_ok         — 200 riepilogo IVA aggregato (mock service)
12) test_indirizzi_get_ok         — 200 pannello indirizzi tipi+slot (mock service)
13) test_indirizzi_upsert_ok      — 200 upsert slot indirizzo, payload propagato (mock)
14) test_indirizzi_delete_ok      — 200 delete slot indirizzo (mock service)
15) test_cambia_stato_annullo_con_conferma — legami_confermati propagato al service
16) test_legami_ok                — 200 GET legami della bolla (mock service)
17) test_riga_qta_evasa_ok        — 200 POST verbo quantita' evasa, payload propagato
"""

from unittest.mock import ANY, Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.ddt_service"

# Patch path del flusso emissione documentale (mirror test_ordini_api): la view
# emetti/ vive in ddt_documenti_views (multipart, emetti + genera PDF atomico).
_DOC_VIEW_SVC = "apps.vendite.api.ddt_documenti_views.ddt_service"
_DOC_GEN_SVC = "apps.vendite.api.ddt_documenti_views.DocumentGenerationService"
_SORGENTI_REPO = "apps.documenti.api.contesto_helpers.SorgentiRepository"
_DDT_REPO = "apps.vendite.api.ddt_documenti_views.DdtRepository"
_VIEW_ATOMIC = "apps.documenti.api.sorgente_documenti_views.transaction.atomic"

_BASE = "/api/v1/vendite/ddt/"
_ORD_BASE = "/api/v1/vendite/ordini/"


class TestDdtApi(JwtMockedApiTest):
    """Smoke test endpoint DDT di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ddt_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "DDT0001",
              "destinatario_denominazione": "Rossi SRL",
              "stato_codice_interno": "DRAFT"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "DDT0001")

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_BASE}export/?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_ddt_rows")
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

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {"id": 7, "uid": "u-7", "numero": None}
        resp = self.client.post(
            _BASE, data={"billing_account_id": 3, "utility_id": 1},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        mock_crea.assert_called_once()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_VIEW_ATOMIC)
    @patch(_DOC_GEN_SVC)
    @patch(_SORGENTI_REPO)
    @patch(_DDT_REPO)
    @patch(_DOC_VIEW_SVC)
    def test_emetti_ok(
        self, svc_mod, repo_cls, sorgenti_repo_cls, doc_svc_cls, _atomic, _auth,
    ) -> None:
        # Emissione documentale multipart (mirror ordini): la view orchestra
        # ddt_service.emetti (assegna numero) + genera_documento in atomico.
        # `emetti` ritorna il risultato LIGHT della transizione (parita'
        # ordini_service.conferma): niente detail pesante nella sezione atomica.
        svc_mod.emetti.return_value = {
            "ddt_id": 7, "stato_precedente": "DRAFT", "stato": "EMESSO",
        }
        repo_cls.return_value.get_for_documento_generation.return_value = {
            "id": 7,
            "uid": "0190b000-0000-0000-0000-000000000007",
            "emittente_fiscale_id": 11,
        }
        sorgenti_repo_cls.return_value.get_sorgente_attiva.return_value = {
            "id": 5, "codice": "DDT_VENDITA",
        }
        doc_svc_cls.return_value.genera_documento.return_value = {
            "id": 100, "uid": "doc-uid-100", "nome_file": "ddt.pdf",
        }
        resp = self.client.post(f"{_BASE}7/emetti/", data={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["ddt"]["stato"], "EMESSO")
        self.assertEqual(body["documento"]["id"], 100)
        svc_mod.emetti.assert_called_once_with(7)
        # genera_documento riceve emittente + sorgente risolti dal contesto.
        doc_svc_cls.return_value.genera_documento.assert_called_once()
        kwargs = doc_svc_cls.return_value.genera_documento.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 5)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.cambia_stato")
    def test_cambia_stato_ok(self, mock_cs, _auth) -> None:
        mock_cs.return_value = {"ddt_id": 7, "stato": "SPEDITO"}
        resp = self.client.post(
            f"{_BASE}7/cambia-stato/", data={"stato_codice": "SPEDITO"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "SPEDITO")
        # Al primo tentativo nessuna dichiarazione (D-8): None, non assente.
        mock_cs.assert_called_once_with(7, "SPEDITO", legami_confermati=None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.cambia_stato")
    def test_cambia_stato_annullo_con_conferma(self, mock_cs, _auth) -> None:
        mock_cs.return_value = {"ddt_id": 7, "stato": "ANNULLATO"}
        resp = self.client.post(
            f"{_BASE}7/cambia-stato/",
            data={"stato_codice": "ANNULLATO", "legami_confermati": 2},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_cs.assert_called_once_with(7, "ANNULLATO", legami_confermati=2)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.get_legami")
    def test_legami_ok(self, mock_leg, _auth) -> None:
        mock_leg.return_value = {"documento": "DDT_VENDITA", "id": 7, "legami": 1, "righe": []}
        resp = self.client.get(f"{_BASE}7/legami/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["legami"], 1)
        mock_leg.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.correggi_qta_evasa")
    def test_riga_qta_evasa_ok(self, mock_qta, _auth) -> None:
        mock_qta.return_value = {"ddt_id": 7, "riga_id": 31, "qta_evasa": "6"}
        resp = self.client.post(
            f"{_BASE}7/righe/31/qta-evasa/", data={"qta_operativa": "6"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["qta_evasa"], "6")
        mock_qta.assert_called_once_with(7, 31, {"qta_operativa": "6"})

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.push_a_commessa")
    def test_push_ok(self, mock_push, _auth) -> None:
        mock_push.return_value = {"ddt_id": 7, "stato": "COMPLETATO"}
        resp = self.client.post(f"{_BASE}7/push/", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "COMPLETATO")
        # user propagato dal JWT (username dell'utente autenticato).
        mock_push.assert_called_once_with(7, user=ANY)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_riepilogo_iva")
    def test_riepilogo_iva_ok(self, mock_riep, _auth) -> None:
        mock_riep.return_value = [
            {"ddt_id": 7, "iva_id": 1, "iva_codice": "22",
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
    @patch(f"{_SVC}.list_indirizzi")
    def test_indirizzi_get_ok(self, mock_list, _auth) -> None:
        mock_list.return_value = {
            "tipi_ammessi": [{"tipo_indirizzo_id": 10,
                              "tipo_indirizzo_codice": "CON",
                              "obbligatorio": True}],
            "indirizzi": [],
        }
        resp = self.client.get(f"{_BASE}7/indirizzi/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["tipi_ammessi"][0]["tipo_indirizzo_codice"], "CON")
        mock_list.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.upsert_indirizzo")
    def test_indirizzi_upsert_ok(self, mock_ups, _auth) -> None:
        mock_ups.return_value = {"id": 3, "ddt_id": 7, "tipo_indirizzo_id": 10}
        resp = self.client.post(
            f"{_BASE}7/indirizzi/",
            data={"tipo_indirizzo_id": 10, "origine_indirizzo_id": 55},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 3)
        mock_ups.assert_called_once_with(
            7, {"tipo_indirizzo_id": 10, "origine_indirizzo_id": 55})

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.delete_indirizzo")
    def test_indirizzi_delete_ok(self, mock_del, _auth) -> None:
        mock_del.return_value = {"deleted": True, "id": 3}
        resp = self.client.delete(f"{_BASE}7/indirizzi/3/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])
        mock_del.assert_called_once_with(7, 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_ddt")
    def test_patch_ddt_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (DRF ha gia' parsato il body JSON).
        mock_upd.return_value = {"ddt_id": 7, "updated": True}
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
        mock_upd.return_value = {"ddt_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"quantita": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1], 3)


class TestOrdineGeneraDdtApi(JwtMockedApiTest):
    """Endpoint di evasione lato ordine: POST /ordini/<id>/genera-ddt/.

    Vive nel dominio SORGENTE (ordine) ma delega a `ddt_service.crea_ddt_da_ordine`
    (import locale nella view). Mock del service, nessun accesso DB.
    """

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt_da_ordine")
    def test_genera_ddt_da_ordine_ok(self, mock_gen, _auth) -> None:
        mock_gen.return_value = {"ddt_id": 42, "numero": None, "ordine_id": 7}
        resp = self.client.post(
            f"{_ORD_BASE}7/genera-ddt/", data={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["ddt_id"], 42)
        # Body vuoto -> None = evade tutto il residuo.
        mock_gen.assert_called_once_with(7, None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_ddt_da_ordine")
    def test_genera_ddt_righe_selettive(self, mock_gen, _auth) -> None:
        # Evasione parziale: le righe {ordine_riga_id, qta_da_evadere} arrivano
        # normalizzate al service (unita' operativa).
        mock_gen.return_value = {"ddt_id": 43, "numero": None, "ordine_id": 7}
        resp = self.client.post(
            f"{_ORD_BASE}7/genera-ddt/",
            data={"righe": [{"ordine_riga_id": 11, "qta_da_evadere": "2"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_gen.assert_called_once_with(
            7, [{"ordine_riga_id": 11, "qta_da_evadere": "2"}],
        )
