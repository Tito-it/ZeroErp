# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service edizioni workflow versionate: lista + drift (Slice 1a),
#        azioni ciclo di vita fork/nuova-versione/pubblica (Slice 1b) e dettaglio
#        + editing strutturale della BOZZA (Slice 2). Le fn/guard DB restano l'unica
#        sede di logica di dominio; qui: guard di bordo, ownership e mapping degli
#        errori DB noti in ServiceError parlanti.
# ------------------------------------------------------------
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.definizioni_repository import STEP_CORE_FIELDS, DefinizioniRepository
from apps.pratiche.services.pratiche_service import _raise_known_db_error

_DRIFT_KEYS = ("versioni_indietro", "preset_corrente_id", "versione_preset_corrente")


# Scopo: mappa i DatabaseError noti (marker in pratiche_service) in ServiceError
# parlanti. Sostituisce il try/except ripetuto: `_raise_known_db_error` solleva
# sempre (marker → ServiceError, altrimenti ri-alza l'originale), quindi il corpo
# del `with` che fallisce non prosegue mai.
@contextmanager
def _mapped_db_errors(function_name: str) -> Iterator[None]:
    try:
        yield
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name=function_name)
        raise  # irraggiungibile: _raise_known_db_error solleva sempre


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


# Scopo: dettaglio editing di un'edizione (Slice 2 anello 1): header con drift
# annidato (mirror del contratto lista) + steps ordinati. 404 se l'id non esiste.
# Read-only: gli anelli di scrittura (step/figli/archi) arrivano dopo, sempre come
# wrapper sottili sulle fn/guard DB (nessuna logica di dominio qui).
def get_definizione_dettaglio(definizione_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    repo = DefinizioniRepository()
    header = repo.get_definizione(definizione_id)
    ErrorManager.require(
        header is not None,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Definizione workflow {definizione_id} non trovata",
    )
    header["drift"] = {k: header.pop(k, None) for k in _DRIFT_KEYS}
    steps = repo.list_steps_definizione(definizione_id)

    # Anello 2 — figli per-nodo annidati sotto lo step, archi al livello edizione.
    # Un giro di query per tipo (no N+1); raggruppo per template_flusso_id in Python.
    by_step = {s["id"]: s for s in steps}
    for s in steps:
        s["canali"] = []
        s["handler_eventi"] = []
        s["competenze"] = []
    for child_key, rows in (
        ("canali", repo.list_canali_definizione(definizione_id)),
        ("handler_eventi", repo.list_handler_eventi_definizione(definizione_id)),
        ("competenze", repo.list_competenze_definizione(definizione_id)),
    ):
        for r in rows:
            step = by_step.get(r.pop("template_flusso_id"))
            if step is not None:
                step[child_key].append(r)

    archi = {
        "prerequisiti": repo.list_prerequisiti_definizione(definizione_id),
        "formule_tempo": repo.list_formule_tempo_definizione(definizione_id),
        "regole_generazione": repo.list_regole_generazione_definizione(definizione_id),
    }
    return {"definizione": header, "steps": steps, "archi": archi}


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
    with _mapped_db_errors("definizioni_service.fork_definizione"):
        nuovo_id = DefinizioniRepository().fork_definizione(definizione_id, emittente_fiscale_id)
    return {"definizione_id": nuovo_id}


# Scopo: crea una nuova versione BOZZA dello stesso scope della definizione.
def nuova_versione_definizione(definizione_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    with _mapped_db_errors("definizioni_service.nuova_versione_definizione"):
        nuovo_id = DefinizioniRepository().nuova_versione_definizione(definizione_id)
    return {"definizione_id": nuovo_id}


# Scopo: pubblica una BOZZA (→ PUBBLICATA; la precedente dello scope → RITIRATA).
def pubblica_definizione(definizione_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    with _mapped_db_errors("definizioni_service.pubblica_definizione"):
        pubblicata_id = DefinizioniRepository().pubblica_definizione(definizione_id)
    return {"definizione_id": pubblicata_id}


# --- Write step su BOZZA (Slice 2 anello 3) ----------------------------------
# Campi core (STEP_CORE_FIELDS, condivisi col repository) editabili in questo giro;
# handler/azione_ui/chiude_pratica/ripetibilita arrivano dopo. L'immutabilita'
# (edizione per-emittente emessa) è enforce dai guard DB (marker
# TEMPLATE_DEFINIZIONE_CONGELATA); qui solo validazione di bordo + ownership.
_STEP_STR_FIELDS = ("codice", "descrizione", "direzione", "modalita_esito", "esito_default")


# Scopo: estrae dal payload i soli campi core noti, normalizzando le stringhe
# (trim; vuoto → None). Non decide default né valida gli enum: quelli sono dei
# CHECK/DEFAULT DB (una sola verità).
def _clean_step_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for k in STEP_CORE_FIELDS:
        if k not in payload:
            continue
        v = payload[k]
        if k in _STEP_STR_FIELDS and v is not None:
            v = str(v).strip() or None
        data[k] = v
    return data


# Scopo: crea uno step nella BOZZA. 404 se la definizione non esiste; DatabaseError
# (immutabilità/unique codice) → marker parlante.
def create_step(definizione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    repo = DefinizioniRepository()
    header = repo.get_definizione(definizione_id)
    ErrorManager.require(
        header is not None,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Definizione workflow {definizione_id} non trovata",
    )
    data = _clean_step_payload(payload)
    ErrorManager.require(
        bool(data.get("codice")) and bool(data.get("descrizione")),
        code="E_VALIDATION_INPUT",
        message="codice e descrizione sono obbligatori per creare uno step",
    )
    with _mapped_db_errors("definizioni_service.create_step"):
        step_id = repo.create_step(definizione_id, header["tipo_prestazione_id"], data)
    return {"step_id": step_id}


# Scopo: aggiorna i campi core di uno step della BOZZA. 404 se lo step non è nello
# scope della definizione; DatabaseError (immutabilità/unique) → marker parlante.
def update_step(definizione_id: int, step_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(step_id, "step_id")
    data = _clean_step_payload(payload)
    ErrorManager.require(
        bool(data),
        code="E_VALIDATION_INPUT",
        message="nessun campo aggiornabile nel payload",
    )
    with _mapped_db_errors("definizioni_service.update_step"):
        n = DefinizioniRepository().update_step(definizione_id, step_id, data)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Step {step_id} non trovato nella definizione {definizione_id}",
    )
    return {"step_id": step_id}


# Scopo: hard DELETE di uno step della BOZZA. 404 se non nello scope; DatabaseError
# (immutabilità su edizione emessa) → marker parlante.
def delete_step(definizione_id: int, step_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(step_id, "step_id")
    with _mapped_db_errors("definizioni_service.delete_step"):
        n = DefinizioniRepository().delete_step(definizione_id, step_id)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Step {step_id} non trovato nella definizione {definizione_id}",
    )
    return {"deleted": True}
