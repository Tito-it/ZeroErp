# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Config app Django per `apps.ui` — strato di presentazione
#        (personalizzazioni liste, schema DB `ui`).
# ------------------------------------------------------------

from django.apps import AppConfig


class UiConfig(AppConfig):
    name = "apps.ui"
    label = "ui"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "UI — personalizzazioni liste"
