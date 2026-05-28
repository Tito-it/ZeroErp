# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da OFFERTA_COMMERCIALE.
#        Mirror di `preventivi_documenti_views` / `contratti_documenti_views`
#        con due specificita' del flusso offerta (decisione 2026-05-27):
#         - l'emissione (BOZZA -> EMESSA) GENERA e PERSISTE il documento
#           insieme agli eventuali allegati, in UNA transazione atomica
#           (`ApiOffertaEmetti`): l'utente conferma una sola volta e
#           ottiene stato avanzato + PDF + allegati; se qualcosa fallisce
#           niente persiste e lo stato resta BOZZA;
#         - gli allegati (PDF/immagini caricati dall'utente) sono file
#           secondari del documento generato; restano aggiungibili anche
#           dopo l'emissione (`ApiOffertaDocumentoAllegati`), finche' lo
#           stato sorgente lo consente (regola lato UI/dominio).
#
#        Endpoint sotto `/api/v1/vendite/offerte/<id>/`:
#         - `POST emetti/`:                 multipart: emetti + genera + allegati
#         - `POST documenti/anteprima/`:    streaming PDF temporaneo (BOZZA)
#         - `GET  documenti/`:              lista documenti generati
#         - `GET  documenti/<doc_id>/file/`:        download PDF principale
#         - `GET  documenti/<doc_id>/allegati/`:    lista file (princ.+all.)
#         - `POST documenti/<doc_id>/allegati/`:    aggiunge allegati (append)
#         - `GET  documenti/<doc_id>/file/<file_id>/`: download file per id
#
#        Permessi del dominio sorgente (Decisione 75): `area_funzionale =
#        "vendite"`.
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
from apps.core.api.payload_validators import optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.documenti.api.contesto_helpers import resolve_contesto_documentale
from apps.documenti.api.multipart_helpers import extract_allegati
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.services.offerte_service import OfferteService

# Codice sorgente OFFERTA_COMMERCIALE -> id risolto runtime via repo
# (memoria feedback_no_hardcoded_ids: lookup per codice, non ID numerici).
_CODICE_SORGENTE_OFFERTA = "OFFERTA_COMMERCIALE"


# Scopo: Risolve il contesto comune per le view che operano "per offerta":
#        offerta esistente, emittente risolto, sorgente_tipo
#        OFFERTA_COMMERCIALE attiva. Wrapper sottile su
#        `resolve_contesto_documentale`.
def _resolve_contesto_offerta(offerta_id: int) -> tuple[dict[str, Any], int]:
    offerta = OfferteRepository().get_for_documento_generation(offerta_id)
    return resolve_contesto_documentale(
        entity=offerta,
        entity_id=offerta_id,
        not_found_message="Offerta commerciale non trovata.",
        emittente_message="Emittente fiscale non risolto per l'offerta.",
        sorgente_codice=_CODICE_SORGENTE_OFFERTA,
    )


