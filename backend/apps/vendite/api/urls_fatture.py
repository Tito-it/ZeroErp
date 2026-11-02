# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    ApiFatturaDocumentoRistampa,
    ApiFatturaDocumentoGenera,
)
from apps.vendite.api.fatture_views import (
    ApiFatturaDetail,
    ApiFatturaGiornale,
    ApiFattureExportView,
    ApiFattureList,
    ApiFatturaRigheListaExportView,
    ApiFatturaRigheListaView,
)
from apps.vendite.api.lineage_views import ApiFatturaPassaggi
from apps.vendite.api.note_views import ApiFatturaNoteDetail, ApiFatturaNoteList

urlpatterns = [
    # Note della fattura (BB partizionato, sesto dominio del ciclo attivo).
    # PRIMA del dettaglio `<int:fattura_id>/`: `note/` è un segmento letterale
    # e non collide, ma tenere le rotte più specifiche in testa evita sorprese
    # se un domani il dettaglio diventasse un pattern più permissivo.
    path("<int:fattura_id>/note/", ApiFatturaNoteList.as_view(),
         name="vendite-fattura-note-list"),
    path("<int:fattura_id>/note/<int:note_id>/", ApiFatturaNoteDetail.as_view(),
         name="vendite-fattura-note-detail"),
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
    # Ristampa fedele (percorso 3): versione pinnata + contesto congelato.
    # Sulla fattura e' il percorso piu' importante: e' un documento fiscale,
    # e riemetterlo non e' un'opzione.
    path("<int:sorgente_id>/documenti/<int:documento_id>/ristampa/",
         ApiFatturaDocumentoRistampa.as_view(),
         name="vendite-fattura-documenti-ristampa"),
    # Passaggi (genealogia): stessa factory degli altri sei domini.
    # ⚠️ PRIMA del dettaglio, come `note/` e `documenti/`.
    path("<int:fattura_id>/passaggi/", ApiFatturaPassaggi.as_view(),
         name="vendite-fattura-passaggi"),
    # ⭐ La LISTA e il suo export — le due rotte senza `<id>`, quindi in cima:
    # `export/` deve precedere qualunque pattern che possa catturarla.
    path("", ApiFattureList.as_view(), name="vendite-fatture-list"),
    path("export/", ApiFattureExportView.as_view(), name="vendite-fatture-export"),
    # Le righe come lista configurabile `vendite.fattura_righe` (lotto C del
    # brief-db-liste-righe-documento): PRIMA del dettaglio, come `passaggi/`.
    # `…/righe/lista/` come sui quattro documenti gemelli: la lettura completa
    # arriva col dettaglio, dalla stessa vista.
    path("<int:fattura_id>/righe/lista/", ApiFatturaRigheListaView.as_view(),
         name="vendite-fattura-righe-lista"),
    path("<int:fattura_id>/righe/lista/export/", ApiFatturaRigheListaExportView.as_view(),
         name="vendite-fattura-righe-lista-export"),
    # Giornale (la storia del documento): come `passaggi/`, PRIMA del dettaglio.
    # ⛔ Da non confondere con `passaggi/`: quello dice con quali altri documenti
    # la fattura e' legata, questo cosa le e' successo.
    path("<int:fattura_id>/giornale/", ApiFatturaGiornale.as_view(),
         name="vendite-fattura-giornale"),
    # Dettaglio di consultazione (drawer fattura): testata + righe + riepilogo
    # IVA + scadenze in un round-trip. ULTIMA della lista: `<int:fattura_id>/`
    # è il pattern più generico e deve cedere il passo a `note/` e `documenti/`.
    path("<int:fattura_id>/", ApiFatturaDetail.as_view(),
         name="vendite-fattura-detail"),
]
