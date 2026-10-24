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
    ApiResiAccrediti,
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
    ApiResoRientri,
    ApiResoRigaRientri,
    ApiResoRigaRientroDetail,
    ApiResoRigaAnnullaAccredito,
    ApiResoRigaDetail,
    ApiResoRighe,
    ApiResoRigheListaExportView,
    ApiResoRigheListaView,
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

    # Verbo dell'accredito: MASSIVO dal primo giorno (D-NC-7), un endpoint solo
    # e la riga singola e' una lista di uno. Prima di `<int:reso_id>/` per non
    # collidere con il path del dettaglio.
    path("accrediti/", ApiResiAccrediti.as_view(),
         name="vendite-resi-accrediti"),

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
    # Righe: la LISTA configurabile (pagina + export). `…/righe/` sopra resta
    # la lettura completa e la creazione (brief-db-liste-righe-documento).
    path("<int:reso_id>/righe/lista/", ApiResoRigheListaView.as_view(),
         name="vendite-resi-righe-lista"),
    path("<int:reso_id>/righe/lista/export/", ApiResoRigheListaExportView.as_view(),
         name="vendite-resi-righe-lista-export"),
    path("<int:reso_id>/righe/<int:riga_id>/", ApiResoRigaDetail.as_view(),
         name="vendite-resi-riga-detail"),
    # Annullo dell'accredito (D-NC-11): sta A MONTE del documento ed e' un'altra
    # cosa dal reset di lotto, che invece RIGENERA la nota al giro dopo.
    path("<int:reso_id>/righe/<int:riga_id>/annulla-accredito/",
         ApiResoRigaAnnullaAccredito.as_view(),
         name="vendite-resi-riga-annulla-accredito"),
    # Rientri (3-bis R-1b): la situazione del reso, e il CRUD sotto la riga.
    path("<int:reso_id>/rientri/", ApiResoRientri.as_view(),
         name="vendite-resi-rientri"),
    path("<int:reso_id>/righe/<int:riga_id>/rientri/", ApiResoRigaRientri.as_view(),
         name="vendite-resi-riga-rientri"),
    path("<int:reso_id>/righe/<int:riga_id>/rientri/<int:rientro_id>/",
         ApiResoRigaRientroDetail.as_view(),
         name="vendite-resi-riga-rientro-detail"),
]
