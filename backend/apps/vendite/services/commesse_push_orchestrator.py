# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestratore push commesse — stateless, fan-out per sorgente.
# ------------------------------------------------------------

"""
CommessaPushOrchestrator:
  - Esegue in sequenza tutti gli handler registrati (o un sottoinsieme
    specificato via source_types).
  - Isola gli errori per handler: un fallimento non blocca gli altri.
  - APRE il giro in commesse_push_log (stato IN_ESECUZIONE, con l'identita'
    del giro) e lo CHIUDE col suo esito, dry_run incluso. ⭐ Un push che muore
    a meta' lascia cosi' la riga IN_ESECUZIONE, che e' l'unica prova che
    qualcosa e' partito e non e' tornato (BE-3b / D-3).
  - Il perimetro del giro (source_types/sorgente_uid/righe_ids) sta sotto
    `risultato.perimetro`.
  - ⛔ NON scrive su vendite.event_log: un giro non e' un'entita' e non ha un
    emittente da cui derivare il perimetro del giornale (BE-3a / D-3).
  - Non usa pipeline, lotti o task-state-machine.
"""

import time
from dataclasses import dataclass, field
from uuid import uuid4
from typing import Any

from django.db import connection

from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.services.commesse_source_handlers import BaseSourceHandler, HandlerResult

_LOCK_KEY = "commesse_push_orchestrator"


@dataclass
class PushReport:
    """Risultato aggregato di un run dell'orchestratore."""

    dry_run: bool
    stato: str  # COMPLETATO | PARZIALE | ERRORE
    handlers: list[HandlerResult] = field(default_factory=list)
    push_log_id: int | None = None
    durata_ms: int | None = None

    def as_risultato(self) -> dict[str, Any]:
        """Serializza i risultati handler per commesse_push_log.risultato (JSONB)."""
        return {r.handler_name: r.as_dict() for r in self.handlers}

    def source_type_names(self) -> list[str]:
        """Codici sorgente processati (config.sorgenti), nell'ordine di esecuzione."""
        return [r.sorgente_codice for r in self.handlers if r.sorgente_codice]


