# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint resi di vendita (CRUD testata + righe,
#        conferma/annullo, DDT di ri-consegna, code di lavoro) + endpoint
#        righe-per-reso lato DDT. Mock del service layer (funzioni modulo),
#        nessun accesso DB (CI-compatible). Verifica envelope, auth, routing e
#        propagazione parametri al service. Clone di test_ddt_api.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_richiede_jwt          — 401 senza Authorization header
 2) test_list_ok_envelope           — 200 envelope paginato (mock service)
 3) test_create_ok                  — 200 create reso da DDT (mock service)
 4) test_conferma_ok                — 200 conferma (fn madre, mock service)
 5) test_annulla_ok                 — 200 annullo (fn madre, mock service)
 6) test_riconsegna_ok_totale       — 200 body vuoto -> righe None (tutta la copertura)
 7) test_riconsegna_righe_parziali  — righe {resi_riga_id, qta} propagate al service
 8) test_patch_reso_ok              — 200 PATCH testata (mock service)
 9) test_righe_get_ok               — 200 lista righe (mock service)
10) test_patch_riga_ok              — 200 PATCH riga (mock service)
11) test_delete_riga_ok             — 200 DELETE riga (mock service)
12) test_da_accreditare_ok          — 200 coda accrediti (mock service)
13) test_da_riconsegnare_ok         — 200 coda ri-consegne (mock service)
14) test_ddt_righe_per_reso_ok      — 200 GET /ddt/<id>/righe-per-reso/ (mock)
15) test_coda_filtro_ddt_propagato — ?ddt_id= arriva al service (FE-2)
16) test_coda_filtro_ordine_propagato — ?ordine_id= arriva al service
17) test_coda_filtro_documento_non_numerico_400 — garbage NON sparisce come filtro
18) test_accrediti_ok                  — POST massivo, ids propagati al service
19) test_accrediti_parziale_e_200      — PARZIALE non e' un errore HTTP
20) test_accrediti_senza_idempotency_key — chiave obbligatoria (documento fiscale)
21) test_annulla_accredito_ok          — motivo propagato, reso+riga dal path
22) test_verbi_accredito_dietro_il_permesso — post_permission sulle due porte
"""

from unittest.mock import Mock, patch


from django.test import Client, SimpleTestCase

from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.resi_service"

_BASE = "/api/v1/vendite/resi/"
_DDT_BASE = "/api/v1/vendite/ddt/"


class TestResiApi(JwtMockedApiTest):
    """Smoke test endpoint resi di vendita."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    def test_list_richiede_jwt(self) -> None:
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_resi_rows")
    def test_list_ok_envelope(self, mock_list, _auth) -> None:
        mock_list.return_value = (
            [{"id": 1, "numero": "RESO0001",
              "destinatario_denominazione": "Rossi SRL",
              "stato_codice_interno": "DRAFT",
              "ddt_origine_numero": "DDT0001"}],
            1,
        )
        resp = self.client.get(f"{_BASE}?limit=25")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["numero"], "RESO0001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.crea_reso")
    def test_create_ok(self, mock_crea, _auth) -> None:
        mock_crea.return_value = {
            "id": 7, "uid": "u-7", "numero": None, "righe_ids": [71],
        }
        resp = self.client.post(
            _BASE,
            data={"ddt_id": 30,
                  "righe": [{"ddt_riga_id": 11, "tipo_reso_id": 1,
                             "qta_operativa": "3"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        payload = mock_crea.call_args[0][0]
        self.assertEqual(payload["ddt_id"], 30)
        self.assertEqual(payload["righe"][0]["ddt_riga_id"], 11)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.conferma_reso")
    def test_conferma_ok(self, mock_conf, _auth) -> None:
        mock_conf.return_value = {
            "reso_id": 7, "stato_precedente": "DRAFT", "stato": "CONFERMATO",
        }
        resp = self.client.post(
            f"{_BASE}7/conferma/", data={}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "CONFERMATO")
        mock_conf.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.annulla_reso")
    def test_annulla_ok(self, mock_ann, _auth) -> None:
        mock_ann.return_value = {
            "reso_id": 7, "stato_precedente": "CONFERMATO", "stato": "ANNULLATO",
        }
        resp = self.client.post(
            f"{_BASE}7/annulla/", data={}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "ANNULLATO")
        mock_ann.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.genera_ddt_riconsegna")
    def test_riconsegna_ok_totale(self, mock_ric, _auth) -> None:
        mock_ric.return_value = {"reso_id": 7, "ddt_id": 42, "numero": None}
        resp = self.client.post(
            f"{_BASE}7/genera-ddt-riconsegna/", data={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["ddt_id"], 42)
        # Body vuoto -> righe None = tutta la copertura residua, data None.
        mock_ric.assert_called_once_with(7, None, None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.genera_ddt_riconsegna")
    def test_riconsegna_righe_parziali(self, mock_ric, _auth) -> None:
        # Ri-spedizione parziale: righe {resi_riga_id, qta} (unita' BASE)
        # propagate al service cosi' come arrivano.
        mock_ric.return_value = {"reso_id": 7, "ddt_id": 43, "numero": None}
        resp = self.client.post(
            f"{_BASE}7/genera-ddt-riconsegna/",
            data={"righe": [{"resi_riga_id": 71, "qta": "3"}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_ric.assert_called_once_with(
            7, [{"resi_riga_id": 71, "qta": "3"}], None,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_reso")
    def test_patch_reso_ok(self, mock_upd, _auth) -> None:
        # PATCH via request.data (DRF ha gia' parsato il body JSON).
        mock_upd.return_value = {"reso_id": 7, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/", data={"data": "2026-07-13"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1]["data"], "2026-07-13")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_righe")
    def test_righe_get_ok(self, mock_righe, _auth) -> None:
        mock_righe.return_value = [
            {"id": 71, "reso_id": 7, "quantita": "3",
             "tipo_reso_codice_interno": "RESO_PER_RICONSEGNA",
             "stato_riconsegna": "DA_RICONSEGNARE", "qta_residua": "3"},
        ]
        resp = self.client.get(f"{_BASE}7/righe/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data[0]["stato_riconsegna"], "DA_RICONSEGNARE")
        mock_righe.assert_called_once_with(7)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.aggiorna_riga")
    def test_patch_riga_ok(self, mock_upd, _auth) -> None:
        mock_upd.return_value = {"reso_id": 7, "riga_id": 3, "updated": True}
        resp = self.client.patch(
            f"{_BASE}7/righe/3/", data={"qta_operativa": "5"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        args = mock_upd.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[1], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.elimina_riga")
    def test_delete_riga_ok(self, mock_del, _auth) -> None:
        mock_del.return_value = {"reso_id": 7, "riga_id": 3, "deleted": True}
        resp = self.client.delete(f"{_BASE}7/righe/3/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])
        mock_del.assert_called_once_with(7, 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_accreditare")
    def test_da_accreditare_ok(self, mock_coda, _auth) -> None:
        mock_coda.return_value = (
            [{"resi_riga_id": 71, "reso_id": 7, "reso_numero": "RESO0001",
              "quantita": "3"}],
            1,
        )
        resp = self.client.get(
            f"{_BASE}da-accreditare/"
            "?billing_account_id=3&search=rossi&order_by=descrizione&order_dir=asc"
            "&etichetta=dovuta",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["count"], 1)
        # Filtro BA + search + sort + etichetta propagati al service (path
        # LIST); etichetta normalizzata upper dalla view (qp_str_upper).
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 3)
        self.assertEqual(kwargs["search"], "rossi")
        self.assertEqual(kwargs["order_by"], "descrizione")
        self.assertEqual(kwargs["order_dir"], "asc")
        self.assertEqual(kwargs["etichetta"], "DOVUTA")
        # Nessun documento indicato: filtri a None, non 0 (che sarebbe un id).
        self.assertIsNone(kwargs["ddt_id"])
        self.assertIsNone(kwargs["ordine_id"])

    # Scopo: FE-2 — il collegamento dal pannello situazione merce del DDT porta
    #        la coda GIA' FILTRATA. Se il param non arrivasse al service,
    #        l'operatore vedrebbe la coda intera credendola quella del documento.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_accreditare")
    def test_coda_filtro_ddt_propagato(self, mock_coda, _auth) -> None:
        mock_coda.return_value = ([], 0)
        resp = self.client.get(f"{_BASE}da-accreditare/?ddt_id=15848")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_coda.call_args.kwargs["ddt_id"], 15848)

    # Scopo: lo stesso dal pannello dell'ordine, e sulla coda ri-consegne — la
    #        simmetria fra le due code e' parte del contratto (il pannello le
    #        mostra una sopra l'altra).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_riconsegnare")
    def test_coda_filtro_ordine_propagato(self, mock_coda, _auth) -> None:
        mock_coda.return_value = ([], 0)
        resp = self.client.get(f"{_BASE}da-riconsegnare/?ordine_id=240")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_coda.call_args.kwargs["ordine_id"], 240)

    # Scopo: 🔴 un id malformato deve dare 400, NON sparire come filtro. Un
    #        filtro che svanisce mostra la coda intera facendola sembrare quella
    #        del documento — ed e' il difetto peggiore dei due, perche' sembra
    #        aver funzionato. `qp_int_optional` e' strict e il ValueError diventa
    #        `E_VALIDATION_INPUT` (400) via ErrorTranslator.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_accreditare")
    def test_coda_filtro_documento_non_numerico_400(self, mock_coda, _auth) -> None:
        resp = self.client.get(f"{_BASE}da-accreditare/?ddt_id=banana")
        self.assertEqual(resp.status_code, 400)
        mock_coda.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_da_riconsegnare")
    def test_da_riconsegnare_ok(self, mock_coda, _auth) -> None:
        mock_coda.return_value = (
            [{"resi_riga_id": 71, "reso_id": 7, "qta_resa": "5",
              "qta_riconsegnata": "2", "qta_residua": "3",
              "stato_riconsegna": "PARZIALE"}],
            1,
        )
        resp = self.client.get(
            f"{_BASE}da-riconsegnare/?search=acme&order_by=qta_residua&order_dir=desc",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["results"][0]["stato_riconsegna"], "PARZIALE")
        # search + sort propagati al service (path LIST).
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["search"], "acme")
        self.assertEqual(kwargs["order_by"], "qta_residua")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.list_righe_ddt_per_reso")
    def test_ddt_righe_per_reso_ok(self, mock_righe, _auth) -> None:
        # Endpoint lato dominio DDT (sorgente): alimenta il pannello
        # "crea reso" del drawer DDT.
        mock_righe.return_value = [
            {"ddt_riga_id": 11, "qta_consegnata": "10", "qta_gia_resa": "2",
             "qta_resa_residua": "8"},
        ]
        resp = self.client.get(f"{_DDT_BASE}30/righe-per-reso/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data[0]["qta_resa_residua"], "8")
        mock_righe.assert_called_once_with(30)

    # ── Verbo dell'accredito (B2) e annullo (B2-bis) ──────────────────

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.accredita_righe_reso")
    def test_accrediti_ok(self, mock_acc, _auth) -> None:
        mock_acc.return_value = {
            "esito": "COMPLETATO", "totale": 2, "ok": 2,
            "accrediti": [{"resi_riga_id": 5797, "accredito_id": 901}],
            "falliti": [],
        }
        resp = self.client.post(
            f"{_BASE}accrediti/",
            data={"resi_riga_ids": [5797, 5799]},
            content_type="application/json",
            headers={"idempotency-key": "smoke-accrediti-1"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["esito"], "COMPLETATO")
        mock_acc.assert_called_once_with([5797, 5799])

    # Scopo: 🔴 PARZIALE e' 200, non un errore. Il verbo non e' l'atto fiscale
    # — il documento nasce dopo, nel giro di fatturazione — quindi un esito
    # parziale non lascia mai mezzo documento: lascia righe che restano in
    # coda. Rispondere 4xx butterebbe via l'esito delle righe riuscite.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.accredita_righe_reso")
    def test_accrediti_parziale_e_200(self, mock_acc, _auth) -> None:
        mock_acc.return_value = {
            "esito": "PARZIALE", "totale": 2, "ok": 1, "accrediti": [],
            "falliti": [{"resi_riga_id": 5799,
                         "codice": "E_ACCREDITO_GIA_ESEGUITO",
                         "messaggio": "gia' eseguito"}],
        }
        resp = self.client.post(
            f"{_BASE}accrediti/",
            data={"resi_riga_ids": [5797, 5799]},
            content_type="application/json",
            headers={"idempotency-key": "smoke-accrediti-2"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["falliti"][0]["codice"],
                         "E_ACCREDITO_GIA_ESEGUITO")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.accredita_righe_reso")
    def test_accrediti_senza_idempotency_key(self, mock_acc, _auth) -> None:
        # Modifica di stato su un documento fiscale: senza chiave il service
        # non viene nemmeno chiamato. `Client` semplice: `ClientApi` la
        # metterebbe da se'.
        resp = Client().post(
            f"{_BASE}accrediti/",
            data={"resi_riga_ids": [5797]},
            content_type="application/json",
        )
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mock_acc.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.annulla_accredito_riga_reso")
    def test_annulla_accredito_ok(self, mock_ann, _auth) -> None:
        mock_ann.return_value = {"reso_id": 7, "resi_riga_id": 24, "rimosse": []}
        resp = self.client.post(
            f"{_BASE}7/righe/24/annulla-accredito/",
            data={"motivo": "riga sbagliata"},
            content_type="application/json",
            headers={"idempotency-key": "smoke-annullo-1"},
        )
        self.assertEqual(resp.status_code, 200)
        mock_ann.assert_called_once_with(7, 24, "riga sbagliata")

    # Scopo: 🔴 il presidio del permesso si legge dalle CLASSI REALI. Fino al
    # seed di P-1 il codename non era a catalogo e il verbo restava
    # fail-closed; ora c'e', e questa e' la porta di un documento fiscale.
    # ⚠️ Le due facce dello stesso atto condividono il codename: due permessi
    # distinti si sfilerebbero al primo profilo configurato a mano.
    def test_verbi_accredito_dietro_il_permesso(self) -> None:
        from apps.vendite.api.views_resi import (
            ApiResiAccrediti,
            ApiResoRigaAnnullaAccredito,
        )

        self.assertEqual(ApiResiAccrediti.post_permission, "accredita_riga_reso")
        self.assertEqual(
            ApiResoRigaAnnullaAccredito.post_permission, "accredita_riga_reso",
        )
        self.assertEqual(ApiResiAccrediti.area_funzionale, "vendite")


class ResiPermessoAzioneTests(SimpleTestCase):
    # Scopo: conferma e annullo del reso non dichiarano piu' l'azione: la legge
    #        la catena dalla riga del passaggio, la stessa del verbo (M-3,
    #        brief-modello-documento-vendita §7.6). Con M-4 l'annullo di una
    #        bozza non chiede `conferma_reso`, e un `post_permission` fisso lo
    #        avrebbe rifiutato.
    def test_conferma_e_annullo_dichiarano_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.views_resi import ApiResoAnnulla, ApiResoConferma

        self.assertEqual(ApiResoConferma.post_passaggio, PassaggioDocumento(
            testata="vendite.resi", documento_kwarg="reso_id", stato_chiesto="CONFERMATO",
        ))
        # L'annullo: lo stato d'annullo dal vocabolario, non un letterale (§9.8).
        self.assertEqual(ApiResoAnnulla.post_passaggio, PassaggioDocumento(
            testata="vendite.resi", documento_kwarg="reso_id", stato_del_modello="annullo",
        ))
        for view in (ApiResoConferma, ApiResoAnnulla):
            with self.subTest(view=view.__name__):
                self.assertIsNone(getattr(view, "post_permission", None))
