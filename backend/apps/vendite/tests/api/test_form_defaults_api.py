# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test API form-defaults vendite (Fase 2.B3-B5).
#        Mock JWT + service, niente DB. Verifica routing, envelope,
#        propagazione query params (billing_account_id) e auth.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_contratto_form_defaults_no_ba         — 200, payload con default_data
 2) test_contratto_form_defaults_con_ba        — 200, ba_id propagato al service
 3) test_contratto_form_defaults_richiede_jwt  — 401 senza Authorization
 4) test_preventivo_form_defaults_no_ba        — 200, default_validita_al
 5) test_preventivo_form_defaults_con_ba       — 200, ba_id propagato al service
 6) test_versione_new_defaults_ok               — 200, listino_id propagato
 7) test_versione_clone_defaults_ok             — 200, listino+versione propagati
 8) test_versione_close_defaults_ok             — 200, listino+versione propagati
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.PermissionResolver"
_SVC = "apps.vendite.api.views_form_defaults"


class TestVenditeFormDefaultsApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Permesso area vendite TUTTO: form-defaults non richiede di piu'.
        self._perm_patcher = patch(_PERM)
        mock_resolver = self._perm_patcher.start()
        mock_resolver.return_value.get_livello_area.return_value = "TUTTO"
        mock_resolver.return_value.is_super_admin.return_value = False
        mock_resolver.return_value.get_ruolo_applicativo.return_value = "OPERATORE"
        self.addCleanup(self._perm_patcher.stop)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_contratto_form_defaults")
    def test_contratto_form_defaults_no_ba(self, mock_fn, _auth):
        mock_fn.return_value = {
            "billing_account_id": None,
            "default_data": "2026-04-30",
            "default_valido_dal": "2026-04-30",
        }
        resp = self.client.get(
            "/api/v1/vendite/contratti/form-defaults/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("data", body)
        self.assertEqual(body["data"]["default_data"], "2026-04-30")
        # ba=None propagato al service.
        kwargs = mock_fn.call_args.kwargs
        self.assertIsNone(kwargs["billing_account_id"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_contratto_form_defaults")
    def test_contratto_form_defaults_con_ba(self, mock_fn, _auth):
        mock_fn.return_value = {"billing_account_id": 10}
        resp = self.client.get(
            "/api/v1/vendite/contratti/form-defaults/?billing_account_id=10",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_fn.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 10)

    def test_contratto_form_defaults_richiede_jwt(self):
        # Senza Authorization header -> 401 (DomainAPIView richiede JWT).
        resp = self.client.get("/api/v1/vendite/contratti/form-defaults/")
        self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_preventivo_form_defaults")
    def test_preventivo_form_defaults_no_ba(self, mock_fn, _auth):
        mock_fn.return_value = {
            "billing_account_id": None,
            "default_validita_al": "2026-05-30",
        }
        resp = self.client.get(
            "/api/v1/vendite/preventivi/form-defaults/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["default_validita_al"], "2026-05-30")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_preventivo_form_defaults")
    def test_preventivo_form_defaults_con_ba(self, mock_fn, _auth):
        mock_fn.return_value = {"billing_account_id": 10, "valuta_id": 1}
        resp = self.client.get(
            "/api/v1/vendite/preventivi/form-defaults/?billing_account_id=10",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_fn.call_args.kwargs["billing_account_id"], 10)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_versione_new_defaults")
    def test_versione_new_defaults_ok(self, mock_fn, _auth):
        mock_fn.return_value = {
            "listino_id": 12, "default_valido_dal": "2026-04-30",
            "has_existing_draft": False, "existing_drafts": [],
        }
        resp = self.client.get(
            "/api/v1/vendite/listini/12/versioni/form-defaults/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_fn.call_args.kwargs["listino_id"], 12)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_versione_clone_defaults")
    def test_versione_clone_defaults_ok(self, mock_fn, _auth):
        mock_fn.return_value = {
            "listino_id": 12, "source_versione_id": 33,
            "default_codice_versione": "v1-clone",
        }
        resp = self.client.get(
            "/api/v1/vendite/listini/12/versioni/33/clone-defaults/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_fn.call_args.kwargs
        self.assertEqual(kwargs["listino_id"], 12)
        self.assertEqual(kwargs["src_versione_id"], 33)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_SVC}.fn_get_versione_close_defaults")
    def test_versione_close_defaults_ok(self, mock_fn, _auth):
        mock_fn.return_value = {
            "listino_id": 12, "versione_id": 33,
            "default_valido_al": "2026-04-30",
            "current_valido_al": None,
        }
        resp = self.client.get(
            "/api/v1/vendite/listini/12/versioni/33/close-defaults/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_fn.call_args.kwargs
        self.assertEqual(kwargs["listino_id"], 12)
        self.assertEqual(kwargs["versione_id"], 33)
