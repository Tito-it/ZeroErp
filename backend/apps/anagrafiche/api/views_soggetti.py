# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views soggetti — view sottili, logica nel service.
#        CRUD soggetti, contatti, indirizzi soggetto, ruoli.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int, paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.anagrafiche.services.cf_validator_it import genera_cf_it


# =================================================================
# Soggetti lista + crea
# =================================================================

class SoggettiView(DomainAPIView):
    """GET lista, POST crea soggetto completo."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="tipo_soggetto_dettaglio_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="SoggettiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata soggetti con search e filtro tipo.
    #        Scope emittente: filtra i badge ruolo CL in base all'emittente
    #        dell'operatore (un operatore non vede il badge CL se il soggetto
    #        ha clienti solo su altri emittenti).
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        tipo_id = optional_int({"v": request.query_params.get("tipo_soggetto_dettaglio_id")}, "v")
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache=cache)
        svc = SoggettiService()
        results, total = svc.list_soggetti(
            search=p["search"], tipo_soggetto_dettaglio_id=tipo_id,
            emittente_ids=emittente_ids,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="SoggettoCreateReq", fields={
            "tipo_soggetto_dettaglio_id": serializers.IntegerField(),
            "cognome": serializers.CharField(required=False),
            "nome": serializers.CharField(required=False),
            "ragione_sociale": serializers.CharField(required=False),
            "codice_fiscale": serializers.CharField(),
            "partita_iva": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="SoggettoCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea soggetto completo (PF o PG + contatto + indirizzo).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=SoggettiService().create_soggetto)


# =================================================================
# Soggetto dettaglio + aggiornamento
# =================================================================

class SoggettiDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna soggetto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        responses={200: inline_serializer(name="SoggettoDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio soggetto con contatti, indirizzi, ruoli.
    #        Scope emittente: filtra ruoli CL per emittente operatore.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache=cache)
        return success_response(SoggettiService().get_soggetto(soggetto_id, emittente_ids))

    @extend_schema(
        request=inline_serializer(name="SoggettoUpdateReq", fields={
            "cognome": serializers.CharField(required=False),
            "nome": serializers.CharField(required=False),
            "codice_fiscale": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="SoggettoUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna campi soggetto.
    def patch(self, request: Request, soggetto_id: str) -> JsonResponse:
        result = SoggettiService().update_soggetto(soggetto_id, request.data)
        return success_response(result)


# =================================================================
# Contatti di un soggetto
# =================================================================

class SoggettiContattiView(DomainAPIView):
    """GET lista contatti, POST crea contatto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        responses={200: inline_serializer(name="SoggettoContattiResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista contatti del soggetto.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        return success_response({"results": SoggettiService().get_soggetto_contatti(soggetto_id)})

    @extend_schema(
        request=inline_serializer(name="ContattoCreateReq", fields={
            "nominativo": serializers.CharField(),
            "email": serializers.CharField(required=False),
            "telefono": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="ContattoCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea contatto per il soggetto.
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().create_contatto(soggetto_id, p),
        )


# =================================================================
# Contatto dettaglio (PATCH)
# =================================================================

class SoggettiContattiDetailView(DomainAPIView):
    """PATCH aggiorna contatto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        request=inline_serializer(name="ContattoUpdateReq", fields={
            "nominativo": serializers.CharField(required=False),
            "email": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="ContattoUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna contatto con verifica ownership soggetto.
    def patch(self, request: Request, soggetto_id: str, contatto_id: int) -> JsonResponse:
        result = SoggettiService().update_contatto(contatto_id, request.data, soggetto_id=soggetto_id)
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(name="ContattoDeleteResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Elimina contatto con verifica ownership soggetto.
    def delete(self, request: Request, soggetto_id: str, contatto_id: int) -> JsonResponse:
        return success_response(
            SoggettiService().delete_contatto(soggetto_id, contatto_id)
        )


# =================================================================
# Indirizzi soggetto
# =================================================================

class SoggettiIndirizziView(DomainAPIView):
    """GET lista indirizzi, POST crea indirizzo soggetto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        responses={200: inline_serializer(name="SoggettoIndirizziResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista indirizzi layer soggetto.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        return success_response({"results": SoggettiService().get_soggetto_indirizzi(soggetto_id)})

    @extend_schema(
        request=inline_serializer(name="IndirizzoSoggettoCreateReq", fields={
            "tipo_indirizzo_codice": serializers.CharField(),
            "indirizzo_dettaglio_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="IndirizzoSoggettoCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea indirizzo layer soggetto.
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().create_indirizzo_soggetto(soggetto_id, p),
        )


class SoggettiIndirizziDetailView(DomainAPIView):
    """PUT sostituisce indirizzo (replace), DELETE elimina."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        request=inline_serializer(name="ReplaceIndirizzoReq", fields={
            "tipo_indirizzo_codice": serializers.CharField(),
        }),
        responses={200: inline_serializer(name="ReplaceIndirizzoResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Sostituisce indirizzo soggetto (delete vecchio + create nuovo).
    def put(self, request: Request, soggetto_id: str, indirizzo_soggetto_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().replace_indirizzo_soggetto(
                soggetto_id, indirizzo_soggetto_id, p
            ),
        )

    @extend_schema(
        responses={200: inline_serializer(name="DeleteIndirizzoResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Elimina associazione indirizzo soggetto.
    def delete(self, request: Request, soggetto_id: str, indirizzo_soggetto_id: int) -> JsonResponse:
        return success_response(
            SoggettiService().delete_indirizzo_soggetto(soggetto_id, indirizzo_soggetto_id)
        )


# =================================================================
# Ruoli soggetto
# =================================================================

class SoggettiRuoliView(DomainAPIView):
    """GET lista ruoli, POST assegna ruolo."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "soggetto")

    @extend_schema(
        responses={200: inline_serializer(name="SoggettoRuoliResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista ruoli assegnati al soggetto con scope emittente su CL.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache=cache)
        return success_response({"results": SoggettiService().get_soggetto_ruoli(soggetto_id, emittente_ids)})

    @extend_schema(
        request=inline_serializer(name="RuoloAssignReq", fields={
            "codice_ruolo": serializers.CharField(),
        }),
        responses={200: inline_serializer(name="RuoloAssignResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Assegna ruolo al soggetto (idempotente).
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().assign_ruolo(soggetto_id, p),
        )


class ValidaCFPIVAView(DomainAPIView):
    """POST validazione CF (congruenza + duplicato) e P.IVA (duplicato)."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="ValidaCFPIVAReq", fields={
            "codice_fiscale": serializers.CharField(required=False),
            "partita_iva": serializers.CharField(required=False),
            "sesso": serializers.CharField(required=False),
            "data_nascita": serializers.DateField(required=False),
            "comune_nascita_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="ValidaCFPIVAResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Validazione CF/PIVA con feedback immediato (errori + warning duplicati).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().valida_cf_piva(p),
        )


class GeneraCFView(DomainAPIView):
    """POST genera codice fiscale italiano da dati anagrafici."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="GeneraCFReq", fields={
            "cognome": serializers.CharField(),
            "nome": serializers.CharField(),
            "data_nascita": serializers.DateField(),
            "sesso": serializers.CharField(),
            "comune_nascita_id": serializers.IntegerField(),
        }),
        responses={200: inline_serializer(name="GeneraCFResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Genera CF italiano da cognome, nome, data nascita, sesso, comune.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().genera_cf(p),
        )
