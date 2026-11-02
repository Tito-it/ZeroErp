# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views CRUD generico per tabelle config whitelisted.
#        Ref: docs/it/dev/api.md
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.openapi_params import parametri_finestra
from apps.core.api.payload_validators import corpo_oggetto, pagina_da_query, qp_bool_optional
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository
from apps.core.services.config_crud_service import ConfigCrudService


# Il corpo di un record: un oggetto le cui chiavi sono le colonne della tabella
# `rel`, diverse per ogni tabella del pannello. ⭐ E' la forma VERA, non un
# ripiego: le colonne (con tipo, obbligatorieta' e sola lettura) le dichiara
# a runtime `GET config/tables/<rel>/metadata/`, ed e' li' che le legge il
# pannello. Uno schema per tabella sarebbe una seconda sede di quel catalogo.
_RECORD_REQUEST = OpenApiTypes.OBJECT

# Scopo: Le rotte che nominano una tabella (`rel`) chiedono il permesso
# sull'OGGETTO a cui la tabella appartiene, non sull'area del pannello
# (D-3 §7.1 del brief del modello, D-5): chi ha TUTTO solo su Configurazione
# non modifica piu' le causali di magazzino. E' lo stesso controllo del verbo
# (`fn_guard_livello` su app_label/model_name della lista), fatto PRIMA di
# aprire la transazione per dare subito il 403: un punto di applicazione in
# piu', non una seconda regola — l'area la dice `fn_area_di_oggetto`.
# ⭐ La view DICHIARA l'oggetto; lo applica la catena di `ZeroERPPermission`
#    (D-P7 del brief-db-pannello-config-verbo-generico), anche in lettura.
#    Fino al 2026-09-25 (sera) questo mixin sovrascriveva `check_permissions`
#    e riscriveva l'area sull'istanza: valutata sulla classe, la view diceva
#    «config», cioe' un'area che non e' quella dell'oggetto.
# Una rel fuori dal pannello non ha oggetto: resta l'area della classe
# («config») e la rifiuta il service con 400, come prima.
class _PermessoSullOggettoMixin:
    area_funzionale = "config"

    # Scopo: L'oggetto (app_label, model_name) della tabella nominata dalla
    #        rotta, letto dalla lista a DB; None se la rel non e' del pannello.
    def oggetto_permesso_da_richiesta(self) -> tuple[str, str] | None:
        voce = TabelleGestibiliRepository().voce(self.kwargs.get("rel"))  # type: ignore[attr-defined]
        if voce is None or not voce["pannello"]:
            return None
        return voce["app_label"], voce["model_name"]


class ConfigTablesListView(DomainAPIView):
    """GET lista tabelle disponibili."""
    area_funzionale = "config"

    @extend_schema(operation_id="core_config_tables_list", responses={200: inline_serializer(name="ConfigTablesListResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": ConfigCrudService().list_tables()})


class ConfigTableMetadataView(_PermessoSullOggettoMixin, DomainAPIView):
    """GET metadata colonne di una tabella."""

    @extend_schema(
        parameters=[OpenApiParameter(name="rel", type=str, location="path", required=True)],
        responses={200: inline_serializer(name="ConfigTableMetadataResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request, rel: str) -> JsonResponse:
        return success_response({"columns": ConfigCrudService().get_metadata(rel)})


class ConfigTableRecordsView(_PermessoSullOggettoMixin, DomainAPIView):
    """GET lista records, POST crea record."""
    is_search_endpoint = True

    @extend_schema(
        operation_id="core_config_tables_records_list",
        parameters=[
            OpenApiParameter(name="rel", type=str, location="path", required=True),
            *parametri_finestra(),
        ],
        responses={200: inline_serializer(name="ConfigTableRecordsResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request, rel: str) -> JsonResponse:
        # Riusa il lookup esistente, sulla lista del pannello
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = ConfigCrudService().list_records(
            rel,
            search=(qp.get("search") or "").strip() or None,
            order_col=qp.get("order_col", "descrizione"),
            order_dir=qp.get("order_dir", "asc"),
            # Il vocabolario unico dei flag (§A6): prima `attivo_only=banana`
            # valeva true, perche' solo `0/false/no` erano falsi.
            attivo_only=qp_bool_optional(qp.get("attivo_only"), "attivo_only", default=False),
            limit=limit,
            offset=offset,
        )
        return success_response(data)

    @extend_schema(
        request=_RECORD_REQUEST,
        operation_id="core_config_tables_records_create",
        parameters=[OpenApiParameter(name="rel", type=str, location="path", required=True)],
        responses={200: inline_serializer(name="ConfigTableCreateResp", fields={"data": serializers.DictField()})},
    )
    def post(self, request: Request, rel: str) -> JsonResponse:
        return handle_post_json(request, handler=lambda p: ConfigCrudService().create_record(rel, p))


class ConfigTableRecordDetailView(_PermessoSullOggettoMixin, DomainAPIView):
    """GET dettaglio, PATCH aggiorna record."""

    @extend_schema(operation_id="core_config_tables_records_retrieve", responses={200: inline_serializer(name="ConfigRecordDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, rel: str, pk: int) -> JsonResponse:
        return success_response(ConfigCrudService().get_record(rel, pk))

    @extend_schema(request=_RECORD_REQUEST, operation_id="core_config_tables_records_partial_update", responses={200: inline_serializer(name="ConfigRecordUpdateResp", fields={"data": serializers.DictField()})})
    def patch(self, request: Request, rel: str, pk: int) -> JsonResponse:
        return success_response(ConfigCrudService().update_record(rel, pk, corpo_oggetto(request)))
