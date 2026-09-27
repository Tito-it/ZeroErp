import json
from datetime import date
from typing import Any

from django.http import HttpRequest
from rest_framework.exceptions import ParseError
from rest_framework.request import Request

# Helper condivisi API: parsing body/date con comportamento uniforme tra domini.


# Scopo: Effettua il parsing di `json_body` con validazione input.
def parse_json_body(request: HttpRequest | Request) -> dict[str, Any]:
    # Supporta sia Django HttpRequest sia DRF Request durante migrazione uniforme API.
    try:
        if isinstance(request, Request):
            value = request.data
        else:
            raw_body = request.body.decode("utf-8") or "{}"
            value = json.loads(raw_body)
    except (json.JSONDecodeError, ParseError) as exc:
        raise ValueError("invalid_json") from exc

    return oggetto_json(value)


# Scopo: ⭐ La regola «il corpo e' un OGGETTO JSON», in un posto solo: la usano
#        `parse_json_body` (per `handle_post_json`) e `corpo_oggetto` (per le
#        view DRF che leggono `request.data`). Un form (`QueryDict`) e' un dict.
def oggetto_json(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("invalid_payload")
    return value


# Scopo: Effettua il parsing di `iso_date` con validazione input.
def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)
