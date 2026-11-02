# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaColonnaAdminService — Blocco F Fase 2 (DEF-5b)
#        CRUD su ui.lista_colonna con UX vincoli (esportabile=False per
#        tipo_colonna='azione') e soft-block DELETE per preferenze.
#        CI senza DB reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   Read
#     0. list_colonne_admin_lista_inesistente_raises
#     1. list_colonne_admin_happy_path
#     2. get_colonna_inesistente_raises
#     3. get_colonna_happy_path
#   Create
#     4. create_colonna_definizione_inesistente_raises
#     5. create_colonna_chiavi_extra_raises
#     6. create_colonna_happy_path_default_allineamento_left
#     7. create_colonna_tipo_colonna_invalido_raises
#     8. create_colonna_tipo_dato_invalido_raises
#     9. create_colonna_allineamento_invalido_raises
#    10. create_colonna_unique_codice_violato
#    11. create_colonna_azione_forza_esportabile_false
#    12. create_colonna_campo_sorgente_null_ammesso
#    13. create_colonna_etichetta_i18n_key_strip_to_null
#   Update
#    14. update_colonna_inesistente_raises
#    15. update_colonna_lista_id_immutabile_raises
#    16. update_colonna_payload_vuoto_raises
#    17. update_colonna_happy_path
#    18. update_colonna_passa_a_azione_forza_esportabile_false
#    19. update_colonna_azione_corrente_blocca_esportabile_true
#    20. update_colonna_attivo_null_raises
#   Delete
#    21. delete_colonna_inesistente_raises
#    22. delete_colonna_in_uso_da_preferenze_raises_409
#    23. delete_colonna_happy_path_zero_preferenze
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_colonna_admin_service import (
    E_COLONNA_IN_USE,
    E_COLONNA_NOT_FOUND,
    E_COLONNA_VALIDATION,
    E_DEFINIZIONE_NOT_FOUND,
    ListaColonnaAdminService,
)


def _make_user(username: str = "tester") -> Any:
    user = MagicMock()
    user.username = username
    user.is_authenticated = True
    return user


def _row_colonna(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": 100,
        "lista_id": 1,
        "codice": "ragione_sociale",
        "etichetta": "Ragione sociale",
        "etichetta_estesa": None,
        "etichetta_i18n_key": "clienti.col_ragione_sociale",
        "campo_sorgente": "ragione_sociale",
        "tipo_colonna": "informazione",
        "tipo_dato": "string",
        "formato": None,
        "larghezza_default": 200,
        "ordine_default": 10,
        "allineamento": "left",
        "gruppo": "anagrafica",
        "gruppo_ordine": 10,
        "filtrabile": True,
        "ordinabile": True,
        "esportabile": True,
        "ricercabile_full": True,
        "sensibile": False,
        "attivo": True,
        "data_insert": None,
        "user_insert": "tester",
        "data_update": None,
        "user_update": None,
    }
    base.update(overrides)
    return base


def _repo_with_lista() -> MagicMock:
    repo = MagicMock()
    repo.get_definizione_admin.return_value = {
        "id": 1, "codice": "anagrafiche.clienti", "attivo": True,
    }
    return repo


def _payload_create_min(**overrides: Any) -> dict[str, Any]:
    base = {
        "codice": "ragione_sociale",
        "etichetta": "Ragione sociale",
        "tipo_colonna": "informazione",
        "tipo_dato": "string",
        "ordine_default": 10,
    }
    base.update(overrides)
    return base


# ============================================================
# Read
# ============================================================

