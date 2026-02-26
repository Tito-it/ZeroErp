from django.urls import path

from apps.vendite.api.views import (
    ApiAttivitaPipelineStatusV1,
    ApiAttivitaTaskRunsV1,
    ApiLottiListV1,
    ApiLottoFattureListV1,
    ApiLottoSegnalazioniSummaryV1,
    ApiLottoTaskRunsV1,
    ApiResetLottoDraftV1,
    ApiResetLottoFatturaDraftV1,
    ApiRunLottoPipelineV1,
)

urlpatterns = [
    path("lotti/", ApiLottiListV1.as_view(), name="vendite-v1-lotti-list"),
    path("pipeline/run/", ApiRunLottoPipelineV1.as_view(), name="vendite-v1-run-lotto-pipeline"),
    path(
        "lotti/<int:lotto_id>/fatture/",
        ApiLottoFattureListV1.as_view(),
        name="vendite-v1-lotto-fatture-list",
    ),
    path(
        "lotti/<int:lotto_id>/segnalazioni/",
        ApiLottoSegnalazioniSummaryV1.as_view(),
        name="vendite-v1-lotto-segnalazioni-summary",
    ),
    path(
        "lotti/<int:lotto_id>/task-runs/",
        ApiLottoTaskRunsV1.as_view(),
        name="vendite-v1-lotto-task-runs",
    ),
    path(
        "lotti/<int:lotto_id>/reset-draft/",
        ApiResetLottoDraftV1.as_view(),
        name="vendite-v1-reset-lotto-draft",
    ),
    path(
        "lotti/<int:lotto_id>/fatture/<int:fattura_id>/reset-draft/",
        ApiResetLottoFatturaDraftV1.as_view(),
        name="vendite-v1-reset-lotto-fattura-draft",
    ),
    path(
        "attivita_fatturabili/pipeline/<int:lotto_id>/status/",
        ApiAttivitaPipelineStatusV1.as_view(),
        name="vendite-v1-attivita-pipeline-status",
    ),
    path(
        "attivita_fatturabili/pipeline/<int:lotto_id>/task-runs/",
        ApiAttivitaTaskRunsV1.as_view(),
        name="vendite-v1-attivita-task-runs",
    ),
]
