# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API ordini di vendita (scheletro CRUD + conferma + push + note).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.note_views import ApiOrdineNoteDetail, ApiOrdineNoteList
from apps.vendite.api.ordini_documenti_views import (
    ApiOrdineDocumentiList,
    ApiOrdineDocumentoAllegati,
    ApiOrdineDocumentoAnteprima,
    ApiOrdineDocumentoFile,
    ApiOrdineDocumentoFileDownload,
    ApiOrdineDocumentoGenera,
)
from apps.vendite.api.views_form_defaults import ApiOrdineFormDefaults
from apps.vendite.api.views_ordini import (
    ApiOrdineConferma,
    ApiOrdineDetail,
    ApiOrdinePush,
    ApiOrdineRigaComponenteDetail,
    ApiOrdineRigaComponentiList,
    ApiOrdineRigaDetail,
    ApiOrdineRigaPreviewComponenti,
    ApiOrdineRighe,
    ApiOrdiniExportView,
    ApiOrdiniList,
)

urlpatterns = [
    # Export (prima di <int:ordine_id>/ per chiarezza).
    path("export/", ApiOrdiniExportView.as_view(), name="vendite-ordini-export"),

    # Form-defaults BA-aware (utility/valuta) per il drawer.
    path("form-defaults/", ApiOrdineFormDefaults.as_view(),
         name="vendite-ordine-form-defaults"),

    # Lista + create
    path("", ApiOrdiniList.as_view(), name="vendite-ordini-list"),
    path("<int:ordine_id>/", ApiOrdineDetail.as_view(), name="vendite-ordine-detail"),

    # Transizioni / integrazione
    path("<int:ordine_id>/conferma/", ApiOrdineConferma.as_view(),
         name="vendite-ordine-conferma"),
    path("<int:ordine_id>/push/", ApiOrdinePush.as_view(),
         name="vendite-ordine-push"),

    # Righe
    path("<int:ordine_id>/righe/", ApiOrdineRighe.as_view(),
         name="vendite-ordine-righe-list"),
    path("<int:ordine_id>/righe/preview-componenti/",
         ApiOrdineRigaPreviewComponenti.as_view(),
         name="vendite-ordine-righe-preview-componenti"),
    path("<int:ordine_id>/righe/<int:riga_id>/", ApiOrdineRigaDetail.as_view(),
         name="vendite-ordine-riga-detail"),

    # Componenti BoM
    path("<int:ordine_id>/righe/<int:riga_id>/componenti/",
         ApiOrdineRigaComponentiList.as_view(),
         name="vendite-ordine-riga-componenti-list"),
    path("<int:ordine_id>/righe/<int:riga_id>/componenti/<int:componente_id>/",
         ApiOrdineRigaComponenteDetail.as_view(),
         name="vendite-ordine-riga-componente-detail"),

    # Documenti generati (stampa PDF) — motore `documenti`, sorgente
    # ORDINE_VENDITA. Clone della catena preventivi/offerte. §12 analisi.
    path("<int:ordine_id>/documenti/", ApiOrdineDocumentiList.as_view(),
         name="vendite-ordine-documenti-list"),
    path("<int:ordine_id>/documenti/genera/", ApiOrdineDocumentoGenera.as_view(),
         name="vendite-ordine-documenti-genera"),
    path("<int:ordine_id>/documenti/anteprima/", ApiOrdineDocumentoAnteprima.as_view(),
         name="vendite-ordine-documenti-anteprima"),
    path("<int:ordine_id>/documenti/<int:documento_id>/file/",
         ApiOrdineDocumentoFile.as_view(),
         name="vendite-ordine-documenti-file"),
    path("<int:ordine_id>/documenti/<int:documento_id>/allegati/",
         ApiOrdineDocumentoAllegati.as_view(),
         name="vendite-ordine-documenti-allegati"),
    path("<int:ordine_id>/documenti/<int:documento_id>/file/<int:file_id>/",
         ApiOrdineDocumentoFileDownload.as_view(),
         name="vendite-ordine-documenti-file-download"),

    # Note partizionate (target_tipo='ORDINE'). Building block
    # PartitionedNoteRepository: 3 righe di cablaggio + view generata.
    path("<int:ordine_id>/note/", ApiOrdineNoteList.as_view(),
         name="vendite-ordine-note-list"),
    path("<int:ordine_id>/note/<int:note_id>/", ApiOrdineNoteDetail.as_view(),
         name="vendite-ordine-note-detail"),
]
