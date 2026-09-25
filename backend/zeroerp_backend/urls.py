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
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from apps.core.api.auth_views import (
    AdminTokenRefreshView,
    AdminTokenView,
    PortaleTokenRefreshView,
    PortaleTokenView,
    ShopTokenRefreshView,
    ShopTokenView,
)
from apps.core.api.api_docs_gate import solo_se_api_docs_abilitate
from apps.core.api.change_password_view import ChangePasswordView
from apps.core.api.logout_view import LogoutView
from apps.core.api.attivazione_view import AttivazioneValidateView, AttivazioneView
from apps.core.api.password_reset_views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
)
from django.conf import settings


# Scopo: Gestisce `health_view` nel flusso applicativo del modulo.
def health_view(_request):
    """Health endpoint minimale per smoke check container."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health_view, name="health"),
    # Niente `/admin/` e niente redirect della root: l'admin Django non e'
    # installato (settings, «Superficie pubblica»). La root risponde 404.
    # Swagger/OpenAPI: `AllowAny` perche' non c'e' un token da esibire, quindi
    # esistono solo dove `API_DOCS_ENABLED` lo dice (404 altrove).
    path(
        "api/schema/",
        solo_se_api_docs_abilitate(
            SpectacularAPIView.as_view(api_version="v1", permission_classes=[AllowAny])
        ),
        name="api-schema",
    ),
    path(
        "api/docs/",
        solo_se_api_docs_abilitate(
            SpectacularSwaggerView.as_view(url_name="api-schema", permission_classes=[AllowAny])
        ),
        name="api-docs",
    ),
    path(
        "api/v1/admin/token/",
        AdminTokenView.as_view(permission_classes=[AllowAny]),
        name="admin-token-obtain-pair",
    ),
    path(
        "api/v1/admin/token/refresh/",
        AdminTokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="admin-token-refresh",
    ),
    path(
        "api/v1/portale/token/",
        PortaleTokenView.as_view(permission_classes=[AllowAny]),
        name="portale-token-obtain-pair",
    ),
    path(
        "api/v1/portale/token/refresh/",
        PortaleTokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="portale-token-refresh",
    ),
    path(
        "api/v1/shop/token/",
        ShopTokenView.as_view(permission_classes=[AllowAny]),
        name="shop-token-obtain-pair",
    ),
    path(
        "api/v1/shop/token/refresh/",
        ShopTokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="shop-token-refresh",
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
        "api/v1/auth/attivazione-validate/<str:token>/",
        AttivazioneValidateView.as_view(),
        name="auth-attivazione-validate",
    ),
    path(
        "api/v1/auth/attivazione/",
        AttivazioneView.as_view(),
        name="auth-attivazione",
    ),
    path("api/v1/core/", include("apps.core.api.urls_v1")),
    path("api/v1/vendite/", include("apps.vendite.api.urls_v1")),
    path("api/v1/pratiche/", include("apps.pratiche.api.urls_v1")),
    path("api/v1/pagamenti/", include("apps.pagamenti.api.urls_v1")),
    path("api/v1/magazzino/", include("apps.magazzino.api.urls_v1")),
    path("api/v1/amm-software/", include("apps.amm_software.api.urls_v1")),
    path("api/v1/anagrafiche/", include("apps.anagrafiche.api.urls")),
    path("api/v1/catalogo/", include("apps.catalogo.api.urls")),
    path("api/v1/config/", include("apps.config.api.urls")),
    path("api/v1/documenti/", include("apps.documenti.api.urls")),
    path("api/v1/portale/", include("apps.portale.api.urls")),
    path("api/v1/shop/", include("apps.shop.api.urls")),
    path("api/v1/ui/", include("apps.ui.api.urls")),
]

# Rotte montate solo se una flag e' accesa: (prefisso, urlconf, flag).
# ⭐ E' la sede UNICA: da qui le monta questo file, e da qui le legge
#    `apps.core.api.rotte.rotte_servite(anche_condizionali=True)`, cosi' i
#    presidi del codice vedono anche le view che in CI (flag spenta) non sono
#    instradate. Una rotta condizionale nuova si aggiunge qui, non con un `if`.
ROTTE_CONDIZIONALI: tuple[tuple[str, str, str], ...] = (
    # AI assistant: a flag spenta l'app non e' nemmeno in INSTALLED_APPS.
    ("api/v1/ai-assistant/", "apps.ai_assistant.api.urls_v1", "AI_ENABLED"),
)

for _prefisso, _urlconf, _flag in ROTTE_CONDIZIONALI:
    if getattr(settings, _flag, False):
        urlpatterns.append(path(_prefisso, include(_urlconf)))
