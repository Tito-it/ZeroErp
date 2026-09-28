# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from typing import TYPE_CHECKING

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
def register_builder(builder: "DocumentContextBuilder") -> None:
    if not builder.CODE:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_VALIDATION",
            message="DocumentContextBuilder senza CODE non registrabile.",
            detail=f"class={type(builder).__name__}",
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


# Scopo: Ritorna l'elenco dei codici registrati. Usato dai test e dalla
#        view diagnostica /api/v1/documenti/context-builders/ (futura).
def registered_codes() -> list[str]:
    return sorted(_REGISTRY.keys())
