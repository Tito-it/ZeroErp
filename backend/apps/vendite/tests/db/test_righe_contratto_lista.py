# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL delle righe di un contratto lette da
#        `ContrattoRigheListaRepository` col BB `RigheListaMixin` sulla
#        FUNZIONE `vendite.fn_contratto_righe_preview`
#        (brief-db-liste-righe-documento, lotto D, 2026-09-30): la pagina della
#        lista `vendite.contratto_righe`.
# Note: nessun DB — si sostituisce `fetch_paged_with_total` nel modulo del BB.
#       La funzione e le sue colonne le presidia il pgTAP
#       `test-contratto-righe-lista-v1` della parte DB; che la query PARTA sul
#       DB vero lo prova `test_lista_proiezione_campo_sorgente`.
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Il contratto e' il primo consumatore del BB la cui sorgente NON e' una vista:
e' una funzione del documento, gia' ristretta a lui. Sbagliare il ramo non da'
errore dove ci si aspetta: una `v.contratto_id = %s` su una funzione che non
porta quella colonna e' un 500 al primo operatore, e una funzione chiamata
senza il parametro del documento lo stesso. E senza una condizione il `WHERE`
deve sparire, non restare vuoto.

Indice test:

 1) test_pagina_legge_la_funzione_del_contratto_senza_where
 2) test_ordine_di_partenza_codice_articolo_e_chiave_di_riga
 3) test_la_ricerca_aggiunge_il_where_e_il_conteggio_lo_segue
 4) test_ordinamento_chiesto_sulla_whitelist
 5) test_la_ricerca_nomina_la_lista_del_contratto
 6) test_vista_e_funzione_insieme_si_rifiutano
 7) test_l_ordine_di_partenza_si_dice_dagli_attributi
"""

import unittest
from unittest.mock import patch

from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.vendite.db import _righe_repo_mixin
from apps.vendite.db._righe_repo_mixin import RigheListaMixin
from apps.vendite.db.contratti_repository import ContrattoRigheListaRepository

_FUNZIONE = "vendite.fn_contratto_righe_preview"


def _pagina(**kwargs):
    kwargs.setdefault("limit", 10)
    with patch.object(_righe_repo_mixin, "fetch_paged_with_total", return_value=([], 0)) as fn:
        ContrattoRigheListaRepository().list_righe_pagina(42, **kwargs)
    args, kw = fn.call_args
    return " ".join(args[0].split()), args[1], kw


class RigheContrattoListaTests(unittest.TestCase):

    def test_pagina_legge_la_funzione_del_contratto_senza_where(self):
        sql, params, kw = _pagina()
        self.assertIn(f"FROM {_FUNZIONE}(%s) v ORDER BY", sql)
        self.assertNotIn("WHERE", sql)
        self.assertNotIn("contratto_id", sql)
        self.assertNotIn("attivo", sql)
        self.assertEqual(params[0], 42)
        self.assertEqual(" ".join(kw["fallback_count_sql"].split()), f"SELECT COUNT(*) FROM {_FUNZIONE}(%s) v")
        self.assertEqual(kw["fallback_params"], [42])

    def test_ordine_di_partenza_codice_articolo_e_chiave_di_riga(self):
        sql, _, _ = _pagina(order_by="", order_dir=None)
        self.assertIn("ORDER BY v.articolo_codice ASC NULLS FIRST, v.riga_key ASC", sql)
        self.assertNotIn("v.id", sql)

    def test_la_ricerca_aggiunge_il_where_e_il_conteggio_lo_segue(self):
        with catalogo_ricerca_finto(["articolo_codice", "articolo_descrizione"]):
            sql, params, kw = _pagina(search="canone")
        self.assertIn(f"FROM {_FUNZIONE}(%s) v WHERE", sql)
        self.assertIn("v.articolo_descrizione", sql)
        self.assertEqual(params[0], 42)
        self.assertIn(f"FROM {_FUNZIONE}(%s) v WHERE", kw["fallback_count_sql"])
        self.assertEqual(kw["fallback_params"], params[:-2])

    def test_ordinamento_chiesto_sulla_whitelist(self):
        sql, _, _ = _pagina(order_by="override_prezzo", order_dir="desc")
        self.assertIn("ORDER BY override_prezzo DESC NULLS LAST", sql)
        self.assertIn("v.riga_key", sql)

    def test_la_ricerca_nomina_la_lista_del_contratto(self):
        self.assertEqual(
            ContrattoRigheListaRepository._righe_ricerca.lista_codice, "vendite.contratto_righe",
        )

    # ⭐ Le due sorgenti sono alternative: dichiararle entrambe lascerebbe
    #    vincere la funzione in silenzio.
    def test_vista_e_funzione_insieme_si_rifiutano(self):
        with self.assertRaises(TypeError):
            type("DueSorgenti", (RigheListaMixin,), {
                "_righe_vista": "vendite.vw_x", "_righe_funzione": "vendite.fn_x",
            })

    # La frase dello schema OpenAPI nasce dagli stessi attributi che ordinano.
    def test_l_ordine_di_partenza_si_dice_dagli_attributi(self):
        self.assertEqual(
            ContrattoRigheListaRepository.righe_ordine_di_partenza(),
            "`articolo_codice`, `riga_key`.",
        )
