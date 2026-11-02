# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Configurazione app Django per il modulo Amm. Software.
# ------------------------------------------------------------

from django.apps import AppConfig


class AmmSoftwareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.amm_software"
