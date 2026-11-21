# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test di `qp_uuid_optional`, l'uuid facoltativo da query string: un
#        valore che non e' un uuid e' il `{name}_invalid` che le view traducono
#        in un 400 (un `%s::uuid` su una stringa qualunque sarebbe un 500).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_assente_o_vuoto — None
2) test_normalizzato — strip e forma canonica minuscola
3) test_non_uuid — invalid, "0" compreso (a differenza di `optional_uuid`, che e' del payload)
"""

from unittest import TestCase

from apps.core.api.payload_validators import qp_uuid_optional

_UUID = "019a2b3c-4d5e-7f60-8a9b-0c1d2e3f4a5b"


class TestQpUuidOptional(TestCase):

    def test_assente_o_vuoto(self):
        for grezzo in (None, "", "   "):
            with self.subTest(grezzo=grezzo):
                self.assertIsNone(qp_uuid_optional(grezzo, "x"))

    def test_normalizzato(self):
        self.assertEqual(qp_uuid_optional(f"  {_UUID.upper()} ", "x"), _UUID)

    def test_non_uuid(self):
        for grezzo in ("banana", "0", "019a2b3c"):
            with self.subTest(grezzo=grezzo), self.assertRaisesRegex(ValueError, "^x_invalid$"):
                qp_uuid_optional(grezzo, "x")
