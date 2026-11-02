# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP dell'export della lista TITOLI IVA DI UN SOGGETTO
#        (`GET /api/v1/anagrafiche/soggetti/<id>/titoli-iva/export/`, DEF-1).
#        Mock di service + UI + renderer: nessun accesso DB, gira in CI.
#
# ⭐ Perche' esiste questo endpoint (2026-09-02): la lista viveva in un drawer
#    senza export, senza personalizzazione colonne e senza paginazione — cioe'
#    fuori dallo standard delle altre quaranta liste, ma senza che niente lo
#    dicesse. Un file scaricabile e' meta' della correzione; l'altra meta' e'
#    che le colonne del file siano quelle che l'operatore VEDE, e quella la fa
#    `build_export_response` leggendo la config runtime.
# ------------------------------------------------------------

"""Indice test eseguiti:
 1) test_export_richiede_jwt — 401 senza Authorization header
 2) test_export_formato_invalido — 400 E_UI_EXPORT_FORMAT_INVALID
 3) test_export_overflow_cap — 422 E_UI_EXPORT_LIMIT_EXCEEDED
 4) test_export_csv_envelope_ok — 200 CSV + filename dal renderer
 5) test_export_chiede_il_dataset_non_la_pagina — limit = EXPORT_MAX_ROWS + 1
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_titoli_iva.TitoliIvaService"
# Coda export estratta in `apps.ui.api.export_helpers`: i mock UI vanno
# puntati li', non al modulo della view.
_UI_SVC = "apps.ui.api.export_helpers.UiService"
_UI_REPO = "apps.ui.api.export_helpers.UiRepository"
_RENDER = "apps.ui.api.export_helpers.ListaExportService"

_SOGG = "11111111-1111-1111-1111-111111111111"
_URL = f"/api/v1/anagrafiche/soggetti/{_SOGG}/titoli-iva/export/"


class TestSoggettoTitoliIvaExportApi(JwtMockedApiTest):
    """Smoke test dell'endpoint di export dei titoli IVA del soggetto."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza questa
        #    riga il budget consumato dai test che girano prima arriva qui, e le
        #    richieste rispondono 429 invece del loro codice.
        cache.clear()

    def _mock_ui(self, mock_ui_svc, mock_ui_repo, mock_render_cls) -> None:
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "tipo", "ordine": 1, "visibile": True}],
            "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "tipo", "etichetta": "Tipo",
             "campo_sorgente": "tipo_descrizione",
             "tipo_colonna": "identificatore", "tipo_dato": "text",
             "esportabile": True, "ordine_default": 10},
        ]
        mock_render_cls.return_value.render.return_value = (
            b"tipo\nPlafond\n", "text/csv; charset=utf-8", "titoli_iva.csv",
        )
        mock_render_cls.select_colonne_visibili_da_config.return_value = []

    def test_export_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(f"{_URL}?formato=csv").status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        # Guard PRIMA di toccare il service: su formato invalido non si esegue
        # nessuna query.
        resp = self.client.get(f"{_URL}?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_export_overflow_cap(self, mock_svc_cls, _auth) -> None:
        # ⛔ Oltre il cap si RIFIUTA, non si tronca: un file troncato in
        #    silenzio e' peggio di nessun file — sembra completo.
        mock_svc_cls.return_value.list_titoli_soggetto.return_value = {
            "results": [], "count": 50_000,
        }
        resp = self.client.get(f"{_URL}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(_SVC)
    def test_export_csv_envelope_ok(
        self, mock_svc_cls, mock_ui_svc, mock_ui_repo, mock_render_cls, _auth,
    ) -> None:
        mock_svc_cls.return_value.list_titoli_soggetto.return_value = {
            "results": [{"tipo_descrizione": "Plafond"}], "count": 1,
        }
        self._mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls)

        resp = self.client.get(f"{_URL}?formato=csv")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("titoli_iva.csv", resp["Content-Disposition"])
        self.assertEqual(resp.content, b"tipo\nPlafond\n")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(_SVC)
    def test_export_chiede_il_dataset_non_la_pagina(
        self, mock_svc_cls, mock_ui_svc, mock_ui_repo, mock_render_cls, _auth,
    ) -> None:
        # ⛔ Il difetto che questo test presidia: se l'export chiedesse la
        #    PAGINA (25 righe), il file conterrebbe la videata invece della
        #    lista — e sarebbe indistinguibile da un export corretto di una
        #    lista corta. Il `+1` e' quello che permette al guard di accorgersi
        #    dell'overflow invece di consegnare un file troncato.
        mock_svc_cls.return_value.list_titoli_soggetto.return_value = {
            "results": [{"tipo_descrizione": "Plafond"}], "count": 1,
        }
        self._mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls)

        self.client.get(f"{_URL}?formato=csv&order_by=iva_codice&order_dir=desc")

        mock_svc_cls.return_value.list_titoli_soggetto.assert_called_once_with(
            _SOGG,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by="iva_codice",
            order_dir="desc",
        )
