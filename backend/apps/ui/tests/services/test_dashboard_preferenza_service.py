# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit DashboardPreferenzaService — valida payload (whitelist
#        chiavi anti-injection), snapshot preset di base, UPSERT/DELETE
#        preferenza, tombstone ignore. CI senza DB reale (SimpleTestCase
#        + repository mockato). Gemello di test_lista_preferenza_service.
#
# Indice test (0..N):
#   0. upsert_happy_path
#   1. upsert_dashboard_inesistente_raises
#   2. upsert_payload_non_dict_raises
#   3. upsert_payload_chiavi_extra_raises
#   4. upsert_widget_non_lista_raises
#   5. upsert_widget_oltre_tetto_raises
#   6. upsert_widget_item_non_dict_raises
#   7. upsert_widget_chiavi_extra_raises
#   8. upsert_widget_codice_mancante_raises
#   9. upsert_widget_codici_duplicati_raises
#  10. upsert_widget_ordine_non_positivo_raises
#  11. upsert_dimensione_max_oltre_tetto_raises
#  12. delete_happy_path_idempotente
#  13. delete_dashboard_inesistente_raises
#  14. ignore_preset_update_happy_path
#  15. ignore_preset_update_senza_preferenza_raises
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.dashboard_preferenza_service import (
    E_UI_DASHBOARD_NON_TROVATA,
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    DashboardPreferenzaService,
)


def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


_VALID_PAYLOAD: dict[str, Any] = {
    "widget": [
        {"codice": "vendite.situazione_aperta", "ordine": 1, "visibile": True},
        {"codice": "vendite.backlog", "ordine": 2, "visibile": False},
    ],
    "dimensione_max": 8,
}

_PATCH_EMITTENTE = patch(
    "apps.ui.services.dashboard_preferenza_service.PermissionResolver"
    ".get_emittente_for_user",
    return_value=11,
)


# Scopo: Repo mockato con dashboard esistente (id=1) e snapshot preset.
def _make_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_dashboard_id.return_value = 1
    repo.get_preset_base_snapshot.return_value = (5, "2026-07-01T00:00")
    repo.upsert_preferenza.return_value = 99
    return repo


