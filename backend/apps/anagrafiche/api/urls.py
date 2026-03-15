from django.urls import path

from apps.anagrafiche.api.views_comuni import ComuniView
from apps.anagrafiche.api.views_indirizzi import CodiciPostaliView, IndirizziDetailView, IndirizziView
from apps.anagrafiche.api.views_province import ProvinceDetailView, ProvinceLookupView, ProvinceView
from apps.anagrafiche.api.views_regioni import RegioniDetailView, RegioniLookupView, RegioniView
from apps.anagrafiche.api.views_stati import StatiDetailView, StatiLookupView, StatiView
from apps.anagrafiche.api.views_toponomastica import ToponomasticaDetailView, ToponomasticaView

urlpatterns = [
    # Indirizzi dettaglio
    path("indirizzi/", IndirizziView.as_view(), name="anagrafiche-indirizzi-list"),
    path("indirizzi/<int:pk>/", IndirizziDetailView.as_view(), name="anagrafiche-indirizzi-detail"),
    # Codici postali
    path("codici-postali/", CodiciPostaliView.as_view(), name="anagrafiche-codici-postali"),
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
