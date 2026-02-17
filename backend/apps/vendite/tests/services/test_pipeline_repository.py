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
4) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_maps_rows
5) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_returns_empty_list
"""

from unittest.mock import MagicMock
from unittest.mock import patch
from unittest import TestCase
from datetime import date
from decimal import Decimal

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

    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_maps_rows(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                101, 2001, 1, 3, "2026/A/123", 123, date(2026, 2, 17),
                501, 601, 1, Decimal("99.50"),
            )
        ]
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fattura_sdi_id, 101)
        self.assertEqual(result[0].fattura_id, 2001)
        self.assertEqual(result[0].codice_documento, "2026/A/123")
        self.assertEqual(result[0].billing_account_id, 501)
        self.assertEqual(result[0].emittente_soggetto_ruolo_id, 601)

    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_returns_empty_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = []
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(result, [])
