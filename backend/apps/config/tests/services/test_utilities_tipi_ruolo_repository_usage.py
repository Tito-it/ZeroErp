# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit della lista `config.utilities_tipi_ruolo_usage` lato
#        repository (`list_emittenti_usage`, lista 86): pagina e conteggio in
#        UNA query, ordinamento sulla whitelist, ripiego del conteggio sullo
#        stesso frammento. Mocka `fetch_paged_with_total`, nessun DB reale.
# ------------------------------------------------------------
"""
Indice test:
1) default: ragione sociale poi codice (clausola a due criteri) + tiebreak ef.id.
2) order_by in whitelist: `override_attivo` -> efu.attivo col verso chiesto.
3) il ripiego del conteggio usa lo STESSO frammento della pagina e gli stessi parametri.
4) order_by fuori whitelist -> default, nessun SQL dall'input.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from apps.config.db.utilities_tipi_ruolo_repository import UtilitiesTipiRuoloRepository

_FETCH = "apps.config.db.utilities_tipi_ruolo_repository.fetch_paged_with_total"


class ListaUsageRepositoryTests(TestCase):

    # Scopo: esegue la lista col fetch mockato e ritorna (sql, params, kwargs).
    def _esegui(self, **kwargs):
        with patch(_FETCH, return_value=([], 0)) as fetch:
            UtilitiesTipiRuoloRepository().list_emittenti_usage(7, **kwargs)
        (sql, params), opzioni = fetch.call_args
        return sql, params, opzioni

    def test_default_ragione_sociale_poi_codice(self) -> None:
        sql, params, _ = self._esegui()
        self.assertIn(
            "ORDER BY s_ef.ragione_sociale_completa ASC, ef.codice ASC, ef.id ASC", sql,
        )
        self.assertIn("COUNT(*) OVER ()", sql)
        self.assertEqual(params, [7, "EF", 25, 0])

    def test_ordina_per_override_attivo(self) -> None:
        sql, _, _ = self._esegui(order_by="override_attivo", order_dir="desc")
        self.assertIn("ORDER BY efu.attivo DESC NULLS LAST, ef.id DESC", sql)

    def test_il_conteggio_di_ripiego_usa_lo_stesso_frammento(self) -> None:
        sql, _, opzioni = self._esegui(offset=50, limit=25)
        conteggio = opzioni["fallback_count_sql"]
        self.assertTrue(conteggio.startswith("SELECT COUNT(*)"))
        self.assertIn("JOIN anagrafiche.soggetti s_ef", conteggio)
        self.assertIn("WHERE utr.id = %s", conteggio)
        self.assertEqual(opzioni["fallback_params"], [7, "EF"])
        self.assertEqual(opzioni["offset"], 50)

    # ⛔ Fuori whitelist: 400 (`order_by_invalid`), dal 2026-10-20 (brief-be-verifica-documentazione-api §A1).
    def test_order_by_fuori_whitelist_e_rifiutato(self) -> None:
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            self._esegui(order_by="1; DROP TABLE x")
