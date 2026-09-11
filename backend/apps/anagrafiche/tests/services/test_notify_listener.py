# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per CambioRepartoListener — listener
#        LISTEN/NOTIFY canale 'cambio_reparto'.
# Note: Usa unittest.TestCase con mock (no DB reale, compatibile CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CambioRepartoListenerTests.test_handle_notification_invalidates_user
2) CambioRepartoListenerTests.test_handle_notification_skips_null_auth_user
3) CambioRepartoListenerTests.test_handle_notification_skips_invalid_json
4) CambioRepartoListenerTests.test_handle_notification_skips_empty_payload
5) CambioRepartoListenerTests.test_handle_notification_skips_non_dict_payload
6) CambioRepartoListenerTests.test_run_listens_and_dispatches
7) CambioRepartoListenerTests.test_run_reconnects_on_connection_loss
8) CambioRepartoListenerTests.test_stop_terminates_loop
9) CambioRepartoListenerTests.test_conninfo_porta_il_codice_del_processo_come_application_name
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import psycopg

from apps.anagrafiche.services.notify_listener import CambioRepartoListener
from apps.core.services.processi import PROCESSO_LISTEN_CAMBIO_REPARTO

_INVALIDATE = "apps.anagrafiche.services.notify_listener.invalidate_user"
_PSYCOPG_CONNECT = "apps.anagrafiche.services.notify_listener.psycopg.connect"
_CONNINFO = "apps.anagrafiche.services.notify_listener.psycopg.conninfo.make_conninfo"
_SETTINGS = "apps.anagrafiche.services.notify_listener.settings"


def _make_notify(payload: str, channel: str = "cambio_reparto") -> MagicMock:
    """Scopo: Crea un mock di psycopg.Notify con payload e canale."""
    notify = MagicMock()
    notify.channel = channel
    notify.payload = payload
    return notify


