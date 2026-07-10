# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API DDT di vendita (CRUD testata + righe + componenti BoM,
#        emissione, cambio stato, push a commessa, note). Clone di urls_ordini.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.ddt_documenti_views import (
    ApiDdtDocumentiList,
    ApiDdtDocumentoAllegati,
    ApiDdtDocumentoAnteprima,
    ApiDdtDocumentoFile,
    ApiDdtDocumentoFileDownload,
    ApiDdtDocumentoGenera,
    ApiDdtEmetti,
)
from apps.vendite.api.note_views import ApiDdtNoteDetail, ApiDdtNoteList
from apps.vendite.api.views_ddt import (
    ApiDdtCambiaStato,
    ApiDdtDetail,
    ApiDdtList,
    ApiDdtPush,
    ApiDdtRigaComponenteDetail,
    ApiDdtRigaComponentiList,
    ApiDdtRigaDetail,
    ApiDdtRigaPreviewComponenti,
    ApiDdtRighe,
)
from apps.vendite.api.views_form_defaults import ApiDdtFormDefaults

urlpatterns = [
    # Lista + create (standalone)
    path("", ApiDdtList.as_view(), name="vendite-ddt-list"),
    # Form-defaults BA-aware (valuta/utility). Famiglia ordini/preventivi.
    path("form-defaults/", ApiDdtFormDefaults.as_view(),
         name="vendite-ddt-form-defaults"),
    path("<int:ddt_id>/", ApiDdtDetail.as_view(), name="vendite-ddt-detail"),

    # Transizioni / integrazione. `emetti/` e' il flusso documentale multipart
    # (DRAFT->EMESSO + genera PDF + allegati, atomico — ddt_documenti_views);
    # `cambia-stato/` resta la transizione pura (riusata internamente).
    path("<int:ddt_id>/emetti/", ApiDdtEmetti.as_view(),
         name="vendite-ddt-emetti"),
    path("<int:ddt_id>/cambia-stato/", ApiDdtCambiaStato.as_view(),
         name="vendite-ddt-cambia-stato"),
    path("<int:ddt_id>/push/", ApiDdtPush.as_view(),
         name="vendite-ddt-push"),

    # Documenti generati (stampa PDF) — motore `documenti`, sorgente
    # DDT_VENDITA (quinto dominio della famiglia).
    path("<int:ddt_id>/documenti/", ApiDdtDocumentiList.as_view(),
         name="vendite-ddt-documenti-list"),
    path("<int:ddt_id>/documenti/genera/", ApiDdtDocumentoGenera.as_view(),
         name="vendite-ddt-documenti-genera"),
    path("<int:ddt_id>/documenti/anteprima/", ApiDdtDocumentoAnteprima.as_view(),
         name="vendite-ddt-documenti-anteprima"),
    path("<int:ddt_id>/documenti/<int:documento_id>/file/",
         ApiDdtDocumentoFile.as_view(),
         name="vendite-ddt-documenti-file"),
    path("<int:ddt_id>/documenti/<int:documento_id>/allegati/",
         ApiDdtDocumentoAllegati.as_view(),
         name="vendite-ddt-documenti-allegati"),
    path("<int:ddt_id>/documenti/<int:documento_id>/file/<int:file_id>/",
         ApiDdtDocumentoFileDownload.as_view(),
         name="vendite-ddt-documenti-file-download"),

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
