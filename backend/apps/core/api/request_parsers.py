import json
from datetime import date
from typing import Any

from django.http import HttpRequest
from rest_framework.exceptions import ParseError
from rest_framework.request import Request

# Helper condivisi API: parsing body/date con comportamento uniforme tra domini.


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

    if not isinstance(value, dict):
        raise ValueError("invalid_payload")
    return value


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)
