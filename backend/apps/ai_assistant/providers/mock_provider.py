# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Provider AI mock per test CI e sviluppo locale.
#        Restituisce risposte predefinite senza chiamate di rete.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.providers.base import AIProvider, EMBEDDING_DIMENSIONS
from apps.ai_assistant.types import ProviderResponse, ToolCall, TokenUsage


class MockProvider(AIProvider):
    """Provider mock per test unitari e CI.

    Comportamento configurabile:
    - Di default restituisce una risposta testuale fissa.
    - Se configurato con tool_response, simula una tool_call.
    - Nessuna chiamata di rete, nessuna dipendenza esterna.
    """

    def __init__(
        self,
        *,
        default_response: str = "Risposta mock dell'assistente AI.",
        tool_response: ToolCall | None = None,
    ) -> None:
        self._default_response = default_response
        self._tool_response = tool_response
        self.last_messages: list[dict[str, Any]] = []
        self.last_system: str = ""
        self.last_tools: list[dict[str, Any]] = []
        self.call_count: int = 0

    # Scopo: Simula una risposta del provider AI.
    #        Registra i parametri ricevuti per consentire asserzioni nei test.
    def send_message(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
        model: str,
        max_tokens: int,
    ) -> ProviderResponse:
        # Registra parametri per ispezione nei test
        self.last_messages = messages
        self.last_system = system
        self.last_tools = tools
        self.call_count += 1

        # Se configurato per simulare tool_call, restituisci quella
        if self._tool_response is not None and self.call_count == 1:
            return ProviderResponse(
                content=None,
                tool_calls=[self._tool_response],
                usage=TokenUsage(input_tokens=100, output_tokens=50),
                stop_reason="tool_use",
            )

        # Altrimenti risposta testuale
        return ProviderResponse(
            content=self._default_response,
            tool_calls=[],
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            stop_reason="end_turn",
        )

    # Scopo: Genera un embedding mock di dimensione configurabile.
    #        Utile per test del sistema RAG senza chiamate API.
    def generate_embedding(self, text: str) -> list[float]:
        # Vettore deterministico basato sulla lunghezza del testo
        base = len(text) % 100 / 100.0
        return [base + (i * 0.001) for i in range(EMBEDDING_DIMENSIONS)]
