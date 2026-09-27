# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory delle API view documentali "per sorgente" (emetti multipart,
#        genera, anteprima, lista, allegati, file, file-download). Estrazione
#        regola-del-2 (memoria feedback_regola_del_2_estrai_bb): il modulo
#        `<dominio>_documenti_views.py` era clonato in 5 domini vendite
#        (preventivi/offerte/contratti/ordini/ddt, ~350 righe l'uno) con soli
#        nomi/repo/service diversi. Qui vive il flusso condiviso; ogni dominio
#        dichiara SOLO i delta via `build_documenti_sorgente_views(...)`.
#
#        Testabilita' (contratto con i test API dei domini): le dipendenze
#        patchate per-modulo nei test (repository, service di dominio,
#        DocumentGenerationService) arrivano come CLOSURE definite nel modulo
#        del dominio — leggono i global del modulo dominio a call-time, quindi
#        `patch("apps.vendite.api.X_documenti_views.<Nome>")` continua a
#        funzionare. `transaction.atomic` e' patchabile da qualunque path
#        (l'attributo vive sul modulo django.db.transaction condiviso).
#
#        Convenzioni preservate 1:1 dai cloni: ordine dell'atomic in emetti
#        (prima transizione di stato, poi genera_documento con savepoint
#        annidato: se il render fallisce lo stato rollbacka), envelope
#        success_response, Content-Disposition inline (anteprima) vs
#        attachment (download), paginazione lista cap 200, defense-in-depth
#        `resolve_contesto` su ogni endpoint nested (tampering URL -> 404).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.documenti.api.contesto_helpers import resolve_contesto_documentale
from apps.documenti.api.multipart_helpers import extract_allegati


