# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo scope emittente NON viaggia piu' dal repository della ricerca
#        universale alle due funzioni SQL: il perimetro dei clienti lo fa la
#        RLS di `anagrafiche.clienti` (R-4 del brief-db-codici-non-trovato-
#        email-e-permessi, 2026-10-08), e `p_emittente_ids` e' superato e in
#        ritiro (R-5, 2026-10-09).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
#
# ⚠️ Storia: fino al 2026-10-09 questo file provava il TRASPORTO dei tre
# stati dello scope (`[]` non doveva degradare a `None`, BE-1 di
# brief-db-perimetro-emittente-liste-e-gerarchia-ba §11.6). Quel rischio
# sparisce con lo scope: ora si prova che il parametro non c'e', cosi' una
# seconda sede del perimetro non rientra in silenzio accanto alla RLS. Il
# binding vero lo prova `test_search_detail_non_trovato_db` sul DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_search_soggetti_non_passa_lo_scope — la lista non manda p_emittente_ids
 2) test_get_search_detail_non_passa_lo_scope — il dettaglio nemmeno
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.search_repository import SearchRepository

# Il parametro SQL superato delle due funzioni.
_PARAM_SCOPE = "p_emittente_ids"


def _mock_connection(mock_conn, *, fetchall=None, fetchone=None):
    """Helper: configura mock connection con context manager sul cursore."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall if fetchall is not None else []
    mock_cursor.fetchone.return_value = fetchone
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


# Scopo: l'SQL che il repository ha mandato al cursore.
def _sql_eseguito(mock_cursor) -> str:
    args, kwargs = mock_cursor.execute.call_args
    return args[0] if args else kwargs["sql"]


class TestScopeNonPassato(TestCase):

    @patch("apps.core.db.search_repository.connection")
    def test_search_soggetti_non_passa_lo_scope(self, mock_conn):
        mock_cursor = _mock_connection(mock_conn, fetchall=[])
        SearchRepository().search_soggetti(search_term="rossi", tipo_ruolo_id=1)
        self.assertNotIn(_PARAM_SCOPE, _sql_eseguito(mock_cursor))

    @patch("apps.core.db.search_repository.connection")
    def test_get_search_detail_non_passa_lo_scope(self, mock_conn):
        mock_cursor = _mock_connection(mock_conn, fetchone=[None])
        SearchRepository().get_search_detail(
            soggetto_id="00000000-0000-0000-0000-000000000001", tipo_ruolo_id=1,
        )
        self.assertNotIn(_PARAM_SCOPE, _sql_eseguito(mock_cursor))
