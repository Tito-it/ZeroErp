from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Middleware fase 2: segnala deprecazione delle route API legacy non versionate.


class ApiLegacyDeprecationMiddleware(MiddlewareMixin):
    LEGACY_PREFIXES = ("/api/core/", "/api/vendite/")

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if not getattr(settings, "API_LEGACY_DEPRECATION_HEADERS_ENABLED", True):
            return response
        if not self._is_legacy_path(request.path):
            return response

        response["Deprecation"] = "true"
        response["Warning"] = '299 - "Deprecated API path, migrate to /api/v1/*"'
        response["Link"] = '</api/v1/>; rel="successor-version"'
        response["Sunset"] = getattr(
            settings,
            "API_LEGACY_SUNSET_HEADER",
            "Tue, 30 Jun 2026 23:59:59 GMT",
        )
        return response

    def _is_legacy_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.LEGACY_PREFIXES)