class CommessaPushOrchestrator:
    """Orchestratore stateless per la sincronizzazione commesse da sorgenti esterne.

    Uso tipico:
        repo = CommesseRepository()
        handlers = [HandlerPreventivi(repo), HandlerOrdini(repo)]
        orch = CommessaPushOrchestrator(repo, handlers)
        report = orch.run(dry_run=True)

    Parametri costruttore:
        repo      — CommesseRepository per log e operazioni commesse
        handlers  — lista ordinata di handler sorgente da eseguire
    """

    def __init__(self, repo: CommesseRepository, handlers: list[BaseSourceHandler]) -> None:
        self._repo = repo
        self._handlers = handlers

    # --- Helpers ---

    @staticmethod
    def _try_acquire_lock() -> bool:
        """Tenta di acquisire un advisory lock session-level. Ritorna False se già acquisito."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(hashtext(%s))", [_LOCK_KEY]
            )
            row = cursor.fetchone()
        return bool(row and row[0])

    @staticmethod
    def _release_lock() -> None:
        """Rilascia l'advisory lock session-level."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))", [_LOCK_KEY]
            )

    def _resolve_handlers(self, source_types: list[str] | None) -> list[BaseSourceHandler]:
        """Restituisce gli handler da eseguire.
        None = tutti i registrati; altrimenti filtra per name.
        """
        if source_types is None:
            return self._handlers
        return [h for h in self._handlers if h.sorgente_codice in source_types]

    @staticmethod
    def _compute_stato(results: list[HandlerResult]) -> str:
        """Determina lo stato aggregato del run.

        COMPLETATO — tutti gli handler terminati senza errori.
        PARZIALE   — almeno un handler con errori, almeno uno senza.
        ERRORE     — nessun handler eseguito, o tutti con errori.

        ⚠️ Perche' questo ciclo NON usa `apps.core.services.fan_out.run_fan_out`
        (valutato e scartato, brief fan-out §F5 — 2026-08-09). Due ragioni, e
        sono di semantica, non di comodita':

        1. Qui «fallito» NON vuol dire «ha sollevato». Un handler che completa
           il suo giro e restituisce un `HandlerResult` con 2 righe in errore e'
           gia' contato come non-riuscito da `any(r.errors)`. Per il fan-out
           quell'handler e' semplicemente riuscito: lui vede solo le eccezioni.
           Sono due domande diverse sullo stesso ciclo.
        2. Sulla lista VUOTA le risposte sono opposte, ed entrambe giuste: qui
           «nessun handler risolto» e' una configurazione sbagliata → ERRORE;
           per un fan-out «nessun item da lavorare» e' un giro riuscito →
           COMPLETATO. Appianare la differenza cambierebbe lo stato scritto in
           `commesse_push_log`.

        Questo ciclo e' un livello sopra: itera su handler che sono ESSI STESSI
        fan-out (`BaseSourceHandler._process_rows`, che il BB lo usa davvero).
        E' un aggregatore di report, non un fan-out — infatti non isola in
        transazione: lo fanno gli handler al loro interno.
        """
        if not results:
            return "ERRORE"
        if all(r.errors for r in results):
            return "ERRORE"
        if any(r.errors for r in results):
            return "PARZIALE"
        return "COMPLETATO"

    # --- Run ---

    def run(
        self,
        *,
        source_types: list[str] | None = None,
        dry_run: bool = False,
        sorgente_uid: int | None = None,
        righe_ids: list[int] | None = None,
    ) -> PushReport:
        """Esegue il push per tutti gli handler (o per i source_types selezionati).

        Parametri:
            source_types — None = tutti; lista di nomi = sottoinsieme
            dry_run      — True: gli handler non scrivono, ma il log viene comunque
                           scritto con dry_run=True per audit
            sorgente_uid — None = batch standard; valorizzato = push singolo
                           filtrato sulla riga sorgente del documento. Tipicamente
                           usato con `source_types=[<codice unico>]`.
            righe_ids    — sottoinsieme righe del documento (smistamento selettivo);
                           ha senso solo con sorgente_uid valorizzato e sorgenti
                           che lo supportano (oggi PREVENTIVO).

        Restituisce PushReport con stato, risultati per handler e push_log_id.
        Se un altro run è già in corso restituisce PushReport con stato SKIPPED.
        """
        if not self._try_acquire_lock():
            return PushReport(dry_run=dry_run, stato="SKIPPED", durata_ms=0)

        try:
            return self._run_locked(
                source_types=source_types, dry_run=dry_run,
                sorgente_uid=sorgente_uid, righe_ids=righe_ids,
            )
        finally:
            self._release_lock()

    def _run_locked(
        self,
        *,
        source_types: list[str] | None,
        dry_run: bool,
        sorgente_uid: int | None = None,
        righe_ids: list[int] | None = None,
    ) -> PushReport:
        """Logica di run effettiva, eseguita sotto advisory lock."""
        t0 = time.monotonic()
        results: list[HandlerResult] = []

        # ⛔ QUI NON SI SCRIVE PIU' SU `event_log` (consegna BE-3a, D-3 del
        #    brief `brief-db-event-log-scope-e-riga-parlante.md`).
        #
        #    Il giornale registra fatti accaduti a un'ENTITA' di cui sappia
        #    dire di chi e': deriva il perimetro da `entity_type`+`entity_id`,
        #    e se non ci riesce rifiuta la riga. Un GIRO di push non e'
        #    un'entita' e non ha un emittente — attraversa piu' sorgenti e
        #    quindi, potenzialmente, piu' emittenti. `TASK_RUN` e' rimasto a
        #    catalogo (`config.tipi_entita`) perche' l'errore di qualcun altro
        #    puo' PUNTARCI, ma con `modo_risoluzione_emittente = NULL`: nel
        #    giornale non entra, e il trigger lo rifiuta anche con un
        #    `entity_id` valido.
        #
        # 🔴 E l'`entity_id = 0` di prima non era un segnaposto: era un id che
        #    NON ESISTEVA ANCORA, perche' la riga di `commesse_push_log`
        #    nasceva a FINE giro. Un segnaposto e' una convenzione da
        #    interpretare, un id inesistente e' una sequenza sbagliata.
        #
        # ⭐ Il momento dell'avvio si registra QUI, in `commesse_push_log`, con
        #    la riga creata IN TESTA allo stato IN_ESECUZIONE (consegna BE-3b).
        #    E' il posto giusto: e' il registro del GIRO, dove stava gia' meta'
        #    della sua storia.

        # ⭐ L'IDENTITA' DEL GIRO (D-7): un uuid nuovo a ogni corsa, coniato
        #    prima che il giro produca qualcosa. Ha dove stare proprio perche'
        #    la riga nasce adesso e non a fine corsa.
        correlation_id = str(uuid4())

        # ⛔ FUORI DAL TELAIO BEST-EFFORT, e la differenza e' sostanziale: qui
        #    non si sta scrivendo un appunto SU un lavoro, si sta aprendo il
        #    registro CHE E' quel lavoro. Il `push_log_id` che torna serve alla
        #    chiusura: se l'apertura fallisse e la si ingoiasse, il giro
        #    proseguirebbe senza un posto dove riferire com'e' andato.
        push_log_id = self._repo.start_push_run(
            dry_run=dry_run,
            source_types=source_types,
            correlation_id=correlation_id,
        )

        for handler in self._resolve_handlers(source_types):
            try:
                result = handler.run(
                    dry_run=dry_run, sorgente_uid=sorgente_uid, righe_ids=righe_ids,
                )
            except Exception as exc:
                result = HandlerResult(
                    handler_name=handler.name,
                    sorgente_codice=handler.sorgente_codice,
                    errors=[str(exc)],
                )
            results.append(result)

        durata_ms = int((time.monotonic() - t0) * 1000)
        stato = self._compute_stato(results)

        report = PushReport(
            dry_run=dry_run,
            stato=stato,
            handlers=results,
            durata_ms=durata_ms,
            push_log_id=push_log_id,
        )

        # ⭐ IL `risultato` PORTA ANCHE IL PERIMETRO DEL GIRO (BE-3a).
        #    `sorgente_uid` e `righe_ids` vivevano SOLO nel payload di
        #    `PUSH_STARTED`: togliendo l'evento senza questa riga si sarebbe
        #    perso «su quale documento, e su quali sue righe» era stato chiesto
        #    il push — cioe' l'unica cosa che distingue un push singolo da un
        #    batch. `stato`, `durata_ms` e l'esito per handler erano gia' qui,
        #    ed e' il motivo per cui `PUSH_COMPLETED` non lascia un buco.
        #
        # ⚠️ `source_types` si ripassa perche' ora e' quello EFFETTIVO (gli
        #    handler risolti), non quello richiesto: e' l'unico dei tre campi
        #    che l'apertura non poteva conoscere.
        self._repo.close_push_run(
            push_log_id=push_log_id,
            stato=stato,
            source_types=report.source_type_names() or None,
            risultato={
                "handlers": report.as_risultato(),
                "perimetro": {
                    "source_types": source_types,
                    "sorgente_uid": sorgente_uid,
                    "righe_ids": righe_ids,
                },
            },
            durata_ms=durata_ms,
        )

        return report