class DashboardPreferenzaUpsertTests(SimpleTestCase):
    @_PATCH_EMITTENTE
    def test_upsert_happy_path(self, _mock_em) -> None:
        repo = _make_repo()
        svc = DashboardPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "home", dict(_VALID_PAYLOAD))

        self.assertEqual(result["id"], 99)
        self.assertEqual(result["preset_base_id"], 5)
        kwargs = repo.upsert_preferenza.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)
        self.assertEqual(kwargs["dashboard_id"], 1)
        self.assertEqual(kwargs["preset_base_id"], 5)
        self.assertEqual(kwargs["preset_base_contenuto_aggiornato_il"], "2026-07-01T00:00")
        cfg = kwargs["configurazione"]
        self.assertEqual(cfg["dimensione_max"], 8)
        self.assertEqual(len(cfg["widget"]), 2)
        # Snapshot calcolato con la stessa cascata della fn DB.
        repo.get_preset_base_snapshot.assert_called_once_with(
            dashboard_id=1, auth_user_id=42, emittente_fiscale_id=11,
        )

    @_PATCH_EMITTENTE
    def test_upsert_dashboard_inesistente_raises(self, _mock_em) -> None:
        repo = _make_repo()
        repo.get_dashboard_id.return_value = None
        svc = DashboardPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "non.esiste", dict(_VALID_PAYLOAD))
        self.assertEqual(ctx.exception.code, E_UI_DASHBOARD_NON_TROVATA)
        repo.upsert_preferenza.assert_not_called()

    # ⭐ Preferenza per chiave (2026-11-01): ogni chiave e' facoltativa, quella
    #    assente vale «come lo standard».
    @_PATCH_EMITTENTE
    def test_upsert_una_chiave_sola_arriva_da_sola(self, _mock_em) -> None:
        repo = _make_repo()
        svc = DashboardPreferenzaService(repository=repo)

        svc.upsert(_make_user(), "home", {"widget": _VALID_PAYLOAD["widget"]})
        cfg = repo.upsert_preferenza.call_args.kwargs["configurazione"]
        self.assertEqual(set(cfg), {"widget"})

    # ⛔ Una preferenza senza chiavi si toglie col DELETE: il PUT vuoto e' un 400.
    @_PATCH_EMITTENTE
    def test_upsert_senza_chiavi_raises(self, _mock_em) -> None:
        repo = _make_repo()
        svc = DashboardPreferenzaService(repository=repo)

        for payload in ({}, {"dimensione_max": None}):
            with self.subTest(payload=payload), self.assertRaises(ServiceError) as ctx:
                svc.upsert(_make_user(), "home", payload)
            self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)
        repo.upsert_preferenza.assert_not_called()

    @_PATCH_EMITTENTE
    def test_upsert_payload_non_dict_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", ["non", "dict"])  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_payload_chiavi_extra_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(
                _make_user(), "home",
                {**_VALID_PAYLOAD, "iniettata": True},
            )
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_non_lista_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", {"widget": {"codice": "x"}})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_oltre_tetto_raises(self, _mock_em) -> None:
        # Guardia anti-payload-abnorme: oltre 100 widget in un salvataggio.
        troppi = [
            {"codice": f"w{i}", "ordine": i + 1, "visibile": True}
            for i in range(101)
        ]
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", {"widget": troppi})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_item_non_dict_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", {"widget": ["stringa"]})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_chiavi_extra_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(
                _make_user(), "home",
                {"widget": [{"codice": "x", "deep_link": {"path": "/x"}}]},
            )
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_codice_mancante_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(
                _make_user(), "home",
                {"widget": [{"ordine": 1, "visibile": True}]},
            )
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_codici_duplicati_raises(self, _mock_em) -> None:
        # Codice duplicato = layout ambiguo (la fn DB joina sul codice).
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(
                _make_user(), "home",
                {"widget": [
                    {"codice": "x", "ordine": 1},
                    {"codice": "x", "ordine": 2},
                ]},
            )
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_widget_ordine_non_positivo_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(
                _make_user(), "home",
                {"widget": [{"codice": "x", "ordine": 0}]},
            )
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @_PATCH_EMITTENTE
    def test_upsert_dimensione_max_oltre_tetto_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", {"dimensione_max": 101})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)


class DashboardPreferenzaDeleteTests(SimpleTestCase):
    @_PATCH_EMITTENTE
    def test_delete_happy_path_idempotente(self, _mock_em) -> None:
        repo = _make_repo()
        repo.delete_preferenza.return_value = False  # non esisteva
        svc = DashboardPreferenzaService(repository=repo)

        result = svc.delete(_make_user(), "home")

        # Idempotente: nessun errore anche se la preferenza non c'era.
        self.assertEqual(result, {"deleted": False})
        repo.delete_preferenza.assert_called_once_with(
            auth_user_id=42, dashboard_id=1,
        )

    @_PATCH_EMITTENTE
    def test_delete_dashboard_inesistente_raises(self, _mock_em) -> None:
        repo = _make_repo()
        repo.get_dashboard_id.return_value = None
        svc = DashboardPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.delete(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_DASHBOARD_NON_TROVATA)
        repo.delete_preferenza.assert_not_called()


class DashboardPreferenzaIgnorePresetUpdateTests(SimpleTestCase):
    @_PATCH_EMITTENTE
    def test_ignore_preset_update_happy_path(self, _mock_em) -> None:
        repo = _make_repo()
        repo.set_preset_aggiornato_ignored.return_value = True
        svc = DashboardPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "home")

        self.assertEqual(result, {"ignored": True})
        repo.set_preset_aggiornato_ignored.assert_called_once_with(
            auth_user_id=42, dashboard_id=1,
        )

    @_PATCH_EMITTENTE
    def test_ignore_preset_update_senza_preferenza_raises(self, _mock_em) -> None:
        # Tombstone su preferenza inesistente -> 404 parlante.
        repo = _make_repo()
        repo.set_preset_aggiornato_ignored.return_value = False
        svc = DashboardPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.ignore_preset_update(_make_user(), "home")
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_NON_TROVATA)
