# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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


# Scopo: Predicato unico "questo utente puo' usare questo tool?".
#        Fonte di verita' condivisa dal filtro catalogo (offer-time) E dal
#        ri-check a execution-time nel service (preview/confirm), per chiudere
#        il gap TOCTOU: senza questo, l'unico gate sarebbe il catalogo all'offer-time.
#        Tre filtri: la blacklist dell'installazione, il permesso
#        dell'endpoint gemello del tool, il livello sull'assistente.
# ⭐ Il permesso NON e' calcolato qui: lo decide `valuta_accesso_endpoint`, la
#    stessa regola di `ZeroERPPermission` per la UI (brief-db-area-funzionale-
#    assistente-ai §5.2). Fino al 2026-09-24 questa funzione ne era una seconda
#    copia, alimentata da valori scritti a mano su ogni tool. Ora l'AI puo'
#    fare cio' che l'operatore puo' fare dalla UI, e niente di piu': area dal
#    model o da `area_funzionale`, `<metodo>_permission`, SUPER_ADMIN, ruolo
#    disabilitato, override per oggetto, `skip_area_check`.
# ⭐ Il terzo filtro e' il livello su `ai_assistant` (§5.3): LETTURA consulta,
#    TUTTO anche agisce. Si chiede all'ingresso dell'assistente (`AIQueryView`)
#    il tipo di accesso del TOOL (`view` se legge, quello del gemello se
#    scrive), non quello della POST della domanda. Vale sempre il piu' stretto
#    dei due livelli: `TUTTO` su `pratiche` e `LETTURA` sull'assistente crea
#    pratiche dalla UI, non tramite l'assistente.
def is_tool_allowed_for_user(
    user: Any,
    tool: AITool,
    *,
    perm_cache: dict[str, Any] | None = None,
    disabled: set[str] | None = None,
) -> bool:
    from apps.ai_assistant.api.views import AIQueryView
    from apps.core.api.permissions import ZeroERPPermission, valuta_accesso_endpoint

    if perm_cache is None:
        perm_cache = {}

    # Filtro 1: blacklist installazione
    if disabled is None:
        disabled = _get_disabled_tools()
    if tool.name in disabled:
        return False

    # Filtro 2: la regola dell'endpoint gemello
    if not valuta_accesso_endpoint(
        user,
        tool.endpoint.view,
        method=tool.endpoint.metodo,
        cache=perm_cache,
    ).consentito:
        return False

    # Filtro 3: il livello sull'assistente, col tipo di accesso del tool, che
    # e' quello del gemello (`view` se legge: e' la stessa regola di
    # `tool.scrive`). Nel caso di un gemello protetto da un'azione, che non ha
    # un tipo CRUD suo, il tipo lo da' comunque il verbo.
    # ⛔ Un tipo che la catena non sa dire nega QUI: passato come `None` a
    #    `valuta`, ricadrebbe sul `post_accesso = "view"` della domanda.
    accesso_tool = ZeroERPPermission.tipo_accesso(
        tool.endpoint.view, method=tool.endpoint.metodo,
    )
    if accesso_tool is None:
        return False
    return valuta_accesso_endpoint(
        user,
        AIQueryView,
        method="POST",
        accesso=accesso_tool,
        cache=perm_cache,
    ).consentito


# Scopo: Restituisce i tool disponibili per un utente specifico.
#        Filtro all'offer-time del catalogo inviato al modello. Usa lo stesso
#        predicato `is_tool_allowed_for_user` del ri-check a execution-time.
def get_tools_for_user(user: Any) -> list[AITool]:
    # Carica blacklist una volta + cache permessi per-request
    disabled = _get_disabled_tools()
    perm_cache: dict[str, Any] = {}

    return [
        tool
        for tool in _REGISTRY.values()
        if is_tool_allowed_for_user(
            user, tool, perm_cache=perm_cache, disabled=disabled
        )
    ]


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
