# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP endpoint export contratti DEF-1/DEF-8
#        (`GET /api/v1/vendite/contratti/export/`). Mock di service + UI +
#        renderer, nessun accesso DB (CI-compatible). Verifica envelope,
#        auth obbligatoria, validazione formato, overflow cap.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_export_richiede_jwt — 401 senza Authorization header
 2) test_export_formato_invalido — 400 E_UI_EXPORT_FORMAT_INVALID
 3) test_export_overflow_cap — 422 E_UI_EXPORT_LIMIT_EXCEEDED su >10k righe
 4) test_export_csv_envelope_ok — 200 con Content-Type csv + filename
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_contratti.ContrattiService"
_SCOPE = "apps.vendite.api.views_contratti.get_scope_user_id"
# Coda export estratta in apps.ui.api.export_helpers.build_export_response
# (regola del 2, 2026-06-02): i mock UI vanno puntati li', non al modulo view.
_UI_SVC = "apps.ui.api.export_helpers.UiService"
_UI_REPO = "apps.ui.api.export_helpers.UiRepository"
_RENDER = "apps.ui.api.export_helpers.ListaExportService"

_URL = "/api/v1/vendite/contratti/export/"


class TestContrattiExportApi(JwtMockedApiTest):
    """Smoke test endpoint export contratti."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_export_richiede_jwt(self) -> None:
        resp = self.client.get(f"{_URL}?formato=csv")
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    def test_export_formato_invalido(self, _auth) -> None:
        # `formato=pdf` non e' ammesso: guard prima di toccare il service.
        resp = self.client.get(f"{_URL}?formato=pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_FORMAT_INVALID",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(_SVC)
    def test_export_overflow_cap(self, mock_svc_cls, _scope, _auth) -> None:
        # `total` > EXPORT_MAX_ROWS -> 422 con codice parlante, niente render.
        mock_svc_cls.return_value.list_contratti.return_value = ([], 50_000)
        resp = self.client.get(f"{_URL}?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json()["error"]["code"], "E_UI_EXPORT_LIMIT_EXCEEDED",
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=None)
    @patch(_RENDER)
    @patch(_UI_REPO, autospec=True)
    @patch(_UI_SVC)
    @patch(_SVC)
    def test_export_csv_envelope_ok(
        self, mock_svc_cls, mock_ui_svc, mock_ui_repo, mock_render_cls,
        _scope, _auth,
    ) -> None:
        # Path felice: 200 con Content-Type CSV e Content-Disposition.
        mock_svc_cls.return_value.list_contratti.return_value = (
            [{"numero": "CNT0001", "ragione_sociale_completa": "Rossi SRL"}], 1,
        )
        mock_svc_cls.return_value.resolve_filtri_export_label.return_value = {}
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "numero", "ordine": 1, "visibile": True}],
            "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "numero", "etichetta": "Numero", "campo_sorgente": "numero",
             "tipo_colonna": "identificatore", "tipo_dato": "text",
             "esportabile": True, "ordine_default": 10},
        ]
        mock_render_cls.return_value.render.return_value = (
            b"numero\nCNT0001\n",
            "text/csv; charset=utf-8",
            "contratti.csv",
        )
        mock_render_cls.select_colonne_visibili_da_config.return_value = []

        resp = self.client.get(f"{_URL}?formato=csv")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("contratti.csv", resp["Content-Disposition"])
        self.assertEqual(resp.content, b"numero\nCNT0001\n")
        # Regressione bug cap-200: l'export deve alzare il cap oltre 200
        # (max_limit), altrimenti il file uscirebbe troncato in silenzio.
        self.assertGreater(
            mock_svc_cls.return_value.list_contratti.call_args.kwargs["max_limit"],
            200,
        )
