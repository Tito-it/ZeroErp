# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL delle righe di una fattura lette da `FattureRepository` col BB
#        `RigheListaMixin` sulla vista `vendite.vw_fattura_righe_lista`
#        (brief-db-liste-righe-documento, lotto C, 2026-09-28): la pagina della
#        lista `vendite.fattura_righe` e la lettura completa.
# Note: nessun DB — si sostituiscono `fetch_paged_with_total` e `connection`
#       nel modulo del BB. La vista e le sue colonne le presidia il pgTAP
#       `test-vw-fattura-righe-lista-v1` della parte DB.
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

La fattura e' il primo consumatore del BB che NON ha le righe in una tabella
con `id` e `attivo`: il padre di un kit non esiste in tabella, la chiave e'
`riga_key`, e l'ordine del documento e' su due colonne. Tre attributi del BB
esistono solo per lei, e sbagliarne uno non da' errore: una chiave `v.id`
spareggerebbe su una colonna che la vista non ha (500), un `attivo` filtrato
su una vista che non lo porta idem, e un ordine su `ordinamento` soltanto
lascerebbe la capofila e le sue parti di plafond in un ordine qualunque.

Indice test:

 1) test_pagina_parte_dall_ordine_del_documento_su_due_colonne
 2) test_nessun_filtro_attivo_e_chiave_di_riga
 3) test_ordinamento_chiesto_sparegia_su_riga_nr_e_chiave
 4) test_lettura_completa_nello_stesso_ordine
 5) test_la_ricerca_nomina_la_lista_della_fattura
 6) test_i_documenti_con_tabella_non_cambiano

I test 7-8 (i componenti decodificati dal mixin, 2026-10-01) sono passati al
lettore comune il 2026-10-28: la decodifica dei jsonb la fa `rows_to_list` dal
tipo della colonna (`apps/core/tests/db/test_rows_to_list_jsonb.py`).
"""

import unittest
from unittest.mock import MagicMock, patch

from apps.core.db import righe_lista_mixin as _righe_repo_mixin
from apps.vendite.db.fatture_repository import FattureRepository
from apps.vendite.db.ordini_repository import OrdiniRepository

_VISTA = "vendite.vw_fattura_righe_lista"


def _pagina(repo_cls=FattureRepository, **kwargs):
    kwargs.setdefault("limit", 10)
    with patch.object(_righe_repo_mixin, "fetch_paged_with_total", return_value=([], 0)) as fn:
        repo_cls().list_righe_pagina(835, **kwargs)
    args, kw = fn.call_args
    return " ".join(args[0].split()), args[1], kw


def _completa():
    cursor = MagicMock()
    cursor.description = []
    cursor.fetchall.return_value = []
    with patch.object(_righe_repo_mixin, "connection") as conn:
        conn.cursor.return_value.__enter__.return_value = cursor
        FattureRepository().list_righe(835)
    sql, params = cursor.execute.call_args.args
    return " ".join(sql.split()), params


class RigheFatturaListaTests(unittest.TestCase):

    def test_pagina_parte_dall_ordine_del_documento_su_due_colonne(self):
        sql, _, _ = _pagina(order_by="", order_dir=None)
        self.assertIn("ORDER BY v.ordinamento ASC NULLS FIRST, v.riga_nr, v.riga_key ASC", sql)

    def test_nessun_filtro_attivo_e_chiave_di_riga(self):
        sql, params, kw = _pagina()
        self.assertIn(f"FROM {_VISTA} v WHERE v.fattura_id = %s", sql)
        self.assertNotIn("attivo", sql)
        self.assertNotIn("v.id", sql)
        self.assertNotIn("attivo", kw["fallback_count_sql"])
        self.assertEqual(params[0], 835)

    def test_ordinamento_chiesto_sparegia_su_riga_nr_e_chiave(self):
        sql, _, _ = _pagina(order_by="importo_riga", order_dir="desc")
        self.assertIn("ORDER BY importo_riga DESC NULLS LAST", sql)
        self.assertIn("v.riga_nr, v.riga_key", sql)

    def test_lettura_completa_nello_stesso_ordine(self):
        sql, params = _completa()
        self.assertIn(f"FROM {_VISTA} v WHERE v.fattura_id = %s ORDER BY v.ordinamento, v.riga_nr, v.riga_key", sql)
        self.assertNotIn("attivo", sql)
        self.assertEqual(params, [835])

    def test_la_ricerca_nomina_la_lista_della_fattura(self):
        self.assertEqual(FattureRepository._righe_ricerca.lista_codice, "vendite.fattura_righe")

    # ⛔ Gli attributi nuovi hanno default che lasciano i quattro documenti
    #    com'erano: `attivo` filtrato, `id` come chiave, ordine su una colonna.
    def test_i_documenti_con_tabella_non_cambiano(self):
        sql, _, _ = _pagina(OrdiniRepository, order_by="", order_dir=None)
        self.assertIn("v.ordine_id = %s AND v.attivo IS TRUE", sql)
        self.assertIn("ORDER BY v.riga_nr ASC NULLS FIRST, v.id ASC", sql)
