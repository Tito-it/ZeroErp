# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `FATTURAZIONE_GIRO` (coda lavori generica, C-3): il
#        giro di fatturazione on-demand richiesto dall'operatore. È il primo
#        consumatore della coda `dbops.coda_lavori`. Registrato nel registry
#        handler (`handler_code = fatturazione_giro_default`, dal seed DB) al
#        boot di `VenditeConfig.ready()`.
#
#        Contesto d'esecuzione: il drainer lo invoca DENTRO
#        `operator_identity_context` (run_as=OPERATORE) → RLS ATTIVA con
#        l'identità dell'operatore che ha accodato. La discovery
#        (`fn_list_emittibili_lane`) e l'esecuzione della pipeline sono quindi
#        **scoped all'operatore via RLS** («esegue con i permessi
#        dell'operatore», guida Gestione code di lavoro). Nessun filtro
#        emittente esplicito qui: lo scope è la RLS, non un parametro.
#
#        Invariante I-1: chiama lo STESSO core del cron
#        (`esegui_giro_fatturazione`), niente seconda implementazione. Corsia
#        `differita` (on-demand): si ferma a EMESSA (D-1); la numerazione è un
#        atto separato (C-4). Best-effort per-terna (il core non solleva su
#        terna fallita): l'esito strutturato diventa il `result` del job.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from apps.core.services.coda_lavori.drain_engine import contesto_terminale
from apps.core.services.error_manager import ServiceError
from apps.vendite.services._fatturazione_job_helpers import (
    messaggio_gruppi_non_serviti,
    parse_competenza_mese,
    parse_gruppi,
    spiega_gruppi_non_serviti,
)

# handler_code seedato in dbops.coda_lavori_tipi per il tipo FATTURAZIONE_GIRO.
HANDLER_CODE = "fatturazione_giro_default"

# Corsia del giro on-demand di MASSA: differita → fermata a EMESSA (D-1).
_MODALITA_ONDEMAND = "differita"

# La corsia dell'EMISSIONE MIRATA (BF-1) NON e' ridichiarata qui: si importa
# dal driver, che ne e' l'owner (`_MODALITA`). Un secondo letterale "mirata"
# in questo modulo si sarebbe potuto disallineare dal dizionario delle corsie
# — e il sintomo sarebbe stato un giro che parte e non fattura nulla.
# L'import e' locale alla funzione, come quello del core: il modulo e'
# registrato in `ready()` e non deve tirarsi dietro la catena driver al boot.

# Codice errore per payload di giro malformato: fallimento di dominio parlante
# (finisce in `coda.ultimo_errore`; non è una risposta HTTP → non va in
# error_policies). Parse condiviso in _fatturazione_job_helpers (regola del 2).
E_GIRO_PAYLOAD = "E_FATTURAZIONE_GIRO_PAYLOAD"

# Emissione MIRATA che non produce nemmeno un lotto: il perimetro qui e'
# NOMINALE — l'operatore ha indicato quei gruppi, uno per uno. «Zero lotti su N
# gruppi chiesti» non e' un giro senza lavoro (quello e' il caso del giro di
# massa, ed e' legittimo): e' una richiesta esplicita non soddisfatta, e deve
# risultare tale nella coda. Stesso principio del ritiro delle bandiere sui task
# per-fattura: chi chiede e non ottiene non legge «fatto».
E_GIRO_NESSUN_LOTTO = "E_FATTURAZIONE_GIRO_NESSUN_LOTTO"


