# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contratto del BB `lista_paginata` (2026-11-24, E-2 di
#        brief-be-fe-BB-audit): la SELECT del chiamante avvolta con
#        `COUNT(*) OVER ()`, l'ordine dato come CORPO di `ORDER BY`, il
#        conteggio di ripiego sulla SELECT nuda — anche quando `dopo_pagina`
#        avvolge la pagina e la query non finisce piu' con `LIMIT/OFFSET`.
# Note: unitari con `connection` finta, come `test_fetch_paged_with_total`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_pagina_avvolta_ordinata_e_finestra_nei_parametri
2) test_oltre_l_ultima_conta_la_select_nuda
3) test_dopo_pagina_riceve_la_pagina_e_l_ordine_intero
4) test_dopo_pagina_oltre_l_ultima_il_ripiego_non_la_paga
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import lista_paginata

_CONN = "apps.core.db._helpers.connection"
_SELECT = "SELECT id FROM t WHERE a = %s"


# Scopo: una `connection` finta che risponde in sequenza le `fetchall` date.
def _connessione(conn: MagicMock, *risposte: list[tuple]) -> MagicMock:
    cursor = MagicMock()
    cursor.description = [SimpleNamespace(name="id"), SimpleNamespace(name="total_count")]
    cursor.fetchall.side_effect = list(risposte)
    cursor.fetchone.return_value = (7,)
    conn.cursor.return_value.__enter__.return_value = cursor
    return cursor


# Scopo: la query eseguita alla chiamata `n`, con gli spazi compressi.
def _sql(cursor: MagicMock, n: int = 0) -> str:
    return " ".join(cursor.execute.call_args_list[n].args[0].split())


class ListaPaginataTests(unittest.TestCase):

    @patch(_CONN)
    def test_pagina_avvolta_ordinata_e_finestra_nei_parametri(self, conn) -> None:
        cursor = _connessione(conn, [(1, 30), (2, 30)])
        righe, totale = lista_paginata(
            select_sql=_SELECT, params=["x"], order_clause="id DESC", limit=10, offset=20,
        )
        self.assertEqual((righe, totale), ([{"id": 1}, {"id": 2}], 30))
        self.assertEqual(
            _sql(cursor),
            f"SELECT *, COUNT(*) OVER () AS total_count FROM ( {_SELECT} ) q "
            "ORDER BY id DESC LIMIT %s OFFSET %s",
        )
        self.assertEqual(cursor.execute.call_args_list[0].args[1], ["x", 10, 20])
        self.assertEqual(cursor.execute.call_count, 1)

    # La pagina stantia: zero righe con offset > 0, il totale si chiede alla
    # SELECT del chiamante, coi soli suoi parametri.
    @patch(_CONN)
    def test_oltre_l_ultima_conta_la_select_nuda(self, conn) -> None:
        cursor = _connessione(conn, [])
        _, totale = lista_paginata(
            select_sql=_SELECT, params=["x"], order_clause="id", limit=10, offset=20,
        )
        self.assertEqual(totale, 7)
        self.assertEqual(_sql(cursor, 1), f"SELECT COUNT(*) FROM ({_SELECT}) q")
        self.assertEqual(cursor.execute.call_args_list[1].args[1], ["x"])

    @patch(_CONN)
    def test_dopo_pagina_riceve_la_pagina_e_l_ordine_intero(self, conn) -> None:
        cursor = _connessione(conn, [(1, 1)])
        ricevuti: list[tuple[str, str]] = []

        def dopo(data_sql: str, ordine: str) -> str:
            ricevuti.append((data_sql, ordine))
            return f"SELECT p.* FROM ({data_sql}) p {ordine}"

        lista_paginata(
            select_sql=_SELECT, params=["x"], order_clause="id", limit=10, offset=0,
            dopo_pagina=dopo,
        )
        data_sql, ordine = ricevuti[0]
        self.assertEqual(ordine, "ORDER BY id")
        self.assertIn("LIMIT %s OFFSET %s", data_sql)
        self.assertTrue(_sql(cursor).startswith("SELECT p.* FROM ( SELECT *, COUNT(*) OVER ()"))
        self.assertTrue(_sql(cursor).endswith(") p ORDER BY id"))

    # ⭐ Il motivo del conteggio sempre esplicito: con `dopo_pagina` la query
    # non sa rileggersi da sola, e il ripiego conta le righe senza giudicarle.
    @patch(_CONN)
    def test_dopo_pagina_oltre_l_ultima_il_ripiego_non_la_paga(self, conn) -> None:
        cursor = _connessione(conn, [])
        _, totale = lista_paginata(
            select_sql=_SELECT, params=["x"], order_clause="id", limit=10, offset=20,
            dopo_pagina=lambda sql, ordine: f"SELECT p.*, 1 AS e FROM ({sql}) p {ordine}",
        )
        self.assertEqual(totale, 7)
        self.assertEqual(_sql(cursor, 1), f"SELECT COUNT(*) FROM ({_SELECT}) q")


if __name__ == "__main__":
    unittest.main()
