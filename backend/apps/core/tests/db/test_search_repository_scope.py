# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari sul TRASPORTO dello scope emittente in
#        SearchRepository — i tre stati della convenzione devono
#        arrivare distinti alla funzione SQL.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
#
# ⚠️ Perche' esiste questo file (BE-1,
# brief-db-perimetro-emittente-liste-e-gerarchia-ba §11.6): il repository
# faceva `emittente_ids if emittente_ids else None`, e in Python la lista
# vuota e' falsa. Cosi' `[]` — che nella convenzione significa «NESSUN
# accesso» — diventava `None`, che per la funzione SQL significa «nessuna
# restrizione»: i due estremi OPPOSTI collassavano sullo stesso valore, e
# dalla parte che APRE. Il test asserisce il valore passato al cursore,
# non l'assenza di errore: un test che chiamasse e basta sarebbe verde
# anche col difetto al suo posto.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_search_soggetti_scope_vuoto_resta_vuoto — `[]` NON degrada a None
 2) test_search_soggetti_scope_none_resta_none — `None` invariato (nessuna restrizione)
 3) test_search_soggetti_scope_whitelist_invariata — lista passata cosi' com'e'
 4) test_get_search_detail_scope_vuoto_resta_vuoto — idem sul dettaglio (livello 2)
 5) test_get_search_detail_scope_none_resta_none — idem
 6) test_get_search_detail_scope_whitelist_invariata — idem
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.search_repository import SearchRepository

# Nome del parametro SQL che porta lo scope in entrambe le funzioni.
_PARAM_SCOPE = "p_emittente_ids"


def _mock_connection(mock_conn, *, fetchall=None, fetchone=None):
    """Helper: configura mock connection con context manager sul cursore."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall if fetchall is not None else []
    mock_cursor.fetchone.return_value = fetchone
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


# Scopo: valore che il repository ha passato al posto di `p_emittente_ids`.
# ⚠️ La posizione si DERIVA dall'SQL contando i `%s` che precedono il
#    parametro, invece di scriverla a mano. Un indice fisso (`params[2]`)
#    verifica la colonna sbagliata il giorno in cui qualcuno riordina gli
#    argomenti della chiamata: qui si romperebbe rumorosamente, ma in un test
#    scritto altrimenti potrebbe anche passare per caso — e un presidio che
#    guarda il parametro sbagliato e' peggio di nessun presidio.
def _valore_dello_scope(mock_cursor):
    args, kwargs = mock_cursor.execute.call_args
    sql = args[0] if args else kwargs["sql"]
    params = args[1] if len(args) > 1 else kwargs["params"]
    testa, marcatore, _ = sql.partition(_PARAM_SCOPE)
    assert marcatore, f"il parametro {_PARAM_SCOPE} non compare nella query"
    return params[testa.count("%s")]


class TestSearchSoggettiScope(TestCase):
    """Trasporto dei tre stati dello scope in search_soggetti (livello 1)."""

    # Scopo: Esegue la ricerca con lo scope indicato e restituisce il valore
    #        che il repository ha effettivamente passato al cursore.
    def _scope_passato(self, mock_conn, emittente_ids):
        mock_cursor = _mock_connection(mock_conn, fetchall=[])
        SearchRepository().search_soggetti(
            search_term="rossi",
            tipo_ruolo_id=1,
            emittente_ids=emittente_ids,
        )
        return _valore_dello_scope(mock_cursor)

    @patch("apps.core.db.search_repository.connection")
    def test_search_soggetti_scope_vuoto_resta_vuoto(self, mock_conn):
        """`[]` = nessun accesso: deve arrivare come array vuoto, mai None."""
        scope = self._scope_passato(mock_conn, [])
        self.assertEqual(scope, [])
        self.assertIsNotNone(
            scope,
            "`[]` degradato a None: «nessun accesso» diventa «nessuna restrizione»",
        )

    @patch("apps.core.db.search_repository.connection")
    def test_search_soggetti_scope_none_resta_none(self, mock_conn):
        """`None` = nessuna restrizione: invariato."""
        self.assertIsNone(self._scope_passato(mock_conn, None))

    @patch("apps.core.db.search_repository.connection")
    def test_search_soggetti_scope_whitelist_invariata(self, mock_conn):
        """Una whitelist arriva com'e', senza copie ne' riordini."""
        self.assertEqual(self._scope_passato(mock_conn, [72, 159]), [72, 159])


class TestGetSearchDetailScope(TestCase):
    """Trasporto dei tre stati dello scope in get_search_detail (livello 2)."""

    # Scopo: Esegue il dettaglio con lo scope indicato e restituisce il valore
    #        che il repository ha effettivamente passato al cursore.
    def _scope_passato(self, mock_conn, emittente_ids):
        mock_cursor = _mock_connection(mock_conn, fetchone=[None])
        SearchRepository().get_search_detail(
            soggetto_id="00000000-0000-0000-0000-000000000001",
            tipo_ruolo_id=1,
            emittente_ids=emittente_ids,
        )
        return _valore_dello_scope(mock_cursor)

    @patch("apps.core.db.search_repository.connection")
    def test_get_search_detail_scope_vuoto_resta_vuoto(self, mock_conn):
        """`[]` = nessun accesso, anche sul dettaglio."""
        scope = self._scope_passato(mock_conn, [])
        self.assertEqual(scope, [])
        self.assertIsNotNone(scope)

    @patch("apps.core.db.search_repository.connection")
    def test_get_search_detail_scope_none_resta_none(self, mock_conn):
        """`None` = nessuna restrizione: invariato."""
        self.assertIsNone(self._scope_passato(mock_conn, None))

    @patch("apps.core.db.search_repository.connection")
    def test_get_search_detail_scope_whitelist_invariata(self, mock_conn):
        """Una whitelist arriva com'e'."""
        self.assertEqual(self._scope_passato(mock_conn, [72]), [72])
