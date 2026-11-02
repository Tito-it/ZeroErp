# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing per CRUD vendite.offerte_commerciali.
#        Perimetro 2026-05-25 (D6 completo): testata + cambio stato
#        (emetti, registra-esito, annulla) + eccezioni + utility 1:1 +
#        revisioni (crea-revisione, revisioni) + push-contratto. Step DB
#        1-9 atterrati, nessun endpoint pendente.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.legami_views import ApiOffertaLegami
from apps.vendite.api.lineage_views import ApiOffertaPassaggi
from apps.vendite.api.note_views import (
    ApiOffertaNoteDetail,
    ApiOffertaNoteList,
)
from apps.vendite.api.offerte_documenti_views import (
    ApiOffertaDocumentiList,
    ApiOffertaDocumentoAllegati,
    ApiOffertaDocumentoAnteprima,
    ApiOffertaDocumentoFile,
    ApiOffertaDocumentoFileDownload,
    ApiOffertaDocumentoRistampa,
    ApiOffertaEmetti,
)
from apps.vendite.api.views_form_defaults import ApiOffertaFormDefaults
from apps.vendite.api.views_offerte import (
    ApiOffertaIndirizzi,
    ApiOffertaIndirizzoDetail,
    ApiOffertaAnnulla,
    ApiOffertaContrattoSovrapposto,
    ApiOffertaCreaRevisione,
    ApiOffertaDetail,
    ApiOffertaEccezioneComponenteDetail,
    ApiOffertaEccezioneComponentiList,
    ApiOffertaEccezioneDetail,
    ApiOffertaEccezioni,
    ApiOffertaEccezionePreviewComponenti,
    ApiOffertaRigaErogazioni,
    ApiOffertaGeneraOrdine,
    ApiOffertaPushContratto,
    ApiOffertaRegistraEsito,
    ApiOffertaRevisioni,
    ApiOffertaRigheListaExportView,
    ApiOffertaRigheListaView,
    ApiOffertaUtility,
    ApiOffertaUtilityDetail,
    ApiOfferteExportView,
    ApiOfferteList,
)

