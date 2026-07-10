# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da DDT_VENDITA (stampa DDT
#        accompagnatorio). Quinto dominio cablato sul motore `documenti`
#        dopo preventivo/offerta/contratto/ordine. Endpoint sotto
#        `/api/v1/vendite/ddt/<id>/`:
#         - `POST emetti/`:                  multipart: DRAFT->EMESSO (il
#           trigger DB assegna il `numero`) + genera documento + allegati in
#           transazione atomica (mirror del flusso ordine `ApiOrdineEmetti`);
#         - `POST documenti/genera/`:        persiste un documento generato
#           (PDF + record DB + evento `GENERATO`);
#         - `POST documenti/anteprima/`:     streaming PDF temporaneo, no
#           persist;
#         - `GET  documenti/` (lista):       documenti generati per il DDT
#           (paginata, scope emittente);
#         - `GET  documenti/<doc_id>/file/`: download PDF principale + emit
#           evento `SCARICATO`;
#         - `GET/POST documenti/<doc_id>/allegati/`: lista file / append allegati.
#
#        Flusso documentale (mirror famiglia vendite): in DRAFT solo anteprima
#        on-demand; nel passaggio DRAFT->EMESSO (`emetti/`) il documento viene
#        generato e archiviato in transazione atomica con allegati opzionali.
#        L'emissione del DDT e' l'atto formale che assegna il numero ed e' il
#        momento naturale in cui l'accompagnatorio va generato e persistito
#        (viaggia con la merce). Gli endpoint genera/anteprima/lista/file/
#        allegati restano per ristampa e gestione documentale post-bozza.
#
#        Ordine nell'atomic: prima `ddt_service.emetti` (il trigger DB assegna
#        il numero -> lo snapshot del context contiene il numero definitivo),
#        poi `genera_documento` (savepoint annidato). Se la generazione
#        fallisce, l'emissione viene annullata dal rollback -> stato resta
#        DRAFT, numero non consumato, niente record documentale orfano.
#
#        Permessi del dominio sorgente: `area_funzionale = "vendite"` ->
#        permission default lettura DDT. La generazione documento non e'
#        modifica del DDT ma riproduzione in PDF di un dato gia' visibile
#        all'operatore (mirror della scelta ordini/preventivi/offerte).
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
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services import ddt_service

# Codice sorgente DDT_VENDITA -> id risolto runtime via repo (memoria
# feedback_no_hardcoded_ids: lookup per codice, non ID numerici). Allineato a
# config.sorgenti.codice_interno + documenti.tipi_documento_output.codice +
# template_documenti.context_builder_code (tutti = DDT_VENDITA).
_CODICE_SORGENTE_DDT = "DDT_VENDITA"


# Scopo: Risolve il contesto comune per le view che operano "per DDT".
#        Wrapper sottile su `resolve_contesto_documentale`.
def _resolve_contesto_ddt(ddt_id: int) -> tuple[dict[str, Any], int]:
    ddt = DdtRepository().get_for_documento_generation(ddt_id)
    return resolve_contesto_documentale(
        entity=ddt,
        entity_id=ddt_id,
        not_found_message="DDT non trovato.",
        emittente_message="Emittente fiscale non risolto per il DDT.",
        sorgente_codice=_CODICE_SORGENTE_DDT,
    )


