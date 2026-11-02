# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint export delle due code resi DEF-1
#        (`GET /api/v1/vendite/resi/da-accreditare/export/` e
#        `.../da-riconsegnare/export/`). Mock di service + UI + renderer,
#        nessun accesso DB (CI-compatible). Verifica auth, validazione
#        formato, overflow cap, envelope csv, e passaggio sort/search.
# ------------------------------------------------------------

"""
Indice test eseguiti (x2 code):
 1) test_export_richiede_jwt        — 401 senza Authorization header
 2) test_export_formato_invalido    — 400 E_UI_EXPORT_FORMAT_INVALID
 3) test_export_overflow_cap        — 422 E_UI_EXPORT_LIMIT_EXCEEDED su >10k righe
 4) test_export_csv_envelope_ok     — 200 Content-Type csv + filename + sort/search
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.services.resi_service"
_SCOPE = "apps.vendite.api.views_resi.get_scope_user_id"
# Coda export estratta in apps.ui.api.export_helpers.build_export_response:
# i mock UI vanno puntati li', non al modulo view (mirror test contratti).
_UI_SVC = "apps.ui.api.export_helpers.UiService"
_UI_REPO = "apps.ui.api.export_helpers.UiRepository"
_RENDER = "apps.ui.api.export_helpers.ListaExportService"

_URL_LISTA = "/api/v1/vendite/resi/export/"
_URL_ACCR = "/api/v1/vendite/resi/da-accreditare/export/"
_URL_RIC = "/api/v1/vendite/resi/da-riconsegnare/export/"


def _mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls, *, filename: str) -> None:
    """Configura i mock UI/renderer per il path felice (comune alle 2 code)."""
    mock_ui_svc.return_value.get_lista_config.return_value = {
        "colonne": [{"codice": "reso_numero", "ordine": 1, "visibile": True}],
        "pagina_dimensione": 25,
    }
    mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
        {"codice": "reso_numero", "etichetta": "Numero",
         "campo_sorgente": "reso_numero", "tipo_colonna": "identificatore",
         "tipo_dato": "string", "esportabile": True, "ordine_default": 10},
    ]
    mock_render_cls.return_value.render.return_value = (
        b"reso_numero\nRESO0001\n", "text/csv; charset=utf-8", filename,
    )
    mock_render_cls.select_colonne_visibili_da_config.return_value = []


class TestResiCodeExportApi(JwtMockedApiTest):
    """Smoke test endpoint export code resi (accreditare / ri-consegnare)."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # --- Auth ---

    def test_export_accreditare_richiede_jwt(self) -> None:
        resp = self.client.get(f"{_URL_ACCR}?formato=csv")
        self.assertEqual(resp.status_code, 401)

    def test_export_riconsegnare_richiede_jwt(self) -> None:
        resp = self.client.get(f"{_URL_RIC}?formato=csv")
        self.assertEqual(resp.status_code, 401)

    # --- Formato invalido (guard prima di toccare il service) ---

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_accreditare_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_URL_ACCR}?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_riconsegnare_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_URL_RIC}?formato=xml")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    # --- Overflow cap: total > EXPORT_MAX_ROWS -> 422, niente render ---

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(f"{_SVC}.list_da_accreditare")
    def test_export_accreditare_overflow_cap(self, mock_coda, _scope, _auth) -> None:
        mock_coda.return_value = ([], 50_000)
        resp = self.client.get(f"{_URL_ACCR}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(f"{_SVC}.list_da_riconsegnare")
    def test_export_riconsegnare_overflow_cap(self, mock_coda, _scope, _auth) -> None:
        mock_coda.return_value = ([], 50_000)
        resp = self.client.get(f"{_URL_RIC}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    # --- Path felice: 200 CSV + filename; sort/search propagati + no-truncate ---

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(f"{_SVC}.list_da_accreditare")
    # La soglia della ricerca e' del catalogo (DB): qui e' un contorno finto.
    @catalogo_ricerca_finto(())
    def test_export_accreditare_csv_envelope_ok(
        self, mock_coda, mock_ui_svc, mock_ui_repo, mock_render_cls,
        _scope, _auth,
    ) -> None:
        mock_coda.return_value = (
            [{"reso_numero": "RESO0001", "descrizione": "Art X"}], 1,
        )
        _mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls,
                 filename="resi_da_accreditare.csv")

        resp = self.client.get(
            f"{_URL_ACCR}?formato=csv&search=rossi&order_by=descrizione&order_dir=asc",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("resi_da_accreditare.csv", resp["Content-Disposition"])
        # Sort/search propagati al service e fetch export senza troncamento
        # (max_limit alza il cap oltre 200: il file non e' capato a 200 righe).
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["search"], "rossi")
        self.assertEqual(kwargs["order_by"], "descrizione")
        self.assertEqual(kwargs["order_dir"], "asc")
        self.assertGreater(kwargs["max_limit"], 200)
        self.assertGreater(kwargs["limit"], 200)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(f"{_SVC}.list_da_riconsegnare")
    def test_export_riconsegnare_csv_envelope_ok(
        self, mock_coda, mock_ui_svc, mock_ui_repo, mock_render_cls,
        _scope, _auth,
    ) -> None:
        mock_coda.return_value = (
            [{"reso_numero": "RESO0002", "stato_riconsegna": "PARZIALE"}], 1,
        )
        _mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls,
                 filename="resi_da_riconsegnare.csv")

        resp = self.client.get(f"{_URL_RIC}?formato=csv&order_by=qta_residua")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("resi_da_riconsegnare.csv", resp["Content-Disposition"])
        kwargs = mock_coda.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "qta_residua")
        self.assertGreater(kwargs["max_limit"], 200)


class TestResiListaExportApi(JwtMockedApiTest):
    """Smoke test endpoint export lista resi (`/vendite/resi/export/`)."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_export_richiede_jwt(self) -> None:
        resp = self.client.get(f"{_URL_LISTA}?formato=csv")
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        resp = self.client.get(f"{_URL_LISTA}?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(f"{_SVC}.list_resi_rows")
    def test_export_overflow_cap(self, mock_list, _scope, _auth) -> None:
        mock_list.return_value = ([], 50_000)
        resp = self.client.get(f"{_URL_LISTA}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(_RENDER)
    @patch(_UI_REPO)
    @patch(_UI_SVC)
    @patch(f"{_SVC}.list_resi_rows")
    # La soglia della ricerca e' del catalogo (DB): qui e' un contorno finto.
    @catalogo_ricerca_finto(())
    def test_export_csv_envelope_ok(
        self, mock_list, mock_ui_svc, mock_ui_repo, mock_render_cls,
        _scope, _auth,
    ) -> None:
        mock_list.return_value = ([{"numero": "RESO0001"}], 1)
        _mock_ui(mock_ui_svc, mock_ui_repo, mock_render_cls, filename="resi.csv")

        resp = self.client.get(
            f"{_URL_LISTA}?formato=csv&search=rossi"
            "&stato_codice_interno=CONFERMATO&order_by=numero&order_dir=asc",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("resi.csv", resp["Content-Disposition"])
        # Filtri/sort propagati + fetch export senza troncamento (max_limit>200).
        kwargs = mock_list.call_args.kwargs
        self.assertEqual(kwargs["search"], "rossi")
        self.assertEqual(kwargs["stato_codice"], "CONFERMATO")
        self.assertEqual(kwargs["order_by"], "numero")
        self.assertGreater(kwargs["max_limit"], 200)