class ListaColonnaReadTests(SimpleTestCase):
    def test_list_colonne_admin_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.list_colonne_admin(999)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.list_colonne_by_lista_admin.assert_not_called()

    def test_list_colonne_admin_happy_path(self) -> None:
        repo = _repo_with_lista()
        repo.list_colonne_by_lista_admin.return_value = [_row_colonna()]
        repo.count_colonne_by_lista_admin.return_value = 1
        svc = ListaColonnaAdminService(repo=repo)
        result = svc.list_colonne_admin(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["codice"], "ragione_sociale")

    # Scopo: il `count` NON e' `len(results)`. E' l'invariante che rende utile
    #        il guard anti-troncamento del frontend: derivato dalle righe
    #        direbbe sempre di si'. Il repo dichiara 40 e consegna 1 riga (il
    #        caso «qualcuno ha messo un LIMIT»): il service RIPORTA la
    #        divergenza, non la appiana.
    def test_count_colonne_non_e_derivato_dalle_righe(self) -> None:
        repo = _repo_with_lista()
        repo.list_colonne_by_lista_admin.return_value = [_row_colonna()]
        repo.count_colonne_by_lista_admin.return_value = 40
        svc = ListaColonnaAdminService(repo=repo)
        result = svc.list_colonne_admin(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 40)

    def test_get_colonna_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = None
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_colonna(999)
        self.assertEqual(ctx.exception.code, E_COLONNA_NOT_FOUND)

    def test_get_colonna_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna(id=42)
        svc = ListaColonnaAdminService(repo=repo)
        result = svc.get_colonna(42)
        self.assertEqual(result["id"], 42)


# ============================================================
# Create
# ============================================================

class ListaColonnaCreateTests(SimpleTestCase):
    def test_create_colonna_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 999, _payload_create_min())
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.create_colonna.assert_not_called()

    def test_create_colonna_chiavi_extra_raises(self) -> None:
        repo = _repo_with_lista()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 1, {
                **_payload_create_min(),
                "campo_inventato": True,
            })
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_create_colonna_happy_path_default_allineamento_left(self) -> None:
        repo = _repo_with_lista()
        repo.create_colonna.return_value = 100
        repo.get_colonna_admin.return_value = _row_colonna(id=100)
        svc = ListaColonnaAdminService(repo=repo)
        svc.create_colonna(_make_user(), 1, _payload_create_min())
        data = repo.create_colonna.call_args.args[0]
        self.assertEqual(data["allineamento"], "left")
        self.assertTrue(data["filtrabile"])
        self.assertTrue(data["ordinabile"])
        self.assertTrue(data["esportabile"])
        self.assertFalse(data["sensibile"])

    def test_create_colonna_tipo_colonna_invalido_raises(self) -> None:
        repo = _repo_with_lista()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 1, {
                **_payload_create_min(),
                "tipo_colonna": "boh",
            })
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_create_colonna_tipo_dato_invalido_raises(self) -> None:
        repo = _repo_with_lista()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 1, {
                **_payload_create_min(),
                "tipo_dato": "varchar",
            })
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_create_colonna_allineamento_invalido_raises(self) -> None:
        repo = _repo_with_lista()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 1, {
                **_payload_create_min(),
                "allineamento": "justify",
            })
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_create_colonna_unique_codice_violato(self) -> None:
        repo = _repo_with_lista()
        repo.create_colonna.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_ui_lista_colonna_lista_codice"'
        )
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_colonna(_make_user(), 1, _payload_create_min())
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_create_colonna_azione_forza_esportabile_false(self) -> None:
        repo = _repo_with_lista()
        repo.create_colonna.return_value = 100
        repo.get_colonna_admin.return_value = _row_colonna(id=100)
        svc = ListaColonnaAdminService(repo=repo)
        # Anche se l'utente passa esportabile=True esplicitamente, la
        # normalize lato BE forza False per coerenza con CHECK DB.
        svc.create_colonna(_make_user(), 1, {
            "codice": "edit_btn",
            "etichetta": "Modifica",
            "tipo_colonna": "azione",
            "tipo_dato": "string",
            "ordine_default": 99,
            "esportabile": True,
        })
        data = repo.create_colonna.call_args.args[0]
        self.assertEqual(data["tipo_colonna"], "azione")
        self.assertFalse(data["esportabile"])

    def test_create_colonna_campo_sorgente_null_ammesso(self) -> None:
        repo = _repo_with_lista()
        repo.create_colonna.return_value = 100
        repo.get_colonna_admin.return_value = _row_colonna(id=100)
        svc = ListaColonnaAdminService(repo=repo)
        # Colonna composta FE-only (vedi DEF-10): campo_sorgente NULL ok.
        svc.create_colonna(_make_user(), 1, {
            **_payload_create_min(),
            "codice": "sosp_riatt",
            "campo_sorgente": None,
        })
        data = repo.create_colonna.call_args.args[0]
        self.assertIsNone(data["campo_sorgente"])

    def test_create_colonna_etichetta_i18n_key_strip_to_null(self) -> None:
        repo = _repo_with_lista()
        repo.create_colonna.return_value = 100
        repo.get_colonna_admin.return_value = _row_colonna(id=100)
        svc = ListaColonnaAdminService(repo=repo)
        svc.create_colonna(_make_user(), 1, {
            **_payload_create_min(),
            "etichetta_i18n_key": "  ",
        })
        data = repo.create_colonna.call_args.args[0]
        self.assertIsNone(data["etichetta_i18n_key"])


