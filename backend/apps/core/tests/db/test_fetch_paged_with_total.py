# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contratto del BB `fetch_paged_with_total` sulla pagina OLTRE
#        l'ultima (2026-09-28): il totale resta quello vero, non 0, anche
#        quando il chiamante non ha un conteggio suo — il BB rilegge la stessa
#        query con `LIMIT 1 OFFSET 0`. Senza, la lista a video non sapeva dove
#        tornare dopo aver eliminato l'unica riga dell'ultima pagina.
# Note: unitari con `connection` finta; l'ultimo test gira sul DATABASE
#       PROVVISTO, su una lista convertita il 2026-09-28 (domini task: seed).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_pagina_piena_una_sola_query
2) test_oltre_l_ultima_rilegge_la_stessa_query_dalla_prima_riga
3) test_oltre_l_ultima_col_conteggio_del_chiamante
4) test_prima_pagina_vuota_nessuna_rilettura
5) test_query_che_non_sa_rileggersi_rifiutata_subito
6) test_offset_ricavato_dalla_query
7) test_offset_dichiarato_diverso_dalla_query_rifiutato
8) test_parametri_con_nome_senza_offset_rifiutati
9) test_db_vero_oltre_l_ultima_pagina_totale_vero
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import fetch_paged_with_total
from apps.core.db.dbops_repository import DbopsRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

_CONN = "apps.core.db._helpers.connection"
_SQL = "SELECT id, COUNT(*) OVER () AS total_count FROM t WHERE a = %s ORDER BY id LIMIT %s OFFSET %s"


# Scopo: una `connection` finta che risponde in sequenza le `fetchall` date.
def _connessione(conn: MagicMock, *risposte: list[tuple]) -> MagicMock:
    cursor = MagicMock()
    cursor.description = [SimpleNamespace(name="id"), SimpleNamespace(name="total_count")]
    cursor.fetchall.side_effect = list(risposte)
    cursor.fetchone.return_value = (7,)
    conn.cursor.return_value.__enter__.return_value = cursor
    return cursor


class FetchPagedWithTotalTests(unittest.TestCase):

    @patch(_CONN)
    def test_pagina_piena_una_sola_query(self, conn) -> None:
        cursor = _connessione(conn, [(1, 30), (2, 30)])
        righe, totale = fetch_paged_with_total(_SQL, ["x", 10, 20], offset=20)
        self.assertEqual((righe, totale), ([{"id": 1}, {"id": 2}], 30))
        self.assertEqual(cursor.execute.call_count, 1)

    # ⭐ Il caso che ha fatto nascere la rilettura: nessun conteggio del
    #    chiamante, la STESSA query con i filtri intatti e la pagina 1 x 1.
    @patch(_CONN)
    def test_oltre_l_ultima_rilegge_la_stessa_query_dalla_prima_riga(self, conn) -> None:
        cursor = _connessione(conn, [], [(1, 20)])
        righe, totale = fetch_paged_with_total(_SQL, ["x", 10, 20], offset=20)
        self.assertEqual((righe, totale), ([], 20))
        seconda = cursor.execute.call_args_list[1].args
        self.assertEqual(seconda, (_SQL, ["x", 1, 0]))

    @patch(_CONN)
    def test_oltre_l_ultima_col_conteggio_del_chiamante(self, conn) -> None:
        cursor = _connessione(conn, [])
        _, totale = fetch_paged_with_total(
            _SQL, ["x", 10, 20], offset=20,
            fallback_count_sql="SELECT COUNT(*) FROM t WHERE a = %s", fallback_params=["x"],
        )
        self.assertEqual(totale, 7)
        self.assertEqual(
            cursor.execute.call_args_list[1].args,
            ("SELECT COUNT(*) FROM t WHERE a = %s", ["x"]),
        )

    @patch(_CONN)
    def test_prima_pagina_vuota_nessuna_rilettura(self, conn) -> None:
        cursor = _connessione(conn, [])
        self.assertEqual(fetch_paged_with_total(_SQL, ["x", 10, 0], offset=0), ([], 0))
        self.assertEqual(cursor.execute.call_count, 1)

    # ⛔ Si rompe al primo test, non al primo operatore su una pagina stantia:
    #    la verifica non aspetta che il ripiego serva.
    @patch(_CONN)
    def test_query_che_non_sa_rileggersi_rifiutata_subito(self, conn) -> None:
        _connessione(conn, [(1, 1)])
        with self.assertRaises(ValueError):
            fetch_paged_with_total("SELECT 1 LIMIT 10", [], offset=0)
        with self.assertRaises(ValueError):
            fetch_paged_with_total(
                "SELECT 1 LIMIT %(l)s OFFSET %(o)s", {"l": 10, "o": 0}, offset=0,
            )


    # ⭐ §9.6 punto 4 (2026-10-04): l'offset e' l'ultimo parametro della
    #    query, e senza `offset=` il ripiego scatta lo stesso.
    @patch(_CONN)
    def test_offset_ricavato_dalla_query(self, conn) -> None:
        cursor = _connessione(conn, [], [(1, 20)])
        _, totale = fetch_paged_with_total(_SQL, ["x", 10, 20])
        self.assertEqual(totale, 20)
        self.assertEqual(cursor.execute.call_count, 2)

    # ⛔ Due valori dello stesso numero che dicono cose diverse: uno e' sbagliato.
    @patch(_CONN)
    def test_offset_dichiarato_diverso_dalla_query_rifiutato(self, conn) -> None:
        _connessione(conn, [(1, 1)])
        with self.assertRaises(ValueError):
            fetch_paged_with_total(_SQL, ["x", 10, 20], offset=0)

    # Con i parametri con nome la query non lo dice: va dichiarato.
    @patch(_CONN)
    def test_parametri_con_nome_senza_offset_rifiutati(self, conn) -> None:
        _connessione(conn, [(1, 1)])
        with self.assertRaises(ValueError):
            fetch_paged_with_total(
                "SELECT 1 LIMIT %(l)s OFFSET %(o)s", {"l": 10, "o": 0},
                fallback_count_sql="SELECT 1", fallback_params={},
            )


class FetchPagedWithTotalDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: su una lista vera, oltre l'ultima pagina il totale e' quello della
    #        prima. ⛔ Una lista senza righe non prova niente: se il seed non
    #        ne ha, il test FALLISCE.
    def test_db_vero_oltre_l_ultima_pagina_totale_vero(self) -> None:
        repo = DbopsRepository()
        _, totale = repo.list_domini_task(attivo_only=False, limit=1, offset=0)
        self.assertGreater(totale, 0, "dbops.domini_task senza righe: il seed manca")
        righe, oltre = repo.list_domini_task(attivo_only=False, limit=10, offset=totale + 100)
        self.assertEqual(righe, [])
        self.assertEqual(oltre, totale)
