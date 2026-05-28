# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da CONTRATTO. Endpoint sotto
#        `/api/v1/vendite/contratti/<id>/`:
#         - `POST emetti/`:                  multipart: DRAFT->ATTIVO + genera
#           documento + allegati in transazione atomica (mirror del flusso
#           offerta/preventivo `ApiOffertaEmetti`/`ApiPreventivoEmetti`);
#         - `POST documenti/genera/`:        persiste PDF + record DB + evento
#           `GENERATO` per contratti gia' ATTIVI;
#         - `POST documenti/anteprima/`:     streaming PDF temporaneo, no persist;
#         - `GET  documenti/`:               lista documenti generati;
#         - `GET  documenti/<doc_id>/file/`: download PDF + evento `SCARICATO`;
#         - `GET/POST documenti/<doc_id>/allegati/`: lista (GET) / append (POST)
#           dei file (principale + allegati) di un documento esistente.
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
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.services.contratti_service import ContrattiService

# Codice sorgente CONTRATTO -> id risolto runtime via repo.
_CODICE_SORGENTE_CONTRATTO = "CONTRATTO"


# Scopo: Risolve il contesto comune per le view che operano "per contratto".
#        Wrapper sottile su `resolve_contesto_documentale`.
def _resolve_contesto_contratto(contratto_id: int) -> tuple[dict[str, Any], int]:
    contratto = ContrattiRepository().get_for_documento_generation(contratto_id)
    return resolve_contesto_documentale(
        entity=contratto,
        entity_id=contratto_id,
        not_found_message="Contratto non trovato.",
        emittente_message="Emittente fiscale non risolto per il contratto.",
        sorgente_codice=_CODICE_SORGENTE_CONTRATTO,
    )


class ApiContrattoEmetti(DomainAPIView):
    """`POST /api/v1/vendite/contratti/<id>/emetti/` (multipart)."""

    area_funzionale = "vendite"
    # Niente post_permission: allineato a `ApiContrattoCambiaStato` (anche le
    # transizioni di stato contratti si appoggiano all'area-level senza
    # azione di processo dedicata).
    # Override del default DRF (solo JSONParser) per consentire upload
    # multipart degli allegati assieme ai campi scalari template/tipo_output.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="VenditeContrattoEmettiReq",
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
            name="VenditeContrattoEmettiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: DRAFT -> ATTIVO con generazione+persistenza del documento e
    #        degli allegati in UNA transazione atomica. Mirror del flusso
    #        offerta/preventivo: prima cambio stato, poi genera_documento
    #        con allegati; su fallimento del render l'atomic esterno
    #        rollbacka lo stato (resta DRAFT, no record orfano).
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")
        allegati = extract_allegati(request)

        with transaction.atomic():
            emit_result = ContrattiService().emetti(contratto_id)
            contratto, sorgente_tipo_id = _resolve_contesto_contratto(contratto_id)
            documento = DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(contratto["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(contratto["id"]),
                sorgente_uid=str(contratto["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
                allegati=allegati,
            )

        return success_response({
            "contratto": emit_result,
            "documento": documento,
        })


class ApiContrattoDocumentoAllegati(DomainAPIView):
    """`/api/v1/vendite/contratti/<contratto_id>/documenti/<documento_id>/allegati/`."""

    area_funzionale = "vendite"
    # POST = upload multipart degli allegati su documento esistente.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: inline_serializer(
            name="ContrattoDocumentoAllegatiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di tutti i file del documento (principale + allegati),
    #        per elenco/scarico nella UI (row-expand su DocumentiGeneratiSorgenteList).
    def get(
        self, request: Request, contratto_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_contratto(contratto_id)
        result = DocumentGenerationService().list_documento_files(
            request.user, int(documento_id),
        )
        return success_response(result)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="ContrattoDocumentoAllegatiUploadReq",
                fields={
                    "allegati": serializers.ListField(
                        child=serializers.FileField(),
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="ContrattoDocumentoAllegatiUploadResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    #        (modalita' append post-attivazione). MIME/size validati dal service.
    def post(
        self, request: Request, contratto_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_contratto(contratto_id)
        allegati = extract_allegati(request)
        result = DocumentGenerationService().aggiungi_allegati(
            request.user, int(documento_id), allegati,
        )
        return success_response(result)


class ApiContrattoDocumentoGenera(DomainAPIView):
    """`POST /api/v1/vendite/contratti/<id>/documenti/genera/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="ContrattoDocumentoGeneraRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={201: inline_serializer(
            name="ContrattoDocumentoGeneraResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera e persiste un documento PDF dal contratto. Il caller
    #        puo' specificare un template esplicito oppure usare il default
    #        per (sorgente=CONTRATTO, emittente).
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        def _execute(payload: dict[str, Any]) -> dict[str, Any]:
            contratto, sorgente_tipo_id = _resolve_contesto_contratto(contratto_id)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")
            return DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(contratto["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(contratto["id"]),
                sorgente_uid=str(contratto["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
            )

        return handle_post_json(request, handler=_execute)


class ApiContrattoDocumentoAnteprima(DomainAPIView):
    """`POST /api/v1/vendite/contratti/<id>/documenti/anteprima/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="ContrattoDocumentoAnteprimaRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: bytes},
    )
    # Scopo: Anteprima PDF temporanea: nessun record DB, nessun file
    #        persistito, nessun evento timeline. Risposta binaria inline.
    def post(self, request: Request, contratto_id: int) -> HttpResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        contratto, sorgente_tipo_id = _resolve_contesto_contratto(contratto_id)
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")

        result = DocumentGenerationService().anteprima_documento(
            request.user,
            emittente_fiscale_id=int(contratto["emittente_fiscale_id"]),
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_id=int(contratto["id"]),
            template_documento_id=template_id,
            tipo_documento_output_id=tipo_output_id,
        )
        response = HttpResponse(
            result["pdf_bytes"], content_type=result["mime_type"],
        )
        response["Content-Disposition"] = (
            f'inline; filename="{result["nome_file"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response


class ApiContrattoDocumentiList(DomainAPIView):
    """`GET /api/v1/vendite/contratti/<id>/documenti/`."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="ContrattoDocumentiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata documenti generati per il contratto, ordinata
    #        dal repository documenti per `generato_at DESC`.
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        contratto, sorgente_tipo_id = _resolve_contesto_contratto(contratto_id)
        qp = request.query_params
        page = max(1, qp_int(qp.get("page"), 1))
        page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
        offset = (page - 1) * page_size
        result = DocumentGenerationService().list_documenti_per_sorgente(
            request.user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=str(contratto["uid"]),
            limit=page_size,
            offset=offset,
        )
        return success_response({
            **result,
            "page": page,
            "page_size": page_size,
        })


class ApiContrattoDocumentoFile(DomainAPIView):
    """`GET /api/v1/vendite/contratti/<contratto_id>/documenti/<documento_id>/file/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download PDF persistito + emit evento `SCARICATO`. La path
    #        nidifica `contratto_id` per coerenza URL; il service applica
    #        scope sul `documento_id`, mentre qui verifichiamo l'esistenza
    #        del contratto per defense-in-depth.
    def get(
        self, request: Request, contratto_id: int, documento_id: int,
    ) -> HttpResponse:
        _resolve_contesto_contratto(contratto_id)

        result = DocumentGenerationService().download_documento(
            request.user, int(documento_id),
        )
        response = HttpResponse(
            result["pdf_bytes"], content_type=result["mime_type"],
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{result["nome_file"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response
