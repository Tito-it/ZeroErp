import json
from datetime import date

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.services.error_translator import ErrorTranslator
from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


@require_POST
def run_lotto_pipeline(request: HttpRequest) -> JsonResponse:
    # Accetta solo payload JSON per rendere la validazione deterministica.
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
        # Errore tipico: parsing data o coercizione payload.
        return JsonResponse({"error": "invalid_payload"}, status=400)
    except Exception as exc:
        api_error = ErrorTranslator.to_api_error(exc)
        status_code = ErrorTranslator.get_http_status(api_error)
        return JsonResponse({"error": api_error.to_dict()}, status=status_code)
