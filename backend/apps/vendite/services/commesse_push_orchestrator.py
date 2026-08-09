# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestratore push commesse — stateless, fan-out per sorgente.
# ------------------------------------------------------------

"""
CommessaPushOrchestrator:
  - Esegue in sequenza tutti gli handler registrati (o un sottoinsieme
    specificato via source_types).
  - Isola gli errori per handler: un fallimento non blocca gli altri.
  - Scrive sempre il log in commesse_push_log al completamento
    (dry_run incluso, con flag dry_run=True sul record).
  - Non usa pipeline, lotti o task-state-machine.
"""

import time
from dataclasses import dataclass, field
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

        # `sorgente_uid`/`righe_ids` propagati nel payload event_log per
        # tracciabilita' del push singolo/selettivo (correlation con la riga
        # sorgente specifica e il sottoinsieme scelto dall'operatore).
        self._repo.log_event(
            domain="COMMESSE",
            entity_type="TASK_RUN",
            entity_id=0,
            event_code="PUSH_STARTED",
            payload={
                "source_types": source_types,
                "dry_run": dry_run,
                "sorgente_uid": sorgente_uid,
                "righe_ids": righe_ids,
            },
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
        )

        push_log_id = self._repo.log_push_run(
            stato=stato,
            dry_run=dry_run,
            source_types=report.source_type_names() or None,
            risultato=report.as_risultato() or None,
            durata_ms=durata_ms,
        )
        report.push_log_id = push_log_id

        errors_count = sum(len(r.errors) for r in results)
        self._repo.log_event(
            domain="COMMESSE",
            entity_type="TASK_RUN",
            entity_id=push_log_id,
            event_code="PUSH_COMPLETED",
            severity="WARN" if stato != "COMPLETATO" else "INFO",
            payload={
                "stato": stato,
                "durata_ms": durata_ms,
                "push_log_id": push_log_id,
                "handlers_count": len(results),
                "errors_count": errors_count,
                "sorgente_uid": sorgente_uid,
            },
        )

        return report
