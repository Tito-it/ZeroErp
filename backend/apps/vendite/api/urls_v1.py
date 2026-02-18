from django.urls import path

from apps.vendite.api.views import (
    ApiLottoSegnalazioniSummaryV1,
    ApiResetLottoDraftV1,
    ApiResetLottoFatturaDraftV1,
    ApiRunLottoPipelineV1,
)

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipelineV1.as_view(), name="vendite-v1-run-lotto-pipeline"),
    path(
        "lotti/<int:lotto_id>/segnalazioni/",
        ApiLottoSegnalazioniSummaryV1.as_view(),
        name="vendite-v1-lotto-segnalazioni-summary",
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
]
