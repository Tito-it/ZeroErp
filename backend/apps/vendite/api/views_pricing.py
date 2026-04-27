# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API diagnostica pricing v5. Espone il resolver
#        `vendite.fn_resolve_prezzo_listino_v2` via endpoint leggero
#        per smoke test, debug UI e supporto operativo.
#        Nessun side-effect: pura lettura deterministica.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services.pricing_service import (
    PARAM_MAX_MAGGIORAZIONE_PCT,
    PARAM_MAX_SCONTO_PCT,
    PricingService,
)


_RESOLVE_REQUEST = inline_serializer(
    name="VenditePricingResolveReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        "uom_id": serializers.IntegerField(),
        "data_riferimento": serializers.DateField(),
        "ba_id": serializers.IntegerField(),
        "utility_id": serializers.IntegerField(),
        "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "emittente_soggetto_ruolo_id": serializers.IntegerField(
            required=False, allow_null=True,
            help_text="Override esplicito emittente. Se assente, derivato dal JWT operatore.",
        ),
    },
)


_RESOLVE_RESPONSE = inline_serializer(
    name="VenditePricingResolveResp",
    fields={
        "prezzo_finale": serializers.DecimalField(max_digits=22, decimal_places=10),
        "prezzo_base_snapshot": serializers.DecimalField(max_digits=22, decimal_places=10),
        "tipo_variazione_applicata": serializers.CharField(allow_null=True),
        "valore_variazione_applicata": serializers.DecimalField(
            max_digits=10, decimal_places=4, allow_null=True,
        ),
        "origine": serializers.CharField(),
        "listino_id": serializers.IntegerField(allow_null=True),
        "listino_versione_id": serializers.IntegerField(allow_null=True),
        "listino_riga_id": serializers.IntegerField(allow_null=True),
        "contratto_id": serializers.IntegerField(allow_null=True),
        "promo_id": serializers.IntegerField(allow_null=True),
        "categoria_cliente_listino_id": serializers.IntegerField(allow_null=True),
        "categoria_cliente_id_snapshot": serializers.IntegerField(allow_null=True),
        "classe_utenza_id_snapshot": serializers.IntegerField(allow_null=True),
    },
)


# Scopo: Serializza valori Decimal/date in forma JSON stabile.
def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


# Scopo: Risolve l'emittente_soggetto_ruolo_id dal JWT operatore.
#        Se il payload lo specifica esplicitamente, ha priorita' (debug).
#        Altrimenti prende il primo emittente autorizzato all'utente.
def _resolve_emittente_sr(request: Request, override: int | None) -> int:
    if override is not None and override > 0:
        return int(override)
    emittenti = PermissionResolver.get_emittenti_sr_ids(request.user) or []
    ErrorManager.require(
        len(emittenti) > 0,
        code="E_VENDITE_VALIDATION",
        message="Impossibile risolvere l'emittente fiscale dell'operatore.",
        detail=(
            "L'operatore non ha emittenti autorizzati. Passare "
            "emittente_soggetto_ruolo_id esplicito nel payload."
        ),
    )
    return int(emittenti[0])


class PricingResolveView(DomainAPIView):
    """POST /api/v1/vendite/pricing/resolve/ — resolver pricing v5 diagnostico.

    Area funzionale: `vendite` (livello LETTURA sufficiente). Nessuna
    scrittura, nessun side-effect: wrapper su
    `PricingService.resolve_prezzo()` utile per smoke test, UI di
    debug e supporto. Gli errori applicativi (`E_PREZZO_LISTINO_*`,
    `E_CATEGORIA_LISTINO_*`, `E_ARTICOLO_NON_NEGOZIATO_*`) sono
    mappati in HTTP 400 dal middleware eccezioni.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=_RESOLVE_REQUEST,
        responses={200: _RESOLVE_RESPONSE},
        tags=["vendite"],
        summary="Resolver pricing v5 (3 stadi: PROMO/CONTRATTO/CATEGORIA)",
    )
    def post(self, request: Request):
        # Scopo: handler chiuso sul request per accedere all'user JWT per
        #        la derivazione emittente. Ritorna dict: handle_post_json
        #        lo wrappa in success_response automaticamente.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            articolo_id = payload.get("articolo_id")
            ErrorManager.require(
                articolo_id is not None,
                code="E_VENDITE_VALIDATION",
                message="articolo_id obbligatorio.",
                context={"field": "articolo_id"},
            )
            data_riferimento_raw = payload.get("data_riferimento")
            ErrorManager.require(
                data_riferimento_raw is not None,
                code="E_VENDITE_VALIDATION",
                message="data_riferimento obbligatoria.",
                context={"field": "data_riferimento"},
            )
            data_riferimento = parse_iso_date(str(data_riferimento_raw))

            emittente_sr = _resolve_emittente_sr(
                request, payload.get("emittente_soggetto_ruolo_id"),
            )

            result = PricingService().resolve_prezzo(
                articolo_id=str(articolo_id),
                uom_id=int(payload.get("uom_id") or 0),
                data_riferimento=data_riferimento,
                ba_id=int(payload.get("ba_id") or 0),
                utility_id=int(payload.get("utility_id") or 0),
                emittente_soggetto_ruolo_id=emittente_sr,
                classe_utenza_id=(
                    int(payload["classe_utenza_id"])
                    if payload.get("classe_utenza_id")
                    else None
                ),
            )
            return {k: _serialize_value(v) for k, v in result.items()}

        return handle_post_json(request, handler=_handler)


_LIMITI_UTENTE_RESPONSE = inline_serializer(
    name="VenditePricingLimitiUtenteResp",
    fields={
        "max_sconto_pct": serializers.DecimalField(max_digits=10, decimal_places=4),
        "max_maggiorazione_pct": serializers.DecimalField(max_digits=10, decimal_places=4),
    },
)


class PricingLimitiUtenteView(DomainAPIView):
    """GET /api/v1/vendite/pricing/limiti-utente/ — L2 limiti variazione prezzo.

    Ritorna i limiti percentuali configurati per l'utente corrente:
    `max_sconto_pct` e `max_maggiorazione_pct`. Risolve la cascata
    scope user -> group -> emittente -> default via
    `ParameterService.get_parameter`.

    Il FE usa questi valori per mostrare hint sotto il campo prezzo
    nel drawer riga preventivo (sconto max, warning vicino al limite)
    senza round-trip a ogni modifica.

    Area funzionale: `vendite` (livello LETTURA sufficiente).
    """

    area_funzionale = "vendite"

    @extend_schema(
        responses={200: _LIMITI_UTENTE_RESPONSE},
        tags=["vendite"],
        summary="Limiti L2 variazione prezzo per l'utente corrente",
    )
    def get(self, request: Request):
        auth_user_id = request.user.id if request.user.is_authenticated else None
        # Single round-trip: risolve entrambe le chiavi in una query DB.
        # Valori ritornati come stringa (envelope stabile); il FE le converte
        # in Number (zero-safe) per l'interpolazione dell'hint.
        values = ParameterService().get_defaults(
            [PARAM_MAX_SCONTO_PCT, PARAM_MAX_MAGGIORAZIONE_PCT],
            django_user_id=auth_user_id,
        )

        def _to_decimal_str(raw):
            try:
                return str(Decimal(str(raw)))
            except (InvalidOperation, ValueError, TypeError):
                return "0"

        return success_response({
            "max_sconto_pct": _to_decimal_str(values.get(PARAM_MAX_SCONTO_PCT, "0")),
            "max_maggiorazione_pct": _to_decimal_str(values.get(PARAM_MAX_MAGGIORAZIONE_PCT, "0")),
        })
