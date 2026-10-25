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
#        attachment (download), lista col contratto standard (cap 200), defense-in-depth
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
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.permissions import PassaggioDocumento
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_int,
    paginated_envelope,
    parse_list_params,
)
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
#         - emetti_passaggio: (testata, stato di emissione) per un documento sul
#                             modello (es. ("vendite.ddt", "EMESSO")): l'azione
#                             la dice la riga del passaggio (`PassaggioDocumento`,
#                             M-3). Senza, l'emissione chiede il livello sul
#                             documento. ⛔ `emetti_post_permission` (l'azione
#                             dichiarata a mano) e' ritirato il 2026-10-25: il
#                             suo ultimo consumatore, il preventivo, e' passato
#                             al modello (brief-modello-documento-vendita §8.7)
#         - area_funzionale:  area delle view (default "vendite")
#         - model_permission: oggetto del catalogo permessi della sorgente
#                             (es. ("vendite", "preventivo")): i documenti sono
#                             una parte dell'oggetto, e ne chiedono il livello
#                             (brief-db-be-fe-catalogo-oggetti-permessi §3.2).
#                             None = solo l'area. Si applica a tutte le view in
#                             UN punto (fine della factory), come l'area.
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
    emetti_passaggio: tuple[str, str] | None = None,
    area_funzionale: str = "vendite",
    model_permission: tuple[str, str] | None = None,
) -> SimpleNamespace:
    # ⛔ L'emissione e la sua chiave nella risposta vanno INSIEME: con la sola
    #    `emetti_call` la risposta avrebbe la chiave `null` (2026-10-09, trovato
    #    da mypy; tutti i domini di oggi passano entrambe). Errore di cablaggio,
    #    quindi all'import e non a una richiesta.
    if emetti_call is not None and not emetti_response_key:
        raise ValueError(
            "build_documenti_sorgente_views: `emetti_response_key` obbligatoria "
            "quando c'e' `emetti_call`"
        )
    chiave_emissione: str = emetti_response_key or ""

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

            # La view e' esposta solo con `emetti_call` (vedi `emetti_view`).
            assert emetti_call is not None
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
                chiave_emissione: emit_result,
                "documento": documento,
            })

    Emetti.__doc__ = f"`POST .../<sorgente_id>/emetti/` (multipart) — {schema_prefix}."
    if emetti_passaggio is not None:
        testata, stato_emissione = emetti_passaggio
        Emetti.post_passaggio = PassaggioDocumento(
            testata=testata, documento_kwarg="sorgente_id", stato_chiesto=stato_emissione,
        )
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
            responses={200: inline_serializer(
                name=f"{schema_prefix}DocumentoGeneraResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: EMETTE un documento NUOVO dalla sorgente: template pubblicato
        #        OGGI + dati CORRENTI, record nuovo in `documenti_generati` +
        #        evento `GENERATO`. `template_documento_id` esplicito
        #        (override) oppure la risoluzione a due livelli del DB per
        #        (sorgente, emittente): il predefinito dell'emittente, se no
        #        lo standard.
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

    class DocumentoAnteprima(DomainAPIView):
        # ⭐ Una POST che LEGGE (decisione A5 di Tid, brief-be-verifica-
        #    documentazione-api): l'anteprima non scrive niente — nessun
        #    record, nessun file, nessun evento — ed e' POST solo perche'
        #    porta un corpo. `post_accesso = "view"` le chiede il permesso di
        #    lettura e la esenta dall'Idempotency-Key, che vale per le POST
        #    che scrivono (`_ApiViewBase.initial`).
        post_accesso = "view"

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

    class DocumentiList(DomainAPIView):
        is_search_endpoint = True
        # ⭐ Il codice e' SCRITTO QUI, nella classe della factory, e non passato
        #    come parametro: gli otto domini sorgente servono tutti la STESSA
        #    lista (`documenti.documenti_sorgente`, 84) — stesse colonne, stessa
        #    whitelist, stessa query — e un parametro permetterebbe a un dominio
        #    di dichiararne un'altra. Scritto come letterale nel corpo della
        #    classe, e' anche cio' che `test_perimetro_emittente_copertura` sa
        #    leggere (`ast` visita le classi annidate nella funzione): niente
        #    sottoclassi per dominio, niente eccezione dichiarata al presidio.
        lista_codice = "documenti.documenti_sorgente"
        # ⭐ La lista si apre DENTRO il contesto di un documento (drawer o
        #    dialog della sorgente), che dice gia' da quale emittente viene: la
        #    lista a catalogo non e' certificata multi-emittente (`multi_emittente
        #    = f`) e senza questa riga il cancello chiederebbe al super admin su
        #    «Tutti» di scegliere l'emittente del documento che ha davanti.
        # ⚠️ Il parametro NON filtra: le righe le fissa la sorgente nel path, e
        #    per modello i documenti di una sorgente sono di un emittente solo.
        #    Farne un filtro trasformerebbe un id della famiglia sbagliata in
        #    una lista vuota, cioe' in «questo documento non ha PDF».
        lista_emittente_param = "emittente_fiscale_id"

        @extend_schema(
            parameters=[
                param_ricerca_full(),
                OpenApiParameter(
                    name="emittente_fiscale_id", type=int, required=False,
                    description=(
                        "L'emittente del documento sorgente, gia' fissato dal "
                        "contesto che apre la lista: scioglie il cancello di "
                        "perimetro, non filtra."
                    ),
                ),
                OpenApiParameter(name="limit", type=int, required=False),
                OpenApiParameter(name="offset", type=int, required=False),
                OpenApiParameter(name="order_by", type=str, required=False),
                OpenApiParameter(name="order_dir", type=str, required=False),
            ],
            responses={200: inline_serializer(
                name=f"{schema_prefix}DocumentiListResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: Lista paginata documenti generati per la sorgente (render
        #        history), col contratto di lista standard: `limit`/`offset`,
        #        `order_by`/`order_dir` sulla whitelist del repository, `search`
        #        dal catalogo, envelope `paginated_envelope` (`count`).
        # ⛔ Fino al 2026-09-27 parlava `page`/`page_size` con default 50 e
        #    rispondeva `total_count`: il frontend non mandava `page_size`, e
        #    la lista si fermava ai primi 50 documenti SENZA dirlo (nessun
        #    paginatore a video). Ora e' `parse_list_params` come ogni lista.
        def get(self, request: Request, sorgente_id: int) -> JsonResponse:
            entity, sorgente_tipo_id = _resolve_contesto(sorgente_id)
            p = parse_list_params(request.query_params, default_order="generato_at")
            result = doc_service().list_documenti_per_sorgente(
                request.user,
                sorgente_tipo_id=sorgente_tipo_id,
                sorgente_uid=str(entity["uid"]),
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=p["limit"],
                offset=p["offset"],
            )
            return success_response(paginated_envelope(
                result["results"], result["total_count"], p["page"], p["limit"],
            ))

    DocumentiList.__doc__ = f"`GET .../documenti/` — {schema_prefix}."

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

    # Permesso: area e oggetto in un punto solo, per tutte le view costruite
    # (anche Emetti, dove pero' decide `post_permission` quando c'e').
    for view_cls in (
        Emetti, DocumentoGenera, DocumentoAnteprima, DocumentiList,
        DocumentoAllegati, DocumentoFile, DocumentoFileDownload,
        DocumentoRistampaFedele,
    ):
        view_cls.area_funzionale = area_funzionale
        if model_permission is not None:
            view_cls.model_permission = model_permission

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
