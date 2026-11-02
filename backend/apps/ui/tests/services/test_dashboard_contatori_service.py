# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit DashboardContatoriService — estrazione key dai widget
#        visibili, isolamento per-key dei fallimenti, registry. CI senza
#        DB reale (SimpleTestCase, callable dei contatori mockate).
#
# Indice test (0..N):
#   0. get_contatori_calcola_solo_key_visibili
#   1. get_contatori_dedup_e_ordine_key
#   2. get_contatori_key_non_registrata_degrada
#   3. get_contatori_callable_che_esplode_non_oscura_le_altre
#   4. get_contatori_config_none_risolve_via_dashboard_service
#   5. registry_contiene_le_key_dei_widget_seedati
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ui.services.dashboard_contatori_service import (
    CONTATORI_REGISTRY,
    DashboardContatoriService,
)

_REGISTRY_PATH = (
    "apps.ui.services.dashboard_contatori_service.CONTATORI_REGISTRY"
)


# Scopo: Config risolta minimale con due widget visibili e uno nascosto.
def _config(widget):
    return {"widget": widget, "dimensione_max": 8}


class DashboardContatoriServiceTests(SimpleTestCase):
    def test_get_contatori_calcola_solo_key_visibili(self) -> None:
        config = _config([
            {"codice": "a", "visibile": True, "contatore_key": "k.a"},
            # Nascosto: non a schermo -> non consuma una query.
            {"codice": "b", "visibile": False, "contatore_key": "k.b"},
            # Visibile ma informativo (senza contatore): nessuna key.
            {"codice": "c", "visibile": True, "contatore_key": None},
        ])
        with patch.dict(_REGISTRY_PATH, {"k.a": lambda: 7}, clear=True):
            contatori = DashboardContatoriService().get_contatori(
                MagicMock(), "home", config=config,
            )

        self.assertEqual(contatori, {"k.a": {"valore": 7, "ok": True}})

    def test_get_contatori_dedup_e_ordine_key(self) -> None:
        # Due widget con la stessa key -> UNA sola computazione.
        chiamate: list[str] = []

        def _conta() -> int:
            chiamate.append("k.a")
            return 3

        config = _config([
            {"codice": "a1", "visibile": True, "contatore_key": "k.a"},
            {"codice": "a2", "visibile": True, "contatore_key": "k.a"},
        ])
        with patch.dict(_REGISTRY_PATH, {"k.a": _conta}, clear=True):
            contatori = DashboardContatoriService().get_contatori(
                MagicMock(), "home", config=config,
            )

        self.assertEqual(contatori["k.a"], {"valore": 3, "ok": True})
        self.assertEqual(chiamate, ["k.a"])

    def test_get_contatori_key_non_registrata_degrada(self) -> None:
        # Widget seedato senza callable = disallineamento seed/registry:
        # degrada la card, non solleva.
        config = _config([
            {"codice": "x", "visibile": True, "contatore_key": "k.ignota"},
        ])
        with patch.dict(_REGISTRY_PATH, {}, clear=True):
            contatori = DashboardContatoriService().get_contatori(
                MagicMock(), "home", config=config,
            )

        self.assertEqual(contatori["k.ignota"], {"valore": None, "ok": False})

    def test_get_contatori_callable_che_esplode_non_oscura_le_altre(
        self,
    ) -> None:
        def _esplode() -> int:
            raise RuntimeError("boom")

        config = _config([
            {"codice": "a", "visibile": True, "contatore_key": "k.rotta"},
            {"codice": "b", "visibile": True, "contatore_key": "k.sana"},
        ])
        with patch.dict(
            _REGISTRY_PATH, {"k.rotta": _esplode, "k.sana": lambda: 5},
            clear=True,
        ):
            # assertLogs assorbe lo stacktrace atteso dal logger del modulo.
            with self.assertLogs(
                "apps.ui.services.dashboard_contatori_service", level="ERROR"
            ):
                contatori = DashboardContatoriService().get_contatori(
                    MagicMock(), "home", config=config,
                )

        # Invariante 2: il KPI rotto degrada la SUA card, le altre vivono.
        self.assertEqual(contatori["k.rotta"], {"valore": None, "ok": False})
        self.assertEqual(contatori["k.sana"], {"valore": 5, "ok": True})

    def test_get_contatori_config_none_risolve_via_dashboard_service(
        self,
    ) -> None:
        # Senza config esplicita il service risolve da solo la dashboard
        # (invariante 1: le key vengono dalla fn DB, mai dal client).
        config = _config([
            {"codice": "a", "visibile": True, "contatore_key": "k.a"},
        ])
        user = MagicMock()
        with (
            patch(
                "apps.ui.services.dashboard_service.DashboardService"
                ".get_dashboard_config",
                return_value=config,
            ) as mock_resolve,
            patch.dict(_REGISTRY_PATH, {"k.a": lambda: 1}, clear=True),
        ):
            contatori = DashboardContatoriService().get_contatori(user, "home")

        mock_resolve.assert_called_once_with(user, "home")
        self.assertEqual(contatori, {"k.a": {"valore": 1, "ok": True}})

    def test_registry_contiene_le_key_dei_widget_seedati(self) -> None:
        # Regressione disallineamento seed/registry: queste key sono quelle
        # seedate in `ui.widget.contatore_key` (brief DB dashboard home).
        # Se una sparisce da qui, la card corrispondente degrada in home.
        for key in (
            "vendite.situazione_aperta.totale_aperto",
            "vendite.backlog.documenti_fermi",
            "vendite.competenza.da_fatturare",
        ):
            self.assertIn(key, CONTATORI_REGISTRY)
