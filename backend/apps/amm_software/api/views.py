# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views Amm. Software — view sottili, logica nel service.
#        Contratto: docs/it/dev/api.md
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.amm_software.constants import DEFAULT_LIMIT, MAX_LIMIT

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.amm_software.services.amm_software_service import AmmSoftwareService


# Scopo: Decodifica query param a bool opzionale. Valori True: 1|true|yes|on
# (case-insensitive). Valori False: qualsiasi altra stringa non vuota. None
# se il param non e' presente. Usato per filtri di lista.
def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    return raw.lower() in ("1", "true", "yes", "on")


# ================================================================== #
# Operatori                                                            #
# ================================================================== #


class OperatoriListView(AdminAPIView):
    """GET lista, POST crea operatore."""
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="ruolo_sistema", type=str, required=False),
            OpenApiParameter(name="is_super_admin", type=bool, required=False),
            OpenApiParameter(name="unita_organizzativa_id", type=int, required=False),
            OpenApiParameter(name="is_active", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="OperatoriListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata operatori con filtri.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        is_active = _parse_optional_bool(qp.get("is_active"))
        is_super_admin = _parse_optional_bool(qp.get("is_super_admin"))

        repo = AmmSoftwareService()
        results, total_count = repo.list_operatori(
            search=qp.get("search") or None,
            ruolo_sistema=qp.get("ruolo_sistema") or None,
            is_super_admin=is_super_admin,
            unita_organizzativa_id=optional_int({"v": qp.get("unita_organizzativa_id")}, "v"),
            is_active=is_active,
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
            order_by=qp.get("order_by") or None,
            order_dir=qp.get("order_dir") or None,
        )
        return success_response({"count": total_count, "results": results})

    @extend_schema(
        summary="Crea operatore (soggetto nuovo o esistente)",
        description=(
            "Due flussi: se soggetto_id presente, associa soggetto esistente "
            "(cognome/nome/CF non richiesti). Se assente, crea soggetto PF nuovo "
            "(cognome/nome/CF obbligatori)."
        ),
        request=inline_serializer(name="OperatoriCreateReq", fields={
            "soggetto_id": serializers.CharField(required=False, help_text="UUID soggetto esistente (flusso B). Se assente, crea nuovo (flusso A)."),
            "cognome": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "nome": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "codice_fiscale": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "username": serializers.CharField(),
            "email": serializers.CharField(),
            "password": serializers.CharField(),
            "qualifica_id": serializers.IntegerField(),
            "ruolo_sistema": serializers.CharField(required=False),
            "unita_organizzativa_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="OperatoriCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea operatore. Flusso A (soggetto nuovo) o B (soggetto esistente).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=AmmSoftwareService().create_operatore)


class OperatoriDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna."""

    @extend_schema(responses={200: inline_serializer(name="OperatoreDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().get_operatore(auth_user_id))

    @extend_schema(
        request=inline_serializer(name="OperatorePatchReq", fields={
            "email": serializers.CharField(required=False),
            "first_name": serializers.CharField(required=False),
            "last_name": serializers.CharField(required=False),
            "ruolo_sistema": serializers.CharField(required=False),
            "unita_organizzativa_id": serializers.IntegerField(required=False),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(name="OperatorePatchResp", fields={"data": serializers.DictField()})},
    )
    def patch(self, request: Request, auth_user_id: int) -> JsonResponse:
        result = AmmSoftwareService().update_operatore(auth_user_id, request.data)
        return success_response(result)


class OperatoriDisabilitaView(AdminAPIView):
    """POST disabilita operatore."""

    @extend_schema(responses={200: inline_serializer(name="OperatoreDisabilitaResp", fields={"data": serializers.DictField()})})
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().disabilita_operatore(auth_user_id))


class OperatoriRiattivaView(AdminAPIView):
    """POST riattiva operatore disabilitato."""

    @extend_schema(responses={200: inline_serializer(name="OperatoreRiattivaResp", fields={"data": serializers.DictField()})})
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().riattiva_operatore(auth_user_id))


# ================================================================== #
# Override permessi                                                    #
# ================================================================== #


class OverrideAreeView(AdminAPIView):
    """GET/PUT override aree."""

    @extend_schema(responses={200: inline_serializer(name="OverrideAreeGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_aree(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideAreePutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideAreePutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_aree(auth_user_id, request.data.get("items", []))
        return success_response({"results": results})


class OverrideAzioniView(AdminAPIView):
    """GET/PUT override azioni."""

    @extend_schema(responses={200: inline_serializer(name="OverrideAzioniGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_azioni(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideAzioniPutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideAzioniPutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_azioni(auth_user_id, request.data.get("items", []))
        return success_response({"results": results})


class OverrideOggettiView(AdminAPIView):
    """GET/PUT override oggetti (v2 permessi — livello model)."""

    @extend_schema(responses={200: inline_serializer(name="OverrideOggettiGetResp", fields={"data": serializers.DictField()})})
    # Scopo: Lista override oggetto per un operatore.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_oggetti(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideOggettiPutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideOggettiPutResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Sostituisce override oggetti di un operatore.
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_oggetti(auth_user_id, request.data.get("items", []))
        return success_response({"results": results})


class ModelOverridesLookupView(AdminAPIView):
    """GET lookup model registrati per dropdown override oggetti."""

    @extend_schema(responses={200: inline_serializer(name="ModelOverridesLookupResp", fields={"data": serializers.DictField()})})
    # Scopo: Lista model registrati in area_model_overrides.
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_model_overrides()})


class EmittentiScopeView(AdminAPIView):
    """GET/PUT scope emittenti."""

    @extend_schema(responses={200: inline_serializer(name="EmittentiScopeGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_emittenti_scope(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="EmittentiScopePutReq", fields={"emittente_ids": serializers.ListField()}),
        responses={200: inline_serializer(name="EmittentiScopePutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_emittenti_scope(auth_user_id, request.data.get("emittente_ids", []))
        return success_response({"results": results})


# ================================================================== #
# Reparti e profili                                                    #
# ================================================================== #


class RepartiListView(AdminAPIView):
    """GET lista reparti."""

    @extend_schema(responses={200: inline_serializer(name="RepartiListResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_reparti()})


class RepartoProfiloView(AdminAPIView):
    """GET/PUT profilo reparto."""

    @extend_schema(responses={200: inline_serializer(name="RepartoProfiloGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, uo_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().get_profilo_reparto(uo_id))

    @extend_schema(
        request=inline_serializer(name="RepartoProfiloPutReq", fields={
            "aree": serializers.ListField(), "azioni": serializers.ListField(),
        }),
        responses={200: inline_serializer(name="RepartoProfiloPutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, uo_id: int) -> JsonResponse:
        result = AmmSoftwareService().put_profilo_reparto(
            uo_id, request.data.get("aree", []), request.data.get("azioni", []),
        )
        return success_response(result)


# ================================================================== #
# Riepilogo permessi                                                   #
# ================================================================== #


class AuditLogView(AdminAPIView):
    """GET audit log globale modifiche permessi."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="tabella", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: inline_serializer(name="AuditLogResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Timeline globale eventi audit permessi.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        events, total_count = AmmSoftwareService().list_audit_log(
            data_da=qp.get("data_da") or None,
            data_a=qp.get("data_a") or None,
            tabella=qp.get("tabella") or None,
            order_by=qp.get("order_by") or None,
            order_dir=qp.get("order_dir") or None,
            limit=min(optional_int({"v": qp.get("limit")}, "v") or 50, 200),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total_count, "results": events})


class PermessiRiepilogoView(AdminAPIView):
    """GET matrice permessi effettivi per tutti gli operatori attivi."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="unita_organizzativa_id", type=int, required=False),
            OpenApiParameter(name="ruolo_sistema", type=str, required=False),
        ],
        responses={200: inline_serializer(name="PermessiRiepilogoResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Matrice operatori × aree con livello effettivo.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        result = AmmSoftwareService().get_permessi_riepilogo(
            unita_organizzativa_id=optional_int({"v": qp.get("unita_organizzativa_id")}, "v"),
            ruolo_sistema=qp.get("ruolo_sistema") or None,
            emittente_fiscale_id=optional_int({"v": qp.get("emittente_fiscale_id")}, "v"),
        )
        return success_response(result)


# ================================================================== #
# Lookup                                                               #
# ================================================================== #


class UtentiUOListView(AdminAPIView):
    """GET lista UO per dropdown."""
    @extend_schema(responses={200: inline_serializer(name="UOListResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_unita_organizzative()})


class LookupAreeView(AdminAPIView):
    """GET aree funzionali."""
    @extend_schema(responses={200: inline_serializer(name="LookupAreeResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_aree_funzionali()})


class LookupAzioniView(AdminAPIView):
    """GET azioni processo."""
    @extend_schema(responses={200: inline_serializer(name="LookupAzioniResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_azioni_processo()})


class LookupEmittentiView(AdminAPIView):
    """GET emittenti fiscali."""
    @extend_schema(responses={200: inline_serializer(name="LookupEmittentiResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_emittenti_fiscali()})



# ================================================================== #
# Setup status (refactor operatore-emittenti)                          #
# ================================================================== #


class SetupStatusView(AdminAPIView):
    """GET stato setup refactor operatore-emittenti.

    Conta emittenti attivi, operatori totali/assegnati/admin globali/non
    assegnati. Usato dal banner UI "operatori non assegnati" che avvisa
    l'admin durante la transizione (decisione D1 del WIP).
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="SetupStatusResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce i 5 contatori di setup status.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(AmmSoftwareService().get_setup_status())
