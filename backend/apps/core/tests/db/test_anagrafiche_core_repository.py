# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AnagraficheCoreRepository (building block soggetto PF).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_crea_soggetto_pf_sql_call — verifica SQL e parametri passati al cursor
 2) test_crea_soggetto_pf_returns_uuid — verifica che ritorni UUID come stringa
 3) test_crea_soggetto_pf_defaults — verifica valori default sesso e stato_iso2
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestAnagraficheCoreRepository(TestCase):
    """Test building block AnagraficheCoreRepository.crea_soggetto_pf()."""

    @patch("apps.core.db.anagrafiche_core_repository.connection")
    def test_crea_soggetto_pf_sql_call(self, mock_conn):
        """Verifica che la query SQL venga eseguita con i parametri corretti."""
        mock_cursor = MagicMock()
        test_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_cursor.fetchone.return_value = (test_uuid,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.anagrafiche_core_repository import AnagraficheCoreRepository

        repo = AnagraficheCoreRepository()
        result = repo.crea_soggetto_pf(
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA90A01H501X",
            email="mario@test.it",
        )

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("fn_crea_soggetto_pf", sql)
        self.assertEqual(params[0], "Rossi")
        self.assertEqual(params[1], "Mario")
        self.assertEqual(params[2], "RSSMRA90A01H501X")
        self.assertEqual(params[3], "mario@test.it")
        self.assertEqual(result, test_uuid)

    @patch("apps.core.db.anagrafiche_core_repository.connection")
    def test_crea_soggetto_pf_returns_uuid(self, mock_conn):
        """Verifica che ritorni UUID come stringa."""
        import uuid

        test_uuid = uuid.uuid4()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (test_uuid,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.anagrafiche_core_repository import AnagraficheCoreRepository

        repo = AnagraficheCoreRepository()
        result = repo.crea_soggetto_pf(
            cognome="Bianchi", nome="Anna",
            codice_fiscale="BNCNNA95B41H501Y", email="anna@test.it",
        )
        self.assertIsInstance(result, str)
        self.assertEqual(result, str(test_uuid))

    @patch("apps.core.db.anagrafiche_core_repository.connection")
    def test_crea_soggetto_pf_defaults(self, mock_conn):
        """Verifica valori default: sesso='M', stato_iso2='IT'."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("uuid-test",)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.anagrafiche_core_repository import AnagraficheCoreRepository

        repo = AnagraficheCoreRepository()
        repo.crea_soggetto_pf(
            cognome="Verdi", nome="Paolo",
            codice_fiscale="VRDPLA80C01H501Z", email="paolo@test.it",
        )

        _, params = mock_cursor.execute.call_args[0]
        # params[5] = sesso, params[6] = stato_iso2
        self.assertEqual(params[5], "M")
        self.assertEqual(params[6], "IT")
