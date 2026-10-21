# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il `limit` che arriva da un LLM, normalizzato senza sorprese.
#
# 🔴 PERCHE' ESISTE (2026-09-10). Chi chiama questi tool non e' un form ne' un
#    client scritto da noi: e' un modello, che manda `"20"` con la stessa
#    naturalezza con cui manda `20`. Il vecchio `min(params.get(...), max)` su
#    quella stringa sollevava un `TypeError`, e su `0` lasciava passare un
#    valore che moriva piu' giu' parlando di un altro parametro.
# ⚠️ Nessuno di questi casi era un 500 — l'executor cattura e gira il testo al
#    modello — ed e' proprio il motivo per cui il difetto poteva restare a lungo:
#    non c'e' una riga di log rossa, c'e' un giro che non conclude.
#
# Indice test:
#   1) assente -> il default del tool (10)
#   2) `null` esplicito -> il default (NON un TypeError: `.get(k, d)` torna None)
#   3) intero valido -> se stesso
#   4) ⭐ stringa numerica -> convertita (e' la forma normale da un LLM)
#   5) sopra il tetto -> clampato in silenzio (il tetto e' dichiarato a contratto)
#   6) zero e negativi -> errore che NOMINA il dato e dice cosa fare
#   7) non numerico -> errore, non TypeError criptico
#   8) bool -> errore (in Python e' un int: senza guard `True` varrebbe 1)
#   9) float non intero -> errore (rigore tipi, come PayloadValidator)
#  10) il messaggio d'errore e' AZIONABILE: nomina il parametro e il valore
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from apps.ai_assistant.tools.base import AITool


class SafePageSizeTests(unittest.TestCase):
    """Il tetto dei risultati non si rompe su cio' che un modello manda davvero."""

    def test_assente_usa_il_default(self):
        self.assertEqual(AITool.safe_limit({}), 10)

    def test_null_esplicito_usa_il_default(self):
        # `params.get("limit", 10)` qui NON basta: torna None, non 10.
        self.assertEqual(AITool.safe_limit({"limit": None}), 10)

    def test_intero_valido_passa(self):
        self.assertEqual(AITool.safe_limit({"limit": 20}), 20)

    def test_stringa_numerica_viene_convertita(self):
        self.assertEqual(AITool.safe_limit({"limit": "20"}), 20)
        self.assertEqual(AITool.safe_limit({"limit": " 7 "}), 7)

    def test_sopra_il_tetto_viene_clampato(self):
        self.assertEqual(AITool.safe_limit({"limit": 200}), 50)
        self.assertEqual(AITool.safe_limit({"limit": 200}, max_size=25), 25)

    def test_zero_e_negativi_sono_un_errore_parlante(self):
        for valore in (0, -5, "0"):
            with self.subTest(valore=valore), self.assertRaises(ValueError) as ctx:
                AITool.safe_limit({"limit": valore})
            self.assertIn("limit", str(ctx.exception))

    def test_non_numerico_e_un_errore_non_un_typeerror(self):
        for valore in ("molti", "20.5", [], {}):
            with self.subTest(valore=valore), self.assertRaises(ValueError):
                AITool.safe_limit({"limit": valore})

    def test_bool_non_e_un_intero(self):
        # In Python `True == 1`: senza guard esplicito una richiesta assurda
        # diventerebbe silenziosamente «una riga».
        with self.assertRaises(ValueError):
            AITool.safe_limit({"limit": True})

    def test_float_non_intero_rifiutato(self):
        with self.assertRaises(ValueError):
            AITool.safe_limit({"limit": 20.5})
        self.assertEqual(AITool.safe_limit({"limit": 20.0}), 20)

    def test_il_messaggio_e_azionabile(self):
        # ⭐ Chi legge e' un modello: il messaggio deve dire QUALE parametro e
        #    QUALE valore, o il giro dopo ripete lo stesso errore.
        with self.assertRaises(ValueError) as ctx:
            AITool.safe_limit({"limit": "molti"})
        messaggio = str(ctx.exception)
        self.assertIn("limit", messaggio)
        self.assertIn("molti", messaggio)
        self.assertIn("50", messaggio)