# ============================================================
# Update
# ============================================================

class ListaColonnaUpdateTests(SimpleTestCase):
    def test_update_colonna_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = None
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_colonna(_make_user(), 999, {"etichetta": "X"})
        self.assertEqual(ctx.exception.code, E_COLONNA_NOT_FOUND)

    def test_update_colonna_lista_id_immutabile_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_colonna(_make_user(), 100, {"lista_id": 2})
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_update_colonna_payload_vuoto_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_colonna(_make_user(), 100, {})
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)

    def test_update_colonna_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        repo.update_colonna.return_value = True
        svc = ListaColonnaAdminService(repo=repo)
        svc.update_colonna(_make_user(), 100, {
            "etichetta": "Nuova etichetta",
            "ordine_default": 50,
        })
        data = repo.update_colonna.call_args.args[1]
        self.assertEqual(data["etichetta"], "Nuova etichetta")
        self.assertEqual(data["ordine_default"], 50)

    def test_update_colonna_passa_a_azione_forza_esportabile_false(self) -> None:
        repo = MagicMock()
        # Colonna corrente: tipo_colonna=informazione, esportabile=True.
        repo.get_colonna_admin.return_value = _row_colonna(
            tipo_colonna="informazione", esportabile=True
        )
        repo.update_colonna.return_value = True
        svc = ListaColonnaAdminService(repo=repo)
        # Cambio a azione: esportabile diventa False anche senza essere
        # passato nel payload.
        svc.update_colonna(_make_user(), 100, {
            "tipo_colonna": "azione",
        })
        data = repo.update_colonna.call_args.args[1]
        self.assertEqual(data["tipo_colonna"], "azione")
        self.assertFalse(data["esportabile"])

    def test_update_colonna_azione_corrente_blocca_esportabile_true(self) -> None:
        # Edge case: colonna corrente gia' di tipo azione; l'utente
        # tenta di passare esportabile=True senza toccare tipo_colonna.
        # Il service deve normalizzare a False (avrebbe fallito il CHECK
        # DB con messaggio meno parlante).
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna(
            tipo_colonna="azione", esportabile=False
        )
        repo.update_colonna.return_value = True
        svc = ListaColonnaAdminService(repo=repo)
        svc.update_colonna(_make_user(), 100, {"esportabile": True})
        data = repo.update_colonna.call_args.args[1]
        self.assertFalse(data["esportabile"])

    def test_update_colonna_attivo_null_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_colonna(_make_user(), 100, {"attivo": None})
        self.assertEqual(ctx.exception.code, E_COLONNA_VALIDATION)


# ============================================================
# Delete
# ============================================================

class ListaColonnaDeleteTests(SimpleTestCase):
    def test_delete_colonna_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = None
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_colonna(999)
        self.assertEqual(ctx.exception.code, E_COLONNA_NOT_FOUND)
        repo.delete_colonna.assert_not_called()

    def test_delete_colonna_in_uso_da_preferenze_raises_409(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        repo.count_preferenze_referenced_by_colonna.return_value = 3
        svc = ListaColonnaAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_colonna(100)
        self.assertEqual(ctx.exception.code, E_COLONNA_IN_USE)
        repo.delete_colonna.assert_not_called()
        repo.count_preferenze_referenced_by_colonna.assert_called_once_with(
            lista_id=1, codice="ragione_sociale",
        )

    def test_delete_colonna_happy_path_zero_preferenze(self) -> None:
        repo = MagicMock()
        repo.get_colonna_admin.return_value = _row_colonna()
        repo.count_preferenze_referenced_by_colonna.return_value = 0
        repo.delete_colonna.return_value = True
        svc = ListaColonnaAdminService(repo=repo)
        result = svc.delete_colonna(100)
        self.assertTrue(result["deleted"])
        self.assertEqual(result["id"], 100)
