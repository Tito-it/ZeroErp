# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ORDER BY e il totale delle quattro liste paginate di
#        `CatalogoRepository` (articoli, tipi UoM, unita' di misura,
#        conversioni), dopo il passaggio ai BB core `sql_order_clause` e
#        `fetch_paged_with_total` (2026-09-26, regola del 2).
# Note: ⚠️ Le prime due classi NON toccano il database: catturano la query che
#       il repository consegna a `fetch_paged_with_total`. La terza e' opt-in
#       `ZEROERP_TEST_DB_E2E=1` e prova il totale sul DB vero.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrdinamentoListeCatalogoTests.test_order_by_fuori_whitelist_e_rifiutato
   Tutte e quattro: `order_by` sconosciuto ripiega sul default della lista.
   ⛔ Su articoli era un KeyError (`ARTICOLI_ORDER_COLUMNS[order_by]`).
2) OrdinamentoListeCatalogoTests.test_desc_mette_i_null_in_coda_e_allinea_il_tiebreak
   DESC -> `DESC NULLS LAST` + tiebreak `id DESC`; ASC -> `ASC NULLS FIRST`
   + `id ASC` (decisioni Tid 2026-07-19 e 2026-08-03).
3) OrdinamentoListeCatalogoTests.test_la_direzione_non_dipende_dalle_maiuscole
   `DESC` e `desc` danno la stessa clausola: le copie usavano `.upper()`
   (conversioni) e `.lower()` (le altre).
4) OrdinamentoListeCatalogoTests.test_le_date_senza_direzione_ordinano_desc
   `order_by` su una colonna data senza `order_dir` -> DESC (colonne_desc).
5) OrdinamentoListeCatalogoTests.test_il_totale_ha_il_ripiego_per_la_pagina_stantia
   La query porta `COUNT(*) OVER ()` e il COUNT di ripiego ha lo stesso
   FROM/WHERE della pagina, con i soli parametri del filtro.
6) TotaleListeCatalogoDbTests.test_pagina_oltre_l_ultima_dice_il_totale_vero
   (opt-in DB) su una pagina oltre l'ultima il totale resta quello vero,
   come col COUNT separato di prima.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.catalogo.db.catalogo_repository import CatalogoRepository

_FILTRI_ARTICOLI = {
    "attivo": None, "is_composito": None, "tipo_voce_id": None,
    "gruppo_voce_id": None, "listino_tipologia_id": None,
    "search": None, "data_da": None, "data_a": None,
}

# (nome lista, chiamata, default atteso, tiebreak)
_LISTE = (
    ("articoli", lambda r, **k: r.list_articoli(**_FILTRI_ARTICOLI, **k), "a.descrizione", "a.id"),
    ("uom_tipi", lambda r, **k: r.list_uom_tipi(attivo=None, search=None, **k), "ut.descrizione", "ut.id"),
    ("unita_misura", lambda r, **k: r.list_unita_misura(attivo=None, search=None, **k), "u.codice", "u.id"),
    ("conversioni", lambda r, **k: r.list_conversioni(attivo=None, **k), "uf.codice", "c.id"),
)


# Scopo: esegue la lista col BB di paginazione finto e ritorna (sql, params,
#        kwargs) consegnati a `fetch_paged_with_total`.
def _cattura(chiamata, **kwargs):
    with patch(
        "apps.catalogo.db.catalogo_repository.fetch_paged_with_total",
        return_value=([], 0),
    ) as finto:
        chiamata(CatalogoRepository(), **kwargs)
    (sql, params), opzioni = finto.call_args
    return " ".join(sql.split()), params, opzioni


def _order_by(sql: str) -> str:
    return sql.split("ORDER BY ", 1)[1].split(" LIMIT", 1)[0]


