# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Interfaccia astratta per i provider AI.
#        Definisce il contratto che ogni provider (Anthropic,
#        Mistral, Ollama, mock) deve implementare.
# ------------------------------------------------------------

from __future__ import annotations

import abc
from typing import Any

from apps.ai_assistant.types import ProviderResponse

# Dimensione vettore embedding. Deve coincidere con la colonna vector(N)
# nella tabella doc_embeddings (Fase 2.5b). Valore standard per modelli
# embedding moderni (Voyage, Mistral, sentence-transformers).
EMBEDDING_DIMENSIONS = 1024


class AIProvider(abc.ABC):
    """Contratto base per tutti i provider AI.

    Ogni implementazione gestisce la comunicazione con uno specifico
    servizio LLM (API esterna o modello locale) e normalizza la
    risposta nella struttura ProviderResponse.
    """

    @abc.abstractmethod
    def send_message(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
        model: str,
        max_tokens: int,
    ) -> ProviderResponse:
        """Scopo: Invia messaggi al provider AI e restituisce la risposta normalizzata.

        Args:
            messages: Lista messaggi conversazione (role + content).
            tools: Catalogo strumenti in formato JSON Schema.
            system: System prompt.
            model: Identificativo modello da usare.
            max_tokens: Limite massimo token risposta.

        Returns:
            ProviderResponse con content, tool_calls, usage, stop_reason.
        """

    @abc.abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """Scopo: Genera un vettore embedding per il testo dato.

        Usato dal sistema RAG (Fase 2.5b) per indicizzazione documenti
        e ricerca semantica.

        Args:
            text: Testo da convertire in embedding.

        Returns:
            Lista di float rappresentante il vettore embedding.
        """
