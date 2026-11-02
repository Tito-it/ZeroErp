# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Rotte API v1 per il modulo assistente AI.
# ------------------------------------------------------------

from django.urls import path

from apps.ai_assistant.api.views import AIQueryView, AIStatusView

urlpatterns = [
    path("query/", AIQueryView.as_view(), name="ai-assistant-query"),
    path("status/", AIStatusView.as_view(), name="ai-assistant-status"),
]
