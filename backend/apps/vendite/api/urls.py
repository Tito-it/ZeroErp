from django.urls import path

from apps.vendite.api.views import ApiRunLottoPipeline

urlpatterns = [
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
]
