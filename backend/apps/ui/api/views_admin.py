# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin per personalizzazioni liste (`/api/v1/ui/admin/*`).
#
#        Blocco F Fase 1 (azioni di processo `ui_preset_manage` /
#        `ui_permesso_manage` o SUPER_ADMIN):
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
#        Blocco F Fase 2 — DEF-5b (SUPER_ADMIN-only via
#        `IsAdminZeroERP`, `AdminAPIView`):
#          - GET    /admin/definizioni/               (lista completa)
#          - POST   /admin/definizioni/               (crea definizione)
#          - GET    /admin/definizioni/<id>/          (dettaglio)
#          - PATCH  /admin/definizioni/<id>/          (aggiorna)
#          - DELETE /admin/definizioni/<id>/          (elimina, RESTRICT)
#          (CRUD lista_colonna in T2)
#
#        Permessi (defense-in-depth):
#          - Lista definizioni e catalogo colonne (Fase 1): SUPER_ADMIN
#            OR azione `ui_preset_manage` OR `ui_permesso_manage`.
#          - CRUD preset: azione `ui_preset_manage`.
#          - CRUD permessi: azione `ui_permesso_manage`.
#          - CRUD definizioni (Fase 2): SUPER_ADMIN-only via
#            `IsAdminZeroERP` (`AdminAPIView`).
#          - SUPER_ADMIN bypass via PermissionResolver.is_super_admin
#            (ZeroERPPermission catena standard).
#
#        Schema `ui` non e' un'area funzionale -> tutte le view
#        dichiarano `skip_area_check = True` (incluso da `AdminAPIView`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from apps.core.api.schema_da_contratto import schema_da_contratto
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView, DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.permissions import cache_permessi_richiesta
from apps.core.api.success_responses import success_response
from apps.core.api.payload_validators import corpo_oggetto
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.services import (
    lista_colonna_admin_service,
    lista_definizione_admin_service,
    lista_preset_admin_service,
)
from apps.ui.services.lista_colonna_admin_service import (
    ListaColonnaAdminService,
)
from apps.ui.services.lista_colonna_permesso_admin_service import (
    ListaColonnaPermessoAdminService,
)
from apps.ui.services.lista_definizione_admin_service import (
    ListaDefinizioneAdminService,
)
from apps.ui.services.lista_preset_admin_service import (
    ListaPresetAdminService,
)
from apps.ui.api._schema_ui import TIPI_UI


