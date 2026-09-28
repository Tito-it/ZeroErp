from __future__ import annotations

from rest_framework.pagination import CursorPagination, PageNumberPagination

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

# Helper DRF: paginazione standard per liste API.


class StandardPageNumberPagination(PageNumberPagination):
    page_size = DEFAULT_LIMIT
    max_page_size = MAX_LIMIT
    page_size_query_param = "page_size"


class StandardCursorPagination(CursorPagination):
    page_size = DEFAULT_LIMIT
    max_page_size = MAX_LIMIT
    ordering = "-data_update"
