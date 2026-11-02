# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository categorie_clienti_listini.
#        Verificano il readback lista/dettaglio senza dipendenza da DB reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_get_matrice_joins_tipi_ruoli_for_emittente_codice
2) test_list_matrice_uses_tipi_ruoli_join_and_not_legacy_sr_codice_ruolo
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.anagrafiche.db.categorie_clienti_listini_repository import (
    CategorieClientiListiniRepository,
)


def _mock_cursor_ctx(mocked_cursor_factory):
    """Scopo: Configura il context manager del cursor mockato."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    mocked_cursor_factory.return_value = cursor
    return cursor


class CategorieClientiListiniRepositoryTests(TestCase):
    @patch("apps.anagrafiche.db.categorie_clienti_listini_repository.connection.cursor")
    def test_get_matrice_joins_tipi_ruoli_for_emittente_codice(self, mocked_cursor_factory):
        """Dettaglio: il codice ruolo emittente arriva da config.tipi_ruoli."""
        cursor = _mock_cursor_ctx(mocked_cursor_factory)
        cursor.description = [MagicMock(name="id")]
        cursor.description[0].name = "id"
        cursor.fetchone.return_value = (7,)

        repo = CategorieClientiListiniRepository()
        result = repo.get_matrice(7)

        self.assertEqual(result, {"id": 7})
        sql, params = cursor.execute.call_args.args
        self.assertIn("JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id", sql)
        self.assertIn("COALESCE(tr.codice_interno, tr.codice) AS emittente_codice_ruolo", sql)
        self.assertNotIn("sr.codice_ruolo", sql)
        self.assertEqual(params, [7])

    @patch("apps.anagrafiche.db.categorie_clienti_listini_repository.connection.cursor")
    def test_list_matrice_uses_tipi_ruoli_join_and_not_legacy_sr_codice_ruolo(self, mocked_cursor_factory):
        """Lista: count+select usano il join corretto e non la colonna legacy inesistente."""
        cursor = _mock_cursor_ctx(mocked_cursor_factory)
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        cursor.description = [MagicMock(name="id")]
        cursor.description[0].name = "id"

        repo = CategorieClientiListiniRepository()
        results, total_count = repo.list_matrice(limit=10, offset=0)

        self.assertEqual(results, [])
        self.assertEqual(total_count, 0)
        self.assertEqual(cursor.execute.call_count, 2)

        count_sql = cursor.execute.call_args_list[0].args[0]
        list_sql = cursor.execute.call_args_list[1].args[0]

        self.assertIn("JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id", count_sql)
        self.assertIn("JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id", list_sql)
        self.assertIn("COALESCE(tr.codice_interno, tr.codice) AS emittente_codice_ruolo", list_sql)
        self.assertNotIn("sr.codice_ruolo", count_sql)
        self.assertNotIn("sr.codice_ruolo", list_sql)
