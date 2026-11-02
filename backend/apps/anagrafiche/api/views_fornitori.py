# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views fornitori — view sottili, logica nel service.
#        Lista paginata, dettaglio, creazione e aggiornamento fornitore.
#        Pattern allineato a views_clienti.py (semplificato).
# ------------------------------------------------------------

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, optional_int, paginated_envelope, parse_list_params, qp_bool_optional
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.fornitori_service import FornitoriService
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.api.openapi_params import param_ricerca_full


# Codice della lista nel registry `ui.lista_definizione`. Stabile per
# ambiente: usato sia per il filename del file generato sia per leggere
# il catalogo colonne (etichette, esportabile, tipo_colonna).
_LISTA_CODICE_FORNITORI = "anagrafiche.fornitori"


# =================================================================
# Fornitori lista + crea
# =================================================================

class FornitoriView(DomainAPIView):
    """GET lista paginata, POST crea fornitore."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")
    is_search_endpoint = True
    lista_codice = "anagrafiche.fornitori"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="stato_fornitore_id", type=int, required=False),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="FornitoriListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata fornitori con search e filtri stato/attivo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        stato_id = optional_int({"v": request.query_params.get("stato_fornitore_id")}, "v")
        # Filtro opzionale: None quando il parametro manca (nessun filtro), non False.
        attivo = qp_bool_optional(request.query_params.get("attivo"), "attivo")
        svc = FornitoriService()
        results, total = svc.list_fornitori(
            search=p["search"],
            stato_fornitore_id=stato_id,
            attivo=attivo,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="FornitoreCreateReq", fields={
            "soggetto_id": serializers.UUIDField(),
            "valuta_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "giorni_pagamento": serializers.IntegerField(required=False),
            "fine_mese": serializers.BooleanField(required=False),
            "split_payment": serializers.BooleanField(required=False),
            "ritenuta_acconto": serializers.BooleanField(required=False),
            "ritenuta_aliquota": serializers.FloatField(required=False),
            "regime_fiscale": serializers.CharField(required=False),
            "bollo_esente": serializers.BooleanField(required=False),
            "canale_fe": serializers.CharField(required=False),
            "pec_email": serializers.CharField(required=False),
            "rating": serializers.IntegerField(required=False),
            "qualifica_scadenza": serializers.DateField(required=False),
            "note": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="FornitoreCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea fornitore completo (ruolo FO + insert in transazione atomica).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=FornitoriService().crea_fornitore)


# =================================================================
# Fornitore dettaglio
# =================================================================

class FornitoriDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna fornitore."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")

    @extend_schema(
        responses={200: inline_serializer(name="FornitoreDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio completo di un fornitore.
    def get(self, request: Request, fornitore_id: int) -> JsonResponse:
        svc = FornitoriService()
        data = svc.get_fornitore(fornitore_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="FornitoreUpdateReq", fields={
            "stato_fornitore_id": serializers.IntegerField(required=False),
            "attivo": serializers.BooleanField(required=False),
            "valuta_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "giorni_pagamento": serializers.IntegerField(required=False),
            "fine_mese": serializers.BooleanField(required=False),
            "split_payment": serializers.BooleanField(required=False),
            "ritenuta_acconto": serializers.BooleanField(required=False),
            "ritenuta_aliquota": serializers.FloatField(required=False),
            "regime_fiscale": serializers.CharField(required=False),
            "bollo_esente": serializers.BooleanField(required=False),
            "canale_fe": serializers.CharField(required=False),
            "pec_email": serializers.CharField(required=False),
            "rating": serializers.IntegerField(required=False),
            "qualifica_scadenza": serializers.DateField(required=False),
            "note": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="FornitoreUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna campi editabili del fornitore (pagamento, fiscale, FE, rating, note).
    def patch(self, request: Request, fornitore_id: int) -> JsonResponse:
        svc = FornitoriService()
        result = svc.update_fornitore(fornitore_id, corpo_oggetto(request))
        return success_response(result)


class FornitoriExportView(DomainAPIView):
    """GET /api/v1/anagrafiche/fornitori/export/?formato=csv|xlsx

    Genera un file CSV o Excel con i fornitori filtrati dalla query string
    (stessi parametri del list endpoint: search, stato_fornitore_id).
    Hard cap 10.000 righe — sopra solleva E_UI_EXPORT_LIMIT_EXCEEDED
    (422). Usa il renderer generico `ListaExportService` (DEF-1) e il
    catalogo colonne registrato in `ui.lista_colonna` per coerenza con
    quanto l'utente vede nella DataTable.

    Pattern endpoint dedicato (DEF-8 gemello clienti/soggetti): path
    separato `/export/` invece di parametro su list endpoint, per chiarezza
    semantica e throttle indipendente.

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata
    prima della view.
    """
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")
    is_search_endpoint = True
    lista_codice = "anagrafiche.fornitori"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="stato_fornitore_id", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Restituisce il file di export. Validazione formato lato view
    #        (la decodifica a 422 e' fatta dal service render). Riusa
    #        `FornitoriService.list_fornitori` con `limit=EXPORT_MAX_ROWS+1`
    #        per intercettare overflow: se il dataset filtrato supera il
    #        cap, blocca senza serializzare.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)

        p = parse_list_params(
            request.query_params,
            default_order="ragione_sociale_completa",
        )
        stato_id = optional_int(
            {"v": request.query_params.get("stato_fornitore_id")}, "v",
        )

        svc = FornitoriService()
        results, total = svc.list_fornitori(
            search=p["search"],
            stato_fornitore_id=stato_id,
            attivo=None,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        filtri_applicati = svc.resolve_filtri_export_label(
            stato_fornitore_id=stato_id,
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_FORNITORI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )
