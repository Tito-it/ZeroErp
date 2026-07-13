from django.urls import include, path

from apps.vendite.api.views import (
    ApiCommessaAttivita,
    ApiCommessaAttivitaRiallineaPrezzo,
    ApiCommessaAttivitaSbloccaPrezzo,
    ApiCommessaAttivitaVariazionePrezzoEccezionale,
    ApiCommessePushLog,
    ApiCommessaStato,
    ApiLottiList,
    ApiLottoFattureList,
    ApiLottoSegnalazioniSummary,
    ApiLottoTaskRuns,
    ApiResetLottoDraft,
    ApiResetLottoFatturaDraft,
    ApiRunCommessePush,
    ApiRunLottoPipeline,
    ApiRunLottoPipelineUntilDone,
)
from apps.vendite.api.views_approvazioni_prezzo import (
    ApprovaPrezzoContrattoView,
    ApprovaPrezzoOffertaView,
    ApprovaPrezzoView,
    ApprovazioniPrezzoCodaView,
    RifiutaPrezzoContrattoView,
    RifiutaPrezzoOffertaView,
    RifiutaPrezzoView,
)
from apps.vendite.api.views_dashboard_backlog import (
    ApiDashboardBacklog,
    ApiDashboardBacklogDocumenti,
)
from apps.vendite.api.views_dashboard_competenza import (
    ApiDashboardCompetenza,
    ApiDashboardCompetenzaAttivita,
    ApiDashboardCompetenzaErrori,
)
from apps.vendite.api.views_dashboard_aperto import (
    ApiDashboardAperto,
    ApiDashboardApertoDocumenti,
)
from apps.vendite.api.views_lookups import (
    ApiAmbitiContrattoLookup,
    ApiListiniSelezionabiliContrattoLookup,
    ApiTipiVariazioneContrattoLookup,
    ApiTipiVariazionePromoLookup,
)
from apps.vendite.api.views_pricing import (
    PricingDiagnoseView,
    PricingLimitiUtenteView,
    PricingResolveView,
)
from apps.vendite.api.views_promo_articoli import (
    PromoArticoliDetailView,
    PromoArticoliView,
)

