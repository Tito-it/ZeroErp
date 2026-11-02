# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La base della lettura «come si puo' erogare questo articolo su una riga
#        di questo documento», comune a contratto e offerta:
#        GET …/<id>/righe/erogazioni/?articolo_id=<uuid>.
# Note: brief-db-offerta-emissione-ed-erogazione B-R4 (§C.9.6), 2026-10-07.
# ------------------------------------------------------------

# ⭐ REGOLA DEL 2. Il DB risponde con UNA funzione per i due documenti
#    (`vendite.fn_documento_riga_erogazioni`), e il form che la legge e' UNO
#    (`RigheEccezioniDrawer`): la view e' una, le due sottoclassi dichiarano
#    solo il permesso dell'oggetto, il nome dell'id nel path e il service.

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response

_RIGA_EROGAZIONE = inline_serializer(
    name="VenditeRigaErogazione",
    fields={
        "tipo_erogazione": serializers.CharField(),
        "fonte_quantita_attesa": serializers.CharField(),
        "e_default": serializers.BooleanField(),
        "origine": serializers.CharField(),
    },
)


class RigaErogazioniView(DomainAPIView):
    """GET …/<id>/righe/erogazioni/?articolo_id=<uuid>

    Le combinazioni (tipo_erogazione, fonte_quantita_attesa) che una riga con
    l'articolo puo' avere sul documento, il default (`e_default`) in testa:
    quello che la riga erediterebbe senza indicarle. ⛔ Il backend le trasporta,
    non le deduce: sono le righe della stessa sede che il DB legge per
    l'eredita' e per il guard del perimetro.
    """

    area_funzionale = "vendite"
    # Il nome dell'id del documento nel path (`contratto_id`, `offerta_id`).
    url_kwarg: str = ""

    # Scopo: le combinazioni dal service del dominio. Le sottoclassi la
    #        scrivono; qui non c'e' un ripiego, che risponderebbe per il
    #        documento sbagliato.
    def elenco(self, documento_id: int, articolo_id: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="articolo_id", type=str, required=True,
                description=(
                    "L'articolo della riga (UUID). Lista vuota se la sua "
                    "tipologia di listino non e' fra quelle della utility del "
                    "documento: su questo documento non si vende."
                ),
            ),
        ],
        responses={200: inline_serializer(
            name="VenditeRigaErogazioniResp",
            fields={"data": inline_serializer(
                name="VenditeRigaErogazioniData",
                fields={"results": serializers.ListField(child=_RIGA_EROGAZIONE)},
            )},
        )},
    )
    # Scopo: le combinazioni per (documento, articolo), nell'envelope dei
    #        lookup (`{"results": [...]}`).
    def get(self, request: Request, **kwargs: Any) -> JsonResponse:
        documento_id = int(kwargs[self.url_kwarg])
        results = self.elenco(documento_id, request.query_params.get("articolo_id"))
        return success_response({"results": results})
