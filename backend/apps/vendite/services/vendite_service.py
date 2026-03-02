# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa generica per lo schema vendite (liste, ricerche, stato entita').
# ------------------------------------------------------------

# Contiene operazioni facade generiche sullo schema vendite,
# non legate a un sottodominio specifico (pipeline, reset, ecc.).

import math
from datetime import date

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.types import LottoFattureRow, LottoListRow

_SORT_BY_VALIDI: frozenset[str] = frozenset({"fattura_id", "nominativo", "totale_doc"})
_SORT_DIR_VALIDI: frozenset[str] = frozenset({"asc", "desc"})


# Scopo: Valida page/page_size con E_VENDITE_VALIDATION e restituisce l'offset calcolato.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _validate_pagination(page: int, page_size: int, function_name: str) -> int:
    ErrorManager.require(
        page >= 1,
        code="E_VENDITE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page deve essere >= 1",
        context={"page": page},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= page_size <= 200,
        code="E_VENDITE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page_size deve essere compreso tra 1 e 200",
        context={"page_size": page_size},
        function_name=function_name,
        log_to_db=True,
    )
    return (page - 1) * page_size


# Scopo: Costruisce l'envelope di risposta paginata standard.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _build_list_response(
    results: list,
    total_count: int,
    page: int,
    page_size: int,
) -> dict[str, object]:
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }


# Scopo: Restituisce elenco lotti paginato con decodifica e filtri opzionali.
# Obiettivo: esporre lista generica lotti con validazione paginazione.
# Perimetro: sola lettura; delega query a VenditeRepository.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotti(
    *,
    competenza_mese: date | None = None,
    utility_id: int | None = None,
    stato_lotto: str | None = None,
    area_geografica_id: int | None = None,
    tipo_doc_fiscale_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    auth_user_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    offset = _validate_pagination(page, page_size, "vendite.vendite_service.fn_list_lotti")
    repository = VenditeRepository()
    results: list[LottoListRow]
    results, total_count = repository.list_lotti(
        competenza_mese=competenza_mese,
        utility_id=utility_id,
        stato_lotto=stato_lotto,
        area_geografica_id=area_geografica_id,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        auth_user_id=auth_user_id,
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)


# Scopo: Restituisce elenco fatture di un lotto con decodifiche, filtri e ordinamento opzionali.
# Obiettivo: esporre lista paginata per lotto con validazione parametri.
# Perimetro: sola lettura; delega query a VenditeRepository.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotto_fatture(
    *,
    lotto_id: int,
    stato_esecuzione: str | None = None,
    esclusa: bool | None = None,
    auth_user_id: int | None = None,
    sort_by: str = "fattura_id",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    offset = _validate_pagination(page, page_size, "vendite.vendite_service.fn_list_lotto_fatture")
    ErrorManager.require(
        sort_by in _SORT_BY_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametro sort_by non valido.",
        detail="Valori ammessi: fattura_id, nominativo, totale_doc",
        context={"sort_by": sort_by},
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
        log_to_db=True,
    )
    ErrorManager.require(
        sort_dir in _SORT_DIR_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametro sort_dir non valido.",
        detail="Valori ammessi: asc, desc",
        context={"sort_dir": sort_dir},
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
        log_to_db=True,
    )
    repository = VenditeRepository()
    results: list[LottoFattureRow]
    results, total_count = repository.list_lotto_fatture(
        lotto_id=lotto_id,
        stato_esecuzione=stato_esecuzione,
        esclusa=esclusa,
        auth_user_id=auth_user_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)