class CambioRepartoListenerTests(TestCase):

    # Scopo: Notifica con auth_user_id valido -> invalidate_user chiamata.
    @patch(_INVALIDATE)
    def test_handle_notification_invalidates_user(self, mock_invalidate):
        listener = CambioRepartoListener()
        payload = json.dumps({
            "risorsa_umana_id": 100,
            "old_uo_id": 1,
            "new_uo_id": 2,
            "auth_user_id": 42,
        })

        listener._handle_notification(_make_notify(payload))

        mock_invalidate.assert_called_once_with(42)

    # Scopo: Notifica con auth_user_id null (risorsa senza bridge)
    # -> invalidate_user NON deve essere chiamata.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_null_auth_user(self, mock_invalidate):
        listener = CambioRepartoListener()
        payload = json.dumps({
            "risorsa_umana_id": 100,
            "old_uo_id": 1,
            "new_uo_id": 2,
            "auth_user_id": None,
        })

        listener._handle_notification(_make_notify(payload))

        mock_invalidate.assert_not_called()

    # Scopo: Payload JSON non valido -> nessun crash, nessuna invalidazione.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_invalid_json(self, mock_invalidate):
        listener = CambioRepartoListener()

        listener._handle_notification(_make_notify("not-valid-json{"))

        mock_invalidate.assert_not_called()

    # Scopo: Payload vuoto/None -> nessun crash, nessuna invalidazione.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_empty_payload(self, mock_invalidate):
        listener = CambioRepartoListener()

        listener._handle_notification(_make_notify(""))

        mock_invalidate.assert_not_called()

    # Scopo: Payload JSON valido ma non-dict (es. array) -> nessun crash.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_non_dict_payload(self, mock_invalidate):
        listener = CambioRepartoListener()

        listener._handle_notification(_make_notify("[1, 2, 3]"))

        mock_invalidate.assert_not_called()

    # Scopo: Verifica che run() apra connessione, esegua LISTEN e
    # dispatchi le notifiche ricevute a _handle_notification.
    @patch(_INVALIDATE)
    @patch(_SETTINGS)
    @patch(_CONNINFO, return_value="host=localhost dbname=test")
    @patch(_PSYCOPG_CONNECT)
    def test_run_listens_and_dispatches(
        self, mock_connect, mock_conninfo, mock_settings, mock_invalidate
    ):
        mock_settings.DATABASES = {
            "default": {
                "HOST": "localhost",
                "PORT": "5432",
                "NAME": "testdb",
                "USER": "testuser",
                "PASSWORD": "testpass",
            }
        }

        # Simula connessione con context manager
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        # Prima iterazione: una notifica; seconda: il listener si ferma
        notify_obj = _make_notify(json.dumps({
            "risorsa_umana_id": 1,
            "old_uo_id": 10,
            "new_uo_id": 20,
            "auth_user_id": 5,
        }))
        call_count = 0

        def fake_notifies(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield notify_obj
            else:
                # Ferma il listener dopo la prima iterazione
                listener.stop()

        mock_conn.notifies = fake_notifies

        # Disabilita signal handlers in test
        listener = CambioRepartoListener(poll_interval=0.1)
        with patch.object(listener, "_install_signal_handlers"):
            listener.run()

        # Verifica LISTEN eseguito
        mock_conn.execute.assert_called_once_with("LISTEN cambio_reparto")

        # Verifica invalidazione
        mock_invalidate.assert_called_once_with(5)

    # Scopo: Verifica che run() riprovi la connessione con backoff
    # quando _listen_loop solleva psycopg.OperationalError.
    @patch(_INVALIDATE)
    @patch("apps.anagrafiche.services.notify_listener.time.sleep")
    def test_run_reconnects_on_connection_loss(self, mock_sleep, mock_invalidate):
        listener = CambioRepartoListener(
            poll_interval=0.1,
            reconnect_base_delay=1.0,
            reconnect_max_delay=10.0,
        )
        call_count = 0

        def fake_listen_loop():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise psycopg.OperationalError("connection lost")
            if call_count == 2:
                raise psycopg.OperationalError("still down")
            # Terza chiamata: ok, poi stop
            listener.stop()

        with patch.object(listener, "_listen_loop", side_effect=fake_listen_loop):
            with patch.object(listener, "_install_signal_handlers"):
                listener.run()

        self.assertEqual(call_count, 3)
        # Backoff: prima 1.0s, poi 2.0s
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    # Scopo: Verifica che stop() imposti il flag _running a False.
    def test_stop_terminates_loop(self):
        listener = CambioRepartoListener()
        listener._running = True

        listener.stop()

        self.assertFalse(listener._running)


    # Scopo: Il segno di vita del listener e' la sessione: `application_name`
    #        DEVE essere il codice del processo a catalogo, perche'
    #        `dbops.vw_processi_programmazione` (segno_di_vita = SESSIONE) lo
    #        cerca in `pg_stat_activity` con quel nome esatto. Senza questa
    #        riga il panorama dice MUTO su un listener vivo — ed e' successo:
    #        e' la riga che il digest ha mostrato dal 2026-09-11 finche' il
    #        backend non si e' presentato col proprio nome.
    # ⚠️ Si legge la stringa che psycopg costruisce DAVVERO, non un mock:
    #    `make_conninfo` e' pura e non apre connessioni.
    @patch(_SETTINGS)
    def test_conninfo_porta_il_codice_del_processo_come_application_name(
        self, mock_settings,
    ):
        mock_settings.DATABASES = {
            "default": {
                "HOST": "localhost",
                "PORT": "5432",
                "NAME": "testdb",
                "USER": "testuser",
                "PASSWORD": "testpass",
            }
        }

        conninfo = CambioRepartoListener._get_conninfo()

        parametri = psycopg.conninfo.conninfo_to_dict(conninfo)
        self.assertEqual(
            parametri.get("application_name"), PROCESSO_LISTEN_CAMBIO_REPARTO,
        )
        self.assertEqual(parametri.get("dbname"), "testdb")
