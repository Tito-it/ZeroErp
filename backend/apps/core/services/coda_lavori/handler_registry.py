# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Registry dei job handler della coda generica: `handler_code → callable`,
#        dispatch CONTROLLATO (no dynamic import), stessa filosofia del
#        `PipelineStepExecutor.handler_registry` e del registry dei context
#        builder documentali. `dbops.coda_lavori_tipi.handler_code` è la chiave
#        DB; la registrazione Python la lega alla funzione, esplicitamente al
#        boot delle app (`AppConfig.ready()`), MAI per auto-discovery.
#
#        Contratto handler: `handler(payload: dict, *, scope: dict | None) -> dict`
#        (ritorna il `result` del job); solleva `ServiceError` su fallimento di
#        dominio (il motore lo traduce in ERRORE/retry). `scope` è lo scope
#        catturato all'enqueue per i job OPERATORE (None per i SISTEMA).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.core.services.error_manager import ErrorManager

# Firma dell'handler di un job.
JobHandler = Callable[..., dict[str, Any] | None]

_REGISTRY: dict[str, JobHandler] = {}

E_HANDLER_NON_REGISTRATO = "E_CODA_HANDLER_NON_REGISTRATO"


# Scopo: Registra (o rimpiazza) l'handler per un `handler_code`. Chiamata
#        esplicita al boot dell'app che possiede il job (es. VenditeConfig.ready()
#        per FATTURAZIONE_GIRO). Rimpiazzo idempotente: ri-registrare lo stesso
#        codice sovrascrive (utile in test/reload), non è un errore.
def register_handler(handler_code: str, handler: JobHandler) -> None:
    _REGISTRY[handler_code] = handler


# Scopo: Risolve l'handler per un `handler_code`. Fail-loud parlante se non
#        registrato: un job con handler mancante è un bug di cablaggio (seed DB
#        senza il corrispondente `register_handler`), non un errore di dominio.
# `str | None`: un codice assente (riga di coda senza `handler_code`) e' lo
# stesso rifiuto di un codice sconosciuto, `E_HANDLER_NON_REGISTRATO`.
def get_handler(handler_code: str | None) -> JobHandler:
    handler = _REGISTRY.get(handler_code) if handler_code is not None else None
    ErrorManager.require(
        handler is not None,
        code=E_HANDLER_NON_REGISTRATO,
        message="Handler di job non registrato.",
        detail=f"handler_code={handler_code!r}",
    )
    assert handler is not None
    return handler


# Scopo: Insieme dei codici handler registrati (introspezione/test).
def registered_handlers() -> set[str]:
    return set(_REGISTRY)
