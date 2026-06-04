# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da ORDINE_VENDITA (stampa
#        conferma d'ordine). Quarto dominio cablato sul motore `documenti`
#        dopo preventivo/offerta/contratto. Endpoint sotto
#        `/api/v1/vendite/ordini/<id>/`:
#         - `POST documenti/genera/`:        persiste un documento generato
#           (PDF + record DB + evento `GENERATO`);
#         - `POST documenti/anteprima/`:     streaming PDF temporaneo, no
#           persist;
#         - `GET  documenti/` (lista):       documenti generati per l'ordine
#           (paginata, scope emittente);
#         - `GET  documenti/<doc_id>/file/`: download PDF principale + emit
#           evento `SCARICATO`;
#         - `GET/POST documenti/<doc_id>/allegati/`: lista file / append allegati.
#
#        Decisione §12.4(a) (analisi-ordini-vendita.md): la stampa e'
#        DISACCOPPIATA dallo stato. Niente `emetti/` (transizione atomica
#        stato+PDF come preventivi/offerte): l'ordine ha gia' `numero` in BOZZA
#        e la sua transizione chiave e' CONFERMA (che governa il push commessa,
#        non la stampa). La conferma d'ordine PDF e' ristampabile on-demand a
#        qualsiasi stato consultabile.
#
#        Permessi del dominio sorgente: `area_funzionale = "vendite"` ->
#        permission default lettura ordini. La generazione documento non e'
#        modifica dell'ordine ma riproduzione in PDF di un dato gia' visibile
#        all'operatore (mirror della scelta preventivi/offerte).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

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
from apps.vendite.db.ordini_repository import OrdiniRepository

# Codice sorgente ORDINE_VENDITA -> id risolto runtime via repo (memoria
# feedback_no_hardcoded_ids: lookup per codice, non ID numerici). Allineato a
# config.sorgenti.codice + documenti.tipi_documento_output.codice +
# template_documenti.context_builder_code (tutti = ORDINE_VENDITA).
_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"


# Scopo: Risolve il contesto comune per le view che operano "per ordine".
#        Wrapper sottile su `resolve_contesto_documentale`.
def _resolve_contesto_ordine(ordine_id: int) -> tuple[dict[str, Any], int]:
    ordine = OrdiniRepository().get_for_documento_generation(ordine_id)
    return resolve_contesto_documentale(
        entity=ordine,
        entity_id=ordine_id,
        not_found_message="Ordine non trovato.",
        emittente_message="Emittente fiscale non risolto per l'ordine.",
        sorgente_codice=_CODICE_SORGENTE_ORDINE,
    )


class ApiOrdineDocumentoGenera(DomainAPIView):
    """`POST /api/v1/vendite/ordini/<id>/documenti/genera/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="OrdineDocumentoGeneraRequest",
            fields={
                "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={201: inline_serializer(
            name="OrdineDocumentoGeneraResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera e persiste un documento PDF dall'ordine. Si registra in
    #        `documenti_generati` con evento `GENERATO`. Il caller puo'
    #        specificare `template_documento_id` esplicito (override) o lasciare
    #        che il service usi il template `is_default=true` per la coppia
    #        (sorgente=ORDINE_VENDITA, emittente).
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        def _execute(payload: dict[str, Any]) -> dict[str, Any]:
            ordine, sorgente_tipo_id = _resolve_contesto_ordine(ordine_id)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")
            return DocumentGenerationService().genera_documento(
                request.user,
                emittente_fiscale_id=int(ordine["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(ordine["id"]),
                sorgente_uid=str(ordine["uid"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
            )

        return handle_post_json(request, handler=_execute)


class ApiOrdineDocumentoAnteprima(DomainAPIView):
    """`POST /api/v1/vendite/ordini/<id>/documenti/anteprima/`."""

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="OrdineDocumentoAnteprimaRequest",
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
    def post(self, request: Request, ordine_id: int) -> HttpResponse:
        # Manuale (no `handle_post_json`): la risposta e' binaria, non JSON.
        payload = request.data if isinstance(request.data, dict) else {}
        ordine, sorgente_tipo_id = _resolve_contesto_ordine(ordine_id)
        template_id = optional_int(payload, "template_documento_id")
        tipo_output_id = optional_int(payload, "tipo_documento_output_id")

        result = DocumentGenerationService().anteprima_documento(
            request.user,
            emittente_fiscale_id=int(ordine["emittente_fiscale_id"]),
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_id=int(ordine["id"]),
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


class ApiOrdineDocumentiList(DomainAPIView):
    """`GET /api/v1/vendite/ordini/<id>/documenti/`."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="OrdineDocumentiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata documenti generati per l'ordine (render history).
    #        Ordinata per `generato_at DESC` lato service.
    def get(self, request: Request, ordine_id: int) -> JsonResponse:
        ordine, sorgente_tipo_id = _resolve_contesto_ordine(ordine_id)
        qp = request.query_params
        page = max(1, qp_int(qp.get("page"), 1))
        page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
        offset = (page - 1) * page_size
        result = DocumentGenerationService().list_documenti_per_sorgente(
            request.user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=str(ordine["uid"]),
            limit=page_size,
            offset=offset,
        )
        return success_response({
            **result,
            "page": page,
            "page_size": page_size,
        })


