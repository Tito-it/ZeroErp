# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views clienti — view sottili, logica nel service.
#        Lista paginata, dettaglio, creazione cliente.
#        Ref: docs/it/dev/work-in-progress/sviluppo-gestione-clienti.md
# ------------------------------------------------------------

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import corpo_oggetto, optional_int, paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.core.services.permissions_resolver import PermissionResolver
from apps.anagrafiche.services.clienti_service import ClientiService
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS


# =================================================================
# Clienti lista + crea
# =================================================================

class ClientiView(DomainAPIView):
    """GET lista paginata, POST crea cliente."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")
    is_search_endpoint = True
    lista_codice = "anagrafiche.clienti"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="stato_cliente_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="ClientiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata clienti con search e filtri utility/stato.
    #        Applica scope emittente fiscale (refactor operatore-emittenti,
    #        BE-3.5): un operatore vede solo i clienti dei BA del proprio
    #        emittente; superuser/admin globale/"0 emittenti" bypassano
    #        (emittente_ids = None).
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        utility_id = optional_int({"v": request.query_params.get("utility_id")}, "v")
        stato_id = optional_int({"v": request.query_params.get("stato_cliente_id")}, "v")
        # sr_ids perche' la query filtra su
        # emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache=cache)
        svc = ClientiService()
        results, total = svc.list_clienti(
            search=p["search"],
            utility_id=utility_id,
            stato_cliente_id=stato_id,
            emittente_ids=emittente_ids,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="ClienteCreateReq", fields={
            "soggetto_id": serializers.UUIDField(),
            "utility_id": serializers.IntegerField(),
            "istanza_utility_id": serializers.IntegerField(required=False),
            "billing_account_id": serializers.IntegerField(required=False),
            "indirizzo_dettaglio_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "ba_fatturazione_ordini": serializers.CharField(required=False),
            "ba_parent_account_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="ClienteCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea cliente completo (istanza + BA + cliente in transazione atomica).
    #        Passa auth_user_id al service per il guard refactor
    #        operatore-emittenti (Q6: admin globale non crea BA).
    def post(self, request: Request) -> JsonResponse:
        # DomainAPIView garantisce richiesta autenticata via ZeroERPPermission.
        auth_user_id = request.user.id
        svc = ClientiService()
        return handle_post_json(
            request,
            handler=lambda payload: svc.crea_cliente(
                payload, auth_user_id=auth_user_id
            ),
        )


# =================================================================
# Cliente dettaglio
# =================================================================

class ClientiDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna cliente."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        responses={200: inline_serializer(name="ClienteDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio completo di un cliente.
    def get(self, request: Request, cliente_id: int) -> JsonResponse:
        svc = ClientiService()
        data = svc.get_cliente(cliente_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="ClienteUpdateReq", fields={
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "garanzia_tipo": serializers.CharField(required=False),
            "garanzia_importo": serializers.FloatField(required=False),
        }),
        responses={200: inline_serializer(name="ClienteUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna campi editabili del cliente (pagamento, garanzia, servizio).
    #        ⛔ `iva_id`, `cliente_pa` e `split_payment` sono usciti il 2026-08-29
    #        (I0/D7-bis/D8): le prime due colonne non esistono piu' su
    #        `anagrafiche.clienti`, i due flag vivono ora su `anagrafiche.soggetti`
    #        e si aggiornano dalla PATCH del soggetto.
    def patch(self, request: Request, cliente_id: int) -> JsonResponse:
        svc = ClientiService()
        result = svc.update_cliente(cliente_id, corpo_oggetto(request))
        return success_response(result)


# =================================================================
# Lookup utility ammesse per creazione manuale
# =================================================================

class UtilitiesManualLookupView(DomainAPIView):
    """GET utility con richiede_pdp=false per creazione manuale cliente."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="UtilitiesManualResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista utility ammesse per creazione manuale (richiede_pdp = false).
    def get(self, request: Request) -> JsonResponse:
        svc = ClientiService()
        results = svc.list_utilities_manuali()
        return success_response({"results": results})


# =================================================================
# Export lista clienti — DEF-1 (CSV / Excel)
# =================================================================

# Codice della lista nel registry `ui.lista_definizione`. Stabile per
# ambiente: usato sia per il filename del file generato sia per leggere
# il catalogo colonne (etichette, esportabile, tipo_colonna).
_LISTA_CODICE_CLIENTI = "anagrafiche.clienti"


class ClientiExportView(DomainAPIView):
    """GET /api/v1/anagrafiche/clienti/export/?formato=csv|xlsx

    Genera un file CSV o Excel con i clienti filtrati dalla query string
    (stessi parametri del list endpoint: search, utility_id, stato).
    Hard cap 10.000 righe — sopra solleva E_UI_EXPORT_LIMIT_EXCEEDED
    (422). Usa il renderer generico `ListaExportService` (DEF-1) e il
    catalogo colonne registrato in `ui.lista_colonna` per coerenza con
    quanto l'utente vede nella DataTable.

    Pattern endpoint dedicato (decisione 2 _def.md): path separato
    `/export/` invece di parametro su list endpoint, per chiarezza
    semantica e throttle indipendente.

    NB: il parametro si chiama `formato` (italiano) NON `format`. `format`
    e' un magic query parameter di DRF (content-negotiation
    URL_FORMAT_OVERRIDE): se non ha un renderer registrato per il valore
    passato, DRF risponde 404 PRIMA di entrare nella view, mascherando
    l'endpoint. Pattern documentato: usare nomi italiani per query param
    custom evita collisioni con DRF default.
    """
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")
    is_search_endpoint = True
    lista_codice = "anagrafiche.clienti"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="stato_cliente_id", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Restituisce il file di export. Validazione formato lato
    #        view (la decodifica a 422 e' fatta dal service render).
    #        Riusa `ClientiService.list_clienti` con `limit=EXPORT_MAX_ROWS+1`
    #        per intercettare overflow: se il dataset "filtrato" supera
    #        il cap, il service renderer rifiuta con messaggio parlante.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)

        # Stessi filtri del list endpoint, niente paginazione.
        # `limit=EXPORT_MAX_ROWS+1` per intercettare l'overflow: il guard
        # limite e la coda render+response vivono in `build_export_response`.
        p = parse_list_params(
            request.query_params,
            default_order="ragione_sociale_completa",
        )
        utility_id = optional_int(
            {"v": request.query_params.get("utility_id")}, "v",
        )
        stato_id = optional_int(
            {"v": request.query_params.get("stato_cliente_id")}, "v",
        )
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(
            request.user, cache=cache,
        )

        svc = ClientiService()
        results, total = svc.list_clienti(
            search=p["search"],
            utility_id=utility_id,
            stato_cliente_id=stato_id,
            emittente_ids=emittente_ids,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        filtri_applicati = svc.resolve_filtri_export_label(
            utility_id=utility_id,
            stato_cliente_id=stato_id,
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_CLIENTI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )
