# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Listener PostgreSQL LISTEN/NOTIFY per il canale
#        'cambio_reparto'. Riceve notifiche dal trigger DB
#        e invalida la cache permessi dell'utente spostato.
# Note: Usa una connessione psycopg3 dedicata (autocommit),
#       separata dal pool Django. Pensato per essere avviato
#       come management command long-running. Include
#       riconnessione automatica con backoff esponenziale.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
import signal
import time
from typing import Any

import psycopg
from django.conf import settings

from apps.core.services.permissions_cache import invalidate_user

logger = logging.getLogger(__name__)

CHANNEL = "cambio_reparto"
DEFAULT_POLL_INTERVAL = 5.0
RECONNECT_BASE_DELAY = 1.0
RECONNECT_MAX_DELAY = 60.0


class CambioRepartoListener:
    """Listener LISTEN/NOTIFY per invalidazione cache al cambio reparto."""

    def __init__(
        self,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        reconnect_base_delay: float = RECONNECT_BASE_DELAY,
        reconnect_max_delay: float = RECONNECT_MAX_DELAY,
    ) -> None:
        self._running = False
        self._poll_interval = poll_interval
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._conn: psycopg.Connection[Any] | None = None

    # Scopo: Costruisce i parametri di connessione psycopg3 dai settings Django.
    @staticmethod
    def _get_conninfo() -> str:
        db = settings.DATABASES["default"]
        return psycopg.conninfo.make_conninfo(
            host=db.get("HOST", ""),
            port=db.get("PORT", ""),
            dbname=db["NAME"],
            user=db.get("USER", ""),
            password=db.get("PASSWORD", ""),
        )

    # Scopo: Avvia il loop LISTEN/NOTIFY con riconnessione automatica.
    # Apre una connessione dedicata con autocommit, registra il canale
    # e cicla sulle notifiche. Se la connessione cade, riprova con
    # backoff esponenziale. Esce con grazia su SIGINT/SIGTERM.
    def run(self) -> None:
        self._running = True
        self._install_signal_handlers()

        logger.info(
            "Avvio listener canale '%s' (poll_interval=%.1fs)",
            CHANNEL,
            self._poll_interval,
        )

        delay = self._reconnect_base_delay
        while self._running:
            try:
                self._listen_loop()
                # Uscita pulita (stop() chiamato)
                delay = self._reconnect_base_delay
            except psycopg.OperationalError as exc:
                if not self._running:
                    break
                logger.warning(
                    "Connessione persa su canale '%s': %s — "
                    "riconnessione tra %.1fs",
                    CHANNEL,
                    exc,
                    delay,
                )
                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_max_delay)

        logger.info("Listener '%s' terminato.", CHANNEL)

    # Scopo: Ciclo interno LISTEN/NOTIFY su una singola connessione.
    # Solleva psycopg.OperationalError se la connessione cade.
    def _listen_loop(self) -> None:
        conninfo = self._get_conninfo()
        with psycopg.connect(conninfo, autocommit=True) as conn:
            self._conn = conn
            conn.execute(f"LISTEN {CHANNEL}")  # noqa: S608 — canale costante
            logger.info("LISTEN %s registrato, in attesa notifiche...", CHANNEL)

            while self._running:
                for notify in conn.notifies(timeout=self._poll_interval):
                    self._handle_notification(notify)

        self._conn = None

    # Scopo: Gestisce una singola notifica NOTIFY.
    # Parsa il payload JSON, estrae auth_user_id e invalida la cache.
    # Se auth_user_id e' null (risorsa senza bridge), logga e ignora.
    def _handle_notification(self, notify: psycopg.Notify) -> None:
        try:
            payload = json.loads(notify.payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Payload non valido su canale '%s': %r",
                notify.channel,
                notify.payload,
            )
            return

        if not isinstance(payload, dict):
            logger.warning(
                "Payload non e' un oggetto JSON su canale '%s': %r",
                notify.channel,
                notify.payload,
            )
            return

        auth_user_id = payload.get("auth_user_id")
        risorsa_id = payload.get("risorsa_umana_id")

        if auth_user_id is None:
            logger.debug(
                "Notifica cambio_reparto per risorsa %s senza auth_user — ignorata.",
                risorsa_id,
            )
            return

        invalidate_user(auth_user_id)

        logger.info(
            "Cache invalidata per auth_user_id=%s (risorsa=%s, old_uo=%s, new_uo=%s)",
            auth_user_id,
            risorsa_id,
            payload.get("old_uo_id"),
            payload.get("new_uo_id"),
        )

    # Scopo: Ferma il loop del listener.
    def stop(self) -> None:
        self._running = False

    # Scopo: Installa handler per SIGINT e SIGTERM per shutdown pulito.
    def _install_signal_handlers(self) -> None:
        def _shutdown(signum: int, frame: Any) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Ricevuto %s, arresto listener...", sig_name)
            self.stop()

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
