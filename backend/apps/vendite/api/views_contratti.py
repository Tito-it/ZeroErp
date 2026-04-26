# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.contratti (CRUD v5 — F2-BE-06).
#        Espone: testata + righe + utility 1:1 + cambio stato.
#        I trigger DB sono autoritativi per le coerenze cross-table
#        (modalita' C, tipo/classe utenza, overlap); il service
#        traduce gli errori P0001 in codici applicativi consumati
#        dal frontend via error envelope uniforme.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_str,
)
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.vendite.services.contratti_service import ContrattiService


# Scopo: Converte un query param intero opzionale (None se assente o vuoto).
def _qp_int_optional(raw: str | None, name: str) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name}_invalid") from exc


def _qp_iso_date(raw: str | None) -> date | None:
    return parse_iso_date(raw) if raw else None


# =================================================================
# Lista + creazione testata
# =================================================================


_CONTRATTO_CREATE_REQUEST = inline_serializer(
    name="VenditeContrattoCreateReq",
    fields={
        "billing_account_id": serializers.IntegerField(),
        "istanza_utility_id": serializers.IntegerField(),
        "utility_id": serializers.IntegerField(),
        "ambito": serializers.CharField(required=False),
        "valido_dal": serializers.DateField(),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "parent_contratto_id": serializers.IntegerField(required=False, allow_null=True),
        "data": serializers.DateField(required=False),
        "listino_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "utility": serializers.DictField(required=False),
    },
)


