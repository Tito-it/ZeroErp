# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service edizioni workflow versionate (Fase 2 Slice 1a): lista
#        + drift per la UI admin. Read-only. Le azioni fork/nuova-versione/
#        pubblica arrivano in lockstep con la conversione DEFINER delle fn
#        DB (brief-db-accesso-be-definizioni-workflow.md §P1).
# ------------------------------------------------------------
from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.definizioni_repository import DefinizioniRepository
from apps.pratiche.services.pratiche_service import _raise_known_db_error

_DRIFT_KEYS = ("versioni_indietro", "preset_corrente_id", "versione_preset_corrente")


# Scopo: elenco edizioni per (tipo [, emittente]) con drift annidato. Il drift e'
# NULL per i preset (nessun fork → vista drift vuota); lo si restituisce come
# oggetto esplicito `drift` invece di campi sparsi (mirror del contratto FE).
def list_definizioni(
    *,
    tipo_prestazione_id: int | None = None,
    emittente_fiscale_id: int | None = None,
) -> list[dict[str, Any]]:
    rows = DefinizioniRepository().list_definizioni(
        tipo_prestazione_id=tipo_prestazione_id,
        emittente_fiscale_id=emittente_fiscale_id,
    )
    for r in rows:
        r["drift"] = {k: r.pop(k, None) for k in _DRIFT_KEYS}
    return rows


# --- Azioni ciclo di vita (Slice 1b) -----------------------------------------
# Wrapper sottili sulle fn DB: nessuna logica/validazione di dominio qui (vive
# nelle fn). Solo guard di bordo sugli id + traduzione DatabaseError → ServiceError
# parlante (marker in pratiche_service._KNOWN_DB_ERROR_MARKERS: DEFINIZIONE_*).
# Co-requisito lockstep: le fn devono essere SECURITY DEFINER perché la DML interna
# passi col ruolo web (brief-db-accesso-be-definizioni-workflow §P1); finché sono
# INVOKER queste azioni restituiscono E_DATABASE (permesso negato).

def _require_id(value: int, nome: str) -> None:
    ErrorManager.require(
        value is not None and value > 0,
        code="E_INVALID_ID",
        message=f"{nome} obbligatorio e > 0",
    )


# Scopo: crea l'edizione BOZZA di un emittente da una definizione (fork con provenance).
def fork_definizione(definizione_id: int, emittente_fiscale_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(emittente_fiscale_id, "emittente_fiscale_id")
    try:
        nuovo_id = DefinizioniRepository().fork_definizione(definizione_id, emittente_fiscale_id)
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="definizioni_service.fork_definizione")
        raise  # irraggiungibile
    return {"definizione_id": nuovo_id}


# Scopo: crea una nuova versione BOZZA dello stesso scope della definizione.
def nuova_versione_definizione(definizione_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    try:
        nuovo_id = DefinizioniRepository().nuova_versione_definizione(definizione_id)
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="definizioni_service.nuova_versione_definizione")
        raise  # irraggiungibile
    return {"definizione_id": nuovo_id}


# Scopo: pubblica una BOZZA (→ PUBBLICATA; la precedente dello scope → RITIRATA).
def pubblica_definizione(definizione_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    try:
        pubblicata_id = DefinizioniRepository().pubblica_definizione(definizione_id)
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="definizioni_service.pubblica_definizione")
        raise  # irraggiungibile
    return {"definizione_id": pubblicata_id}
