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
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from apps.core.api.auth_views import AuditTokenObtainPairView, AuditTokenRefreshView
from apps.core.api.change_password_view import ChangePasswordView
from apps.core.api.logout_view import LogoutView
from apps.core.api.attivazione_view import AttivazioneView
from apps.core.api.password_reset_views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
)


# Scopo: Gestisce `health_view` nel flusso applicativo del modulo.
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
        AuditTokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="token-obtain-pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        AuditTokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh",
    ),
    path(
        "api/v1/auth/logout/",
        LogoutView.as_view(),
        name="auth-logout",
    ),
    path(
        "api/v1/auth/change-password/",
        ChangePasswordView.as_view(),
        name="auth-change-password",
    ),
    path(
        "api/v1/auth/password-reset-request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "api/v1/auth/password-reset-validate/<str:token>/",
        PasswordResetValidateView.as_view(),
        name="auth-password-reset-validate",
    ),
    path(
        "api/v1/auth/password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path(
        "api/v1/auth/attivazione/",
        AttivazioneView.as_view(),
        name="auth-attivazione",
    ),
    path("api/v1/core/", include("apps.core.api.urls_v1")),
    path("api/v1/vendite/", include("apps.vendite.api.urls_v1")),
    path("api/v1/pratiche/", include("apps.pratiche.api.urls_v1")),
    path("api/v1/amm-software/", include("apps.amm_software.api.urls_v1")),
    path("api/v1/anagrafiche/", include("apps.anagrafiche.api.urls")),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]
