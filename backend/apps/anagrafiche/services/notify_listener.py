# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Listener PostgreSQL LISTEN/NOTIFY che tiene la cache permessi
#        allineata alle scritture fatte FUORI dall'applicazione. Due canali,
#        una connessione:
#        - 'cambio_reparto': un utente ha cambiato reparto → si invalida
#          la cache di QUELL'utente;
#        - 'permessi_catalogo': e' cambiato il catalogo o un profilo dei
#          permessi (seed al migrate, correzione in psql, leva manuale
#          `script.fn_notify_permessi_catalogo`) → si invalida la cache di
#          TUTTI (brief-db-permessi-catalogo-notify-cache.md).
# Note: Usa una connessione psycopg3 dedicata (autocommit),
#       separata dal pool Django. Pensato per essere avviato
#       come management command long-running. Include
#       riconnessione automatica con backoff esponenziale.
#
#       ⭐ A OGNI CONNESSIONE (avvio e riconnessione) si svuota tutta la
#       cache. LISTEN/NOTIFY non accoda: una notifica emessa mentre il processo
#       era giu' e' persa, e il migrate fatto col listener spento e' proprio il
#       caso che il canale del catalogo deve coprire. L'invalidazione si fa
#       DOPO il `LISTEN`: nell'ordine inverso, una scrittura committata fra le
#       due istruzioni non svuoterebbe niente e non sarebbe notificata.
#
#       ⭐ IL SEGNO DI VITA DI QUESTO PROCESSO E' LA SUA CONNESSIONE, non una
#       riga sul giornale (decisione di Tid, 2026-09-11 — brief
#       `brief-db-quattro-processi-senza-presidio.md` §10.3). Il listener
#       scrive UN SOLO run, quello di avvio (2026-09-05): «è vivo adesso?» si
#       legge in `pg_stat_activity`, dove la sessione si presenta con
#       `application_name = dbops.processi.codice`. A catalogo il processo ha
#       `segno_di_vita = 'SESSIONE'`, e `dbops.vw_processi_programmazione` lo
#       dà `OK` se trova quella sessione, `MUTO` altrimenti: se il processo
#       muore la sessione sparisce, se sta riconnettendo non c'e' — ed e' vero.
#       ⛔ Il nome NON si ricopia: e' `PROCESSO_LISTEN_PERMESSI`, la
#       stessa costante con cui il command registra il run. Scritto a mano qui
#       sarebbe la seconda sede, e la vista guarderebbe un nome che non esiste
#       rispondendo «muto» su un listener vivo.
#
#       ⛔ CHI ASCOLTA SOLTANTO NON SI ACCORGE CHE IL SERVER E' SPARITO
#       (2026-10-09). Un LISTEN e' un socket su cui il client non scrive mai:
#       se il server muore senza chiudere la connessione (riavvio della
#       macchina del DB, rete che cade), dal lato client il socket resta
#       «aperto» per sempre, `notifies()` scade a vuoto ogni giro e nessun
#       errore arriva alla riconnessione. Il processo e' vivo per systemd,
#       sordo per il database — e il panorama lo segna MUTO, giustamente. E'
#       successo: Postgres sul dbdev e' ripartito sette minuti dopo l'avvio
#       del listener, e il listener e' rimasto in ascolto del nulla.
#       Il rimedio e' la SONDA: a ogni giro del poll il listener SCRIVE
#       (`SELECT 1`). Su una connessione morta la scrittura fallisce con
#       `OperationalError` e passa dalla riconnessione che esiste gia' (con
#       la sua `invalidate_all`, che recupera le notifiche perse).
#       ⚠️ La sonda da sola non basta: su un host irraggiungibile il kernel
#       ritrasmette per ~15 minuti prima di arrendersi, e la `SELECT 1`
#       resterebbe appesa. Lo taglia `tcp_user_timeout` nella connessione;
#       `connect_timeout` fa lo stesso per i tentativi di riconnessione.
#       ⭐ Dal 2026-10-17 i tetti sono quelli di OGNI connessione del backend,
#       `settings.DB_TETTI_DI_RETE` (regola del 2, ok Tid): prima erano due
#       costanti di questo modulo, con gli stessi valori. Ci sono anche i
#       keepalive TCP: qui non decidono niente (la sonda scrive comunque ogni
#       `poll_interval`), ma la regola della connessione e' una sola.
#       ⚠️ «Sonda», non «battito»: nel progetto il battito e' un segno di vita
#       SCRITTO SUL GIORNALE (`job_liveness`, il battito del digest). La sonda
#       non scrive niente da nessuna parte: chiede solo alla connessione se
#       c'e' ancora. Il segno di vita del listener resta la sessione.
#       ⛔ LIMITE DICHIARATO: la sonda scopre un server SPARITO (risponde RST
#       o non risponde affatto), non un server APPESO che riceve e non
#       risponde mai. Quello e' un guasto del database, e lo vede il
#       panorama: la sessione c'e' ma non serve nessuno.
#
#       ⭐ IL RITARDO DI RICONNESSIONE RIPARTE DA CAPO A OGNI CONNESSIONE
#       RIUSCITA (2026-10-09). Prima ripartiva solo all'uscita pulita, cioe'
#       mai: ogni caduta, anche a settimane di distanza, ereditava il ritardo
#       raddoppiato della precedente, fino a fermarsi per sempre al massimo.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
import signal
import time
from typing import Any

