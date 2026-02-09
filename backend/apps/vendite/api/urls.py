from django.urls import path

from apps.vendite.api.views import ApiResetLottoDraft, ApiRunLottoPipeline

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
    path("lotti/<int:lotto_id>/reset-draft/", ApiResetLottoDraft.as_view(), name="vendite-reset-lotto-draft"),
]
