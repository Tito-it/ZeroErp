# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Registro centralizzato degli strumenti AI.
#        Gestisce il catalogo dei tool disponibili, il filtro
#        per permessi utente e la blacklist da config.parameters.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import time
from typing import Any

from apps.ai_assistant.tools.base import AITool

logger = logging.getLogger(__name__)

# Catalogo globale dei tool registrati
_REGISTRY: dict[str, AITool] = {}

# Cache blacklist: (set, timestamp). TTL 300s — la blacklist cambia raramente.
_DISABLED_CACHE: tuple[set[str], float] | None = None
_DISABLED_CACHE_TTL = 300


# Scopo: Registra un tool nel catalogo globale.
#        Chiamata all'avvio dell'app per popolare il registro.
def register_tool(tool: AITool) -> None:
    _REGISTRY[tool.name] = tool
    logger.debug("AI tool registrato: %s", tool.name)


# Scopo: Registra una lista di tool in blocco.
def register_tools(tools: list[AITool]) -> None:
    for tool in tools:
        register_tool(tool)


# Scopo: Restituisce i tool disponibili per un utente specifico.
#        Applica tre livelli di filtro:
#        1. Blacklist da config.parameters (disabilitati per installazione)
#        2. Permessi area_funzionale dell'utente (via PermissionResolver core)
#        3. Livello accesso minimo richiesto dal tool
def get_tools_for_user(user: Any) -> list[AITool]:
    from apps.core.services.permissions_resolver import PermissionResolver

    # Carica blacklist da config.parameters
    disabled = _get_disabled_tools()

    # Cache per-request per evitare query ripetute sulla stessa area
    perm_cache: dict[str, Any] = {}

    filtered: list[AITool] = []
    for tool in _REGISTRY.values():
        # Filtro 1: blacklist installazione
        if tool.name in disabled:
            continue

        # Filtro 2: area funzionale (None = disponibile a tutti)
        if tool.required_area is not None:
            area_level = PermissionResolver.get_livello_area(
                user, tool.required_area, cache=perm_cache
            )
            if area_level == "BLOCCATO":
                continue

            # Filtro 3: livello accesso minimo
            if tool.required_level == "TUTTO" and area_level != "TUTTO":
                continue

        filtered.append(tool)

    return filtered


# Scopo: Recupera un tool per nome dal catalogo.
#        Restituisce None se il tool non esiste.
def get_tool_by_name(name: str) -> AITool | None:
    return _REGISTRY.get(name)


# Scopo: Restituisce tutti i tool registrati (senza filtri).
#        Utile per diagnostica e test.
def get_all_tools() -> list[AITool]:
    return list(_REGISTRY.values())


# Scopo: Svuota il registro. Solo per test.
def clear_registry() -> None:
    _REGISTRY.clear()


# Scopo: Legge la blacklist tool da config.parameters con cache TTL.
#        Chiave: AI_DISABLED_TOOLS (lista separata da virgola).
#        Cache 300s — la blacklist cambia raramente.
def _get_disabled_tools() -> set[str]:
    global _DISABLED_CACHE
    now = time.monotonic()

    if _DISABLED_CACHE is not None:
        cached_set, cached_at = _DISABLED_CACHE
        if now - cached_at < _DISABLED_CACHE_TTL:
            return cached_set

    result: set[str] = set()
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_get_parameter_full('AI_DISABLED_TOOLS')"
            )
            row = cursor.fetchone()
            if row and row[0]:
                result = {t.strip() for t in str(row[0]).split(",") if t.strip()}
    except Exception:
        logger.debug("config.parameters AI_DISABLED_TOOLS non trovato, nessun tool disabilitato")

    _DISABLED_CACHE = (result, now)
    return result



# Scopo: Popola il registro con tutti i tool disponibili.
#        Chiamata da AppConfig.ready() all'avvio dell'app.
#        Aggiungere qui i nuovi moduli tool quando vengono creati.
def populate_registry() -> None:
    from apps.ai_assistant.tools.pratiche_tools import get_pratiche_tools
    from apps.ai_assistant.tools.anagrafiche_tools import get_anagrafiche_tools
    from apps.ai_assistant.tools.billing_account_tools import get_billing_account_tools
    from apps.ai_assistant.tools.catalogo_tools import get_catalogo_tools
    from apps.ai_assistant.tools.config_tools import get_config_tools
    from apps.ai_assistant.tools.vendite_tools import get_vendite_tools
    from apps.ai_assistant.tools.documenti_tools import get_documenti_tools

    register_tools(get_pratiche_tools())
    register_tools(get_anagrafiche_tools())
    register_tools(get_billing_account_tools())
    register_tools(get_catalogo_tools())
    register_tools(get_config_tools())
    register_tools(get_vendite_tools())
    register_tools(get_documenti_tools())
    logger.info("AI tool registry popolato: %d tool registrati", len(_REGISTRY))
