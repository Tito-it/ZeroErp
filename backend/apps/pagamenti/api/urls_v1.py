# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 del dominio pagamenti — tutto sotto /api/v1/pagamenti/.
# Note: ⚠️ L'ORDINE conta. Le rotte piu' specifiche stanno PRIMA del pattern
#       generico `<int:contabile_id>/`, che altrimenti le intercetta.
# ------------------------------------------------------------

from django.urls import path

from apps.pagamenti.api.views import (
    ApiDistintaAnteprimaRegistrazione,
    ApiDistintaDetail,
    ApiDistintaCorreggi,
    ApiDistintaRegistra,
    ApiDistintaRighe,
    ApiDistintaRigheDaRate,
    ApiDistintaRigheExport,
    ApiDistintaStato,
    ApiContiIncasso,
    ApiDistinteList,
    ApiEccedenze,
    ApiEnteIncassoDetail,
    ApiEntiIncasso,
    ApiFatturaRateSaldo,
    ApiFatturaSistemazioni,
    ApiFatturaSistemazioniExport,
    ApiFatturaSaldo,
    ApiRataSaldo,
    ApiRateFuoriCapienza,
    ApiRateList,
    ApiRigaAbbina,
    ApiRigaDetail,
    ApiRigaRegistra,
    ApiRigaStato,
    ApiRigheCoda,
    ApiSistemazioneAnnulla,
    ApiSistemazioneConferma,
    ApiSistemazioneDetail,
    ApiSistemazioni,
)

