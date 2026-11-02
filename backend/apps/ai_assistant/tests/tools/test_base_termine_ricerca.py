# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il termine di ricerca che arriva da un LLM: sotto soglia e' un errore,
#        non un filtro ignorato.
#
# 🔴 PERCHE' ESISTE (2026-09-24, Tid). Le liste che cercano col BB
#    `add_ricerca_full_condition` ignorano un termine piu' corto di
#    `RICERCA_MIN_CARATTERI`. Un modello che cerca «ab» riceverebbe TUTTE le
#    righe e le presenterebbe come risultato della ricerca: nessun errore,
#    nessun log, una risposta sbagliata.
#
# Indice test:
#   1) assente, `null`, vuoto o solo spazi -> None (nessun filtro)
#   2) alla soglia -> il termine, senza spazi ai bordi
#   3) ⭐ sotto soglia -> errore che nomina il dato e la soglia
#   4) non testo -> errore
#   5) gli strumenti che cercano su una lista passano dall'helper
# ------------------------------------------------------------

from __future__ import annotations

import inspect
import unittest

from apps.ai_assistant.tools import (
    anagrafiche_tools,
    config_tools,
    pratiche_tools,
    vendite_tools,
)
from apps.ai_assistant.tools.base import AITool
from apps.core.db._helpers import RICERCA_MIN_CARATTERI


class TermineRicercaTests(unittest.TestCase):
    """La soglia della ricerca vale anche per chi chiama da un modello."""

    def test_assente_o_vuoto_non_filtra(self):
        for params in ({}, {"search": None}, {"search": ""}, {"search": "   "}):
            with self.subTest(params=params):
                self.assertIsNone(AITool.termine_ricerca(params))

    def test_alla_soglia_torna_il_termine_ripulito(self):
        termine = "x" * RICERCA_MIN_CARATTERI
        self.assertEqual(AITool.termine_ricerca({"search": f"  {termine} "}), termine)

    def test_sotto_soglia_e_un_errore_azionabile(self):
        corto = "x" * (RICERCA_MIN_CARATTERI - 1)
        with self.assertRaises(ValueError) as ctx:
            AITool.termine_ricerca({"search": f" {corto} "})
        messaggio = str(ctx.exception)
        self.assertIn("search", messaggio)
        self.assertIn(str(RICERCA_MIN_CARATTERI), messaggio)
        self.assertIn(repr(corto), messaggio)

    def test_non_testo_e_un_errore(self):
        with self.assertRaises(ValueError):
            AITool.termine_ricerca({"search": 123})

    # ⚠️ Presidio di percorso: un `params.get("search")` rimasto in uno di
    #    questi moduli e' un tool che ignora la soglia in silenzio.
    def test_i_tool_di_lista_passano_dall_helper(self):
        for modulo in (anagrafiche_tools, config_tools, pratiche_tools, vendite_tools):
            with self.subTest(modulo=modulo.__name__):
                sorgente = inspect.getsource(modulo)
                self.assertNotIn('params.get("search")', sorgente)
                self.assertIn("self.termine_ricerca(params)", sorgente)
