# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaPreferenzaService — valida payload, snapshot
#        preset di base, UPSERT/DELETE preferenza utente. CI senza DB
#        reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   0. upsert_happy_path
#   1. upsert_lista_inesistente_raises
#   2. upsert_payload_chiavi_extra_raises
#   3. upsert_colonna_codice_mancante_raises
#   4. upsert_colonna_chiavi_extra_raises
#   5. upsert_pagina_dimensione_la_decide_il_db
#   6. upsert_pagina_dimensione_non_int_raises
#   7. upsert_visibile_non_bool_raises
#   8. upsert_payload_non_dict_raises
#   9. upsert_snapshot_preset_passato_a_repo
#  10. delete_happy_path
#  11. delete_lista_inesistente_raises
#  12. delete_idempotente_se_pref_assente
#  13. ignore_preset_update_happy_path (DEF-2)
#  14. ignore_preset_update_lista_inesistente_raises (DEF-2)
#  15. ignore_preset_update_senza_preferenza_raises (DEF-2)
#  16. ignore_preset_update_pref_senza_preset_base_id (DEF-2 — edge)
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_preferenza_service import (
    E_UI_LISTA_NON_TROVATA,
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    ListaPreferenzaService,
)


def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


_VALID_PAYLOAD: dict[str, Any] = {
    "colonne": [
        {
            "codice": "ragione_sociale",
            "ordine": 1,
            "larghezza": 240,
            "visibile": True,
            "fissata": True,
        },
        {"codice": "partita_iva", "ordine": 2, "visibile": True},
    ],
    "ordinamento": [{"col": "ragione_sociale", "dir": "asc"}],
    "filtri": {"attivo": True},
    "pagina_dimensione": 50,
}


class ListaPreferenzaUpsertTests(SimpleTestCase):
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_happy_path(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.get_preset_base_snapshot.return_value = (5, "2026-05-06T00:00")
        repo.upsert_preferenza.return_value = 99
        svc = ListaPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "anagrafiche.clienti", dict(_VALID_PAYLOAD))

        self.assertEqual(result["id"], 99)
        self.assertEqual(result["preset_base_id"], 5)
        repo.upsert_preferenza.assert_called_once()
        kwargs = repo.upsert_preferenza.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)
        self.assertEqual(kwargs["lista_id"], 1)
        self.assertEqual(kwargs["preset_base_id"], 5)
        self.assertEqual(kwargs["preset_base_data_update"], "2026-05-06T00:00")
        # Configurazione normalizzata propagata.
        cfg = kwargs["configurazione"]
        self.assertEqual(cfg["pagina_dimensione"], 50)
        self.assertEqual(len(cfg["colonne"]), 2)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_lista_inesistente_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = None
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "non.esiste", dict(_VALID_PAYLOAD))
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)
        repo.upsert_preferenza.assert_not_called()

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_payload_chiavi_extra_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        bad_payload = dict(_VALID_PAYLOAD)
        bad_payload["malicious_key"] = "<script>"
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", bad_payload)
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_colonna_codice_mancante_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        bad = {"colonne": [{"ordine": 1, "visibile": True}]}
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", bad)
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_colonna_chiavi_extra_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        bad = {"colonne": [{"codice": "x", "extra_field": 1}]}
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", bad)
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    # ⭐ Dal 2026-09-30 il service NON giudica la misura: quali sono ammesse lo
    #    dice il catalogo `ui.misure_pagina`, e il rifiuto lo da' il guard a DB
    #    (`E_UI_MISURA_PAGINA_NON_AMMESSA`, provato sul DB vero in
    #    `tests/db/test_misure_pagina_db`). Qui si prova che la misura arriva
    #    intatta al repository: un tetto rimasto nel service sarebbe una
    #    seconda regola, diversa dal catalogo.
    def test_upsert_pagina_dimensione_la_decide_il_db(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.get_preset_base_snapshot.return_value = (None, None)
        repo.upsert_preferenza.return_value = 7
        svc = ListaPreferenzaService(repository=repo)

        svc.upsert(_make_user(), "anagrafiche.clienti", {"pagina_dimensione": 5000})
        cfg = repo.upsert_preferenza.call_args.kwargs["configurazione"]
        self.assertEqual(cfg["pagina_dimensione"], 5000)

    # ⭐ Preferenza per chiave (2026-11-01): ogni chiave e' facoltativa, quella
    #    assente vale «come lo standard». Arriva al repository la sola chiave
    #    mandata, senza le altre riempite.
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_una_chiave_sola_arriva_da_sola(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.get_preset_base_snapshot.return_value = (5, "2026-05-06T00:00")
        repo.upsert_preferenza.return_value = 7
        svc = ListaPreferenzaService(repository=repo)

        svc.upsert(_make_user(), "anagrafiche.clienti", {"colonne": _VALID_PAYLOAD["colonne"]})
        cfg = repo.upsert_preferenza.call_args.kwargs["configurazione"]
        self.assertEqual(set(cfg), {"colonne"})

    # ⛔ Una preferenza senza chiavi si toglie col DELETE: il PUT vuoto, o con
    #    le sole chiavi a null, e' un 400 e non scrive niente.
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_senza_chiavi_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        for payload in ({}, {"pagina_dimensione": None, "colonne": None}):
            with self.subTest(payload=payload), self.assertRaises(ServiceError) as ctx:
                svc.upsert(_make_user(), "anagrafiche.clienti", payload)
            self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)
        repo.upsert_preferenza.assert_not_called()

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_pagina_dimensione_non_int_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        bad = {"pagina_dimensione": "venti"}
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", bad)
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_visibile_non_bool_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        bad = {"colonne": [{"codice": "x", "visibile": "yes"}]}
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", bad)
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_payload_non_dict_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", ["not", "a", "dict"])  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=None,  # admin globale
    )
    def test_upsert_snapshot_preset_none_quando_nessun_preset(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.get_preset_base_snapshot.return_value = (None, None)
        repo.upsert_preferenza.return_value = 99
        svc = ListaPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "anagrafiche.clienti", dict(_VALID_PAYLOAD))

        self.assertIsNone(result["preset_base_id"])
        kwargs = repo.upsert_preferenza.call_args.kwargs
        self.assertIsNone(kwargs["preset_base_id"])
        self.assertIsNone(kwargs["preset_base_data_update"])


