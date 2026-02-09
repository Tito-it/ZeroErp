from django.urls import path

from apps.vendite.api.views import ApiResetLottoDraftV1, ApiRunLottoPipelineV1

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipelineV1.as_view(), name="vendite-v1-run-lotto-pipeline"),
    path(
        "lotti/<int:lotto_id>/reset-draft/",
        ApiResetLottoDraftV1.as_view(),
        name="vendite-v1-reset-lotto-draft",
    ),
]
