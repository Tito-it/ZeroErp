from typing import Any
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_bool
from apps.core.api.request_parsers import parse_iso_date

# Template riusabile per future API dominio (POST JSON + error envelope standard).


# Scopo: Gestisce `example_domain_endpoint` nel flusso applicativo del modulo.
@require_POST
def example_domain_endpoint(request: HttpRequest) -> JsonResponse:
    # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
    def _handler(payload: dict[str, Any]) -> dict[str, Any]:
        # Esempio campi tipici da payload.
        competenza_mese = parse_iso_date(payload.get("competenza_mese"))
        # ⛔ Mai `bool(payload.get(...))`: `bool("false")` e' True.
        dry_run = optional_bool(payload, "dry_run", default=False)

        # Qui invocare un service dominio reale, es:
        # result_id = domain_service.run_operation(...)
        result_id = 1

        return {
            "id": result_id,
            "competenza_mese": None if competenza_mese is None else competenza_mese.isoformat(),
            "dry_run": dry_run,
            "status": "ok",
        }

    return handle_post_json(request, handler=_handler)
