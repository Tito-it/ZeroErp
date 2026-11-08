# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La CONSULTAZIONE del magazzino — la disponibilita' (per magazzino e
#        per articolo, con i blocchi che la spiegano) e il registro dei
#        movimenti. Sola lettura per costruzione: si scrive solo dalla porta.
# Note: ⚠️ Le viste sono `security_invoker`: si leggono CON la connessione
#       dell'utente, mai da un canale di sistema (il repository lo presidia).
#       La disponibilita' e' la FORMULA IN COLONNE del DB (`giacenza +
#       bloccata`, con `bloccata` negativa): qui non si somma niente.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.magazzino.db.famiglie import FAMIGLIE
from apps.magazzino.db.magazzino_repository import (
    DISPONIBILITA_ARTICOLI_SORT_COLUMNS,
    DISPONIBILITA_SORT_COLUMNS,
    MOVIMENTI_SORT_COLUMNS,
    MagazzinoRepository,
)
from apps.magazzino.services._helpers import (
    E_VALIDAZIONE,
    articolo_uuid,
    ordinamento_validato,
    risposta_paginata as _risposta,
)

_FN = "magazzino.consultazione_service"
_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)


# Scopo: La disponibilita' per (articolo, magazzino) — lista `magazzino.disponibilita`.
def list_disponibilita(
    *,
    auth_user_id: int | None,
    articolo_id: str | None = None,
    magazzino_id: int | None = None,
    solo_negativa: bool = False,
    solo_con_giacenza: bool = False,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=DISPONIBILITA_SORT_COLUMNS,
        function_name=f"{_FN}.list_disponibilita",
    )
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=False, function_name=f"{_FN}.list_disponibilita",
    )
    results, total = MagazzinoRepository().list_disponibilita(
        auth_user_id=auth_user_id,
        articolo_id=articolo_id,
        magazzino_id=magazzino_id,
        solo_negativa=bool(solo_negativa),
        solo_con_giacenza=bool(solo_con_giacenza),
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _risposta(results, total)


# Scopo: La disponibilita' per articolo, somma sui magazzini visibili —
#        lista `magazzino.disponibilita_articoli`.
def list_disponibilita_articoli(
    *,
    articolo_id: str | None = None,
    solo_negativa: bool = False,
    solo_con_giacenza: bool = False,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=DISPONIBILITA_ARTICOLI_SORT_COLUMNS,
        function_name=f"{_FN}.list_disponibilita_articoli",
    )
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=False, function_name=f"{_FN}.list_disponibilita_articoli",
    )
    results, total = MagazzinoRepository().list_disponibilita_articoli(
        articolo_id=articolo_id,
        solo_negativa=bool(solo_negativa),
        solo_con_giacenza=bool(solo_con_giacenza),
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _risposta(results, total)


# Scopo: I blocchi su (articolo, magazzino): il drill-down di `n_blocchi`.
def list_blocchi(*, articolo_id: str, magazzino_id: int) -> dict[str, Any]:
    _PAYLOAD.guard_positive_int(magazzino_id, field="magazzino_id")
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=True, function_name=f"{_FN}.list_blocchi",
    )
    return {"results": MagazzinoRepository().list_blocchi(
        articolo_id=articolo_id, magazzino_id=magazzino_id,
    )}


# Scopo: Il registro dei movimenti — lista `magazzino.movimenti`.
# ⭐ `inventario_id` / `rettifica_id`: i movimenti di QUEL documento (il
#    deep-link dal documento `POSTED`). Uno solo dei due.
def list_movimenti(
    *,
    auth_user_id: int | None,
    magazzino_id: int | None = None,
    articolo_id: str | None = None,
    causale_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    sorgente_codice_interno: str | None = None,
    inventario_id: int | None = None,
    rettifica_id: int | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=MOVIMENTI_SORT_COLUMNS,
        function_name=f"{_FN}.list_movimenti",
    )
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=False, function_name=f"{_FN}.list_movimenti",
    )
    ErrorManager.require(
        inventario_id is None or rettifica_id is None,
        code=E_VALIDAZIONE,
        message="Indicare un solo documento sorgente (inventario o rettifica).",
        context={"parametro": "inventario_id"},
        function_name=f"{_FN}.list_movimenti",
    )
    documento_sorgente = None
    if inventario_id is not None:
        documento_sorgente = (FAMIGLIE["inventari"], inventario_id)
    elif rettifica_id is not None:
        documento_sorgente = (FAMIGLIE["rettifiche"], rettifica_id)

    results, total = MagazzinoRepository().list_movimenti(
        auth_user_id=auth_user_id,
        magazzino_id=magazzino_id,
        articolo_id=articolo_id,
        causale_id=causale_id,
        data_da=data_da,
        data_a=data_a,
        sorgente_codice_interno=sorgente_codice_interno,
        documento_sorgente=documento_sorgente,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _risposta(results, total)
