# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit della lista `pratiche.flussi` lato repository
#        (`PraticheRepository.list_flussi_pagina`, lista 85): ordinamento
#        sulla whitelist, pagina e conteggio in UNA query col ripiego sullo
#        stesso FROM/WHERE. Mocka `fetch_paged_with_total`, nessun DB reale.
# Note: ⛔ Il caso che conta e' il JOIN su `pratiche.pratiche` nel conteggio:
#       `pratiche.flussi` non ha RLS, la pratica si'. Un COUNT sulla sola
#       `flussi` direbbe «12» a chi, sotto RLS, non vede nessuna riga.
# ------------------------------------------------------------
"""
Indice test:
1) default: ORDER BY f.sequenza ASC con tiebreak f.id, pratica come parametro.
2) colonna data senza verso -> DESC (colonne_desc), whitelist sul campo_sorgente.
3) il ripiego del conteggio usa lo STESSO frammento della pagina (JOIN pratiche).
4) order_by fuori whitelist -> default, nessun SQL dall'input.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from apps.pratiche.db.pratiche_repository import PraticheRepository

_FETCH = "apps.pratiche.db.pratiche_repository.fetch_paged_with_total"


class ListaFlussiRepositoryTests(TestCase):

    # Scopo: esegue la lista col fetch mockato e ritorna (sql, params, kwargs).
    def _esegui(self, **kwargs):
        with patch(_FETCH, return_value=([], 0)) as fetch:
            PraticheRepository().list_flussi_pagina(42, **kwargs)
        (sql, params), opzioni = fetch.call_args
        return sql, params, opzioni

    def test_default_ordina_per_sequenza(self) -> None:
        sql, params, _ = self._esegui()
        self.assertIn("ORDER BY f.sequenza ASC NULLS FIRST, f.id ASC", sql)
        self.assertIn("COUNT(*) OVER () AS total_count", sql)
        self.assertEqual(params, [42, 25, 0])

    def test_colonna_data_senza_verso_ordina_desc(self) -> None:
        sql, _, _ = self._esegui(order_by="data_insert", limit=10, offset=30)
        self.assertIn("ORDER BY f.data_insert DESC NULLS LAST, f.id DESC", sql)

    def test_il_conteggio_di_ripiego_ha_il_join_sulla_pratica(self) -> None:
        sql, _, opzioni = self._esegui(order_by="unita_organizzativa_descrizione", offset=25)
        conteggio = opzioni["fallback_count_sql"]
        self.assertIn("JOIN pratiche.pratiche p ON p.id = f.pratica_id", conteggio)
        self.assertIn("JOIN pratiche.pratiche p ON p.id = f.pratica_id", sql)
        self.assertEqual(opzioni["fallback_params"], [42])
        self.assertEqual(opzioni["offset"], 25)
        self.assertIn("ORDER BY uo.descrizione ASC", sql)

    # ⛔ Fuori whitelist: 400 (`order_by_invalid`), dal 2026-10-20 (brief-be-verifica-documentazione-api §A1).
    def test_order_by_fuori_whitelist_e_rifiutato(self) -> None:
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            self._esegui(order_by="f.id; DROP TABLE x")
