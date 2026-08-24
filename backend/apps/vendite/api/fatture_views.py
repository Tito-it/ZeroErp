# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view di CONSULTAZIONE della fattura — dettaglio completo
#        (testata + righe + riepilogo IVA + scadenze) per il drawer di
#        visualizzazione. Sola lettura: la fattura si produce dalla pipeline
#        di fatturazione e oltre EMESSA le righe sono congelate a DB
#        (`trgfn_fatture_righe_guard_congelamento`), quindi qui non esiste
#        nessun verbo di modifica.
#        Le view dei documenti generati (stampa/allegati) vivono in
#        `fatture_documenti_views.py`; le azioni di processo (emissione,
#        numerazione, ristampa massiva) nel cockpit fatturazione.
#        Brief: docs/it/dev/work-done/brief-be-fe-drawer-fattura.md §5
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id
from apps.core.api.payload_validators import qp_int_strict
from apps.core.services.value_normalizer import as_bool
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import (
    get_fattura_dettaglio,
    get_fattura_giornale,
)


class ApiFatturaDetail(DomainAPIView):
    """Dettaglio completo di una fattura per la consultazione a video.

    Restituisce in un solo round-trip testata (cliente, emittente, pagamento,
    totali, tutto gia' decodificato), righe, riepilogo IVA e piano rate — gli
    stessi quattro lettori che alimentano il contesto del PDF, cosi' video e
    stampa mostrano lo stesso documento per costruzione — piu' i `contatori`
    dei badge (note), che il drawer mostra senza una seconda chiamata.

    Fattura inesistente **o fuori scope emittente** → 404 identico: un errore
    che distinguesse i due casi confermerebbe l'esistenza di una fattura altrui.
    """

    area_funzionale = "vendite"
    # `vendite.fattura` E' catalogato in `config.area_model_overrides`: un admin
    # puo' bloccare le fatture come singolo oggetto, e il drawer deve
    # rispettarlo. Senza override il resolver ricade sul livello area, quindi
    # per l'operatore normale non cambia nulla.
    model_permission = ("vendite", "fattura")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeFatturaDettaglioResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturaDettaglioData",
                        fields={
                            "fattura": serializers.DictField(),
                            "righe": serializers.ListField(child=serializers.DictField()),
                            "riepilogo_iva": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            "scadenze": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            # Badge della barra azioni del drawer senza un
                            # secondo round-trip. Dict (non scalare) per
                            # reggere i prossimi contatori.
                            "contatori": inline_serializer(
                                name="VenditeFatturaDettaglioContatori",
                                fields={"note": serializers.IntegerField()},
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il documento fattura completo per il drawer.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        # `get_scope_user_id` ritorna None per il superuser (vede tutto): lo
        # scope applicativo si somma alla RLS, non la sostituisce.
        data = get_fattura_dettaglio(
            fattura_id=fattura_id,
            auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)


class ApiFatturaGiornale(DomainAPIView):
    """La STORIA di una fattura: cosa le e' successo, in ordine di tempo.

    Elenco paginato e di sola lettura dalla vista cucita
    `script.vw_giornale_entita`, che unisce i registri di evento del progetto in
    una forma normalizzata — per la fattura oggi risponde `vendite.fatture_log`.

    ⭐ E' il **primo consumatore** di quella vista: fino al 2026-08-24 il suo
    perimetro era verificato dal pgTAP e non dall'uso.

    ⛔ Non e' il pannello «Collegamenti» (`/passaggi/`), che dice **con quali
    altri documenti** questo e' legato: qui si risponde a *«cosa gli e'
    successo»*, che e' una domanda diversa e ha una sorgente diversa.

    Fattura inesistente **o fuori scope emittente** → 404 identico. ⚠️ E il 404
    lo decide la TESTATA, non la vista: quella e' `security_invoker` e su una
    fattura altrui risponderebbe zero righe, cioe' «non e' successo niente»
    invece di «non la vedi».
    """

    area_funzionale = "vendite"
    # Stesso livello oggetto del dettaglio: chi non puo' vedere la fattura non
    # ne vede nemmeno la storia.
    model_permission = ("vendite", "fattura")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="page_size", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="sort_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento: `gravita` (default, i piu' gravi "
                    "prima) oppure `quando`. Un valore fuori whitelist ricade "
                    "sul default. ⛔ L'ordinamento e' del SERVER perche' la "
                    "lista e' paginata: ordinare la sola pagina caricata "
                    "risponderebbe a una domanda piu' stretta senza dirlo."
                ),
            ),
            OpenApiParameter(
                name="sort_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Verso: `desc` (default) o `asc`.",
            ),
            OpenApiParameter(
                name="ritirate",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Include anche le segnalazioni RITIRATE (`disabilitato`), che di "
                    "default sono nascoste perche' appartengono a un tentativo poi "
                    "rifatto. Quante ne sono state nascoste lo dice `ritirate_count`."
                ),
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeFatturaGiornaleResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturaGiornaleData",
                        fields={
                            "fattura_id": serializers.IntegerField(),
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "ritirate_count": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il giornale paginato della fattura.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        q = request.query_params
        data = get_fattura_giornale(
            fattura_id=fattura_id,
            page=qp_int_strict(q.get("page"), "page", 1),
            page_size=qp_int_strict(q.get("page_size"), "page_size", 50),
            includi_ritirate=as_bool(q.get("ritirate"), default=False),
            sort_by=q.get("sort_by") or "gravita",
            sort_dir=q.get("sort_dir") or "desc",
            auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)
