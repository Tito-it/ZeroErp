# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory della API view «legami» dei documenti vendita che si
#        annullano con conferma (bolla, ordine, preventivo, contratto,
#        commessa) + le cinque view di dominio. Il flusso e' lo stesso per tutti: cambiano
#        i nomi OpenAPI, il kwarg URL e il lettore del service (che legge
#        prima la testata del suo documento: 404 col codice del dominio).
#        Stessa architettura di lineage_views.
# ------------------------------------------------------------

# brief-db-annullo-documento-con-legami R-1 (2026-10-11): la finestra di
# conferma dell'annullo legge da qui che cosa si riapre e dove. Il BB del
# backend e' `services/_annullo_con_legami.legami_del_documento`.
# La commessa (brief-db-annullo-a-valle-riapre-a-monte D-2, 2026-10-12) e' la
# quinta: annullarla riapre a monte cio' che l'ha riempita.

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response


# Scopo: Costruisce la view GET /vendite/<dominio>/<id>/legami/. Parametri:
#         - schema_prefix: prefisso dei nomi OpenAPI (es. "Ordine")
#         - url_kwarg: nome del kwarg URL del documento (es. "ordine_id")
#         - lettore: `id -> dict`, risolto a OGNI chiamata (lambda sul modulo
#                    del service), cosi' i patch dei test sul service valgono
#         - model_permission: oggetto del catalogo permessi del documento;
#                    None = il solo livello d'area (la commessa non ha un
#                    oggetto suo nel catalogo, come per i suoi passaggi)
def build_legami_view(
    *,
    schema_prefix: str,
    url_kwarg: str,
    lettore: Callable[[int], dict[str, Any]],
    model_permission: tuple[str, str] | None,
) -> type[DomainAPIView]:
    class _LegamiView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}LegamiResponse",
                fields={"data": inline_serializer(
                    name=f"{schema_prefix}LegamiData",
                    fields={
                        "documento": serializers.CharField(),
                        "id": serializers.IntegerField(),
                        "legami": serializers.IntegerField(),
                        "righe": serializers.ListField(child=serializers.DictField()),
                    },
                )},
            )},
        )
        # Scopo: I legami del documento, per la finestra di conferma dell'annullo.
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(lettore(int(kwargs[url_kwarg])))

    if model_permission is not None:
        _LegamiView.model_permission = model_permission
    _LegamiView.__doc__ = f"""GET /api/v1/vendite/.../<id>/legami/

    Legami del documento ({schema_prefix}) che l'annullo riapre: una riga per
    legame (`vendite.fn_documento_legami`), il loro numero (`legami`, da
    dichiarare nella conferma come `legami_confermati`) e il nome del documento
    dall'altra parte, dal lineage.
    """
    _LegamiView.__name__ = f"Api{schema_prefix}Legami"
    _LegamiView.__qualname__ = _LegamiView.__name__
    return _LegamiView


# Le view di dominio. Import locali nelle lambda: il modulo del service si
# risolve a call-time (patch dei test, nessun ciclo di import).
def _ddt(documento_id: int) -> dict[str, Any]:
    from apps.vendite.services import ddt_service
    return ddt_service.get_legami(documento_id)


def _ordine(documento_id: int) -> dict[str, Any]:
    from apps.vendite.services import ordini_service
    return ordini_service.get_legami(documento_id)


def _preventivo(documento_id: int) -> dict[str, Any]:
    from apps.vendite.services import preventivi_service
    return preventivi_service.get_legami(documento_id)


def _contratto(documento_id: int) -> dict[str, Any]:
    from apps.vendite.services.contratti_service import ContrattiService
    return ContrattiService().get_legami(documento_id)


def _commessa(documento_id: int) -> dict[str, Any]:
    from apps.vendite.services import commesse_service
    return commesse_service.get_legami(documento_id)


ApiDdtLegami = build_legami_view(
    schema_prefix="Ddt", url_kwarg="ddt_id", lettore=_ddt,
    model_permission=("vendite", "ddt"),
)
ApiOrdineLegami = build_legami_view(
    schema_prefix="Ordine", url_kwarg="ordine_id", lettore=_ordine,
    model_permission=("vendite", "ordine"),
)
ApiPreventivoLegami = build_legami_view(
    schema_prefix="Preventivo", url_kwarg="preventivo_id", lettore=_preventivo,
    model_permission=("vendite", "preventivo"),
)
ApiContrattoLegami = build_legami_view(
    schema_prefix="Contratto", url_kwarg="contratto_id", lettore=_contratto,
    model_permission=("vendite", "contratto"),
)
ApiCommessaLegami = build_legami_view(
    schema_prefix="Commessa", url_kwarg="commessa_id", lettore=_commessa,
    model_permission=None,
)
