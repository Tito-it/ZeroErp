# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin per personalizzazioni liste (`/api/v1/ui/admin/*`)
#        — Blocco F Fase 1.
#
#        Endpoint:
#          - GET    /admin/liste/                     (Select header)
#          - GET    /admin/liste/<id>/colonne/        (catalogo per composizione)
#          - GET    /admin/liste/<id>/preset/         (preset di una lista)
#          - POST   /admin/liste/<id>/preset/         (crea preset)
#          - PATCH  /admin/preset/<preset_id>/        (aggiorna preset)
#          - DELETE /admin/preset/<preset_id>/        (elimina preset)
#          - GET    /admin/preset/<preset_id>/colonne/  (composizione)
#          - PUT    /admin/preset/<preset_id>/colonne/  (replace composizione)
#          - GET    /admin/liste/<id>/permessi/       (permessi colonna)
#          - POST   /admin/permessi/                  (UPSERT permesso)
#          - DELETE /admin/permessi/<id>/             (elimina permesso)
#
#        Permessi (defense-in-depth):
#          - Lista definizioni e catalogo colonne: SUPER_ADMIN OR
#            azione `ui_preset_manage` OR azione `ui_permesso_manage`
#            (il Select header serve a entrambi i tab).
#          - CRUD preset: azione `ui_preset_manage`.
#          - CRUD permessi: azione `ui_permesso_manage`.
#          - SUPER_ADMIN bypass via PermissionResolver.is_super_admin
#            (ZeroERPPermission catena standard).
#
#        Schema `ui` non e' un'area funzionale -> tutte le view
#        dichiarano `skip_area_check = True`.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.success_responses import success_response
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.services.lista_colonna_permesso_admin_service import (
    ListaColonnaPermessoAdminService,
)
from apps.ui.services.lista_definizione_admin_service import (
    ListaDefinizioneAdminService,
)
from apps.ui.services.lista_preset_admin_service import (
    ListaPresetAdminService,
)


# Serializer envelope risposta. Le 11 view ritornano JSON eterogeneo,
# meglio un wrapper unico che 11 schemi inline non riusabili.
_DATA_RESPONSE = inline_serializer(
    name="UiAdminDataResponse",
    fields={
        "data": serializers.JSONField(),
        "meta": serializers.DictField(required=False),
    },
)


# Scopo: Verifica che l'utente abbia almeno una delle azioni passate
#        (OR-azioni). SUPER_ADMIN bypass. Solleva PermissionDenied
#        altrimenti. Usato dalle view del Select "Lista corrente" che
#        servono entrambi i tab Preset + Permessi.
#        Usa la cache di `ZeroERPPermission` per evitare round-trip DB
#        ridondanti su `is_super_admin` + `check_azione` (la cache e'
#        gia' popolata in `has_permission` poco prima di entrare nel
#        body della view).
def _require_any_action(request: Request, codenames: list[str]) -> None:
    user = request.user
    if user.is_superuser:
        return
    cache = ZeroERPPermission._get_cache(request)
    try:
        if PermissionResolver.is_super_admin(user, cache=cache):
            return
        for codename in codenames:
            if PermissionResolver.check_azione(user, codename, cache=cache):
                return
        raise PermissionDenied("Non hai i permessi per questa operazione.")
    finally:
        ZeroERPPermission._save_cache_to_redis(request)


# =================================================================
# /admin/liste/  -  Select header + catalogo colonne
# =================================================================

class ApiAdminListaDefinizioneListView(DomainAPIView):
    """
    GET /api/v1/ui/admin/liste/

    Lista delle definizioni di lista attive. Pre-popola il Select
    "Lista corrente" della pagina admin. Visibile a chi ha almeno una
    delle 2 azioni di processo o e' SUPER_ADMIN.
    """

    skip_area_check = True

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la lista delle definizioni attive.
    def get(self, request: Request) -> JsonResponse:
        _require_any_action(
            request, ["ui_preset_manage", "ui_permesso_manage"]
        )
        return success_response(
            ListaDefinizioneAdminService().list_definizioni()
        )


class ApiAdminListaColonneView(DomainAPIView):
    """
    GET /api/v1/ui/admin/liste/<id>/colonne/

    Catalogo colonne grezzo (no filtro permessi: amministrazione tecnica).
    Usato dal sub-drawer composizione preset per offrire al
    super-admin/tenant admin il catalogo da cui pescare le colonne.
    Visibile con azione `ui_preset_manage`.
    """

    skip_area_check = True
    get_permission = "ui_preset_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce il catalogo colonne grezzo della lista.
    def get(self, request: Request, lista_id: int) -> JsonResponse:
        return success_response(
            ListaDefinizioneAdminService().list_colonne_lista(lista_id)
        )


# =================================================================
# /admin/liste/<id>/preset/  + /admin/preset/<id>/
# =================================================================

