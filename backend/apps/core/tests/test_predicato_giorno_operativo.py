# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB `predicato_giorno_operativo` (apps/core/db/_helpers):
#        la forma dell'SQL, l'ordine dei parametri, il rifiuto di una colonna
#        che non e' un identificatore. Nessun DB: la semantica sui confini sta
#        in `apps/core/tests/db/test_predicato_giorno_operativo_db.py`.
# ------------------------------------------------------------
"""Indice test.

1. test_i_confini_li_calcola_il_db
2. test_i_parametri_sono_nell_ordine_dei_segnaposto
3. test_l_sql_non_dipende_dai_valori
4. test_una_colonna_che_non_e_un_identificatore_e_rifiutata
"""

from __future__ import annotations

from datetime import date
from unittest import TestCase

from apps.core.db._helpers import predicato_giorno_operativo


class PredicatoGiornoOperativoTests(TestCase):
    """La forma del filtro per giorno."""

    # 1. I confini sono `fn_inizio_giorno_operativo(da)` e `(a + 1)`, sulla
    #    colonna nuda (indice): nessun `::date` sulla colonna, nessun `+ interval`.
    def test_i_confini_li_calcola_il_db(self) -> None:
        sql, _ = predicato_giorno_operativo("e.occurred_at", date(2026, 9, 1), date(2026, 9, 30))
        self.assertIn("e.occurred_at >= script.fn_inizio_giorno_operativo(%s::date)", sql)
        self.assertIn("e.occurred_at < script.fn_inizio_giorno_operativo(%s::date + 1)", sql)
        self.assertNotIn("occurred_at::date", sql)
        self.assertNotIn("interval", sql.lower())

    # 2. Quattro segnaposto, quattro parametri: (da, da, a, a).
    def test_i_parametri_sono_nell_ordine_dei_segnaposto(self) -> None:
        da, a = date(2026, 9, 1), date(2026, 9, 30)
        sql, params = predicato_giorno_operativo("quando", da, a)
        self.assertEqual(sql.count("%s"), len(params))
        self.assertEqual(params, [da, da, a, a])

    # 3. L'SQL e' costante: un filtro assente vale None nei parametri, e il
    #    testo resta lo stesso (sta anche in WHERE costanti col conteggio di ripiego).
    def test_l_sql_non_dipende_dai_valori(self) -> None:
        pieno, _ = predicato_giorno_operativo("quando", date(2026, 9, 1), date(2026, 9, 2))
        vuoto, params = predicato_giorno_operativo("quando", None, None)
        self.assertEqual(pieno, vuoto)
        self.assertEqual(params, [None, None, None, None])

    # 4. La colonna finisce interpolata: tutto cio' che non e' `alias.colonna`
    #    si ferma qui.
    def test_una_colonna_che_non_e_un_identificatore_e_rifiutata(self) -> None:
        for colonna in ("quando; DROP TABLE x", "a.b.c", "Quando", "", "quando::date"):
            with self.subTest(colonna=colonna), self.assertRaises(ValueError):
                predicato_giorno_operativo(colonna, None, None)
