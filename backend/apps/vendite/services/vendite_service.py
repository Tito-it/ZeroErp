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
from apps.core.services.list_helpers import validate_pagination
from apps.vendite.db.vendite_repository import (
    DASH_FATTURAZIONE_AREE,
    DASH_FATTURAZIONE_AREE_EURO,
    VenditeRepository,
)
from apps.vendite.types import (
    DashFatturazioneAreaRow,
    DashFatturazioneFermoRow,
    LottoFattureRow,
    LottoListRow,
)

_SORT_BY_VALIDI: frozenset[str] = frozenset({"fattura_id", "nominativo", "totale_doc"})
_SORT_DIR_VALIDI: frozenset[str] = frozenset({"asc", "desc"})


# Scopo: Valida page/page_size con E_VENDITE_VALIDATION e restituisce l'offset calcolato.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _validate_pagination(page: int, page_size: int, function_name: str) -> int:
    return validate_pagination(
        page, page_size, error_code="E_VENDITE_VALIDATION", function_name=function_name,
    )


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


# Range anni ammesso per la dashboard fatturazione (brief §6: anno libero
# validato con range sensato).
_DASH_ANNO_MIN = 2000
_DASH_ANNO_MAX = 2100


# Scopo: Restituisce la matrice della dashboard fatturazione per un anno:
#        12 mesi SEMPRE presenti (D-5), ognuno con le 5 aree del funnel in
#        ordine fisso. I mesi/aree senza dati arrivano con zeri; per le aree
#        in euro il valore assente e' "0", per le aree a conteggi resta None
#        (D-2/D-3: OFFERTE e CONTRATTI senza valore monetario in v1).
# Perimetro: sola lettura; la RLS emittente filtra via vista invoker.
# Risultato: dict {anno, mesi: [{competenza_mese, aree: [...] x5}] x12}.
def fn_dash_fatturazione_mensile(
    *,
    anno: int,
) -> dict[str, object]:
    ErrorManager.require(
        _DASH_ANNO_MIN <= anno <= _DASH_ANNO_MAX,
        code="E_VENDITE_VALIDATION",
        message="Parametro anno fuori range.",
        detail=f"Valori ammessi: {_DASH_ANNO_MIN}-{_DASH_ANNO_MAX}",
        context={"anno": anno},
        function_name="vendite.vendite_service.fn_dash_fatturazione_mensile",
    )
    repository = VenditeRepository()
    rows = repository.list_dash_fatturazione_mensile(anno=anno)
    by_key = {(r["competenza_mese"], r["area"]): r for r in rows}

    mesi: list[dict[str, object]] = []
    for mese_num in range(1, 13):
        competenza = date(anno, mese_num, 1).isoformat()
        aree: list[DashFatturazioneAreaRow] = []
        for area in DASH_FATTURAZIONE_AREE:
            r = by_key.get((competenza, area))
            is_euro = area in DASH_FATTURAZIONE_AREE_EURO
            valore_totale = r["valore_totale"] if r else None
            valore_transitato = r["valore_transitato"] if r else None
            aree.append(
                {
                    "area": area,
                    # Aree euro: zero esplicito quando il mese e' vuoto, cosi'
                    # il FE non distingue "mese vuoto" da "totale zero".
                    "valore_totale": (valore_totale or "0") if is_euro else None,
                    "valore_transitato": (valore_transitato or "0") if is_euro else None,
                    "n_documenti": r["n_documenti"] if r else 0,
                    "n_transitati": r["n_transitati"] if r else 0,
                    "n_fermi": r["n_fermi"] if r else 0,
                    "n_abortiti": r["n_abortiti"] if r else 0,
                }
            )
        mesi.append({"competenza_mese": competenza, "aree": aree})
    return {"anno": anno, "mesi": mesi}


# Scopo: Restituisce il drill-down paginato degli elementi fermi di un'area
#        in un mese di competenza (dashboard fatturazione). La competenza
#        viene normalizzata al 1° del mese (bucket mensile).
# Perimetro: sola lettura; lo scope emittente e' interamente DB-side (RLS per
#        le aree documento, filtro GUC nel resolver commesse dal 20260703-60):
#        nessun parametro scope applicativo.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_fatturazione_fermi(
    *,
    competenza_mese: date,
    area: str,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    ErrorManager.require(
        area in DASH_FATTURAZIONE_AREE,
        code="E_VENDITE_VALIDATION",
        message="Parametro area non valido.",
        detail=f"Valori ammessi: {', '.join(DASH_FATTURAZIONE_AREE)}",
        context={"area": area},
        function_name="vendite.vendite_service.fn_dash_fatturazione_fermi",
    )
    offset = _validate_pagination(
        page, page_size, "vendite.vendite_service.fn_dash_fatturazione_fermi"
    )
    repository = VenditeRepository()
    results: list[DashFatturazioneFermoRow]
    results, total_count = repository.list_dash_fatturazione_fermi(
        area=area,
        competenza_mese=competenza_mese.replace(day=1),
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)