# Serializer envelope risposta. Le 11 view ritornano JSON eterogeneo,
# meglio un wrapper unico che 11 schemi inline non riusabili.
_DATA_RESPONSE = inline_serializer(
    name="UiAdminDataResponse",
    fields={
        "data": serializers.JSONField(),
        "meta": serializers.DictField(required=False),
    },
)


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
# ⚠️ Il preset nasce sotto la sua lista: `lista_id` e' nel contratto del
#    service ma lo mette la view dal PERCORSO, sovrascrivendo il corpo.
_PRESET_CREATE_REQUEST = schema_da_contratto(
    "UiAdminPresetCreateRequest",
    lista_preset_admin_service.CREATE_KEYS - {"lista_id"}, tipi=TIPI_UI,
    obbligatorie=("codice", "descrizione", "ambito"),
)
_PRESET_UPDATE_REQUEST = schema_da_contratto(
    "UiAdminPresetUpdateRequest", lista_preset_admin_service.UPDATE_KEYS, tipi=TIPI_UI,
)
_DEFINIZIONE_CREATE_REQUEST = schema_da_contratto(
    "UiAdminDefinizioneCreateRequest", lista_definizione_admin_service.CREATE_KEYS,
    tipi=TIPI_UI, obbligatorie=("codice", "descrizione", "schema_dati"),
)
_DEFINIZIONE_UPDATE_REQUEST = schema_da_contratto(
    "UiAdminDefinizioneUpdateRequest", lista_definizione_admin_service.UPDATE_KEYS,
    tipi=TIPI_UI,
)
_COLONNA_CREATE_REQUEST = schema_da_contratto(
    "UiAdminColonnaCreateRequest", lista_colonna_admin_service.CREATE_KEYS, tipi=TIPI_UI,
    obbligatorie=("codice", "etichetta", "tipo_colonna", "tipo_dato", "ordine_default"),
)
_COLONNA_UPDATE_REQUEST = schema_da_contratto(
    "UiAdminColonnaUpdateRequest", lista_colonna_admin_service.UPDATE_KEYS, tipi=TIPI_UI,
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
    with cache_permessi_richiesta(request) as cache:
        if PermissionResolver.is_super_admin(user, cache=cache):
            return
        for codename in codenames:
            if PermissionResolver.check_azione(user, codename, cache=cache):
                return
    raise PermissionDenied("Non hai i permessi per questa operazione.")


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
        request=_PRESET_CREATE_REQUEST,
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Crea un nuovo preset per la lista. lista_id viene dal path.
    def post(self, request: Request, lista_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            data = dict(payload)
            data["lista_id"] = lista_id
            return ListaPresetAdminService().create_preset(
                data
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

    @extend_schema(request=_PRESET_UPDATE_REQUEST, responses={200: _DATA_RESPONSE})
    # Scopo: Aggiorna campi mutabili di un preset.
    def patch(self, request: Request, preset_id: int) -> JsonResponse:
        result = ListaPresetAdminService().update_preset(
            preset_id, corpo_oggetto(request),
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
            preset_id, corpo_oggetto(request)
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ListaColonnaPermessoAdminService().upsert_permesso(
                dict(payload),
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


# =================================================================
# Fase 2 - DEF-5b - CRUD ui.lista_definizione (SUPER_ADMIN only)
# =================================================================
# AdminAPIView gia' integra IsAdminZeroERP + skip_area_check.
# Endpoint dedicati per la pagina tecnica
# `/amm-software/personalizzazioni-liste-tecniche`. Niente azioni di
# processo: l'amministrazione delle definizioni richiede SUPER_ADMIN
# perche' la `vista_sql` riferita e' DDL e va in changeset Liquibase.

class ApiAdminListaDefinizioneAdminView(AdminAPIView):
    """
    GET  /api/v1/ui/admin/definizioni/   -> lista completa (incluse disattive)
    POST /api/v1/ui/admin/definizioni/   -> crea definizione
    """

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la lista completa delle definizioni (anche
    #        disattivate) per la pagina tecnica, nella forma
    #        `{results, count}`. Il `count` non impagina — dichiara quante
    #        righe esistono, cosi' il client puo' verificare di averle tutte.
    def get(self, request: Request) -> JsonResponse:
        return success_response(
            ListaDefinizioneAdminService().list_definizioni_admin()
        )

    @extend_schema(
        request=_DEFINIZIONE_CREATE_REQUEST,
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Crea una nuova definizione lista. Idempotency-Key
    #        obbligatoria (UNIQUE codice mappato lato service).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ListaDefinizioneAdminService().create_definizione(
                dict(payload),
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )


class ApiAdminListaDefinizioneAdminDetailView(AdminAPIView):
    """
    GET    /api/v1/ui/admin/definizioni/<id>/  -> dettaglio singolo
    PATCH  /api/v1/ui/admin/definizioni/<id>/  -> aggiorna campi mutabili
    DELETE /api/v1/ui/admin/definizioni/<id>/  -> elimina (RESTRICT FK)
    """

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce il dettaglio della definizione (campi completi).
    def get(self, request: Request, lista_id: int) -> JsonResponse:
        return success_response(
            ListaDefinizioneAdminService().get_definizione(lista_id)
        )

    @extend_schema(request=_DEFINIZIONE_UPDATE_REQUEST, responses={200: _DATA_RESPONSE})
    # Scopo: Aggiorna campi mutabili della definizione. Tutti i campi
    #        sono mutabili: codice cambia con UNIQUE check DB.
    def patch(self, request: Request, lista_id: int) -> JsonResponse:
        result = ListaDefinizioneAdminService().update_definizione(
            lista_id, corpo_oggetto(request),
        )
        return success_response(result)

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Cancella definizione. FK RESTRICT su lista_colonna,
    #        lista_preset e lista_preferenza_utente: se in uso il DB
    #        solleva IntegrityError mappato a E_UI_DEFINIZIONE_IN_USO.
    def delete(self, request: Request, lista_id: int) -> JsonResponse:
        result = ListaDefinizioneAdminService().delete_definizione(lista_id)
        return success_response(result)


# =================================================================
# Fase 2 - DEF-5b - CRUD ui.lista_colonna (SUPER_ADMIN only)
# =================================================================
# Path semantico: il catalogo colonne sta sotto la definizione di
# riferimento. POST/list usano `/admin/definizioni/<lista_id>/colonne/`,
# detail/PATCH/DELETE usano `/admin/colonne/<id>/` (id stabile, non
# serve lista_id ridondante).

class ApiAdminListaColonnaListView(AdminAPIView):
    """
    GET  /api/v1/ui/admin/definizioni/<lista_id>/colonne/  -> lista admin
    POST /api/v1/ui/admin/definizioni/<lista_id>/colonne/  -> crea colonna
    """

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce il catalogo completo (incluse disattivate)
    #        delle colonne registrate per la lista.
    def get(self, request: Request, lista_id: int) -> JsonResponse:
        return success_response(
            ListaColonnaAdminService().list_colonne_admin(lista_id)
        )

    @extend_schema(
        request=_COLONNA_CREATE_REQUEST,
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Crea una nuova colonna nella lista indicata. Idempotency-Key
    #        obbligatoria (UNIQUE lista_id+codice mappato lato service).
    def post(self, request: Request, lista_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ListaColonnaAdminService().create_colonna(
                lista_id, dict(payload),
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )


class ApiAdminListaColonnaDetailView(AdminAPIView):
    """
    GET    /api/v1/ui/admin/colonne/<id>/  -> dettaglio singolo
    PATCH  /api/v1/ui/admin/colonne/<id>/  -> aggiorna campi mutabili
    DELETE /api/v1/ui/admin/colonne/<id>/  -> elimina (soft-block preferenze)
    """

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce il dettaglio della colonna (campi completi).
    def get(self, request: Request, colonna_id: int) -> JsonResponse:
        return success_response(
            ListaColonnaAdminService().get_colonna(colonna_id)
        )

    @extend_schema(request=_COLONNA_UPDATE_REQUEST, responses={200: _DATA_RESPONSE})
    # Scopo: Aggiorna campi mutabili della colonna. lista_id e' immutabile
    #        (per spostare una colonna fra liste, cancellarla e ricrearla).
    def patch(self, request: Request, colonna_id: int) -> JsonResponse:
        result = ListaColonnaAdminService().update_colonna(
            colonna_id, corpo_oggetto(request),
        )
        return success_response(result)

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Cancella colonna. Soft-block applicativo se referenziata da
    #        preferenze utente; FK CASCADE pulisce preset_colonna e
    #        permessi colonna.
    def delete(self, request: Request, colonna_id: int) -> JsonResponse:
        result = ListaColonnaAdminService().delete_colonna(colonna_id)
        return success_response(result)
