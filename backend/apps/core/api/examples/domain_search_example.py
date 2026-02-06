# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Esempio API search con throttling, min length e paginazione.
# ------------------------------------------------------------
from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.pagination import StandardPageNumberPagination
from apps.core.api.search_validators import require_min_search_length
from apps.core.api.success_responses import success_response

# Esempio search API (GET) con throttling + validazione min length.


class ExampleSearchEndpoint(APIView):
    is_search_endpoint = True

    def get(self, request: Request) -> Response:
        term = request.query_params.get("term")
        require_min_search_length(term, min_length=3, field_name="term")

        # Placeholder: sostituire con query reale/paginata.
        results = [
            {"id": 1, "label": "Esempio A"},
            {"id": 2, "label": "Esempio B"},
        ]
        # PageNumber per liste piccole/medie; per grandi volumi usare CursorPagination.
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(results, request)
        page_items = page if page is not None else results
        return success_response(
            {
                "items": page_items,
                "total": len(results),
                "page_size": paginator.get_page_size(request),
            }
        )
