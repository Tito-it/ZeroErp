# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from typing import Any, Literal, overload

from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import PayloadValidator

_FN = "magazzino.helpers"

# Il codice di validazione del payload del dominio (`DATO_ERRATO`,
# `highlight_form_fields`), gemello di `E_PAGAMENTI_VALIDATION`. ⭐ A catalogo
# dal 2026-09-23 (R-6 del brief 2-bis): fino a quel giorno il magazzino usava
# il generico `E_VALIDATION_INPUT`, e nel registro degli errori i suoi rifiuti
# non si distinguevano da quelli di ogni altro dominio.
# ⚠️ La frase a catalogo e' SENZA segnaposto, come quella dei diciotto
# fratelli `*_VALIDATION`: a riempire un `%s` e' `fn_log_and_raise_error`, e un
# codice che solleva solo il BACKEND da li' non ci passa mai. Quale campo non
# va lo dice il `ServiceError` (`context.field`), non la frase.
E_VALIDAZIONE = "E_MAGAZZINO_VALIDATION"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)


# Scopo: L'involucro paginato offset-based `{count, results}` — la lingua di
#        `useSearchTable` e delle liste nate su `<ListaConfigurabile>`.
def risposta_paginata(results: list[Any], total: int) -> dict[str, Any]:
    return {"count": total, "results": results}


# Scopo: Valida `order_by`/`order_dir` di una lista contro la whitelist del
#        repository. `nullable=True`: «non specificato» e' legittimo e l'ordine
#        lo decide il repository; fuori whitelist e' un 400 col campo.
# ⭐ `order_dir` arriva GREZZO dalla query string (api.md §parse_list_params)
#    e passa grezzo: dal 2026-09-26 il BB lo giudica con `order_dir_ammessa`
#    (maiuscole e spazi ammessi) e lo ritorna normalizzato.
def ordinamento_validato(
    order_by: str | None,
    order_dir: str | None,
    *,
    colonne: Mapping[str, str],
    function_name: str,
) -> tuple[str | None, str | None]:
    return validate_order_params(
        order_by,
        order_dir,
        allowed_columns=colonne,
        error_code=E_VALIDAZIONE,
        function_name=function_name,
        nullable=True,
    )


# Scopo: Un `articolo_id` letto da query string o da un parametro di firma,
#        come UUID canonico; `None` se assente e non obbligatorio. Un valore
#        che non e' un UUID e' un 400 col campo, non un errore del database.
@overload
def articolo_uuid(
    valore: Any, *, obbligatorio: Literal[True], function_name: str
) -> str: ...
@overload
def articolo_uuid(
    valore: Any, *, obbligatorio: bool, function_name: str
) -> str | None: ...
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
