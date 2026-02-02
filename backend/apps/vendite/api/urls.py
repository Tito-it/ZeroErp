from django.urls import path

from apps.vendite.api.views import run_lotto_pipeline

urlpatterns = [
    path("pipeline/run/", run_lotto_pipeline, name="vendite-run-lotto-pipeline"),
]
