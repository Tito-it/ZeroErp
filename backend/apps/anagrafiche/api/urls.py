from django.urls import path

from apps.anagrafiche.api.views_clienti import ClientiDetailView, ClientiView, UtilitiesManualLookupView
from apps.anagrafiche.api.views_fornitori import FornitoriDetailView, FornitoriView
from apps.anagrafiche.api.views_matrice_indirizzi import MatriceIndirizziDetailView, MatriceIndirizziView
from apps.anagrafiche.api.views_contatti_ruolo import RuoloContattiDetailView, RuoloContattiView
from apps.anagrafiche.api.views_indirizzi_ruolo import RuoloIndirizziDetailView, RuoloIndirizziView
from apps.anagrafiche.api.views_codici_postali import CodiciPostaliDetailView, CodiciPostaliView
from apps.anagrafiche.api.views_comuni import ComuniView
from apps.anagrafiche.api.views_indirizzi import IndirizziCheckDuplicatoView, IndirizziDetailView, IndirizziView
from apps.anagrafiche.api.views_province import ProvinceDetailView, ProvinceLookupView, ProvinceView
from apps.anagrafiche.api.views_regioni import RegioniDetailView, RegioniLookupView, RegioniView
from apps.anagrafiche.api.views_soggetti import (
    GeneraCFView,
    ValidaCFPIVAView,
    SoggettiContattiDetailView,
    SoggettiContattiView,
    SoggettiDetailView,
    SoggettiIndirizziDetailView,
    SoggettiIndirizziView,
    SoggettiRuoliView,
    SoggettiView,
)
from apps.anagrafiche.api.views_conti_bancari import (
    BankBranchesLookupView,
    ContiBancariLookupView,
    RuoloContiBancariDetailView,
    RuoloContiBancariView,
    SoggettoContiBancariDetailView,
    SoggettoContiBancariView,
)
from apps.anagrafiche.api.views_stati import StatiDetailView, StatiLookupView, StatiView
from apps.anagrafiche.api.views_ruoli_config import RuoliConfigResolverView
from apps.anagrafiche.api.views_toponomastica import ToponomasticaDetailView, ToponomasticaView

urlpatterns = [
    # Clienti
    path("clienti/", ClientiView.as_view(), name="anagrafiche-clienti-list"),
    path("clienti/<int:cliente_id>/", ClientiDetailView.as_view(), name="anagrafiche-clienti-detail"),
    # Fornitori
    path("fornitori/", FornitoriView.as_view(), name="anagrafiche-fornitori-list"),
    path("fornitori/<int:fornitore_id>/", FornitoriDetailView.as_view(), name="anagrafiche-fornitori-detail"),
    # Matrice indirizzi per ruolo
    path("matrice-indirizzi-ruolo/", MatriceIndirizziView.as_view(), name="anagrafiche-matrice-indirizzi-list"),
    path("matrice-indirizzi-ruolo/<int:regola_id>/", MatriceIndirizziDetailView.as_view(), name="anagrafiche-matrice-indirizzi-detail"),
    # Utility ammesse per creazione manuale
    path("utilities/manual-lookup/", UtilitiesManualLookupView.as_view(), name="anagrafiche-utilities-manual-lookup"),
    # Contatti ruolo
    path("ruoli/<int:soggetto_ruolo_id>/contatti/", RuoloContattiView.as_view(), name="anagrafiche-ruoli-contatti"),
    path("ruoli/<int:soggetto_ruolo_id>/contatti/<int:contatto_id>/", RuoloContattiDetailView.as_view(), name="anagrafiche-ruoli-contatti-detail"),
    # Ruoli — config resolver (prima delle rotte parametriche)
    path("ruoli/<str:tipo_ruolo_codice>/config-resolver/", RuoliConfigResolverView.as_view(), name="anagrafiche-ruoli-config-resolver"),
    # Indirizzi ruolo
    path("ruoli/<int:soggetto_ruolo_id>/indirizzi/", RuoloIndirizziView.as_view(), name="anagrafiche-ruoli-indirizzi"),
    path("ruoli/<int:soggetto_ruolo_id>/indirizzi/<int:indirizzo_id>/", RuoloIndirizziDetailView.as_view(), name="anagrafiche-ruoli-indirizzi-detail"),
    # Conti bancari ruolo
    path("ruoli/<int:soggetto_ruolo_id>/conti-bancari/", RuoloContiBancariView.as_view(), name="anagrafiche-ruoli-conti-bancari"),
    path("ruoli/<int:soggetto_ruolo_id>/conti-bancari/<int:cb_id>/", RuoloContiBancariDetailView.as_view(), name="anagrafiche-ruoli-conti-bancari-detail"),
    # Soggetti — utility (prima delle rotte con <str:soggetto_id>)
    path("soggetti/valida-cf-piva/", ValidaCFPIVAView.as_view(), name="anagrafiche-valida-cf-piva"),
    path("soggetti/genera-cf/", GeneraCFView.as_view(), name="anagrafiche-genera-cf"),
    # Soggetti — CRUD
    path("soggetti/", SoggettiView.as_view(), name="anagrafiche-soggetti-list"),
    path("soggetti/<str:soggetto_id>/", SoggettiDetailView.as_view(), name="anagrafiche-soggetti-detail"),
    path("soggetti/<str:soggetto_id>/contatti/", SoggettiContattiView.as_view(), name="anagrafiche-soggetti-contatti"),
    path("soggetti/<str:soggetto_id>/contatti/<int:contatto_id>/", SoggettiContattiDetailView.as_view(), name="anagrafiche-soggetti-contatti-detail"),
    path("soggetti/<str:soggetto_id>/indirizzi/", SoggettiIndirizziView.as_view(), name="anagrafiche-soggetti-indirizzi"),
    path("soggetti/<str:soggetto_id>/indirizzi/<int:indirizzo_soggetto_id>/", SoggettiIndirizziDetailView.as_view(), name="anagrafiche-soggetti-indirizzi-detail"),
    path("soggetti/<str:soggetto_id>/ruoli/", SoggettiRuoliView.as_view(), name="anagrafiche-soggetti-ruoli"),
    # Conti bancari soggetto
    path("soggetti/<str:soggetto_id>/conti-bancari/", SoggettoContiBancariView.as_view(), name="anagrafiche-soggetti-conti-bancari"),
    path("soggetti/<str:soggetto_id>/conti-bancari/<int:cb_id>/", SoggettoContiBancariDetailView.as_view(), name="anagrafiche-soggetti-conti-bancari-detail"),
    # Conti bancari — lookup
    path("conti-bancari/lookup/", ContiBancariLookupView.as_view(), name="anagrafiche-conti-bancari-lookup"),
    path("bank-branches/lookup/", BankBranchesLookupView.as_view(), name="anagrafiche-bank-branches-lookup"),
    # Indirizzi dettaglio
    path("indirizzi/check-duplicato/", IndirizziCheckDuplicatoView.as_view(), name="anagrafiche-indirizzi-check-duplicato"),
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