import psycopg
from django.conf import settings

from apps.core.services.permissions_cache import invalidate_all, invalidate_user
from apps.core.services.processi import PROCESSO_LISTEN_PERMESSI

logger = logging.getLogger(__name__)

# I nomi dei canali: lato DB la sede e' la funzione che emette
# (`anagrafiche.fn_notify_cambio_reparto`, `script.fn_notify_permessi_catalogo`).
CANALE_CAMBIO_REPARTO = "cambio_reparto"
CANALE_PERMESSI_CATALOGO = "permessi_catalogo"
CANALI = (CANALE_CAMBIO_REPARTO, CANALE_PERMESSI_CATALOGO)
DEFAULT_POLL_INTERVAL = 5.0
RECONNECT_BASE_DELAY = 1.0
RECONNECT_MAX_DELAY = 60.0
# La sonda: istruzione che fa scrivere il client sulla connessione.
SONDA_SQL = "SELECT 1"


class PermessiListener:
    """Listener LISTEN/NOTIFY per invalidazione cache permessi (cambio di
    reparto e cambio del catalogo dei permessi)."""

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
        self._delay = reconnect_base_delay
        self._conn: psycopg.Connection[Any] | None = None

    # Scopo: Costruisce i parametri di connessione psycopg3 dai settings Django.
    # ⚠️ `application_name` e' il segno di vita del processo (vedi header): il
    #    database lo legge da `pg_stat_activity` per dire se il listener e' vivo.
    # ⚠️ `tcp_user_timeout` e `connect_timeout` (in `DB_TETTI_DI_RETE`, la
    #    sede comune) sono il tetto della sonda (vedi header): senza, una
    #    connessione mezza morta tiene appeso il listener per minuti invece di
    #    farlo riconnettere.
    @staticmethod
    def _get_conninfo() -> str:
        db = settings.DATABASES["default"]
        return psycopg.conninfo.make_conninfo(
            "",
            host=db.get("HOST", ""),
            port=db.get("PORT", ""),
            dbname=db["NAME"],
            user=db.get("USER", ""),
            password=db.get("PASSWORD", ""),
            application_name=PROCESSO_LISTEN_PERMESSI,
            **settings.DB_TETTI_DI_RETE,
        )

    # Scopo: Avvia il loop LISTEN/NOTIFY con riconnessione automatica.
    # Apre una connessione dedicata con autocommit, registra i canali
    # e cicla sulle notifiche. Se la connessione cade, riprova con
    # backoff esponenziale. Esce con grazia su SIGINT/SIGTERM.
    def run(self) -> None:
        self._running = True
        self._install_signal_handlers()

        logger.info(
            "Avvio listener canali %s (poll_interval=%.1fs)",
            ", ".join(CANALI),
            self._poll_interval,
        )

        self._delay = self._reconnect_base_delay
        while self._running:
            try:
                self._listen_loop()
            except psycopg.OperationalError as exc:
                if not self._running:
                    break
                logger.warning(
                    "Connessione persa (listener %s): %s — "
                    "riconnessione tra %.1fs",
                    PROCESSO_LISTEN_PERMESSI,
                    exc,
                    self._delay,
                )
                time.sleep(self._delay)
                self._delay = min(self._delay * 2, self._reconnect_max_delay)

        logger.info("Listener %s terminato.", PROCESSO_LISTEN_PERMESSI)

    # Scopo: Ciclo interno LISTEN/NOTIFY su una singola connessione.
    # Registra i canali, poi svuota tutta la cache (vedi header: cio' che e'
    # stato notificato mentre la connessione non c'era e' perso) e cicla.
    # A ogni giro sonda la connessione (vedi header): e' cio' che fa emergere
    # una connessione morta in silenzio. A connessione riuscita il ritardo di
    # riconnessione riparte dalla base. Solleva psycopg.OperationalError se la connessione
    # cade.
    def _listen_loop(self) -> None:
        conninfo = self._get_conninfo()
        with psycopg.connect(conninfo, autocommit=True) as conn:
            self._conn = conn
            for canale in CANALI:
                conn.execute(f"LISTEN {canale}")  # canali costanti
            logger.info(
                "LISTEN %s registrati, in attesa notifiche...", ", ".join(CANALI),
            )
            invalidate_all()
            self._delay = self._reconnect_base_delay

            while self._running:
                for notify in conn.notifies(timeout=self._poll_interval):
                    self._handle_notification(notify)
                if self._running:
                    conn.execute(SONDA_SQL)

        self._conn = None

    # Scopo: Smista una notifica per canale.
    # ⭐ Sul canale del catalogo il segnale E' la notifica: il payload
    #    (`{"tabella": ...}`) dice solo chi l'ha emessa e serve al log. Se e'
    #    malformato si invalida lo stesso — scartare l'avviso perche' la
    #    didascalia e' rotta lascerebbe i permessi vecchi fino al TTL.
    #    Sul canale del reparto invece il payload porta il destinatario, e
    #    senza quello non c'e' niente da invalidare.
    def _handle_notification(self, notify: psycopg.Notify) -> None:
        if notify.channel == CANALE_PERMESSI_CATALOGO:
            self._handle_permessi_catalogo(notify)
        elif notify.channel == CANALE_CAMBIO_REPARTO:
            self._handle_cambio_reparto(notify)
        else:
            logger.warning(
                "Notifica su canale non atteso '%s': %r — ignorata.",
                notify.channel,
                notify.payload,
            )

    # Scopo: Cambio del catalogo o di un profilo dei permessi → invalida la
    # cache di tutti (per generazione: un ricalcolo per utente alla richiesta
    # successiva).
    def _handle_permessi_catalogo(self, notify: psycopg.Notify) -> None:
        payload = self._parse_payload(notify)
        tabella = payload.get("tabella") if payload is not None else None

        invalidate_all()

        logger.info("Cache permessi invalidata per tutti (tabella=%s)", tabella)

    # Scopo: Cambio di reparto → invalida la cache dell'utente spostato.
    # Estrae auth_user_id dal payload; se e' null (risorsa senza bridge),
    # logga e ignora.
    def _handle_cambio_reparto(self, notify: psycopg.Notify) -> None:
        payload = self._parse_payload(notify)
        if payload is None:
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

    # Scopo: Parsa il payload JSON di una notifica. Restituisce il dict, o
    # None (con un warning) se non e' JSON o non e' un oggetto.
    @staticmethod
    def _parse_payload(notify: psycopg.Notify) -> dict[str, Any] | None:
        try:
            payload = json.loads(notify.payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Payload non valido su canale '%s': %r",
                notify.channel,
                notify.payload,
            )
            return None

        if not isinstance(payload, dict):
            logger.warning(
                "Payload non e' un oggetto JSON su canale '%s': %r",
                notify.channel,
                notify.payload,
            )
            return None

        return payload

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
