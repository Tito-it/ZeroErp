# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dell'unica domanda rimasta sul bypass della RLS:
#        `connection_role_bypasses_rls`.
# ⭐ I due test del GATEWAY sono stati tolti il 2026-09-05 (R-2) insieme al
#    gateway: `system_process_context` non esiste piu'. Che non torni lo
#    presidia `apps/core/tests/test_system_context_usage_whitelist.py`, che dal
#    2026-09-05 pretende ZERO occorrenze invece di una whitelist.
# Indice test:
#   1) connection_role_bypasses_rls legge rolbypassrls del ruolo corrente
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services import system_context

_CONNECTIONS = "apps.core.services.system_context.connections"


def _make_fake_connections(*, bypassrls: bool):
    """Scopo: mappa connections fittizia (default + system_fatturazione) con
    cursor che risponde rolbypassrls=<bypassrls> al check del gateway."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (bypassrls,)
    default = MagicMock()
    default.settings_dict = {"USER": "zeroerp_app", "PASSWORD": "webpw", "NAME": "z"}
    default.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    default.cursor.return_value.__exit__ = MagicMock(return_value=False)
    sys_conn = MagicMock()
    sys_conn.settings_dict = {"USER": "zeroerp_batch_fatturazione", "PASSWORD": "batchpw"}
    return {"default": default, "system_fatturazione": sys_conn}, default, cursor


class SystemProcessContextTests(TestCase):
    # Scopo: dentro il blocco la default usa le credenziali del canale + audit;
    #        all'uscita le credenziali web sono ripristinate.
    def test_connection_role_bypasses_rls_reads_current_user(self):
        fake, _default, cursor = _make_fake_connections(bypassrls=True)
        with patch(_CONNECTIONS, fake):
            self.assertTrue(system_context.connection_role_bypasses_rls("default"))
        sql = cursor.execute.call_args[0][0]
        self.assertIn("rolbypassrls", sql)
        self.assertIn("current_user", sql)