urlpatterns = [
    # --- Distinte contabili ---
    path("distinte/", ApiDistinteList.as_view(), name="pagamenti-distinte-list"),
    # Sotto-risorse e azioni PRIMA del dettaglio generico.
    path(
        "distinte/<int:contabile_id>/righe/",
        ApiDistintaRighe.as_view(),
        name="pagamenti-distinta-righe",
    ),
    # ⭐ `export/` e' una rotta SORELLA di `righe/` (la forma della famiglia,
    #    come `fatture/<id>/sistemazioni/export/`): sotto `righe/` non c'e'
    #    nessun `<int:...>`, quindi l'ordine fra le due non decide niente.
    path(
        "distinte/<int:contabile_id>/righe/export/",
        ApiDistintaRigheExport.as_view(),
        name="pagamenti-distinta-righe-export",
    ),
    # ⭐ N rate scelte nel picker → N righe in un Salva (D19-d): verbo di
    #    collezione sulle righe della distinta, esito PARZIALE per riga.
    path(
        "distinte/<int:contabile_id>/righe/da-rate/",
        ApiDistintaRigheDaRate.as_view(),
        name="pagamenti-distinta-righe-da-rate",
    ),
    path(
        "distinte/<int:contabile_id>/stato/",
        ApiDistintaStato.as_view(),
        name="pagamenti-distinta-stato",
    ),
    path(
        "distinte/<int:contabile_id>/anteprima-registrazione/",
        ApiDistintaAnteprimaRegistrazione.as_view(),
        name="pagamenti-distinta-anteprima-registrazione",
    ),
    path(
        "distinte/<int:contabile_id>/registra/",
        ApiDistintaRegistra.as_view(),
        name="pagamenti-distinta-registra",
    ),
    # ⭐ La CORREZIONE GUIDATA (Q-7): apre una distinta nuova con le righe di
    #    segno opposto gia' compilate. ⛔ Va PRIMA della rotta di dettaglio, come
    #    tutte le sue sorelle: `distinte/<id>/` la intercetterebbe.
    path(
        "distinte/<int:contabile_id>/correggi/",
        ApiDistintaCorreggi.as_view(),
        name="pagamenti-distinta-correggi",
    ),
    path(
        "distinte/<int:contabile_id>/",
        ApiDistintaDetail.as_view(),
        name="pagamenti-distinta-detail",
    ),
    # --- Righe contabili (indirizzate per id proprio, non sotto la distinta:
    #     una riga si lavora anche dalla coda del riconciliatore, dove la
    #     distinta di appartenenza non e' il contesto) ---
    path("righe/", ApiRigheCoda.as_view(), name="pagamenti-righe-coda"),
    path(
        "righe/<int:riga_id>/abbina/",
        ApiRigaAbbina.as_view(),
        name="pagamenti-riga-abbina",
    ),
    path(
        "righe/<int:riga_id>/stato/",
        ApiRigaStato.as_view(),
        name="pagamenti-riga-stato",
    ),
    # ⭐ La registrazione TARDIVA (D20-b): «abbina e registra» una sospesa sotto
    #    una distinta gia' registrata. Verbo di dominio, ultimo segmento, stesso
    #    cancello della registrazione.
    path(
        "righe/<int:riga_id>/registra/",
        ApiRigaRegistra.as_view(),
        name="pagamenti-riga-registra",
    ),
    path("righe/<int:riga_id>/", ApiRigaDetail.as_view(), name="pagamenti-riga-detail"),
    # --- Rate ---
    # ⭐ `rate/` e' l'ELENCO delle rate col saldo (lista `pagamenti.rate`, D19-c):
    #    la sorgente del picker della distinta e dello scadenzario.
    path("rate/", ApiRateList.as_view(), name="pagamenti-rate-list"),
    # ⚠️ `fuori-capienza/` PRIMA di `<int:scadenza_id>/`, o il pattern generico
    #     se la mangia (non e' un intero, ma l'ordine e' la regola: la prossima
    #     rotta di elenco potrebbe esserlo).
    path(
        "rate/fuori-capienza/",
        ApiRateFuoriCapienza.as_view(),
        name="pagamenti-rate-fuori-capienza",
    ),
    path(
        "rate/<int:scadenza_id>/saldo/",
        ApiRataSaldo.as_view(),
        name="pagamenti-rata-saldo",
    ),
    # --- Saldi di un documento (li consumano schermate di `vendite`) ---
    path(
        "fatture/<int:fattura_id>/saldo/",
        ApiFatturaSaldo.as_view(),
        name="pagamenti-fattura-saldo",
    ),
    path(
        "fatture/<int:fattura_id>/rate/",
        ApiFatturaRateSaldo.as_view(),
        name="pagamenti-fattura-rate",
    ),
    path(
        "fatture/<int:fattura_id>/sistemazioni/",
        ApiFatturaSistemazioni.as_view(),
        name="pagamenti-fattura-sistemazioni",
    ),
    # ⭐ `export/` e' una rotta SORELLA, non una sotto-risorsa dell'atto: sotto
    #    `sistemazioni/` non c'e' nessun `<int:...>`, quindi non c'e' nemmeno un
    #    ordine da rispettare — ma la forma resta quella della famiglia.
    path(
        "fatture/<int:fattura_id>/sistemazioni/export/",
        ApiFatturaSistemazioniExport.as_view(),
        name="pagamenti-fattura-sistemazioni-export",
    ),
    # --- I canali di incasso: da dove arrivano i soldi ---
    # ⚠️ `conti-incasso/` e' una risorsa a se' e non una sotto-risorsa del
    #     canale: si consulta PRIMA di avere un canale, mentre lo si crea.
    path("conti-incasso/", ApiContiIncasso.as_view(), name="pagamenti-conti-incasso"),
    path("enti-incasso/", ApiEntiIncasso.as_view(), name="pagamenti-enti-incasso"),
    path(
        "enti-incasso/<int:ente_incasso_id>/",
        ApiEnteIncassoDetail.as_view(),
        name="pagamenti-ente-incasso-detail",
    ),
    # --- Le sistemazioni: l'elenco presenta, la persona decide, i due verbi
    #     fanno diventare la decisione un fatto (o la scartano) ---
    path("eccedenze/", ApiEccedenze.as_view(), name="pagamenti-eccedenze"),
    path("sistemazioni/", ApiSistemazioni.as_view(), name="pagamenti-sistemazioni"),
    path(
        "sistemazioni/<int:sistemazione_id>/conferma/",
        ApiSistemazioneConferma.as_view(),
        name="pagamenti-sistemazione-conferma",
    ),
    path(
        "sistemazioni/<int:sistemazione_id>/annulla/",
        ApiSistemazioneAnnulla.as_view(),
        name="pagamenti-sistemazione-annulla",
    ),
    path(
        "sistemazioni/<int:sistemazione_id>/",
        ApiSistemazioneDetail.as_view(),
        name="pagamenti-sistemazione-detail",
    ),
]