class OrdinamentoListeCatalogoTests(unittest.TestCase):
    # 1. Fuori whitelist: 400 (`order_by_invalid`), non il default della lista
    #    (dal 2026-10-20, brief-be-verifica-documentazione-api §A1). Assente: il default.
    def test_order_by_fuori_whitelist_e_rifiutato(self):
        for nome, chiamata, default, tiebreak in _LISTE:
            with self.subTest(lista=nome):
                with self.assertRaisesRegex(ValueError, "order_by_invalid"):
                    _cattura(
                        chiamata, order_by="colonna_inesistente", order_dir="asc",
                        limit=25, offset=0,
                    )
                sql, _p, _o = _cattura(
                    chiamata, order_by=None, order_dir="asc", limit=25, offset=0,
                )
                self.assertEqual(
                    _order_by(sql), f"{default} ASC NULLS FIRST, {tiebreak} ASC",
                )

    # 2. NULLS espliciti e tiebreak nel verso della colonna.
    def test_desc_mette_i_null_in_coda_e_allinea_il_tiebreak(self):
        for nome, chiamata, _default, tiebreak in _LISTE:
            with self.subTest(lista=nome):
                sql, _p, _o = _cattura(
                    chiamata, order_by="attivo", order_dir="desc", limit=25, offset=0,
                )
                self.assertTrue(
                    _order_by(sql).endswith(f"attivo DESC NULLS LAST, {tiebreak} DESC"),
                    _order_by(sql),
                )
                sql, _p, _o = _cattura(
                    chiamata, order_by="attivo", order_dir="asc", limit=25, offset=0,
                )
                self.assertTrue(
                    _order_by(sql).endswith(f"attivo ASC NULLS FIRST, {tiebreak} ASC"),
                    _order_by(sql),
                )

    # 3. Una regola sola per la direzione.
    def test_la_direzione_non_dipende_dalle_maiuscole(self):
        for nome, chiamata, _default, _tiebreak in _LISTE:
            with self.subTest(lista=nome):
                maiuscolo, _p, _o = _cattura(
                    chiamata, order_by="attivo", order_dir="DESC", limit=25, offset=0,
                )
                minuscolo, _p, _o = _cattura(
                    chiamata, order_by="attivo", order_dir="desc", limit=25, offset=0,
                )
                self.assertEqual(_order_by(maiuscolo), _order_by(minuscolo))
                self.assertIn("DESC NULLS LAST", _order_by(maiuscolo))

    # 4. Le date, senza direzione, si leggono dalla piu' recente.
    def test_le_date_senza_direzione_ordinano_desc(self):
        casi = (
            (_LISTE[1][1], "data_insert", "ut.data_insert DESC NULLS LAST, ut.id DESC"),
            (_LISTE[2][1], "data_update", "u.data_update DESC NULLS LAST, u.id DESC"),
            (_LISTE[3][1], "valido_dal", "c.valido_dal DESC NULLS LAST, c.id DESC"),
            (
                _LISTE[3][1], "valido_al",
                "COALESCE(c.valido_al, 'infinity'::date) DESC NULLS LAST, c.id DESC",
            ),
        )
        for chiamata, colonna, attesa in casi:
            with self.subTest(colonna=colonna):
                sql, _p, _o = _cattura(
                    chiamata, order_by=colonna, order_dir=None, limit=25, offset=0,
                )
                self.assertEqual(_order_by(sql), attesa)

    # 5. Totale in una valutazione + ripiego con lo stesso perimetro.
    def test_il_totale_ha_il_ripiego_per_la_pagina_stantia(self):
        for nome, chiamata, _default, _tiebreak in _LISTE:
            with self.subTest(lista=nome):
                sql, params, opzioni = _cattura(
                    chiamata, order_by="attivo", order_dir="asc", limit=10, offset=30,
                )
                self.assertIn("COUNT(*) OVER () AS total_count", sql)
                self.assertEqual(params[-2:], [10, 30])
                self.assertEqual(opzioni["offset"], 30)
                self.assertEqual(opzioni["fallback_params"], params[:-2])
                ripiego = " ".join(opzioni["fallback_count_sql"].split())
                da_from = sql.split(" FROM ", 1)[1].split(" ORDER BY", 1)[0]
                self.assertEqual(ripiego, f"SELECT COUNT(*) FROM {da_from}")


class TotaleListeCatalogoDbTests(unittest.TestCase):
    """Il totale sulla pagina stantia, sul database vero (opt-in)."""

    def setUp(self):
        from apps.core.tests.db_e2e import richiedi_db_provvisto

        richiedi_db_provvisto()

    # 6. ⭐ Con la sola window function una pagina vuota direbbe «0 risultati»:
    #    il ripiego deve rendere lo stesso totale della prima pagina.
    def test_pagina_oltre_l_ultima_dice_il_totale_vero(self):
        repo = CatalogoRepository()
        _righe, totale = repo.list_uom_tipi(
            attivo=None, search=None, order_by="codice", order_dir="asc",
            limit=1, offset=0,
        )
        if totale == 0:
            self.skipTest("nessun tipo UoM: il caso non si puo' costruire qui")
        righe, totale_stantio = repo.list_uom_tipi(
            attivo=None, search=None, order_by="codice", order_dir="asc",
            limit=1, offset=totale + 10,
        )
        self.assertEqual(righe, [])
        self.assertEqual(totale_stantio, totale)
