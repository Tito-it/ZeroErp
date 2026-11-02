# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per PermessiListener — listener
#        LISTEN/NOTIFY sui canali 'cambio_reparto' e 'permessi_catalogo'.
# Note: Usa unittest.TestCase con mock (no DB reale, compatibile CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PermessiListenerTests.test_handle_notification_invalidates_user
2) PermessiListenerTests.test_handle_notification_skips_null_auth_user
3) PermessiListenerTests.test_handle_notification_skips_invalid_json
4) PermessiListenerTests.test_handle_notification_skips_empty_payload
5) PermessiListenerTests.test_handle_notification_skips_non_dict_payload
6) PermessiListenerTests.test_run_listens_and_dispatches
7) PermessiListenerTests.test_run_reconnects_on_connection_loss
8) PermessiListenerTests.test_stop_terminates_loop
9) PermessiListenerTests.test_conninfo_porta_il_codice_del_processo_come_application_name
10) PermessiListenerTests.test_catalogo_invalida_tutti
11) PermessiListenerTests.test_catalogo_payload_non_valido_invalida_lo_stesso
12) PermessiListenerTests.test_canale_non_atteso_ignorato
13) PermessiListenerTests.test_invalidate_all_dopo_listen_a_ogni_connessione
14) PermessiListenerTests.test_socket_muto_la_sonda_fa_riconnettere
15) PermessiListenerTests.test_conninfo_porta_i_tetti_di_rete_della_sonda
16) PermessiListenerTests.test_ritardo_riparte_a_ogni_connessione_riuscita
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import psycopg

from django.conf import settings

from apps.anagrafiche.services.notify_listener import (
    SONDA_SQL,
    CANALE_CAMBIO_REPARTO,
    CANALE_PERMESSI_CATALOGO,
    PermessiListener,
)
from apps.core.services.processi import PROCESSO_LISTEN_PERMESSI

_INVALIDATE = "apps.anagrafiche.services.notify_listener.invalidate_user"
_INVALIDATE_ALL = "apps.anagrafiche.services.notify_listener.invalidate_all"
_PSYCOPG_CONNECT = "apps.anagrafiche.services.notify_listener.psycopg.connect"
_CONNINFO = "apps.anagrafiche.services.notify_listener.psycopg.conninfo.make_conninfo"
_SETTINGS = "apps.anagrafiche.services.notify_listener.settings"


def _make_notify(payload: str, channel: str = CANALE_CAMBIO_REPARTO) -> MagicMock:
    """Scopo: Crea un mock di psycopg.Notify con payload e canale."""
    notify = MagicMock()
    notify.channel = channel
    notify.payload = payload
    return notify


