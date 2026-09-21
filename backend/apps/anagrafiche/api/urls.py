from django.urls import path

from apps.anagrafiche.api.views_billing_account import (
    BillingAccountLookupByIdView,
    BillingAccountLookupView,
    BillingAccountUtilitiesView,
)
from apps.anagrafiche.api.views_categorie_clienti import (
    CategorieClientiDetailView,
    CategorieClientiView,
)
from apps.anagrafiche.api.views_categorie_clienti_listini import (
    CategorieClientiListiniDetailView,
    CategorieClientiListiniTipiVariazioneLookupView,
    CategorieClientiListiniView,
)
from apps.anagrafiche.api.views_clienti import (
    ClientiDetailView,
    ClientiExportView,
    ClientiView,
    UtilitiesManualLookupView,
)
from apps.anagrafiche.api.views_risorse_umane import RisorseUmaneLookupView
from apps.anagrafiche.api.views_invito_portale import (
    ClientiDisattivaPortaleView,
    ClientiDisattivaShopView,
    ClientiInvitaPortaleView,
    ClientiInvitaShopView,
    ClientiStatoAccessiView,
    FornitoriDisattivaPortaleView,
    FornitoriInvitaPortaleView,
    FornitoriStatoAccessiView,
)
from apps.anagrafiche.api.views_emittenti_fiscali import (
    EmittentiFiscaliBillingAccountDetailView,
    EmittentiFiscaliBillingAccountSummaryView,
    EmittentiFiscaliBillingAccountView,
    EmittentiFiscaliDetailView,
    EmittentiFiscaliUtilitiesDetailView,
    EmittentiFiscaliUtilitiesView,
    EmittentiFiscaliView,
)
from apps.anagrafiche.api.views_fornitori import (
    FornitoriDetailView,
    FornitoriExportView,
    FornitoriView,
)
from apps.anagrafiche.api.views_contatti_ruolo import RuoloContattiDetailView, RuoloContattiView
from apps.anagrafiche.api.views_indirizzi_ruolo import RuoloIndirizziDetailView, RuoloIndirizziView
from apps.anagrafiche.api.views_istanze_utility import (
    IstanzaUtilityLookupByIdView,
    IstanzaUtilityLookupView,
)
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
    SoggettiExportView,
    SoggettiIndirizziDetailView,
    SoggettiIndirizziView,
    SoggettiRuoliLookupByIdView,
    SoggettiRuoliLookupView,
    SoggettiRuoliView,
    SoggettiView,
)
from apps.anagrafiche.api.views_titoli_iva import (
    SoggettoTitoliIvaDetailView,
    SoggettoTitoliIvaView,
    SoggettoTitoloIvaAmbitiView,
    SoggettoTitoloIvaAmbitoDetailView,
    SoggettoTitoloIvaMovimentiView,
    SoggettoTitoloIvaMovimentoAnnullaView,
    SoggettoTitoliIvaExportView,
    TitoliIvaSfondatiView,
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
    # Export DEF-1: deve precedere /<int:cliente_id>/ per non collidere
    # con il route detail (Django scarta su tipo, ma l'ordine semantico
    # tiene insieme i route della stessa risorsa).
    path("clienti/export/", ClientiExportView.as_view(), name="anagrafiche-clienti-export"),
    path("clienti/<int:cliente_id>/", ClientiDetailView.as_view(), name="anagrafiche-clienti-detail"),
    path(
        "clienti/<int:cliente_id>/invita-portale/",
        ClientiInvitaPortaleView.as_view(),
        name="anagrafiche-clienti-invita-portale",
    ),
    path(
        "clienti/<int:cliente_id>/invita-shop/",
        ClientiInvitaShopView.as_view(),
        name="anagrafiche-clienti-invita-shop",
    ),
    path(
        "clienti/<int:cliente_id>/stato-accessi/",
        ClientiStatoAccessiView.as_view(),
        name="anagrafiche-clienti-stato-accessi",
    ),
    path(
        "clienti/<int:cliente_id>/disattiva-portale/",
        ClientiDisattivaPortaleView.as_view(),
        name="anagrafiche-clienti-disattiva-portale",
    ),
    path(
        "clienti/<int:cliente_id>/disattiva-shop/",
        ClientiDisattivaShopView.as_view(),
        name="anagrafiche-clienti-disattiva-shop",
    ),
    # Fornitori
    path("fornitori/", FornitoriView.as_view(), name="anagrafiche-fornitori-list"),
    path("fornitori/export/", FornitoriExportView.as_view(), name="anagrafiche-fornitori-export"),
    path("fornitori/<int:fornitore_id>/", FornitoriDetailView.as_view(), name="anagrafiche-fornitori-detail"),
    path(
        "fornitori/<int:fornitore_id>/invita-portale/",
        FornitoriInvitaPortaleView.as_view(),
        name="anagrafiche-fornitori-invita-portale",
    ),
    path(
        "fornitori/<int:fornitore_id>/stato-accessi/",
        FornitoriStatoAccessiView.as_view(),
        name="anagrafiche-fornitori-stato-accessi",
    ),
    path(
        "fornitori/<int:fornitore_id>/disattiva-portale/",
        FornitoriDisattivaPortaleView.as_view(),
        name="anagrafiche-fornitori-disattiva-portale",
    ),
    # Emittenti fiscali (admin only)
    path("emittenti-fiscali/", EmittentiFiscaliView.as_view(), name="anagrafiche-emittenti-fiscali-list"),
    path("emittenti-fiscali/<int:emittente_id>/", EmittentiFiscaliDetailView.as_view(), name="anagrafiche-emittenti-fiscali-detail"),
    # Sub-resource: mapping BA -> emittente
    path("emittenti-fiscali/<int:emittente_id>/billing-account/", EmittentiFiscaliBillingAccountView.as_view(), name="anagrafiche-emittenti-fiscali-ba-list"),
    path("emittenti-fiscali/<int:emittente_id>/billing-account/summary/", EmittentiFiscaliBillingAccountSummaryView.as_view(), name="anagrafiche-emittenti-fiscali-ba-summary"),
    path("emittenti-fiscali/<int:emittente_id>/billing-account/<int:mapping_id>/", EmittentiFiscaliBillingAccountDetailView.as_view(), name="anagrafiche-emittenti-fiscali-ba-detail"),
    # Sub-resource: utilities per emittente
    path("emittenti-fiscali/<int:emittente_id>/utilities/", EmittentiFiscaliUtilitiesView.as_view(), name="anagrafiche-emittenti-fiscali-utilities-list"),
    path("emittenti-fiscali/<int:emittente_id>/utilities/<int:record_id>/", EmittentiFiscaliUtilitiesDetailView.as_view(), name="anagrafiche-emittenti-fiscali-utilities-detail"),
    # Utility ammesse per creazione manuale
    path("utilities/manual-lookup/", UtilitiesManualLookupView.as_view(), name="anagrafiche-utilities-manual-lookup"),
    # Billing account — lookup ricco per autocomplete cross-dominio
    path("billing-account/lookup/", BillingAccountLookupView.as_view(), name="anagrafiche-billing-account-lookup"),
    path("billing-account/<int:billing_account_id>/lookup/", BillingAccountLookupByIdView.as_view(), name="anagrafiche-billing-account-lookup-by-id"),
    # Billing account — utility "guidate da emittente" (refactor operatore-emittenti)
    path("billing-account/<int:billing_account_id>/utilities/", BillingAccountUtilitiesView.as_view(), name="anagrafiche-billing-account-utilities"),
    # Istanze utility — lookup ricco per autocomplete (preventivi prospect senza BA, ecc.)
    path("istanze-utility/lookup/", IstanzaUtilityLookupView.as_view(), name="anagrafiche-istanze-utility-lookup"),
    path("istanze-utility/<int:istanza_utility_id>/lookup/", IstanzaUtilityLookupByIdView.as_view(), name="anagrafiche-istanze-utility-lookup-by-id"),
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
    path("soggetti/export/", SoggettiExportView.as_view(), name="anagrafiche-soggetti-export"),
    # Soggetti — CRUD
    # Soggetti-ruoli — lookup ricco per selezione contesto pratica (una riga
    # per ruolo + riga "senza ruolo" per i prospect puri). PRIMA delle rotte
    # <str:soggetto_id> per evitare il match del path parametrico.
    path("soggetti-ruoli/lookup/", SoggettiRuoliLookupView.as_view(), name="anagrafiche-soggetti-ruoli-lookup"),
    path("soggetti-ruoli/lookup-by-id/", SoggettiRuoliLookupByIdView.as_view(), name="anagrafiche-soggetti-ruoli-lookup-by-id"),
    path("soggetti/", SoggettiView.as_view(), name="anagrafiche-soggetti-list"),
    path("soggetti/<str:soggetto_id>/", SoggettiDetailView.as_view(), name="anagrafiche-soggetti-detail"),
    path("soggetti/<str:soggetto_id>/contatti/", SoggettiContattiView.as_view(), name="anagrafiche-soggetti-contatti"),
    path("soggetti/<str:soggetto_id>/contatti/<int:contatto_id>/", SoggettiContattiDetailView.as_view(), name="anagrafiche-soggetti-contatti-detail"),
    path("soggetti/<str:soggetto_id>/indirizzi/", SoggettiIndirizziView.as_view(), name="anagrafiche-soggetti-indirizzi"),
    path("soggetti/<str:soggetto_id>/indirizzi/<int:indirizzo_soggetto_id>/", SoggettiIndirizziDetailView.as_view(), name="anagrafiche-soggetti-indirizzi-detail"),
    path("soggetti/<str:soggetto_id>/ruoli/", SoggettiRuoliView.as_view(), name="anagrafiche-soggetti-ruoli"),
    # Conti bancari soggetto
    # Titoli IVA del soggetto (I7 / D10). ⭐ `titoli-iva/sfondati/` sta PRIMA
    # della rotta di dettaglio del titolo: e' una lista cross-soggetto e non ha
    # un `soggetto_id`, quindi vive fuori dal ramo annidato.
    path("titoli-iva/sfondati/", TitoliIvaSfondatiView.as_view(), name="anagrafiche-titoli-iva-sfondati"),
    path("soggetti/<str:soggetto_id>/titoli-iva/", SoggettoTitoliIvaView.as_view(), name="anagrafiche-soggetti-titoli-iva"),
    # ⭐ `export/` PRIMA della rotta di dettaglio: `<int:titolo_id>` non
    #    cattura una parola, ma tenere l'ordine giusto e' la regola della
    #    famiglia (vedi `titoli-iva/sfondati/` qui sopra).
    path("soggetti/<str:soggetto_id>/titoli-iva/export/", SoggettoTitoliIvaExportView.as_view(), name="anagrafiche-soggetti-titoli-iva-export"),
    path("soggetti/<str:soggetto_id>/titoli-iva/<int:titolo_id>/", SoggettoTitoliIvaDetailView.as_view(), name="anagrafiche-soggetti-titoli-iva-detail"),
    path("soggetti/<str:soggetto_id>/titoli-iva/<int:titolo_id>/ambiti/", SoggettoTitoloIvaAmbitiView.as_view(), name="anagrafiche-titoli-iva-ambiti"),
    path("soggetti/<str:soggetto_id>/titoli-iva/<int:titolo_id>/ambiti/<int:ambito_id>/", SoggettoTitoloIvaAmbitoDetailView.as_view(), name="anagrafiche-titoli-iva-ambiti-detail"),
    path("soggetti/<str:soggetto_id>/titoli-iva/<int:titolo_id>/movimenti/", SoggettoTitoloIvaMovimentiView.as_view(), name="anagrafiche-titoli-iva-movimenti"),
    # ⭐ Il verbo come ultimo segmento, e non un DELETE: annullare NON cancella,
    #    aggiunge il contro-movimento che dice quale riga corregge (Q7).
    path("soggetti/<str:soggetto_id>/titoli-iva/<int:titolo_id>/movimenti/<int:movimento_id>/annulla/", SoggettoTitoloIvaMovimentoAnnullaView.as_view(), name="anagrafiche-titoli-iva-movimento-annulla"),
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
    # Risorse umane — lookup di selezione cross-dominio (responsabile commessa,
    # brief-db-modifiche-certe-ciclo-vendita-e-articolo §5.5 voce 4). ⛔ Non
    # il lookup generico: `risorse_umane` non ha codice/descrizione, il nome
    # e' quello del soggetto (vista `vw_risorse_umane_dettaglio`).
    path("risorse-umane/lookup/", RisorseUmaneLookupView.as_view(), name="anagrafiche-risorse-umane-lookup"),
    # Stati
    path("stati/", StatiView.as_view(), name="anagrafiche-stati-list"),
    path("stati/<int:pk>/", StatiDetailView.as_view(), name="anagrafiche-stati-detail"),
    path("stati/lookup/", StatiLookupView.as_view(), name="anagrafiche-stati-lookup"),
    # Categorie cliente (sviluppo-listini v5 §4.1 — contenitore commerciale BA)
    # Endpoint admin per CRUD. Per la dropdown generica "scegli categoria"
    # usare il lookup centrale:
    #   GET /api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti
    # (tabella inserita in apps/core/db/dbops_repository.py:REL_CONSENTITE).
    # NON creare endpoint /lookup/ dedicato: duplicherebbe la whitelist.
    path("categorie-clienti/", CategorieClientiView.as_view(), name="anagrafiche-categorie-clienti-list"),
    path("categorie-clienti/<int:record_id>/", CategorieClientiDetailView.as_view(), name="anagrafiche-categorie-clienti-detail"),
    # Matrice categoria cliente x listino (sviluppo-listini v5 §4.2 — STADIO 2 resolver).
    # Per la dropdown generica "scegli riga matrice per quadrupla" usare il lookup centrale:
    #   GET /api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti_listini
    # (tabella inserita in apps/core/db/dbops_repository.py:REL_CONSENTITE).
    path("categorie-clienti-listini/", CategorieClientiListiniView.as_view(), name="anagrafiche-categorie-clienti-listini-list"),
    path("categorie-clienti-listini/lookup/tipi-variazione/", CategorieClientiListiniTipiVariazioneLookupView.as_view(), name="anagrafiche-categorie-clienti-listini-tipi-variazione"),
    path("categorie-clienti-listini/<int:record_id>/", CategorieClientiListiniDetailView.as_view(), name="anagrafiche-categorie-clienti-listini-detail"),
]
