# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /vendite/giornale/ (+ export/) — il giornale TRASVERSALE degli
#        eventi (pezzo G del piano BE/FE dell'osservabilita', 2026-09-19).
#        Repository mockato, nessun DB: la PORTA, la normalizzazione dei
#        filtri, i vocabolari (400 fuori vocabolario) e l'envelope.
#
# Indice test:
#   1. senza JWT -> 401
#   2. porta `DomainAPIView` area vendite, rotte, e l'export legge il
#      `lista_codice` dalla lista
#   3. filtri normalizzati: csv -> liste MAIUSCOLE, date ISO, filo uuid,
#      `solo_vive` bool; default `gravita=['ERROR']`, `order_by=quando`,
#      `order_dir` grezzo (None)
#   4. `gravita` fuori vocabolario -> 400 (non «zero righe»)
#   5. `registro` fuori vocabolario -> 400: il vocabolario e' LETTO dal
#      catalogo (`registri_giornale_ammessi`), e senza filtro non si legge
#   6. `filo` non uuid -> 400; data malformata -> 400
#   7. envelope: paginato standard + `ritirate_count`; con `solo_vive=0` il
#      totale include le ritirate e `ritirate_count` e' 0
# ------------------------------------------------------------
from datetime import date
from unittest.mock import Mock, patch

from django.test import Client
from django.urls import resolve

from apps.core.api.base_views import DomainAPIView
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.vendite.api.views import ApiGiornale, ApiGiornaleExport

_AUTH = patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)
_REPO = "apps.vendite.services.vendite_service.VenditeRepository"
_URL = "/api/v1/vendite/giornale/"
_FILO = "123e4567-e89b-12d3-a456-426614174000"
# Il catalogo, come lo risponderebbe `registri_giornale_ammessi` sul DB vero.
_REGISTRI = frozenset({"EVENT_LOG", "LOTTO_LOG", "TASK_RUN", "FATTURA_LOG"})


def _riga(**override) -> dict:
    base = {
        "riga_key": "EVENT_LOG:1", "registro": "EVENT_LOG", "quando": "2026-09-19T10:00:00+02:00",
        "gravita": "ERROR", "cosa": "LOTTO_ERRORE", "tx_id": _FILO, "correlation_id": None,
        "auth_user_id": None, "user_insert": "app", "ritirata": False,
        "entity_type": "LOTTO", "entity_id": 42, "etichetta_key": None, "entita_display": "LTF-0000042",
    }
    return {**base, **override}


class GiornaleTrasversaleApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)

    # 2.
    def test_porta_e_rotte(self) -> None:
        self.assertTrue(issubclass(ApiGiornale, DomainAPIView))
        self.assertEqual(ApiGiornale.area_funzionale, "vendite")
        self.assertEqual(ApiGiornale.lista_codice, "vendite.giornale")
        self.assertIs(ApiGiornaleExport.lista_codice, ApiGiornale.lista_codice)
        self.assertIs(resolve(_URL).func.view_class, ApiGiornale)
        self.assertIs(resolve(_URL + "export/").func.view_class, ApiGiornaleExport)

    # 3.
    # Il controllo del vocabolario di `entity_type` (BB
    # `richiedi_codice_a_vocabolario`) legge il DB: qui lo si sostituisce
    # restituendo il valore, e si verifica che riceva quello NORMALIZZATO.
    @_AUTH
    @patch("apps.vendite.services.vendite_service.richiedi_codice_a_vocabolario",
           side_effect=lambda tabella, colonna, valore, **_k: valore)
    @patch(_REPO)
    def test_filtri_normalizzati(self, repo_cls, vocab, _auth) -> None:
        repo_cls.return_value.list_giornale_trasversale.return_value = ([], 0, 0, 0)
        repo_cls.return_value.registri_giornale_ammessi.return_value = _REGISTRI
        resp = self.client.get(_URL, {
            "gravita": "error, warn", "registro": "event_log,task_run",
            "entity_type": "lotto", "data_da": "2026-09-01", "data_a": "2026-09-19",
            "filo": _FILO, "solo_vive": "false", "limit": "10", "offset": "20",
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        repo_cls.return_value.list_giornale_trasversale.assert_called_once_with(
            gravita=["ERROR", "WARN"], registri=["EVENT_LOG", "TASK_RUN"],
            entity_type="LOTTO", data_da=date(2026, 9, 1), data_a=date(2026, 9, 19),
            filo=_FILO, solo_vive=False, limit=10, offset=20,
            # Verso assente = `None`: il DESC lo decide il repository
            # (`sql_order_direction(default_desc=True)`), sede unica del
            # default per i tre lettori del giornale (2026-09-27).
            sort_by="quando", sort_dir=None,
        )
        self.assertEqual(resp.json()["data"]["page"], 3)
        self.assertEqual(vocab.call_args.args, ("config.tipi_entita", "codice", "LOTTO"))

    @_AUTH
    @patch(_REPO)
    def test_default_gravita_error_e_ordine_quando(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_giornale_trasversale.return_value = ([], 0, 0, 0)
        self.assertEqual(self.client.get(_URL).status_code, 200)
        chiamata = repo_cls.return_value.list_giornale_trasversale.call_args.kwargs
        self.assertEqual(chiamata["gravita"], ["ERROR"])
        self.assertIsNone(chiamata["registri"])
        self.assertTrue(chiamata["solo_vive"])
        # Senza il filtro `registro` il catalogo non si interroga: e' il costo
        # dichiarato della lettura dal catalogo (una SELECT solo quando serve).
        repo_cls.return_value.registri_giornale_ammessi.assert_not_called()
        self.assertEqual((chiamata["sort_by"], chiamata["sort_dir"]), ("quando", None))

    # 4-5. Vocabolari: un valore ignoto e' un 400, mai «zero righe».
    @_AUTH
    @patch(_REPO)
    def test_gravita_fuori_vocabolario_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"gravita": "GRAVE"})
        self.assertEqual(resp.status_code, 400, resp.content)
        # Filtro di query: niente `fields` (non e' un input del form, Tid 2026-10-20).
        self.assertNotIn("fields", resp.json()["error"])
        repo_cls.return_value.list_giornale_trasversale.assert_not_called()

    @_AUTH
    @patch(_REPO)
    def test_registro_fuori_vocabolario_400(self, repo_cls, _auth) -> None:
        # ⭐ Il vocabolario e' quello che il CATALOGO risponde, non una costante:
        #    un registro che il catalogo non conosce e' un 400, e uno che conosce
        #    passa anche se questo file non l'ha mai sentito nominare.
        repo_cls.return_value.registri_giornale_ammessi.return_value = _REGISTRI
        resp = self.client.get(_URL, {"registro": "PRATICHE"})
        self.assertEqual(resp.status_code, 400, resp.content)
        # Filtro di query: niente `fields` (non e' un input del form, Tid 2026-10-20).
        self.assertNotIn("fields", resp.json()["error"])
        repo_cls.return_value.list_giornale_trasversale.assert_not_called()
        repo_cls.return_value.registri_giornale_ammessi.return_value = _REGISTRI | {"PRATICHE"}
        repo_cls.return_value.list_giornale_trasversale.return_value = ([], 0, 0, 0)
        self.assertEqual(self.client.get(_URL, {"registro": "PRATICHE"}).status_code, 200)

    # 6.
    @_AUTH
    @patch(_REPO)
    def test_filo_non_uuid_e_data_malformata_400(self, repo_cls, _auth) -> None:
        self.assertEqual(self.client.get(_URL, {"filo": "x"}).status_code, 400)
        self.assertEqual(self.client.get(_URL, {"data_a": "19/09/2026"}).status_code, 400)
        repo_cls.return_value.list_giornale_trasversale.assert_not_called()

    # 7.
    @_AUTH
    @patch(_REPO)
    def test_envelope_e_ritirate_count(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_giornale_trasversale.return_value = ([_riga()], 5, 2, 0)
        data = self.client.get(_URL).json()["data"]
        self.assertEqual({"count", "page", "page_size", "total_pages", "ritirate_count", "results"}, set(data))
        self.assertEqual((data["count"], data["ritirate_count"]), (5, 2))
        self.assertEqual(data["results"][0]["entita_display"], "LTF-0000042")
        # ⛔ Niente context/payload nella lista trasversale (vincolo del Passo A).
        self.assertNotIn("payload", data["results"][0])
        self.assertNotIn("context", data["results"][0])
        # Con le ritirate incluse il totale le conta e il contatore tace.
        data = self.client.get(_URL, {"solo_vive": "false"}).json()["data"]
        self.assertEqual((data["count"], data["ritirate_count"]), (7, 0))
