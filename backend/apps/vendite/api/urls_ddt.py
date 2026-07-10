# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API DDT di vendita (CRUD testata + righe + componenti BoM,
#        emissione, cambio stato, push a commessa, note). Clone di urls_ordini.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.note_views import ApiDdtNoteDetail, ApiDdtNoteList
from apps.vendite.api.views_ddt import (
    ApiDdtCambiaStato,
    ApiDdtDetail,
    ApiDdtEmetti,
    ApiDdtList,
    ApiDdtPush,
    ApiDdtRigaComponenteDetail,
    ApiDdtRigaComponentiList,
    ApiDdtRigaDetail,
    ApiDdtRigaPreviewComponenti,
    ApiDdtRighe,
)

urlpatterns = [
    # Lista + create (standalone)
    path("", ApiDdtList.as_view(), name="vendite-ddt-list"),
    path("<int:ddt_id>/", ApiDdtDetail.as_view(), name="vendite-ddt-detail"),

    # Transizioni / integrazione
    path("<int:ddt_id>/emetti/", ApiDdtEmetti.as_view(),
         name="vendite-ddt-emetti"),
    path("<int:ddt_id>/cambia-stato/", ApiDdtCambiaStato.as_view(),
         name="vendite-ddt-cambia-stato"),
    path("<int:ddt_id>/push/", ApiDdtPush.as_view(),
         name="vendite-ddt-push"),

    # Righe
    path("<int:ddt_id>/righe/", ApiDdtRighe.as_view(),
         name="vendite-ddt-righe-list"),
    path("<int:ddt_id>/righe/preview-componenti/",
         ApiDdtRigaPreviewComponenti.as_view(),
         name="vendite-ddt-righe-preview-componenti"),
    path("<int:ddt_id>/righe/<int:riga_id>/", ApiDdtRigaDetail.as_view(),
         name="vendite-ddt-riga-detail"),

    # Componenti BoM
    path("<int:ddt_id>/righe/<int:riga_id>/componenti/",
         ApiDdtRigaComponentiList.as_view(),
         name="vendite-ddt-riga-componenti-list"),
    path("<int:ddt_id>/righe/<int:riga_id>/componenti/<int:componente_id>/",
         ApiDdtRigaComponenteDetail.as_view(),
         name="vendite-ddt-riga-componente-detail"),

    # Note partizionate (target_tipo='DDT'). Building block
    # PartitionedNoteRepository: 3 righe di cablaggio + view generata.
    path("<int:ddt_id>/note/", ApiDdtNoteList.as_view(),
         name="vendite-ddt-note-list"),
    path("<int:ddt_id>/note/<int:note_id>/", ApiDdtNoteDetail.as_view(),
         name="vendite-ddt-note-detail"),
]
