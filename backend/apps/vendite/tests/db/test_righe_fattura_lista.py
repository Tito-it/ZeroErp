# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
 7) test_i_componenti_arrivano_come_lista_nei_due_percorsi (2026-10-01)
 8) test_le_altre_righe_non_si_decodificano (2026-10-01)
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

# Il kit come lo rende il cursor fuori dall'ORM: `componenti` e' TESTO JSON.
_KIT_GREZZO = {
    "riga_key": "K:835:abc", "tipo_riga": "KIT_PADRE",
    "componenti": '[{"descrizione": "Pezzo A", "quantita": 2}]',
}
_NORMALE_GREZZA = {"riga_key": "R:1", "tipo_riga": "NORMALE", "componenti": None}


class ComponentiDecodificatiTests(unittest.TestCase):
    # 7. Consegnati come stringa, i componenti li scorreva un carattere alla
    #    volta chi li leggeva: il drawer fattura disegnava una riga «— · —»
    #    per carattere sotto il kit, e le note di riga facevano `.map` su una
    #    stringa (2026-10-01, prima fattura con un kit su dbdev). La pagina e
    #    la lettura completa passano dallo stesso punto, e si provano tutte e due.
    def test_i_componenti_arrivano_come_lista_nei_due_percorsi(self):
        attesi = [{"descrizione": "Pezzo A", "quantita": 2}]
        with patch.object(
            _righe_repo_mixin, "fetch_paged_with_total",
            return_value=([dict(_KIT_GREZZO), dict(_NORMALE_GREZZA)], 2),
        ):
            righe, totale = FattureRepository().list_righe_pagina(835, limit=10)
        self.assertEqual(totale, 2)
        self.assertEqual(righe[0]["componenti"], attesi)
        self.assertIsNone(righe[1]["componenti"])

        with patch.object(_righe_repo_mixin, "connection"), patch.object(
            _righe_repo_mixin, "rows_to_list", return_value=[dict(_KIT_GREZZO)],
        ):
            righe = FattureRepository().list_righe(835)
        self.assertEqual(righe[0]["componenti"], attesi)

    # 8. Un documento che non dichiara colonne jsonb consegna le righe come
    #    le legge: il default e' vuoto.
    def test_le_altre_righe_non_si_decodificano(self):
        self.assertEqual(OrdiniRepository._righe_jsonb, ())
        grezza = {"id": 1, "componenti": "[]"}
        with patch.object(
            _righe_repo_mixin, "fetch_paged_with_total", return_value=([dict(grezza)], 1),
        ):
            righe, _ = OrdiniRepository().list_righe_pagina(7, limit=10)
        self.assertEqual(righe[0]["componenti"], "[]")