urlpatterns = [
    # Form-defaults BA-aware: valuta_id + categoria_cliente + utility
    # contestuali al BA selezionato. Simmetrico a preventivi/contratti.
    path(
        "form-defaults/",
        ApiOffertaFormDefaults.as_view(),
        name="vendite-offerta-form-defaults",
    ),
    # Export CSV/XLSX lista configurabile (DEF-1). Prima della rotta lista ""
    # per matchare il path dedicato.
    path(
        "export/",
        ApiOfferteExportView.as_view(),
        name="vendite-offerte-export",
    ),
    # Lista + creazione testata.
    path("", ApiOfferteList.as_view(), name="vendite-offerte-list"),
    path(
        "<int:offerta_id>/",
        ApiOffertaDetail.as_view(),
        name="vendite-offerta-detail",
    ),
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage).
    path(
        "<int:offerta_id>/passaggi/",
        ApiOffertaPassaggi.as_view(),
        name="vendite-offerta-passaggi",
    ),
    # Transizioni di stato manuali.
    path(
        "<int:sorgente_id>/emetti/",
        ApiOffertaEmetti.as_view(),
        name="vendite-offerta-emetti",
    ),
    path(
        "<int:offerta_id>/indirizzi/",
        ApiOffertaIndirizzi.as_view(),
        name="vendite-offerta-indirizzi",
    ),
    path(
        "<int:offerta_id>/indirizzi/<int:indirizzo_id>/",
        ApiOffertaIndirizzoDetail.as_view(),
        name="vendite-offerta-indirizzo-detail",
    ),
    path(
        "<int:offerta_id>/registra-esito/",
        ApiOffertaRegistraEsito.as_view(),
        name="vendite-offerta-registra-esito",
    ),
    path(
        "<int:offerta_id>/annulla/",
        ApiOffertaAnnulla.as_view(),
        name="vendite-offerta-annulla",
    ),
    # I legami per la finestra di conferma dell'annullo (O-4): la revisione
    # precedente che torna emessa.
    path(
        "<int:offerta_id>/legami/",
        ApiOffertaLegami.as_view(),
        name="vendite-offerta-legami",
    ),
    # Revisioni (Step 6-7 brief DB, atterrati 2026-05-25).
    path(
        "<int:offerta_id>/crea-revisione/",
        ApiOffertaCreaRevisione.as_view(),
        name="vendite-offerta-crea-revisione",
    ),
    path(
        "<int:offerta_id>/revisioni/",
        ApiOffertaRevisioni.as_view(),
        name="vendite-offerta-revisioni-list",
    ),
    # Conversione upstream → ordine (§7.4): righe espanse via fn DB.
    path(
        "<int:offerta_id>/genera-ordine/",
        ApiOffertaGeneraOrdine.as_view(),
        name="vendite-offerta-genera-ordine",
    ),
    # Push a contratto (Step 8 brief DB, atterrato 2026-05-25).
    path(
        "<int:offerta_id>/push-contratto/",
        ApiOffertaPushContratto.as_view(),
        name="vendite-offerta-push-contratto",
    ),
    # Pre-check overlap per il dialog di successione (brief successione
    # 2026-05-31): contratto sovrapposto al push, read-only.
    path(
        "<int:offerta_id>/contratto-sovrapposto/",
        ApiOffertaContrattoSovrapposto.as_view(),
        name="vendite-offerta-contratto-sovrapposto",
    ),
    # Eccezioni.
    # La lista configurabile `vendite.offerta_righe` su un percorso suo, come
    # il contratto: `…/eccezioni/` resta eccezioni scritte + creazione.
    path("<int:offerta_id>/righe/lista/", ApiOffertaRigheListaView.as_view(),
         name="vendite-offerta-righe-lista"),
    path("<int:offerta_id>/righe/lista/export/", ApiOffertaRigheListaExportView.as_view(),
         name="vendite-offerta-righe-lista-export"),
    # Le combinazioni erogazione/fonte di una riga con l'articolo dato, col
    # default in testa: il form delle righe le legge invece di ricopiare la
    # matrice (brief-db-offerta-emissione-ed-erogazione B-R4).
    path("<int:offerta_id>/righe/erogazioni/", ApiOffertaRigaErogazioni.as_view(),
         name="vendite-offerta-righe-erogazioni"),
    path(
        "<int:offerta_id>/eccezioni/",
        ApiOffertaEccezioni.as_view(),
        name="vendite-offerta-eccezioni-list",
    ),
    path(
        "<int:offerta_id>/eccezioni/<int:eccezione_id>/",
        ApiOffertaEccezioneDetail.as_view(),
        name="vendite-offerta-eccezione-detail",
    ),
    # Componenti BoM eccezione (mirror contratti, simmetria 2026-05-26).
    path(
        "<int:offerta_id>/eccezioni/preview-componenti/",
        ApiOffertaEccezionePreviewComponenti.as_view(),
        name="vendite-offerta-eccezioni-preview-componenti",
    ),
    path(
        "<int:offerta_id>/eccezioni/<int:eccezione_id>/componenti/",
        ApiOffertaEccezioneComponentiList.as_view(),
        name="vendite-offerta-eccezione-componenti-list",
    ),
    path(
        "<int:offerta_id>/eccezioni/<int:eccezione_id>/componenti/<int:componente_id>/",
        ApiOffertaEccezioneComponenteDetail.as_view(),
        name="vendite-offerta-eccezione-componente-detail",
    ),
    # Utility 1:1.
    path(
        "<int:offerta_id>/utility/",
        ApiOffertaUtility.as_view(),
        name="vendite-offerta-utility",
    ),
    path(
        "<int:offerta_id>/utility/<int:utility_id>/",
        ApiOffertaUtilityDetail.as_view(),
        name="vendite-offerta-utility-detail",
    ),
    # Note partizionate (target_tipo='OFFERTA_COMMERCIALE'). Building block
    # PartitionedNoteRepository: 3 righe di cablaggio + view generata.
    path(
        "<int:offerta_id>/note/",
        ApiOffertaNoteList.as_view(),
        name="vendite-offerta-note-list",
    ),
    path(
        "<int:offerta_id>/note/<int:note_id>/",
        ApiOffertaNoteDetail.as_view(),
        name="vendite-offerta-note-detail",
    ),
    # Documenti generati (motore documentale). L'emissione genera+persiste
    # il documento + allegati (vedi `ApiOffertaEmetti` sopra). Qui:
    # anteprima (BOZZA), lista, download principale, lista/append allegati,
    # download file per id.
    path(
        "<int:sorgente_id>/documenti/anteprima/",
        ApiOffertaDocumentoAnteprima.as_view(),
        name="vendite-offerta-documento-anteprima",
    ),
    path(
        "<int:sorgente_id>/documenti/",
        ApiOffertaDocumentiList.as_view(),
        name="vendite-offerta-documenti-list",
    ),
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/",
        ApiOffertaDocumentoFile.as_view(),
        name="vendite-offerta-documento-file",
    ),
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
        ApiOffertaDocumentoAllegati.as_view(),
        name="vendite-offerta-documento-allegati",
    ),
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
        ApiOffertaDocumentoFileDownload.as_view(),
        name="vendite-offerta-documento-file-download",
    ),
    # Ristampa fedele (percorso 3): versione pinnata + contesto congelato.
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/ristampa/",
        ApiOffertaDocumentoRistampa.as_view(),
        name="vendite-offerta-documento-ristampa",
    ),
]
