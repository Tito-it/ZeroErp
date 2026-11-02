# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API flussi (lista, dettaglio, stato,
#        prerequisiti, canali, generazione cross-pratica).
#        Mock services e repository, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FlussiApiTests.test_get_lista_flussi_ok
2) FlussiApiTests.test_post_crea_flusso_ok
3) FlussiApiTests.test_get_dettaglio_flusso_ok
4) FlussiApiTests.test_get_dettaglio_flusso_ownership_mismatch
5) FlussiApiTests.test_post_stato_flusso_completamento_ok
6) FlussiApiTests.test_post_stato_flusso_avvio_ok
7) FlussiApiTests.test_post_stato_flusso_generico_ok
8) FlussiApiTests.test_get_prerequisiti_ok
9) FlussiApiTests.test_get_prerequisiti_senza_template
10) FlussiApiTests.test_get_canali_ok
11) FlussiApiTests.test_get_regole_generazione_ok
12) FlussiApiTests.test_post_genera_pratica_ok
13) FlussiApiTests.test_get_pratiche_generate_ok
14) FlussiApiTests.test_v1_richiede_jwt
15) FlussiApiTests.test_post_assegnazione_flusso_ok
16) FlussiApiTests.test_post_assegnazione_flusso_ownership_mismatch
17) FlussiApiTests.test_post_assegnazione_flusso_parziale
18) FlussiApiTests.test_get_operatori_reparto_ok
19) FlussiApiTests.test_get_pratica_di_flusso_ok
20) FlussiApiTests.test_get_pratica_di_flusso_non_visibile
21) FlussiApiTests.test_get_lista_flussi_parametri_lista
22) FlussiApiTests.test_lista_flussi_dichiara_il_cancello_col_parametro_emittente
23) FlussiApiTests.test_post_crea_flusso_passa_l_emittente_della_query_al_cancello
"""

import json
from unittest.mock import ANY, Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"
_SVC = "apps.pratiche.services.pratiche_service"


def _mock_flusso_row(
    flusso_id: int = 1,
    *,
    pratica_id: int = 1,
    template_flusso_id: int | None = 10,
    stato_codice_interno: str | None = None,
) -> dict:
    return {
        "id": flusso_id,
        "pratica_id": pratica_id,
        "template_flusso_id": template_flusso_id,
        "stato_id": 1,
        "stato_codice_interno": stato_codice_interno,
        "flusso_padre_id": None,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "sequenza": 0,
        "esito": None,
        "note_esito": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test",
    }


class FlussiApiTests(JwtMockedApiTest):

    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Scopo: Verifica GET lista flussi per pratica: envelope paginato col
    #        totale del repository (non `len(results)`), default `sequenza`.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_lista_flussi_ok(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.list_flussi_pagina.return_value = ([_mock_flusso_row()], 7)

        response = self.client.get("/api/v1/pratiche/1/flussi/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 7)
        repo.list_flussi_pagina.assert_called_once_with(
            1, search=None, order_by="sequenza", order_dir=None, limit=25, offset=0,
        )

    # Scopo: la lista passa al repository ricerca, ordinamento e pagina come
    #        arrivano; `emittente_fiscale_id` NON e' un filtro (lo legge il
    #        cancello di perimetro), quindi al repository non arriva.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_lista_flussi_parametri_lista(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.list_flussi_pagina.return_value = ([], 0)

        response = self.client.get(
            "/api/v1/pratiche/3/flussi/?search=cont&order_by=data_scadenza"
            "&order_dir=desc&limit=10&offset=20&emittente_fiscale_id=5",
        )
        self.assertEqual(response.status_code, 200)
        repo.list_flussi_pagina.assert_called_once_with(
            3, search="cont", order_by="data_scadenza", order_dir="desc",
            limit=10, offset=20,
        )
        self.assertEqual(response.json()["data"]["page"], 3)

    # Scopo: la view dichiara lista e parametro dell'emittente — e' il
    #        contratto che il tab dentro il drawer pratica usa per non essere
    #        sbarrato (422) a chi ha piu' emittenti nello scope.
    def test_lista_flussi_dichiara_il_cancello_col_parametro_emittente(self):
        from apps.pratiche.api.views import ApiPraticaFlussiList

        self.assertEqual(ApiPraticaFlussiList.lista_codice, "pratiche.flussi")
        self.assertEqual(ApiPraticaFlussiList.lista_emittente_param, "emittente_fiscale_id")

    # Scopo: il cancello di perimetro vale anche sul POST (stessa rotta della
    #        lista): l'emittente della pratica, in query, arriva al cancello
    #        come emittente esplicito. Senza, chi vede piu' emittenti prendeva
    #        un 422 creando un flusso dalla dashboard.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch("apps.core.services.perimetro_emittente.guard_lista_per_codice")
    @patch(f"{_VIEWS}.pratiche_service.crea_flusso")
    def test_post_crea_flusso_passa_l_emittente_della_query_al_cancello(self, mock_crea, mock_guard, _auth):
        mock_crea.return_value = 99

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/?emittente_fiscale_id=7",
            data=json.dumps({"template_flusso_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_guard.assert_called_once_with(
            user=ANY, lista_codice="pratiche.flussi", emittente_esplicito=7,
        )

    # Scopo: Verifica POST creazione flusso con esito positivo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_flusso")
    def test_post_crea_flusso_ok(self, mock_crea, _auth):
        mock_crea.return_value = 99

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/",
            data=json.dumps({"template_flusso_id": 10, "sequenza": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["flusso_id"], 99)

    # Scopo: Verifica GET dettaglio flusso con ownership corretta.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_dettaglio_flusso_ok(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["id"], 5)

    # Scopo: ⭐ «Dove vive questo flusso», dal solo id — l'unica rotta dei flussi
    #        NON annidata sotto la pratica. La usa chi il flusso lo nomina da
    #        fuori: il bersaglio di un errore porta `FLUSSO:<id>` e nient'altro.
    #        ⚠️ Si mocka il repository del SERVICE, non quello delle views: e'
    #        di la' che la rotta passa.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_pratica_di_flusso_ok(self, MockRepo, _auth):
        MockRepo.return_value.get_pratica_di_flusso.return_value = 185

        response = self.client.get("/api/v1/pratiche/flussi/166/pratica/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["pratica_id"], 185)

    # Scopo: ⛔ FAIL-CLOSED. La lettura e' agganciata a `pratiche.pratiche` (che
    #        ha la RLS) e non al solo `flussi` (che non ce l'ha): un flusso fuori
    #        perimetro torna None ed e' indistinguibile da uno inesistente.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_pratica_di_flusso_non_visibile(self, MockRepo, _auth):
        MockRepo.return_value.get_pratica_di_flusso.return_value = None

        response = self.client.get("/api/v1/pratiche/flussi/999/pratica/")
        self.assertEqual(response.json()["error"]["code"], "E_FLUSSO_NOT_FOUND")

    # Scopo: Verifica errore ownership quando flusso non appartiene alla pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_dettaglio_flusso_ownership_mismatch(self, MockRepo, _auth):
        repo = MockRepo.return_value
        # Flusso con pratica_id=999, ma URL chiede pratica 1.
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=999)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_FLUSSO_OWNERSHIP")

    # Scopo: Verifica POST completamento flusso con esito.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.completa_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_completamento_ok(self, MockRepo, mock_completa, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({
                "nuovo_stato": "COMPLETATO",
                "esito": "POSITIVO",
                "note_esito": "Tutto ok",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # La view inoltra l'utente acting agli handler di completamento (p_user).
        mock_completa.assert_called_once_with(
            5, esito="POSITIVO", note_esito="Tutto ok", user=ANY, meta=None,
        )

    # Scopo: CONTESTUALE — COMPLETATO da DA_ESEGUIRE instrada ad avvia_e_completa
    # (avvio + esito in un'unica azione), non a completa_flusso.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.avvia_e_completa_flusso")
    @patch(f"{_VIEWS}.pratiche_service.completa_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_completamento_contestuale(self, MockRepo, mock_completa, mock_avvia_e_completa, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(
            5, pratica_id=1, stato_codice_interno="DA_ESEGUIRE",
        )

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({
                "nuovo_stato": "COMPLETATO",
                "esito": "POSITIVO",
                "note_esito": "ok",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_avvia_e_completa.assert_called_once_with(
            5, esito="POSITIVO", note_esito="ok", user=ANY, meta=None,
        )
        mock_completa.assert_not_called()

    # Scopo: step DOMINIO (esito calcolato dal dominio) — POST COMPLETATO dal
    # percorso operatore respinto con 400 parlante (companion BE-1.3): va chiuso
    # dall'azione di dominio dedicata, non qui. completa_flusso mai chiamato.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.completa_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_dominio_respinto(self, MockRepo, mock_completa, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)
        # POSITIVO è un verdetto (passa il guard selezionabile); è la modalità
        # DOMINIO dello step a respingere il completamento manuale.
        repo.get_esito_flusso_vocabolario.return_value = (True, True)
        repo.get_flusso_esito_config.return_value = ("DOMINIO", None)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({"nuovo_stato": "COMPLETATO", "esito": "POSITIVO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_FLUSSO_VALIDATION")
        mock_completa.assert_not_called()

    # Scopo: Verifica POST avvio flusso (IN_CORSO).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.avvia_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_avvio_ok(self, MockRepo, mock_avvia, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({"nuovo_stato": "IN_CORSO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # La view passa l'utente acting (p_user §8.5); username derivato dal Mock.
        mock_avvia.assert_called_once_with(5, user=ANY)

    # Scopo: Verifica POST transizione generica via service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.cambia_stato_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_stato_flusso_generico_ok(self, MockRepo, mock_cambia, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/stato/",
            data=json.dumps({"nuovo_stato": "SOSPESO"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_cambia.assert_called_once_with(5, "SOSPESO")

    # Scopo: Verifica GET prerequisiti flusso con template.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.verifica_prerequisiti")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_prerequisiti_ok(self, MockRepo, mock_prereq, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=10)

        prerequisiti = [
            {"prerequisito_id": 1, "codice": "DOC", "descrizione": "Doc", "soddisfatto": True},
        ]
        mock_prereq.return_value = prerequisiti

        response = self.client.get("/api/v1/pratiche/1/flussi/5/prerequisiti/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        self.assertTrue(body["data"]["results"][0]["soddisfatto"])

    # Scopo: Verifica GET prerequisiti senza template → lista vuota.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_prerequisiti_senza_template(self, MockRepo, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=None)

        response = self.client.get("/api/v1/pratiche/1/flussi/5/prerequisiti/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["results"], [])

    # Scopo: Verifica GET canali flusso con template.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_canali_disponibili")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_canali_ok(self, MockRepo, mock_canali, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1, template_flusso_id=10)

        canali = [{"id": 1, "codice": "WEB_CLIENTI", "descrizione": "Web", "codice_interno": "WEB_CLIENTI"}]
        mock_canali.return_value = canali

        response = self.client.get("/api/v1/pratiche/1/flussi/5/canali/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["results"]), 1)

    # Scopo: Verifica GET regole generazione per flusso.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.get_regole_applicabili")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_regole_generazione_ok(self, MockRepo, mock_regole, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_regole.return_value = [{"id": 1, "auto": False, "descrizione": "Regola"}]

        response = self.client.get("/api/v1/pratiche/1/flussi/5/regole-generazione/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["results"]), 1)

    # Scopo: Verifica POST generazione manuale pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.genera_pratica_manuale")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_genera_pratica_ok(self, MockRepo, mock_genera, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_genera.return_value = 200

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/genera/",
            data=json.dumps({"regola_id": 3}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["pratica_id"], 200)

    # Scopo: Verifica GET pratiche generate dal flusso.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.generazione_service.get_pratiche_generate")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_get_pratiche_generate_ok(self, MockRepo, mock_generate, _auth):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        mock_generate.return_value = []

        response = self.client.get("/api/v1/pratiche/1/flussi/5/pratiche-generate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["results"], [])

    # Scopo: POST assegnazione flusso a operatore → service con flag set_*.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.assegna_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_assegnazione_flusso_ok(self, MockRepo, mock_assegna, _auth):
        MockRepo.return_value.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/assegnazione/",
            data=json.dumps({"risorsa_umana_id": 10, "unita_organizzativa_id": 3}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_assegna.assert_called_once()
        _, kwargs = mock_assegna.call_args
        self.assertEqual(kwargs["risorsa_umana_id"], 10)
        self.assertEqual(kwargs["unita_organizzativa_id"], 3)
        self.assertTrue(kwargs["set_risorsa"])
        self.assertTrue(kwargs["set_unita"])

    # Scopo: POST assegnazione su flusso di altra pratica → 400 ownership.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_assegnazione_flusso_ownership_mismatch(self, MockRepo, _auth):
        MockRepo.return_value.get_flusso.return_value = _mock_flusso_row(5, pratica_id=99)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/assegnazione/",
            data=json.dumps({"risorsa_umana_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # Scopo: POST assegnazione con la sola chiave operatore → set_unita False
    # (il reparto non viene toccato).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.assegna_flusso")
    @patch(f"{_VIEWS}.PraticheRepository")
    def test_post_assegnazione_flusso_parziale(self, MockRepo, mock_assegna, _auth):
        MockRepo.return_value.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)

        response = self.client.post(
            "/api/v1/pratiche/1/flussi/5/assegnazione/",
            data=json.dumps({"risorsa_umana_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        _, kwargs = mock_assegna.call_args
        self.assertTrue(kwargs["set_risorsa"])
        self.assertFalse(kwargs["set_unita"])

    # Scopo: GET operatori del reparto delegato al service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.list_operatori_reparto")
    def test_get_operatori_reparto_ok(self, mock_lista, _auth):
        mock_lista.return_value = [{"id": 1, "display": "Rossi Mario"}]

        response = self.client.get("/api/v1/pratiche/operatori/?unita_organizzativa_id=3")
        self.assertEqual(response.status_code, 200)
        mock_lista.assert_called_once_with(3)
        self.assertEqual(response.json()["data"]["results"][0]["display"], "Rossi Mario")

    # Scopo: Verifica che endpoint V1 flussi richieda JWT.
    def test_v1_richiede_jwt(self):
        response = self.client.get("/api/v1/pratiche/1/flussi/")
        self.assertEqual(response.status_code, 401)
