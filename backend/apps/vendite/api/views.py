from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date
from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

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
                "lock_batch_id": serializers.IntegerField(required=False, allow_null=True),
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
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            lotto_id = pr_run_lotto_pipeline(
                lotto_id=optional_int(payload, "lotto_id"),
                competenza_mese=optional_iso_date(payload, "competenza_mese"),
                tipo_doc_fiscale_id=optional_int(payload, "tipo_doc_fiscale_id"),
                utility_id=optional_int(payload, "utility_id"),
                billing_account_id=optional_int(payload, "billing_account_id"),
                lock_batch_id=optional_int(payload, "lock_batch_id"),
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
