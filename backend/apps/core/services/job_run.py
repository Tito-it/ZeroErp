# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block GENERICO per la registrazione run-level dei job HEADLESS
#        (management command / cron / systemd) in `maintenance.job_run_log`, via le
#        funzioni `script.fn_job_run_start` / `fn_job_run_end` (SECURITY DEFINER).
#        Distinto dai job pgAgent (`maintenance.fn_run_and_log`) tramite la colonna
#        `origine`. Riusabile da qualsiasi futuro processo headless — nessun
#        accoppiamento di dominio. Vedi design
#        work-in-progress/brief-design-job-run-registrazione.md.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)

# Valori della colonna discriminante `maintenance.job_run_log.origine`
# (CHECK `chk_job_run_log_origine`). PGAGENT resta dei job schedulati via
# `fn_run_and_log`; i processi headless applicativi usano CRON (timer/cron) o
# COMMAND (lancio manuale).
ORIGINE_PGAGENT = "PGAGENT"
ORIGINE_CRON = "CRON"
ORIGINE_COMMAND = "COMMAND"


# Scopo: handle del run restituito da `registered_job`. Espone l'esito dello start
#        (acquired/run_uuid) e raccoglie ciò che il corpo del job vuole persistere a
#        fine run (meta, message, rows_affected).
class JobRunHandle:
    def __init__(self, run_id: int, run_uuid: object, acquired: bool) -> None:
        self.id = run_id
        self.run_uuid = run_uuid
        self.acquired = acquired
        self.meta: dict | None = None
        self.message: str | None = None
        self.rows_affected: int | None = None

    # Scopo: imposta il riepilogo GENERICO del run (no dettaglio di dominio).
    def set_meta(self, meta: dict) -> None:
        self.meta = meta

    # Scopo: messaggio di esito sintetico del run.
    def set_message(self, message: str) -> None:
        self.message = message

    # Scopo: righe coinvolte dal run (metrica generica).
    def set_rows_affected(self, rows: int) -> None:
        self.rows_affected = rows


# Scopo: context manager che registra l'esecuzione di un job headless. All'ingresso
#        apre la riga su `job_run_log` (stato in esecuzione) via `script.fn_job_run_start`
#        — con advisory-lock anti-overlap se `lock_key` è dato; all'uscita la chiude con
#        esito/durata/meta via `script.fn_job_run_end` (ok=False + error_* se il corpo è
#        uscito per eccezione, poi rilancia). Se il lock è occupato (`acquired=False`) la
#        riga "skip" è già loggata dallo start: il corpo NON va eseguito (il caller
#        controlla `handle.acquired`) e `fn_job_run_end` non viene chiamato (nessun lock
#        posseduto). DEVE girare sulla stessa connessione del corpo job, così il
#        lock di sessione vive per tutto il run — vedi design §4.
#        ⚠️ Fino al 2026-09-05 questa riga diceva «dentro il gateway del canale di
#        sistema»: quel gateway è stato ritirato (R-2) e la connessione è ora
#        sempre quella applicativa. Il vincolo «stessa connessione» resta.
#
#        ⭐ `processo_codice` (2026-09-05) e' L'ATTORE: chi ha eseguito, scritto su
#        `maintenance.job_run_log.processo_codice` con **hard FK** verso
#        `dbops.processi`. E' keyword-only e SENZA default di proposito — un job
#        nuovo non deve poter nascere senza dire chi e', e con un default lo
#        dimenticherebbe il prossimo senza che niente lo segnali. Le costanti
#        stanno in `apps.core.services.processi`.
#        ⛔ NON si deriva dal `job_name`: `run_fatturazione_batch` si registra come
#        `run_fatturazione_batch:immediata`, con la corsia attaccata. *Una
#        derivazione incompleta e' peggio di nessuna derivazione* — copre una
#        parte dei casi e tace sull'altra. Dove la derivazione e' completa esiste
#        gia', ed e' dentro `maintenance.fn_run_and_log` per i job pgAgent.
#        ⚠️ `auth_user_id` e' l'utente TECNICO, e si valorizza solo dove la
#        risposta e' UNA: un processo di dominio che lavora un emittente alla
#        volta ce l'ha, un produttore che ne serve N no (i suoi utenti sono N, e
#        chi scrive davvero e' il lavoro accodato).
@contextmanager
def registered_job(
    job_name: str,
    *,
    processo_codice: str,
    origine: str = ORIGINE_CRON,
    stepname: str | None = None,
    lock_key: str | None = None,
    agent_host: str | None = None,
    auth_user_id: int | None = None,
) -> Iterator[JobRunHandle]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, run_uuid, acquired "
            "FROM script.fn_job_run_start(%s, %s, %s, %s, %s, %s, %s)",
            [job_name, origine, stepname, lock_key, agent_host,
             processo_codice, auth_user_id],
        )
        row = cursor.fetchone()
    assert row is not None  # la funzione ritorna sempre una riga
    handle = JobRunHandle(run_id=row[0], run_uuid=row[1], acquired=bool(row[2]))

    # Lock occupato: riga "skip" già chiusa da start, nessun lock posseduto → niente
    # fn_job_run_end. Il caller salta il corpo guardando handle.acquired.
    if not handle.acquired:
        yield handle
        return

    ok = True
    error_code: str | None = None
    error_detail: str | None = None
    try:
        yield handle
    except BaseException as exc:
        ok = False
        # ServiceError espone `.code`; per le altre eccezioni il nome classe.
        error_code = str(getattr(exc, "code", type(exc).__name__))
        error_detail = str(exc) or None
        raise
    finally:
        # Chiusura del run = logging best-effort: NON deve mai mascherare l'eccezione
        # primaria del corpo job (gotcha del finally). Su fallimento del DB qui, si logga
        # e si lascia propagare l'errore reale; la riga resta "aperta" (ended_at NULL) →
        # osservabile, e il lock di sessione cade comunque alla chiusura del processo.
        meta_json = json.dumps(handle.meta) if handle.meta is not None else None
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_job_run_end(%s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                    [
                        handle.id, ok, handle.message, handle.rows_affected,
                        error_code, error_detail, meta_json, lock_key,
                    ],
                )
        except DatabaseError:
            logger.error(
                "job_run.fn_job_run_end_failed job=%s id=%s (run-log non chiuso)",
                job_name, handle.id, exc_info=True,
            )