class PermessiListenerTests(TestCase):

    # Scopo: Notifica con auth_user_id valido -> invalidate_user chiamata,
    # e SOLO quella: un cambio di reparto non svuota la cache di tutti.
    @patch(_INVALIDATE_ALL)
    @patch(_INVALIDATE)
    def test_handle_notification_invalidates_user(self, mock_invalidate, mock_all):
        listener = PermessiListener()
        payload = json.dumps({
            "risorsa_umana_id": 100,
            "old_uo_id": 1,
            "new_uo_id": 2,
            "auth_user_id": 42,
        })

        listener._handle_notification(_make_notify(payload))

        mock_invalidate.assert_called_once_with(42)
        mock_all.assert_not_called()

    # Scopo: Notifica con auth_user_id null (risorsa senza bridge)
    # -> invalidate_user NON deve essere chiamata.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_null_auth_user(self, mock_invalidate):
        listener = PermessiListener()
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
        listener = PermessiListener()

        listener._handle_notification(_make_notify("not-valid-json{"))

        mock_invalidate.assert_not_called()

    # Scopo: Payload vuoto/None -> nessun crash, nessuna invalidazione.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_empty_payload(self, mock_invalidate):
        listener = PermessiListener()

        listener._handle_notification(_make_notify(""))

        mock_invalidate.assert_not_called()

    # Scopo: Payload JSON valido ma non-dict (es. array) -> nessun crash.
    @patch(_INVALIDATE)
    def test_handle_notification_skips_non_dict_payload(self, mock_invalidate):
        listener = PermessiListener()

        listener._handle_notification(_make_notify("[1, 2, 3]"))

        mock_invalidate.assert_not_called()

    # Scopo: Verifica che run() apra connessione, esegua LISTEN su entrambi i
    # canali e dispatchi le notifiche ricevute a _handle_notification.
    @patch(_INVALIDATE_ALL)
    @patch(_INVALIDATE)
    @patch(_SETTINGS)
    @patch(_CONNINFO, return_value="host=localhost dbname=test")
    @patch(_PSYCOPG_CONNECT)
    def test_run_listens_and_dispatches(
        self, mock_connect, mock_conninfo, mock_settings, mock_invalidate, mock_all
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
        listener = PermessiListener(poll_interval=0.1)
        with patch.object(listener, "_install_signal_handlers"):
            listener.run()

        # Verifica LISTEN eseguito, un canale per istruzione; poi la sonda
        # del primo giro (il secondo giro si ferma e non sonda)
        self.assertEqual(
            [c.args for c in mock_conn.execute.call_args_list],
            [
                ("LISTEN cambio_reparto",),
                ("LISTEN permessi_catalogo",),
                (SONDA_SQL,),
            ],
        )

        # Verifica invalidazione
        mock_invalidate.assert_called_once_with(5)

    # Scopo: Verifica che run() riprovi la connessione con backoff
    # quando _listen_loop solleva psycopg.OperationalError.
    @patch(_INVALIDATE)
    @patch("apps.anagrafiche.services.notify_listener.time.sleep")
    def test_run_reconnects_on_connection_loss(self, mock_sleep, mock_invalidate):
        listener = PermessiListener(
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
        listener = PermessiListener()
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

        mock_settings.DB_TETTI_DI_RETE = settings.DB_TETTI_DI_RETE
        conninfo = PermessiListener._get_conninfo()

        parametri = psycopg.conninfo.conninfo_to_dict(conninfo)
        self.assertEqual(
            parametri.get("application_name"), PROCESSO_LISTEN_PERMESSI,
        )
        self.assertEqual(parametri.get("dbname"), "testdb")

    # Scopo: Notifica sul canale del catalogo -> invalidate_all, non per utente.
    @patch(_INVALIDATE_ALL)
    @patch(_INVALIDATE)
    def test_catalogo_invalida_tutti(self, mock_invalidate, mock_all):
        listener = PermessiListener()
        payload = json.dumps({"tabella": "config.azioni_processo"})

        listener._handle_notification(
            _make_notify(payload, channel=CANALE_PERMESSI_CATALOGO),
        )

        mock_all.assert_called_once_with()
        mock_invalidate.assert_not_called()

    # Scopo: Sul canale del catalogo il segnale e' la notifica, non il
    #        payload: uno malformato non deve far perdere l'invalidazione
    #        (resterebbero i permessi vecchi fino al TTL).
    @patch(_INVALIDATE_ALL)
    def test_catalogo_payload_non_valido_invalida_lo_stesso(self, mock_all):
        listener = PermessiListener()

        for payload in ("not-valid-json{", "", "[1, 2, 3]"):
            with self.subTest(payload=payload):
                mock_all.reset_mock()
                listener._handle_notification(
                    _make_notify(payload, channel=CANALE_PERMESSI_CATALOGO),
                )
                mock_all.assert_called_once_with()

    # Scopo: Un canale che il listener non conosce -> nessuna invalidazione.
    @patch(_INVALIDATE_ALL)
    @patch(_INVALIDATE)
    def test_canale_non_atteso_ignorato(self, mock_invalidate, mock_all):
        listener = PermessiListener()

        listener._handle_notification(
            _make_notify(json.dumps({"auth_user_id": 42}), channel="altro"),
        )

        mock_invalidate.assert_not_called()
        mock_all.assert_not_called()

    # Scopo: LISTEN/NOTIFY non accoda: cio' che e' stato notificato mentre la
    #        connessione non c'era e' perso. Per questo a OGNI connessione
    #        (avvio e riconnessione) si svuota tutta la cache, e DOPO i LISTEN:
    #        nell'ordine inverso una scrittura committata in mezzo non
    #        svuoterebbe niente e non arriverebbe come notifica.
    @patch("apps.anagrafiche.services.notify_listener.time.sleep")
    @patch(_SETTINGS)
    @patch(_CONNINFO, return_value="host=localhost dbname=test")
    @patch(_PSYCOPG_CONNECT)
    def test_invalidate_all_dopo_listen_a_ogni_connessione(
        self, mock_connect, mock_conninfo, mock_settings, mock_sleep,
    ):
        mock_settings.DATABASES = {"default": {"NAME": "testdb"}}
        ordine = MagicMock()

        listener = PermessiListener(poll_interval=0.1)
        connessioni = 0

        def fake_notifies(timeout=None):
            # Prima connessione: cade. Seconda: il listener si ferma.
            if connessioni == 1:
                raise psycopg.OperationalError("connection lost")
            listener.stop()
            yield from ()

        def nuova_connessione(*args, **kwargs):
            nonlocal connessioni
            connessioni += 1
            conn = MagicMock()
            conn.execute = ordine.execute
            conn.notifies = fake_notifies
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=conn)
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_connect.side_effect = nuova_connessione

        with patch(_INVALIDATE_ALL, ordine.invalidate_all):
            with patch.object(listener, "_install_signal_handlers"):
                listener.run()

        self.assertEqual(connessioni, 2)
        giro = [
            ("execute", ("LISTEN cambio_reparto",)),
            ("execute", ("LISTEN permessi_catalogo",)),
            ("invalidate_all", ()),
        ]
        self.assertEqual(
            [(c[0], c.args) for c in ordine.mock_calls], giro + giro,
        )

    # Scopo: Il caso del 2026-10-09. Il server sparisce senza chiudere la
    #        connessione: `notifies()` scade a vuoto ogni giro, nessun errore
    #        arriva da li'. E' la sonda (la scrittura) a far emergere la
    #        connessione morta, e da li' la riconnessione, con la sua
    #        `invalidate_all` che recupera le notifiche perse.
    # ⛔ Senza la sonda questo test non termina: il ciclo resterebbe sulla
    #    prima connessione per sempre — ed e' esattamente il difetto. Il tetto
    #    `giri` lo trasforma in un fallimento invece che in un test appeso.
    @patch(_INVALIDATE_ALL)
    @patch("apps.anagrafiche.services.notify_listener.time.sleep")
    @patch(_SETTINGS)
    @patch(_CONNINFO, return_value="host=localhost dbname=test")
    @patch(_PSYCOPG_CONNECT)
    def test_socket_muto_la_sonda_fa_riconnettere(
        self, mock_connect, mock_conninfo, mock_settings, mock_sleep, mock_all,
    ):
        mock_settings.DATABASES = {"default": {"NAME": "testdb"}}
        listener = PermessiListener(poll_interval=0.1)
        connessioni = 0
        giri = 0

        def muto(timeout=None):
            # Socket mezzo morto: nessuna notifica, nessun errore. Mai.
            nonlocal giri
            giri += 1
            if giri > 10:
                listener.stop()
                self.fail("il listener e' rimasto sulla connessione muta")
            yield from ()

        def sana(timeout=None):
            listener.stop()
            yield from ()

        def execute_muta(sql):
            if sql == SONDA_SQL:
                raise psycopg.OperationalError("server closed the connection")

        def nuova_connessione(*args, **kwargs):
            nonlocal connessioni
            connessioni += 1
            conn = MagicMock()
            if connessioni == 1:
                conn.notifies = muto
                conn.execute = MagicMock(side_effect=execute_muta)
            else:
                conn.notifies = sana
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=conn)
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_connect.side_effect = nuova_connessione

        with patch.object(listener, "_install_signal_handlers"):
            listener.run()

        self.assertEqual(giri, 1)
        self.assertEqual(connessioni, 2)
        self.assertEqual(mock_all.call_count, 2)

    # Scopo: La sonda vale solo se una scrittura senza risposta fallisce in
    #        fretta: senza `tcp_user_timeout` il kernel ritrasmette per ~15
    #        minuti e la `SELECT 1` resta appesa. Si legge la stringa che
    #        libpq accetta DAVVERO (`conninfo_to_dict` la analizza con
    #        PQconninfoParse, e un parametro sconosciuto solleva).
    # ⭐ Dal 2026-10-17 i tetti sono quelli di OGNI connessione del backend
    #    (`settings.DB_TETTI_DI_RETE`, regola del 2): si prova che il listener
    #    li porti TUTTI, e che fra loro ci siano i due della sonda.
    @patch(_SETTINGS)
    def test_conninfo_porta_i_tetti_di_rete_della_sonda(self, mock_settings):
        mock_settings.DATABASES = {"default": {"NAME": "testdb"}}
        mock_settings.DB_TETTI_DI_RETE = settings.DB_TETTI_DI_RETE

        parametri = psycopg.conninfo.conninfo_to_dict(
            PermessiListener._get_conninfo(),
        )

        self.assertIn("tcp_user_timeout", settings.DB_TETTI_DI_RETE)
        self.assertIn("connect_timeout", settings.DB_TETTI_DI_RETE)
        for chiave, valore in settings.DB_TETTI_DI_RETE.items():
            with self.subTest(parametro=chiave):
                self.assertEqual(parametri.get(chiave), str(valore))

    # Scopo: Il ritardo di riconnessione raddoppia mentre il server non
    #        risponde, ma riparte dalla base a ogni connessione RIUSCITA. Prima
    #        ripartiva solo all'uscita pulita, cioe' mai: la seconda caduta,
    #        anche a settimane dalla prima, ereditava il ritardo raddoppiato,
    #        e dopo qualche incidente il listener restava al massimo per sempre.
    #        Qui: caduta, riconnessione riuscita, caduta di nuovo -> 1s e 1s
    #        (non 1s e 2s).
    @patch(_INVALIDATE_ALL)
    @patch("apps.anagrafiche.services.notify_listener.time.sleep")
    @patch(_SETTINGS)
    @patch(_CONNINFO, return_value="host=localhost dbname=test")
    @patch(_PSYCOPG_CONNECT)
    def test_ritardo_riparte_a_ogni_connessione_riuscita(
        self, mock_connect, mock_conninfo, mock_settings, mock_sleep, mock_all,
    ):
        mock_settings.DATABASES = {"default": {"NAME": "testdb"}}
        listener = PermessiListener(
            poll_interval=0.1, reconnect_base_delay=1.0, reconnect_max_delay=10.0,
        )
        connessioni = 0

        def cade(timeout=None):
            raise psycopg.OperationalError("connection lost")
            yield  # pragma: no cover - rende la funzione un generatore

        def ferma(timeout=None):
            listener.stop()
            yield from ()

        def nuova_connessione(*args, **kwargs):
            nonlocal connessioni
            connessioni += 1
            conn = MagicMock()
            conn.notifies = cade if connessioni < 3 else ferma
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=conn)
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_connect.side_effect = nuova_connessione

        with patch.object(listener, "_install_signal_handlers"):
            listener.run()

        self.assertEqual(connessioni, 3)
        self.assertEqual([c.args for c in mock_sleep.call_args_list], [(1.0,), (1.0,)])
