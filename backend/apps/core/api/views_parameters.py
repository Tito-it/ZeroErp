# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per parametri di sistema con risoluzione override.
#        Endpoint:
#        - GET    /api/v1/core/parameters/defaults/                — risoluzione N parametri
#        - GET    /api/v1/core/parameters/settings/                — lista parametri per utente con livelli
#        - POST   /api/v1/core/parameters/settings/override/       — upsert override personale o emittente
#        - DELETE /api/v1/core/parameters/settings/override/<id>/  — rimuovi override personale o emittente
#        Lo scope ('user'|'emittente') determina la fascia di applicazione.
#        Lo scope 'emittente' e' riservato agli amministratori.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

import re

from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json, utente_autenticato, utente_autenticato_id
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import paginated_envelope, parse_list_params, qp_int_optional
from apps.core.api.permissions import IsAdminZeroERP
from apps.core.api.success_responses import success_response
from apps.core.db.parameter_repository import MAX_CODES
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import SMALLINT_MAX, SMALLINT_MIN

# Regex per int firmato stretto: rifiuta degenerazioni come "--5", "++1", "1.0".
# Coerente con _SIGNED_INT_RE di payload_helpers.py.
_INT_RE = re.compile(r"^-?\d+$")

# Scope override consentiti dal payload del POST.
# - user:               override personale (qualunque utente, default)
# - emittente:          override per emittente (admin-only, EF derivato dal profilo)
# - categoria_cliente:  override per categoria cliente (admin-only, id esplicito
#                       nel payload/query param). Phase B 2026-05-19 cascata
#                       parametri (cf. migration 20260519-01).
SCOPE_USER = "user"
SCOPE_EMITTENTE = "emittente"
SCOPE_CATEGORIA_CLIENTE = "categoria_cliente"
ALLOWED_SCOPES = (SCOPE_USER, SCOPE_EMITTENTE, SCOPE_CATEGORIA_CLIENTE)


# Scopo: Verifica che l'utente corrente sia ADMIN o superuser.
#        Riusa la logica di IsAdminZeroERP (l'argomento `view` non e' usato
#        dall'implementazione, quindi passare None e' sicuro per questo check).
def _is_admin(request: Request) -> bool:
    return IsAdminZeroERP().has_permission(request, view=None)


# Scopo: Verifica che l'operazione su scope='emittente' sia consentita e
#        restituisce l'emittente_fiscale_id da usare per l'override.
#        Solleva E_PERMISSION_DENIED se non admin, E_PARAMETER_VALIDATION
#        se l'utente non e' associato ad alcun emittente.
#        Centralizza il controllo riusato da POST e DELETE.
def _require_admin_emittente_id(request: Request, svc: ParameterService) -> int:
    ErrorManager.require(
        _is_admin(request),
        code="E_PERMISSION_DENIED",
        message="Solo gli amministratori possono operare sugli override a livello emittente.",
    )
    emittente_fiscale_id = svc.get_emittente_fiscale_id_for_user(utente_autenticato_id(request))
    ErrorManager.require(
        emittente_fiscale_id is not None,
        code="E_PARAMETER_VALIDATION",
        message="Emittente fiscale non risolvibile per l'utente corrente.",
    )
    return emittente_fiscale_id  # type: ignore[return-value]


# Scopo: Verifica che l'operazione su scope='categoria_cliente' sia consentita
#        e ritorna l'id categoria estratto dal payload (POST) o dal query
#        param (DELETE). Solleva E_PERMISSION_DENIED se non admin,
#        E_PARAMETER_VALIDATION se id assente o non positivo.
def _require_admin_categoria_cliente_id(
    request: Request, *, raw_id: int | str | None,
) -> int:
    ErrorManager.require(
        _is_admin(request),
        code="E_PERMISSION_DENIED",
        message=(
            "Solo gli amministratori possono operare sugli override "
            "a livello categoria cliente."
        ),
    )
    cat_id: int | None = None
    if isinstance(raw_id, int) and not isinstance(raw_id, bool):
        cat_id = raw_id
    elif isinstance(raw_id, str) and _INT_RE.match(raw_id.strip()):
        # Regex stretto: rifiuta "--5", "++1", "1.0". Solo int firmato valido.
        cat_id = int(raw_id.strip())
    ErrorManager.require(
        cat_id is not None and cat_id > 0,
        code="E_PARAMETER_VALIDATION",
        message="categoria_cliente_id deve essere un intero positivo.",
        context={"categoria_cliente_id": raw_id},
    )
    assert cat_id is not None
    return cat_id