class ListaPreferenzaDeleteTests(SimpleTestCase):
    def test_delete_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.delete_preferenza.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.delete(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["deleted"])
        repo.delete_preferenza.assert_called_once_with(
            auth_user_id=42, lista_id=1,
        )

    def test_delete_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = None
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.delete(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)
        repo.delete_preferenza.assert_not_called()

    def test_delete_idempotente_se_pref_assente(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.delete_preferenza.return_value = False  # nessuna riga eliminata
        svc = ListaPreferenzaService(repository=repo)

        result = svc.delete(_make_user(), "anagrafiche.clienti")

        # Non solleva — solo `deleted=False`.
        self.assertFalse(result["deleted"])


class ListaPreferenzaIgnorePresetUpdateTests(SimpleTestCase):
    """DEF-2: tombstone 'ignora banner preset aggiornato'."""

    def test_ignore_preset_update_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.set_preset_aggiornato_ignored.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["ignored"])
        repo.set_preset_aggiornato_ignored.assert_called_once_with(
            auth_user_id=42, lista_id=1,
        )

    def test_ignore_preset_update_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = None
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.ignore_preset_update(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)
        repo.set_preset_aggiornato_ignored.assert_not_called()

    def test_ignore_preset_update_senza_preferenza_raises(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.set_preset_aggiornato_ignored.return_value = False  # no riga
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_NON_TROVATA)

    def test_ignore_preset_update_pref_senza_preset_base_id(self) -> None:
        # Edge: preferenza esiste ma `preset_base_id` e' NULL (utente ha
        # salvato senza preset applicabile). L'UPDATE setta comunque il
        # tombstone — il trigger DB non si attiva (preset_base_id non
        # cambia) e la fn DB ritorna sempre preset_aggiornato=false. Il
        # service non deve sollevare: dal suo punto di vista la riga
        # esiste e l'UPDATE e' atomico.
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.set_preset_aggiornato_ignored.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["ignored"])