class ApiOrdineDocumentoAllegati(DomainAPIView):
    """`/api/v1/vendite/ordini/<ordine_id>/documenti/<documento_id>/allegati/`."""

    area_funzionale = "vendite"
    # POST = upload multipart degli allegati su documento esistente.
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: inline_serializer(
            name="OrdineDocumentoAllegatiListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di tutti i file del documento (principale + allegati), per
    #        elenco/scarico nella UI (row-expand su DocumentiGeneratiSorgenteList).
    def get(
        self, request: Request, ordine_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_ordine(ordine_id)
        result = DocumentGenerationService().list_documento_files(
            request.user, int(documento_id),
        )
        return success_response(result)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="OrdineDocumentoAllegatiUploadReq",
                fields={
                    "allegati": serializers.ListField(
                        child=serializers.FileField(),
                    ),
                },
            ),
        },
        responses={200: inline_serializer(
            name="OrdineDocumentoAllegatiUploadResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    #        (modalita' append). MIME/size validati dal service.
    def post(
        self, request: Request, ordine_id: int, documento_id: int,
    ) -> JsonResponse:
        _resolve_contesto_ordine(ordine_id)
        allegati = extract_allegati(request)
        result = DocumentGenerationService().aggiungi_allegati(
            request.user, int(documento_id), allegati,
        )
        return success_response(result)


class ApiOrdineDocumentoFile(DomainAPIView):
    """`GET /api/v1/vendite/ordini/<ordine_id>/documenti/<documento_id>/file/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download PDF persistito + emit evento `SCARICATO` (log ad ogni
    #        download). La path nidifica `ordine_id` per coerenza URL ma il
    #        service applica scope sull'`documento_id`: defense-in-depth contro
    #        tampering URL (documento di altro ordine via path errato -> 404
    #        unificato no leak).
    def get(
        self, request: Request, ordine_id: int, documento_id: int,
    ) -> HttpResponse:
        # Defense-in-depth: verifica che l'ordine esista e sia visibile.
        _resolve_contesto_ordine(ordine_id)

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


class ApiOrdineDocumentoFileDownload(DomainAPIView):
    """`GET .../documenti/<documento_id>/file/<file_id>/`."""

    area_funzionale = "vendite"

    @extend_schema(responses={200: bytes})
    # Scopo: Download di uno specifico file del documento per id (principale o
    #        allegato) + emit evento `SCARICATO`. Cabla l'intero BB documenti
    #        (il client FE `ordineDocumenti.downloadFile` / la row-expand del
    #        dialog lo usano): senza, sarebbe un 404 latente appena si abilita
    #        la modalita' "scarica da archivio". Mirror di offerte.
    def get(
        self,
        request: Request,
        ordine_id: int,
        documento_id: int,
        file_id: int,
    ) -> HttpResponse:
        _resolve_contesto_ordine(ordine_id)
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
