# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il vocabolario degli stati del documento interno SPECCHIATO in
#        Python (`STATI_DOCUMENTO_INTERNO`) e' pinnato sui `CHECK` che lo
#        possiedono — `chk_mag_inventari_stato` e `chk_mag_rettifiche_stato`,
#        letti dal catalogo PG col BB `valori_check`. E i RICHIEDIBILI sono
#        un sottoinsieme che NON contiene `POSTED`, per decisione.
# Note: Le due famiglie devono dire la STESSA cosa: e' la matrice unica
#       (D-L2-h) letta da due CHECK, e una divergenza fra i due sarebbe un
#       difetto del modello da segnalare, non da assorbire.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) StatiDocumentoInternoTests.test_il_vocabolario_python_e_quello_dei_due_check
2) StatiDocumentoInternoTests.test_i_richiedibili_sono_un_sottoinsieme_senza_posted
"""
from __future__ import annotations

import unittest

from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check
from apps.magazzino.services.magazzino_service import (
    STATI_DOCUMENTO_INTERNO,
    STATI_RICHIEDIBILI,
)


class StatiDocumentoInternoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_il_vocabolario_python_e_quello_dei_due_check(self):
        inventari = valori_check("magazzino.inventari", "chk_mag_inventari_stato")
        rettifiche = valori_check("magazzino.rettifiche", "chk_mag_rettifiche_stato")
        self.assertEqual(inventari, rettifiche, "le due famiglie hanno vocabolari diversi")
        self.assertEqual(set(STATI_DOCUMENTO_INTERNO), inventari)

    def test_i_richiedibili_sono_un_sottoinsieme_senza_posted(self):
        self.assertTrue(set(STATI_RICHIEDIBILI) < set(STATI_DOCUMENTO_INTERNO))
        self.assertNotIn("POSTED", STATI_RICHIEDIBILI)
