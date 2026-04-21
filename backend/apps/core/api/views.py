from django.contrib.auth import get_user_model
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.payload_validators import qp_int_strict
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.services.lookup_service import fn_list_lookup_codici
from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver
from apps.core.services.service_errors import ServiceError

# Endpoint diagnostici core: utili per verificare contratto error envelope API.


class ApiDiagnosticsErrorEnvelope(DomainAPIView):
    skip_area_check = True
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




class ApiLookupCodici(DomainAPIView):
    skip_area_check = True
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
        rel = (request.query_params.get("rel") or "").strip()

        raw_search = request.query_params.get("search")
        search = raw_search.strip() or None if raw_search is not None else None

        order_col = request.query_params.get("order_col", "descrizione").strip() or "descrizione"
        order_dir = request.query_params.get("order_dir", "asc").strip() or "asc"

        raw_attivo = request.query_params.get("attivo_only", "true").strip().lower()
        attivo_only = raw_attivo not in {"0", "false", "no", "n", "off"}

        page = qp_int_strict(request.query_params.get("page"), "page", 1)
        page_size = qp_int_strict(request.query_params.get("page_size"), "page_size", 50)

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




class ApiPermessiEffettivi(DomainAPIView):
    skip_area_check = True
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
        user = request.user
        cache: dict = {}

        # Solo SUPER_ADMIN/superuser possono vedere permessi di altri utenti
        if user_id != user.id:
            if not user.is_superuser and not PermissionResolver.is_super_admin(
                user, cache=cache
            ):
                raise ServiceError(
                    code="E_PERMESSO_NEGATO",
                    message="Non hai i permessi per questa operazione.",
                    detail="Solo SUPER_ADMIN possono consultare permessi di altri utenti.",
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

        # Risolvi permessi per target. Il campo di output `ruolo_sistema`
        # resta per retrocompat del frontend (Stage B cambiera' contract
        # a `ruolo_applicativo` + `is_super_admin`). Ricostruzione: se e'
        # SUPER_ADMIN -> "ADMIN"; se ruolo_applicativo=DISABILITATO ->
        # "DISABILITATO"; altrimenti -> "OPERATIVO".
        target_cache: dict = {}
        is_super = PermissionResolver.is_super_admin(target_user, cache=target_cache)
        ruolo_app = PermissionResolver.get_ruolo_applicativo(
            target_user, cache=target_cache
        )
        if is_super:
            ruolo = "ADMIN"
        elif ruolo_app == "DISABILITATO":
            ruolo = "DISABILITATO"
        elif ruolo_app is None:
            ruolo = None
        else:
            ruolo = "OPERATIVO"
        uo_id = PermissionResolver.get_unita_organizzativa_id(
            target_user, cache=target_cache
        )
        emittenti_ids = PermissionResolver.get_emittenti_ids(
            target_user, cache=target_cache
        )

        # Itera tutte le aree funzionali attive
        from apps.config.models import AreaFunzionale

        # Carica una volta sola il catalogo model configurabili, raggruppati per area.
        model_map = PermissionResolver.list_model_overrides_grouped()

        aree_result = []
        for area in AreaFunzionale.objects.filter(attivo=True):
            livello = PermissionResolver.get_livello_area(
                target_user, area.schema_db, cache=target_cache
            )
            # Field name output `has_profilo_reparto` mantenuto per
            # retrocompat frontend (Stage B lo rinominera' coerente).
            has_profilo = PermissionResolver.has_profilo_applicabile_per_area(
                target_user, area.schema_db, cache=target_cache
            )
            # Livello oggetto per ogni model registrato nell'area.
            modelli = []
            for m in model_map.get(area.schema_db, []):
                livello_obj = PermissionResolver.get_livello_oggetto(
                    target_user,
                    m["app_label"],
                    m["model_name"],
                    area.schema_db,
                    cache=target_cache,
                )
                modelli.append({
                    "app_label": m["app_label"],
                    "model_name": m["model_name"],
                    "livello": livello_obj,
                })
            aree_result.append({
                "codice": area.codice,
                "schema_db": area.schema_db,
                "descrizione": area.descrizione,
                "livello": livello,
                "azioni_consentite": sorted(LIVELLO_MAP.get(livello, frozenset())),
                "has_profilo_reparto": has_profilo,
                "modelli": modelli,
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




class ApiPermessiAudit(DomainAPIView):
    skip_area_check = True
    @extend_schema(
        parameters=[
            OpenApiParameter(name="data_da", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro data inizio (YYYY-MM-DD)."),
            OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro data fine (YYYY-MM-DD)."),
            OpenApiParameter(name="tabella", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro singola tabella sorgente (es. user_override_aree)."),
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, required=False, description="Numero pagina (default 1)."),
            OpenApiParameter(name="page_size", type=int, location=OpenApiParameter.QUERY, required=False, description="Dimensione pagina (default 50, max 200)."),
        ],
        responses={
            200: inline_serializer(
                name="CorePermessiAuditResponse",
                fields={
                    "data": inline_serializer(
                        name="CorePermessiAuditData",
                        fields={
                            "user_id": serializers.IntegerField(),
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "events": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la timeline audit delle modifiche ai permessi di un utente.
    # Interroga le 7 tabelle storico permessi con filtri opzionali e paginazione.
    # Solo ADMIN e superuser possono consultare altri utenti.
    def get(self, request: Request, user_id: int) -> JsonResponse:
        from apps.core.api.payload_validators import optional_int, optional_iso_date
        from apps.core.db.permissions_audit_repository import PermissionsAuditRepository

        user = request.user
        cache: dict = {}

        # Scopo: Verifica autorizzazione — stessa policy di permessi-effettivi.
        if user_id != user.id:
            if not user.is_superuser and not PermissionResolver.is_super_admin(
                user, cache=cache
            ):
                raise ServiceError(
                    code="E_PERMESSO_NEGATO",
                    message="Non hai i permessi per questa operazione.",
                    detail="Solo SUPER_ADMIN possono consultare audit permessi di altri utenti.",
                )

        # Scopo: Verifica che l'utente target esista.
        User = get_user_model()
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Utente non trovato.",
                detail=f"Nessun utente con id={user_id}.",
            )

        # Scopo: Parse query params.
        data_da = optional_iso_date(
            {"data_da": request.query_params.get("data_da")}, "data_da"
        )
        data_a = optional_iso_date(
            {"data_a": request.query_params.get("data_a")}, "data_a"
        )
        tabella = request.query_params.get("tabella")
        if tabella:
            tabella = tabella.strip() or None
        if tabella and tabella not in PermissionsAuditRepository._VALID_TABLE_NAMES:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Tabella non valida.",
                detail=f"Tabella '{tabella}' non riconosciuta. Valori ammessi: {sorted(PermissionsAuditRepository._VALID_TABLE_NAMES)}.",
            )
        page = optional_int(
            {"page": request.query_params.get("page", "1")}, "page"
        )
        page_size = optional_int(
            {"page_size": request.query_params.get("page_size", "50")}, "page_size"
        )
        page_size = min(page_size, 200)

        # Scopo: Risolve UO dell'utente target per includere tabelle reparto.
        target_cache: dict = {}
        uo_id = PermissionResolver.get_unita_organizzativa_id(
            target_user, cache=target_cache
        )

        repo = PermissionsAuditRepository()
        result = repo.list_audit_events(
            auth_user_id=user_id,
            uo_id=uo_id,
            data_da=data_da,
            data_a=data_a,
            tabella=tabella,
            page=page,
            page_size=page_size,
        )
        result["user_id"] = user_id
        return success_response(result)


