# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Configurazione app Django per il modulo gestione pratiche.
# ------------------------------------------------------------

from django.apps import AppConfig


class PraticheConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pratiche"