# Scopo: Normalizza e valida lo scope ricevuto da payload o query string.
#        Default 'user' se assente. Solleva E_PARAMETER_VALIDATION se non valido.
def _parse_scope(raw: str | None) -> str:
    scope = (raw or SCOPE_USER).strip().lower()
    ErrorManager.require(
        scope in ALLOWED_SCOPES,
        code="E_PARAMETER_VALIDATION",
        message=f"Scope override non valido: '{scope}'.",
    )
    return scope


# Scopo: Helper per estrarre contesto utente per la risoluzione parametri.
#        Ritorna sempre i valori reali (anche per superuser): la cascade
#        override (user → group → emittente → default) e' identity-based,
#        non un filtro di scope. Un superuser che setta un override
#        personale via UI deve vederlo applicato come qualsiasi altro
#        utente — il bypass precedente forzava il fallback al solo default
#        globale e mascherava gli override gia' persistiti.
#        Per filtri di scope dati (es. emittenti_scope) usare invece
#        `get_scope_user_id` (apps/core/api/endpoint_helpers.py) che
#        applica il bypass superuser.
def get_user_context(request: Request, svc: ParameterService) -> dict:
    user = utente_autenticato(request)
    return {
        "django_user_id": user.id,
        "group_ids": list(user.groups.values_list("id", flat=True)),
        "emittente_fiscale_id": svc.get_emittente_fiscale_id_for_user(user.id),
    }


class ParameterDefaultsView(DomainAPIView):
    """Risolve N parametri di sistema con override per l'utente loggato."""

    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="codes",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Codici parametro separati da virgola (es. DEFAULT_IVA_ID,DEFAULT_CURRENCY).",
                required=True,
            ),
        ],
        responses={
            200: inline_serializer(
                name="ParameterDefaultsResponse",
                fields={
                    "data": serializers.DictField(
                        child=serializers.CharField(),
                        help_text="Mappa {code: valore_risolto}",
                    ),
                },
            )
        },
    )
    # Scopo: Restituisce i valori risolti (con override utente) per i codici richiesti.
    #        I codici non trovati vengono esclusi dal risultato.
    def get(self, request: Request) -> JsonResponse:
        raw_codes = request.query_params.get("codes", "")
        codes = [c.strip() for c in raw_codes.split(",") if c.strip()]
        if not codes:
            return success_response({})
        codes = codes[:MAX_CODES]

        svc = ParameterService()
        ctx = get_user_context(request, svc)
        defaults = svc.get_defaults(codes, **ctx)
        return success_response(defaults)