class ApiOffertaEmetti(DomainAPIView):
    """`POST /api/v1/vendite/offerte/<id>/emetti/` (multipart)."""

    area_funzionale = "vendite"
    # Override del default DRF (solo JSONParser) per consentire upload
    # multipart degli allegati assieme ai campi scalari template/tipo_output.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="VenditeOffertaEmettiReq",
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
            name="VenditeOffertaEmettiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: BOZZA -> EMESSA con generazione+persistenza del documento e
    #        degli allegati in UNA transazione atomica. Ordine: prima
    #        `emetti` (cosi' lo snapshot del context riflette stato EMESSA),
    #        poi `genera_documento` (che apre il proprio savepoint annidato).
    #        Se la generazione fallisce, l'`emetti` viene annullato dal
    #        rollback dell'atomic esterno -> stato resta BOZZA, niente record
    #        documentale orfano. Il trigger DB su `emetti` verifica comunque
    #        `listino_versione_id` + versione ATTIVA prima di tutto.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")
        allegati = extract_allegati(request)

        with transaction.atomic():
            emit_result = OfferteService().emetti(offerta_id)
            offerta, sorgente_tipo_id = _resolve_contesto_offerta(offerta_id)
            documento = DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(offerta["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(offerta["id"]),
                sorgente_uid=str(offerta["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
                allegati=allegati,
            )

        return success_response({
            "offerta": emit_result,
            "documento": documento,
        })


class ApiOffertaDocumentoAnteprima(DomainAPIView):
    """`POST /api/v1/vendite/offerte/<id>/documenti/anteprima/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="OffertaDocumentoAnteprimaRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: bytes},
    )
    # Scopo: Anteprima PDF temporanea (Decisione 30): nessun record DB,
    #        nessun file persistito, nessun evento timeline. Usata in BOZZA
    #        per la preview del documento prima dell'emissione. Risposta
    #        binaria `application/pdf` inline.
    def post(self, request: Request, offerta_id: int) -> HttpResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        offerta, sorgente_tipo_id = _resolve_contesto_offerta(offerta_id)
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")

        result = DocumentGenerationService().anteprima_documento(
            request.user,
            emittente_fiscale_id=int(offerta["emittente_fiscale_id"]),
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_id=int(offerta["id"]),
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


class ApiOffertaDocumentiList(DomainAPIView):
    """`GET /api/v1/vendite/offerte/<id>/documenti/`."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="OffertaDocumentiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata documenti generati per l'offerta, ordinata dal
    #        repository documenti per `generato_at DESC`.
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        offerta, sorgente_tipo_id = _resolve_contesto_offerta(offerta_id)
        qp = request.query_params
        page = max(1, qp_int(qp.get("page"), 1))
        page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
        offset = (page - 1) * page_size
        result = DocumentGenerationService().list_documenti_per_sorgente(
            request.user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=str(offerta["uid"]),
            limit=page_size,
            offset=offset,
        )
        return success_response({
            **result,
            "page": page,
            "page_size": page_size,
        })


class ApiOffertaDocumentoFile(DomainAPIView):
    """`GET /api/v1/vendite/offerte/<offerta_id>/documenti/<documento_id>/file/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download PDF principale persistito + emit evento `SCARICATO`.
    #        La path nidifica `offerta_id` per coerenza URL; il service
    #        applica scope sul `documento_id`, qui verifichiamo l'esistenza
    #        dell'offerta per defense-in-depth.
    def get(
        self, request: Request, offerta_id: int, documento_id: int,
    ) -> HttpResponse:
        _resolve_contesto_offerta(offerta_id)
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


class ApiOffertaDocumentoAllegati(DomainAPIView):
    """`/api/v1/vendite/offerte/<offerta_id>/documenti/<documento_id>/allegati/`."""

    area_funzionale = "vendite"
    # POST = upload multipart degli allegati su documento esistente.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: inline_serializer(
            name="OffertaDocumentoAllegatiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di tutti i file del documento (principale + allegati),
    #        per elenco/scarico nella UI.
    def get(
        self, request: Request, offerta_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_offerta(offerta_id)
        result = DocumentGenerationService().list_documento_files(
            request.user, int(documento_id),
        )
        return success_response(result)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="OffertaDocumentoAllegatiUploadReq",
                fields={
                    "allegati": serializers.ListField(
                        child=serializers.FileField(),
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="OffertaDocumentoAllegatiUploadResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    #        (modalita' append post-emissione). La regola di stato — fino a
    #        EMESSA compresa — e' applicata lato UI/dominio; qui il service
    #        valida solo MIME/size e persiste i file.
    def post(
        self, request: Request, offerta_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_offerta(offerta_id)
        allegati = extract_allegati(request)
        result = DocumentGenerationService().aggiungi_allegati(
            request.user, int(documento_id), allegati,
        )
        return success_response(result)


class ApiOffertaDocumentoFileDownload(DomainAPIView):
    """`GET .../documenti/<documento_id>/file/<file_id>/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download di uno specifico file del documento per id (principale
    #        o allegato) + emit evento `SCARICATO`.
    def get(
        self,
        request: Request,
        offerta_id: int,
        documento_id: int,
        file_id: int,
    ) -> HttpResponse:
        _resolve_contesto_offerta(offerta_id)
        result = DocumentGenerationService().download_documento_file(
            request.user, int(documento_id), int(file_id),
        )
        response = HttpResponse(
            result["pdf_bytes"], content_type=result["mime_type"],
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{result["nome_file"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response
