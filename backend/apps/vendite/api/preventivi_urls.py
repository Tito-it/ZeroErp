# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL patterns per preventivi vendita (/api/v1/vendite/preventivi/).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.legami_views import ApiPreventivoLegami
from apps.vendite.api.lineage_views import ApiPreventivoPassaggi
from apps.vendite.api.note_views import (
    ApiPreventivoNoteDetail,
    ApiPreventivoNoteList,
)
from apps.vendite.api.preventivi_documenti_views import (
    ApiPreventivoDocumentiList,
    ApiPreventivoDocumentoAllegati,
    ApiPreventivoDocumentoAnteprima,
    ApiPreventivoDocumentoFile,
    ApiPreventivoDocumentoFileDownload,
    ApiPreventivoDocumentoRistampa,
    ApiPreventivoDocumentoGenera,
    ApiPreventivoEmetti,
)
from apps.vendite.api.preventivi_views import (
    ApiPreventiviExportView,
    ApiPreventiviList,
    ApiPreventivoContestoPricing,
    ApiPreventivoDetail,
    ApiPreventivoCollegaPratica,
    ApiPreventivoGeneraOrdine,
    ApiPreventivoRigheSmistabiliOrdine,
    ApiPreventivoGeneraPratica,
    ApiPreventivoIndirizzi,
    ApiPreventivoIndirizzoDetail,
    ApiPreventivoPushCommessa,
    ApiPreventivoRevisione,
    ApiPreventivoRevisioniList,
    ApiPreventivoRootPerFlusso,
    ApiPreventivoRootPerPratica,
    ApiPreventivoRiepilogoIva,
    ApiPreventivoRigaComponenteDetail,
    ApiPreventivoRigaComponentiList,
    ApiPreventivoRigaDetail,
    ApiPreventivoRigaPreviewComponenti,
    ApiPreventivoRigaSuggerisciPrezzo,
    ApiPreventivoRigheDateConsegna,
    ApiPreventivoRigheList,
    ApiPreventivoRigheListaExportView,
    ApiPreventivoRigheListaView,
    ApiPreventivoStato,
    ApiPreventivoStatoDaPratica,
    ApiPreventivoCompletaSmistamento,
    ApiPreventivoSmistamento,
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
    # Riapertura pratica-first: risolve il preventivo ROOT agganciato a un flusso.
    # Prima della rotta lista "" per matchare il path dedicato.
    path(
        "root-per-flusso/",
        ApiPreventivoRootPerFlusso.as_view(),
        name="vendite-preventivi-root-per-flusso",
    ),
    # Step a valle del percorso (es. SMISTAMENTO): risolve il ROOT della pratica.
    path(
        "root-per-pratica/",
        ApiPreventivoRootPerPratica.as_view(),
        name="vendite-preventivi-root-per-pratica",
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
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage).
    path(
        "<int:preventivo_id>/passaggi/",
        ApiPreventivoPassaggi.as_view(),
        name="vendite-preventivi-passaggi",
    ),
    # I legami del preventivo, per la conferma dell'annullo (legami_views).
    path(
        "<int:preventivo_id>/legami/",
        ApiPreventivoLegami.as_view(),
        name="vendite-preventivi-legami",
    ),
    # Cambio stato
    path(
        "<int:preventivo_id>/stato/",
        ApiPreventivoStato.as_view(),
        name="vendite-preventivi-stato",
    ),
    # GUIDA (D4): cambio stato del preventivo ROOT risolto dalla pratica —
    # «Accetta/Rifiuta» in-pratica (inversione handler→proiezione). Segmento
    # testuale "da-pratica" (no conflitto col converter <int>).
    path(
        "da-pratica/<int:pratica_id>/stato/",
        ApiPreventivoStatoDaPratica.as_view(),
        name="vendite-preventivi-stato-da-pratica",
    ),
    # Emissione BOZZA->EMESSO (multipart): orchestra stato + genera doc +
    # allegati in transazione atomica. Mirror di vendite-offerta-emetti.
    path(
        "<int:sorgente_id>/emetti/",
        ApiPreventivoEmetti.as_view(),
        name="vendite-preventivi-emetti",
    ),
    # Smistamento MERCE → ordine (modello split D8)
    path(
        "<int:preventivo_id>/righe-smistabili-ordine/",
        ApiPreventivoRigheSmistabiliOrdine.as_view(),
        name="vendite-preventivi-righe-smistabili-ordine",
    ),
    path(
        "<int:preventivo_id>/genera-ordine/",
        ApiPreventivoGeneraOrdine.as_view(),
        name="vendite-preventivi-genera-ordine",
    ),
    # PREVENTIVAZIONE: aggancia il preventivo come ROOT a una pratica
    path(
        "<int:preventivo_id>/collega-pratica/",
        ApiPreventivoCollegaPratica.as_view(),
        name="vendite-preventivi-collega-pratica",
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
    # Righe: la LISTA configurabile (pagina + export). `…/righe/` sopra resta
    # la lettura completa e la creazione (brief-db-liste-righe-documento).
    path("<int:preventivo_id>/righe/lista/", ApiPreventivoRigheListaView.as_view(),
         name="vendite-preventivi-righe-lista"),
    path("<int:preventivo_id>/righe/lista/export/", ApiPreventivoRigheListaExportView.as_view(),
         name="vendite-preventivi-righe-lista-export"),
    # Righe: aggiornamento + eliminazione
    path(
        "<int:preventivo_id>/righe/<int:riga_id>/",
        ApiPreventivoRigaDetail.as_view(),
        name="vendite-preventivi-righe-detail",
    ),
    # Righe: le date di consegna in blocco (brief-db-date-consegna-righe-in-blocco)
    path(
        "<int:preventivo_id>/righe/date-consegna/",
        ApiPreventivoRigheDateConsegna.as_view(),
        name="vendite-preventivi-righe-date-consegna",
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
    path(
        "<int:preventivo_id>/indirizzi/<int:indirizzo_id>/",
        ApiPreventivoIndirizzoDetail.as_view(),
        name="vendite-preventivi-indirizzo-detail",
    ),
    # Integrazione: push commessa
    path(
        "<int:preventivo_id>/push-commessa/",
        ApiPreventivoPushCommessa.as_view(),
        name="vendite-preventivi-push-commessa",
    ),
    # Integrazione: smistamento (Pannello Smistamento — aggregato + righe)
    path(
        "<int:preventivo_id>/smistamento/",
        ApiPreventivoSmistamento.as_view(),
        name="vendite-preventivi-smistamento",
    ),
    # Integrazione: completa SMISTAMENTO (esito di ramo calcolato dal dominio)
    path(
        "<int:preventivo_id>/completa-smistamento/",
        ApiPreventivoCompletaSmistamento.as_view(),
        name="vendite-preventivi-completa-smistamento",
    ),
    # Integrazione: genera pratica
    path(
        "<int:preventivo_id>/genera-pratica/",
        ApiPreventivoGeneraPratica.as_view(),
        name="vendite-preventivi-genera-pratica",
    ),
    # Documenti generati (Tranche K motore documentale parametrico)
    path(
        "<int:sorgente_id>/documenti/",
        ApiPreventivoDocumentiList.as_view(),
        name="vendite-preventivi-documenti-list",
    ),
    path(
        "<int:sorgente_id>/documenti/genera/",
        ApiPreventivoDocumentoGenera.as_view(),
        name="vendite-preventivi-documenti-genera",
    ),
    path(
        "<int:sorgente_id>/documenti/anteprima/",
        ApiPreventivoDocumentoAnteprima.as_view(),
        name="vendite-preventivi-documenti-anteprima",
    ),
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/",
        ApiPreventivoDocumentoFile.as_view(),
        name="vendite-preventivi-documenti-file",
    ),
    # Lista (GET) + append (POST multipart) dei file del documento (principale
    # + allegati). Mirror di vendite-offerta-documento-allegati: usato dal
    # row-expand di DocumentiGeneratiSorgenteList per popolare filesPerDoc.
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/allegati/",
        ApiPreventivoDocumentoAllegati.as_view(),
        name="vendite-preventivi-documenti-allegati",
    ),
    # Download di uno specifico file (principale o allegato) per id. Colma il
    # gap latente della famiglia: il row-expand di DocumentiGeneratiSorgenteList
    # chiama downloadFile(file_id) per QUALSIASI sorgente (prima 404).
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/file/<int:file_id>/",
        ApiPreventivoDocumentoFileDownload.as_view(),
        name="vendite-preventivi-documenti-file-download",
    ),
    # Ristampa fedele (percorso 3): ri-renderizza l'originale dalla versione
    # pinnata + contesto congelato. Non emette nulla di nuovo.
    path(
        "<int:sorgente_id>/documenti/<int:documento_id>/ristampa/",
        ApiPreventivoDocumentoRistampa.as_view(),
        name="vendite-preventivi-documenti-ristampa",
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
