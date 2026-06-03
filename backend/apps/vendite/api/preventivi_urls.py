# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL patterns per preventivi vendita (/api/v1/vendite/preventivi/).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.note_views import (
    ApiPreventivoNoteDetail,
    ApiPreventivoNoteList,
)
from apps.vendite.api.preventivi_documenti_views import (
    ApiPreventivoDocumentiList,
    ApiPreventivoDocumentoAllegati,
    ApiPreventivoDocumentoAnteprima,
    ApiPreventivoDocumentoFile,
    ApiPreventivoDocumentoGenera,
    ApiPreventivoEmetti,
)
from apps.vendite.api.preventivi_views import (
    ApiPreventiviExportView,
    ApiPreventiviList,
    ApiPreventivoContestoPricing,
    ApiPreventivoDetail,
    ApiPreventivoGeneraPratica,
    ApiPreventivoIndirizzi,
    ApiPreventivoPratiche,
    ApiPreventivoPushCommessa,
    ApiPreventivoRevisione,
    ApiPreventivoRevisioniList,
    ApiPreventivoRiepilogoIva,
    ApiPreventivoRigaComponenteDetail,
    ApiPreventivoRigaComponentiList,
    ApiPreventivoRigaDetail,
    ApiPreventivoRigaPreviewComponenti,
    ApiPreventivoRigaSuggerisciPrezzo,
    ApiPreventivoRigheList,
    ApiPreventivoStato,
    ApiPreventivoStatoFatturazione,
)
from apps.vendite.api.views_form_defaults import ApiPreventivoFormDefaults

