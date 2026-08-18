# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only dell'elenco «fondi fattura da decidere» — i casi in cui
#        il giro automatico si ferma e la scelta resta a una persona.
# ------------------------------------------------------------

# Un solo endpoint GET sottile sopra `vendite.vw_fondi_fattura_da_decidere`
# (BE-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3, vista scritta in
# §8.2-quinquies D-10). Livello LETTURA sufficiente: l'elenco PRESENTA e non
# sana, quindi non e' un'azione di processo.
#
# ⚠️ La vista e' `security_invoker=on`: il perimetro emittente lo applica la RLS
# di `vendite.fatture` con l'identita' della richiesta. Va quindi letta con la
# connessione dell'utente e MAI da un canale di sistema (ruolo BYPASSRLS), o il
# perimetro salta. Il filtro applicativo (`auth_user_id` -> scope SR nel
# repository) resta come defense-in-depth, com'e' la convenzione del progetto.
#
# ⚠️ Nessuna capability per riga: le liste non chiamano `fn_available_actions_*`
# riga per riga. Il gating delle azioni lo fa il FE sui codici che la vista
# porta gia' in riga (`motivo`, e lo stato dell'atto dove esiste).

from django.http import JsonResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id
from apps.core.api.payload_validators import qp_int_strict, qp_str, qp_str_upper
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import fn_fondi_fattura_da_decidere


class ApiFondiFatturaDaDecidere(DomainAPIView):
    """GET /api/v1/vendite/fondi-fattura/da-decidere/ — i casi che chiedono una persona."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.fondi_fattura_da_decidere"

    @extend_schema(
        operation_id="vendite_fondi_fattura_da_decidere",
        parameters=[
            OpenApiParameter(
                name="motivo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro motivo (whitelist chiusa, default: tutti): "
                    "PROPOSTA_SENZA_ATTO = la fattura merita un fondo e non ce "
                    "l'ha | IMPORTO_NON_CORRISPONDENTE = il residuo non "
                    "assomiglia al documento e l'automatismo tace | "
                    "NON_PIU_CAPIENTE = l'atto esiste ma la sorgente non lo "
                    "regge piu' | UTILITY_NON_ATTRIBUIBILE = e' nella banda ma "
                    "senza utility, irraggiungibile da qualunque giro. "
                    "Motivo fuori vocabolario -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): data (default) | "
                    "motivo | anno | numero | totale_a_pagare | "
                    "importo_proposto | capienza_attuale. "
                    "Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc (default desc: le "
                    "fatture piu' recenti prima). Valore diverso -> 400."
                ),
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeFondiFatturaDaDecidereResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFondiFatturaDaDecidereData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET l'elenco paginato dei fondi fattura che
    #        chiedono una decisione, filtrabile per motivo.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        motivo = qp_str_upper(qp.get("motivo"))
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        data = fn_fondi_fattura_da_decidere(
            motivo=motivo,
            # Defense-in-depth sopra la RLS invoker della vista: None per
            # superuser (che la RLS gia' non filtra).
            auth_user_id=get_scope_user_id(request),
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