# Scopo: Esegue il giro di fatturazione on-demand. `payload`:
#        `{competenza_mese: ISO, fino_a_stato?: codice, gruppi?: [chiavi]}`.
#        `scope`: catturato all'enqueue (`{auth_user_id, emittente_ids}`) — qui
#        NON usato per filtrare (lo fa la RLS del contesto operatore), presente
#        per il vincolo DB run_as↔scope e per l'audit. Ritorna l'esito compatto
#        del giro (senza la lista per-terna) come `result` del job.
#
#        Due modi nello STESSO job type, distinti dalla presenza di `gruppi`:
#        senza → giro di massa del mese (corsia differita, comportamento
#        storico); con → EMISSIONE MIRATA sui soli gruppi richiesti (corsia
#        mirata). Un solo verbo, un solo handler: la differenza e' il
#        perimetro, non il processo (invariante I-1).
def fatturazione_giro_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    competenza = parse_competenza_mese(
        payload.get("competenza_mese"), error_code=E_GIRO_PAYLOAD,
    )
    fino_a_stato = payload.get("fino_a_stato")
    gruppi = parse_gruppi(payload.get("gruppi"), error_code=E_GIRO_PAYLOAD)

    # Import locale: evita di caricare la catena driver al boot del modulo
    # (registrato in ready()); il core è l'unico punto di verità I-1.
    from apps.vendite.services.fatturazione_driver_service import (
        MODALITA_MIRATA,
        esegui_giro_fatturazione,
    )

    kwargs: dict[str, Any] = {
        "modalita": MODALITA_MIRATA if gruppi else _MODALITA_ONDEMAND,
        "competenza": competenza,
    }
    if gruppi:
        kwargs["gruppi"] = gruppi
    if fino_a_stato:
        kwargs["fino_a_stato"] = fino_a_stato

    summary = esegui_giro_fatturazione(**kwargs)

    # Emissione mirata a vuoto: si fallisce, invece di restituire un successo
    # muto (difetto misurato il 2026-08-03, job 141). DUE cause distinte, e
    # vanno tenute separate:
    #   - terne trovate ma pipeline fallita (`falliti` > 0) → la causa vera e'
    #     negli esiti per terna, e puo' essere TRANSIENTE (lock, DB): niente
    #     diagnosi di perimetro (racconterebbe la cosa sbagliata) e niente
    #     marca terminale (i retry della coda hanno senso);
    #   - nessuna terna → la diagnosi di perimetro spiega perche', ed e'
    #     deterministica (una commessa in BOZZA resta in BOZZA al 5° tentativo).
    # La diagnosi gira SOLO a valle di un giro vuoto: dopo un'emissione
    # riuscita le righe sono gia' EMESSA e la fotografia racconterebbe
    # l'arrivo, non l'ostacolo.
    if gruppi and not summary.get("lotti"):
        if summary.get("falliti"):
            _fallisci_giro_mirato_per_errori_terna(gruppi, summary)
        _fallisci_giro_mirato(gruppi, competenza, summary)

    # Emissione mirata PARZIALE: lotti prodotti, ma qualche gruppo richiesto
    # non e' entrato in nessuna terna (`gruppi_non_coperti`, misurato alla
    # discovery — rev DB 2026-08-15). Era il caso PEGGIORE dei tre perche'
    # l'unico silenzioso: «zero fatture» solleva ed e' un errore parlante,
    # «2 su 3» sembrava un successo e il lavoro non fatturato restava fermo
    # senza che nessuno lo cercasse. NON si solleva — i lotti prodotti sono
    # lavoro vero e il job e' riuscito per la sua parte — ma l'esito porta la
    # diagnosi per-gruppo (stessa classificazione del giro a vuoto), cosi' il
    # FE puo' dire «2 su 3, il terzo no perche'…» e l'operatore agisce sulla
    # causa invece di riprovare al buio.
    if gruppi and summary.get("lotti") and summary.get("gruppi_non_coperti"):
        summary["gruppi_non_serviti"] = _diagnostica_e_spiega(
            summary["gruppi_non_coperti"], competenza,
        )

    # Compatta per il `result` del job (la lista per-terna gonfierebbe il jsonb;
    # il dettaglio vive nei log/task_runs, correlati via job_run). La chiave
    # `lotti` NON si potata: e' l'estratto compatto che alimenta il «vai al
    # lotto» del FE, e senza di essa l'operatore dovrebbe cercare a mano nella
    # lista lotti il contenitore appena prodotto.
    return {k: v for k, v in summary.items() if k != "esiti"}


