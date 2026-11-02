# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AuthRepository (building block auth_user).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_crea_auth_user_sql_call — verifica SQL e parametri passati al cursor
 2) test_crea_auth_user_returns_id — verifica che ritorni auth_user.id
 3) test_crea_auth_user_optional_names — verifica passaggio first/last name opzionali
 4) test_find_identita_ruoli_vuoti — ruoli_applicativi vuoto: None senza query
 5) test_find_identita_match — query filtra per auth_user + ruolo + attivo
 6) test_find_identita_no_match — nessuna identita: ritorna None
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestAuthRepository(TestCase):
    """Test building block AuthRepository.crea_auth_user()."""

    @patch("apps.core.db.auth_repository.connection")
    def test_crea_auth_user_sql_call(self, mock_conn):
        """Verifica che la query SQL venga eseguita con i parametri corretti."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        result = repo.crea_auth_user(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_pw",
        )

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("fn_crea_auth_user", sql)
        self.assertEqual(params[0], "test_user")
        self.assertEqual(params[1], "test@example.com")
        self.assertEqual(params[2], "hashed_pw")
        self.assertEqual(result, 42)

    @patch("apps.core.db.auth_repository.connection")
    def test_crea_auth_user_returns_id(self, mock_conn):
        """Verifica che ritorni l'id corretto."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (99,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        result = repo.crea_auth_user(
            username="admin", email="admin@test.it", password_hash="hash123",
        )
        self.assertEqual(result, 99)

    @patch("apps.core.db.auth_repository.connection")
    def test_crea_auth_user_optional_names(self, mock_conn):
        """Verifica che first_name e last_name vengano passati al SQL."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (10,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        repo.crea_auth_user(
            username="user1",
            email="user1@test.it",
            password_hash="hash",
            first_name="Mario",
            last_name="Rossi",
        )

        _, params = mock_cursor.execute.call_args[0]
        self.assertEqual(params[3], "Mario")
        self.assertEqual(params[4], "Rossi")

    @patch("apps.core.db.auth_repository.connection")
    def test_find_identita_ruoli_vuoti(self, mock_conn):
        """Con ruoli_applicativi vuoto il metodo ritorna None senza
        toccare il DB (short-circuit per evitare query inutili e per
        non generare `ANY([])` che su enum Postgres e' ambiguo)."""
        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        result = repo.find_veste_utilizzabile_per_ruoli(auth_user_id=1, ruoli_applicativi=[])

        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()

    @patch("apps.core.db.auth_repository.connection")
    def test_find_identita_match(self, mock_conn):
        """Verifica SQL + parametri e dict ritornato quando l'identita esiste."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (99, 7, "OPERATORE")
        # psycopg.cursor.description espone oggetti con attr `.name`.
        # SimpleNamespace e' il modo piu' pulito: MagicMock(name=...) usa
        # il kwarg `name` solo come display, non setta l'attributo.
        mock_cursor.description = [
            SimpleNamespace(name="id"),
            SimpleNamespace(name="soggetto_ruolo_id"),
            SimpleNamespace(name="ruolo_applicativo"),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        result = repo.find_veste_utilizzabile_per_ruoli(
            auth_user_id=42, ruoli_applicativi=("OPERATORE", "CLIENTE_PORTALE")
        )

        self.assertEqual(result, {"id": 99, "soggetto_ruolo_id": 7, "ruolo_applicativo": "OPERATORE"})
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("anagrafiche.identita_digitali", sql)
        # La regola «utilizzabile» la decide il DB: il Python non la riscrive.
        self.assertIn("script.fn_veste_utilizzabile(id)", sql)
        self.assertNotIn("attivo = true", sql)
        self.assertIn("ruolo_applicativo::text = ANY", sql)
        self.assertEqual(params[0], 42)
        self.assertEqual(params[1], ["OPERATORE", "CLIENTE_PORTALE"])

    @patch("apps.core.db.auth_repository.connection")
    def test_find_identita_no_match(self, mock_conn):
        """Nessuna identita per i ruoli richiesti: ritorna None."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.auth_repository import AuthRepository

        repo = AuthRepository()
        result = repo.find_veste_utilizzabile_per_ruoli(
            auth_user_id=42, ruoli_applicativi=("OPERATORE",)
        )

        self.assertIsNone(result)
