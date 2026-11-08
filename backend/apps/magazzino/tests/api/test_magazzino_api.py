# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP del dominio `magazzino` — le rotte delle due famiglie
#        dalla stessa factory, la traduzione dei query param, l'`Idempotency-
#        Key` sulle scritture, l'export che chiede il DATASET, i lookup con
#        l'envelope `{"results": [...]}`. Mock del service: nessun DB.
# ------------------------------------------------------------
"""
Indice test eseguiti:
 1) RotteTests.test_le_rotte_delle_due_famiglie_esistono
 2) RotteTests.test_il_piano_esiste_solo_per_gli_inventari
 3) RotteTests.test_export_e_lista_dichiarano_lo_stesso_lista_codice
 4) AuthTests.test_lista_richiede_jwt
 5) AuthTests.test_registra_richiede_jwt
 6) ListaApiTests.test_filtri_arrivano_tradotti
 7) ListaApiTests.test_senza_ordinamento_al_service_arriva_none
 8) ListaApiTests.test_ricerca_corta_non_e_un_errore
 9) ListaApiTests.test_creazione_senza_idempotency_key_rifiutata
10) ListaApiTests.test_creazione_ok
11) DettaglioApiTests.test_patch_passa_il_payload
12) DettaglioApiTests.test_delete_richiede_idempotency_key
13) DettaglioApiTests.test_stato_e_registra
14) RigheApiTests.test_righe_lista_e_riga_crud
15) RigheApiTests.test_motivi_traduce_i_parametri
16) ExportApiTests.test_i_filtri_del_file_sono_serializzabili — 2026-09-18: una data nel filtro non e' un 500 dell'export
16-bis) ExportApiTests.test_export_chiede_il_dataset_non_la_pagina
17) LookupApiTests.test_i_lookup_tornano_l_envelope_results
18) ConsultazioneApiTests.test_disponibilita_filtri_tradotti
19) ConsultazioneApiTests.test_movimenti_filtri_tradotti
"""

import json
from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.magazzino.api import views
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

_AUTH = patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)
_SVC = "apps.magazzino.api.views.magazzino_service"
_CONS = "apps.magazzino.api.views.consultazione_service"
_KEY = {"HTTP_IDEMPOTENCY_KEY": "test-key-0001"}
_JSON = {"content_type": "application/json"}