urlpatterns = [
    path("preventivi/", include("apps.vendite.api.preventivi_urls")),
    path("listini/", include("apps.vendite.api.urls_listini")),
    path("contratti/", include("apps.vendite.api.urls_contratti")),
    path("offerte/", include("apps.vendite.api.urls_offerte")),
    path("ordini/", include("apps.vendite.api.urls_ordini")),
    path("ddt/", include("apps.vendite.api.urls_ddt")),
    path("resi/", include("apps.vendite.api.urls_resi")),
    # Pricing v5 diagnostico: resolver 3 stadi (PROMO/CONTRATTO/CATEGORIA).
    path("pricing/resolve/", PricingResolveView.as_view(), name="vendite-pricing-resolve"),
    # Diagnostica configurazione asset pricing (BA, contratto, matrice, promo)
    # — checklist a stadi + azioni suggerite per UX e supporto.
    path("pricing/diagnose/", PricingDiagnoseView.as_view(), name="vendite-pricing-diagnose"),
    # L2 autorizzazioni prezzi: limiti sconto/maggiorazione per utente corrente.
    path("pricing/limiti-utente/", PricingLimitiUtenteView.as_view(), name="vendite-pricing-limiti-utente"),
    # L3 workflow approvazione prezzo out-of-policy (Sprint E).
    path(
        "righe/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoView.as_view(),
        name="vendite-approva-prezzo",
    ),
    path(
        "righe/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoView.as_view(),
        name="vendite-rifiuta-prezzo",
    ),
    # L3 workflow approvazione prezzo su riga **contratto** (refactor
    # 2026-05-19 BE porting gate riga contratti). Endpoint distinto da
    # `righe/` per evitare ambiguita' su `riga_id` (preventivi e contratti
    # hanno tabelle/sequence indipendenti). Servizio service-side fa
    # dispatch via parametro sorgente='contratto'.
    path(
        "righe-contratto/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoContrattoView.as_view(),
        name="vendite-approva-prezzo-contratto",
    ),
    path(
        "righe-contratto/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoContrattoView.as_view(),
        name="vendite-rifiuta-prezzo-contratto",
    ),
    # L3 workflow approvazione prezzo su **eccezione offerta** (refactor
    # 2026-06-01 gate prezzi offerte). Endpoint distinto: `riga_id` = id
    # eccezione; service dispatch via sorgente='offerta'.
    path(
        "eccezioni-offerta/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoOffertaView.as_view(),
        name="vendite-approva-prezzo-offerta",
    ),
    path(
        "eccezioni-offerta/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoOffertaView.as_view(),
        name="vendite-rifiuta-prezzo-offerta",
    ),
    path(
        "approvazioni-prezzo/",
        ApprovazioniPrezzoCodaView.as_view(),
        name="vendite-approvazioni-prezzo-coda",
    ),
    # Promo articoli (STADIO 0 resolver v5). Matrice CRUD admin.
    # Non esposta via /core/lookup/codici/: ha codice ma non e'
    # candidata come tabella config lookup (semantica temporale).
    path("promo-articoli/", PromoArticoliView.as_view(), name="vendite-promo-articoli-list"),
    path("promo-articoli/<int:record_id>/", PromoArticoliDetailView.as_view(), name="vendite-promo-articoli-detail"),
    # Situazione aperta — stock documenti per fase, senza asse temporale
    # (brief-design-fatturazione-due-lenti §6-bis): riepilogo + drill-down.
    # Sostituisce la dashboard fatturazione 5-card (Fase 3, trasformazione).
    path(
        "dashboard-aperto/",
        ApiDashboardAperto.as_view(),
        name="vendite-dashboard-aperto",
    ),
    path(
        "dashboard-aperto/documenti/",
        ApiDashboardApertoDocumenti.as_view(),
        name="vendite-dashboard-aperto-documenti",
    ),
    # Lente 1 Competenza — funnel commessa → fattura per mese di competenza
    # (brief-design-fatturazione-due-lenti §4): aggregata + drill-down + errori.
    path(
        "dashboard-competenza/",
        ApiDashboardCompetenza.as_view(),
        name="vendite-dashboard-competenza",
    ),
    path(
        "dashboard-competenza/attivita/",
        ApiDashboardCompetenzaAttivita.as_view(),
        name="vendite-dashboard-competenza-attivita",
    ),
    path(
        "dashboard-competenza/errori/",
        ApiDashboardCompetenzaErrori.as_view(),
        name="vendite-dashboard-competenza-errori",
    ),
    # Lente 2 Backlog — non-collegati per anzianita' + classe azionabilita'
    # (brief-design-fatturazione-due-lenti §5): contatori + lista.
    path(
        "dashboard-backlog/",
        ApiDashboardBacklog.as_view(),
        name="vendite-dashboard-backlog",
    ),
    path(
        "dashboard-backlog/documenti/",
        ApiDashboardBacklogDocumenti.as_view(),
        name="vendite-dashboard-backlog-documenti",
    ),
    path("lotti/", ApiLottiList.as_view(), name="vendite-lotti-list"),
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
    path(
        "pipeline/run-until-done/",
        ApiRunLottoPipelineUntilDone.as_view(),
        name="vendite-run-lotto-pipeline-until-done",
    ),
    path(
        "lotti/<int:lotto_id>/fatture/",
        ApiLottoFattureList.as_view(),
        name="vendite-lotto-fatture-list",
    ),
    path(
        "lotti/<int:lotto_id>/segnalazioni/",
        ApiLottoSegnalazioniSummary.as_view(),
        name="vendite-lotto-segnalazioni-summary",
    ),
    path(
        "lotti/<int:lotto_id>/task-runs/",
        ApiLottoTaskRuns.as_view(),
        name="vendite-lotto-task-runs",
    ),
    path(
        "lotti/<int:lotto_id>/reset-draft/",
        ApiResetLottoDraft.as_view(),
        name="vendite-reset-lotto-draft",
    ),
    path(
        "lotti/<int:lotto_id>/fatture/<int:fattura_id>/reset-draft/",
        ApiResetLottoFatturaDraft.as_view(),
        name="vendite-reset-lotto-fattura-draft",
    ),
    # --- Commesse ---
    path(
        "commesse/push/run/",
        ApiRunCommessePush.as_view(),
        name="vendite-run-commesse-push",
    ),
    path(
        "commesse/push/<int:push_log_id>/",
        ApiCommessePushLog.as_view(),
        name="vendite-commesse-push-log",
    ),
    path(
        "commesse/<int:commessa_id>/stato/",
        ApiCommessaStato.as_view(),
        name="vendite-commessa-stato",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/riallinea-prezzo/",
        ApiCommessaAttivitaRiallineaPrezzo.as_view(),
        name="vendite-commessa-attivita-riallinea-prezzo",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/variazione-prezzo-eccezionale/",
        ApiCommessaAttivitaVariazionePrezzoEccezionale.as_view(),
        name="vendite-commessa-attivita-variazione-prezzo",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/sblocca-prezzo/",
        ApiCommessaAttivitaSbloccaPrezzo.as_view(),
        name="vendite-commessa-attivita-sblocca-prezzo",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/",
        ApiCommessaAttivita.as_view(),
        name="vendite-commessa-attivita",
    ),
    # --- Lookup statici (Fase 2 refactor frontend vendite) ---
    path(
        "lookup/tipi-variazione-contratto/",
        ApiTipiVariazioneContrattoLookup.as_view(),
        name="vendite-lookup-tipi-variazione-contratto",
    ),
    path(
        "lookup/tipi-variazione-promo/",
        ApiTipiVariazionePromoLookup.as_view(),
        name="vendite-lookup-tipi-variazione-promo",
    ),
    path(
        "lookup/ambiti-contratto/",
        ApiAmbitiContrattoLookup.as_view(),
        name="vendite-lookup-ambiti-contratto",
    ),
    # Lookup dinamico listini selezionabili come riferimento contrattuale
    # (filtra per esistenza di una versione ATTIVA — decisione 2026-05-18
    # §4.4 refactor-contratti-modalita). Sostituisce LookupSelect generico
    # `rel=vendite.listini` nel ContrattoDrawer.
    path(
        "lookup/listini-selezionabili-contratto/",
        ApiListiniSelezionabiliContrattoLookup.as_view(),
        name="vendite-lookup-listini-selezionabili-contratto",
    ),
]
