# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `ESEGUI_PROCESSO`: «Esegui ora» su una sveglia di
#        deploy. Lancia `bin/run-command.sh <comando>` come SOTTOPROCESSO —
#        la stessa riga che il timer esegue, meno l'orario — con l'identita'
#        di chi ha premuto, e riporta l'esito nel lavoro.
#
#        ⭐ IL DISEGNO (brief-db-avvio-manuale-di-un-processo §1 e §8,
#        piano-be-fe-avvio-manuale §2.3). Il web non esegue niente: accoda
#        (`ProcessiService.esegui_ora`); il drenatore — `draina_coda_lavori`,
#        ogni minuto, sotto systemd — prende il lavoro e chiama questo handler
#        dentro `operator_identity_context` con la terna di chi ha premuto
#        (`run_as = OPERATORE`). Il comando lanciato registra il SUO run sul
#        giornale, sotto il processo eseguito, con `origine = COMMAND` e
#        l'utente di chi ha premuto: lo legge dall'ambiente (`job_run.py`,
#        `ZEROERP_JOB_ORIGINE` / `ZEROERP_JOB_AUTH_USER_ID`). Il lavoro di coda
#        e' l'audit del GESTO; il run del comando e' l'audit dell'ESECUZIONE
#        (§8.2.1: sotto `avvio_manuale` non si scrive nessun run).
#
#        ⛔ NIENTE ARRIVA DAL PAYLOAD OLTRE A DUE NOMI. `processo_codice` e
#        `unit` si risolvono nel dichiarato di deploy (`sveglie.json`), che e'
#        la whitelist: l'argv e' quello di `Sveglia.comando`, gia' validato
#        token per token da `carica_sveglie` (niente spazi, `%`, `$`, `|`).
#        Una `unit` che il deploy non ha e' un payload rotto, non un caso da
#        ritentare. E il predicato «si puo' lanciare a mano?» si RICONTROLLA
#        qui (difesa in profondita', analisi §8): il produttore l'ha gia'
#        fatto, ma la whitelist si rilegge dove si esegue.
#
#        ⚠️ L'AMBIENTE SI PASSA AL FIGLIO, NON SI TOCCA IL PROPRIO. Le due
#        variabili entrano nell'`env` del sottoprocesso — un dizionario
#        copiato — mai in `os.environ`: il drenatore lavora piu' item per
#        giro, e un attore lasciato nell'ambiente del padre passerebbe al
#        lavoro successivo. Il figlio muore con le sue variabili. Sotto
#        systemd il drenatore ha `EnvironmentFile=.env.systemd`, quindi il
#        figlio eredita i segreti che `run-command.sh` si aspetta, esattamente
#        come sotto il timer.
#
#        ⛔ LISTA, MAI SHELL. `Popen([RUN_COMMAND, *comando])`: ogni token
#        passa intero, niente interpolazione, niente `shell=True`.
#
#        ⭐ IL TETTO (`TETTO_SOTTOPROCESSO_SECONDI`, 300 s — decisione 2a di
#        Tid, brief §8.5): mentre aspetta, il drenatore non drena altro. Oltre
#        il tetto il comando viene UCCISO e il lavoro va in ERRORE terminale
#        con `E_PROCESSO_AVVIO_TROPPO_LUNGO`: non e' un guasto, e' un limite
#        dichiarato dell'attrezzo — il rimedio e' `avvio_manuale: false` nel
#        dichiarato, non riparare qualcosa.
#        ⛔ SI UCCIDE IL GRUPPO, NON IL SOLO FIGLIO: sessione propria e
#        `SIGKILL` al gruppo sul tetto o sull'interruzione del drenatore. Il
#        perche' sta nel BB `apps.core.services.sottoprocesso`, che lo fa.
#
#        ⛔ TUTTI GLI ESITI NEGATIVI SONO TERMINALI (`contesto_terminale`). Il
#        tipo ha `max_tentativi = 1` a catalogo (brief §2: un processo caduto a
#        meta' non e' idempotente), ma il marcatore si scrive lo stesso: se un
#        giorno il seed alzasse i tentativi, ritentare un payload rotto, una
#        sveglia non candidata o un comando che e' gia' fallito riprodurrebbe
#        lo stesso esito tenendo il lavoro «in corso» a video.
#
#        ⚠️ Un run lanciato a mano MENTRE il timer sta girando: il lock di
#        `fn_job_run_start` (dove il command lo usa) produce una riga di skip
#        nel giornale del comando, non due corse; il lavoro esce `FATTO` con
#        exit 0. E' cio' che succede oggi a chi lancia da shell.
# Note: Il tipo `ESEGUI_PROCESSO` e' seedato `attivo = false` finche' questo
#        handler non e' in release (regola del binding): a tipo spento
#        `fn_accoda_lavoro` rifiuta con `E_JOB_TYPE_NON_ATTIVO` (501), e
#        l'endpoint non lo maschera. Accenderlo e' una riga del CSV
#        `coda_lavori_tipi`, a carico del team DB, DOPO il deploy di questo
#        file (brief §10.4).
# ------------------------------------------------------------

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.avvio_manuale import (
    E_AVVIO_FALLITO,
    E_AVVIO_TROPPO_LUNGO,
    HANDLER_CODE,
    TETTO_SOTTOPROCESSO_SECONDI,
    motivi_esegui_ora,
)
from apps.core.services.coda_lavori.context import E_SCOPE_OPERATORE
from apps.core.services.sottoprocesso import lancia_con_tetto
from apps.core.services.coda_lavori.drain_engine import contesto_terminale
from apps.core.services.job_run import (
    ENV_JOB_AUTH_USER_ID,
    ENV_JOB_ORIGINE,
    ORIGINE_COMMAND,
)
from apps.core.services.processi_service import E_NOT_FOUND
from apps.core.services.service_errors import E_CONFIG_MANCANTE, E_VALIDATION_INPUT, ServiceError
from apps.core.services.sveglie import RUN_COMMAND, Sveglia, sveglia_di_processo