class _Base(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()


class RotteTests(_Base):
    def test_le_rotte_delle_due_famiglie_esistono(self):
        for fam in ("inventari", "rettifiche"):
            self.assertEqual(reverse(f"magazzino-{fam}-list"), f"/api/v1/magazzino/{fam}/")
            self.assertEqual(reverse(f"magazzino-{fam}-export"), f"/api/v1/magazzino/{fam}/export/")
            self.assertEqual(reverse(f"magazzino-{fam}-detail", args=[7]), f"/api/v1/magazzino/{fam}/7/")
            self.assertEqual(reverse(f"magazzino-{fam}-stato", args=[7]), f"/api/v1/magazzino/{fam}/7/stato/")
            self.assertEqual(reverse(f"magazzino-{fam}-registra", args=[7]), f"/api/v1/magazzino/{fam}/7/registra/")
            self.assertEqual(reverse(f"magazzino-{fam}-righe", args=[7]), f"/api/v1/magazzino/{fam}/7/righe/")
            self.assertEqual(reverse(f"magazzino-{fam}-righe-export", args=[7]), f"/api/v1/magazzino/{fam}/7/righe/export/")
            self.assertEqual(reverse(f"magazzino-{fam}-riga-detail", args=[7, 3]), f"/api/v1/magazzino/{fam}/7/righe/3/")
        self.assertEqual(reverse("magazzino-righe-motivi"), "/api/v1/magazzino/righe/motivi/")
        self.assertEqual(reverse("magazzino-lotti-lookup"), "/api/v1/magazzino/lotti/lookup/")
        self.assertEqual(reverse("magazzino-assets-lookup"), "/api/v1/magazzino/assets/lookup/")
        self.assertEqual(reverse("magazzino-ubicazioni-lookup", args=[3]), "/api/v1/magazzino/magazzini/3/ubicazioni/lookup/")
        self.assertEqual(reverse("magazzino-disponibilita-list"), "/api/v1/magazzino/disponibilita/")
        self.assertEqual(reverse("magazzino-disponibilita-articoli-list"), "/api/v1/magazzino/disponibilita/articoli/")
        self.assertEqual(reverse("magazzino-disponibilita-blocchi"), "/api/v1/magazzino/disponibilita/blocchi/")
        self.assertEqual(reverse("magazzino-movimenti-list"), "/api/v1/magazzino/movimenti/")
        self.assertEqual(reverse("magazzino-movimenti-export"), "/api/v1/magazzino/movimenti/export/")

    def test_il_piano_esiste_solo_per_gli_inventari(self):
        self.assertEqual(reverse("magazzino-inventari-piano", args=[7]), "/api/v1/magazzino/inventari/7/piano/")
        self.assertEqual(reverse("magazzino-inventari-piano-export", args=[7]), "/api/v1/magazzino/inventari/7/piano/export/")
        self.assertNotIn("piano", views.VISTE_RETTIFICHE)

    # Scopo: due letterali uguali divergono al primo rename: l'export LEGGE il
    #        codice dalla lista (il presidio trasversale e' `test_export_lista_codice_pari`).
    def test_export_e_lista_dichiarano_lo_stesso_lista_codice(self):
        for viste in (views.VISTE_INVENTARI, views.VISTE_RETTIFICHE):
            self.assertEqual(viste["lista_export"].lista_codice, viste["lista"].lista_codice)
            self.assertEqual(viste["righe_export"].lista_codice, viste["righe"].lista_codice)
        self.assertEqual(views.VISTE_INVENTARI["piano_export"].lista_codice, views.VISTE_INVENTARI["piano"].lista_codice)
        self.assertEqual(views.VISTE_INVENTARI["lista"].lista_codice, "magazzino.inventari")
        self.assertEqual(views.VISTE_RETTIFICHE["righe"].lista_codice, "magazzino.rettifica_righe")
        self.assertEqual(views.ApiMovimentiExport.lista_codice, views.ApiMovimenti.lista_codice)
        self.assertEqual(views.ApiDisponibilitaExport.lista_codice, views.ApiDisponibilita.lista_codice)


class AuthTests(_Base):
    def test_lista_richiede_jwt(self):
        self.assertEqual(self.client.get("/api/v1/magazzino/inventari/").status_code, 401)

    def test_registra_richiede_jwt(self):
        self.assertEqual(
            self.client.post("/api/v1/magazzino/inventari/7/registra/", data={}, **_JSON, **_KEY).status_code, 401,
        )


class ListaApiTests(_Base):
    @_AUTH
    @patch(f"{_SVC}.list_documenti")
    def test_filtri_arrivano_tradotti(self, mocked, _auth):
        mocked.return_value = {"count": 0, "results": []}
        resp = self.client.get(
            "/api/v1/magazzino/rettifiche/?magazzino_id=3&stato=draft&data_da=2026-09-01"
            "&search=carico&limit=10&offset=20&order_by=data&order_dir=desc"
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mocked.call_args.kwargs
        self.assertEqual(mocked.call_args.args[0], "rettifiche")
        self.assertEqual(kwargs["magazzino_id"], 3)
        self.assertEqual(kwargs["stato"], "DRAFT")
        self.assertEqual(kwargs["data_da"], date(2026, 9, 1))
        self.assertIsNone(kwargs["data_a"])
        self.assertEqual(kwargs["search"], "carico")
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 20))
        self.assertEqual((kwargs["order_by"], kwargs["order_dir"]), ("data", "desc"))

    # Scopo: `order_dir` NON passa dal bundle, che lo normalizzerebbe ad `asc`.
    @_AUTH
    @patch(f"{_SVC}.list_documenti")
    def test_senza_ordinamento_al_service_arriva_none(self, mocked, _auth):
        mocked.return_value = {"count": 0, "results": []}
        self.client.get("/api/v1/magazzino/inventari/")
        kwargs = mocked.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])

    @_AUTH
    @patch(f"{_SVC}.list_documenti")
    # ⛔ Nessun 400 sotto soglia (brief-db-be-fe-ricerca-soglia-per-lista §6 a,
    #    Tid 2026-09-26): il termine arriva al service, e sotto la soglia del
    #    catalogo lo ignora il BB di ricerca.
    def test_ricerca_corta_non_e_un_errore(self, mocked, _auth):
        mocked.return_value = {"count": 0, "results": []}
        resp = self.client.get("/api/v1/magazzino/inventari/?search=ab")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mocked.call_args.kwargs["search"], "ab")

    @_AUTH
    @patch(f"{_SVC}.crea_documento")
    def test_creazione_senza_idempotency_key_rifiutata(self, mocked, _auth):
        resp = self.client.post("/api/v1/magazzino/inventari/", data={"magazzino_id": 3}, **_JSON)
        self.assertEqual(resp.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mocked.assert_not_called()

    @_AUTH
    @patch(f"{_SVC}.crea_documento")
    def test_creazione_ok(self, mocked, _auth):
        mocked.return_value = {"id": 7, "stato": "DRAFT"}
        resp = self.client.post("/api/v1/magazzino/inventari/", data={"magazzino_id": 3}, **_JSON, **_KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)
        mocked.assert_called_once_with("inventari", {"magazzino_id": 3})


class DettaglioApiTests(_Base):
    @_AUTH
    @patch(f"{_SVC}.aggiorna_documento")
    def test_patch_passa_il_payload(self, mocked, _auth):
        mocked.return_value = {"id": 7}
        resp = self.client.patch("/api/v1/magazzino/inventari/7/", data={"descrizione": "x"}, **_JSON)
        self.assertEqual(resp.status_code, 200)
        mocked.assert_called_once_with("inventari", 7, {"descrizione": "x"})

    @_AUTH
    @patch(f"{_SVC}.elimina_documento")
    def test_delete_richiede_idempotency_key(self, mocked, _auth):
        resp = self.client.delete("/api/v1/magazzino/inventari/7/")
        self.assertEqual(resp.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mocked.assert_not_called()
        mocked.return_value = {"id": 7, "eliminato": True}
        resp = self.client.delete("/api/v1/magazzino/inventari/7/", **_KEY)
        self.assertEqual(resp.status_code, 200)
        mocked.assert_called_once_with("inventari", 7)

    @_AUTH
    @patch(f"{_SVC}.registra_documento")
    @patch(f"{_SVC}.cambia_stato_documento")
    def test_stato_e_registra(self, mock_stato, mock_registra, _auth):
        mock_stato.return_value = {"id": 7, "stato": "CONFIRM"}
        resp = self.client.post("/api/v1/magazzino/rettifiche/7/stato/", data={"stato": "CONFIRM"}, **_JSON, **_KEY)
        self.assertEqual(resp.status_code, 200)
        mock_stato.assert_called_once_with("rettifiche", 7, {"stato": "CONFIRM"})
        mock_registra.return_value = {"movimenti": [], "n_movimenti": 0, "documento": {"id": 7}}
        resp = self.client.post("/api/v1/magazzino/rettifiche/7/registra/", data={}, **_JSON, **_KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["n_movimenti"], 0)
        mock_registra.assert_called_once_with("rettifiche", 7)
        self.assertEqual(views.VISTE_RETTIFICHE["registra"].post_permission, "registra_magazzino")


class RigheApiTests(_Base):
    @_AUTH
    @patch(f"{_SVC}.elimina_riga")
    @patch(f"{_SVC}.aggiorna_riga")
    @patch(f"{_SVC}.crea_riga")
    @patch(f"{_SVC}.list_righe")
    def test_righe_lista_e_riga_crud(self, mock_list, mock_crea, mock_upd, mock_del, _auth):
        mock_list.return_value = {"count": 0, "results": []}
        self.client.get("/api/v1/magazzino/inventari/7/righe/?limit=5&order_by=articolo_codice&order_dir=asc&search=vite")
        mock_list.assert_called_once_with(
            "inventari", 7, search="vite", order_by="articolo_codice", order_dir="asc", limit=5, offset=0,
        )
        mock_crea.return_value = {"id": 11}
        payload = {"articolo_id": "a", "qta_contata": "10"}
        self.client.post("/api/v1/magazzino/inventari/7/righe/", data=payload, **_JSON, **_KEY)
        mock_crea.assert_called_once_with("inventari", 7, payload)
        mock_upd.return_value = {"id": 11}
        self.client.patch("/api/v1/magazzino/inventari/7/righe/11/", data={"qta_contata": 3}, **_JSON)
        mock_upd.assert_called_once_with("inventari", 7, 11, {"qta_contata": 3})
        mock_del.return_value = {"riga_id": 11, "eliminata": True}
        self.client.delete("/api/v1/magazzino/inventari/7/righe/11/", **_KEY)
        mock_del.assert_called_once_with("inventari", 7, 11)

    @_AUTH
    @patch(f"{_SVC}.motivi_riga")
    def test_motivi_traduce_i_parametri(self, mocked, _auth):
        mocked.return_value = {"motivi": []}
        resp = self.client.get("/api/v1/magazzino/righe/motivi/?magazzino_id=3&articolo_id=abc&lotto_id=5")
        self.assertEqual(resp.status_code, 200)
        mocked.assert_called_once_with(magazzino_id=3, articolo_id="abc", lotto_id=5, asset_id=None, ubicazione_id=None)


class ExportApiTests(_Base):
    # Scopo: l'intestazione «filtri applicati» del file passa da `json.dumps`
    #        senza `default=`: una `date` la farebbe esplodere. Si passa in ISO,
    #        e i filtri vuoti non compaiono.
    def test_i_filtri_del_file_sono_serializzabili(self):
        etichette = views.filtri_label({
            "data_da": date(2026, 9, 1), "magazzino_id": 3, "search": None, "stato": "DRAFT",
        })
        self.assertEqual(etichette, {"data_da": "2026-09-01", "magazzino_id": 3, "stato": "DRAFT"})
        json.dumps(etichette)

    # Scopo: l'export chiede il DATASET (`EXPORT_MAX_ROWS + 1`), non la pagina.
    @_AUTH
    @patch("apps.ui.api.export_helpers.ListaExportService")
    @patch("apps.ui.api.export_helpers.UiRepository", autospec=True)
    @patch("apps.ui.api.export_helpers.UiService")
    @patch(f"{_CONS}.list_movimenti")
    def test_export_chiede_il_dataset_non_la_pagina(self, mock_list, mock_ui_svc, mock_ui_repo, mock_render, _auth):
        mock_list.return_value = {"results": [{"qta": "10"}], "count": 1}
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "qta", "ordine": 1, "visibile": True}], "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "qta", "etichetta": "Qta", "campo_sorgente": "qta", "tipo_colonna": "informazione",
             "tipo_dato": "numeric", "esportabile": True, "ordine_default": 1},
        ]
        mock_render.return_value.render.return_value = (b"qta\n10\n", "text/csv; charset=utf-8", "movimenti.csv")
        mock_render.select_colonne_visibili_da_config.return_value = []
        resp = self.client.get("/api/v1/magazzino/movimenti/export/?formato=csv&magazzino_id=3&order_by=qta&order_dir=desc")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_list.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (EXPORT_MAX_ROWS + 1, 0))
        self.assertEqual((kwargs["magazzino_id"], kwargs["order_by"], kwargs["order_dir"]), (3, "qta", "desc"))
        self.assertEqual(self.client.get("/api/v1/magazzino/movimenti/export/?formato=pdf").status_code, 400)


