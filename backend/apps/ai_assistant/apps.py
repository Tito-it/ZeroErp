# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Configurazione app Django per il modulo assistente AI.
# ------------------------------------------------------------

from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"

    # Scopo: Popola il registro strumenti AI all'avvio dell'app.
    def ready(self) -> None:
        from apps.ai_assistant.services.tool_registry import populate_registry

        populate_registry()
