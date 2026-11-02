# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit DashboardService (lettura dashboard configurabili).
#        Mock repository + PermissionResolver. CI senza DB reale
#        (SimpleTestCase). Gemello di test_ui_service per le liste.
#
# Indice test (0..N):
#   0. get_dashboard_config_happy_path
#   1. get_dashboard_config_admin_globale_passa_emittente_none
#   2. get_dashboard_config_config_vuota_raises
#   3. get_dashboard_config_database_error_marker_riconosciuto
#   4. get_dashboard_config_database_error_fallback_generic
#   5. get_catalogo_ritorna_pool_completo
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.dashboard_service import (
    E_UI_DASHBOARD_NON_TROVATA,
    E_UI_GENERIC_FAILED,
    DashboardService,
)


# Scopo: Costruisce un MagicMock user con id stabile.
def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


# Config risolta tipo, come la restituisce fn_resolve_dashboard_config.
_CONFIG: dict[str, Any] = {
    "widget": [
        {
            "codice": "vendite.situazione_aperta",
            "ordine": 1,
            "visibile": True,
            "etichetta": "Situazione aperta",
            "contatore_key": "vendite.situazione_aperta.totale_aperto",
        },
        {
            "codice": "core.benvenuto",
            "ordine": 2,
            "visibile": False,
            "etichetta": "Benvenuto",
            "contatore_key": None,
        },
    ],
    "dimensione_max": 8,
    "widget_nuovi": 1,
    "preset_aggiornato": False,
}


class DashboardServiceGetConfigTests(SimpleTestCase):
    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_get_dashboard_config_happy_path(self, _mock_em) -> None:
        repo = MagicMock()
        repo.resolve_dashboard_config.return_value = dict(_CONFIG)
        svc = DashboardService(repository=repo)

        config = svc.get_dashboard_config(_make_user(), "home")

        self.assertEqual(config["dimensione_max"], 8)
        self.assertEqual(len(config["widget"]), 2)
        repo.resolve_dashboard_config.assert_called_once_with(
            dashboard_codice="home",
            auth_user_id=42,
            emittente_fiscale_id=11,
        )

    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=None,
    )
    def test_get_dashboard_config_admin_globale_passa_emittente_none(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        repo.resolve_dashboard_config.return_value = dict(_CONFIG)
        svc = DashboardService(repository=repo)

        svc.get_dashboard_config(_make_user(), "home")

        # Admin globale -> emittente_fiscale_id=None propagato alla fn DB.
        repo.resolve_dashboard_config.assert_called_once_with(
            dashboard_codice="home",
            auth_user_id=42,
            emittente_fiscale_id=None,
        )

    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_get_dashboard_config_config_vuota_raises(self, _mock_em) -> None:
        # Caso difensivo: la fn ritorna dict vuoto invece di raise.
        repo = MagicMock()
        repo.resolve_dashboard_config.return_value = {}
        svc = DashboardService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_dashboard_config(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_DASHBOARD_NON_TROVATA)

    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_get_dashboard_config_database_error_marker_riconosciuto(
        self, _mock_em
    ) -> None:
        # Il codice DB nel MESSAGE del RAISE P0001 sopravvive nel
        # ServiceError tradotto (match marker).
        repo = MagicMock()
        repo.resolve_dashboard_config.side_effect = DatabaseError(
            "ERRORE E_UI_DASHBOARD_NON_TROVATA: dashboard 'x' inesistente"
        )
        svc = DashboardService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_dashboard_config(_make_user(), "x")
        self.assertEqual(ctx.exception.code, E_UI_DASHBOARD_NON_TROVATA)

    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_get_dashboard_config_database_error_fallback_generic(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        repo.resolve_dashboard_config.side_effect = DatabaseError(
            "deadlock detected"
        )
        svc = DashboardService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_dashboard_config(_make_user(), "home")
        self.assertEqual(ctx.exception.code, E_UI_GENERIC_FAILED)


class DashboardServiceGetCatalogoTests(SimpleTestCase):
    @patch(
        "apps.ui.services.dashboard_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_get_catalogo_ritorna_pool_completo(self, _mock_em) -> None:
        # Il pool della modale e' `widget[]` cosi' com'e' (inclusi i non
        # visibili): il filtro permessi e' gia' avvenuto nella fn DB.
        repo = MagicMock()
        repo.resolve_dashboard_config.return_value = dict(_CONFIG)
        svc = DashboardService(repository=repo)

        catalogo = svc.get_catalogo(_make_user(), "home")

        self.assertEqual(len(catalogo["widget"]), 2)
        self.assertEqual(catalogo["dimensione_max"], 8)
        # Anche il widget non visibile resta nel pool selezionabile.
        self.assertFalse(catalogo["widget"][1]["visibile"])