# Scopo: Costruisce le 7 view documentali per un dominio sorgente. Ritorna un
#        SimpleNamespace con le classi (emetti, genera, anteprima, lista,
#        allegati, file, file_download) + `resolve_contesto` riusabile.
#        Parametri:
#         - schema_prefix:    prefisso nomi OpenAPI (es. "Ordine" ->
#                             "OrdineDocumentoGeneraResponse", "VenditeOrdineEmettiReq")
#         - sorgente_codice:  codice_interno config.sorgenti (es. "ORDINE_VENDITA")
#         - not_found_message / emittente_message: messaggi guard contesto
#         - get_entity:       closure dominio (id) -> dict|None
#                             (repo.get_for_documento_generation)
#         - doc_service:      closure dominio () -> DocumentGenerationService
#         - emetti_call:      closure dominio (request, sorgente_id) -> dict
#                             (transizione di stato del dominio). **Opzionale**:
#                             sorgenti SENZA emissione manuale (es. FATTURA, gia'
#                             prodotta dalla pipeline — si stampa/ristampa, non si
#                             "emette") passano None → la view `emetti` non viene
#                             costruita (namespace.emetti = None).
#         - emetti_response_key: chiave del risultato transizione nella
#                             response emetti (es. "ordine", "ddt"). Ignorato se
#                             emetti_call is None.
#         - emetti_post_permission: azione di processo per emetti (opzionale,
#                             es. "cambia_stato_preventivi")
def build_documenti_sorgente_views(
    *,
    schema_prefix: str,
    sorgente_codice: str,
    not_found_message: str,
    emittente_message: str,
    get_entity: Callable[[int], dict[str, Any] | None],
    doc_service: Callable[[], Any],
    emetti_call: Callable[[Request, int], dict[str, Any]] | None = None,
    emetti_response_key: str | None = None,
    emetti_post_permission: str | None = None,
    area_funzionale: str = "vendite",
) -> SimpleNamespace:

    # Scopo: Risolve il contesto comune (entity + sorgente_tipo_id) con i
    #        guard NOT_FOUND/emittente/sorgente-attiva del BB condiviso.
    def _resolve_contesto(sorgente_id: int) -> tuple[dict[str, Any], int]:
        return resolve_contesto_documentale(
            entity=get_entity(int(sorgente_id)),
            entity_id=int(sorgente_id),
            not_found_message=not_found_message,
            emittente_message=emittente_message,
            sorgente_codice=sorgente_codice,
        )

    class Emetti(DomainAPIView):
        # Override del default DRF (solo JSONParser) per consentire upload
        # multipart degli allegati assieme ai campi scalari template/tipo_output.
        parser_classes = [MultiPartParser, FormParser]

        @extend_schema(
            request={
                "multipart/form-data": inline_serializer(
                    name=f"Vendite{schema_prefix}EmettiReq",
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
                name=f"Vendite{schema_prefix}EmettiResp",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: transizione di stato del dominio + generazione/persistenza
        #        del documento e degli allegati in UNA transazione atomica.
        #        Ordine: prima `emetti_call` (lo snapshot del context riflette
        #        lo stato avanzato — numero/stato assegnati dai trigger DB),
        #        poi `genera_documento` (savepoint annidato). Se la
        #        generazione fallisce, la transizione viene annullata dal
        #        rollback dell'atomic esterno: stato invariato, niente record
        #        documentale orfano.
        def post(self, request: Request, sorgente_id: int) -> JsonResponse:
            payload = corpo_oggetto(request)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")
            allegati = extract_allegati(request)

            with transaction.atomic():
                emit_result = emetti_call(request, int(sorgente_id))
                entity, sorgente_tipo_id = _resolve_contesto(int(sorgente_id))
                documento = doc_service().genera_documento(
                    request.user,
                    emittente_fiscale_id=int(entity["emittente_fiscale_id"]),
                    sorgente_tipo_id=sorgente_tipo_id,
                    sorgente_id=int(entity["id"]),
                    sorgente_uid=str(entity["uid"]),
                    template_documento_id=template_id,
                    tipo_documento_output_id=tipo_output_id,
                    allegati=allegati,
                )

            return success_response({
                emetti_response_key: emit_result,
                "documento": documento,
            })

    Emetti.__doc__ = f"`POST .../<sorgente_id>/emetti/` (multipart) — {schema_prefix}."
    Emetti.area_funzionale = area_funzionale
    if emetti_post_permission is not None:
        Emetti.post_permission = emetti_post_permission
    # Sorgenti senza emissione manuale (FATTURA): la view emetti non viene
    # esposta (namespace.emetti = None) → il dominio non ne cabla la rotta.
    # La classe resta definita ma inerte (closure su emetti_call=None mai chiamata).
    emetti_view = Emetti if emetti_call is not None else None

    class DocumentoGenera(DomainAPIView):
        @extend_schema(
            request=inline_serializer(
                name=f"{schema_prefix}DocumentoGeneraRequest",
                fields={
                    "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                    "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
                },
            ),
            responses={201: inline_serializer(
                name=f"{schema_prefix}DocumentoGeneraResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: EMETTE un documento NUOVO dalla sorgente: template pubblicato
        #        OGGI + dati CORRENTI, record nuovo in `documenti_generati` +
        #        evento `GENERATO`. `template_documento_id` esplicito
        #        (override) oppure template `is_default=true` per
        #        (sorgente, emittente).
        #
        #        ⚠️ **NON e' una ristampa**, benche' fino al 2026-08-03 questo
        #        commento la chiamasse cosi': per un documento del 2025
        #        produrrebbe il modello del 2026 con i dati di oggi — cioe'
        #        l'opposto di riprodurre l'originale. Il nome sbagliato faceva
        #        credere al chiamante di avere una ristampa (brief
        #        ristampa-fedele §2.2: «non e' un difetto di questo codice, fa
        #        bene il suo mestiere — e' il nome a mentire»).
        #        La ristampa vera e' `DocumentoRistampaFedele` qui sotto.
        def post(self, request: Request, sorgente_id: int) -> JsonResponse:
            # Scopo: handler handle_post_json — risolve contesto e genera il PDF.
            def _execute(payload: dict[str, Any]) -> dict[str, Any]:
                entity, sorgente_tipo_id = _resolve_contesto(sorgente_id)
                template_id = optional_int(payload, "template_documento_id")
                tipo_output_id = optional_int(payload, "tipo_documento_output_id")
                return doc_service().genera_documento(
                    request.user,
                    emittente_fiscale_id=int(entity["emittente_fiscale_id"]),
                    sorgente_tipo_id=sorgente_tipo_id,
                    sorgente_id=int(entity["id"]),
                    sorgente_uid=str(entity["uid"]),
                    template_documento_id=template_id,
                    tipo_documento_output_id=tipo_output_id,
                )

            return handle_post_json(request, handler=_execute)

    DocumentoGenera.__doc__ = f"`POST .../documenti/genera/` — {schema_prefix}."
    DocumentoGenera.area_funzionale = area_funzionale

    class DocumentoAnteprima(DomainAPIView):
        @extend_schema(
            request=inline_serializer(
                name=f"{schema_prefix}DocumentoAnteprimaRequest",
                fields={
                    "template_documento_id": serializers.IntegerField(required=False, allow_null=True),
                    "tipo_documento_output_id": serializers.IntegerField(required=False, allow_null=True),
                },
            ),
            responses={200: bytes},
        )
        # Scopo: Anteprima PDF temporanea: nessun record DB, nessun file
        #        persistito, nessun evento timeline. Stream binario
        #        `application/pdf` inline (il browser decide se aprire).
        def post(self, request: Request, sorgente_id: int) -> HttpResponse:
            # Manuale (no `handle_post_json`): la risposta e' binaria, non JSON.
            payload = corpo_oggetto(request)
            entity, sorgente_tipo_id = _resolve_contesto(sorgente_id)
            template_id = optional_int(payload, "template_documento_id")
            tipo_output_id = optional_int(payload, "tipo_documento_output_id")

            result = doc_service().anteprima_documento(
                request.user,
                emittente_fiscale_id=int(entity["emittente_fiscale_id"]),
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_id=int(entity["id"]),
                template_documento_id=template_id,
                tipo_documento_output_id=tipo_output_id,
            )
            response = HttpResponse(
                result["pdf_bytes"], content_type=result["mime_type"],
            )
            # `inline`: l'anteprima e' temporanea per design, no download forzato.
            response["Content-Disposition"] = (
                f'inline; filename="{result["nome_file"]}"'
            )
            response["Content-Length"] = str(result["size_bytes"])
            return response

    DocumentoAnteprima.__doc__ = f"`POST .../documenti/anteprima/` — {schema_prefix}."
    DocumentoAnteprima.area_funzionale = area_funzionale

    class DocumentiList(DomainAPIView):
        @extend_schema(
            parameters=[
                OpenApiParameter(name="page", type=int, required=False),
                OpenApiParameter(name="page_size", type=int, required=False),
            ],
            responses={200: inline_serializer(
                name=f"{schema_prefix}DocumentiListResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: Lista paginata documenti generati per la sorgente (render
        #        history), ordinata per `generato_at DESC` lato service.
        def get(self, request: Request, sorgente_id: int) -> JsonResponse:
            entity, sorgente_tipo_id = _resolve_contesto(sorgente_id)
            qp = request.query_params
            page = max(1, qp_int(qp.get("page"), 1))
            page_size = max(1, min(qp_int(qp.get("page_size"), 50), 200))
            offset = (page - 1) * page_size
            result = doc_service().list_documenti_per_sorgente(
                request.user,
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_uid=str(entity["uid"]),
                limit=page_size,
                offset=offset,
            )
            return success_response({
                **result,
                "page": page,
                "page_size": page_size,
            })

    DocumentiList.__doc__ = f"`GET .../documenti/` — {schema_prefix}."
    DocumentiList.area_funzionale = area_funzionale

    class DocumentoAllegati(DomainAPIView):
        # POST = upload multipart degli allegati su documento esistente.
        parser_classes = [MultiPartParser, FormParser]

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}DocumentoAllegatiListResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: Lista di tutti i file del documento (principale + allegati),
        #        per elenco/scarico nella UI (row-expand DocumentiGeneratiSorgenteList).
        def get(
            self, request: Request, sorgente_id: int, documento_id: int,
        ) -> JsonResponse:
            _resolve_contesto(sorgente_id)
            result = doc_service().list_documento_files(
                request.user, int(documento_id),
            )
            return success_response(result)

        @extend_schema(
            request={
                "multipart/form-data": inline_serializer(
                    name=f"{schema_prefix}DocumentoAllegatiUploadReq",
                    fields={
                        "allegati": serializers.ListField(
                            child=serializers.FileField(),
                        ),
                    },
                ),
            },
            responses={200: inline_serializer(
                name=f"{schema_prefix}DocumentoAllegatiUploadResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: Aggiunge allegati (file secondari) a un documento gia'
        #        generato (append). MIME/size validati dal service.
        def post(
            self, request: Request, sorgente_id: int, documento_id: int,
        ) -> JsonResponse:
            _resolve_contesto(sorgente_id)
            allegati = extract_allegati(request)
            result = doc_service().aggiungi_allegati(
                request.user, int(documento_id), allegati,
            )
            return success_response(result)

    DocumentoAllegati.__doc__ = f"`GET/POST .../documenti/<documento_id>/allegati/` — {schema_prefix}."
    DocumentoAllegati.area_funzionale = area_funzionale

    class DocumentoFile(DomainAPIView):
        @extend_schema(responses={200: bytes})
        # Scopo: Download PDF persistito + emit evento `SCARICATO`. La path
        #        nidifica l'id sorgente per coerenza URL ma il service applica
        #        scope sul `documento_id`: defense-in-depth contro tampering
        #        URL (documento di altra sorgente -> 404 unificato no leak).
        def get(
            self, request: Request, sorgente_id: int, documento_id: int,
        ) -> HttpResponse:
            # Defense-in-depth: verifica che la sorgente esista e sia visibile.
            _resolve_contesto(sorgente_id)

            result = doc_service().download_documento(
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

    DocumentoFile.__doc__ = f"`GET .../documenti/<documento_id>/file/` — {schema_prefix}."
    DocumentoFile.area_funzionale = area_funzionale

    class DocumentoFileDownload(DomainAPIView):
        @extend_schema(responses={200: bytes})
        # Scopo: Download di uno specifico file del documento per id
        #        (principale o allegato) + emit evento `SCARICATO`. Cabla la
        #        row-expand del dialog documenti FE (`downloadFile`).
        def get(
            self,
            request: Request,
            sorgente_id: int,
            documento_id: int,
            file_id: int,
        ) -> HttpResponse:
            _resolve_contesto(sorgente_id)
            result = doc_service().download_documento_file(
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

    DocumentoFileDownload.__doc__ = f"`GET .../documenti/<documento_id>/file/<file_id>/` — {schema_prefix}."
    DocumentoFileDownload.area_funzionale = area_funzionale

    class DocumentoRistampaFedele(DomainAPIView):
        @extend_schema(
            parameters=[
                OpenApiParameter(
                    name="X-Ristampa-Pdf-Hash-Match",
                    type=str,
                    location=OpenApiParameter.HEADER,
                    response=True,
                    required=False,
                    description=(
                        "`1` se il PDF ri-renderizzato coincide byte per byte "
                        "con l'originale, `0` se e' fedele nel contenuto ma "
                        "non nei byte (renderer non deterministico)."
                    ),
                ),
            ],
            responses={200: bytes},
        )
        # Scopo: RISTAMPA FEDELE — riproduce il documento **com'era**, dalla
        #        versione di template con cui nacque e dal contesto congelato
        #        di allora. Terzo percorso, distinto dagli altri due:
        #         - `file/` scarica l'ORIGINALE (solo se il file esiste);
        #         - `genera/` EMETTE un documento NUOVO (modello e dati di oggi);
        #         - questo RI-RENDERIZZA l'originale, e funziona anche per i
        #           documenti privi di file salvato.
        #        Non persiste nulla (nessuna riga nuova, nessun progressivo):
        #        l'unica scrittura e' l'evento di audit. Stream `inline` come
        #        l'anteprima: e' una consultazione, non un salvataggio.
        #        La fedelta' di BYTE viaggia in header invece che nel corpo,
        #        perche' il corpo e' il PDF — dichiarata, non nascosta.
        def get(
            self, request: Request, sorgente_id: int, documento_id: int,
        ) -> HttpResponse:
            # Defense-in-depth come gli altri endpoint nested: la sorgente
            # deve esistere ed essere visibile; lo scope vero e' sul documento.
            _resolve_contesto(sorgente_id)

            result = doc_service().ristampa_fedele(
                request.user, int(documento_id),
            )
            response = HttpResponse(
                result["pdf_bytes"], content_type=result["mime_type"],
            )
            response["Content-Disposition"] = (
                f'inline; filename="{result["nome_file"]}"'
            )
            response["Content-Length"] = str(result["size_bytes"])
            response["X-Ristampa-Pdf-Hash-Match"] = (
                "1" if result["pdf_hash_match"] else "0"
            )
            return response

    DocumentoRistampaFedele.__doc__ = (
        f"`GET .../documenti/<documento_id>/ristampa/` — {schema_prefix}."
    )
    DocumentoRistampaFedele.area_funzionale = area_funzionale

    return SimpleNamespace(
        emetti=emetti_view,
        genera=DocumentoGenera,
        anteprima=DocumentoAnteprima,
        lista=DocumentiList,
        allegati=DocumentoAllegati,
        file=DocumentoFile,
        file_download=DocumentoFileDownload,
        ristampa=DocumentoRistampaFedele,
        resolve_contesto=_resolve_contesto,
    )
