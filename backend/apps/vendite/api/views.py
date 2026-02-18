from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date, optional_uuid
from apps.core.api.success_responses import success_response
from apps.vendite.services.pipeline_service import (
    fn_get_lotto_segnalazioni_summary,
    fn_reset_lotto_draft,
    fn_reset_lotto_fattura_draft,
    pr_run_lotto_pipeline,
)

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.


class ApiRunLottoPipeline(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeRunLottoPipelineRequest",
            fields={
                "lotto_id": serializers.IntegerField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "tipo_doc_fiscale_id": serializers.IntegerField(required=False, allow_null=True),
                "utility_id": serializers.IntegerField(required=False, allow_null=True),
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "lock_batch_id": serializers.UUIDField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False),
                "dry_run": serializers.BooleanField(required=False),
                "tipo_lotto": serializers.CharField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeRunLottoPipelineResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRunLottoPipelineData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "status": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            lotto_id = pr_run_lotto_pipeline(
                lotto_id=optional_int(payload, "lotto_id", zero_as_none=True),
                competenza_mese=optional_iso_date(payload, "competenza_mese"),
                tipo_doc_fiscale_id=optional_int(payload, "tipo_doc_fiscale_id", zero_as_none=True),
                utility_id=optional_int(payload, "utility_id", zero_as_none=True),
                billing_account_id=optional_int(payload, "billing_account_id", zero_as_none=True),
                lock_batch_id=optional_uuid(payload, "lock_batch_id"),
                meta=payload.get("meta"),
                dry_run=optional_bool(payload, "dry_run", default=False),
                tipo_lotto=payload.get("tipo_lotto", "MASSIVO"),
            )
            return {"lotto_id": lotto_id, "status": "ok"}

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRunLottoPipelineV1(ApiRunLottoPipeline):
    # Versione canonica protetta: richiede JWT su /api/v1/*
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiLottoSegnalazioniSummary(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeLottoSegnalazioniSummaryResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoSegnalazioniSummaryData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "critical_count": serializers.IntegerField(),
                            "warning_count": serializers.IntegerField(),
                            "attention_count": serializers.IntegerField(),
                            "is_error": serializers.BooleanField(),
                            "blocks_next_step": serializers.BooleanField(),
                            "summary": serializers.DictField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il riepilogo segnalazioni del lotto per uso operativo/UI.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        try:
            data = fn_get_lotto_segnalazioni_summary(lotto_id=lotto_id)
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLottoSegnalazioniSummaryV1(ApiLottoSegnalazioniSummary):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiResetLottoDraft(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeResetLottoDraftRequest",
            fields={},
        ),
        responses={
            200: inline_serializer(
                name="VenditeResetLottoDraftResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeResetLottoDraftData",
                        fields={
                            "updated_lotti": serializers.IntegerField(),
                            "updated_attivita": serializers.IntegerField(),
                            "deleted_fatture": serializers.IntegerField(),
                            "deleted_righe": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request, lotto_id: int) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            result = fn_reset_lotto_draft(lotto_id=lotto_id)
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiResetLottoDraftV1(ApiResetLottoDraft):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiResetLottoFatturaDraft(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeResetLottoFatturaDraftRequest",
            fields={},
        ),
        responses={
            200: inline_serializer(
                name="VenditeResetLottoFatturaDraftResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeResetLottoFatturaDraftData",
                        fields={
                            "updated_attivita": serializers.IntegerField(),
                            "deleted_fatture": serializers.IntegerField(),
                            "deleted_righe": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request, lotto_id: int, fattura_id: int) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            result = fn_reset_lotto_fattura_draft(lotto_id=lotto_id, fattura_id=fattura_id)
            return {"data": result}

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiResetLottoFatturaDraftV1(ApiResetLottoFatturaDraft):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
