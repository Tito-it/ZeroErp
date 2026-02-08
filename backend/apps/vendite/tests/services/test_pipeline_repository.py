# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository pipeline vendite.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_list_from_jsonb_list
2) VenditePipelineRepositoryUnitTests.test_get_step_processes_decodes_jsonb_string_list
3) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_empty_on_invalid_json
"""

from unittest.mock import MagicMock
from unittest.mock import patch
from unittest import TestCase

from apps.vendite.db.pipeline_repository import VenditePipelineRepository


class VenditePipelineRepositoryUnitTests(TestCase):
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_list_from_jsonb_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ([{"task": "select_attivita"}],)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "select_attivita"}])

    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_decodes_jsonb_string_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('[{"task":"generate_fatture_righe"}]',)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "generate_fatture_righe"}])

    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_empty_on_invalid_json(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("not-a-json",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [])
