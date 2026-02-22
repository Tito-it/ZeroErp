# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione esecuzione pipeline attivita fatturabili.
# ------------------------------------------------------------


from dataclasses import dataclass
from datetime import date

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineRepository,
    AttivitaSorgenteBranchPolicy,
)
from apps.vendite.services.attivita_pipeline_error_logger import AttivitaPipelineErrorLogger
from apps.vendite.services.attivita_pipeline_step_executor import (
    AttivitaPipelineStepExecutor,
    _AttivitaBranchBlockError,
    _AttivitaGlobalBlockError,
)

# Orchestratore applicativo della pipeline attivita fatturabili con semantica branch-first.


@dataclass(frozen=True)
class AttivitaPipelineParams:
    lotto_id: int | None = None
    competenza_mese: date | None = None
    utility_id: int | None = None
    billing_account_id: int | None = None
    sorgente_tipo_id: int | None = None  # filtro opzionale: solo questa sorgente
    emittente_soggetto_ruolo_id: int | None = None
    lock_batch_id: str | None = None
    meta: dict | None = None
    dry_run: bool = False


class AttivitaPipelineRunner:
    """Orchestratore pipeline attivita fatturabili: branch indipendenti per sorgente."""

    # Scopo: Inizializza la istanza.
    def __init__(
        self,
        repository: AttivitaPipelineRepository | None = None,
        step_executor: AttivitaPipelineStepExecutor | None = None,
        error_logger: AttivitaPipelineErrorLogger | None = None,
    ) -> None:
        self.repository = repository or AttivitaPipelineRepository()
        self.step_executor = step_executor or AttivitaPipelineStepExecutor(self.repository)
        self.error_logger = error_logger or AttivitaPipelineErrorLogger(self.repository)

    # Scopo: Registra errore lotto attivita su log dominio e forza stato ERRORE.
    def _mark_lotto_error(self, lotto_id: int, detail: str) -> None:
        self.error_logger.log_error(
            scope="ATTIVITA_FATTURABILI",
            severity="C",
            code="E_ATTIVITA_PIPELINE",
            message="Errore pipeline attivita fatturabili",
            detail=detail,
            lotto_id=lotto_id,
            function_name="vendite.attivita_pipeline_runner.run_pipeline",
        )
        self.repository.set_lotto_attivita_stato(lotto_id, "ERRORE", "Errore pipeline")

    # Scopo: Prova a marcare il lotto in errore senza mascherare l'eccezione principale.
    def _mark_lotto_error_safely(self, lotto_id: int, detail: str) -> None:
        # Il mark errore non deve mai mascherare l'eccezione principale.
        try:
            self._mark_lotto_error(lotto_id, detail)
        except Exception as mark_exc:
            ErrorManager.log_error_only(
                code="E_ATTIVITA_PIPELINE",
                context={
                    "lotto_id": lotto_id,
                    "detail": detail,
                    "mark_error": str(mark_exc),
                },
                area="backend",
                function_name="vendite.attivita_pipeline_runner.run_pipeline",
            )

    # Scopo: Esegue tutti gli step del branch per la sorgente indicata.
    def _run_branch(
        self,
        *,
        lotto_id: int,
        sorgente: AttivitaSorgenteBranchPolicy,
        params: AttivitaPipelineParams,
    ) -> None:
        steps = self.repository.list_attivita_pipeline_steps(
            utility_id=params.utility_id,
            sorgente_tipo_id=sorgente.sorgente_tipo_id,
        )
        for step in steps:
            self.step_executor.execute_step(
                lotto_id=lotto_id,
                codice_step=step.codice_step,
                sorgente=sorgente,
                dry_run=params.dry_run,
            )

    # Scopo: Orchestra l'intero flusso pipeline attivita: risoluzione lotto, branch loop, gestione errori.
    def run_pipeline(self, params: AttivitaPipelineParams) -> int:
        lotto_id: int | None = None
        try:
            with transaction.atomic():
                # lotto_id=0 equivale a creare/risolvere un lotto (compatibilita` con dominio lotto).
                normalized_lotto_id = None if params.lotto_id in (0, None) else params.lotto_id
                is_existing = normalized_lotto_id is not None

                lotto_id = self.repository.get_or_create_lotto_attivita(
                    lotto_id=normalized_lotto_id,
                    competenza_mese=params.competenza_mese,
                    utility_id=params.utility_id,
                    billing_account_id=params.billing_account_id,
                    sorgente_tipo_id=params.sorgente_tipo_id,
                    lock_batch_id=params.lock_batch_id,
                    meta=params.meta,
                    emittente_soggetto_ruolo_id=params.emittente_soggetto_ruolo_id,
                )

                # Guard: non rilanciare su lotto gia` in esecuzione.
                # Evita falsi positivi sui lotti appena creati (lotto_id=0).
                if is_existing and self.repository.is_lotto_attivita_in_esecuzione(lotto_id):
                    ErrorManager.raise_error(
                        code="E_ATTIVITA_PIPELINE",
                        message="Lotto attivita gia` in esecuzione.",
                        detail=f"Rilancio non consentito su lotto in esecuzione: {lotto_id}",
                        context={"lotto_id": lotto_id},
                        function_name="vendite.attivita_pipeline_runner.run_pipeline",
                        log_to_db=True,
                    )

                # Sorgenti abilitate con filtro opzionale per sorgente_tipo_id.
                sorgenti = self.repository.list_sorgenti_abilitate(
                    utility_id=params.utility_id
                )
                if params.sorgente_tipo_id is not None:
                    sorgenti = [
                        s for s in sorgenti if s.sorgente_tipo_id == params.sorgente_tipo_id
                    ]

                ErrorManager.require(
                    bool(sorgenti),
                    code="E_ATTIVITA_PIPELINE",
                    message="Nessuna sorgente abilitata trovata.",
                    detail="Pipeline attivita richiede almeno una sorgente abilitata",
                    context={
                        "utility_id": params.utility_id,
                        "sorgente_tipo_id": params.sorgente_tipo_id,
                    },
                    function_name="vendite.attivita_pipeline_runner.run_pipeline",
                    log_to_db=True,
                )

                self.repository.set_lotto_attivita_stato(
                    lotto_id, "IN_ESECUZIONE", "Avvio pipeline"
                )

                # Branch-first: ogni sorgente e` un branch indipendente.
                global_blocked = False
                for sorgente in sorgenti:
                    try:
                        self._run_branch(
                            lotto_id=lotto_id, sorgente=sorgente, params=params
                        )
                    except _AttivitaGlobalBlockError:
                        global_blocked = True
                        break
                    except _AttivitaBranchBlockError:
                        continue  # branch fallisce, altri branch proseguono

                stato_finale = "ERRORE" if global_blocked else "COMPLETATO"
                self.repository.set_lotto_attivita_stato(
                    lotto_id,
                    stato_finale,
                    "Pipeline completata" if stato_finale == "COMPLETATO" else "Pipeline in errore",
                )
                return lotto_id

        except ServiceError as exc:
            if lotto_id is not None:
                self._mark_lotto_error_safely(lotto_id, exc.detail or str(exc))
            raise
        except Exception as exc:
            if lotto_id is not None:
                self._mark_lotto_error_safely(lotto_id, str(exc))
            ErrorManager.raise_error(
                code="E_ATTIVITA_PIPELINE",
                message="Errore nella pipeline attivita fatturabili.",
                detail=str(exc),
                context={"lotto_id": lotto_id},
                function_name="vendite.attivita_pipeline_runner.run_pipeline",
                # Se il lotto e` gia` creato l'errore e` gia` persistito da _mark_lotto_error.
                log_to_db=lotto_id is None,
                cause=exc,
            )
