from django.http import JsonResponse

from apps.core.services.error_translator import ErrorTranslator

# Helper condivisi API: envelope errori uniforme per tutti i domini.


def invalid_json_response() -> JsonResponse:
    return JsonResponse({"error": "invalid_json"}, status=400)


def invalid_payload_response() -> JsonResponse:
    return JsonResponse({"error": "invalid_payload"}, status=400)


def exception_to_error_response(exc: Exception) -> JsonResponse:
    api_error = ErrorTranslator.to_api_error(exc)
    status_code = ErrorTranslator.get_http_status(api_error)
    return JsonResponse({"error": api_error.to_dict()}, status=status_code)