urlpatterns = [
    # Form-defaults BA-aware (Fase 2.B4 refactor frontend vendite).
    # Risolve valuta/termini/iva dal cliente del BA + validita_al da parameter.
    path(
        "form-defaults/",
        ApiPreventivoFormDefaults.as_view(),
        name="vendite-preventivi-form-defaults",
    ),
    # Export CSV/XLSX lista configurabile (DEF-1). Prima della rotta lista ""
    # per matchare il path dedicato.
    path(
        "export/",
        ApiPreventiviExportView.as_view(),
        name="vendite-preventivi-export",
    ),
    # Testata: lista + creazione
    path("", ApiPreventiviList.as_view(), name="vendite-preventivi-list"),
    # Testata: dettaglio + aggiornamento
    path(
        "<int:preventivo_id>/",
        ApiPreventivoDetail.as_view(),
        name="vendite-preventivi-detail",
    ),
    # Cambio stato
    path(
        "<int:preventivo_id>/stato/",
        ApiPreventivoStato.as_view(),
        name="vendite-preventivi-stato",
    ),
    # Emissione BOZZA->EMESSO (multipart): orchestra stato + genera doc +
    # allegati in transazione atomica. Mirror di vendite-offerta-emetti.
    path(
        "<int:preventivo_id>/emetti/",
        ApiPreventivoEmetti.as_view(),
        name="vendite-preventivi-emetti",
    ),
    # Revisione
    path(
        "<int:preventivo_id>/revisione/",
        ApiPreventivoRevisione.as_view(),
        name="vendite-preventivi-revisione",
    ),
    # Lista catena revisioni (GET): tutte le revisioni con stesso `numero`
    # ordinate per `rev` ASC. Mirror endpoint offerte `/revisioni/`.
    path(
        "<int:preventivo_id>/revisioni/",
        ApiPreventivoRevisioniList.as_view(),
        name="vendite-preventivi-revisioni-list",
    ),
    # Righe: lista + creazione
    path(
        "<int:preventivo_id>/righe/",
        ApiPreventivoRigheList.as_view(),
        name="vendite-preventivi-righe-list",
    ),
    # Righe: aggiornamento + eliminazione
    path(
        "<int:preventivo_id>/righe/<int:riga_id>/",
        ApiPreventivoRigaDetail.as_view(),
        name="vendite-preventivi-righe-detail",
    ),
    # Righe: suggerimento prezzo via pricing resolver v5
    path(
        "<int:preventivo_id>/righe/suggerisci-prezzo/",
        ApiPreventivoRigaSuggerisciPrezzo.as_view(),
        name="vendite-preventivi-righe-suggerisci-prezzo",
    ),
    # Componenti BoM CASO A nidificati sotto la riga padre (refactor 2026-05-11)
    # Preview componenti pre-save (form atomic 2026-05-12)
    path(
        "<int:preventivo_id>/righe/preview-componenti/",
        ApiPreventivoRigaPreviewComponenti.as_view(),
        name="vendite-preventivi-righe-preview-componenti",
    ),
    path(
        "<int:preventivo_id>/righe/<int:riga_id>/componenti/",
        ApiPreventivoRigaComponentiList.as_view(),
        name="vendite-preventivi-riga-componenti-list",
    ),
    path(
        "<int:preventivo_id>/righe/<int:riga_id>/componenti/<int:componente_id>/",
        ApiPreventivoRigaComponenteDetail.as_view(),
        name="vendite-preventivi-riga-componente-detail",
    ),
    # Riepilogo IVA aggregato (regola fiscale art. 21 DPR 633/72)
    path(
        "<int:preventivo_id>/riepilogo-iva/",
        ApiPreventivoRiepilogoIva.as_view(),
        name="vendite-preventivi-riepilogo-iva",
    ),
    # Contesto pricing (audit visivo header drawer): contratto attivo o
    # listino categoria fallback applicato dal resolver al preventivo.
    path(
        "<int:preventivo_id>/contesto-pricing/",
        ApiPreventivoContestoPricing.as_view(),
        name="vendite-preventivi-contesto-pricing",
    ),
    # Indirizzi
    path(
        "<int:preventivo_id>/indirizzi/",
        ApiPreventivoIndirizzi.as_view(),
        name="vendite-preventivi-indirizzi",
    ),
    # Integrazione: push commessa
    path(
        "<int:preventivo_id>/push-commessa/",
        ApiPreventivoPushCommessa.as_view(),
        name="vendite-preventivi-push-commessa",
    ),
    # Integrazione: stato fatturazione
    path(
        "<int:preventivo_id>/stato-fatturazione/",
        ApiPreventivoStatoFatturazione.as_view(),
        name="vendite-preventivi-stato-fatturazione",
    ),
    # Integrazione: genera pratica
    path(
        "<int:preventivo_id>/genera-pratica/",
        ApiPreventivoGeneraPratica.as_view(),
        name="vendite-preventivi-genera-pratica",
    ),
    # Integrazione: pratiche collegate
    path(
        "<int:preventivo_id>/pratiche/",
        ApiPreventivoPratiche.as_view(),
        name="vendite-preventivi-pratiche",
    ),
    # Documenti generati (Tranche K motore documentale parametrico)
    path(
        "<int:preventivo_id>/documenti/",
        ApiPreventivoDocumentiList.as_view(),
        name="vendite-preventivi-documenti-list",
    ),
    path(
        "<int:preventivo_id>/documenti/genera/",
        ApiPreventivoDocumentoGenera.as_view(),
        name="vendite-preventivi-documenti-genera",
    ),
    path(
        "<int:preventivo_id>/documenti/anteprima/",
        ApiPreventivoDocumentoAnteprima.as_view(),
        name="vendite-preventivi-documenti-anteprima",
    ),
    path(
        "<int:preventivo_id>/documenti/<int:documento_id>/file/",
        ApiPreventivoDocumentoFile.as_view(),
        name="vendite-preventivi-documenti-file",
    ),
    # Lista (GET) + append (POST multipart) dei file del documento (principale
    # + allegati). Mirror di vendite-offerta-documento-allegati: usato dal
    # row-expand di DocumentiGeneratiSorgenteList per popolare filesPerDoc.
    path(
        "<int:preventivo_id>/documenti/<int:documento_id>/allegati/",
        ApiPreventivoDocumentoAllegati.as_view(),
        name="vendite-preventivi-documenti-allegati",
    ),
    # Note partizionate (vendite.note_preventivo) — testata o riga.
    # GET ?target_riga_id=<rid> per filtrare le note della singola riga.
    # POST body con target_riga_id per nota di riga.
    path(
        "<int:preventivo_id>/note/",
        ApiPreventivoNoteList.as_view(),
        name="vendite-preventivi-note-list",
    ),
    path(
        "<int:preventivo_id>/note/<int:note_id>/",
        ApiPreventivoNoteDetail.as_view(),
        name="vendite-preventivi-note-detail",
    ),
]
