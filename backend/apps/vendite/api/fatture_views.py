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
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import get_fattura_dettaglio


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
