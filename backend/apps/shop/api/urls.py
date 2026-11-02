# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL namespace `/api/v1/shop/*` — attivazione shop customer
#        (B1 §13.7 admin-driven) + stub residui per flussi self-register
#        che arriveranno con PR-C/PR-D.
# ------------------------------------------------------------

from __future__ import annotations

from django.urls import path

from apps.shop.api.views import ShopRegisterCheckEmailView
from apps.shop.api.views_attivazione import (
    AttivazioneShopValidateView,
    AttivazioneShopView,
)

urlpatterns = [
    # §13.7 B1: attivazione shop customer (INVITO o CROSS).
    path(
        "attivazione/validate/<str:token>/",
        AttivazioneShopValidateView.as_view(),
        name="shop-attivazione-validate",
    ),
    path(
        "attivazione/conferma/",
        AttivazioneShopView.as_view(),
        name="shop-attivazione-conferma",
    ),
    # §8.4.5 stub: check email per registrazione shop self-service.
    # Resta stub finche' il flusso pubblico (§5.6 completo) non viene
    # implementato.
    path(
        "register/check-email/",
        ShopRegisterCheckEmailView.as_view(),
        name="shop-register-check-email",
    ),
]
