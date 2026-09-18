# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i due service di `magazzino` condividono — il codice di
#        validazione del dominio, l'involucro paginato offset-based, la
#        validazione dell'ordinamento e la lettura di un `articolo_id`.
# Note: Stampo `pagamenti/services/_helpers.py`: materiale INTERNO del
#       dominio, non un building block di progetto. Nato il 2026-09-18 alla
#       seconda occorrenza — `_risposta` era scritto in entrambi i service e
#       il blocco `validate_order_params(order_by, order_dir.lower() …)` era
#       ripetuto SETTE volte fra i due, con la stessa forma.
#
#       ⚠️ `articolo_id` viaggia come UUID in `%s::uuid` dentro le SQL del
#       repository: un valore che non e' un UUID («abc», stringa vuota) non
#       darebbe un 400 ma un `DataError` di PostgreSQL, cioe' un 500 su un
#       parametro che il contratto dichiara ammesso
#       (`feedback_contratto_dichiarato_provalo_intero`). Si legge QUI, una
#       volta, con il validator del dominio.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import PayloadValidator

_FN = "magazzino.helpers"

# Il codice di validazione del payload. ⚠️ Quello GENERICO (`DATO_ERRATO`,
# `highlight_form_fields`): il dominio non ha ancora il suo — e' un seed del
# team DB (`E_MAGAZZINO_VALIDATION`, come `E_PAGAMENTI_VALIDATION`), chiesto
# nel brief 2-bis. Cambiarlo e' una riga qui.
E_VALIDAZIONE = "E_VALIDATION_INPUT"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)


# Scopo: L'involucro paginato offset-based `{count, results}` — la lingua di
#        `useSearchTable` e delle liste nate su `<ListaConfigurabile>`.
def risposta_paginata(results: list[Any], total: int) -> dict[str, Any]:
    return {"count": total, "results": results}


# Scopo: Valida `order_by`/`order_dir` di una lista contro la whitelist del
#        repository. `nullable=True`: «non specificato» e' legittimo e l'ordine
#        lo decide il repository; fuori whitelist e' un 400 col campo.
# ⚠️ `order_dir` arriva GREZZO dalla query string (api.md §parse_list_params):
#    il BB confronta case-sensitive, quindi qui si normalizza a minuscolo.
def ordinamento_validato(
    order_by: str | None,
    order_dir: str | None,
    *,
    colonne: Mapping[str, str],
    function_name: str,
) -> tuple[str | None, str | None]:
    return validate_order_params(
        order_by,
        order_dir.lower() if order_dir else None,
        allowed_columns=colonne,
        error_code=E_VALIDAZIONE,
        function_name=function_name,
        nullable=True,
    )


# Scopo: Un `articolo_id` letto da query string o da un parametro di firma,
#        come UUID canonico; `None` se assente e non obbligatorio. Un valore
#        che non e' un UUID e' un 400 col campo, non un errore del database.
def articolo_uuid(
    valore: Any, *, obbligatorio: bool, function_name: str
) -> str | None:
    if valore in (None, ""):
        if not obbligatorio:
            return None
        return _PAYLOAD.require_uuid({}, "articolo_id", function_name=function_name)
    return _PAYLOAD.require_uuid(
        {"articolo_id": valore}, "articolo_id", function_name=function_name,
    )
