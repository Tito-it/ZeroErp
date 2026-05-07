# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaDefinizioneAdminService — Blocco F admin
#        read-only (Select header + catalogo colonne grezzo).
#
# Indice test (0..N):
#   0. list_definizioni_delegata_a_repo
#   1. list_colonne_lista_inesistente_raises
#   2. list_colonne_lista_happy_path
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_definizione_admin_service import (
    E_LISTA_NOT_FOUND,
    ListaDefinizioneAdminService,
)


class ListaDefinizioneAdminTests(SimpleTestCase):
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
