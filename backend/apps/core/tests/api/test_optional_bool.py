# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `optional_bool` delle view: un flag del CORPO JSON e' un
#        booleano JSON, con la stessa regola di `PayloadValidator.optional_bool`
#        a cui delega. Ogni altro valore e' un 400 `E_VALIDATION_INPUT` col
#        campo — e mai, soprattutto, la stringa "false" letta come vero.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_booleani_e_default — True/False passano; assente e null danno il default
2) test_non_booleani_rifiutati_col_campo — "false", "true", "1", 0, 1, "abc": 400 col campo
"""

from unittest import TestCase

from apps.core.api.payload_validators import optional_bool
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError


class TestOptionalBool(TestCase):

    def test_booleani_e_default(self):
        self.assertIs(optional_bool({"x": True}, "x"), True)
        self.assertIs(optional_bool({"x": False}, "x", default=True), False)
        self.assertIs(optional_bool({}, "x"), False)
        self.assertIs(optional_bool({}, "x", default=True), True)
        self.assertIs(optional_bool({"x": None}, "x", default=True), True)

    # Scopo: ⛔ fino al 2026-10-20 qui si accettava un vocabolario di stringhe,
    #        diverso da quello del BB dei service, che le rifiutava: lo stesso
    #        flag aveva due regole. Ora una sola, e l'errore porta il campo.
    def test_non_booleani_rifiutati_col_campo(self):
        for grezzo in ("false", "true", "1", 0, 1, "abc", ""):
            with self.subTest(grezzo=grezzo), self.assertRaises(ServiceError) as ctx:
                optional_bool({"x": grezzo}, "x")
            self.assertEqual(ctx.exception.code, E_VALIDATION_INPUT)
            self.assertEqual(ctx.exception.context["field"], "x")
