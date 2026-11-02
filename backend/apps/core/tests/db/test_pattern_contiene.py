# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio del BB `pattern_contiene`, l'unico modo di costruire il
#        pattern di una ricerca «contiene» con `ILIKE` (estratto il 2026-09-26:
#        in 18 punti il pattern era scritto a mano SENZA escape).
#
# ⛔ Il difetto che presidia non da' errore: un `%` o un `_` scritti
#    dall'utente fanno da jolly e la ricerca torna righe in piu'. Per questo il
#    test 4 lo prova sul database, dove si vede l'effetto e non solo la stringa.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_assente_o_vuoto_e_none
1. test_ripulisce_gli_spazi
2. test_escapa_i_metacaratteri
3. test_termine_normale_resta_contiene
4. test_sul_database_il_percento_non_fa_da_jolly   (opt-in `ZEROERP_TEST_DB_E2E=1`)
"""

from __future__ import annotations

import unittest
from unittest import TestCase

from django.db import connection

from apps.core.db._helpers import pattern_contiene
from apps.core.tests.db_e2e import richiedi_db_provvisto


class PatternContieneTests(TestCase):

    # 0. Niente termine = niente filtro: il chiamante ha il suo `IS NULL OR`.
    def test_assente_o_vuoto_e_none(self) -> None:
        self.assertIsNone(pattern_contiene(None))
        self.assertIsNone(pattern_contiene(""))
        self.assertIsNone(pattern_contiene("   "))

    # 1.
    def test_ripulisce_gli_spazi(self) -> None:
        self.assertEqual(pattern_contiene("  roma "), "%roma%")

    # 2. Backslash per primo, poi `%` e `_`.
    def test_escapa_i_metacaratteri(self) -> None:
        self.assertEqual(pattern_contiene("50%"), "%50\\%%")
        self.assertEqual(pattern_contiene("A_1"), "%A\\_1%")
        self.assertEqual(pattern_contiene("c:\\x"), "%c:\\\\x%")

    # 3.
    def test_termine_normale_resta_contiene(self) -> None:
        self.assertEqual(pattern_contiene("abc"), "%abc%")


# ⚠️ `unittest.TestCase` e non un TestCase Django: nessun database dichiarato,
#    la connessione resta quella configurata (vedi `db_e2e`). Nessuna scrittura:
#    la query legge solo una `VALUES`.
class PatternContieneDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 4. Il `%` cercato trova solo la riga che lo contiene davvero, e `_`
    #    non vale per un carattere qualunque.
    def test_sul_database_il_percento_non_fa_da_jolly(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT v
                  FROM (VALUES ('sconto 50%%'), ('500 pezzi'), ('A_1'), ('AB1')) t(v)
                 WHERE v ILIKE %s OR v ILIKE %s
                 ORDER BY v
                """,
                [pattern_contiene("50%"), pattern_contiene("A_1")],
            )
            trovate = [r[0] for r in cursor.fetchall()]
        self.assertEqual(trovate, ["A_1", "sconto 50%"])
