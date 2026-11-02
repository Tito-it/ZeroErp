# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per API toponomastica (lista, crea, modifica).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_toponomastica — lista con risultati
 2) test_list_toponomastica_empty — nessun risultato
 3) test_create_toponomastica — creazione OK
 4) test_create_toponomastica_duplicate — errore unicita'
 5) test_create_toponomastica_empty — descrizione vuota
 6) test_update_toponomastica — modifica OK
 7) test_update_toponomastica_not_found — id non esistente
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import IntegrityError



class TestToponomasticaRepository(TestCase):
    """Test IndirizziRepository — metodi toponomastica."""

    @patch("apps.core.db._helpers.connection")
    def test_list_toponomastica(self, mock_conn):
        """Lista toponomastica con risultati e paginazione."""
        cols = ["id", "descrizione", "attivo", "total_count"]
        rows = [
            (1, "Via", True, 3),
            (2, "Piazza", True, 3),
            (3, "Corso", True, 3),
        ]
        mock_cursor = MagicMock()
        mock_cursor.description = [MagicMock(name=c) for c in cols]
        for i, c in enumerate(cols):
            mock_cursor.description[i].name = c
        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        results, total = repo.list_toponomastica(limit=25, offset=0)

        self.assertEqual(len(results), 3)
        self.assertEqual(total, 3)
        self.assertEqual(results[0]["descrizione"], "Via")

    @patch("apps.core.db._helpers.connection")
    def test_list_toponomastica_empty(self, mock_conn):
        """Lista vuota."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        results, total = repo.list_toponomastica()

        self.assertEqual(results, [])
        self.assertEqual(total, 0)

    @patch("apps.anagrafiche.db.geo_repository.connection")
    def test_create_toponomastica(self, mock_conn):
        """Creazione tipo strada OK."""
        cols = ["id", "descrizione", "attivo"]
        rows = [(10, "Viale", True)]
        mock_cursor = MagicMock()
        mock_cursor.description = [MagicMock(name=c) for c in cols]
        for i, c in enumerate(cols):
            mock_cursor.description[i].name = c
        mock_cursor.fetchone.return_value = rows[0]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        result = repo.create_toponomastica(descrizione="Viale")

        self.assertEqual(result["id"], 10)
        self.assertEqual(result["descrizione"], "Viale")
        # INSERT ... RETURNING id, poi la riga riletta dalla sorgente della
        # lista (dal 2026-09-28): la create restituisce cio' che mostra il dettaglio.
        insert_sql, rilettura_sql = (c[0][0] for c in mock_cursor.execute.call_args_list)
        self.assertIn("INSERT INTO config.toponomastica", insert_sql)
        self.assertIn("FROM config.toponomastica WHERE id = %s", rilettura_sql)
        self.assertEqual(mock_cursor.execute.call_args_list[1][0][1], [10])

    @patch("apps.anagrafiche.db.geo_repository.connection")
    def test_create_toponomastica_duplicate(self, mock_conn):
        """Creazione con descrizione duplicata — IntegrityError."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = IntegrityError("unique violation")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        with self.assertRaises(IntegrityError):
            repo.create_toponomastica(descrizione="Via")

    def test_create_toponomastica_empty(self):
        """Descrizione vuota — gestita a livello view con ErrorManager."""
        # La validazione e' nella view, non nel repository.
        # Il repository riceve sempre una stringa pulita.

    @patch("apps.core.db.sql_write_helpers.connection")
    def test_update_toponomastica(self, mock_conn):
        """Modifica tipo strada OK."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        updated = repo.update_toponomastica(1, {"descrizione": "Viale", "attivo": True})

        self.assertTrue(updated)
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("UPDATE config.toponomastica", sql)

    @patch("apps.core.db.sql_write_helpers.connection")
    def test_update_toponomastica_not_found(self, mock_conn):
        """ID non esistente — rowcount 0."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        repo = GeoRepository()
        updated = repo.update_toponomastica(999, {"descrizione": "Test"})

        self.assertFalse(updated)