class ApiDdtEmetti(DomainAPIView):
    """`POST /api/v1/vendite/ddt/<ddt_id>/emetti/` (multipart)."""

    area_funzionale = "vendite"
    # Override del default DRF (solo JSONParser) per consentire upload
    # multipart degli allegati assieme ai campi scalari template/tipo_output.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="VenditeDdtEmettiReq",
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
            name="VenditeDdtEmettiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: DRAFT -> EMESSO con generazione+persistenza del documento e degli
    #        allegati in UNA transazione atomica. Ordine: prima
    #        `ddt_service.emetti` (il trigger DB assegna il `numero` -> lo
    #        snapshot del context riflette il numero definitivo), poi
    #        `genera_documento` (savepoint annidato). Se la generazione
    #        fallisce, l'emissione viene annullata dal rollback -> stato resta
    #        DRAFT, niente record documentale orfano. Mirror del flusso ordine.
    #        `emetti` resta il punto di dominio (guard transizione dal trigger
    #        DB + gate componenti BoM): qui si riusa, non si duplica.
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        payload = request.data if isinstance(request.data, dict) else {}
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")
        allegati = extract_allegati(request)

        with transaction.atomic():
            emetti_result = ddt_service.emetti(int(ddt_id))
            ddt, sorgente_tipo_id = _resolve_contesto_ddt(int(ddt_id))
            documento = DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(ddt["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(ddt["id"]),
                sorgente_uid=str(ddt["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
                allegati=allegati,
            )

        return success_response({
            "ddt": emetti_result,
            "documento": documento,
        })


class ApiDdtDocumentoGenera(DomainAPIView):
    """`POST /api/v1/vendite/ddt/<ddt_id>/documenti/genera/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="DdtDocumentoGeneraRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={201: inline_serializer(
            name="DdtDocumentoGeneraResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera e persiste un documento PDF dal DDT (ristampa/archivio).
    #        Si registra in `documenti_generati` con evento `GENERATO`. Il
    #        caller puo' specificare `template_documento_id` esplicito
    #        (override) o lasciare che il service usi il template
    #        `is_default=true` per la coppia (sorgente=DDT_VENDITA, emittente).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        # Scopo: handler handle_post_json — risolve contesto e genera il PDF.
        def _execute(payload: dict[str, Any]) -> dict[str, Any]:
            ddt, sorgente_tipo_id = _resolve_contesto_ddt(ddt_id)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")
            return DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(ddt["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(ddt["id"]),
                sorgente_uid=str(ddt["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
            )

        return handle_post_json(request, handler=_execute)


class ApiDdtDocumentoAnteprima(DomainAPIView):
    """`POST /api/v1/vendite/ddt/<ddt_id>/documenti/anteprima/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="DdtDocumentoAnteprimaRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: bytes},
    )
    # Scopo: Anteprima PDF temporanea: nessun record DB, nessun file
    #        persistito, nessun evento timeline. Risposta come stream binario
    #        `application/pdf` inline (il browser decide se aprire o scaricare).
    #        In DRAFT il `numero` e' NULL: il template mostra il fallback.
    def post(self, request: Request, ddt_id: int) -> HttpResponse:
        # Manuale (no `handle_post_json`): la risposta e' binaria, non JSON.
        payload = request.data if isinstance(request.data, dict) else {}
        ddt, sorgente_tipo_id = _resolve_contesto_ddt(ddt_id)
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")

        result = DocumentGenerationService().anteprima_documento(
            request.user,
            emittente_fiscale_id=int(ddt["emittente_fiscale_id"]),
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_id=int(ddt["id"]),
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


class ApiDdtDocumentiList(DomainAPIView):
    """`GET /api/v1/vendite/ddt/<ddt_id>/documenti/`."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="DdtDocumentiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata documenti generati per il DDT (render history).
    #        Ordinata per `generato_at DESC` lato service.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        ddt, sorgente_tipo_id = _resolve_contesto_ddt(ddt_id)
        qp = request.query_params
        page = max(1, qp_int(qp.get("page"), 1))
        page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
        offset = (page - 1) * page_size
        result = DocumentGenerationService().list_documenti_per_sorgente(
            request.user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=str(ddt["uid"]),
            limit=page_size,
            offset=offset,
        )
        return success_response({
            **result,
            "page": page,
            "page_size": page_size,
        })


class ApiDdtDocumentoAllegati(DomainAPIView):
    """`/api/v1/vendite/ddt/<ddt_id>/documenti/<documento_id>/allegati/`."""

    area_funzionale = "vendite"
    # POST = upload multipart degli allegati su documento esistente.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: inline_serializer(
            name="DdtDocumentoAllegatiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di tutti i file del documento (principale + allegati), per
    #        elenco/scarico nella UI (row-expand su DocumentiGeneratiSorgenteList).
    def get(
        self, request: Request, ddt_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_ddt(ddt_id)
        result = DocumentGenerationService().list_documento_files(
            request.user, int(documento_id),
        )
        return success_response(result)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="DdtDocumentoAllegatiUploadReq",
                fields={
                    "allegati": serializers.ListField(
                        child=serializers.FileField(),
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="DdtDocumentoAllegatiUploadResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    #        (modalita' append). MIME/size validati dal service.
    def post(
        self, request: Request, ddt_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_ddt(ddt_id)
        allegati = extract_allegati(request)
        result = DocumentGenerationService().aggiungi_allegati(
            request.user, int(documento_id), allegati,
        )
        return success_response(result)


class ApiDdtDocumentoFile(DomainAPIView):
    """`GET /api/v1/vendite/ddt/<ddt_id>/documenti/<documento_id>/file/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download PDF persistito + emit evento `SCARICATO` (log ad ogni
    #        download). La path nidifica `ddt_id` per coerenza URL ma il
    #        service applica scope sull'`documento_id`: defense-in-depth contro
    #        tampering URL (documento di altro DDT via path errato -> 404
    #        unificato no leak).
    def get(
        self, request: Request, ddt_id: int, documento_id: int,
    ) -> HttpResponse:
        # Defense-in-depth: verifica che il DDT esista e sia visibile.
        _resolve_contesto_ddt(ddt_id)

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


class ApiDdtDocumentoFileDownload(DomainAPIView):
    """`GET .../documenti/<documento_id>/file/<file_id>/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download di uno specifico file del documento per id (principale o
    #        allegato) + emit evento `SCARICATO`. Cabla l'intero BB documenti
    #        (il client FE `ddtDocumenti.downloadFile` / la row-expand del
    #        dialog lo usano). Mirror di ordini/offerte.
    def get(
        self,
        request: Request,
        ddt_id: int,
        documento_id: int,
        file_id: int,
    ) -> HttpResponse:
        _resolve_contesto_ddt(ddt_id)
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
