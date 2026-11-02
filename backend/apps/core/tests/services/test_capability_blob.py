# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Fissa il contratto di `capabilities_o_vuoto` — il ripiego del blob
#        capability condiviso da offerte e lotto (regola del 2, 2026-09-23).
# Note: Indice test:
#        1) capability layer sano → il blob, intatto
#        2) DatabaseError → `{}` + warning sul logger del CHIAMANTE
#        3) dentro un blocco atomico la lettura va in un savepoint suo;
#           fuori non se ne apre nessuno
#        4) un errore che non e' del DB sale: il ripiego non e' un catch-all
# ------------------------------------------------------------

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.capability_blob import capabilities_o_vuoto

_LOGGER = logging.getLogger("apps.test.capability_blob")
_MODULO = "apps.core.services.capability_blob.transaction"


def _leggi(risultato=None, errore=None):
    leggi = MagicMock(return_value=risultato, side_effect=errore)
    return leggi


class CapabilitiesOVuotoTest(SimpleTestCase):

    def _chiama(self, leggi, *, in_atomic=False):
        with patch(_MODULO) as tx:
            tx.get_connection.return_value.in_atomic_block = in_atomic
            out = capabilities_o_vuoto(
                leggi, funzione="fn_available_actions_x", entita_id=7, logger=_LOGGER,
            )
        return out, tx

    def test_1_blob_intatto(self):
        blob = {"available_actions": [{"key": "a"}], "can_edit_testata": True}
        out, _ = self._chiama(_leggi(blob))
        self.assertIs(out, blob)

    def test_2_database_error_blob_vuoto_e_warning(self):
        with self.assertLogs(_LOGGER, level="WARNING") as log:
            out, _ = self._chiama(_leggi(errore=DatabaseError("fn assente")))
        self.assertEqual(out, {})
        self.assertIn("fn_available_actions_x", log.output[0])
        self.assertIn("id=7", log.output[0])

    def test_3_savepoint_solo_dentro_un_blocco_atomico(self):
        _, tx = self._chiama(_leggi({}), in_atomic=True)
        tx.atomic.assert_called_once_with()
        _, tx = self._chiama(_leggi({}), in_atomic=False)
        tx.atomic.assert_not_called()

    def test_4_errore_non_db_sale(self):
        with self.assertRaises(KeyError):
            self._chiama(_leggi(errore=KeyError("x")))
