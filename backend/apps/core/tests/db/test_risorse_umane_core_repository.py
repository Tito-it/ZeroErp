# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per RisorseUmaneCoreRepository (building block risorsa umana).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_crea_risorsa_umana_sql_call — verifica SQL e parametri
 2) test_crea_risorsa_umana_returns_id — verifica che ritorni risorse_umane.id
 3) test_crea_risorsa_umana_with_auth_user — verifica passaggio auth_user_id
 4) test_crea_risorsa_umana_without_auth_user — verifica che auth_user_id sia None
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestRisorseUmaneCoreRepository(TestCase):
    """Test building block RisorseUmaneCoreRepository.crea_risorsa_umana()."""

    @patch("apps.core.db.risorse_umane_core_repository.connection")
    def test_crea_risorsa_umana_sql_call(self, mock_conn):
        """Verifica che la query SQL venga eseguita con i parametri corretti."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository

        repo = RisorseUmaneCoreRepository()
        result = repo.crea_risorsa_umana(
            soggetto_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            qualifica_id=1,
            unita_organizzativa_id=10,
            auth_user_id=42,
        )

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("fn_crea_risorsa_umana", sql)
        self.assertEqual(params[0], "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        self.assertEqual(params[1], 1)
        self.assertEqual(params[2], 10)
        self.assertEqual(result, 100)

    @patch("apps.core.db.risorse_umane_core_repository.connection")
    def test_crea_risorsa_umana_returns_id(self, mock_conn):
        """Verifica che ritorni risorse_umane.id corretto."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (555,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository

        repo = RisorseUmaneCoreRepository()
        result = repo.crea_risorsa_umana(
            soggetto_id="uuid-test", qualifica_id=2,
        )
        self.assertEqual(result, 555)

    @patch("apps.core.db.risorse_umane_core_repository.connection")
    def test_crea_risorsa_umana_with_auth_user(self, mock_conn):
        """Verifica che auth_user_id + flag multi-face vengano passati al SQL."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (200,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository

        repo = RisorseUmaneCoreRepository()
        repo.crea_risorsa_umana(
            soggetto_id="uuid-test", qualifica_id=1,
            auth_user_id=42, is_super_admin=True, attivo=True,
        )

        sql, params = mock_cursor.execute.call_args[0]
        # Step 6 Fase 7: contract multi-face puro. La fn DB v2 accetta
        # p_is_super_admin/p_attivo come bool. Niente piu' p_ruolo_sistema.
        self.assertNotIn("p_ruolo_sistema", sql)
        self.assertIn("p_is_super_admin", sql)
        self.assertIn("p_attivo", sql)
        # params[5] = auth_user_id, params[6] = is_super_admin, params[7] = attivo
        self.assertEqual(params[5], 42)
        self.assertTrue(params[6])
        self.assertTrue(params[7])

    @patch("apps.core.db.risorse_umane_core_repository.connection")
    def test_crea_risorsa_umana_without_auth_user(self, mock_conn):
        """Verifica che auth_user_id sia None quando non fornito."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (300,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository

        repo = RisorseUmaneCoreRepository()
        repo.crea_risorsa_umana(
            soggetto_id="uuid-test", qualifica_id=1,
        )

        _, params = mock_cursor.execute.call_args[0]
        # params[5] = auth_user_id (dovrebbe essere None)
        self.assertIsNone(params[5])
