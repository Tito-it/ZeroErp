from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.request_parsers import parse_iso_date
from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.


@require_POST
def run_lotto_pipeline(request: HttpRequest) -> JsonResponse:
    def _handler(payload: dict[str, object]) -> dict[str, object]:
        lotto_id = pr_run_lotto_pipeline(
            lotto_id=payload.get("lotto_id"),
            competenza_mese=parse_iso_date(payload.get("competenza_mese")),
            tipo_doc_fiscale_id=payload.get("tipo_doc_fiscale_id"),
            utility_id=payload.get("utility_id"),
            billing_account_id=payload.get("billing_account_id"),
            lock_batch_id=payload.get("lock_batch_id"),
            meta=payload.get("meta"),
            dry_run=bool(payload.get("dry_run", False)),
            tipo_lotto=payload.get("tipo_lotto", "MASSIVO"),
        )
        return {"lotto_id": lotto_id, "status": "ok"}

    # Pattern condiviso: JSON parse + envelope errori centralizzato.
    return handle_post_json(request, handler=_handler)