_CONTRATTO_PATCH_REQUEST = inline_serializer(
    name="VenditeContrattoPatchReq",
    fields={
        "ambito": serializers.CharField(required=False),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "parent_contratto_id": serializers.IntegerField(required=False, allow_null=True),
        "data": serializers.DateField(required=False),
        "listino_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


class ApiContrattiList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su numero contratto e ragione sociale BA."),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_doc_contratto_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="ambito", type=str, required=False,
                             description="COMMODITY | COMMERCIO"),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO YYYY-MM-DD. Default: 1 gennaio anno-1."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="numero | data | valido_dal | valido_al | "
                                         "ba_ragione_sociale | stato_codice | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeContrattiListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata contratti con filtri standard.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        svc = ContrattiService()
        results, total = svc.list_contratti(
            search=p["search"],
            billing_account_id=_qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
            stato_doc_contratto_id=_qp_int_optional(qp.get("stato_doc_contratto_id"), "stato_doc_contratto_id"),
            utility_id=_qp_int_optional(qp.get("utility_id"), "utility_id"),
            ambito=qp_str(qp.get("ambito")),
            listino_id=_qp_int_optional(qp.get("listino_id"), "listino_id"),
            data_da=_qp_iso_date(qp.get("data_da")),
            data_a=_qp_iso_date(qp.get("data_a")),
            scadenza_mese=qp_str(qp.get("scadenza_mese")),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_CONTRATTO_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuovo contratto. Numero generato dal service; stato DRAFT.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ContrattiService().create_contratto)


class ApiContrattoDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio contratto (testata + utility 1:1 + righe).
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        del request
        return success_response(ContrattiService().get_contratto(contratto_id))

    @extend_schema(
        request=_CONTRATTO_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi mutabili. Numero/identificativi/stato immutabili
    #        in PATCH (cambio stato via endpoint dedicato).
    def patch(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().update_contratto(contratto_id, request.data)
        )


# =================================================================
# Cambio stato
# =================================================================


_CONTRATTO_STATO_REQUEST = inline_serializer(
    name="VenditeContrattoStatoReq",
    fields={
        "codice_interno": serializers.CharField(),
        "valido_al": serializers.DateField(
            required=False, allow_null=True,
            help_text="Opzionale: data fine validita' (cessazione contestuale al cambio stato).",
        ),
    },
)


class ApiContrattoCambiaStato(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_CONTRATTO_STATO_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoStatoResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato del contratto (DRAFT/ATTIVO/SOSPESO/CESSATO).
    #        Se valido_al e' fornito, applica anche PATCH valido_al nella
    #        stessa transazione (caso d'uso: dialog "Cessa contratto" che
    #        chiede la data al click). Trigger DB fa fail-fast su
    #        attivazione modalita' C incompleta.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        body = request.data or {}
        codice = body.get("codice_interno", "")
        valido_al_raw = body.get("valido_al")
        valido_al = parse_iso_date(valido_al_raw) if valido_al_raw else None
        return success_response(
            ContrattiService().cambia_stato(
                contratto_id, codice_interno=codice, valido_al=valido_al,
            )
        )


# =================================================================
# Righe contratto
# =================================================================


_RIGA_CREATE_REQUEST = inline_serializer(
    name="VenditeContrattoRigaCreateReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        "tipo_erogazione": serializers.CharField(required=False),
        "fonte_quantita_attesa": serializers.CharField(required=False),
        "periodicita": serializers.CharField(required=False),
        "generazione_canone": serializers.CharField(required=False),
        "competenza_canone": serializers.CharField(required=False),
        "prezzo_unitario": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "quantita_fissa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "qta_operativa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "factor_to_base": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False,
        ),
        "ordine": serializers.IntegerField(required=False),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


_RIGA_PATCH_REQUEST = inline_serializer(
    name="VenditeContrattoRigaPatchReq",
    fields={
        "tipo_erogazione": serializers.CharField(required=False),
        "fonte_quantita_attesa": serializers.CharField(required=False),
        "periodicita": serializers.CharField(required=False),
        "generazione_canone": serializers.CharField(required=False),
        "competenza_canone": serializers.CharField(required=False),
        "prezzo_unitario": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "quantita_fissa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "qta_operativa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "factor_to_base": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False,
        ),
        "ordine": serializers.IntegerField(required=False),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


class ApiContrattoRigheList(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RIGA_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge una riga al contratto.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().create_riga(contratto_id, request.data)
        )


class ApiContrattoRighePreview(DomainAPIView):
    """GET preview righe applicate dal contratto.

    Modalita' A: tutte le righe del listino con prezzo finale = prezzo
    listino + variazione globale (origine='DA_LISTINO').

    Modalita' B: tutte le righe del listino, con override applicato dove
    presente in contratti_righe (origine='OVERRIDE') o variazione globale
    sulle altre (origine='DA_LISTINO').

    Modalita' C: lista righe vuota (le righe vivono in contratti_righe e
    sono lette dall'endpoint standard /righe/).

    Endpoint readonly: il FE lo usa per mostrare l'anteprima dei prezzi
    applicati al cliente senza duplicare la formula di calcolo.
    """

    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoRighePreviewResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce envelope con testata sintetica + righe preview.
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        del request
        return success_response(
            ContrattiService().list_righe_preview(contratto_id)
        )


class ApiContrattoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RIGA_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna una riga (articolo_id immutabile).
    def patch(self, request: Request, contratto_id: int, riga_id: int) -> JsonResponse:
        del contratto_id  # riga_id e' identificatore globale; contratto_id solo per coerenza URL.
        return success_response(ContrattiService().update_riga(riga_id, request.data))

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoRigaDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cancella una riga (FK note_contratto blocca via trigger).
    def delete(self, request: Request, contratto_id: int, riga_id: int) -> JsonResponse:
        del request, contratto_id
        ContrattiService().delete_riga(riga_id)
        return success_response({"deleted": True, "id": riga_id})


# =================================================================
# Utility 1:1
# =================================================================


_UTILITY_REQUEST = inline_serializer(
    name="VenditeContrattoUtilityReq",
    fields={
        "istanza_dati_precontrattuali_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "param_1_num": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "param_2_txt": serializers.CharField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


class ApiContrattoUtility(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_UTILITY_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea la riga utility 1:1 per il contratto.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().create_utility(contratto_id, request.data)
        )

    @extend_schema(
        request=_UTILITY_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna la riga utility (istanza/utility immutabili).
    def patch(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().update_utility(contratto_id, request.data)
        )
