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
)
from apps.vendite.api.views_promo_articoli import (
    PromoArticoliDetailView,
    PromoArticoliView,
)

urlpatterns = [
    path("preventivi/", include("apps.vendite.api.preventivi_urls")),
    path("listini/", include("apps.vendite.api.urls_listini")),
    # Promo articoli (STADIO 0 resolver v5). Matrice CRUD admin.
    # Non esposta via /core/lookup/codici/: ha codice ma non e'
    # candidata come tabella config lookup (semantica temporale).
    path("promo-articoli/", PromoArticoliView.as_view(), name="vendite-promo-articoli-list"),
    path("promo-articoli/<int:record_id>/", PromoArticoliDetailView.as_view(), name="vendite-promo-articoli-detail"),
    path("lotti/", ApiLottiList.as_view(), name="vendite-lotti-list"),
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
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
]
