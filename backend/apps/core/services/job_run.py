# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from django.db import DatabaseError, connection

from apps.core.services.db_error_fields import (
    codice_strutturato_del_driver,
    sqlstate_del_driver,
)
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger(__name__)

# Valori della colonna discriminante `maintenance.job_run_log.origine`
# (CHECK `chk_job_run_log_origine`). PGAGENT resta dei job schedulati via
# `fn_run_and_log`; i processi headless applicativi usano CRON (timer/cron) o
# COMMAND (lancio manuale).
ORIGINE_PGAGENT = "PGAGENT"
ORIGINE_CRON = "CRON"
ORIGINE_COMMAND = "COMMAND"
_ORIGINI = (ORIGINE_PGAGENT, ORIGINE_CRON, ORIGINE_COMMAND)

# ⭐ CHI STA LANCIANDO QUESTO COMMAND, detto dall'AMBIENTE (dal 2026-09-15).
#    Un command scrive da solo la propria origine (`ORIGINE_CRON`, tutti e sei)
#    e non sa chi lo ha fatto partire. Quando a lanciarlo e' «Esegui ora» dal
#    drawer dei processi — l'handler `esegui_processo_default` del drenatore,
#    come sottoprocesso `run-command.sh <comando>` — la corsa e' di una
#    PERSONA, e sul giornale deve distinguersi dal timer: `origine = COMMAND`
#    e `auth_user_id` di chi ha premuto. La sede e' UNA, qui: l'handler mette
#    le due variabili nell'ambiente del figlio, e ogni command presente e
#    futuro le eredita senza una riga (analisi-riavvio-processi-da-interfaccia
#    §4.1-bis, brief-db-avvio-manuale-di-un-processo §8.1).
# ⛔ SE CI SONO, VINCONO sugli argomenti: il command dice «CRON» per abitudine,
#    l'ambiente dice la verita' di QUESTA corsa.
# ⛔ FAIL-LOUD SUL VALORE: un'origine fuori dal CHECK o un id non numerico
#    SOLLEVANO, non ripiegano sull'argomento — un ripiego scriverebbe un run
#    del timer per una corsa a mano, cioe' il contrario di cio' per cui la
#    variabile esiste. Vale anche per la stringa vuota: una variabile presente
#    e vuota e' un segnaposto mai riempito, non un'assenza.
# ⚠️ `auth_user_id` sul giornale e' documentato come «l'utente TECNICO, solo
#    dove la risposta e' UNA» (vedi `registered_job`). Qui la risposta e' una:
#    la persona che ha premuto. Non e' un'eccezione alla regola, e' il caso in
#    cui la regola risponde si'.
ENV_JOB_ORIGINE = "ZEROERP_JOB_ORIGINE"
ENV_JOB_AUTH_USER_ID = "ZEROERP_JOB_AUTH_USER_ID"

# Il codice di una corsa finita con elementi falliti che non hanno un registro
# loro (D9 di brief-db-presidio-job-run-a-chi-tocca). Vedi
# `chiudi_se_elementi_non_completati`.
E_JOB_ELEMENTI_NON_COMPLETATI = "E_JOB_ELEMENTI_NON_COMPLETATI"


# Scopo: applica l'ambiente agli argomenti di `registered_job`: ritorna
#        (origine, auth_user_id) da scrivere sul giornale — quelli dell'ambiente
#        se dichiarati, altrimenti quelli del chiamante.
# ⚠️ Si legge `os.environ` a ogni chiamata, non a import: il modulo vive anche
#    nel processo del drenatore, dove le variabili NON devono esserci (stanno
#    nell'`env` del figlio) — leggerle una volta all'import le renderebbe
#    invisibili al test e a qualunque ambiente cambiato dopo.
def origine_e_attore_dall_ambiente(
    origine: str, auth_user_id: int | None,
) -> tuple[str, int | None]:
    grezza = os.environ.get(ENV_JOB_ORIGINE)
    if grezza is not None:
        valore = grezza.strip()
        if valore not in _ORIGINI:
            raise ValueError(
                f"{ENV_JOB_ORIGINE}={grezza!r} non e' un'origine ammessa "
                f"(attese: {', '.join(_ORIGINI)}): il run non si registra con "
                f"un'origine di ripiego"
            )
        origine = valore

    grezzo_id = os.environ.get(ENV_JOB_AUTH_USER_ID)
    if grezzo_id is not None:
        try:
            valore_id = int(grezzo_id.strip())
        except ValueError:
            valore_id = 0
        if valore_id <= 0:
            raise ValueError(
                f"{ENV_JOB_AUTH_USER_ID}={grezzo_id!r} non e' un id utente "
                f"(intero > 0): il run non si registra con un attore di ripiego"
            )
        auth_user_id = valore_id

    return origine, auth_user_id


# Quanti anelli di `__cause__` si risalgono al massimo: una catena reale ne ha
# due o tre (ServiceError → errore Django → errore del driver). Il tetto e' la
# difesa da una catena circolare, non una stima.
_PROFONDITA_CAUSE = 10


