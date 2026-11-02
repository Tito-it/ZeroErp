# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Config app Django per `apps.shop`.
# ------------------------------------------------------------

from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "apps.shop"
    label = "shop"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Shop B2C"
