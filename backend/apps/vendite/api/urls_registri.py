# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Rotte del CRUD dei registri di numerazione, montate da `urls_v1.py`
#        sotto `registri/`. Brief: brief-be-fe-crud-registri-di-numerazione §10.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.views_registri import (
    ApiRegistriList,
    ApiRegistroAttivo,
    ApiRegistroDetail,
)

urlpatterns = [
    path("", ApiRegistriList.as_view(), name="vendite-registri-list"),
    path(
        "<int:registro_id>/",
        ApiRegistroDetail.as_view(),
        name="vendite-registri-detail",
    ),
    # ⭐ Verbo suo e non un PATCH su `attivo`: e' l'azione che riattiva un
    #    registro spento al posto di crearne un altro sulla stessa terna (§0).
    path(
        "<int:registro_id>/attivo/",
        ApiRegistroAttivo.as_view(),
        name="vendite-registri-attivo",
    ),
]
