from django.urls import path

from apps.vendite.api.views import ApiRunLottoPipelineV1

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipelineV1.as_view(), name="vendite-v1-run-lotto-pipeline"),
]
