# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit DashboardPreferenzaService — il corpo arriva intatto al
#        DB (la forma la giudica il guard), preset di base dalla risoluzione,
#        UPSERT/DELETE preferenza, «ignora». CI senza DB reale (SimpleTestCase
#        + repository mockato). Gemello di test_lista_preferenza_service.
#
# Indice test (0..N):
#   0. upsert_happy_path
#   1. upsert_senza_preset_di_base
#   2. upsert_dashboard_inesistente_raises
#   3. upsert_una_chiave_sola_arriva_da_sola
#   4. upsert_senza_chiavi_raises
#   5. upsert_payload_non_dict_raises
#   6. upsert_la_forma_arriva_intatta_al_db (BE8 e BE11, giro 2: la forma la giudica il DB)
#   7. delete_happy_path_idempotente
#   8. delete_dashboard_inesistente_raises
#   9. ignore_preset_update_happy_path
#  10. ignore_preset_update_senza_preferenza_raises
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


# Scopo: Repo mockato con dashboard esistente (id=1) e preset di base 5.
def _make_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_dashboard_id.return_value = 1
    repo.resolve_dashboard_config.return_value = {
        "preset_base": {
            "id": 5,
            "ambito": "sistema",
            "contenuto_aggiornato_il": "2026-07-01T00:00:00+00:00",
        },
    }
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
        # ⭐ Lo snapshot lo scrive il trigger del DB (BE6): il service non lo passa.
        self.assertNotIn("preset_base_contenuto_aggiornato_il", kwargs)
        cfg = kwargs["configurazione"]
        self.assertEqual(cfg["dimensione_max"], 8)
        self.assertEqual(len(cfg["widget"]), 2)
        # La base viene dalla risoluzione, con l'emittente dell'utente (BE5).
        repo.resolve_dashboard_config.assert_called_once_with(
            dashboard_codice="home", auth_user_id=42, emittente_fiscale_id=11,
        )

    @_PATCH_EMITTENTE
    def test_upsert_senza_preset_di_base(self, _mock_em) -> None:
        repo = _make_repo()
        repo.resolve_dashboard_config.return_value = {"preset_base": None}
        svc = DashboardPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "home", dict(_VALID_PAYLOAD))

        self.assertIsNone(result["preset_base_id"])
        self.assertIsNone(repo.upsert_preferenza.call_args.kwargs["preset_base_id"])

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

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", {})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)
        repo.upsert_preferenza.assert_not_called()

    @_PATCH_EMITTENTE
    def test_upsert_payload_non_dict_raises(self, _mock_em) -> None:
        svc = DashboardPreferenzaService(repository=_make_repo())

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "home", ["non", "dict"])  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    # ⛔ La forma la giudica il guard del DB (BE8 e BE11 di
    #    brief-db-revisione-ui, giro 2): chiavi, voci, codici doppi e il tetto
    #    1-100 di `dimensione_max`. Il service non toglie, non converte e non
    #    rifiuta niente: un corpo sbagliato in ogni modo arriva INTATTO al
    #    repository; il rifiuto (`E_UI_CONFIGURAZIONE_FORMA`, 400) lo prova
    #    `tests/db/test_forma_preferenza_db`.
    @_PATCH_EMITTENTE
    def test_upsert_la_forma_arriva_intatta_al_db(self, _mock_em) -> None:
        repo = _make_repo()
        svc = DashboardPreferenzaService(repository=repo)

        payload = {
            "widget": [
                {"codice": "x", "ordine": 0, "deep_link": {"path": "/x"}},
                {"codice": "x", "visibile": None},
            ],
            "dimensione_max": 101,
            "iniettata": True,
        }
        svc.upsert(_make_user(), "home", payload)
        self.assertEqual(repo.upsert_preferenza.call_args.kwargs["configurazione"], payload)


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
        repo.riallinea_snapshot_base.return_value = True
        svc = DashboardPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "home")

        self.assertEqual(result, {"ignored": True})
        repo.riallinea_snapshot_base.assert_called_once_with(
            auth_user_id=42, dashboard_id=1,
        )

    @_PATCH_EMITTENTE
    def test_ignore_preset_update_senza_preferenza_raises(self, _mock_em) -> None:
        # Tombstone su preferenza inesistente -> 404 parlante.
        repo = _make_repo()
        repo.riallinea_snapshot_base.return_value = False
        svc = DashboardPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.ignore_preset_update(_make_user(), "home")
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_NON_TROVATA)