class LookupApiTests(_Base):
    # Scopo: `{"data": {"results": [...]}}`, MAI la lista nuda (api.md).
    @_AUTH
    @patch(f"{_SVC}.lookup_assets")
    @patch(f"{_SVC}.lookup_lotti")
    @patch(f"{_SVC}.lookup_ubicazioni")
    def test_i_lookup_tornano_l_envelope_results(self, mock_ub, mock_lotti, mock_assets, _auth):
        mock_ub.return_value = {"results": [{"id": 1, "codice": "UX"}]}
        resp = self.client.get("/api/v1/magazzino/magazzini/3/ubicazioni/lookup/")
        self.assertEqual(resp.json()["data"]["results"][0]["codice"], "UX")
        mock_ub.assert_called_once_with(3)
        mock_lotti.return_value = {"results": []}
        self.client.get("/api/v1/magazzino/lotti/lookup/?articolo_id=abc&search=L-")
        mock_lotti.assert_called_once_with(articolo_id="abc", search="L-")
        mock_assets.return_value = {"results": []}
        resp = self.client.get("/api/v1/magazzino/assets/lookup/?articolo_id=abc&magazzino_id=3")
        self.assertIn("results", resp.json()["data"])
        mock_assets.assert_called_once_with(articolo_id="abc", magazzino_id=3)


