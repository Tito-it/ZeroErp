from __future__ import annotations

from rest_framework.pagination import CursorPagination, PageNumberPagination

# Helper DRF: paginazione standard per liste API.


class StandardPageNumberPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 200
    page_size_query_param = "page_size"


class StandardCursorPagination(CursorPagination):
    page_size = 50
    max_page_size = 200
    ordering = "-data_update"
