# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory della API view "riepilogo IVA" dei documenti vendita.
#        Estrazione regola-del-2 (memoria feedback_regola_del_2_estrai_bb):
#        la classe era clonata identica in preventivi e ordini (il DDT
#        sarebbe stata la terza copia); cambiavano solo nomi OpenAPI, kwarg
#        URL e service chiamato. Qui vive il flusso condiviso; ogni dominio
#        dichiara i delta via `build_riepilogo_iva_view(...)`.
#
#        Testabilita' (stesso contratto di sorgente_documenti_views): il
#        service arriva come CLOSURE definita nel modulo del dominio, che
#        legge il global di modulo a call-time — i patch dei test su
#        `apps.vendite.services.<dominio>_service.list_riepilogo_iva`
#        continuano a funzionare.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response


# Scopo: Costruisce la view GET riepilogo-iva per un dominio documento.
#        Parametri:
#         - schema_prefix: prefisso nomi OpenAPI (es. "Ordine" ->
#                          "OrdineRiepilogoIvaResponse")
#         - url_kwarg:     nome del kwarg URL del documento (es. "ordine_id")
#         - list_call:     closure dominio (documento_id) -> list[dict]
#                          (service.list_riepilogo_iva)
#         - doc:           docstring completa della classe (testo dominio
#                          preservato 1:1 per OpenAPI/description)
#         - model_permission: oggetto del catalogo permessi del documento
#                          (es. ("vendite", "preventivo")): la view e' una
#                          parte dell'oggetto e ne chiede il livello
#                          (brief-db-be-fe-catalogo-oggetti-permessi §3.2).
#                          None = solo l'area.
def build_riepilogo_iva_view(
    *,
    schema_prefix: str,
    url_kwarg: str,
    list_call: Callable[[int], list[dict[str, Any]]],
    doc: str,
    model_permission: tuple[str, str] | None = None,
) -> type[DomainAPIView]:
    class _RiepilogoIvaView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}RiepilogoIvaResponse",
                fields={"data": serializers.ListField(child=serializers.DictField())},
            )},
        )
        # Scopo: Restituisce via GET il riepilogo IVA aggregato del documento.
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(list_call(int(kwargs[url_kwarg])))

    _RiepilogoIvaView.__doc__ = doc
    _RiepilogoIvaView.__name__ = f"Api{schema_prefix}RiepilogoIva"
    _RiepilogoIvaView.__qualname__ = _RiepilogoIvaView.__name__
    if model_permission is not None:
        _RiepilogoIvaView.model_permission = model_permission
    return _RiepilogoIvaView
