# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Rotte del CRUD delle famiglie di documento, montate da `urls_v1.py`
#        sotto `famiglie/`. Brief: brief-be-fe-crud-registri-di-numerazione
#        §11.10.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.views_famiglie import (
    ApiFamigliaAttivo,
    ApiFamigliaDetail,
    ApiFamiglieExport,
    ApiFamiglieList,
    ApiFamiglieLookup,
    ApiFamiglieSorgenti,
)

urlpatterns = [
    path("", ApiFamiglieList.as_view(), name="vendite-famiglie-list"),
    # ⚠️ Prima delle rotte con `<int:...>`: `lookup` ed `export` sono segmenti
    #    fissi e non collidono col convertitore intero, ma l'ordine esplicito
    #    tiene il file leggibile quando le rotte cresceranno.
    path("lookup/", ApiFamiglieLookup.as_view(), name="vendite-famiglie-lookup"),
    path("export/", ApiFamiglieExport.as_view(), name="vendite-famiglie-export"),
    path("sorgenti/", ApiFamiglieSorgenti.as_view(), name="vendite-famiglie-sorgenti"),
    path(
        "<int:famiglia_id>/",
        ApiFamigliaDetail.as_view(),
        name="vendite-famiglie-detail",
    ),
    # ⭐ Verbo suo e non un PATCH su `attivo`: e' l'azione che il guard di
    #    disattivazione presidia, e che si rifa' al posto di creare una seconda
    #    famiglia sulla stessa tabella.
    path(
        "<int:famiglia_id>/attivo/",
        ApiFamigliaAttivo.as_view(),
        name="vendite-famiglie-attivo",
    ),
]
