# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API diagnostica pricing v5. Espone il resolver
#        `vendite.fn_resolve_prezzo_listino_v2` via endpoint leggero
#        per smoke test, debug UI e supporto operativo.
#        Nessun side-effect: pura lettura deterministica.
# ------------------------------------------------------------

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id, handle_post_json
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.parameter_service import ParameterService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.api._serialize_helpers import serialize_value
from apps.vendite.services.pricing_diagnose_service import (
    PricingDiagnoseService,
)
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
        "articolo_padre_contesto": serializers.UUIDField(
            required=False, allow_null=True,
            help_text=(
                "UUID articolo composito padre per attivare STADIO BUNDLE "
                "(modello unificato BoM 2026-05-13). Se fornito, il resolver "
                "cerca prima il prezzo bundle in listini_righe_componenti "
                "per la coppia (padre, figlio); fallback su standalone."
            ),
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
        # Id + denormalizzati (codice/descrizione) via LEFT JOIN nel repository,
        # esposti per UI diagnostica leggibile (TestResolverDialog) senza
        # round-trip aggiuntivi.
        "listino_id": serializers.IntegerField(allow_null=True),
        "listino_codice": serializers.CharField(allow_null=True),
        "listino_descrizione": serializers.CharField(allow_null=True),
        "listino_versione_id": serializers.IntegerField(allow_null=True),
        "listino_versione_codice": serializers.CharField(allow_null=True),
        "listino_riga_id": serializers.IntegerField(allow_null=True),
        "contratto_id": serializers.IntegerField(allow_null=True),
        "contratto_numero": serializers.CharField(allow_null=True),
        "promo_id": serializers.IntegerField(allow_null=True),
        "promo_codice": serializers.CharField(allow_null=True),
        "promo_descrizione": serializers.CharField(allow_null=True),
        "categoria_cliente_listino_id": serializers.IntegerField(allow_null=True),
        "categoria_cliente_id_snapshot": serializers.IntegerField(allow_null=True),
        "categoria_cliente_codice": serializers.CharField(allow_null=True),
        "categoria_cliente_descrizione": serializers.CharField(allow_null=True),
        "classe_utenza_id_snapshot": serializers.IntegerField(allow_null=True),
        "classe_utenza_descrizione": serializers.CharField(allow_null=True),
    },
)


# ⛔ I tre id obbligatori del resolver (pagina `api_pricing.md`) dal BB: fino al
#    2026-10-20 `int(payload.get(x) or 0)` faceva di un campo assente uno 0, che
#    arrivava al DB e tornava come un errore generico invece che sul campo.
_V = PayloadValidator(validation_code="E_VENDITE_VALIDATION")


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


# Scopo: la `data_riferimento` del corpo, OBBLIGATORIA, come `date`. Una per
#        resolve e diagnose (regola del 2, ok Tid 2026-10-09).
# ⚠️ L'obbligo si giudica sulla data CONVERTITA: `""` passa un controllo sul
#    valore grezzo e `parse_iso_date` lo rende None. Fino al 2026-10-09 il
#    controllo era sul grezzo, e una data vuota arrivava al resolver (trovato
#    da mypy). Il campo si nomina in entrambi i percorsi.
def _data_riferimento_obbligatoria(payload: dict[str, Any]) -> date:
    data_riferimento_raw = payload.get("data_riferimento")
    data_riferimento = (
        parse_iso_date(str(data_riferimento_raw))
        if data_riferimento_raw is not None else None
    )
    ErrorManager.require(
        data_riferimento is not None,
        code="E_VENDITE_VALIDATION",
        message="data_riferimento obbligatoria.",
        context={"field": "data_riferimento"},
    )
    assert data_riferimento is not None
    return data_riferimento


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
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

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
            data_riferimento = _data_riferimento_obbligatoria(payload)

            emittente_sr = _resolve_emittente_sr(
                request, payload.get("emittente_soggetto_ruolo_id"),
            )

            padre_raw = payload.get("articolo_padre_contesto")
            result = PricingService().resolve_prezzo(
                articolo_id=str(articolo_id),
                uom_id=_V.require_positive_int(payload, "uom_id"),
                data_riferimento=data_riferimento,
                ba_id=_V.require_positive_int(payload, "ba_id"),
                utility_id=_V.require_positive_int(payload, "utility_id"),
                emittente_soggetto_ruolo_id=emittente_sr,
                classe_utenza_id=_V.optional_positive_int(payload, "classe_utenza_id"),
                articolo_padre_contesto=str(padre_raw) if padre_raw else None,
            )
            return {k: serialize_value(v) for k, v in result.items()}

        return handle_post_json(request, handler=_handler)


# ====================================================================
# Endpoint diagnostico pricing (POST /vendite/pricing/diagnose/)
# ====================================================================
#
# Scopo: diagnosticare la configurazione asset (BA, contratto, matrice
#        categoria→listino, promo) per la combinazione di parametri data,
#        spiegando perche' il resolver fallisce e cosa l'admin deve
#        configurare. Read-only, nessun side-effect, leggero (4 query
#        mirate, no chiamata al resolver vero).
#
# Pattern UX: il TestResolverDialog chiama questo endpoint dopo che il
#        resolver ha sollevato errore e mostra una checklist a stadi
#        con le azioni suggerite.

_DIAGNOSE_REQUEST = _RESOLVE_REQUEST  # stessi parametri del resolver

_DIAGNOSE_BA = inline_serializer(
    name="VenditePricingDiagnoseBA",
    fields={
        "trovato": serializers.BooleanField(),
        "categoria_id": serializers.IntegerField(allow_null=True),
        "categoria_codice": serializers.CharField(allow_null=True),
        "categoria_descrizione": serializers.CharField(allow_null=True),
        "categoria_partecipa_promo": serializers.BooleanField(),
    },
)

_DIAGNOSE_STADIO = inline_serializer(
    name="VenditePricingDiagnoseStadio",
    fields={
        "applicabile": serializers.BooleanField(),
        "motivo": serializers.CharField(allow_null=True),
    },
)

_DIAGNOSE_RESPONSE = inline_serializer(
    name="VenditePricingDiagnoseResp",
    fields={
        "ba": _DIAGNOSE_BA,
        "stadio_0_promo": serializers.DictField(),
        "stadio_1_contratto": serializers.DictField(),
        "stadio_2_categoria": serializers.DictField(),
        "esito_atteso": serializers.DictField(),
        "azioni_suggerite": serializers.ListField(child=serializers.CharField()),
    },
)


class PricingDiagnoseView(DomainAPIView):
    """POST /api/v1/vendite/pricing/diagnose/ — diagnostica asset pricing.

    Per la stessa combinazione di parametri del resolver, ritorna lo
    stato di configurazione dei 3 stadi (PROMO/CONTRATTO/CATEGORIA) +
    azioni operative suggerite per sbloccare l'eventuale errore.
    Non chiama il resolver vero: ispeziona la configurazione.

    Area funzionale: `vendite` (livello LETTURA sufficiente).
    """

    area_funzionale = "vendite"
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=_DIAGNOSE_REQUEST,
        responses={200: _DIAGNOSE_RESPONSE},
        tags=["vendite"],
        summary="Diagnostica configurazione asset pricing",
    )
    def post(self, request: Request):
        # Scopo: handler simmetrico a PricingResolveView. Riusa
        #        `_resolve_emittente_sr` per la derivazione dal JWT (fallback
        #        a override esplicito) e `parse_iso_date` per la data.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            articolo_id = payload.get("articolo_id")
            ErrorManager.require(
                articolo_id is not None,
                code="E_VENDITE_VALIDATION",
                message="articolo_id obbligatorio.",
            )
            data_riferimento = _data_riferimento_obbligatoria(payload)

            emittente_sr = _resolve_emittente_sr(
                request, payload.get("emittente_soggetto_ruolo_id"),
            )

            result = PricingDiagnoseService().diagnose(
                articolo_id=str(articolo_id),
                uom_id=_V.require_positive_int(payload, "uom_id"),
                data_riferimento=data_riferimento,
                ba_id=_V.require_positive_int(payload, "ba_id"),
                utility_id=_V.require_positive_int(payload, "utility_id"),
                emittente_soggetto_ruolo_id=emittente_sr,
                classe_utenza_id=_V.optional_positive_int(payload, "classe_utenza_id"),
            )
            return result

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
    user -> categoria_cliente -> group -> emittente -> default via
    `ParameterService.get_parameter` (cascata estesa 2026-05-15).

    Query param opzionale `billing_account_id`: se fornito, il livello
    `categoria_cliente` della cascata viene alimentato con la categoria
    del BA destinatario. Senza, il livello viene saltato e si applica
    la soglia "generica" per l'utente. Il FE deve passarlo nel drawer
    riga preventivo per mostrare la soglia coerente con il cliente target.

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
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Opzionale. ID del billing account destinatario: se "
                    "presente, la cascata include il livello categoria_cliente "
                    "del BA. Senza, il livello categoria viene saltato. "
                    "Non numerico o <= 0 → 400 E_VALIDATION_INPUT; BA inesistente "
                    "o fuori scope → 404 E_ANAG_NOT_FOUND."
                ),
            ),
        ],
    )
    def get(self, request: Request):
        auth_user_id = get_actor_user_id(request)
        # Single round-trip: risolve entrambe le chiavi in una query DB.
        # Valori ritornati come stringa (envelope stabile); il FE le converte
        # in Number (zero-safe) per l'interpolazione dell'hint.
        # Derivazione emittente dell'operatore: senza questo passaggio la
        # cascata user → categoria_cliente → group → emittente → default
        # salterebbe lo step "emittente" e gli override impostati per EF non
        # sarebbero mai applicati (sintomo: admin imposta MAX_SCONTO_PCT=10
        # per emittente X, l'operatore vede sempre 0 nel drawer).
        # Derivazione categoria: solo se il FE passa billing_account_id come
        # query param. Senza BA il livello categoria_cliente viene saltato.
        param_service = ParameterService()
        emittente_fiscale_id = (
            param_service.get_emittente_fiscale_id_for_user(auth_user_id)
            if auth_user_id is not None else None
        )
        # BA malformato → 400, BA che non risulta (inesistente o fuori scope
        # RLS) → 404 (F-6): prima saltavano il livello categoria in silenzio, e
        # il drawer mostrava la soglia generica come se fosse quella del cliente.
        categoria_cliente_id = categoria_cliente_da_query(
            request.query_params.get("billing_account_id"),
        )
        values = param_service.get_defaults(
            [PARAM_MAX_SCONTO_PCT, PARAM_MAX_MAGGIORAZIONE_PCT],
            django_user_id=auth_user_id,
            emittente_fiscale_id=emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
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
