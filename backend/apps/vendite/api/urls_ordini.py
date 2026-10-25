# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API ordini di vendita (scheletro CRUD + conferma + push + note).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.legami_views import ApiOrdineLegami
from apps.vendite.api.lineage_views import ApiOrdinePassaggi
from apps.vendite.api.situazione_merce_views import ApiOrdineSituazioneMerce
from apps.vendite.api.note_views import ApiOrdineNoteDetail, ApiOrdineNoteList
from apps.vendite.api.ordini_documenti_views import (
    ApiOrdineDocumentiList,
    ApiOrdineDocumentoAllegati,
    ApiOrdineDocumentoAnteprima,
    ApiOrdineDocumentoFile,
    ApiOrdineDocumentoFileDownload,
    ApiOrdineDocumentoRistampa,
    ApiOrdineDocumentoGenera,
    ApiOrdineEmetti,
)
from apps.vendite.api.views_form_defaults import ApiOrdineFormDefaults
from apps.vendite.api.views_ordini import (
    ApiOrdineCambiaStato,
    ApiOrdineConferma,
    ApiOrdineDetail,
    ApiOrdineGeneraDdt,
    ApiOrdinePerPratica,
    ApiOrdineIndirizzi,
    ApiOrdineIndirizzoDetail,
    ApiOrdinePush,
    ApiOrdineRiepilogoIva,
    ApiOrdineRigaComponenteDetail,
    ApiOrdineRigaComponentiList,
    ApiOrdineRigaDataConsegnaConfermata,
    ApiOrdineRigheDateConsegna,
    ApiOrdineRigaDetail,
    ApiOrdineRigaPreviewComponenti,
    ApiOrdineRighe,
    ApiOrdineRigheListaExportView,
    ApiOrdineRigheListaView,
    ApiOrdiniExportView,
    ApiOrdiniList,
)

