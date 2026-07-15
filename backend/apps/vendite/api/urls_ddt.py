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
from apps.vendite.api.lineage_views import ApiDdtPassaggi
from apps.vendite.api.note_views import ApiDdtNoteDetail, ApiDdtNoteList
from apps.vendite.api.views_ddt import (
    ApiDdtCambiaStato,
    ApiDdtDetail,
    ApiDdtExportView,
    ApiDdtIndirizzi,
    ApiDdtIndirizzoDetail,
    ApiDdtList,
    ApiDdtPush,
    ApiDdtRiepilogoIva,
    ApiDdtRigaComponenteDetail,
    ApiDdtRigaComponentiList,
    ApiDdtRigaDetail,
    ApiDdtRigaPreviewComponenti,
    ApiDdtRighe,
    ApiDdtRighePerReso,
)
from apps.vendite.api.views_form_defaults import ApiDdtFormDefaults

urlpatterns = [
    # Lista + create (standalone)
    path("", ApiDdtList.as_view(), name="vendite-ddt-list"),
    # Export CSV/XLSX (DEF-1, `?formato=`). Prima di `<int:ddt_id>/` per non
    # collidere con il path del dettaglio.
    path("export/", ApiDdtExportView.as_view(), name="vendite-ddt-export"),
    # Form-defaults BA-aware (valuta/utility). Famiglia ordini/preventivi.
    path("form-defaults/", ApiDdtFormDefaults.as_view(),
         name="vendite-ddt-form-defaults"),
    path("<int:ddt_id>/", ApiDdtDetail.as_view(), name="vendite-ddt-detail"),
    path("<int:ddt_id>/riepilogo-iva/", ApiDdtRiepilogoIva.as_view(),
         name="vendite-ddt-riepilogo-iva"),
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage).
    path("<int:ddt_id>/passaggi/", ApiDdtPassaggi.as_view(),
         name="vendite-ddt-passaggi"),
    path("<int:ddt_id>/indirizzi/", ApiDdtIndirizzi.as_view(),
         name="vendite-ddt-indirizzi"),
    path("<int:ddt_id>/indirizzi/<int:indirizzo_id>/",
         ApiDdtIndirizzoDetail.as_view(),
         name="vendite-ddt-indirizzo-detail"),

    # Transizioni / integrazione. `emetti/` e' il flusso documentale multipart
    # (DRAFT->EMESSO + genera PDF + allegati, atomico — factory condiviso in
    # apps/documenti/api, converter `sorgente_id`); `cambia-stato/` resta la
    # transizione pura (riusata internamente).
    path("<int:sorgente_id>/emetti/", ApiDdtEmetti.as_view(),
         name="vendite-ddt-emetti"),
    path("<int:ddt_id>/cambia-stato/", ApiDdtCambiaStato.as_view(),
         name="vendite-ddt-cambia-stato"),
    path("<int:ddt_id>/push/", ApiDdtPush.as_view(),
         name="vendite-ddt-push"),

    # Documenti generati (stampa PDF) — motore `documenti`, sorgente
    # DDT_VENDITA (quinto dominio della famiglia, view dal factory condiviso:
    # converter uniforme `sorgente_id`).
    path("<int:sorgente_id>/documenti/", ApiDdtDocumentiList.as_view(),
         name="vendite-ddt-documenti-list"),
    path("<int:sorgente_id>/documenti/genera/", ApiDdtDocumentoGenera.as_view(),
         name="vendite-ddt-documenti-genera"),
    path("<int:sorgente_id>/documenti/anteprima/", ApiDdtDocumentoAnteprima.as_view(),
         name="vendite-ddt-documenti-anteprima"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/",
         ApiDdtDocumentoFile.as_view(),
         name="vendite-ddt-documenti-file"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
         ApiDdtDocumentoAllegati.as_view(),
         name="vendite-ddt-documenti-allegati"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
         ApiDdtDocumentoFileDownload.as_view(),
         name="vendite-ddt-documenti-file-download"),

    # Righe
    path("<int:ddt_id>/righe/", ApiDdtRighe.as_view(),
         name="vendite-ddt-righe-list"),
    # Righe con residuo rendibile per il pannello "crea reso" (slice resi).
    path("<int:ddt_id>/righe-per-reso/", ApiDdtRighePerReso.as_view(),
         name="vendite-ddt-righe-per-reso"),
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
