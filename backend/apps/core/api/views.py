from django.contrib.auth import get_user_model
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from apps.core.api.permissions import ZeroERPPermission
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.services.lookup_service import fn_list_lookup_codici
from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver
from apps.core.services.service_errors import ServiceError

# Endpoint diagnostici core: utili per verificare contratto error envelope API.


class ApiDiagnosticsErrorEnvelope(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="kind",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=["generic", "retryable", "not_found"],
                description="Tipo errore diagnostico da simulare.",
                required=False,
            )
        ],
        responses={
            500: inline_serializer(
                name="CoreDiagnosticsErrorEnvelopeResponse",
                fields={
                    "error": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP GET del relativo endpoint API.
    def get(self, request: Request) -> JsonResponse:
        kind = request.query_params.get("kind", "generic")

        if kind == "retryable":
            exc = ServiceError(
                code="E_DATABASE_RETRYABLE",
                message="Conflitto transazionale, riprovare.",
                retryable=True,
            )
        elif kind == "not_found":
            exc = ServiceError(
                code="E_PIPELINE_LOTTO_NOT_FOUND",
                message="Lotto pipeline non trovato.",
                detail="Lotto non trovato (diagnostica core).",
            )
        else:
            exc = ServiceError(
                code="E_GENERICO",
                message="Errore diagnostico core.",
                detail="Endpoint diagnostico error-envelope.",
            )

        return exception_to_error_response(exc)


class ApiDiagnosticsErrorEnvelopeV1(ApiDiagnosticsErrorEnvelope):
    # Versione canonica protetta: richiede JWT su /api/v1/*
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]


class ApiLookupCodici(APIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="rel", type=str, location=OpenApiParameter.QUERY, required=True, description="Relazione config da interrogare (es. config.stati_sdi)."),
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False, description="Ricerca libera su codice o descrizione (ILIKE, OR). Es. 'fat' restituisce tutti i record il cui codice o descrizione contiene 'fat'."),
            OpenApiParameter(name="order_col", type=str, location=OpenApiParameter.QUERY, required=False, enum=["codice", "descrizione"], description="Colonna di ordinamento (default: descrizione)."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, enum=["asc", "desc"], description="Direzione ordinamento (default: asc)."),
            OpenApiParameter(name="attivo_only", type=bool, location=OpenApiParameter.QUERY, required=False, description="Filtra solo record attivi (default: true)."),
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, required=False, description="Numero pagina (default 1)."),
            OpenApiParameter(name="page_size", type=int, location=OpenApiParameter.QUERY, required=False, description="Dimensione pagina (default 50, max 200)."),
        ],
        responses={
            200: inline_serializer(
                name="CoreLookupCodiciResponse",
                fields={
                    "data": inline_serializer(
                        name="CoreLookupCodiciData",
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
    # Scopo: Restituisce via GET l'elenco paginato dei codici/descrizioni di una tabella config
    # con ricerca ILIKE opzionale su codice e descrizione.
    def get(self, request: Request) -> JsonResponse:
        try:
            rel = (request.query_params.get("rel") or "").strip()

            raw_search = request.query_params.get("search")
            search = raw_search.strip() or None if raw_search is not None else None

            order_col = request.query_params.get("order_col", "descrizione").strip() or "descrizione"
            order_dir = request.query_params.get("order_dir", "asc").strip() or "asc"

            raw_attivo = request.query_params.get("attivo_only", "true").strip().lower()
            attivo_only = raw_attivo not in {"0", "false", "no", "n", "off"}

            page = int(request.query_params.get("page", "1"))
            page_size = int(request.query_params.get("page_size", "50"))

            data = fn_list_lookup_codici(
                rel=rel,
                search=search,
                order_col=order_col,
                order_dir=order_dir,
                attivo_only=attivo_only,
                page=page,
                page_size=page_size,
            )
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLookupCodiciV1(ApiLookupCodici):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]


class ApiPermessiEffettivi(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="CorePermessiEffettiviResponse",
                fields={
                    "data": inline_serializer(
                        name="CorePermessiEffettiviData",
                        fields={
                            "user_id": serializers.IntegerField(),
                            "username": serializers.CharField(),
                            "ruolo_sistema": serializers.CharField(allow_null=True),
                            "unita_organizzativa_id": serializers.IntegerField(allow_null=True),
                            "aree": serializers.ListField(child=serializers.DictField()),
                            "emittenti_ids": serializers.ListField(
                                child=serializers.IntegerField(), allow_null=True
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET i permessi effettivi risolti per un utente.
    # Solo ADMIN e superuser possono consultare altri utenti.
    def get(self, request: Request, user_id: int) -> JsonResponse:
        try:
            user = request.user
            cache: dict = {}

            # Solo ADMIN/superuser possono vedere permessi di altri utenti
            ruolo_richiedente = PermissionResolver.get_ruolo_sistema(user, cache=cache)
            if user_id != user.id:
                if not user.is_superuser and ruolo_richiedente != "ADMIN":
                    raise ServiceError(
                        code="E_PERMESSO_NEGATO",
                        message="Non hai i permessi per questa operazione.",
                        detail="Solo ADMIN possono consultare permessi di altri utenti.",
                    )

            # Carica l'utente target
            User = get_user_model()
            try:
                target_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise ServiceError(
                    code="E_CORE_VALIDATION",
                    message="Utente non trovato.",
                    detail=f"Nessun utente con id={user_id}.",
                )

            # Risolvi permessi per target
            target_cache: dict = {}
            ruolo = PermissionResolver.get_ruolo_sistema(target_user, cache=target_cache)
            uo_id = PermissionResolver.get_unita_organizzativa_id(
                target_user, cache=target_cache
            )
            emittenti_ids = PermissionResolver.get_emittenti_ids(
                target_user, cache=target_cache
            )

            # Itera tutte le aree funzionali attive
            from apps.config.models import AreaFunzionale

            aree_result = []
            for area in AreaFunzionale.objects.filter(attivo=True):
                livello = PermissionResolver.get_livello_area(
                    target_user, area.schema_db, cache=target_cache
                )
                has_profilo = PermissionResolver.has_profilo_reparto_area(
                    target_user, area.schema_db, cache=target_cache
                )
                aree_result.append({
                    "codice": area.codice,
                    "schema_db": area.schema_db,
                    "descrizione": area.descrizione,
                    "livello": livello,
                    "azioni_consentite": sorted(LIVELLO_MAP.get(livello, frozenset())),
                    "has_profilo_reparto": has_profilo,
                })

            data = {
                "user_id": target_user.id,
                "username": target_user.get_username(),
                "ruolo_sistema": ruolo,
                "unita_organizzativa_id": uo_id,
                "aree": aree_result,
                "emittenti_ids": emittenti_ids,
            }
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiPermessiEffettiviV1(ApiPermessiEffettivi):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
