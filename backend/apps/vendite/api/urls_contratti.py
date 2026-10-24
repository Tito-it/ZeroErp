# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing per CRUD contratti v5 (F2-BE-06).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.contratti_documenti_views import (
    ApiContrattoDocumentiList,
    ApiContrattoDocumentoAllegati,
    ApiContrattoDocumentoAnteprima,
    ApiContrattoDocumentoFile,
    ApiContrattoDocumentoFileDownload,
    ApiContrattoDocumentoRistampa,
    ApiContrattoDocumentoGenera,
    ApiContrattoEmetti,
)
from apps.vendite.api.legami_views import ApiContrattoLegami
from apps.vendite.api.lineage_views import ApiContrattoPassaggi
from apps.vendite.api.note_views import (
    ApiContrattoNoteDetail,
    ApiContrattoNoteList,
)
from apps.vendite.api.views_contratti import (
    ApiContrattoIndirizzi,
    ApiContrattoIndirizzoDetail,
    ApiContrattiExportView,
    ApiContrattiList,
    ApiContrattoCambiaStato,
    ApiContrattoContestoPricing,
    ApiContrattoDetail,
    ApiContrattoRigaComponenteDetail,
    ApiContrattoRigaComponentiList,
    ApiContrattoRigaDetail,
    ApiContrattoRigaErogazioni,
    ApiContrattoRigaPreviewComponenti,
    ApiContrattoRigheList,
    ApiContrattoRigheListaExportView,
    ApiContrattoRigheListaView,
    ApiContrattoUtility,
)
from apps.vendite.api.views_form_defaults import ApiContrattoFormDefaults

