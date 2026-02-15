"""
URL configuration for zeroerp_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health_view(_request):
    """Health endpoint minimale per smoke check container."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health_view, name="health"),
    path("admin/", admin.site.urls),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(api_version="v1", permission_classes=[AllowAny]),
        name="api-schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema", permission_classes=[AllowAny]),
        name="api-docs",
    ),
    path(
        "api/v1/auth/token/",
        TokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="token-obtain-pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh",
    ),
    path("api/v1/core/", include("apps.core.api.urls_v1")),
    path("api/v1/vendite/", include("apps.vendite.api.urls_v1")),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]

if settings.API_LEGACY_ROUTES_ENABLED:
    # Compatibilita` temporanea: route legacy senza version prefix.
    urlpatterns += [
        path("api/core/", include("apps.core.api.urls")),
        path("api/vendite/", include("apps.vendite.api.urls")),
    ]
