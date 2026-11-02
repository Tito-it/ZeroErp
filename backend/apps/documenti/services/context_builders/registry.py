# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Registry centrale dei DocumentContextBuilder. Dict
#        CODE -> Builder mantenuto a modulo-level. La registrazione
#        avviene via import esplicito dal modulo concreto del dominio
#        sorgente (es. apps.vendite.services....register_builder()).
#        Pattern coerente con `pipeline_task_registry_impl` di vendite:
#        nessuna magia di auto-discovery, niente signal Django, IDE-grep
#        completo. Vincolo non negoziabile (Decisione 18 + 74): il
#        codice del template_documenti.context_builder_code DEVE
#        risolvere a una entry registrata, altrimenti
#        ServiceError(E_DOCUMENTI_VALIDATION).
# ------------------------------------------------------------

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.core.services.error_manager import ErrorManager

if TYPE_CHECKING:
    from apps.documenti.services.context_builders.base import (
        DocumentContextBuilder,
    )

# Dizionario di whitelist: codice template -> istanza builder.
# Le istanze sono stateless: un singleton per processo e' sufficiente.
_REGISTRY: dict[str, "DocumentContextBuilder"] = {}


# Scopo: Registra una nuova entry nel registry.
#        Chiamato all'import del modulo del builder concreto.
#        Idempotente: una seconda registrazione con lo stesso CODE rimpiazza
#        silenziosamente (utile per test che reinizializzano il registry).
#        ⛔ Un builder senza la forma dei dati (`CONTEXT_VERSION` intero >= 1)
#        non si registra: la forma decide se una versione di template puo'
#        stampare, e una forma assente e' una forma dichiarata da nessuno
#        (brief-db-documenti-versione-contesto-template §8.1).
def register_builder(builder: "DocumentContextBuilder") -> None:
    if not builder.CODE:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_VALIDATION",
            message="DocumentContextBuilder senza CODE non registrabile.",
            detail=f"class={type(builder).__name__}",
        )
    forma = builder.CONTEXT_VERSION
    if isinstance(forma, bool) or not isinstance(forma, int) or forma < 1:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_VALIDATION",
            message="DocumentContextBuilder senza CONTEXT_VERSION non registrabile.",
            detail=f"class={type(builder).__name__} CONTEXT_VERSION={forma!r}",
        )
    _REGISTRY[builder.CODE] = builder


# Scopo: Risolve il builder da un codice. Solleva se il codice non e'
#        whitelisted: la lista delle chiavi e' la whitelist applicativa
#        del backend, indipendente da cosa permette il DDL DB.
def get_builder(code: str) -> "DocumentContextBuilder":
    builder = _REGISTRY.get(code)
    ErrorManager.require(
        builder is not None,
        code="E_DOCUMENTI_VALIDATION",
        message=f"Context builder '{code}' non registrato lato backend.",
        detail=f"registrati={sorted(_REGISTRY.keys())!r}",
    )
    assert builder is not None
    return builder


# Scopo: Il builder di un TEMPLATE (`template_documenti.context_builder_code`):
#        chi genera e chi pubblica una versione lo risolvono qui, con lo stesso
#        rifiuto (E_DOCUMENTI_VALIDATION) per un codice vuoto e per uno non
#        registrato. Regola del 2 (2026-09-30): generazione e pubblicazione
#        lo scrivevano ognuna a modo suo, e il codice vuoto rispondeva con due
#        frasi diverse.
def get_builder_del_template(template: dict[str, Any]) -> "DocumentContextBuilder":
    code = template.get("context_builder_code") or ""
    ErrorManager.require(
        bool(code),
        code="E_DOCUMENTI_VALIDATION",
        message="Template senza context_builder_code configurato.",
        detail=f"template_id={template.get('id')}",
    )
    return get_builder(code)


# Scopo: La forma dei dati che il builder `code` produce oggi, o None se il
#        codice non e' registrato. Per chi deve MOSTRARE la forma (il
#        dettaglio del template), non per chi deve stampare o pubblicare:
#        quelli passano da `get_builder`, che su un codice ignoto solleva.
def versione_contesto_registrata(code: str | None) -> int | None:
    builder = _REGISTRY.get(code or "")
    return builder.CONTEXT_VERSION if builder is not None else None


# Scopo: I builder registrati, ciascuno con la forma dei dati che produce
#        oggi, ordinati per codice. E' la sorgente della tendina del
#        template (`GET /api/v1/documenti/context-builders/`): il frontend
#        legge il registro, non ne tiene una copia.
def builder_registrati() -> list[dict[str, Any]]:
    return [
        {"codice": code, "versione_contesto": _REGISTRY[code].CONTEXT_VERSION}
        for code in sorted(_REGISTRY.keys())
    ]


# Scopo: Ritorna l'elenco dei codici registrati (per i test).
def registered_codes() -> list[str]:
    return [b["codice"] for b in builder_registrati()]
