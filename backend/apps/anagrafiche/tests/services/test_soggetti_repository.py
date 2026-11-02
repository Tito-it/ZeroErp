# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository soggetti.
#        Il campo `ruoli` (jsonb_agg): il driver lo consegna come TESTO, il
#        lettore comune lo decodifica dal tipo della colonna (2026-10-28), il
#        repository fa del NULL una lista vuota.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_list_soggetti_normalizes_ruoli_string_to_list — ruoli jsonb come testo → lista
2) test_list_soggetti_keeps_ruoli_list_unchanged       — ruoli gia' lista, non toccata
3) test_list_soggetti_handles_ruoli_none               — ruoli None → lista vuota
(4, JSON malformato → lista vuota, ritirato il 2026-10-28: una colonna jsonb
non lo contiene, e il lettore comune su un JSON illeggibile esplode di proposito.)
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
        # `ruoli` e' un jsonb_agg: il tipo che il driver dichiara (3802).
        col.type_code = 3802 if name == "ruoli" else 25
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
        """Caso reale: il driver consegna il jsonb come testo → il lettore comune lo fa lista."""
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