logger = logging.getLogger(__name__)

# Codici RIUSATI, perche' la condizione e' la stessa di dove sono nati
# (brief §9.1): payload che non risolve nel dichiarato, wrapper assente, scope
# senza l'attore. `E_CONFIG_MANCANTE` (wrapper assente) viene da
# `service_errors`, come `E_VALIDATION_INPUT`.
E_PAYLOAD = E_VALIDATION_INPUT

# Quanto output del comando si tiene nel lavoro: le ULTIME righe, cappate. La
# diagnosi intera sta nel run del comando e nel journal; qui basta la coda per
# capire di che cosa si tratta senza aprire un'altra schermata.
CODA_OUTPUT_RIGHE = 40
CODA_OUTPUT_CARATTERI = 4000


# Scopo: risolve la sveglia (processo, unit) nel dichiarato di deploy. Non
#        trovata ⇒ terminale con `E_VALIDATION_INPUT`, campo `unit`: un
#        payload che nomina una unit che il deploy non ha non migliora
#        ritentando.
def _risolvi_sveglia(processo_codice: str, unit: str) -> Sveglia:
    sveglia = sveglia_di_processo(processo_codice, unit)
    if sveglia is not None:
        return sveglia
    raise ServiceError(
        code=E_PAYLOAD,
        message=(
            f"La sveglia {unit or '(vuota)'} non e' fra quelle dichiarate per il "
            f"processo {processo_codice or '(vuoto)'}: il lavoro non si esegue."
        ),
        detail=f"processo_codice={processo_codice!r} unit={unit!r}",
        context=contesto_terminale(field="unit", processo_codice=processo_codice, unit=unit),
    )


# Scopo: le ultime righe di stdout+stderr del comando, cappate in righe e
#        caratteri. Accetta str o bytes (su `TimeoutExpired` Python li passa
#        come li ha raccolti) e non fallisce mai: e' diagnostica, e una
#        diagnostica che solleva nasconde l'errore che doveva mostrare.
def coda_output(stdout: Any, stderr: Any) -> str:
    righe: list[str] = []
    for grezzo in (stdout, stderr):
        if not grezzo:
            continue
        testo = grezzo.decode("utf-8", errors="replace") if isinstance(grezzo, bytes) else str(grezzo)
        righe.extend(testo.splitlines())
    coda = "\n".join(righe[-CODA_OUTPUT_RIGHE:])
    return coda[-CODA_OUTPUT_CARATTERI:]


