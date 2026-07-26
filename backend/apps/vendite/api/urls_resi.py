# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API resi di vendita (CRUD testata + righe, conferma/annullo,
#        DDT di ri-consegna, code di lavoro). Clone ridotto di urls_ddt.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.lineage_views import ApiResoPassaggi
from apps.vendite.api.views_resi import (
    ApiResiDaAccreditare,
    ApiResiDaAccreditareExport,
    ApiResiDaRiconsegnare,
    ApiResiDaRiconsegnareExport,
    ApiResiExport,
    ApiResiList,
    ApiResoAnnulla,
    ApiResoChiudiRiconsegna,
    ApiResoConferma,
    ApiResoDetail,
    ApiResoGeneraDdtRiconsegna,
    ApiResoRiapriRiconsegna,
    ApiResoRigaDetail,
    ApiResoRighe,
)

urlpatterns = [
    # Lista + create (reso da DDT)
    path("", ApiResiList.as_view(), name="vendite-resi-list"),

    # Export lista (DEF-1). Prima di `<int:reso_id>/` per non collidere.
    path("export/", ApiResiExport.as_view(), name="vendite-resi-export"),

    # Code di lavoro (viste dedicate). Prima di `<int:reso_id>/` per non
    # collidere con il path del dettaglio.
    path("da-accreditare/", ApiResiDaAccreditare.as_view(),
         name="vendite-resi-da-accreditare"),
    path("da-accreditare/export/", ApiResiDaAccreditareExport.as_view(),
         name="vendite-resi-da-accreditare-export"),
    path("da-riconsegnare/", ApiResiDaRiconsegnare.as_view(),
         name="vendite-resi-da-riconsegnare"),
    path("da-riconsegnare/export/", ApiResiDaRiconsegnareExport.as_view(),
         name="vendite-resi-da-riconsegnare-export"),

    path("<int:reso_id>/", ApiResoDetail.as_view(), name="vendite-resi-detail"),
    # Genealogia/lineage (pannello "Passaggi", brief-be-fe-lineage): per il
    # reso la catena significativa e' l'origine (reso <- DDT <- ordine <- ...).
    path("<int:reso_id>/passaggi/", ApiResoPassaggi.as_view(),
         name="vendite-resi-passaggi"),

    # Azioni di dominio (fn madri DB): niente cambia-stato generico — conferma
    # e annullo hanno effetti (residuo/proiezioni/flip DDT).
    path("<int:reso_id>/conferma/", ApiResoConferma.as_view(),
         name="vendite-resi-conferma"),
    path("<int:reso_id>/annulla/", ApiResoAnnulla.as_view(),
         name="vendite-resi-annulla"),
    path("<int:reso_id>/genera-ddt-riconsegna/",
         ApiResoGeneraDdtRiconsegna.as_view(),
         name="vendite-resi-genera-ddt-riconsegna"),
    # Le due uscite della stessa copertura: ri-spedisci (sopra) oppure dichiara
    # definitivo (qui). La riapertura e' il rimedio a una chiusura errata.
    path("<int:reso_id>/chiudi-riconsegna/",
         ApiResoChiudiRiconsegna.as_view(),
         name="vendite-resi-chiudi-riconsegna"),
    path("<int:reso_id>/riapri-riconsegna/",
         ApiResoRiapriRiconsegna.as_view(),
         name="vendite-resi-riapri-riconsegna"),

    # Righe
    path("<int:reso_id>/righe/", ApiResoRighe.as_view(),
         name="vendite-resi-righe-list"),
    path("<int:reso_id>/righe/<int:riga_id>/", ApiResoRigaDetail.as_view(),
         name="vendite-resi-riga-detail"),
]
