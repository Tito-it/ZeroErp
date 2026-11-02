# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL delle righe di un contratto e di un'offerta lette da
#        `ContrattoRigheListaRepository` e `OffertaRigheListaRepository` col
#        BB `RigheListaMixin` sulla FUNZIONE del documento
#        (`vendite.fn_contratto_righe_preview`, brief-db-liste-righe-documento
#        lotto D, 2026-09-30; `vendite.fn_offerta_righe_preview`,
#        brief-db-righe-esclusione-solo-non-si-vende §8.1, 2026-10-05): la
#        pagina delle liste `vendite.contratto_righe` (103) e
#        `vendite.offerta_righe` (106).
# Note: nessun DB — si sostituisce `fetch_paged_with_total` nel modulo del BB.
#       Le funzioni e le loro colonne le presidiano i pgTAP della parte DB;
#       che la query PARTA sul DB vero lo prova `test_lista_proiezione_campo_sorgente`.
#       ⭐ Le due gemelle girano gli STESSI test (classe base): sono due
#       dichiarazioni della stessa lettura, e un attributo che divergesse fra le
#       due (l'ordine, la chiave, il filtro `attivo`) e' il difetto da vedere.
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Il contratto e' il primo consumatore del BB la cui sorgente NON e' una vista:
e' una funzione del documento, gia' ristretta a lui. Sbagliare il ramo non da'
errore dove ci si aspetta: una `v.contratto_id = %s` su una funzione che non
porta quella colonna e' un 500 al primo operatore, e una funzione chiamata
senza il parametro del documento lo stesso. E senza una condizione il `WHERE`
deve sparire, non restare vuoto. L'offerta e' la seconda, sulla stessa forma.

Indice test (contratto e offerta, ciascuno):

 1) test_pagina_legge_la_funzione_del_documento_senza_where
 2) test_ordine_di_partenza_codice_articolo_e_chiave_di_riga
 3) test_la_ricerca_aggiunge_il_where_e_il_conteggio_lo_segue
 4) test_ordinamento_chiesto_sulla_whitelist
 5) test_la_ricerca_nomina_la_lista_del_documento
 6) test_l_ordine_di_partenza_si_dice_dagli_attributi

Una volta sola:

 7) test_vista_e_funzione_insieme_si_rifiutano
"""

import unittest
from typing import Any
from unittest.mock import patch

from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.core.db import righe_lista_mixin as _righe_repo_mixin
from apps.core.db.righe_lista_mixin import RigheListaMixin
from apps.vendite.db.contratti_repository import ContrattoRigheListaRepository
from apps.vendite.db.offerte_repository import OffertaRigheListaRepository


class _RigheEccezioneListaBase:
    """I test comuni; le sottoclassi dicono repository, funzione e lista."""

    repo_cls: type[RigheListaMixin]
    funzione: str
    lista_codice: str
    # Il nome della FK del documento, che nella SQL non deve comparire.
    fk_documento: str

    def _pagina(self, **kwargs: Any) -> tuple[str, list[Any], dict[str, Any]]:
        kwargs.setdefault("limit", 10)
        with patch.object(_righe_repo_mixin, "fetch_paged_with_total", return_value=([], 0)) as fn:
            self.repo_cls().list_righe_pagina(42, **kwargs)
        args, kw = fn.call_args
        return " ".join(args[0].split()), args[1], kw

    def test_pagina_legge_la_funzione_del_documento_senza_where(self):
        sql, params, kw = self._pagina()
        self.assertIn(f"FROM {self.funzione}(%s) v ORDER BY", sql)
        self.assertNotIn("WHERE", sql)
        self.assertNotIn(self.fk_documento, sql)
        self.assertNotIn("attivo", sql)
        self.assertEqual(params[0], 42)
        self.assertEqual(
            " ".join(kw["fallback_count_sql"].split()), f"SELECT COUNT(*) FROM {self.funzione}(%s) v",
        )
        self.assertEqual(kw["fallback_params"], [42])

    def test_ordine_di_partenza_codice_articolo_e_chiave_di_riga(self):
        sql, _, _ = self._pagina(order_by="", order_dir=None)
        self.assertIn("ORDER BY v.articolo_codice ASC NULLS FIRST, v.riga_key ASC", sql)
        self.assertNotIn("v.id", sql)

    def test_la_ricerca_aggiunge_il_where_e_il_conteggio_lo_segue(self):
        with catalogo_ricerca_finto(["articolo_codice", "articolo_descrizione"]):
            sql, params, kw = self._pagina(search="canone")
        self.assertIn(f"FROM {self.funzione}(%s) v WHERE", sql)
        self.assertIn("v.articolo_descrizione", sql)
        self.assertEqual(params[0], 42)
        self.assertIn(f"FROM {self.funzione}(%s) v WHERE", kw["fallback_count_sql"])
        self.assertEqual(kw["fallback_params"], params[:-2])

    def test_ordinamento_chiesto_sulla_whitelist(self):
        sql, _, _ = self._pagina(order_by="override_prezzo", order_dir="desc")
        self.assertIn("ORDER BY override_prezzo DESC NULLS LAST", sql)
        self.assertIn("v.riga_key", sql)

    def test_la_ricerca_nomina_la_lista_del_documento(self):
        self.assertEqual(self.repo_cls._righe_ricerca.lista_codice, self.lista_codice)

    # La frase dello schema OpenAPI nasce dagli stessi attributi che ordinano.
    def test_l_ordine_di_partenza_si_dice_dagli_attributi(self):
        self.assertEqual(self.repo_cls.righe_ordine_di_partenza(), "`articolo_codice`, `riga_key`.")


class RigheContrattoListaTests(_RigheEccezioneListaBase, unittest.TestCase):
    repo_cls = ContrattoRigheListaRepository
    funzione = "vendite.fn_contratto_righe_preview"
    lista_codice = "vendite.contratto_righe"
    fk_documento = "contratto_id"

    # ⭐ Le due sorgenti sono alternative: dichiararle entrambe lascerebbe
    #    vincere la funzione in silenzio. E' del BB: si prova una volta.
    def test_vista_e_funzione_insieme_si_rifiutano(self):
        with self.assertRaises(TypeError):
            type("DueSorgenti", (RigheListaMixin,), {
                "_righe_vista": "vendite.vw_x", "_righe_funzione": "vendite.fn_x",
            })


class RigheOffertaListaTests(_RigheEccezioneListaBase, unittest.TestCase):
    repo_cls = OffertaRigheListaRepository
    funzione = "vendite.fn_offerta_righe_preview"
    lista_codice = "vendite.offerta_righe"
    fk_documento = "offerta_id"
