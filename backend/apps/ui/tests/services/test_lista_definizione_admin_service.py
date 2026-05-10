# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaDefinizioneAdminService.
#        Fase 1 (read-only): Select header + catalogo colonne grezzo.
#        Fase 2 — DEF-5b (CRUD SUPER_ADMIN): create/update/delete con
#        mapping IntegrityError per UNIQUE codice e FK RESTRICT (in uso).
#        CI senza DB reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   Fase 1
#     0. list_definizioni_delegata_a_repo
#     1. list_colonne_lista_inesistente_raises
#     2. list_colonne_lista_happy_path
#   Fase 2 read
#     3. list_definizioni_admin_delegata_a_repo
#     4. get_definizione_inesistente_raises
#     5. get_definizione_happy_path_include_disattive
#   Fase 2 create
#     6. create_definizione_happy_path
#     7. create_definizione_chiavi_extra_raises
#     8. create_definizione_codice_obbligatorio
#     9. create_definizione_unique_codice_violato
#    10. create_definizione_vista_sql_e_note_strip_to_null
#    11. create_definizione_attivo_default_true
#   Fase 2 update
#    12. update_definizione_inesistente_raises
#    13. update_definizione_payload_vuoto_raises
#    14. update_definizione_happy_path
#    15. update_definizione_attivo_null_raises
#   Fase 2 delete
#    16. delete_definizione_inesistente_raises
#    17. delete_definizione_in_uso_raises_409
#    18. delete_definizione_happy_path
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_definizione_admin_service import (
    E_DEFINIZIONE_IN_USE,
    E_DEFINIZIONE_NOT_FOUND,
    E_DEFINIZIONE_VALIDATION,
    E_LISTA_NOT_FOUND,
    ListaDefinizioneAdminService,
)


def _make_user(username: str = "tester") -> Any:
    user = MagicMock()
    user.username = username
    user.is_authenticated = True
    return user


def _row_definizione_full(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": 7,
        "codice": "anagrafiche.clienti",
        "descrizione": "Clienti",
        "schema_dati": "anagrafiche",
        "vista_sql": "vw_clienti_lista",
        "note": None,
        "attivo": True,
        "data_insert": None,
        "user_insert": "tester",
        "data_update": None,
        "user_update": None,
    }
    base.update(overrides)
    return base


# ============================================================
# Fase 1 - Read (Select header + catalogo)
# ============================================================

class ListaDefinizioneFase1ReadTests(SimpleTestCase):
    def test_list_definizioni_delegata_a_repo(self) -> None:
        repo = MagicMock()
        repo.list_definizioni.return_value = [
            {"id": 1, "codice": "anagrafiche.clienti", "descrizione": "Clienti"},
        ]
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_definizioni()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "anagrafiche.clienti")
        repo.list_definizioni.assert_called_once_with()

    def test_list_colonne_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.list_colonne_lista(999)
        self.assertEqual(ctx.exception.code, E_LISTA_NOT_FOUND)
        repo.list_colonne_by_lista.assert_not_called()

    def test_list_colonne_lista_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = {"id": 1, "attivo": True}
        repo.list_colonne_by_lista.return_value = [
            {"id": 10, "codice": "ragione_sociale", "etichetta": "Ragione sociale"},
        ]
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_colonne_lista(1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "ragione_sociale")
        repo.list_colonne_by_lista.assert_called_once_with(1)


# ============================================================
# Fase 2 - Read admin
# ============================================================

