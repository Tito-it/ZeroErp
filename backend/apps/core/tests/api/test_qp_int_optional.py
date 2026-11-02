# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del tetto di `qp_int_optional` e `qp_int_strict`: un intero fuori
#        dal tipo dove arriva e' il `{name}_invalid` che le view traducono in un
#        400. Senza tetto psycopg lo manda come bigint (o numeric), il parametro
#        `integer` di una funzione non si risolve e la risposta e' un 500.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_default_bigint — i due estremi di bigint passano, un passo oltre no
2) test_tetto_integer_dichiarato — con INTEGER_MIN/MAX il passo oltre integer e' invalid
3) test_assente_e_non_numerico_invariati — None su assente/vuoto, invalid su testo
4) test_qp_int_strict_default_bigint — stesso tetto di default
"""

from unittest import TestCase

from apps.core.api.payload_validators import qp_int_optional, qp_int_strict
from apps.core.services.payload_helpers import (
    BIGINT_MAX,
    BIGINT_MIN,
    INTEGER_MAX,
    INTEGER_MIN,
)


class TestQpIntOptionalTetto(TestCase):

    def test_default_bigint(self):
        self.assertEqual(qp_int_optional(str(BIGINT_MAX), "x"), BIGINT_MAX)
        self.assertEqual(qp_int_optional(str(BIGINT_MIN), "x"), BIGINT_MIN)
        for grezzo in (str(BIGINT_MAX + 1), str(BIGINT_MIN - 1), "1" + "0" * 30):
            with self.subTest(grezzo=grezzo), self.assertRaisesRegex(ValueError, "^x_invalid$"):
                qp_int_optional(grezzo, "x")

    def test_tetto_integer_dichiarato(self):
        tetto = {"min_val": INTEGER_MIN, "max_val": INTEGER_MAX}
        self.assertEqual(qp_int_optional(str(INTEGER_MAX), "x", **tetto), INTEGER_MAX)
        self.assertEqual(qp_int_optional(str(INTEGER_MIN), "x", **tetto), INTEGER_MIN)
        for grezzo in (str(INTEGER_MAX + 1), str(INTEGER_MIN - 1)):
            with self.subTest(grezzo=grezzo), self.assertRaisesRegex(ValueError, "^x_invalid$"):
                qp_int_optional(grezzo, "x", **tetto)

    def test_assente_e_non_numerico_invariati(self):
        self.assertIsNone(qp_int_optional(None, "x"))
        self.assertIsNone(qp_int_optional("  ", "x"))
        self.assertEqual(qp_int_optional(" 42 ", "x"), 42)
        with self.assertRaisesRegex(ValueError, "^x_invalid$"):
            qp_int_optional("abc", "x")

    def test_qp_int_strict_default_bigint(self):
        self.assertEqual(qp_int_strict(None, "x", 5), 5)
        self.assertEqual(qp_int_strict(str(BIGINT_MAX), "x", 5), BIGINT_MAX)
        with self.assertRaisesRegex(ValueError, "^x_invalid$"):
            qp_int_strict(str(BIGINT_MAX + 1), "x", 5)
