# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari DbopsRepository.check_lookup_id_exists.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DbopsRepositoryTests.test_check_lookup_id_exists_true
2) DbopsRepositoryTests.test_check_lookup_id_exists_false
3) DbopsRepositoryTests.test_check_lookup_id_exists_rel_non_consentita
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


class DbopsRepositoryTests(TestCase):

    # Scopo: ID esistente e attivo restituisce True.
    @patch("apps.core.db.dbops_repository.connection")
    def test_check_lookup_id_exists_true(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (True,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = DbopsRepository()
        result = repo.check_lookup_id_exists(rel="config.tipi_doc_fiscale", record_id=1)

        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()
        sql_arg = mock_cursor.execute.call_args[0][0]
        self.assertIn("config.tipi_doc_fiscale", sql_arg)
        self.assertEqual(mock_cursor.execute.call_args[0][1], [1])

    # Scopo: ID inesistente o non attivo restituisce False.
    @patch("apps.core.db.dbops_repository.connection")
    def test_check_lookup_id_exists_false(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (False,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = DbopsRepository()
        result = repo.check_lookup_id_exists(rel="config.utilities", record_id=999)

        self.assertFalse(result)

    # Scopo: Relazione non in whitelist solleva ServiceError.
    def test_check_lookup_id_exists_rel_non_consentita(self):
        from apps.core.db.dbops_repository import DbopsRepository

        repo = DbopsRepository()
        with self.assertRaises(ServiceError) as ctx:
            repo.check_lookup_id_exists(rel="public.tabella_segreta", record_id=1)
        self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")
