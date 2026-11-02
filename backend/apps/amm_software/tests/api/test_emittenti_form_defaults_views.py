# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API Fase 3 — form-defaults emittente fiscale
#        + lookup rounding-modes. Mock ParameterService, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_form_defaults_admin_ok — GET 200 superuser, shape {defaults, non_editable_fields}
 2) test_form_defaults_anonymous_403 — request non autenticato -> 403
 3) test_rounding_modes_lookup_ok — GET 200, lista 4 codici (no HALF_EVEN)
 4) test_rounding_modes_lookup_response_shape — data e' lista nuda, non envelope paginato
 5) test_audit_sources_lookup_ok — GET 200, delega a service.list_audit_sources (Fase 5)
(Il lookup degli stati email log e' uscito il 2026-09-26: ora e'
`/core/email/log/stati/`, test in `core/tests/api/test_email_log_stati_lookup.py`.)
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    AuditSourcesLookupView,
    EmittenteRoundingModesLookupView,
    EmittentiFormDefaultsView,
)


def _admin_request() -> MagicMock:
    # Scopo: Crea un mock request autenticato come superuser (bypass admin check).
    request = MagicMock()
    request.method = "GET"
    request.path = "/api/v1/amm-software/emittenti-fiscali/form-defaults/"
    user = MagicMock()
    user.id = 99
    user.is_authenticated = True
    user.is_superuser = True
    request.user = user
    request.query_params = {}
    return request


PARAM_SVC = "apps.amm_software.services.amm_software_service.ParameterService"


class TestEmittentiFormDefaultsView(TestCase):
    """View GET /api/v1/amm-software/emittenti-fiscali/form-defaults/."""

    @patch(PARAM_SVC)
    def test_form_defaults_admin_ok(self, mock_ps_cls: MagicMock) -> None:
        # Scopo: GET 200 con shape {defaults: {...}, non_editable_fields: [...]}.
        mock_ps_cls.return_value.get_defaults.return_value = {
            "EMITTENTE_DEFAULT_BOLLO_AUTO": "false",
            "EMITTENTE_DEFAULT_BOLLO_SOGLIA": "",
            "EMITTENTE_DEFAULT_ROUNDING_POLICY": "HALF_UP",
        }

        view = EmittentiFormDefaultsView()
        view.check_permissions = MagicMock()  # Bypass permission (testata altrove)
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertIn("defaults", body["data"])
        self.assertIn("non_editable_fields", body["data"])
        self.assertEqual(body["data"]["defaults"], {
            "bollo_auto": False,
            "bollo_soglia": None,
            "rounding_policy": "HALF_UP",
        })
        self.assertEqual(body["data"]["non_editable_fields"], ["codice", "soggetto_id"])


class TestEmittenteRoundingModesLookupView(TestCase):
    """View GET /api/v1/amm-software/lookup/rounding-modes/."""

    def test_rounding_modes_lookup_ok(self) -> None:
        # Scopo: GET 200 con 4 codici (UP, DOWN, HALF_UP, HALF_DOWN).
        # Allineati al CHECK chk_emittenti_fiscali_rounding_policy: NO HALF_EVEN.
        view = EmittenteRoundingModesLookupView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        codici = [row["codice"] for row in body["data"]]
        self.assertEqual(set(codici), {"UP", "DOWN", "HALF_UP", "HALF_DOWN"})
        self.assertNotIn("HALF_EVEN", codici)

    def test_rounding_modes_lookup_response_shape(self) -> None:
        # Scopo: l'envelope `data` e' una lista nuda (non `{count, results}`).
        # Allineato al lookup catalogo `/catalogo/lookup/rounding-modes/`.
        # Il FE EmittenteRoundingModeSelect.vue dipende da questa shape per
        # il transform `(r) => r.data.data` su useGlobalLookup.
        view = EmittenteRoundingModesLookupView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request())

        body = json.loads(response.content)
        self.assertIsInstance(body["data"], list)
        self.assertEqual(len(body["data"]), 4)
        for row in body["data"]:
            self.assertIn("codice", row)
            self.assertIn("descrizione", row)
            self.assertIn("ordering", row)


# =================================================================
# Fase 5 — audit-sources lookup (email-log-stati: sceso in core il 2026-09-26)
# =================================================================


REPO_PATH = "apps.amm_software.services.amm_software_service.AmmSoftwareRepository"


class TestAuditSourcesLookupView(TestCase):
    """View GET /api/v1/amm-software/lookup/audit-sources/ (Fase 5 — A13)."""

    @patch(REPO_PATH)
    def test_audit_sources_lookup_ok(self, mock_repo_cls: MagicMock) -> None:
        # Service delega a repo (vw_audit_sources). Il mock evita il DB:
        # verifichiamo il passaggio della shape attraverso la view.
        mock_repo_cls.return_value.list_audit_sources.return_value = [
            {"code": "user_override_aree", "label_key": "amm.audit_tabella_override_aree", "area_funzionale": "PERMESSI"},
            {"code": "identita_digitali", "label_key": "amm.audit_tabella_identita", "area_funzionale": "AUTH"},
        ]

        view = AuditSourcesLookupView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertIsInstance(body["data"], list)
        self.assertEqual(len(body["data"]), 2)
        codici = [r["code"] for r in body["data"]]
        self.assertIn("user_override_aree", codici)
        self.assertIn("identita_digitali", codici)
        for row in body["data"]:
            self.assertIn("label_key", row)
            self.assertIn("area_funzionale", row)