class ParameterSettingsView(DomainAPIView):
    """La pagina della lista `config.parametri_impostazioni`: i parametri con i
    valori a ogni livello di scope per l'utente loggato (dal 2026-10-31 a
    catalogo: pagina, ricerca, ordinamento; prima la lista intera)."""

    skip_area_check = True
    is_search_endpoint = True
    lista_codice = "config.parametri_impostazioni"

    @extend_schema(
        summary="Lista parametri con livelli override",
        description=(
            "Restituisce tutti i parametri di sistema con i valori a ogni livello "
            "(default, emittente, gruppo, categoria_cliente, utente) e il valore "
            "risolto finale. Cascata: user > categoria_cliente > group > emittente > default. "
            "`ammette_override` dice la famiglia: a false il parametro vale per tutti, i "
            "livelli sono null, il valore risolto e' il default e l'override e' rifiutato "
            "(400 E_PARAMETER_OVERRIDE_NON_AMMESSO)."
        ),
        parameters=[
            OpenApiParameter(
                name="categoria_cliente_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Smallint opzionale: se valorizzato attiva il livello "
                    "categoria_cliente fra user e group, valorizzando "
                    "`categoria_cliente_value` e `categoria_cliente_override_id` "
                    "nelle righe risultato. Non numerico o <= 0 → 400 "
                    "E_VALIDATION_INPUT."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Alternativa a categoria_cliente_id: deriva la categoria dal "
                    "BA indicato via anagrafiche.billing_account.categoria_cliente_id. "
                    "Ignorato se categoria_cliente_id e' valorizzato (priorita' al "
                    "valore esplicito). Non numerico o <= 0 → 400 "
                    "E_VALIDATION_INPUT; BA inesistente o fuori scope → 404 "
                    "E_ANAG_NOT_FOUND."
                ),
            ),
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False,
                             description="`code` (default) o `description`."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="ParameterSettingsResponse",
                fields={"data": serializers.DictField(help_text="Pagina della lista parametri con livelli override")},
            )
        },
    )
    # Scopo: Restituisce una pagina della lista parametri con i valori a ogni
    #        livello di scope e il valore risolto finale per l'utente corrente.
    #        Per la lista settings, risolve sempre django_user_id e
    #        emittente_fiscale_id anche per superuser, altrimenti il LEFT JOIN
    #        su emittente_fiscale_id = NULL non matcha mai (NULL = NULL e' false
    #        in SQL) e gli override emittente non vengono mostrati.
    #        Post brief DB 2026-05-19 (migration 20260519-01): accetta
    #        `categoria_cliente_id` come query param (esplicito) oppure
    #        `billing_account_id` (deriva la categoria dal BA col BB
    #        `categoria_cliente_da_query`: BA che non risulta → 404).
    #        Priorita': esplicito > derivato. Se nessuno dei due, il livello
    #        categoria resta NULL nelle righe (`categoria_cliente_value` NULL).
    def get(self, request: Request) -> JsonResponse:
        svc = ParameterService()
        ctx = get_user_context(request, svc)
        qp = request.query_params

        # Fallback per superuser: risolve sempre user e emittente reali.
        django_user_id = ctx["django_user_id"] or utente_autenticato_id(request)
        emittente_fiscale_id = ctx["emittente_fiscale_id"] or svc.get_emittente_fiscale_id_for_user(utente_autenticato_id(request))

        # Risoluzione categoria_cliente_id: esplicito > derivato da BA.
        # Guard `> 0`: rifiuta 0/negativi invece di passarli in silenzio al DB
        # (LEFT JOIN no-match, l'utente non capirebbe perche'
        # categoria_cliente_value resta null). Non numerico o <= 0 →
        # ValueError → 400 E_VALIDATION_INPUT, come `billing_account_id` qui
        # sotto: un query string malformato e' un dato di input (api.md
        # §Query params), non un valore di parametro di configurazione
        # (`E_PARAMETER_VALIDATION`, che restava qui fino al 2026-10-08).
        # ⚠️ Tetto smallint: il valore arriva al `%s::smallint` di
        # `script.fn_list_parameters_for_user` (oltre, un 500).
        categoria_cliente_id = qp_int_optional(
            qp.get("categoria_cliente_id"), "categoria_cliente_id",
            min_val=SMALLINT_MIN, max_val=SMALLINT_MAX,
        )
        if categoria_cliente_id is not None:
            if categoria_cliente_id <= 0:
                raise ValueError("categoria_cliente_id_invalid")
        else:
            # BA che non risulta (inesistente o fuori scope RLS) → 404, F-6.
            categoria_cliente_id = categoria_cliente_da_query(qp.get("billing_account_id"))

        p = parse_list_params(qp, default_order="code")
        results, total = svc.list_parameters_for_user(
            django_user_id=django_user_id,
            group_ids=ctx["group_ids"],
            emittente_fiscale_id=emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class ParameterOverrideView(DomainAPIView):
    """Crea/aggiorna un override per un parametro a scope personale, emittente
    o categoria_cliente.

    Scope ammessi:
    - "user"               → override personale (default per qualunque utente)
    - "emittente"          → override valido per tutti gli utenti dell'emittente
                             corrente (riservato agli admin)
    - "categoria_cliente"  → override valido per tutti gli utenti che operano
                             su BA della categoria indicata (riservato agli admin,
                             id passato nel payload). Phase B 2026-05-19.
    """

    skip_area_check = True

    @extend_schema(
        summary="Crea o aggiorna override parametro",
        request=inline_serializer(
            name="ParameterOverrideRequest",
            fields={
                "parameter_code": serializers.CharField(
                    help_text=(
                        "Codice del parametro da sovrascrivere. Un parametro che "
                        "vale per tutti (ammette_override false nella lista) e' "
                        "rifiutato dal DB: 400 E_PARAMETER_OVERRIDE_NON_AMMESSO."
                    ),
                ),
                "value": serializers.CharField(
                    help_text="Nuovo valore dell'override",
                ),
                "scope": serializers.ChoiceField(
                    choices=list(ALLOWED_SCOPES),
                    required=False,
                    help_text=(
                        "Scope: 'user' (default), 'emittente' (admin), "
                        "'categoria_cliente' (admin, richiede categoria_cliente_id)."
                    ),
                ),
                "categoria_cliente_id": serializers.IntegerField(
                    required=False,
                    help_text="Obbligatorio se scope='categoria_cliente'",
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="ParameterOverrideResponse",
                fields={
                    "data": serializers.DictField(
                        help_text="ID dell'override creato/aggiornato + scope",
                    ),
                },
            )
        },
    )
    # Scopo: Crea o aggiorna un override per il parametro indicato.
    #        Lo scope determina la fascia di applicazione.
    def post(self, request: Request) -> JsonResponse:
        svc = ParameterService()

        def handler(payload: dict) -> dict:
            scope = _parse_scope(payload.get("scope"))
            raw_value = payload.get("value")
            # ⛔ Un override senza valore e' un 400 sul campo, non un override
            #    vuoto: fino al 2026-10-21 `value` assente o `null` diventava `""`
            #    e si scriveva, con un 200 (brief-be-verifica-documentazione-api
            #    §B6). La stringa vuota ESPLICITA resta un valore.
            ErrorManager.require(
                raw_value is not None,
                code="E_PARAMETER_VALIDATION",
                message="Valore dell'override obbligatorio.",
                context={"field": "value"},
            )
            # ⛔ Il valore di un parametro e' TESTO (la colonna e il drawer):
            #    `str()` su un JSON qualunque scriveva `true` come "True" e un
            #    oggetto come "{'a': 1}", con un 200.
            ErrorManager.require(
                isinstance(raw_value, str),
                code="E_PARAMETER_VALIDATION",
                message="Il valore dell'override dev'essere una stringa.",
                detail=f"value={type(raw_value).__name__}",
                context={"field": "value"},
            )
            assert isinstance(raw_value, str)
            value = raw_value
            parameter_code = payload.get("parameter_code", "")
            # Un codice non stringa arrivava a `.strip()` nel service: un 500.
            ErrorManager.require(
                isinstance(parameter_code, str),
                code="E_PARAMETER_VALIDATION",
                message="Codice parametro non valido.",
                context={"field": "parameter_code"},
            )

            if scope == SCOPE_EMITTENTE:
                emittente_fiscale_id = _require_admin_emittente_id(request, svc)
                override_id = svc.upsert_emittente_override(
                    parameter_code=parameter_code,
                    emittente_fiscale_id=emittente_fiscale_id,
                    value=value,
                )
            elif scope == SCOPE_CATEGORIA_CLIENTE:
                categoria_cliente_id = _require_admin_categoria_cliente_id(
                    request, raw_id=payload.get("categoria_cliente_id"),
                )
                override_id = svc.upsert_categoria_cliente_override(
                    parameter_code=parameter_code,
                    categoria_cliente_id=categoria_cliente_id,
                    value=value,
                )
            else:
                override_id = svc.upsert_user_override(
                    parameter_code=parameter_code,
                    django_user_id=utente_autenticato_id(request),
                    value=value,
                )

            return {"override_id": override_id, "scope": scope}

        return handle_post_json(request, handler=handler)


class ParameterOverrideDeleteView(DomainAPIView):
    """Rimuove un override (personale, emittente o categoria_cliente).

    Lo scope viene passato come query string ?scope=user|emittente|categoria_cliente
    (default 'user'). Gli scope 'emittente' e 'categoria_cliente' richiedono ruolo admin.
    Per scope='categoria_cliente' serve anche `?categoria_cliente_id=<id>`.
    """

    skip_area_check = True

    @extend_schema(
        summary="Rimuovi override parametro",
        parameters=[
            OpenApiParameter(
                name="scope",
                type=str,
                location=OpenApiParameter.QUERY,
                description=(
                    "Scope dell'override: 'user' (default), 'emittente', "
                    "'categoria_cliente'."
                ),
                required=False,
            ),
            OpenApiParameter(
                name="categoria_cliente_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Obbligatorio se scope='categoria_cliente'.",
                required=False,
            ),
        ],
        responses={
            200: inline_serializer(
                name="ParameterOverrideDeleteResponse",
                fields={
                    "data": serializers.DictField(
                        help_text="Conferma eliminazione",
                    ),
                },
            )
        },
    )
    # Scopo: Rimuove un override per il parametro indicato.
    def delete(self, request: Request, override_id: int) -> JsonResponse:
        svc = ParameterService()
        scope = _parse_scope(request.query_params.get("scope"))

        if scope == SCOPE_EMITTENTE:
            emittente_fiscale_id = _require_admin_emittente_id(request, svc)
            svc.delete_emittente_override(
                override_id=override_id,
                emittente_fiscale_id=emittente_fiscale_id,
            )
        elif scope == SCOPE_CATEGORIA_CLIENTE:
            categoria_cliente_id = _require_admin_categoria_cliente_id(
                request, raw_id=request.query_params.get("categoria_cliente_id"),
            )
            svc.delete_categoria_cliente_override(
                override_id=override_id,
                categoria_cliente_id=categoria_cliente_id,
            )
        else:
            svc.delete_user_override(
                override_id=override_id,
                django_user_id=utente_autenticato_id(request),
            )

        return success_response({"deleted": True, "scope": scope})
