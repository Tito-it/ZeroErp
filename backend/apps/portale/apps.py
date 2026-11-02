# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Config app Django per `apps.portale`.
# ------------------------------------------------------------

from django.apps import AppConfig


class PortaleConfig(AppConfig):
    name = "apps.portale"
    label = "portale"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Portale clienti/fornitori"
