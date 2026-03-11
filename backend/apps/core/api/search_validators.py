from __future__ import annotations

from apps.core.services.service_errors import ServiceError

# Helper DRF: validazione search per evitare query troppo generiche.


# Scopo: Valida il requisito `min_search_length` e solleva errore in caso di violazione.
def require_min_search_length(term: str | None, *, min_length: int = 3, field_name: str = "term") -> None:
    if term is None:
        return
    if len(term.strip()) >= min_length:
        return
    raise ServiceError(
        code="E_SEARCH_VALIDATION",
        message="Parametri ricerca non validi.",
        detail=f"{field_name} troppo corto (min {min_length}).",
    )
