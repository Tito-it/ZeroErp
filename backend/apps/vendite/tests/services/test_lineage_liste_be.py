# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari colonne lineage nelle 5 liste documento (Fase B
#        brief-be-fe-lineage): whitelist ORDER BY estesa a pratica/fase.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineageListeOrderWhitelistTests.test_pratica_e_fase_ordinabili_su_tutte_le_liste
2) LineageListeOrderWhitelistTests.test_frontiera_non_ordinabile
"""

from unittest import TestCase

from apps.vendite.db.contratti_repository import _ORDER_COLS_CONTRATTI
from apps.vendite.db.ddt_repository import _ORDER_COLS_DDT
from apps.vendite.db.offerte_repository import _ORDER_COLS_OFFERTE
from apps.vendite.db.ordini_repository import _ORDER_COLS_ORDINI
from apps.vendite.db.preventivi_repository import _ORDER_COLS_PREVENTIVI

# Le 5 whitelist ORDER BY delle liste documento (chiave FE campo_sorgente ->
# colonna SQL sull'alias `v` della vista canonica).
_WHITELISTS = {
    "preventivi": _ORDER_COLS_PREVENTIVI,
    "offerte": _ORDER_COLS_OFFERTE,
    "ordini": _ORDER_COLS_ORDINI,
    "contratti": _ORDER_COLS_CONTRATTI,
    "ddt": _ORDER_COLS_DDT,
}


class LineageListeOrderWhitelistTests(TestCase):
    # Scopo: pratica_numero e fase sono ordinabili su tutte e 5 le liste,
    #        mappate sulle colonne della vista (seed ui.lista_colonna:
    #        pratica.ordinabile=true, fase.ordinabile=true).
    def test_pratica_e_fase_ordinabili_su_tutte_le_liste(self):
        for nome, wl in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertEqual(wl.get("pratica_numero"), "v.pratica_numero")
                self.assertEqual(wl.get("fase"), "v.fase")

    # Scopo: la frontiera (chip transito) NON e' ordinabile — nessuna colonna
    #        di ordinamento la espone (seed transito.ordinabile=false).
    def test_frontiera_non_ordinabile(self):
        for nome, wl in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertNotIn("frontiera_codice", wl)
                self.assertNotIn("transito", wl)
