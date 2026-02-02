from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor

# Orchestratore applicativo della pipeline lotto vendite (equivalente SQL).

@dataclass(frozen=True)
class LottoPipelineParams:
    lotto_id: int | None = None
    competenza_mese: date | None = None
    tipo_doc_fiscale_id: int | None = None
    utility_id: int | None = None
    billing_account_id: int | None = None
    lock_batch_id: int | None = None
    meta: dict[str, Any] | None = None
    dry_run: bool = False
    tipo_lotto: str = "MASSIVO"


class LottoPipelineRunner:
    """Controparte Django della procedura SQL vendite.pr_run_lotto_pipeline."""

    def __init__(
        self,
        repository: VenditePipelineRepository | None = None,
        step_executor: PipelineStepExecutor | None = None,
    ) -> None:
        self.repository = repository or VenditePipelineRepository()
        self.step_executor = step_executor or PipelineStepExecutor(self.repository)

    def run(self, params: LottoPipelineParams) -> int:
        lotto_id: int | None = None
        try:
            with transaction.atomic():
                # Mantiene il comportamento SQL: lotto_id=0 equivale a creare/risolvere un lotto.
                normalized_lotto_id = None if params.lotto_id in (0, None) else params.lotto_id
                lotto_id = self.repository.get_or_create_lotto(
                    lotto_id=normalized_lotto_id,
                    competenza_mese=params.competenza_mese,
                    tipo_doc_fiscale_id=params.tipo_doc_fiscale_id,
                    utility_id=params.utility_id,
                    billing_account_id=params.billing_account_id,
                    lock_batch_id=params.lock_batch_id,
                    meta=params.meta,
                    tipo_lotto=params.tipo_lotto,
                )

                lotto_tipo = self.repository.get_lotto_tipo(lotto_id) or params.tipo_lotto or "MASSIVO"
                inviata_id = self.repository.get_stato_doc_fiscale_id("INVIATA")

                self.repository.set_lotto_job_stato(lotto_id, "IN_ESECUZIONE", "Avvio pipeline")

                for step in self.repository.list_pipeline_steps(lotto_tipo):
                    # Traccia avanzamento step coerente con il flusso SQL originale.
                    self.repository.update_lotto_stato_doc(lotto_id, step.stato_doc_fiscale_id)
                    if (
                        lotto_tipo == "GIORNALIERO"
                        and inviata_id is not None
                        and step.stato_doc_fiscale_id == inviata_id
                    ):
                        # Il lotto giornaliero viene chiuso operativamente allo stato INVIATA.
                        self.repository.close_giornaliero_lotto(lotto_id, inviata_id)

                    self.repository.log_pipeline_fase(
                        lotto_id=lotto_id,
                        stato_doc_fiscale_id=step.stato_doc_fiscale_id,
                        fase=step.descrizione or "Esecuzione step",
                        status="I",
                        messaggio=None,
                        meta={"ordine": step.ordine, "dry_run": params.dry_run},
                    )

                    self.step_executor.execute_step(
                        lotto_id=lotto_id,
                        stato_doc_fiscale_id=step.stato_doc_fiscale_id,
                        rollback=False,
                        dry_run=params.dry_run,
                    )

                self.repository.set_lotto_job_stato(lotto_id, "COMPLETATO", "Pipeline completata")
                return lotto_id
        except Exception:
            if lotto_id is not None:
                # Preserva il contratto SQL: qualsiasi errore porta il lotto in stato ERRORE.
                with transaction.atomic():
                    self.repository.set_lotto_job_stato(lotto_id, "ERRORE", "Errore pipeline")
                    # Log applicativo centralizzato in tabella errori (best-effort).
                    ErrorManager.log_error_only(
                        code="E_PIPELINE_RUN",
                        context={"lotto_id": lotto_id, "tipo_lotto": params.tipo_lotto},
                        area="backend",
                        function_name="vendite.pr_run_lotto_pipeline",
                    )
            raise
