# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaPresetAdminService — Blocco F admin CRUD su
#        ui.lista_preset + composizione (lista_preset_colonna).
#        CI senza DB reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   0. list_preset_lista_inesistente_raises
#   1. get_preset_inesistente_raises
#   2. create_preset_sistema_happy_path
#   3. create_preset_ruolo_richiede_profilo
#   4. create_preset_emittente_richiede_emittente
#   5. create_preset_chiavi_extra_raises
#   6. create_preset_ambito_invalido_raises
#   7. create_preset_lista_inesistente_raises
#   8. update_preset_immutabili_raises
#   9. update_preset_payload_vuoto_raises
#  10. update_preset_happy_path
#  11. delete_preset_inesistente_raises
#  12. delete_preset_happy_path
#  13. replace_preset_colonne_happy_path
#  14. replace_preset_colonne_duplicato_raises
#  15. replace_preset_colonne_payload_non_lista_raises
#  16. replace_preset_colonne_chiavi_extra_riga_raises
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_preset_admin_service import (
    E_LISTA_NOT_FOUND,
    E_PRESET_NOT_FOUND,
    E_PRESET_VALIDATION,
    ListaPresetAdminService,
)


def _make_user(username: str = "tester") -> Any:
    user = MagicMock()
    user.username = username
    user.is_authenticated = True
    return user


def _repo_with_lista_attiva() -> MagicMock:
    repo = MagicMock()
    repo.get_definizione.return_value = {
        "id": 1,
        "codice": "anagrafiche.clienti",
        "descrizione": "Clienti",
        "schema_dati": "anagrafiche",
        "attivo": True,
    }
    return repo


class ListaPresetAdminReadTests(SimpleTestCase):
    def test_list_preset_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = None
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.list_preset(999)
        self.assertEqual(ctx.exception.code, E_LISTA_NOT_FOUND)
        repo.list_preset_by_lista.assert_not_called()

    def test_get_preset_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = None
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_preset(999)
        self.assertEqual(ctx.exception.code, E_PRESET_NOT_FOUND)


class ListaPresetAdminCreateTests(SimpleTestCase):
    def test_create_preset_sistema_happy_path(self) -> None:
        repo = _repo_with_lista_attiva()
        repo.create_preset.return_value = 7
        repo.get_preset.return_value = {"id": 7, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)

        result = svc.create_preset(_make_user(), {
            "lista_id": 1,
            "codice": "default",
            "descrizione": "Default sistema",
            "ambito": "sistema",
            "is_default": True,
            "pagina_dimensione": 50,
            "ordinamento_default": [{"col": "id", "dir": "asc"}],
            "filtri_default": {"attivo": True},
        })

        self.assertEqual(result["id"], 7)
        repo.create_preset.assert_called_once()
        data = repo.create_preset.call_args.args[0]
        self.assertEqual(data["ambito"], "sistema")
        # Refs azzerati per ambito sistema.
        self.assertIsNone(data["profilo_accesso_id"])
        self.assertIsNone(data["emittente_fiscale_id"])

    def test_create_preset_ruolo_richiede_profilo(self) -> None:
        repo = _repo_with_lista_attiva()
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_preset(_make_user(), {
                "lista_id": 1,
                "codice": "p_ruolo",
                "descrizione": "Ruolo",
                "ambito": "ruolo",
                # profilo_accesso_id mancante
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)
        repo.create_preset.assert_not_called()

    def test_create_preset_emittente_richiede_emittente(self) -> None:
        repo = _repo_with_lista_attiva()
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_preset(_make_user(), {
                "lista_id": 1,
                "codice": "p_em",
                "descrizione": "Emittente",
                "ambito": "emittente_fiscale",
                # emittente_fiscale_id mancante
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)

    def test_create_preset_chiavi_extra_raises(self) -> None:
        repo = _repo_with_lista_attiva()
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_preset(_make_user(), {
                "lista_id": 1,
                "codice": "x",
                "descrizione": "X",
                "ambito": "sistema",
                "malicious_field": "drop_table",
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)

    def test_create_preset_ambito_invalido_raises(self) -> None:
        repo = _repo_with_lista_attiva()
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_preset(_make_user(), {
                "lista_id": 1,
                "codice": "x",
                "descrizione": "X",
                "ambito": "qualcos_altro",
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)

    def test_create_preset_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = None
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_preset(_make_user(), {
                "lista_id": 999,
                "codice": "x",
                "descrizione": "X",
                "ambito": "sistema",
            })
        self.assertEqual(ctx.exception.code, E_LISTA_NOT_FOUND)


class ListaPresetAdminUpdateTests(SimpleTestCase):
    def test_update_preset_immutabili_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_preset(_make_user(), 5, {
                "lista_id": 99,  # immutabile
                "codice": "rename",
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)
        repo.update_preset.assert_not_called()

    def test_update_preset_payload_vuoto_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_preset(_make_user(), 5, {})
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)

    def test_update_preset_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        repo.update_preset.return_value = True
        svc = ListaPresetAdminService(repo=repo)

        svc.update_preset(_make_user(), 5, {
            "descrizione": "Nuova",
            "is_default": False,
            "pagina_dimensione": 100,
        })

        repo.update_preset.assert_called_once()
        update_data = repo.update_preset.call_args.args[1]
        self.assertEqual(update_data["descrizione"], "Nuova")
        self.assertIs(update_data["is_default"], False)
        self.assertEqual(update_data["pagina_dimensione"], 100)


class ListaPresetAdminDeleteTests(SimpleTestCase):
    def test_delete_preset_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.delete_preset.return_value = False
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_preset(404)
        self.assertEqual(ctx.exception.code, E_PRESET_NOT_FOUND)

    def test_delete_preset_happy_path(self) -> None:
        repo = MagicMock()
        repo.delete_preset.return_value = True
        svc = ListaPresetAdminService(repo=repo)
        result = svc.delete_preset(7)
        self.assertEqual(result, {"deleted": True, "id": 7})


class ListaPresetAdminColonneTests(SimpleTestCase):
    def test_replace_preset_colonne_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        repo.replace_preset_colonne.return_value = 2
        svc = ListaPresetAdminService(repo=repo)

        result = svc.replace_preset_colonne(5, {
            "colonne": [
                {"colonna_id": 1, "ordine": 1, "visibile": True},
                {"colonna_id": 2, "ordine": 2, "larghezza": 100},
            ],
        })
        self.assertEqual(result, {"preset_id": 5, "inserted": 2})

    def test_replace_preset_colonne_duplicato_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.replace_preset_colonne(5, {
                "colonne": [
                    {"colonna_id": 1, "ordine": 1},
                    {"colonna_id": 1, "ordine": 2},  # duplicato
                ],
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)
        repo.replace_preset_colonne.assert_not_called()

    def test_replace_preset_colonne_payload_non_lista_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.replace_preset_colonne(5, {"colonne": "non-una-lista"})
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)

    def test_replace_preset_colonne_chiavi_extra_riga_raises(self) -> None:
        repo = MagicMock()
        repo.get_preset.return_value = {"id": 5, "ambito": "sistema"}
        svc = ListaPresetAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.replace_preset_colonne(5, {
                "colonne": [
                    {"colonna_id": 1, "ordine": 1, "rogue": "x"},
                ],
            })
        self.assertEqual(ctx.exception.code, E_PRESET_VALIDATION)
