# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.db.ui_admin_repository import UiAdminRepository
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

    # Scopo: happy path della lista preset — non esisteva, e la lista era
    #        l'unica delle quattro `ui` senza copertura sulla FORMA della
    #        risposta (`{results, count}`).
    def test_list_preset_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = {"id": 1}
        repo.list_preset_by_lista.return_value = [
            {"id": 7, "codice": "default", "ambito": "sistema"}
        ]
        repo.count_preset_by_lista.return_value = 1
        svc = ListaPresetAdminService(repo=repo)
        result = svc.list_preset(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["codice"], "default")

    # Scopo: il `count` NON e' `len(results)` — vedi il gemello in
    #        test_lista_colonna_admin_service.
    def test_count_preset_non_e_derivato_dalle_righe(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = {"id": 1}
        repo.list_preset_by_lista.return_value = [{"id": 7, "codice": "default"}]
        repo.count_preset_by_lista.return_value = 5
        svc = ListaPresetAdminService(repo=repo)
        result = svc.list_preset(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 5)

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


# Scopo: presidia l'SQL di `update_preset` / `update_definizione` dopo il
#        passaggio al BB `execute_dynamic_update` (2026-09-26): audit
#        `user_update` come parametro + `data_update = now()`, JSONB a
#        `::jsonb` con json.dumps, None che azzera, chiavi fuori whitelist
#        RIFIUTATE (RuntimeError, dal 2026-09-26: prima scartate in silenzio),
#        payload vuoto senza query.
class UiAdminRepositoryUpdateSqlTests(SimpleTestCase):
    def _esegui(self, azione):
        with patch("apps.core.db.sql_write_helpers.connection") as mock_conn:
            cursor = MagicMock()
            cursor.rowcount = 1
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            esito = azione(UiAdminRepository())
            return esito, cursor

    def test_update_preset_jsonb_audit_e_whitelist(self) -> None:
        esito, cursor = self._esegui(lambda r: r.update_preset(
            5,
            {
                "descrizione": "Base",
                "ordinamento_default": [{"campo": "codice", "dir": "asc"}],
                "filtri_default": None,
            },
            user_update="tester",
        ))
        self.assertTrue(esito)
        sql, params = cursor.execute.call_args.args
        self.assertTrue(sql.startswith("UPDATE ui.lista_preset SET "))
        self.assertIn("ordinamento_default = %s::jsonb", sql)
        self.assertIn("filtri_default = %s", sql)
        self.assertIn("user_update = %s", sql)
        self.assertIn("data_update = now()", sql)
        self.assertTrue(sql.endswith("WHERE id = %s"))
        self.assertEqual(
            params,
            ["Base", '[{"campo": "codice", "dir": "asc"}]', None, "tester", 5],
        )

    # ⛔ Un immutabile (`ambito`) che arrivasse fin qui e' un errore di
    #    programmazione — il service lo rifiuta prima con un 400 — e non uno
    #    scarto silenzioso: nessuna query parte.
    def test_update_preset_chiave_fuori_whitelist_rifiutata(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            self._esegui(lambda r: r.update_preset(
                5, {"descrizione": "Base", "ambito": "globale"}, user_update="tester",
            ))
        self.assertIn("ambito", str(ctx.exception))

    def test_update_preset_payload_vuoto_nessuna_query(self) -> None:
        esito, cursor = self._esegui(
            lambda r: r.update_preset(5, {}, user_update="tester")
        )
        self.assertFalse(esito)
        cursor.execute.assert_not_called()

    def test_update_definizione_audit(self) -> None:
        esito, cursor = self._esegui(lambda r: r.update_definizione(
            7, {"note": None, "attivo": False}, user_update="tester",
        ))
        self.assertTrue(esito)
        sql, params = cursor.execute.call_args.args
        self.assertEqual(
            sql,
            "UPDATE ui.lista_definizione SET note = %s, attivo = %s, "
            "user_update = %s, data_update = now() WHERE id = %s",
        )
        self.assertEqual(params, [None, False, "tester", 7])