# Scopo: Diagnostica e classifica un elenco di gruppi non serviti — la STESSA
#        fotografia e la STESSA classificazione per entrambi gli esiti che la
#        usano: il giro a vuoto (che poi solleva) e il giro parziale (che
#        arricchisce l'esito). Sede unica di proposito: se la catena cambia
#        (un kwarg nuovo, un filtro), i due percorsi non possono divergere.
def _diagnostica_e_spiega(
    gruppi_non_serviti: tuple[str, ...] | list[str],
    competenza: date,
) -> list[dict[str, Any]]:
    # Import locale come il core: l'handler e' importato in `ready()` e non deve
    # tirarsi dietro il repository al boot.
    from apps.vendite.db.commesse_repository import CommesseRepository

    diagnosi = CommesseRepository().diagnostica_gruppi(
        gruppi=gruppi_non_serviti, competenza_mese=competenza,
    )
    return spiega_gruppi_non_serviti(diagnosi)


# Scopo: SOLLEVA per il giro mirato in cui le terne c'erano ma OGNI pipeline e'
#        fallita. Il messaggio riporta gli errori per terna (dagli `esiti` del
#        core), non la fotografia del perimetro: il perimetro era valido, e'
#        l'esecuzione che si e' rotta. NON terminale: un errore pipeline puo'
#        essere transiente e i retry con backoff della coda sono il rimedio
#        giusto — al contrario del fallimento di perimetro qui sotto.
def _fallisci_giro_mirato_per_errori_terna(
    gruppi: tuple[str, ...],
    summary: dict[str, Any],
) -> None:
    errori = [
        f"{e.get('errore_code') or '?'}: {e.get('errore_detail') or ''}".strip(": ")
        for e in summary.get("esiti") or []
        if not e.get("ok")
    ]
    raise ServiceError(
        code=E_GIRO_NESSUN_LOTTO,
        message=(
            "Nessun lotto prodotto: il giro sui gruppi selezionati è fallito "
            f"({'; '.join(errori) or 'nessun dettaglio dalle terne'})."
        ),
        detail=f"gruppi richiesti: {len(gruppi)}, terne fallite: {summary['falliti']}",
        context={
            "errori_terna": errori,
            "summary": {k: v for k, v in summary.items() if k != "esiti"},
        },
    )


# Scopo: Diagnostica i gruppi richiesti e SOLLEVA con il motivo per ciascuno.
#        Obiettivo: l'operatore che ha chiesto «fattura questo» deve leggere
#        perche' non e' successo, non un generico «nulla era fatturabile».
#        Il messaggio finisce in `coda_lavori.ultimo_errore.message`, che il FE
#        rende com'e'; il dettaglio strutturato (un motivo per gruppo) va in
#        `context`, che il motore della coda PERSISTE dentro `ultimo_errore`
#        (drain_engine._lavora_item): resta interrogabile senza riparsare il
#        testo.
#
#        `context["terminale"]`: il fallimento e' DETERMINISTICO — una commessa in
#        BOZZA resta in BOZZA anche al quinto tentativo. Senza questa marca la
#        coda ripeterebbe il giro `max_tentativi` volte (5 per FATTURAZIONE_GIRO)
#        con backoff, lasciando il job «in corso» a video per minuti e scrivendo
#        cinque volte lo stesso errore.
def _fallisci_giro_mirato(
    gruppi: tuple[str, ...],
    competenza: date,
    summary: dict[str, Any],
) -> None:
    spiegazioni = _diagnostica_e_spiega(gruppi, competenza)
    raise ServiceError(
        code=E_GIRO_NESSUN_LOTTO,
        message=messaggio_gruppi_non_serviti(
            spiegazioni, totale_richiesti=len(gruppi),
        ),
        detail=f"gruppi richiesti: {len(gruppi)}, lotti prodotti: 0",
        context=contesto_terminale(
            gruppi_non_serviti=spiegazioni,
            summary={k: v for k, v in summary.items() if k != "esiti"},
        ),
    )


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `VenditeConfig.ready()` (import del modulo). Dispatch controllato:
#        `dbops.coda_lavori_tipi.handler_code` → questa funzione.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, fatturazione_giro_handler)
