# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari DbopsRepository.check_lookup_id_exists.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DbopsRepositoryTests.test_check_lookup_id_exists_true
2) DbopsRepositoryTests.test_check_lookup_id_exists_false
3) DbopsRepositoryTests.test_check_lookup_id_exists_rel_non_consentita
4) (spostato sul DB vero: test_config_panel_registro_db, la lista e' in config.tabelle_gestibili)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


class DbopsRepositoryTests(TestCase):

    # Scopo: tabella CON colonna `attivo` → la query di esistenza filtra anche su attivo.
    @patch("apps.core.db.dbops_repository.connection")
    def test_check_lookup_id_exists_true_with_attivo(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        mock_cursor = MagicMock()
        # 1ª query: has_attivo? → True ; 2ª query: esistenza → True
        mock_cursor.fetchone.side_effect = [(True,), (True,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = DbopsRepository()
        result = repo.check_lookup_id_exists(rel="config.tipi_doc_fiscale", record_id=1)

        self.assertTrue(result)
        self.assertEqual(mock_cursor.execute.call_count, 2)
        # la query di esistenza (ultima) deve filtrare su attivo + usare la rel + l'id
        exists_sql = mock_cursor.execute.call_args_list[-1][0][0]
        self.assertIn("config.tipi_doc_fiscale", exists_sql)
        self.assertIn("attivo = true", exists_sql)
        self.assertEqual(mock_cursor.execute.call_args_list[-1][0][1], [1])

    # Scopo: tabella SENZA colonna `attivo` (es. config.utilities) → sola esistenza,
    #        nessun filtro su attivo (altrimenti UndefinedColumn).
    @patch("apps.core.db.dbops_repository.connection")
    def test_check_lookup_id_exists_no_attivo_column(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        mock_cursor = MagicMock()
        # 1ª query: has_attivo? → False ; 2ª query: esistenza → True
        mock_cursor.fetchone.side_effect = [(False,), (True,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = DbopsRepository()
        result = repo.check_lookup_id_exists(rel="config.utilities", record_id=5)

        self.assertTrue(result)
        exists_sql = mock_cursor.execute.call_args_list[-1][0][0]
        self.assertIn("config.utilities", exists_sql)
        self.assertNotIn("attivo", exists_sql)

    # Scopo: ID inesistente restituisce False (tabella senza attivo).
    @patch("apps.core.db.dbops_repository.connection")
    def test_check_lookup_id_exists_false(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(False,), (False,)]
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


