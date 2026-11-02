# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Config app Django per `apps.documenti`.
# ------------------------------------------------------------

from django.apps import AppConfig


class DocumentiConfig(AppConfig):
    name = "apps.documenti"
    label = "documenti"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Documenti — motore documentale parametrico"
