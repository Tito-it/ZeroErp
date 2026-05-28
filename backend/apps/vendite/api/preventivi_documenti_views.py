# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da PREVENTIVO (Tranche K
#        motore documentale + emissione 2026-05-28). Endpoint sotto
#        `/api/v1/vendite/preventivi/<id>/`:
#         - `POST emetti/`:                  multipart: BOZZA->EMESSO + genera
#           documento + allegati in transazione atomica (mirror del flusso
#           offerta `ApiOffertaEmetti`);
#         - `POST documenti/genera/`:        persiste un documento generato
#           (PDF + record DB + evento `GENERATO`) per preventivi gia' EMESSI;
#         - `POST documenti/anteprima/`:     streaming PDF temporaneo, no
#           persist (Decisione 30);
#         - `GET  documenti/` (lista):       documenti generati per il
#           preventivo (paginata, scope emittente);
#         - `GET  documenti/<doc_id>/file/`: download PDF principale + emit
#           evento `SCARICATO` (Decisione 31).
#
#        Permessi del dominio sorgente (Decisione 75): `area_funzionale =
#        "vendite"` -> permission default lettura preventivi. Per
#        endpoint che modificano stato (genera = INSERT) lasciamo
#        comunque il permesso default lettura: la "generazione documento"
#        non e' modifica del preventivo, ma riproduzione in PDF di un
#        dato gia' visibile all'operatore. `emetti/` invece transita lo
#        stato -> si appoggia al service che applica i guard di dominio.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.documenti.api.contesto_helpers import resolve_contesto_documentale
from apps.documenti.api.multipart_helpers import extract_allegati
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services import preventivi_service

# Codice sorgente PREVENTIVO -> id risolto runtime via repo (memoria
# feedback_no_hardcoded_ids: lookup per codice, non ID numerici).
_CODICE_SORGENTE_PREVENTIVO = "PREVENTIVO"


# Scopo: Risolve il contesto comune per le view che operano "per preventivo".
#        Wrapper sottile su `resolve_contesto_documentale`.
def _resolve_contesto_preventivo(preventivo_id: int) -> tuple[dict[str, Any], int]:
    preventivo = PreventiviRepository().get_for_documento_generation(preventivo_id)
    return resolve_contesto_documentale(
        entity=preventivo,
        entity_id=preventivo_id,
        not_found_message="Preventivo non trovato.",
        emittente_message="Emittente fiscale non risolto per il preventivo.",
        sorgente_codice=_CODICE_SORGENTE_PREVENTIVO,
    )


