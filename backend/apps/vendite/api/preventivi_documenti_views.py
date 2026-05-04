# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da PREVENTIVO (Tranche K
#        motore documentale). 4 endpoint sotto
#        `/api/v1/vendite/preventivi/<id>/documenti/`:
#         - `POST genera/`:    persiste un documento generato (PDF +
#           record DB + evento `GENERATO`);
#         - `POST anteprima/`: streaming PDF temporaneo, no persist
#           (Decisione 30);
#         - `GET ` (lista):    documenti generati per il preventivo
#           (paginata, scope emittente);
#         - `GET <doc_id>/file/`: download PDF principale + emit evento
#           `SCARICATO` (Decisione 31).
#
#        Permessi del dominio sorgente (Decisione 75): `area_funzionale =
#        "vendite"` -> permission default lettura preventivi. Per
#        endpoint che modificano stato (genera = INSERT) lasciamo
#        comunque il permesso default lettura: la "generazione documento"
#        non e' modifica del preventivo, ma riproduzione in PDF di un
#        dato gia' visibile all'operatore.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.preventivi_repository import PreventiviRepository

# Codice sorgente PREVENTIVO -> id risolto runtime via repo (memoria
# feedback_no_hardcoded_ids: lookup per codice, non ID numerici).
_CODICE_SORGENTE_PREVENTIVO = "PREVENTIVO"

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


# Scopo: Risolve il contesto comune per le 3 view che operano "per preventivo"
#        (genera/anteprima/lista): preventivo esiste, sorgente_tipo PREVENTIVO
#        attivo, ritorna `(preventivo_dict, sorgente_tipo_id)`.
def _resolve_contesto_preventivo(preventivo_id: int) -> tuple[dict[str, Any], int]:
    prev_repo = PreventiviRepository()
    preventivo = prev_repo.get_for_documento_generation(preventivo_id)
    ErrorManager.require(
        preventivo is not None,
        code=E_NOT_FOUND,
        message="Preventivo non trovato.",
        detail=f"preventivo_id={preventivo_id}",
    )
    assert preventivo is not None

    doc_repo = DocumentiRepository()
    sorgente = doc_repo.get_sorgente_tipo_id_by_codice(_CODICE_SORGENTE_PREVENTIVO)
    ErrorManager.require(
        sorgente is not None and sorgente.get("attivo"),
        code=E_VALIDATION,
        message="Sorgente 'PREVENTIVO' non configurata o non attiva.",
    )
    assert sorgente is not None
    return preventivo, int(sorgente["id"])


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
