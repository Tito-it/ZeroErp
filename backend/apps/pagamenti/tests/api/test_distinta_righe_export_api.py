# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP della lista PAGINATA delle righe di una distinta e
#        del suo export (`GET /api/v1/pagamenti/distinte/<id>/righe/` e
#        `.../righe/export/`, lista `pagamenti.distinta_righe`, 2026-09-18).
#        Mock di service + UI + renderer: nessun accesso DB, gira in CI.
#
# ⭐ Perche' esiste (rilievo in-app di Tid, 2026-09-18): le righe della
#    distinta vivevano nel drawer su una `DataTable` grezza — senza
#    paginazione, senza ricarica, senza «Personalizza colonne» e senza export,
#    cioe' senza nessuna delle caratteristiche di una lista standard. Un file
#    scaricabile e' meta' della correzione; l'altra meta' e' che le colonne del
#    file siano quelle che l'operatore VEDE, e quella la fa
#    `build_export_response` leggendo la config runtime.
# ------------------------------------------------------------

"""Indice test eseguiti:
 1) test_la_rotta_export_esiste — `pagamenti-distinta-righe-export`
 2) test_export_richiede_jwt — 401 senza Authorization header
 3) test_export_formato_invalido — 400 E_UI_EXPORT_FORMAT_INVALID
 4) test_export_overflow_cap — 422 E_UI_EXPORT_LIMIT_EXCEEDED
 5) test_export_csv_envelope_ok — 200 CSV + filename dal renderer
 6) test_export_chiede_il_dataset_non_la_pagina — limit = EXPORT_MAX_ROWS + 1
 7) test_lista_passa_pagina_e_ordinamento_grezzi — `order_dir` non normalizzato
 7a) test_scartate_arriva_al_service_su_lista_ed_export — `scartate` letto uguale dalle due porte
 8) test_lista_senza_ordinamento_lascia_decidere_al_repository — None, non 'asc'
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_LIST = "apps.pagamenti.api.views.pagamenti_service.list_righe"
# Coda export estratta in `apps.ui.api.export_helpers`: i mock UI vanno
# puntati li', non al modulo della view.
_UI_SVC = "apps.ui.api.export_helpers.UiService"
_UI_REPO = "apps.ui.api.export_helpers.UiRepository"
_RENDER = "apps.ui.api.export_helpers.ListaExportService"

_URL_LISTA = "/api/v1/pagamenti/distinte/7/righe/"
_URL = "/api/v1/pagamenti/distinte/7/righe/export/"


class TestDistintaRigheExportApi(JwtMockedApiTest):
    """Smoke test della lista paginata delle righe e del suo export."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # ⚠️ La cache del throttle e' CONDIVISA da tutta la suite: senza questa
        #    riga il budget consumato dai test che girano prima arriva qui, e le
        #    richieste rispondono 429 invece del loro codice.
        cache.clear()

    def _mock_ui(self, mock_ui_svc, mock_ui_repo, mock_render_cls) -> None:
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "importo", "ordine": 1, "visibile": True}],
            "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "importo", "etichetta": "Importo",
             "campo_sorgente": "importo",
             "tipo_colonna": "informazione", "tipo_dato": "numeric",
             "esportabile": True, "ordine_default": 30},
        ]
        mock_render_cls.return_value.render.return_value = (
            b"importo\n500.00\n", "text/csv; charset=utf-8", "distinta_righe.csv",
        )
        mock_render_cls.select_colonne_visibili_da_config.return_value = []

    # Scopo: la rotta e' una SORELLA di `righe/`, non intercettata da
    #        `distinte/<id>/` (che sta dopo) ne' da `righe/da-rate/`.
    def test_la_rotta_export_esiste(self) -> None:
        self.assertEqual(
            reverse("pagamenti-distinta-righe-export", args=[7]), _URL,
        )

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
    @patch(_LIST)
    def test_export_overflow_cap(self, mock_list, _auth) -> None:
        # ⛔ Oltre il cap si RIFIUTA, non si tronca: un file troncato in
        #    silenzio e' peggio di nessun file — sembra completo.
        mock_list.return_value = {"results": [], "count": 50_000}
        resp = self.client.get(f"{_URL}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(_LIST)
    def test_export_csv_envelope_ok(
        self, mock_list, mock_ui_svc, mock_ui_repo, mock_render_cls, _auth,
    ) -> None:
        mock_list.return_value = {"results": [{"importo": "500.00"}], "count": 1}
        self._mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls)

        resp = self.client.get(f"{_URL}?formato=csv")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("distinta_righe.csv", resp["Content-Disposition"])
        self.assertEqual(resp.content, b"importo\n500.00\n")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(_LIST)
    def test_export_chiede_il_dataset_non_la_pagina(
        self, mock_list, mock_ui_svc, mock_ui_repo, mock_render_cls, _auth,
    ) -> None:
        # ⛔ Il difetto che questo test presidia: se l'export chiedesse la
        #    PAGINA (25 righe), il file conterrebbe la videata invece della
        #    distinta — e sarebbe indistinguibile da un export corretto di una
        #    distinta corta. Il `+1` e' quello che permette al guard di
        #    accorgersi dell'overflow invece di consegnare un file troncato.
        mock_list.return_value = {"results": [{"importo": "500.00"}], "count": 1}
        self._mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls)

        self.client.get(f"{_URL}?formato=csv&order_by=importo&order_dir=desc&search=rossi")

        # La ricerca a video vale anche per il file: il file segue la videata.
        mock_list.assert_called_once_with(
            7,
            search="rossi",
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by="importo",
            order_dir="desc",
            scartate=False,
        )

    # Scopo: la lista a video passa pagina e ordinamento COM'E': `order_dir`
    #        non passa dal bundle, che lo normalizzerebbe ad `asc`.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_LIST)
    def test_lista_passa_pagina_e_ordinamento_grezzi(self, mock_list, _auth) -> None:
        mock_list.return_value = {"results": [], "count": 0}
        resp = self.client.get(
            f"{_URL_LISTA}?limit=10&offset=20&order_by=data_pagamento&order_dir=desc&search=rossi"
        )
        self.assertEqual(resp.status_code, 200)
        mock_list.assert_called_once_with(
            7, search="rossi", limit=10, offset=20, order_by="data_pagamento", order_dir="desc",
            scartate=False,
        )

    # Scopo: ⭐ `scartate=true` arriva al service come `True` (BE-2, D20-c) e
    #        l'EXPORT lo legge dallo stesso parametro della lista: il file segue
    #        la videata, interruttore compreso. Assente = nascoste.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_LIST)
    def test_scartate_arriva_al_service_su_lista_ed_export(self, mock_list, _auth) -> None:
        mock_list.return_value = {"results": [], "count": 0, "scartate_count": 0}
        self.client.get(f"{_URL_LISTA}?scartate=true")
        self.assertIs(mock_list.call_args.kwargs["scartate"], True)
        mock_list.reset_mock()
        self.client.get(f"{_URL_LISTA}?scartate=false")
        self.assertIs(mock_list.call_args.kwargs["scartate"], False)

    # Scopo: senza `order_by` al service arriva `None` (non `"descrizione"`, il
    #        default del bundle, e non `"asc"`): il verso di apertura — `id
    #        DESC`, l'ultima riga digitata in cima — lo decide il repository.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_LIST)
    def test_lista_senza_ordinamento_lascia_decidere_al_repository(
        self, mock_list, _auth,
    ) -> None:
        mock_list.return_value = {"results": [], "count": 0}
        self.client.get(_URL_LISTA)
        kwargs = mock_list.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])
