# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del canale di sistema headless (RLS Path A) — gateway
#        system_process_context + helper connection_role_bypasses_rls.
# Indice test:
#   1) il gateway ripunta la connessione default alle credenziali del canale,
#      setta app.jwt_user (audit) e RIPRISTINA le credenziali web in uscita
#   2) fail-loud: se il ruolo del canale non ha BYPASSRLS → RuntimeError + ripristino
#   3) connection_role_bypasses_rls legge rolbypassrls del ruolo corrente
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
    def test_swaps_credentials_sets_audit_and_restores(self):
        fake, default, cursor = _make_fake_connections(bypassrls=True)
        with patch(_CONNECTIONS, fake):
            seen = {}
            with system_context.system_process_context(
                alias="system_fatturazione", actor="BATCH_FATTURAZIONE",
            ):
                seen["user"] = default.settings_dict["USER"]
                seen["password"] = default.settings_dict["PASSWORD"]

        # Dentro il blocco: credenziali del canale batch.
        self.assertEqual(seen["user"], "zeroerp_batch_fatturazione")
        self.assertEqual(seen["password"], "batchpw")
        # Audit attore settato sulla connessione di sistema.
        calls = [c.args for c in cursor.execute.call_args_list]
        self.assertIn(
            ("SELECT set_config('app.jwt_user', %s, false)", ["BATCH_FATTURAZIONE"]),
            calls,
        )
        # All'uscita: credenziali web ripristinate + connessione chiusa (open + restore).
        self.assertEqual(default.settings_dict["USER"], "zeroerp_app")
        self.assertEqual(default.settings_dict["PASSWORD"], "webpw")
        self.assertGreaterEqual(default.close.call_count, 2)

    # Scopo: fail-loud — ruolo del canale senza BYPASSRLS → RuntimeError (niente
    #        batch in default-deny silenzioso) + ripristino credenziali web.
    def test_fail_loud_when_channel_role_not_bypassrls(self):
        fake, default, _cursor = _make_fake_connections(bypassrls=False)
        with patch(_CONNECTIONS, fake):
            with self.assertRaises(RuntimeError):
                with system_context.system_process_context(
                    alias="system_fatturazione", actor="BATCH_FATTURAZIONE",
                ):
                    pass
        # Anche in errore le credenziali web devono essere ripristinate.
        self.assertEqual(default.settings_dict["USER"], "zeroerp_app")
        self.assertEqual(default.settings_dict["PASSWORD"], "webpw")

    # Scopo: connection_role_bypasses_rls interroga rolbypassrls del ruolo corrente.
    def test_connection_role_bypasses_rls_reads_current_user(self):
        fake, _default, cursor = _make_fake_connections(bypassrls=True)
        with patch(_CONNECTIONS, fake):
            self.assertTrue(system_context.connection_role_bypasses_rls("default"))
        sql = cursor.execute.call_args[0][0]
        self.assertIn("rolbypassrls", sql)
        self.assertIn("current_user", sql)
