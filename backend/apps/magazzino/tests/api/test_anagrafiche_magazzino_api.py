# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP delle tre ANAGRAFICHE di magazzino — le rotte (con
#        `export/` e `lookup/` PRIMA dei pattern `<int>`), la traduzione dei
#        query param, l'`Idempotency-Key` sulle POST, il PATCH che passa il
#        payload, l'export che chiede il DATASET. Mock del service: nessun DB.
# ------------------------------------------------------------
"""
Indice test eseguiti:
 1) RotteTests.test_le_rotte_delle_tre_anagrafiche_esistono
 2) RotteTests.test_export_e_lookup_non_sono_intercettati_dal_dettaglio
 3) MagazziniApiTests.test_filtri_arrivano_tradotti
 4) MagazziniApiTests.test_creazione_richiede_idempotency_key
 5) MagazziniApiTests.test_creazione_e_patch_passano_il_payload
 6) UbicazioniApiTests.test_lista_e_crea_portano_il_magazzino_del_path
 7) LottiApiTests.test_articolo_id_viaggia_grezzo_e_il_service_lo_valida
 8) ExportApiTests.test_export_chiede_il_dataset_non_la_pagina
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto

_AUTH = patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)
_SVC = "apps.magazzino.api.views_anagrafiche.svc"
_KEY = {"HTTP_IDEMPOTENCY_KEY": "test-key-0001"}
_JSON = {"content_type": "application/json"}
_VUOTA = {"count": 0, "results": []}


class _Base(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()


class RotteTests(_Base):
    # 1.
    def test_le_rotte_delle_tre_anagrafiche_esistono(self):
        self.assertEqual(reverse("magazzino-magazzini-list"), "/api/v1/magazzino/magazzini/")
        self.assertEqual(reverse("magazzino-magazzini-export"), "/api/v1/magazzino/magazzini/export/")
        self.assertEqual(reverse("magazzino-magazzini-detail", args=[3]), "/api/v1/magazzino/magazzini/3/")
        self.assertEqual(reverse("magazzino-ubicazioni-list", args=[3]), "/api/v1/magazzino/magazzini/3/ubicazioni/")
        self.assertEqual(reverse("magazzino-ubicazioni-export", args=[3]), "/api/v1/magazzino/magazzini/3/ubicazioni/export/")
        self.assertEqual(reverse("magazzino-ubicazioni-detail", args=[3, 9]), "/api/v1/magazzino/magazzini/3/ubicazioni/9/")
        self.assertEqual(reverse("magazzino-lotti-list"), "/api/v1/magazzino/lotti/")
        self.assertEqual(reverse("magazzino-lotti-export"), "/api/v1/magazzino/lotti/export/")
        self.assertEqual(reverse("magazzino-lotti-detail", args=[5]), "/api/v1/magazzino/lotti/5/")

    # 2. `export/` e `lookup/` NON sono interi: un ordine sbagliato delle rotte
    #    li manderebbe al pattern `<int>` del dettaglio. Si legge dal resolver.
    def test_export_e_lookup_non_sono_intercettati_dal_dettaglio(self):
        from django.urls import resolve
        self.assertEqual(resolve("/api/v1/magazzino/lotti/export/").url_name, "magazzino-lotti-export")
        self.assertEqual(resolve("/api/v1/magazzino/lotti/lookup/").url_name, "magazzino-lotti-lookup")
        self.assertEqual(resolve("/api/v1/magazzino/magazzini/export/").url_name, "magazzino-magazzini-export")
        self.assertEqual(resolve("/api/v1/magazzino/magazzini/3/ubicazioni/export/").url_name, "magazzino-ubicazioni-export")
        self.assertEqual(resolve("/api/v1/magazzino/magazzini/3/ubicazioni/lookup/").url_name, "magazzino-ubicazioni-lookup")
        self.assertEqual(resolve("/api/v1/magazzino/magazzini/3/ubicazioni/9/").url_name, "magazzino-ubicazioni-detail")


class MagazziniApiTests(_Base):
    # 3.
    @_AUTH
    @patch(f"{_SVC}.list_magazzini", return_value=_VUOTA)
    def test_filtri_arrivano_tradotti(self, mocked, _auth):
        resp = self.client.get(
            "/api/v1/magazzino/magazzini/?search=depo&attivo=false&limit=10&offset=20&order_by=codice&order_dir=desc"
        )
        self.assertEqual(resp.status_code, 200)
        kw = mocked.call_args.kwargs
        self.assertEqual(kw["search"], "depo")
        self.assertIs(kw["attivo"], False)
        self.assertEqual((kw["limit"], kw["offset"]), (10, 20))
        self.assertEqual((kw["order_by"], kw["order_dir"]), ("codice", "desc"))
        # Senza filtri: `attivo` assente = None (tutti), ordinamento None.
        self.client.get("/api/v1/magazzino/magazzini/")
        kw = mocked.call_args.kwargs
        self.assertIsNone(kw["attivo"])
        self.assertIsNone(kw["order_by"])

    # 4.
    @_AUTH
    @patch(f"{_SVC}.crea_magazzino")
    def test_creazione_richiede_idempotency_key(self, mocked, _auth):
        resp = self.client.post("/api/v1/magazzino/magazzini/", data={"codice": "X"}, **_JSON)
        self.assertEqual(resp.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mocked.assert_not_called()

    # 5.
    @_AUTH
    @patch(f"{_SVC}.aggiorna_magazzino", return_value={"id": 7, "attivo": False})
    @patch(f"{_SVC}.crea_magazzino", return_value={"id": 7})
    def test_creazione_e_patch_passano_il_payload(self, mock_crea, mock_upd, _auth):
        payload = {"codice": "X", "descrizione": "d", "indirizzo_dettaglio_id": 4}
        resp = self.client.post("/api/v1/magazzino/magazzini/", data=payload, **_JSON, **_KEY)
        self.assertEqual(resp.status_code, 200)
        mock_crea.assert_called_once_with(payload)
        resp = self.client.patch("/api/v1/magazzino/magazzini/7/", data={"attivo": False}, **_JSON)
        self.assertEqual(resp.status_code, 200)
        mock_upd.assert_called_once_with(7, {"attivo": False})


class UbicazioniApiTests(_Base):
    # 6.
    @_AUTH
    @patch(f"{_SVC}.crea_ubicazione", return_value={"id": 1})
    @patch(f"{_SVC}.list_ubicazioni", return_value=_VUOTA)
    def test_lista_e_crea_portano_il_magazzino_del_path(self, mock_list, mock_crea, _auth):
        resp = self.client.get("/api/v1/magazzino/magazzini/3/ubicazioni/?parent_id=8&attivo=true")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_list.call_args.args[0], 3)
        self.assertEqual(mock_list.call_args.kwargs["parent_id"], 8)
        self.assertIs(mock_list.call_args.kwargs["attivo"], True)
        resp = self.client.post("/api/v1/magazzino/magazzini/3/ubicazioni/", data={"codice": "A", "tipo_id": 2}, **_JSON, **_KEY)
        self.assertEqual(resp.status_code, 200)
        mock_crea.assert_called_once_with(3, {"codice": "A", "tipo_id": 2})


class LottiApiTests(_Base):
    # 7. `articolo_id` non si valida nella view: lo fa il service (uuid, 400
    #    col campo), e qui arriva GREZZO — anche assente.
    @_AUTH
    @patch(f"{_SVC}.list_lotti", return_value=_VUOTA)
    def test_articolo_id_viaggia_grezzo_e_il_service_lo_valida(self, mocked, _auth):
        self.client.get("/api/v1/magazzino/lotti/?articolo_id=abc&search=L-0")
        kw = mocked.call_args.kwargs
        self.assertEqual((kw["articolo_id"], kw["search"]), ("abc", "L-0"))
        self.client.get("/api/v1/magazzino/lotti/")
        self.assertIsNone(mocked.call_args.kwargs["articolo_id"])


class ExportApiTests(_Base):
    # 8.
    @_AUTH
    @patch("apps.ui.api.export_helpers.ListaExportService")
    @patch("apps.ui.api.export_helpers.UiRepository")
    @patch("apps.ui.api.export_helpers.UiService")
    @patch(f"{_SVC}.list_magazzini")
    # La soglia della ricerca e' del catalogo (DB): qui e' un contorno finto.
    @catalogo_ricerca_finto(())
    def test_export_chiede_il_dataset_non_la_pagina(self, mock_list, mock_ui_svc, mock_ui_repo, mock_render, _auth):
        mock_list.return_value = {"results": [{"codice": "A"}], "count": 1}
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "codice", "ordine": 1, "visibile": True}], "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "codice", "etichetta": "Codice", "campo_sorgente": "codice", "tipo_colonna": "identificatore",
             "tipo_dato": "string", "esportabile": True, "ordine_default": 1},
        ]
        mock_render.return_value.render.return_value = (b"codice\nA\n", "text/csv; charset=utf-8", "magazzini.csv")
        mock_render.select_colonne_visibili_da_config.return_value = []
        resp = self.client.get("/api/v1/magazzino/magazzini/export/?formato=csv&search=depo&order_by=codice&order_dir=desc")
        self.assertEqual(resp.status_code, 200)
        kw = mock_list.call_args.kwargs
        self.assertEqual((kw["limit"], kw["offset"]), (EXPORT_MAX_ROWS + 1, 0))
        self.assertEqual((kw["search"], kw["order_by"], kw["order_dir"]), ("depo", "codice", "desc"))
        self.assertEqual(self.client.get("/api/v1/magazzino/magazzini/export/?formato=pdf").status_code, 400)
