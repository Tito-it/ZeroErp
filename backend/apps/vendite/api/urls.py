from django.urls import path

from apps.vendite.api.views import (
    ApiResetLottoDraft,
    ApiResetLottoFatturaDraft,
    ApiRunLottoPipeline,
)

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
    path("lotti/<int:lotto_id>/reset-draft/", ApiResetLottoDraft.as_view(), name="vendite-reset-lotto-draft"),
    path(
        "lotti/<int:lotto_id>/fatture/<int:fattura_id>/reset-draft/",
        ApiResetLottoFatturaDraft.as_view(),
        name="vendite-reset-lotto-fattura-draft",
    ),
]
