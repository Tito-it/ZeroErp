# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i service di `pagamenti` condividono — il codice di
#        validazione del dominio, la lettura di un importo e l'involucro
#        paginato.
# Note: Nati dentro `pagamenti_service`, spostati qui alla SECONDA occorrenza
#       (il giro delle sistemazioni). ⛔ Non e' un building block di progetto:
#       e' materiale interno di questo dominio, e sta qui perche' importare i
#       nomi privati di un altro modulo (`_decimal_da_payload`) e' un legame
#       che non regge il primo riordino.
# ------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.core.services.error_manager import ErrorManager

_FN = "pagamenti.helpers"

# Codice di validazione del payload di questo dominio. ⭐ Seminato dal team DB
# il 2026-08-25 su richiesta del backend: fino ad allora si usava il generico
# `E_VALIDATION_INPUT`.
# ⚠️ Il nome e' `..._VALIDATION` (come `E_VENDITE_VALIDATION`), non
# `..._VALIDAZIONE`: il catalogo tiene le due forme e questa e' quella scelta.
E_VALIDAZIONE = "E_PAGAMENTI_VALIDATION"

# La fattura indicata non c'e' — o il perimetro non la lascia vedere, e i due
# restano volutamente indistinguibili. ⭐ A catalogo (NON_TROVATO, 404); e'
# il codice che i tre service del dominio sollevano da se' quando leggono un
# documento per id: era scritto in ognuno dei tre, e una stringa ripetuta e'
# gia' divergente il giorno in cui una delle copie cambia.
E_FATTURA_NON_TROVATA = "E_FATTURA_NON_TROVATA"


# Scopo: Rifiuta un valore che non e' un importo, con la stessa frase ovunque.
def rifiuta_importo(raw: Any, key: str, *, condizione: bool) -> None:
    if not condizione:
        return
    ErrorManager.raise_error(
        code=E_VALIDAZIONE,
        message=f"Campo '{key}' non e' un importo valido.",
        detail=f"Valore ricevuto: {raw!r}",
        context={"field": key, key: str(raw)},
        function_name=_FN,
    )


# Scopo: Estrae un importo dal payload come Decimal esatto.
# ⚠️ Passa da `str`: `Decimal(0.1)` porta dentro l'errore del float, e su un
#    importo di denaro quell'errore poi si somma. Il float in ingresso e'
#    ammesso (il JSON non ha decimali) ma si converte sempre dalla sua forma
#    testuale.
def decimal_da_payload(
    payload: dict[str, Any], key: str, *, obbligatorio: bool
) -> Decimal | None:
    raw = payload.get(key)
    if raw is None:
        ErrorManager.require(
            not obbligatorio,
            code=E_VALIDAZIONE,
            message=f"Campo '{key}' obbligatorio.",
            context={"field": key},
            function_name=_FN,
        )
        return None

    # `True` sommerebbe come 1, e un flag scambiato per un importo non lo
    # segnalerebbe nessuno.
    rifiuta_importo(raw, key, condizione=isinstance(raw, bool))

    try:
        valore = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        rifiuta_importo(raw, key, condizione=True)
        raise AssertionError("unreachable")  # pragma: no cover

    # ⚠️ `Decimal("NaN")` e `Decimal("Infinity")` si costruiscono senza
    # protestare, e un JSON puo' portarli. Un importo non finito arriverebbe
    # fino alla colonna numeric, dove ogni somma che lo incontra diventa NaN —
    # e un totale NaN non si vede: si legge come un campo vuoto.
    rifiuta_importo(raw, key, condizione=not valore.is_finite())
    return valore


# Scopo: L'involucro paginato, uguale per tutte le liste del dominio.
def risposta_paginata(
    results: list[Any], total: int, page: int, page_size: int
) -> dict[str, Any]:
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        "results": results,
    }