# Scopo: «il wrapper c'e' sull'host?» — in una funzione sua, cosi' il test
#        la sostituisce senza toccare il filesystem (`Path.is_file` non si
#        patcha su un'istanza).
def _wrapper_presente() -> bool:
    return RUN_COMMAND.is_file()


# Scopo: l'ambiente del FIGLIO: quello del drenatore piu' le due variabili che
#        `registered_job` legge — origine `COMMAND` e l'attore, cioe' chi ha
#        premuto. Dizionario NUOVO: `os.environ` del padre non si tocca.
def _ambiente_del_figlio(auth_user_id: int) -> dict[str, str]:
    return {
        **os.environ,
        ENV_JOB_ORIGINE: ORIGINE_COMMAND,
        ENV_JOB_AUTH_USER_ID: str(auth_user_id),
    }


# ⭐ Il lancio col tetto (sessione propria, colpo al GRUPPO sul tetto o
#    sull'interruzione) sta nel BB `apps.core.services.sottoprocesso`
#    (`lancia_con_tetto`), dal 2026-10-13: lo usa anche il giro notturno degli
#    smoke. Qui resta solo il tetto di QUESTO attrezzo.
def _lancia(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return lancia_con_tetto(argv, TETTO_SOTTOPROCESSO_SECONDI, env=env)


# Scopo: lo stato effettivo del processo su questa installazione, letto dal
#        DB al momento di lanciare (P-2: spento si rifiuta anche qui, non solo
#        all'accodamento — fra i due c'e' fino a un minuto, e una persona puo'
#        averlo spento nel frattempo). Una funzione a se' perche' i test la
#        sostituiscano senza un database.
# ⛔ Il processo che non c'e' piu' nel registro (la sveglia del dichiarato
#    nomina un codice ritirato dal catalogo) e' il SUO rifiuto, terminale:
#    non «ambiente non dichiarato», che manderebbe a cercare altrove.
def _acceso(processo_codice: str, unit: str) -> bool | None:
    try:
        return ProcessiRepository().acceso_processo(processo_codice)
    except LookupError as exc:
        raise ServiceError(
            code=E_NOT_FOUND,
            message=(
                f"Il processo {processo_codice} della sveglia {unit} non esiste "
                f"nel registro: il lavoro non si esegue."
            ),
            detail=str(exc),
            context=contesto_terminale(processo_codice=processo_codice, unit=unit),
        ) from exc


# Scopo: Esegue il lavoro, nelle cinque mosse del piano §2.3: risolve la
#        sveglia dal dichiarato; ricontrolla il predicato; verifica il wrapper;
#        lancia il sottoprocesso con l'ambiente del figlio e il tetto; traduce
#        l'esito. Ritorna il `result` del lavoro su exit 0.
#        `scope` e' lo scope OPERATORE catturato all'enqueue: da li' si prende
#        l'attore per il giornale del comando.
def esegui_processo_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    processo_codice = str(payload.get("processo_codice") or "")
    unit = str(payload.get("unit") or "")

    # 1. La sveglia, dal dichiarato: e' la whitelist.
    sveglia = _risolvi_sveglia(processo_codice, unit)

    # 2. Il predicato, ricontrollato dove si esegue. `lavoro_vivo=None`: il
    #    lavoro vivo con questa chiave siamo NOI.
    motivi = motivi_esegui_ora(
        sveglia, acceso=_acceso(processo_codice, unit), lavoro_vivo=None,
    )
    if motivi:
        raise motivi[0].come_errore(**contesto_terminale(unit=unit))

    # 3. L'attore: senza, il run del comando non saprebbe dire CHI ha premuto,
    #    e scriverlo come CRON sarebbe il contrario di cio' per cui la
    #    variabile esiste. Un lavoro OPERATORE arriva sempre con la terna
    #    (il produttore la rifiuta prima di accodare): qui e' il presidio.
    auth_user_id = (scope or {}).get("auth_user_id")
    if auth_user_id is None:
        raise ServiceError(
            code=E_SCOPE_OPERATORE,
            message=(
                f"Il lavoro «Esegui ora» della sveglia {unit} non porta l'utente "
                f"che l'ha chiesto: il comando non si lancia senza un attore."
            ),
            detail=f"scope={scope!r}",
            context=contesto_terminale(unit=unit),
        )

    # 4. Il wrapper: e' un fatto del layout, calcolato in `sveglie.py`. Assente
    #    = deploy rotto, e ritentare fra un minuto non lo fa comparire.
    if not _wrapper_presente():
        raise ServiceError(
            code=E_CONFIG_MANCANTE,
            message=(
                f"Il wrapper dei comandi non esiste sull'host "
                f"({RUN_COMMAND}): il deploy del backend non e' completo."
            ),
            detail=f"run_command={str(RUN_COMMAND)!r}",
            context=contesto_terminale(unit=unit, run_command=str(RUN_COMMAND)),
        )

    argv = [str(RUN_COMMAND), *sveglia.comando]
    env = _ambiente_del_figlio(int(auth_user_id))
    logger.info(
        "esegui_processo.avvio unit=%s comando=%s auth_user_id=%s tetto_s=%s",
        unit, " ".join(sveglia.comando), auth_user_id, TETTO_SOTTOPROCESSO_SECONDI,
    )

    # 5. Il sottoprocesso: lista, mai shell; output catturato; il tetto
    #    uccide il gruppo intero.
    partenza = time.monotonic()
    try:
        proc = _lancia(argv, env)
    except subprocess.TimeoutExpired as exc:
        durata_ms = int((time.monotonic() - partenza) * 1000)
        coda = coda_output(exc.stdout, exc.stderr)
        logger.warning(
            "esegui_processo.troppo_lungo unit=%s tetto_s=%s durata_ms=%s",
            unit, TETTO_SOTTOPROCESSO_SECONDI, durata_ms,
        )
        raise ServiceError(
            code=E_AVVIO_TROPPO_LUNGO,
            message=(
                f"Il comando della sveglia {unit} non e' finito entro "
                f"{TETTO_SOTTOPROCESSO_SECONDI} secondi: e' troppo lungo per "
                f"«Esegui ora» ed e' stato interrotto."
            ),
            detail=f"unit={unit!r} tetto_s={TETTO_SOTTOPROCESSO_SECONDI} durata_ms={durata_ms}",
            context=contesto_terminale(
                unit=unit, tetto_secondi=TETTO_SOTTOPROCESSO_SECONDI,
                durata_ms=durata_ms, coda_output=coda,
            ),
        ) from exc

    durata_ms = int((time.monotonic() - partenza) * 1000)
    coda = coda_output(proc.stdout, proc.stderr)
    if proc.returncode != 0:
        logger.warning(
            "esegui_processo.fallito unit=%s exit_code=%s durata_ms=%s",
            unit, proc.returncode, durata_ms,
        )
        raise ServiceError(
            code=E_AVVIO_FALLITO,
            message=(
                f"Il comando della sveglia {unit} e' uscito con codice "
                f"{proc.returncode}: il dettaglio e' nel giornale del processo "
                f"eseguito."
            ),
            detail=f"unit={unit!r} exit_code={proc.returncode} durata_ms={durata_ms}",
            context=contesto_terminale(
                unit=unit, exit_code=proc.returncode, durata_ms=durata_ms,
                coda_output=coda,
            ),
        )

    logger.info(
        "esegui_processo.fatto unit=%s exit_code=0 durata_ms=%s", unit, durata_ms,
    )
    return {
        "unit": unit,
        "comando": list(sveglia.comando),
        "exit_code": 0,
        "durata_ms": durata_ms,
        "coda_output": coda,
    }


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `CoreConfig.ready()`: registrazione esplicita al boot, mai
#        auto-discovery — stesso patto degli altri handler di coda.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, esegui_processo_handler)
