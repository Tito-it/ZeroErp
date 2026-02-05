from dataclasses import dataclass
from datetime import date

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import LottoPipelineMeta, PipelineStepLogMeta
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor

# Orchestratore applicativo della pipeline lotto vendite (equivalente SQL).

@dataclass(frozen=True)
class LottoPipelineParams:
    lotto_id: int | None = None
    competenza_mese: date | None = None
    tipo_doc_fiscale_id: int | None = None
    utility_id: int | None = None
    billing_account_id: int | None = None
    lock_batch_id: str | None = None
    meta: LottoPipelineMeta | None = None
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

    def _mark_lotto_error(
        self,
        *,
        lotto_id: int,
        code: str,
        tipo_lotto: str,
        detail: str | None,
    ) -> None:
        # Mantiene stato lotto coerente e traccia errore con codice uniforme.
        with transaction.atomic():
            self.repository.set_lotto_job_stato(lotto_id, "ERRORE", "Errore pipeline")
            ErrorManager.log_error_only(
                code=code,
                context={"lotto_id": lotto_id, "tipo_lotto": tipo_lotto, "detail": detail},
                area="backend",
                function_name="vendite.pr_run_lotto_pipeline",
            )

    def run_pipeline(self, params: LottoPipelineParams) -> int:
        lotto_id: int | None = None
        effective_tipo_lotto = params.tipo_lotto or "MASSIVO"
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

                # Fonte autoritativa dominio: il tipo persistito sul lotto a DB; params è fallback.
                lotto_tipo_db = self.repository.get_lotto_tipo(lotto_id)
                effective_tipo_lotto = lotto_tipo_db or effective_tipo_lotto
                inviata_id = self.repository.get_stato_doc_fiscale_id("INVIATA")

                self.repository.set_lotto_job_stato(lotto_id, "IN_ESECUZIONE", "Avvio pipeline")

                for step in self.repository.list_pipeline_steps(effective_tipo_lotto):
                    # Traccia avanzamento step coerente con il flusso SQL originale.
                    self.repository.update_lotto_stato_doc(lotto_id, step.stato_doc_fiscale_id)
                    if (
                        effective_tipo_lotto == "GIORNALIERO"
                        and inviata_id is not None
                        and step.stato_doc_fiscale_id == inviata_id
                    ):
                        # Il lotto giornaliero viene chiuso operativamente allo stato INVIATA.
                        self.repository.close_giornaliero_lotto(lotto_id, inviata_id)

                    step_meta: PipelineStepLogMeta = {
                        "ordine": step.ordine,
                        "dry_run": params.dry_run,
                    }
                    self.repository.log_pipeline_fase(
                        lotto_id=lotto_id,
                        stato_doc_fiscale_id=step.stato_doc_fiscale_id,
                        fase=step.descrizione or "Esecuzione step",
                        status="I",
                        messaggio=None,
                        meta=step_meta,
                    )

                    self.step_executor.execute_step(
                        lotto_id=lotto_id,
                        stato_doc_fiscale_id=step.stato_doc_fiscale_id,
                        rollback=False,
                        dry_run=params.dry_run,
                    )

                self.repository.set_lotto_job_stato(lotto_id, "COMPLETATO", "Pipeline completata")
                return lotto_id
        except ServiceError as exc:
            if lotto_id is not None:
                self._mark_lotto_error(
                    lotto_id=lotto_id,
                    code=exc.code,
                    tipo_lotto=effective_tipo_lotto,
                    detail=exc.detail or str(exc),
                )
            raise
        except Exception as exc:
            if lotto_id is not None:
                self._mark_lotto_error(
                    lotto_id=lotto_id,
                    code="E_PIPELINE",
                    tipo_lotto=effective_tipo_lotto,
                    detail=str(exc),
                )
            ErrorManager.raise_error(
                code="E_PIPELINE",
                message="Errore nella pipeline di fatturazione.",
                detail=str(exc),
                context={"lotto_id": lotto_id, "tipo_lotto": effective_tipo_lotto},
                function_name="vendite.pr_run_lotto_pipeline",
                # Se il lotto è già creato l'errore è già persistito da _mark_lotto_error.
                log_to_db=lotto_id is None,
                cause=exc,
            )
