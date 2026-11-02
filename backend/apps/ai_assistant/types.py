# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict e tipi condivisi per il modulo ai_assistant.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, TypedDict


class ProviderResponse(TypedDict):
    """Risposta normalizzata da qualsiasi provider AI."""

    content: str | None
    tool_calls: list[ToolCall]
    usage: TokenUsage
    stop_reason: str


class ToolCall(TypedDict):
    """Singola chiamata tool richiesta dal provider."""

    id: str
    name: str
    input: dict[str, Any]


class TokenUsage(TypedDict):
    """Conteggio token consumati."""

    input_tokens: int
    output_tokens: int


class ToolResult(TypedDict):
    """Risultato dell'esecuzione di un tool, da restituire al provider."""

    tool_use_id: str
    content: str


class AIQueryResult(TypedDict):
    """Risultato finale di una query AI, restituito dall'endpoint."""

    conversation_id: str
    response: str
    tools_used: list[str]
    actions: list[dict[str, Any]]
    has_more: bool