urlpatterns = [
    # Form-defaults BA-aware (Fase 2.B3 refactor frontend vendite).
    # Risolve categoria_cliente_id_snapshot/utility/istanza dal BA + default
    # data/valido_dal da parameter (lead_gg).
    path(
        "form-defaults/",
        ApiContrattoFormDefaults.as_view(),
        name="vendite-contratto-form-defaults",
    ),
    path("", ApiContrattiList.as_view(), name="vendite-contratti-list"),
    # Export CSV/Excel (DEF-1) — colonne coerenti con la lista configurabile.
    path("export/", ApiContrattiExportView.as_view(), name="vendite-contratti-export"),
    path("<int:contratto_id>/", ApiContrattoDetail.as_view(), name="vendite-contratto-detail"),
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage).
    path("<int:contratto_id>/passaggi/", ApiContrattoPassaggi.as_view(),
         name="vendite-contratto-passaggi"),
    # I legami del contratto, per la conferma dell'annullo (legami_views).
    path("<int:contratto_id>/legami/", ApiContrattoLegami.as_view(),
         name="vendite-contratto-legami"),
    path("<int:contratto_id>/indirizzi/", ApiContrattoIndirizzi.as_view(),
         name="vendite-contratto-indirizzi"),
    path("<int:contratto_id>/indirizzi/<int:indirizzo_id>/",
         ApiContrattoIndirizzoDetail.as_view(),
         name="vendite-contratto-indirizzo-detail"),
    path(
        "<int:contratto_id>/cambia-stato/",
        ApiContrattoCambiaStato.as_view(),
        name="vendite-contratto-cambia-stato",
    ),
    # Attivazione DRAFT->ATTIVO (multipart): orchestra stato + genera doc +
    # allegati in transazione atomica. Mirror di vendite-offerta-emetti e
    # vendite-preventivi-emetti.
    path(
        "<int:sorgente_id>/emetti/",
        ApiContrattoEmetti.as_view(),
        name="vendite-contratto-emetti",
    ),
    path(
        "<int:contratto_id>/righe/",
        ApiContrattoRigheList.as_view(),
        name="vendite-contratto-righe-list",
    ),
    # La lista configurabile `vendite.contratto_righe` su un percorso suo, come
    # i documenti gemelli: `…/righe/` resta righe persistite + creazione.
    path("<int:contratto_id>/righe/lista/", ApiContrattoRigheListaView.as_view(),
         name="vendite-contratto-righe-lista"),
    path("<int:contratto_id>/righe/lista/export/", ApiContrattoRigheListaExportView.as_view(),
         name="vendite-contratto-righe-lista-export"),
    # Le combinazioni erogazione/fonte di una riga con l'articolo dato, col
    # default in testa: il form delle righe le legge invece di ricopiare la
    # matrice (brief-db-offerta-emissione-ed-erogazione B-R4).
    path("<int:contratto_id>/righe/erogazioni/", ApiContrattoRigaErogazioni.as_view(),
         name="vendite-contratto-righe-erogazioni"),
    path(
        "<int:contratto_id>/contesto-pricing/",
        ApiContrattoContestoPricing.as_view(),
        name="vendite-contratto-contesto-pricing",
    ),
    path(
        "<int:contratto_id>/righe/<int:riga_id>/",
        ApiContrattoRigaDetail.as_view(),
        name="vendite-contratto-riga-detail",
    ),
    # Componenti BoM (modello unificato 2026-05-13) nidificati sotto riga.
    path(
        "<int:contratto_id>/righe/preview-componenti/",
        ApiContrattoRigaPreviewComponenti.as_view(),
        name="vendite-contratto-righe-preview-componenti",
    ),
    path(
        "<int:contratto_id>/righe/<int:riga_id>/componenti/",
        ApiContrattoRigaComponentiList.as_view(),
        name="vendite-contratto-riga-componenti-list",
    ),
    path(
        "<int:contratto_id>/righe/<int:riga_id>/componenti/<int:componente_id>/",
        ApiContrattoRigaComponenteDetail.as_view(),
        name="vendite-contratto-riga-componente-detail",
    ),
    path(
        "<int:contratto_id>/utility/",
        ApiContrattoUtility.as_view(),
        name="vendite-contratto-utility",
    ),
    # Documenti generati dal contratto.
    path(
        "<int:sorgente_id>/documenti/",
        ApiContrattoDocumentiList.as_view(),
        name="vendite-contratti-documenti-list",
    ),
    path(
        "<int:sorgente_id>/documenti/genera/",
        ApiContrattoDocumentoGenera.as_view(),
        name="vendite-contratti-documenti-genera",
    ),
    path(
        "<int:sorgente_id>/documenti/anteprima/",
        ApiContrattoDocumentoAnteprima.as_view(),
        name="vendite-contratti-documenti-anteprima",
    ),
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/",
        ApiContrattoDocumentoFile.as_view(),
        name="vendite-contratti-documenti-file",
    ),
    # Lista (GET) + append (POST multipart) dei file del documento
    # (principale + allegati). Usato dal row-expand di
    # DocumentiGeneratiSorgenteList per popolare filesPerDoc.
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
        ApiContrattoDocumentoAllegati.as_view(),
        name="vendite-contratti-documenti-allegati",
    ),
    # Download di uno specifico file (principale o allegato) per id. Colma il
    # gap latente della famiglia: il row-expand di DocumentiGeneratiSorgenteList
    # chiama downloadFile(file_id) per QUALSIASI sorgente (prima 404).
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
        ApiContrattoDocumentoFileDownload.as_view(),
        name="vendite-contratti-documenti-file-download",
    ),
    # Ristampa fedele (percorso 3): versione pinnata + contesto congelato.
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/ristampa/",
        ApiContrattoDocumentoRistampa.as_view(),
        name="vendite-contratti-documenti-ristampa",
    ),
    # Note partizionate (vendite.note_contratto) — testata o riga.
    # GET ?target_riga_id=<rid> per filtrare le note della singola riga.
    # POST body con target_riga_id per nota di riga.
    path(
        "<int:contratto_id>/note/",
        ApiContrattoNoteList.as_view(),
        name="vendite-contratto-note-list",
    ),
    path(
        "<int:contratto_id>/note/<int:note_id>/",
        ApiContrattoNoteDetail.as_view(),
        name="vendite-contratto-note-detail",
    ),
]
