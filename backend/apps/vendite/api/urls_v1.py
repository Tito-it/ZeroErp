from django.urls import include, path

from apps.vendite.api.views import (
    ApiCommessaAttivita,
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

urlpatterns = [
    path("listini/", include("apps.vendite.api.urls_listini")),
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
        "commesse/<int:commessa_id>/attivita/",
        ApiCommessaAttivita.as_view(),
        name="vendite-commessa-attivita",
    ),
]