# Scopo: Il primo errore del DRIVER (quello che porta uno SQLSTATE) lungo le
#        cause ESPLICITE di `exc`, compresa `exc` stessa; None se la catena non
#        ne contiene uno.
# ⭐ Si risale, e non ci si ferma alla prima `__cause__`: un command che passa da
#    un service riceve un `ServiceError` tradotto da un errore Django, che a sua
#    volta nasconde quello del driver. Fermarsi al primo anello perderebbe lo
#    SQLSTATE proprio sulla strada piu' comune.
# ⚠️ Solo `__cause__` (`raise … from …`), non `__context__`: un'eccezione nata
#    MENTRE se ne gestiva un'altra non e' detto che ne sia la conseguenza, e
#    lo SQLSTATE di quell'altra sarebbe il guasto sbagliato.
def errore_del_driver(exc: BaseException) -> BaseException | None:
    anello: BaseException | None = exc
    for _ in range(_PROFONDITA_CAUSE):
        if anello is None:
            return None
        if sqlstate_del_driver(anello) is not None:
            return anello
        anello = anello.__cause__
    return None


# Scopo: Cosa scrivere sul giornale per una corsa uscita con `exc`: il codice
#        (`error_code`) e lo SQLSTATE (`sqlstate`, nono argomento di
#        `script.fn_job_run_end`). brief-db-presidio-job-run-a-chi-tocca §4.2.
#        Il codice, in quest'ordine:
#          1. il `code` dell'eccezione (`ServiceError`, `GiroSmokeFallito`): e' il
#             codice che il backend ha dato al proprio fallimento;
#          2. il codice `E_` di un `P0001` sollevato dal database, invece del nome
#             di classe `InternalError`: e' la regola che `fn_run_and_log`
#             applica ai job pgAgent, e senza `config.codici_errore` non vede la
#             causa che il codice dichiara;
#          3. il nome della classe Python.
# ⭐ Lo SQLSTATE e' quello che decide l'AMBIENTE nella vista
#    (`script.fn_sqlstate_di_ambiente`): senza, un disco pieno o una connessione
#    caduta dentro un command arrivavano come `OperationalError` e finivano allo
#    sviluppo.
# ⚠️ Lo SQLSTATE viaggia anche quando il codice e' il `code` dell'eccezione: un
#    `ServiceError` tradotto da un `53100` resta un disco pieno.
# ⚠️ Un errore lato client (la connessione che non si apre) non ha SQLSTATE: il
#    driver non ne riceve uno dal server, e qui non se ne inventa uno.
def esito_errore(exc: BaseException) -> tuple[str, str | None]:
    driver = errore_del_driver(exc)
    sqlstate = sqlstate_del_driver(driver) if driver is not None else None
    codice = getattr(exc, "code", None)
    if codice is None and driver is not None:
        codice = codice_strutturato_del_driver(driver)
    return str(codice if codice is not None else type(exc).__name__), sqlstate


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
#        ⭐ `origine` e `auth_user_id` possono arrivare dall'AMBIENTE e VINCERE
#        sugli argomenti (`ENV_JOB_ORIGINE`, `ENV_JOB_AUTH_USER_ID`, dal
#        2026-09-15): e' il canale con cui «Esegui ora» dice al command che
#        questa corsa e' di una persona. Un valore invalido solleva PRIMA di
#        aprire il run — vedi `origine_e_attore_dall_ambiente`.
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
    # ⛔ Prima del cursore: un ambiente malformato non deve aprire nessuna riga.
    origine, auth_user_id = origine_e_attore_dall_ambiente(origine, auth_user_id)
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
    sqlstate: str | None = None
    try:
        yield handle
    except BaseException as exc:
        ok = False
        error_code, sqlstate = esito_errore(exc)
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
                    "SELECT script.fn_job_run_end(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)",
                    [
                        handle.id, ok, handle.message, handle.rows_affected,
                        error_code, error_detail, meta_json, lock_key, sqlstate,
                    ],
                )
        except DatabaseError:
            logger.exception(
                "job_run.fn_job_run_end_failed job=%s id=%s (run-log non chiuso)",
                job_name, handle.id,
            )


# Scopo: ⭐ Chiude ROSSA una corsa che ha finito il lavoro ma ha lasciato indietro
#        elementi che non hanno un registro loro, solo il `meta` della corsa.
#        Senza, un giro fallito su tutte le aziende chiudeva verde, e il presidio
#        delle corse (`maintenance.vw_job_run_da_guardare`) non lo vedeva
#        (D9 di brief-db-presidio-job-run-a-chi-tocca, §10.3).
#        `elementi` sono i nomi da mettere nel dettaglio (per esempio i codici
#        delle aziende), `cosa` dice che cosa sono, al plurale.
# ⛔ Si chiama IN FONDO, dopo aver finito gli altri elementi e dopo `set_meta`:
#    il lavoro sugli altri resta fatto, e il `meta` col dettaglio arriva al
#    giornale insieme al rosso. Solleva dentro `registered_job`, che chiude la
#    corsa con `ok = false` e questo codice.
# ⚠️ Solo per fallimenti SENZA un registro loro. Un'email, un lavoro in coda, una
#    stampa hanno ognuno il proprio presidio: chiudere rossa anche la corsa
#    li direbbe due volte.
# Regola del 2 (2026-10-17, ok Tid): la stessa chiusura serviva identica a
#    `run_fatturazione_batch` (`falliti`) e a `send_pending_emails`
#    (`badge_falliti`).
def chiudi_se_elementi_non_completati(
    job: JobRunHandle, elementi: Sequence[str], *, cosa: str,
) -> None:
    if not elementi:
        return
    riassunto = f"{cosa}: {len(elementi)}"
    job.set_message(f"{job.message}; {riassunto}" if job.message else riassunto)
    raise ServiceError(
        code=E_JOB_ELEMENTI_NON_COMPLETATI,
        message=riassunto,
        detail=f"{riassunto} ({', '.join(elementi)})",
    )
