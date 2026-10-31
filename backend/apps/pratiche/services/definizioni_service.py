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

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.service_errors import E_VALIDATION_INPUT
from apps.pratiche.db.definizioni_repository import (
    CHILD_SPECS,
    DEFINIZIONI_ORDER_COLUMNS,
    EDGE_SPECS,
    STEP_CORE_FIELDS,
    DefinizioniRepository,
)
from apps.pratiche.services.pratiche_service import _raise_known_db_error

_V = PayloadValidator(validation_code=E_VALIDATION_INPUT)

_DRIFT_KEYS = ("versioni_indietro", "preset_corrente_id", "versione_preset_corrente")
_DEFINIZIONI_ORDER_BY_VALIDI: frozenset[str] = frozenset(DEFINIZIONI_ORDER_COLUMNS)


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


# Scopo: la pagina della lista `pratiche.definizioni_workflow` (dal 2026-10-31,
# brief-db-liste-datatable-grezze-secondo-giro riga 1), con l'ordinamento
# validato sulla whitelist del repository. ⚠️ Il drift resta in colonne PIATTE
# (`versioni_indietro`, ...): sono i `campo_sorgente` del catalogo. Il dettaglio
# lo annida ancora in `drift` per l'editor.
def list_definizioni(
    *,
    tipo_prestazione_id: int | None = None,
    emittente_fiscale_id: int | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    if order_by:
        order_by, order_dir = validate_order_params(
            order_by, order_dir,
            allowed_columns=_DEFINIZIONI_ORDER_BY_VALIDI,
            error_code="E_VALIDATION_INPUT",
            nullable=True,
            function_name="pratiche.definizioni_service.list_definizioni",
        )
    return DefinizioniRepository().list_definizioni(
        tipo_prestazione_id=tipo_prestazione_id,
        emittente_fiscale_id=emittente_fiscale_id,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


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
    assert header is not None
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


# Scopo: estrae dal payload i soli campi in `fields`, trimmando le stringhe (vuoto
# → None). Cleaner condiviso da step/figli/archi. Non decide default né valida
# enum/FK: sono constraint DB (una sola verità).
# ⛔ Dal 2026-09-26 una chiave fuori `fields` è un 400 `E_VALIDATION_INPUT`, non
#    più uno scarto silenzioso: un PATCH che «riesce» senza aver scritto il campo
#    è il difetto che non dà errore (e il repository, dietro, è RIGIDO:
#    RuntimeError). I form dell'editor (DefinizioneStepForm, Step*Tab, Archi*Tab)
#    mandano solo chiavi scrivibili — verificato quel giorno.
def _clean_writable(fields: tuple[str, ...], payload: dict[str, Any]) -> dict[str, Any]:
    _V.validate_allowed_keys(
        payload, allowed=frozenset(fields), message="Campi non modificabili nel payload.",
    )
    data: dict[str, Any] = {}
    for k in fields:
        if k not in payload:
            continue
        v = payload[k]
        if isinstance(v, str):
            v = v.strip() or None
        data[k] = v
    return data


# Scopo: guard di bordo — ogni campo `required` deve essere presente e non vuoto
# in `data` (400 parlante prima del NOT NULL DB). Condiviso figli/archi.
def _require_fields(data: dict[str, Any], required: tuple[str, ...], kind: str) -> None:
    for campo in required:
        ErrorManager.require(
            data.get(campo) not in (None, ""),
            code=E_VALIDATION_INPUT,
            message=f"campo '{campo}' obbligatorio per {kind}",
        )


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
    assert header is not None
    data = _clean_writable(STEP_CORE_FIELDS, payload)
    ErrorManager.require(
        bool(data.get("codice")) and bool(data.get("descrizione")),
        code=E_VALIDATION_INPUT,
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
    data = _clean_writable(STEP_CORE_FIELDS, payload)
    _V.require_campi_da_aggiornare(
        data,
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


# --- Write figli per-nodo su BOZZA (Slice 2 anello 4) ------------------------
# CRUD dei figli (canali/handler_eventi/competenze) parametrizzato da CHILD_SPECS
# (unica fonte col repository). `child_kind` arriva dalla urlconf (allowlist fissa).
# Immutabilità enforce dal guard figli DB (marker TEMPLATE_DEFINIZIONE_CONGELATA).


# Scopo: estrae dal payload le sole colonne scrivibili del figlio (via cleaner condiviso).
def _clean_child_payload(child_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _clean_writable(CHILD_SPECS[child_kind].writable, payload)


# Scopo: crea un figlio sotto uno step della BOZZA. 404 se lo step non è nello
# scope della definizione; campi `required` mancanti → 400; DatabaseError
# (immutabilità) → marker parlante.
def create_step_figlio(
    definizione_id: int, step_id: int, child_kind: str, payload: dict[str, Any],
) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(step_id, "step_id")
    repo = DefinizioniRepository()
    ErrorManager.require(
        repo.step_in_definizione(definizione_id, step_id),
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Step {step_id} non trovato nella definizione {definizione_id}",
    )
    data = _clean_child_payload(child_kind, payload)
    _require_fields(data, CHILD_SPECS[child_kind].required, child_kind)
    with _mapped_db_errors(f"definizioni_service.create_step_figlio.{child_kind}"):
        row_id = repo.create_child(child_kind, step_id, data)
    return {"id": row_id}


# Scopo: aggiorna un figlio (scoping riga→step→definizione). 404 fuori scope.
def update_step_figlio(
    definizione_id: int, step_id: int, child_kind: str, row_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(step_id, "step_id")
    _require_id(row_id, "row_id")
    data = _clean_child_payload(child_kind, payload)
    _V.require_campi_da_aggiornare(
        data,
    )
    with _mapped_db_errors(f"definizioni_service.update_step_figlio.{child_kind}"):
        n = DefinizioniRepository().update_child(
            child_kind, definizione_id, step_id, row_id, data)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"{child_kind} {row_id} non trovato per lo step {step_id}",
    )
    return {"id": row_id}


# Scopo: hard DELETE di un figlio (scoping riga→step→definizione). 404 fuori scope.
def delete_step_figlio(
    definizione_id: int, step_id: int, child_kind: str, row_id: int,
) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(step_id, "step_id")
    _require_id(row_id, "row_id")
    with _mapped_db_errors(f"definizioni_service.delete_step_figlio.{child_kind}"):
        n = DefinizioniRepository().delete_child(child_kind, definizione_id, step_id, row_id)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"{child_kind} {row_id} non trovato per lo step {step_id}",
    )
    return {"deleted": True}


# --- Write archi del grafo su BOZZA (Slice 2 anello 5) -----------------------
# CRUD degli archi (prerequisiti/formule_tempo/regole_generazione) parametrizzato
# da EDGE_SPECS (unica fonte col repository). `edge_kind` dalla urlconf. Gli step
# referenziati devono appartenere alla definizione (in_def_cols); il tipo (dove
# NOT NULL) è auto-derivato dalla definizione. Immutabilità dai guard figli DB.


# Scopo: ogni endpoint step dell'arco PRESENTE in `data` (in_def_cols) deve
# appartenere alla definizione (404 altrimenti). Vale in create E in update: senza
# questo, un PATCH potrebbe ri-puntare un arco a uno step di un'altra edizione (il
# guard DB non lo impedisce: verifica solo che l'edizione corrente sia editabile).
def _valida_endpoint_in_def(definizione_id: int, edge_kind: str, data: dict[str, Any]) -> None:
    repo = DefinizioniRepository()
    for col in EDGE_SPECS[edge_kind].in_def_cols:
        if col not in data:
            continue
        try:
            sid = int(data[col])
        except (TypeError, ValueError):
            sid = None
        ErrorManager.require(
            sid is not None and repo.step_in_definizione(definizione_id, sid),
            code="E_DEFINIZIONE_NOT_FOUND",
            message=f"lo step '{col}'={data[col]} non appartiene alla definizione {definizione_id}",
        )


# Scopo: crea un arco nel grafo della BOZZA. 404 se la definizione o uno step
# endpoint non esiste nello scope; campi required mancanti → 400; immutabilità → marker.
def create_arco(definizione_id: int, edge_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    spec = EDGE_SPECS[edge_kind]
    repo = DefinizioniRepository()
    header = repo.get_definizione(definizione_id)
    ErrorManager.require(
        header is not None,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"Definizione workflow {definizione_id} non trovata",
    )
    assert header is not None
    data = _clean_writable(spec.writable, payload)
    _require_fields(data, spec.required, edge_kind)
    _valida_endpoint_in_def(definizione_id, edge_kind, data)
    if spec.tipo_col:
        data[spec.tipo_col] = header["tipo_prestazione_id"]
    with _mapped_db_errors(f"definizioni_service.create_arco.{edge_kind}"):
        row_id = repo.create_edge(edge_kind, data)
    return {"id": row_id}


# Scopo: aggiorna un arco (solo campi writable), scoping anchor→definizione. 404 fuori
# scope. Se il payload cambia un endpoint step, lo si rivalida in-definizione.
def update_arco(definizione_id: int, edge_kind: str, row_id: int,
                payload: dict[str, Any]) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(row_id, "row_id")
    data = _clean_writable(EDGE_SPECS[edge_kind].writable, payload)
    _V.require_campi_da_aggiornare(
        data,
    )
    _valida_endpoint_in_def(definizione_id, edge_kind, data)
    with _mapped_db_errors(f"definizioni_service.update_arco.{edge_kind}"):
        n = DefinizioniRepository().update_edge(edge_kind, definizione_id, row_id, data)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"{edge_kind} {row_id} non trovato nella definizione {definizione_id}",
    )
    return {"id": row_id}


# Scopo: hard DELETE di un arco, scoping anchor→definizione. 404 fuori scope.
def delete_arco(definizione_id: int, edge_kind: str, row_id: int) -> dict[str, Any]:
    _require_id(definizione_id, "definizione_id")
    _require_id(row_id, "row_id")
    with _mapped_db_errors(f"definizioni_service.delete_arco.{edge_kind}"):
        n = DefinizioniRepository().delete_edge(edge_kind, definizione_id, row_id)
    ErrorManager.require(
        n > 0,
        code="E_DEFINIZIONE_NOT_FOUND",
        message=f"{edge_kind} {row_id} non trovato nella definizione {definizione_id}",
    )
    return {"deleted": True}
