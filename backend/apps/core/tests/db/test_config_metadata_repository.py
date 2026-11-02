# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per la normalizzazione del default colonna del CRUD
#        config generico (_parse_column_default). Funzione pura, no DB → CI-safe.
# ------------------------------------------------------------
#
# Indice test:
#  - test_boolean_literal_false / _true / _con_cast
#  - test_boolean_non_literal_none (nextval/now → None)
#  - test_number_int / _float / _con_cast / _non_literal_none
#  - test_text_literal_quotato / _con_cast / _espressione_none
#  - test_default_none

from unittest import TestCase

from apps.core.db.config_metadata_repository import _parse_column_default


class ParseColumnDefaultTests(TestCase):
    # Scopo: i boolean con default literal sono tipizzati (bug chiude_pratica).
    def test_boolean_literal_false(self):
        self.assertIs(_parse_column_default("false", "boolean"), False)

    def test_boolean_literal_true(self):
        self.assertIs(_parse_column_default("true", "boolean"), True)

    def test_boolean_con_cast(self):
        self.assertIs(_parse_column_default("'false'::boolean", "boolean"), False)

    def test_boolean_non_literal_none(self):
        self.assertIsNone(_parse_column_default("nextval('seq')", "boolean"))

    # Scopo: i number con default literal sono parsati int/float.
    def test_number_int(self):
        self.assertEqual(_parse_column_default("0", "number"), 0)

    def test_number_float(self):
        self.assertEqual(_parse_column_default("1.5::numeric", "number"), 1.5)

    def test_number_non_literal_none(self):
        self.assertIsNone(_parse_column_default("now()", "number"))

    # Scopo: i text prefillano solo da literal quotato, mai da espressioni SQL.
    def test_text_literal_quotato(self):
        self.assertEqual(_parse_column_default("'IT'::character varying", "text"), "IT")

    def test_text_espressione_none(self):
        self.assertIsNone(_parse_column_default("now()", "text"))

    # Scopo: nessun default DB → None, il FE applica il proprio fallback.
    def test_default_none(self):
        self.assertIsNone(_parse_column_default(None, "boolean"))