class ListaDefinizioneFase2ReadTests(SimpleTestCase):
    def test_list_definizioni_admin_delegata_a_repo(self) -> None:
        repo = MagicMock()
        repo.list_definizioni_admin.return_value = [
            _row_definizione_full(),
            _row_definizione_full(id=8, codice="vendite.fatture", attivo=False),
        ]
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_definizioni_admin()
        self.assertEqual(len(result), 2)
        self.assertFalse(result[1]["attivo"])
        repo.list_definizioni_admin.assert_called_once_with()

    def test_get_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_definizione(999)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)

    def test_get_definizione_happy_path_include_disattive(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full(
            attivo=False
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.get_definizione(7)
        self.assertEqual(result["id"], 7)
        self.assertFalse(result["attivo"])


# ============================================================
# Fase 2 - Create
# ============================================================

class ListaDefinizioneFase2CreateTests(SimpleTestCase):
    def test_create_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 42
        repo.get_definizione_admin.return_value = _row_definizione_full(id=42)
        svc = ListaDefinizioneAdminService(repo=repo)

        result = svc.create_definizione(_make_user(), {
            "codice": "anagrafiche.fornitori",
            "descrizione": "Fornitori",
            "schema_dati": "anagrafiche",
            "vista_sql": "vw_fornitori_lista",
            "attivo": True,
        })

        self.assertEqual(result["id"], 42)
        repo.create_definizione.assert_called_once()
        data = repo.create_definizione.call_args.args[0]
        self.assertEqual(data["codice"], "anagrafiche.fornitori")
        self.assertEqual(data["vista_sql"], "vw_fornitori_lista")
        self.assertTrue(data["attivo"])

    def test_create_definizione_chiavi_extra_raises(self) -> None:
        repo = MagicMock()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione(_make_user(), {
                "codice": "x.y",
                "descrizione": "X",
                "schema_dati": "x",
                "campo_inventato": True,
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.create_definizione.assert_not_called()

    def test_create_definizione_codice_obbligatorio(self) -> None:
        repo = MagicMock()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione(_make_user(), {
                "descrizione": "X",
                "schema_dati": "x",
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.create_definizione.assert_not_called()

    def test_create_definizione_unique_codice_violato(self) -> None:
        repo = MagicMock()
        # IntegrityError con marker del vincolo UNIQUE sul codice.
        repo.create_definizione.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_ui_lista_definizione_codice"'
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione(_make_user(), {
                "codice": "duplicate.code",
                "descrizione": "Dup",
                "schema_dati": "x",
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)

    def test_create_definizione_vista_sql_e_note_strip_to_null(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 1
        repo.get_definizione_admin.return_value = _row_definizione_full(id=1)
        svc = ListaDefinizioneAdminService(repo=repo)
        # Stringa vuota -> None (pattern null_vs_empty).
        svc.create_definizione(_make_user(), {
            "codice": "x.y",
            "descrizione": "X",
            "schema_dati": "x",
            "vista_sql": "   ",
            "note": "",
        })
        data = repo.create_definizione.call_args.args[0]
        self.assertIsNone(data["vista_sql"])
        self.assertIsNone(data["note"])

    def test_create_definizione_attivo_default_true(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 1
        repo.get_definizione_admin.return_value = _row_definizione_full(id=1)
        svc = ListaDefinizioneAdminService(repo=repo)
        # `attivo` omesso -> True applicativo (workflow standard, non
        # draft).
        svc.create_definizione(_make_user(), {
            "codice": "x.y",
            "descrizione": "X",
            "schema_dati": "x",
        })
        data = repo.create_definizione.call_args.args[0]
        self.assertTrue(data["attivo"])


# ============================================================
# Fase 2 - Update
# ============================================================

class ListaDefinizioneFase2UpdateTests(SimpleTestCase):
    def test_update_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(_make_user(), 999, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.update_definizione.assert_not_called()

    def test_update_definizione_payload_vuoto_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(_make_user(), 7, {})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.update_definizione.assert_not_called()

    def test_update_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        repo.update_definizione.return_value = True
        svc = ListaDefinizioneAdminService(repo=repo)
        svc.update_definizione(_make_user(), 7, {
            "descrizione": "Clienti rinominati",
            "attivo": False,
        })
        repo.update_definizione.assert_called_once()
        data = repo.update_definizione.call_args.args[1]
        self.assertEqual(data["descrizione"], "Clienti rinominati")
        self.assertFalse(data["attivo"])

    def test_update_definizione_attivo_null_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(_make_user(), 7, {"attivo": None})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)


# ============================================================
# Fase 2 - Delete
# ============================================================

class ListaDefinizioneFase2DeleteTests(SimpleTestCase):
    def test_delete_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_definizione(999)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.delete_definizione.assert_not_called()

    def test_delete_definizione_in_uso_raises_409(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        # FK RESTRICT su lista_preferenza_utente.
        repo.delete_definizione.side_effect = IntegrityError(
            'update or delete on table "lista_definizione" violates '
            'foreign key constraint "fk_lista_preferenza_utente_lista_definizione"'
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_definizione(7)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_IN_USE)

    def test_delete_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        repo.delete_definizione.return_value = True
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.delete_definizione(7)
        self.assertTrue(result["deleted"])
        self.assertEqual(result["id"], 7)
