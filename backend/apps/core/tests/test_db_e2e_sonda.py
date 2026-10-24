# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le due risposte di `richiedi_db_provvisto` (BB `apps/core/tests/db_e2e.py`)
#        quando la flag e' accesa e il DB risponde: schema assente -> SKIP
#        (ambiente), schema presente e sonda del chiamante assente -> ROSSO
#        (difetto). Senza DB: il cursore e' finto.
# Note: ⛔ Il secondo caso e' quello che prima saltava: una sonda con la firma
#       vecchia di un builder spegneva il test in silenzio
#       (brief-modello-documento-vendita §4-octies, BE-1).
# ------------------------------------------------------------

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_e2e import FLAG_DB_E2E, richiedi_db_provvisto


# Scopo: una connessione finta il cui cursore risponde (schema, sonda).
def _connessione(schema_presente: bool, sonda_presente: bool) -> MagicMock:
    cur = MagicMock()
    cur.fetchone.return_value = (schema_presente, sonda_presente)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn


@patch.dict(os.environ, {FLAG_DB_E2E: "1"})
class RichiediDbProvvistoTests(SimpleTestCase):
    # 1. Schema assente: il DB e' quello usa-e-getta, il test non ha senso -> skip.
    def test_schema_assente_salta(self) -> None:
        with patch("django.db.connection", _connessione(False, False)), \
                self.assertRaises(unittest.SkipTest):
            richiedi_db_provvisto("dbops.fn_x(text)")

    # 2. Schema presente, sonda assente: la funzione manca o ha cambiato firma -> rosso.
    def test_sonda_assente_su_schema_presente_e_rosso(self) -> None:
        with patch("django.db.connection", _connessione(True, False)), \
                self.assertRaises(AssertionError) as ctx:
            richiedi_db_provvisto("dbops.fn_x(text)")
        self.assertIn("dbops.fn_x(text)", str(ctx.exception))

    # 3. Tutto presente: nessuna eccezione.
    def test_tutto_presente_passa(self) -> None:
        with patch("django.db.connection", _connessione(True, True)):
            richiedi_db_provvisto("dbops.fn_x(text)")
