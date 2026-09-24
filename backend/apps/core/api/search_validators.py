from __future__ import annotations

from apps.core.db._helpers import RICERCA_MIN_CARATTERI
from apps.core.services.service_errors import ServiceError

# Helper DRF: validazione search per evitare query troppo generiche.

# Colonne ammesse per l'ordinamento nella ricerca universale.
# La whitelist e' duplicata nel DB (fn_search_soggetti_universale),
# qui serve solo per dare un errore 400 immediato senza round-trip.
ALLOWED_ORDER_COLUMNS = frozenset({
    "ragione_sociale_completa",
    "soggetto_codice",
    "id_fiscale_univoco",
    "utility_list",
})

ALLOWED_ORDER_DIRS = frozenset({"ASC", "DESC"})


# Scopo: Valida il requisito `min_search_length` e solleva errore in caso di violazione.
# ⭐ Default = `RICERCA_MIN_CARATTERI`, la soglia del BB `add_ricerca_full_condition`
#    (2026-09-24): il 400 della view e il «non filtra» del repository non devono
#    poter parlare di due soglie diverse. Fino ad allora qui c'era un 3 scritto
#    a mano, seconda sede dello stesso numero.
# ⭐ `context={"field": …}`: la convenzione degli errori Python (api.md
#    §Tassonomia errori), cosi' il 400 nomina il campo come ogni altro.
def require_min_search_length(
    term: str | None, *, min_length: int = RICERCA_MIN_CARATTERI, field_name: str = "term",
) -> None:
    if term is None:
        return
    if len(term.strip()) >= min_length:
        return
    raise ServiceError(
        code="E_SEARCH_VALIDATION",
        message="Parametri ricerca non validi.",
        detail=f"{field_name} troppo corto (min {min_length}).",
        context={"field": field_name},
    )


# Scopo: Valida order_by contro la whitelist e order_dir in ASC/DESC.
# Ritorna la coppia normalizzata (order_by, order_dir) o (None, None) se non specificati.
def validate_order_params(
    order_by: str | None, order_dir: str | None
) -> tuple[str | None, str | None]:
    if not order_by:
        return None, None

    if order_by not in ALLOWED_ORDER_COLUMNS:
        raise ServiceError(
            code="E_SEARCH_VALIDATION",
            message="Parametri ordinamento non validi.",
            detail=f"order_by='{order_by}' non e' una colonna ammessa. "
                   f"Valori consentiti: {', '.join(sorted(ALLOWED_ORDER_COLUMNS))}.",
        )

    normalized_dir = (order_dir or "ASC").upper()
    if normalized_dir not in ALLOWED_ORDER_DIRS:
        raise ServiceError(
            code="E_SEARCH_VALIDATION",
            message="Parametri ordinamento non validi.",
            detail=f"order_dir='{order_dir}' non valido. Valori consentiti: ASC, DESC.",
        )

    return order_by, normalized_dir
