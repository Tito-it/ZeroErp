# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
    ApiDistintaRegistra,
    ApiDistintaRighe,
    ApiDistintaStato,
    ApiDistinteList,
    ApiFatturaRateSaldo,
    ApiFatturaSaldo,
    ApiRataSaldo,
    ApiRateFuoriCapienza,
    ApiRigaAbbina,
    ApiRigaDetail,
    ApiRigaStato,
    ApiRigheCoda,
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
    path("righe/<int:riga_id>/", ApiRigaDetail.as_view(), name="pagamenti-riga-detail"),
    # --- Rate ---
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
]