class ApiPreventivoEmetti(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/emetti/` (multipart)."""

    area_funzionale = "vendite"
    # Cambia stato del preventivo: usa lo stesso permesso del cambio stato.
    post_permission = "cambia_stato_preventivi"
    # Override del default DRF (solo JSONParser) per consentire upload
    # multipart degli allegati assieme ai campi scalari template/tipo_output.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="VenditePreventivoEmettiReq",
                fields={
                    "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                    "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
                    "allegati": serializers.ListField(
                        child=serializers.FileField(), required=False,
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="VenditePreventivoEmettiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: BOZZA -> EMESSO con generazione+persistenza del documento e
    #        degli allegati in UNA transazione atomica. Ordine: prima
    #        `emetti` (cosi' lo snapshot del context riflette stato EMESSO),
    #        poi `genera_documento` (che apre il proprio savepoint annidato).
    #        Se la generazione fallisce, l'`emetti` viene annullato dal
    #        rollback dell'atomic esterno -> stato resta BOZZA, niente
    #        record documentale orfano. Mirror del flusso offerta.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")
        allegati = extract_allegati(request)

        with transaction.atomic():
            emit_result = preventivi_service.emetti(preventivo_id)
            preventivo, sorgente_tipo_id = _resolve_contesto_preventivo(preventivo_id)
            documento = DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(preventivo["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(preventivo["id"]),
                sorgente_uid=str(preventivo["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
                allegati=allegati,
            )

        return success_response({
            "preventivo": emit_result,
            "documento": documento,
        })


class ApiPreventivoDocumentoGenera(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/documenti/genera/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoDocumentoGeneraRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={201: inline_serializer(
            name="PreventivoDocumentoGeneraResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera e persiste un documento PDF dal preventivo. Il
    #        documento si registra in `documenti_generati` con evento
    #        `GENERATO` (Tranche I orchestrator). Il caller puo' specificare
    #        `template_documento_id` esplicito (override) o lasciare che
    #        il service usi il template `is_default=true` per la coppia
    #        (sorgente=PREVENTIVO, emittente).
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _execute(payload: dict[str, Any]) -> dict[str, Any]:
            preventivo, sorgente_tipo_id = _resolve_contesto_preventivo(preventivo_id)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")
            return DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(preventivo["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(preventivo["id"]),
                sorgente_uid=str(preventivo["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
            )

        return handle_post_json(request, handler=_execute)


class ApiPreventivoDocumentoAnteprima(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/documenti/anteprima/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoDocumentoAnteprimaRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: bytes},
    )
    # Scopo: Anteprima PDF temporanea (Decisione 30): nessun record DB,
    #        nessun file persistito, nessun evento timeline. Risposta
    #        come stream binario `application/pdf` inline (browser
    #        decide se aprire o scaricare).
    def post(self, request: Request, preventivo_id: int) -> HttpResponse:
        # Manuale (no `handle_post_json`): la risposta e' binaria, non JSON.
        payload = request.data if isinstance(request.data, dict) else {}
        preventivo, sorgente_tipo_id = _resolve_contesto_preventivo(preventivo_id)
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")

        result = DocumentGenerationService().anteprima_documento(
            request.user,
            emittente_fiscale_id=int(preventivo["emittente_fiscale_id"]),
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_id=int(preventivo["id"]),
            template_documento_id=template_id,
            tipo_documento_output_id=tipo_output_id,
        )
        response = HttpResponse(
            result["pdf_bytes"], content_type=result["mime_type"],
        )
        # `inline`: browser apre direttamente. Non offriamo download
        # forzato per l'anteprima (e' temporanea per design).
        response["Content-Disposition"] = (
            f'inline; filename="{result["nome_file"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response


class ApiPreventivoDocumentiList(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/<id>/documenti/`."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="PreventivoDocumentiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata documenti generati per il preventivo (timeline
    #        applicativa: render history). Ordinata per `generato_at DESC`.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        preventivo, sorgente_tipo_id = _resolve_contesto_preventivo(preventivo_id)
        qp = request.query_params
        page = max(1, qp_int(qp.get("page"), 1))
        page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
        offset = (page - 1) * page_size
        result = DocumentGenerationService().list_documenti_per_sorgente(
            request.user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=str(preventivo["uid"]),
            limit=page_size,
            offset=offset,
        )
        return success_response({
            **result,
            "page": page,
            "page_size": page_size,
        })


class ApiPreventivoDocumentoAllegati(DomainAPIView):
    """`/api/v1/vendite/preventivi/<preventivo_id>/documenti/<documento_id>/allegati/`."""

    area_funzionale = "vendite"
    # POST = upload multipart degli allegati su documento esistente.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDocumentoAllegatiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di tutti i file del documento (principale + allegati),
    #        per elenco/scarico nella UI (row-expand su DocumentiGeneratiSorgenteList).
    def get(
        self, request: Request, preventivo_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_preventivo(preventivo_id)
        result = DocumentGenerationService().list_documento_files(
            request.user, int(documento_id),
        )
        return success_response(result)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="PreventivoDocumentoAllegatiUploadReq",
                fields={
                    "allegati": serializers.ListField(
                        child=serializers.FileField(),
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="PreventivoDocumentoAllegatiUploadResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    #        (modalita' append post-emissione). MIME/size validati dal service.
    def post(
        self, request: Request, preventivo_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_preventivo(preventivo_id)
        allegati = extract_allegati(request)
        result = DocumentGenerationService().aggiungi_allegati(
            request.user, int(documento_id), allegati,
        )
        return success_response(result)


class ApiPreventivoDocumentoFile(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/<preventivo_id>/documenti/<documento_id>/file/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download PDF persistito + emit evento `SCARICATO` (Decisione 31:
    #        log ad ogni download). La path nidifica `preventivo_id` per
    #        coerenza URL ma il service applica scope sull'`documento_id`:
    #        defense-in-depth contro tampering URL (documento di altro
    #        preventivo via path errato -> 404 unificato no leak).
    def get(
        self, request: Request, preventivo_id: int, documento_id: int,
    ) -> HttpResponse:
        # Defense-in-depth: verifica che il preventivo esista e sia
        # visibile (la list/detail di documento usa lo stesso scope EF,
        # ma chiamando questa URL da fuori contesto previene 200 spuri).
        _resolve_contesto_preventivo(preventivo_id)

        result = DocumentGenerationService().download_documento(
            request.user, int(documento_id),
        )
        response = HttpResponse(
            result["pdf_bytes"], content_type=result["mime_type"],
        )
        # `attachment`: il browser propone "Salva con nome".
        response["Content-Disposition"] = (
            f'attachment; filename="{result["nome_file"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response
