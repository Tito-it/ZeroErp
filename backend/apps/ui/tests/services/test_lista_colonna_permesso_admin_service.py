# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaColonnaPermessoAdminService — Blocco F admin
#        UPSERT/DELETE su ui.lista_colonna_permesso. CI senza DB reale
#        (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   0. list_permessi_lista_inesistente_raises
#   1. list_permessi_happy_path
#   2. upsert_happy_path
#   3. upsert_chiavi_extra_raises
#   4. upsert_livello_invalido_raises
#   5. upsert_colonna_id_mancante_raises
#   6. delete_inesistente_raises
#   7. delete_happy_path
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_colonna_permesso_admin_service import (
    E_LISTA_NOT_FOUND,
    E_PERMESSO_NOT_FOUND,
    E_PERMESSO_VALIDATION,
    ListaColonnaPermessoAdminService,
)


def _make_user(username: str = "tester") -> Any:
    user = MagicMock()
    user.username = username
    user.is_authenticated = True
    return user


def _repo_lista_attiva() -> MagicMock:
    repo = MagicMock()
    repo.get_definizione.return_value = {
        "id": 1,
        "codice": "anagrafiche.clienti",
        "descrizione": "Clienti",
        "schema_dati": "anagrafiche",
        "attivo": True,
    }
    return repo


class ListaColonnaPermessoListTests(SimpleTestCase):
    def test_list_permessi_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = None
        svc = ListaColonnaPermessoAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.list_permessi(404)
        self.assertEqual(ctx.exception.code, E_LISTA_NOT_FOUND)

    def test_list_permessi_happy_path(self) -> None:
        repo = _repo_lista_attiva()
        repo.list_permessi_by_lista.return_value = [
            {
                "id": 1,
                "colonna_id": 10,
                "colonna_codice": "stato",
                "profilo_accesso_id": 9001,
                "profilo_accesso_codice": "CLIENTE_PORTALE_STANDARD",
                "livello_accesso": "BLOCCATO",
            }
        ]
        repo.count_permessi_by_lista.return_value = 1
        svc = ListaColonnaPermessoAdminService(repo=repo)
        result = svc.list_permessi(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["livello_accesso"], "BLOCCATO")

    # Scopo: il `count` NON e' `len(results)` — vedi il gemello in
    #        test_lista_colonna_admin_service. Qui vale doppio: il conteggio
    #        replica gli INNER JOIN della lista, quindi deve contare lo stesso
    #        PERIMETRO pur restando indipendente dalle RIGHE.
    def test_count_permessi_non_e_derivato_dalle_righe(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = {"id": 1}
        repo.list_permessi_by_lista.return_value = [{"id": 1, "livello_accesso": "BLOCCATO"}]
        repo.count_permessi_by_lista.return_value = 12
        svc = ListaColonnaPermessoAdminService(repo=repo)
        result = svc.list_permessi(1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 12)


class ListaColonnaPermessoUpsertTests(SimpleTestCase):
    def test_upsert_happy_path(self) -> None:
        repo = MagicMock()
        repo.upsert_permesso.return_value = 42
        svc = ListaColonnaPermessoAdminService(repo=repo)
        result = svc.upsert_permesso(_make_user(), {
            "colonna_id": 10,
            "profilo_accesso_id": 9001,
            "livello_accesso": "LETTURA",
        })
        self.assertEqual(result["id"], 42)
        self.assertEqual(result["livello_accesso"], "LETTURA")
        repo.upsert_permesso.assert_called_once()

    def test_upsert_chiavi_extra_raises(self) -> None:
        repo = MagicMock()
        svc = ListaColonnaPermessoAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert_permesso(_make_user(), {
                "colonna_id": 10,
                "profilo_accesso_id": 9001,
                "livello_accesso": "TUTTO",
                "rogue": "x",
            })
        self.assertEqual(ctx.exception.code, E_PERMESSO_VALIDATION)

    def test_upsert_livello_invalido_raises(self) -> None:
        repo = MagicMock()
        svc = ListaColonnaPermessoAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert_permesso(_make_user(), {
                "colonna_id": 10,
                "profilo_accesso_id": 9001,
                "livello_accesso": "QUALCOSALTRO",
            })
        self.assertEqual(ctx.exception.code, E_PERMESSO_VALIDATION)

    def test_upsert_colonna_id_mancante_raises(self) -> None:
        repo = MagicMock()
        svc = ListaColonnaPermessoAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.upsert_permesso(_make_user(), {
                "profilo_accesso_id": 9001,
                "livello_accesso": "LETTURA",
            })
        self.assertEqual(ctx.exception.code, E_PERMESSO_VALIDATION)


class ListaColonnaPermessoDeleteTests(SimpleTestCase):
    def test_delete_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.delete_permesso.return_value = False
        svc = ListaColonnaPermessoAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_permesso(404)
        self.assertEqual(ctx.exception.code, E_PERMESSO_NOT_FOUND)

    def test_delete_happy_path(self) -> None:
        repo = MagicMock()
        repo.delete_permesso.return_value = True
        svc = ListaColonnaPermessoAdminService(repo=repo)
        result = svc.delete_permesso(7)
        self.assertEqual(result, {"deleted": True, "id": 7})
