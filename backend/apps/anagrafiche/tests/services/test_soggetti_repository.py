# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository soggetti.
#        Verifica normalizzazione campo `ruoli` (jsonb_agg) che psycopg
#        in alcune configurazioni ritorna come stringa anziche' lista.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_list_soggetti_normalizes_ruoli_string_to_list — psycopg ritorna ruoli come stringa JSON
2) test_list_soggetti_keeps_ruoli_list_unchanged       — psycopg ritorna ruoli gia' lista
3) test_list_soggetti_handles_ruoli_none               — ruoli None → lista vuota
4) test_list_soggetti_handles_ruoli_malformed_string   — JSON malformato → lista vuota fail-safe
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.anagrafiche.db.soggetti_repository import SoggettiRepository


def _mock_cursor_with_row(mocked_cursor_factory, ruoli_value):
    """Scopo: Configura il cursor mockato con una row che contiene ruoli."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    mocked_cursor_factory.return_value = cursor
    descr = []
    for name in ("id", "ragione_sociale_completa", "ruoli", "total_count"):
        col = MagicMock()
        col.name = name
        descr.append(col)
    cursor.description = descr
    cursor.fetchall.return_value = [
        ("uuid-1", "Rossi Mario", ruoli_value, 1),
    ]
    return cursor


class SoggettiRepositoryListRuoliTests(TestCase):
    """Verifica del fix A1 — normalizzazione campo ruoli jsonb."""

    @patch("apps.anagrafiche.db.soggetti_repository.connection.cursor")
    def test_list_soggetti_normalizes_ruoli_string_to_list(self, mocked_factory):
        """Caso reale: psycopg ritorna ruoli come stringa JSON → deve diventare list."""
        ruoli_str = '[{"soggetto_ruolo_id": 1, "codice": "CL", "descrizione": "Cliente"}]'
        _mock_cursor_with_row(mocked_factory, ruoli_str)

        results, total = SoggettiRepository().list_soggetti()

        self.assertEqual(total, 1)
        self.assertIsInstance(results[0]["ruoli"], list)
        self.assertEqual(len(results[0]["ruoli"]), 1)
        self.assertEqual(results[0]["ruoli"][0]["codice"], "CL")

    @patch("apps.anagrafiche.db.soggetti_repository.connection.cursor")
    def test_list_soggetti_keeps_ruoli_list_unchanged(self, mocked_factory):
        """psycopg con json decoder registrato → ruoli arriva gia' lista, non toccare."""
        ruoli_list = [{"soggetto_ruolo_id": 2, "codice": "FO", "descrizione": "Fornitore"}]
        _mock_cursor_with_row(mocked_factory, ruoli_list)

        results, _ = SoggettiRepository().list_soggetti()

        self.assertIsInstance(results[0]["ruoli"], list)
        self.assertEqual(results[0]["ruoli"], ruoli_list)

    @patch("apps.anagrafiche.db.soggetti_repository.connection.cursor")
    def test_list_soggetti_handles_ruoli_none(self, mocked_factory):
        """ruoli None (caso degenere) → lista vuota."""
        _mock_cursor_with_row(mocked_factory, None)

        results, _ = SoggettiRepository().list_soggetti()

        self.assertEqual(results[0]["ruoli"], [])

    @patch("apps.anagrafiche.db.soggetti_repository.connection.cursor")
    def test_list_soggetti_handles_ruoli_malformed_string(self, mocked_factory):
        """Stringa JSON malformata → fail-safe a lista vuota, non solleva."""
        _mock_cursor_with_row(mocked_factory, "{not valid json")

        results, _ = SoggettiRepository().list_soggetti()

        self.assertEqual(results[0]["ruoli"], [])