class ApiAdminPresetListView(DomainAPIView):
    """
    GET  /api/v1/ui/admin/liste/<id>/preset/  -> lista preset
    POST /api/v1/ui/admin/liste/<id>/preset/  -> crea preset

    Auth via azione `ui_preset_manage`.
    """

    skip_area_check = True
    get_permission = "ui_preset_manage"
    post_permission = "ui_preset_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la lista dei preset di una lista.
    def get(self, request: Request, lista_id: int) -> JsonResponse:
        return success_response(
            ListaPresetAdminService().list_preset(lista_id)
        )

    @extend_schema(
        request=inline_serializer(
            name="UiAdminPresetCreateRequest",
            fields={
                "codice": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "ambito": serializers.CharField(),
                "profilo_accesso_id": serializers.IntegerField(required=False, allow_null=True),
                "emittente_fiscale_id": serializers.IntegerField(required=False, allow_null=True),
                "is_default": serializers.BooleanField(required=False),
                "pagina_dimensione": serializers.IntegerField(required=False, allow_null=True),
                "ordinamento_default": serializers.JSONField(required=False, allow_null=True),
                "filtri_default": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Crea un nuovo preset per la lista. lista_id viene dal path.
    def post(self, request: Request, lista_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            data = dict(payload)
            data["lista_id"] = lista_id
            return ListaPresetAdminService().create_preset(
                request.user, data
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )


class ApiAdminPresetDetailView(DomainAPIView):
    """
    PATCH  /api/v1/ui/admin/preset/<preset_id>/  -> aggiorna testata
    DELETE /api/v1/ui/admin/preset/<preset_id>/  -> elimina preset
    """

    skip_area_check = True
    patch_permission = "ui_preset_manage"
    delete_permission = "ui_preset_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Aggiorna campi mutabili di un preset.
    def patch(self, request: Request, preset_id: int) -> JsonResponse:
        result = ListaPresetAdminService().update_preset(
            request.user, preset_id, dict(request.data),
        )
        return success_response(result)

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Cancella un preset (CASCADE su composizione, SET NULL su preferenze).
    def delete(self, request: Request, preset_id: int) -> JsonResponse:
        result = ListaPresetAdminService().delete_preset(preset_id)
        return success_response(result)


class ApiAdminPresetColonneView(DomainAPIView):
    """
    GET /api/v1/ui/admin/preset/<preset_id>/colonne/  -> composizione
    PUT /api/v1/ui/admin/preset/<preset_id>/colonne/  -> replace atomico
    """

    skip_area_check = True
    get_permission = "ui_preset_manage"
    put_permission = "ui_preset_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la composizione attuale del preset.
    def get(self, request: Request, preset_id: int) -> JsonResponse:
        return success_response(
            ListaPresetAdminService().list_preset_colonne(preset_id)
        )

    @extend_schema(
        request=inline_serializer(
            name="UiAdminPresetColonneRequest",
            fields={
                "colonne": serializers.ListField(
                    child=serializers.DictField(),
                ),
            },
        ),
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Replace atomico della composizione del preset.
    def put(self, request: Request, preset_id: int) -> JsonResponse:
        result = ListaPresetAdminService().replace_preset_colonne(
            preset_id, dict(request.data)
        )
        return success_response(result)


# =================================================================
# /admin/liste/<id>/permessi/  +  /admin/permessi/<id>/
# =================================================================

class ApiAdminPermessoListView(DomainAPIView):
    """
    GET  /api/v1/ui/admin/liste/<id>/permessi/  -> lista permessi colonna
    POST /api/v1/ui/admin/permessi/             -> UPSERT permesso colonna

    POST e' su `/admin/permessi/` perche' la coppia (colonna_id, profilo)
    identifica la riga: il `lista_id` del path della GET serve solo da
    filtro lettura.
    """

    skip_area_check = True
    get_permission = "ui_permesso_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce i permessi colonna di una lista.
    def get(self, request: Request, lista_id: int) -> JsonResponse:
        return success_response(
            ListaColonnaPermessoAdminService().list_permessi(lista_id)
        )


class ApiAdminPermessoCreateView(DomainAPIView):
    """
    POST /api/v1/ui/admin/permessi/  -> UPSERT permesso colonna

    Idempotency-Key obbligatoria (UPSERT su UNIQUE).
    """

    skip_area_check = True
    post_permission = "ui_permesso_manage"

    @extend_schema(
        request=inline_serializer(
            name="UiAdminPermessoUpsertRequest",
            fields={
                "colonna_id": serializers.IntegerField(),
                "profilo_accesso_id": serializers.IntegerField(),
                "livello_accesso": serializers.CharField(),
            },
        ),
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: UPSERT permesso colonna su (colonna_id, profilo_accesso_id).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return ListaColonnaPermessoAdminService().upsert_permesso(
                request.user, dict(payload),
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )


class ApiAdminPermessoDetailView(DomainAPIView):
    """
    DELETE /api/v1/ui/admin/permessi/<id>/  -> elimina permesso
    """

    skip_area_check = True
    delete_permission = "ui_permesso_manage"

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Cancella permesso colonna per id.
    def delete(self, request: Request, permesso_id: int) -> JsonResponse:
        result = ListaColonnaPermessoAdminService().delete_permesso(permesso_id)
        return success_response(result)
