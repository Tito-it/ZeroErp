import json
from datetime import date

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from apps.vendite.services.exceptions import PipelineError
from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


@require_POST
def run_lotto_pipeline(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    try:
        lotto_id = pr_run_lotto_pipeline(
            lotto_id=payload.get("lotto_id"),
            competenza_mese=_parse_date(payload.get("competenza_mese")),
            tipo_doc_fiscale_id=payload.get("tipo_doc_fiscale_id"),
            utility_id=payload.get("utility_id"),
            billing_account_id=payload.get("billing_account_id"),
            lock_batch_id=payload.get("lock_batch_id"),
            meta=payload.get("meta"),
            dry_run=bool(payload.get("dry_run", False)),
            tipo_lotto=payload.get("tipo_lotto", "MASSIVO"),
        )
        return JsonResponse({"lotto_id": lotto_id, "status": "ok"})
    except ValueError:
        return JsonResponse({"error": "invalid_payload"}, status=400)
    except PipelineError as exc:
        return JsonResponse({"error": "pipeline_error", "detail": str(exc)}, status=400)
