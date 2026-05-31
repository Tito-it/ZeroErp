# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing per CRUD vendite.offerte_commerciali.
#        Perimetro 2026-05-25 (D6 completo): testata + cambio stato
#        (emetti, registra-esito, annulla) + eccezioni + utility 1:1 +
#        revisioni (crea-revisione, revisioni) + push-contratto. Step DB
#        1-9 atterrati, nessun endpoint pendente.
# ------------------------------------------------------------

from django.urls import path

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
    ApiOffertaEmetti,
)
from apps.vendite.api.views_form_defaults import ApiOffertaFormDefaults
from apps.vendite.api.views_offerte import (
    ApiOffertaAnnulla,
    ApiOffertaContrattoSovrapposto,
    ApiOffertaCreaRevisione,
    ApiOffertaDetail,
    ApiOffertaEccezioneComponenteDetail,
    ApiOffertaEccezioneComponentiList,
    ApiOffertaEccezioneDetail,
    ApiOffertaEccezioni,
    ApiOffertaEccezionePreviewComponenti,
    ApiOffertaPushContratto,
    ApiOffertaRegistraEsito,
    ApiOffertaRevisioni,
    ApiOffertaUtility,
    ApiOffertaUtilityDetail,
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
    # Lista + creazione testata.
    path("", ApiOfferteList.as_view(), name="vendite-offerte-list"),
    path(
        "<int:offerta_id>/",
        ApiOffertaDetail.as_view(),
        name="vendite-offerta-detail",
    ),
    # Transizioni di stato manuali.
    path(
        "<int:offerta_id>/emetti/",
        ApiOffertaEmetti.as_view(),
        name="vendite-offerta-emetti",
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
    # Note partizionate (target_tipo='OFFERTA'). Building block
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
        "<int:offerta_id>/documenti/anteprima/",
        ApiOffertaDocumentoAnteprima.as_view(),
        name="vendite-offerta-documento-anteprima",
    ),
    path(
        "<int:offerta_id>/documenti/",
        ApiOffertaDocumentiList.as_view(),
        name="vendite-offerta-documenti-list",
    ),
    path(
        "<int:offerta_id>/documenti/<int:documento_id>/file/",
        ApiOffertaDocumentoFile.as_view(),
        name="vendite-offerta-documento-file",
    ),
    path(
        "<int:offerta_id>/documenti/<int:documento_id>/allegati/",
        ApiOffertaDocumentoAllegati.as_view(),
        name="vendite-offerta-documento-allegati",
    ),
    path(
        "<int:offerta_id>/documenti/<int:documento_id>/file/<int:file_id>/",
        ApiOffertaDocumentoFileDownload.as_view(),
        name="vendite-offerta-documento-file-download",
    ),
]
