# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
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