class ConsultazioneApiTests(_Base):
    @_AUTH
    @patch(f"{_CONS}.list_disponibilita")
    def test_disponibilita_filtri_tradotti(self, mocked, _auth):
        mocked.return_value = {"count": 0, "results": []}
        self.client.get("/api/v1/magazzino/disponibilita/?magazzino_id=3&solo_negativa=true&search=abc")
        kwargs = mocked.call_args.kwargs
        self.assertEqual((kwargs["magazzino_id"], kwargs["solo_negativa"], kwargs["solo_con_giacenza"], kwargs["search"]),
                         (3, True, False, "abc"))
        resp = self.client.get("/api/v1/magazzino/disponibilita/?solo_negativa=banana")
        self.assertEqual(resp.status_code, 400)

    @_AUTH
    @patch(f"{_CONS}.list_movimenti")
    def test_movimenti_filtri_tradotti(self, mocked, _auth):
        mocked.return_value = {"count": 0, "results": []}
        self.client.get(
            "/api/v1/magazzino/movimenti/?inventario_id=7&sorgente_tipo=inventario&data_a=2026-09-30&causale_id=2"
        )
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["inventario_id"], 7)
        self.assertIsNone(kwargs["rettifica_id"])
        self.assertEqual(kwargs["sorgente_codice_interno"], "INVENTARIO")
        self.assertEqual(kwargs["data_a"], date(2026, 9, 30))
        self.assertEqual(kwargs["causale_id"], 2)
