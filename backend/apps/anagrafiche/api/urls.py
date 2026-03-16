from django.urls import path

from apps.anagrafiche.api.views_codici_postali import CodiciPostaliDetailView, CodiciPostaliView
from apps.anagrafiche.api.views_comuni import ComuniView
from apps.anagrafiche.api.views_indirizzi import IndirizziDetailView, IndirizziView
from apps.anagrafiche.api.views_province import ProvinceDetailView, ProvinceLookupView, ProvinceView
from apps.anagrafiche.api.views_regioni import RegioniDetailView, RegioniLookupView, RegioniView
from apps.anagrafiche.api.views_soggetti import (
    SoggettiContattiDetailView,
    SoggettiContattiView,
    SoggettiDetailView,
    SoggettiIndirizziView,
    SoggettiRuoliView,
    SoggettiView,
)
from apps.anagrafiche.api.views_stati import StatiDetailView, StatiLookupView, StatiView
from apps.anagrafiche.api.views_toponomastica import ToponomasticaDetailView, ToponomasticaView

urlpatterns = [
    # Soggetti
    path("soggetti/", SoggettiView.as_view(), name="anagrafiche-soggetti-list"),
    path("soggetti/<str:soggetto_id>/", SoggettiDetailView.as_view(), name="anagrafiche-soggetti-detail"),
    path("soggetti/<str:soggetto_id>/contatti/", SoggettiContattiView.as_view(), name="anagrafiche-soggetti-contatti"),
    path("soggetti/<str:soggetto_id>/contatti/<int:contatto_id>/", SoggettiContattiDetailView.as_view(), name="anagrafiche-soggetti-contatti-detail"),
    path("soggetti/<str:soggetto_id>/indirizzi/", SoggettiIndirizziView.as_view(), name="anagrafiche-soggetti-indirizzi"),
    path("soggetti/<str:soggetto_id>/ruoli/", SoggettiRuoliView.as_view(), name="anagrafiche-soggetti-ruoli"),
    # Indirizzi dettaglio
    path("indirizzi/", IndirizziView.as_view(), name="anagrafiche-indirizzi-list"),
    path("indirizzi/<int:pk>/", IndirizziDetailView.as_view(), name="anagrafiche-indirizzi-detail"),
    # Codici postali
    path("codici-postali/", CodiciPostaliView.as_view(), name="anagrafiche-codici-postali-list"),
    path("codici-postali/<int:pk>/", CodiciPostaliDetailView.as_view(), name="anagrafiche-codici-postali-detail"),
    # Toponomastica
    path("toponomastica/", ToponomasticaView.as_view(), name="anagrafiche-toponomastica-list"),
    path("toponomastica/<int:pk>/", ToponomasticaDetailView.as_view(), name="anagrafiche-toponomastica-detail"),
    # Comuni
    path("comuni/", ComuniView.as_view(), name="anagrafiche-comuni-list"),
    # Province
    path("province/", ProvinceView.as_view(), name="anagrafiche-province-list"),
    path("province/<int:pk>/", ProvinceDetailView.as_view(), name="anagrafiche-province-detail"),
    path("province/lookup/", ProvinceLookupView.as_view(), name="anagrafiche-province-lookup"),
    # Regioni
    path("regioni/", RegioniView.as_view(), name="anagrafiche-regioni-list"),
    path("regioni/<int:pk>/", RegioniDetailView.as_view(), name="anagrafiche-regioni-detail"),
    path("regioni/lookup/", RegioniLookupView.as_view(), name="anagrafiche-regioni-lookup"),
    # Stati
    path("stati/", StatiView.as_view(), name="anagrafiche-stati-list"),
    path("stati/<int:pk>/", StatiDetailView.as_view(), name="anagrafiche-stati-detail"),
    path("stati/lookup/", StatiLookupView.as_view(), name="anagrafiche-stati-lookup"),
]
