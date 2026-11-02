# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `optional_int`: una stringa e' un intero solo se fatta di
#        cifre ASCII. Tutto il resto e' il `{key}_invalid` che i chiamanti
#        traducono in un 400 — mai un ValueError di `int()`, che non lo e'.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_valori_validi — int, stringa di cifre (anche con spazi), assente
2) test_cifre_non_ascii_sono_invalid — «²» e «٣» passano `isdigit()`, non qui
3) test_altre_stringhe_sono_invalid — segni, decimali, vuoto, bool
"""

from unittest import TestCase

from apps.core.api.payload_validators import optional_int


class TestOptionalInt(TestCase):

    def test_valori_validi(self):
        self.assertEqual(optional_int({"x": 7}, "x"), 7)
        self.assertEqual(optional_int({"x": "42"}, "x"), 42)
        self.assertEqual(optional_int({"x": " 42 "}, "x"), 42)
        self.assertIsNone(optional_int({}, "x"))
        self.assertIsNone(optional_int({"x": "0"}, "x", zero_as_none=True))

    def test_cifre_non_ascii_sono_invalid(self):
        """⛔ «²» farebbe fallire `int()` con un messaggio che non e' `x_invalid`;
        «٣» passerebbe come 3 un valore che nessun client scrive."""
        for grezzo in ("²", "7²", "٣"):
            with self.subTest(grezzo=grezzo), self.assertRaisesRegex(ValueError, "^x_invalid$"):
                optional_int({"x": grezzo}, "x")

    def test_altre_stringhe_sono_invalid(self):
        for grezzo in ("-3", "+3", "3.0", "", "abc", True):
            with self.subTest(grezzo=grezzo), self.assertRaisesRegex(ValueError, "^x_invalid$"):
                optional_int({"x": grezzo}, "x")
