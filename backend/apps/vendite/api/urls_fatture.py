# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API fatture — documenti generati (stampa/ristampa PDF),
#        motore `documenti`, sorgente FATTURA. A differenza degli altri
#        domini vendite NON c'è rotta `emetti/`: la fattura è prodotta dalla
#        pipeline di fatturazione, si stampa/ristampa soltanto (C-2).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.fatture_documenti_views import (
    ApiFatturaDocumentiList,
    ApiFatturaDocumentoAllegati,
    ApiFatturaDocumentoAnteprima,
    ApiFatturaDocumentoFile,
    ApiFatturaDocumentoFileDownload,
    ApiFatturaDocumentoGenera,
)

urlpatterns = [
    # Documenti generati (stampa PDF) — motore `documenti`, sorgente FATTURA.
    # Clone della catena ordini/DDT, SENZA emissione (la fattura non si emette).
    path("<int:sorgente_id>/documenti/", ApiFatturaDocumentiList.as_view(),
         name="vendite-fattura-documenti-list"),
    path("<int:sorgente_id>/documenti/genera/", ApiFatturaDocumentoGenera.as_view(),
         name="vendite-fattura-documenti-genera"),
    path("<int:sorgente_id>/documenti/anteprima/", ApiFatturaDocumentoAnteprima.as_view(),
         name="vendite-fattura-documenti-anteprima"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/",
         ApiFatturaDocumentoFile.as_view(),
         name="vendite-fattura-documenti-file"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
         ApiFatturaDocumentoAllegati.as_view(),
         name="vendite-fattura-documenti-allegati"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
         ApiFatturaDocumentoFileDownload.as_view(),
         name="vendite-fattura-documenti-file-download"),
]
