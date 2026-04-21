# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL namespace `/api/v1/shop/*` — stub PR-B (§8.4.4/§8.4.5),
#        MVP reale in PR-C.
# ------------------------------------------------------------

from __future__ import annotations

from django.urls import path

from apps.shop.api.views import (
    ShopActivateView,
    ShopRegisterCheckEmailView,
)

urlpatterns = [
    # §8.4.4 stub: attivazione account shop via token.
    path(
        "activate/<str:token>/",
        ShopActivateView.as_view(),
        name="shop-activate",
    ),
    # §8.4.5 stub: check email per registrazione shop.
    path(
        "register/check-email/",
        ShopRegisterCheckEmailView.as_view(),
        name="shop-register-check-email",
    ),
]