urlpatterns = [
    # Export (prima di <int:ordine_id>/ per chiarezza).
    path("export/", ApiOrdiniExportView.as_view(), name="vendite-ordini-export"),

    # Form-defaults BA-aware (utility/valuta) per il drawer.
    path("form-defaults/", ApiOrdineFormDefaults.as_view(),
         name="vendite-ordine-form-defaults"),

    # Step pratica a valle: risolve l'ordine COLLEGATO della pratica
    # (prima di <int:ordine_id>/ per matchare il path dedicato).
    path("per-pratica/", ApiOrdinePerPratica.as_view(),
         name="vendite-ordine-per-pratica"),

    # Lista + create
    path("", ApiOrdiniList.as_view(), name="vendite-ordini-list"),
    path("<int:ordine_id>/", ApiOrdineDetail.as_view(), name="vendite-ordine-detail"),

    # Riepilogo IVA aggregato (regola fiscale art. 21 DPR 633/72) — view derivata
    path("<int:ordine_id>/riepilogo-iva/", ApiOrdineRiepilogoIva.as_view(),
         name="vendite-ordine-riepilogo-iva"),
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage).
    path("<int:ordine_id>/passaggi/", ApiOrdinePassaggi.as_view(),
         name="vendite-ordine-passaggi"),
    # I legami dell'ordine, per la conferma dell'annullo (legami_views).
    path("<int:ordine_id>/legami/", ApiOrdineLegami.as_view(),
         name="vendite-ordine-legami"),
    # Situazione merce (pannello cantiere 2): riassunto per riga d'ordine +
    # partite + le due code, in un round-trip. Sola lettura.
    path("<int:ordine_id>/situazione-merce/", ApiOrdineSituazioneMerce.as_view(),
         name="vendite-ordine-situazione-merce"),

    # Indirizzi documento (pannello slot-per-tipo, factory condiviso)
    path("<int:ordine_id>/indirizzi/", ApiOrdineIndirizzi.as_view(),
         name="vendite-ordine-indirizzi"),
    path("<int:ordine_id>/indirizzi/<int:indirizzo_id>/",
         ApiOrdineIndirizzoDetail.as_view(),
         name="vendite-ordine-indirizzo-detail"),

    # Transizioni / integrazione
    # Emissione = conferma documentale (DRAFT->CONFERMATO + genera PDF +
    # allegati, multipart, atomica). Flusso target della famiglia vendite
    # (§6 brief-ordini-stampa.md). `/conferma/` resta come API di servizio
    # (sola transizione, riusata internamente da `emetti`).
    path("<int:sorgente_id>/emetti/", ApiOrdineEmetti.as_view(),
         name="vendite-ordine-emetti"),
    path("<int:ordine_id>/conferma/", ApiOrdineConferma.as_view(),
         name="vendite-ordine-conferma"),
    path("<int:ordine_id>/cambia-stato/", ApiOrdineCambiaStato.as_view(),
         name="vendite-ordine-cambia-stato"),
    path("<int:ordine_id>/push/", ApiOrdinePush.as_view(),
         name="vendite-ordine-push"),

    # Evasione: genera un DDT (DRAFT) dall'ordine (dominio sorgente, come
    # genera-ordine sta nei preventivi). Logica in ddt_service.
    path("<int:ordine_id>/genera-ddt/", ApiOrdineGeneraDdt.as_view(),
         name="vendite-ordine-genera-ddt"),

    # Righe
    path("<int:ordine_id>/righe/", ApiOrdineRighe.as_view(),
         name="vendite-ordine-righe-list"),
    # Righe: la LISTA configurabile (pagina + export). `…/righe/` sopra resta
    # la lettura completa e la creazione (brief-db-liste-righe-documento).
    path("<int:ordine_id>/righe/lista/", ApiOrdineRigheListaView.as_view(),
         name="vendite-ordine-righe-lista"),
    path("<int:ordine_id>/righe/lista/export/", ApiOrdineRigheListaExportView.as_view(),
         name="vendite-ordine-righe-lista-export"),
    # Le date di consegna in blocco (brief-db-date-consegna-righe-in-blocco).
    path("<int:ordine_id>/righe/date-consegna/", ApiOrdineRigheDateConsegna.as_view(),
         name="vendite-ordine-righe-date-consegna"),
    path("<int:ordine_id>/righe/preview-componenti/",
         ApiOrdineRigaPreviewComponenti.as_view(),
         name="vendite-ordine-righe-preview-componenti"),
    path("<int:ordine_id>/righe/<int:riga_id>/", ApiOrdineRigaDetail.as_view(),
         name="vendite-ordine-riga-detail"),
    # La promessa di consegna dopo la conferma: verbo dedicato, la regola e'
    # del lock delle righe (brief-db-testata-dopo-emissione, fase 1).
    path("<int:ordine_id>/righe/<int:riga_id>/data-consegna-confermata/",
         ApiOrdineRigaDataConsegnaConfermata.as_view(),
         name="vendite-ordine-riga-data-consegna-confermata"),

    # Componenti BoM
    path("<int:ordine_id>/righe/<int:riga_id>/componenti/",
         ApiOrdineRigaComponentiList.as_view(),
         name="vendite-ordine-riga-componenti-list"),
    path("<int:ordine_id>/righe/<int:riga_id>/componenti/<int:componente_id>/",
         ApiOrdineRigaComponenteDetail.as_view(),
         name="vendite-ordine-riga-componente-detail"),

    # Documenti generati (stampa PDF) — motore `documenti`, sorgente
    # ORDINE_VENDITA. Clone della catena preventivi/offerte. §12 analisi.
    path("<int:sorgente_id>/documenti/", ApiOrdineDocumentiList.as_view(),
         name="vendite-ordine-documenti-list"),
    path("<int:sorgente_id>/documenti/genera/", ApiOrdineDocumentoGenera.as_view(),
         name="vendite-ordine-documenti-genera"),
    path("<int:sorgente_id>/documenti/anteprima/", ApiOrdineDocumentoAnteprima.as_view(),
         name="vendite-ordine-documenti-anteprima"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/",
         ApiOrdineDocumentoFile.as_view(),
         name="vendite-ordine-documenti-file"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
         ApiOrdineDocumentoAllegati.as_view(),
         name="vendite-ordine-documenti-allegati"),
    path("<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
         ApiOrdineDocumentoFileDownload.as_view(),
         name="vendite-ordine-documenti-file-download"),
    # Ristampa fedele (percorso 3): versione pinnata + contesto congelato.
    path("<int:sorgente_id>/documenti/<int:documento_id>/ristampa/",
         ApiOrdineDocumentoRistampa.as_view(),
         name="vendite-ordine-documenti-ristampa"),

    # Note partizionate (target_tipo='ORDINE_VENDITA'). Building block
    # PartitionedNoteRepository: 3 righe di cablaggio + view generata.
    path("<int:ordine_id>/note/", ApiOrdineNoteList.as_view(),
         name="vendite-ordine-note-list"),
    path("<int:ordine_id>/note/<int:note_id>/", ApiOrdineNoteDetail.as_view(),
         name="vendite-ordine-note-detail"),
]
