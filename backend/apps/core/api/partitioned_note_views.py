# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory di view DRF per esporre il CRUD note partizionate
#        (cfr. apps.core.services.partitioned_note_service). Un solo set
#        di view riusabile da qualunque dominio: il caller passa
#        area_funzionale + service_factory e ottiene 2 classi pronte da
#        montare in urls (ListCreate + Detail).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Callable

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.openapi_params import param_ricerca_full, parametri_finestra
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id, handle_post_json
from apps.core.api.payload_validators import envelope_da_offset, parse_list_params, corpo_oggetto, qp_bool_optional, qp_int_strict, qp_str
from apps.core.api.success_responses import success_response
from apps.core.services.partitioned_note_service import PartitionedNoteService

# Type alias: il caller fornisce un callable senza argomenti che istanzia
# il service. Permette di iniettare contesto o mock nei test.
ServiceFactory = Callable[[], PartitionedNoteService]


# Scopo: Costruisce inline_serializer request/response unici per la coppia
#        (target_tipo, suffisso). Serializer name DEVE essere unico nel
#        progetto drf-spectacular, altrimenti lo schema OpenAPI collisiona.
def _make_serializer_name(target_tipo: str, suffix: str) -> str:
    return f"PartitionedNote_{target_tipo}_{suffix}"


# Scopo: Il nome di classe delle view, in CamelCase dal codice del tipo
#        (`DDT_VENDITA` -> `DdtVendita`). Dal 2026-10-25 i codici sono quelli
#        di `config.tipi_entita`, con `_`: `.title()` dava `Ddt_Vendita`.
def _make_view_name(target_tipo: str, suffix: str) -> str:
    camel = "".join(parte.capitalize() for parte in target_tipo.split("_"))
    return f"Note{camel}{suffix}"


# Scopo: Costruisce la coppia (ListCreateView, DetailView) cablate sul
#        service factory passato. Le view derivano da DomainAPIView con
#        area_funzionale del dominio chiamante.
#
#        Parametri:
#         - area_funzionale: area DB del dominio (es. "vendite", "catalogo")
#         - parent_path_param: nome del kwarg URL che porta il target_id
#                              (es. "preventivo_id", "contratto_id")
#         - service_factory: callable () -> PartitionedNoteService
#         - target_tipo: per naming serializer drf-spectacular univoco
#         - model_permission: tuple (app_label, model_name) opzionale per
#                             livello oggetto v2 permessi (es. ("vendite",
#                             "preventivo")). Se None, fallback al livello area.
#         - is_search_endpoint: True abilita SearchBurstRateThrottle sulla GET
#                               (default True per la lista note)
def make_note_views(
    *,
    area_funzionale: str,
    parent_path_param: str,
    service_factory: ServiceFactory,
    target_tipo: str,
    model_permission: tuple[str, str] | None = None,
    is_search_endpoint: bool = True,
) -> tuple[type[DomainAPIView], type[DomainAPIView]]:
    # Serializer inline univoci per il dominio. Schema OpenAPI puro: i campi
    # sono dichiarativi per drf-spectacular ma la validazione effettiva resta
    # nel service (PayloadValidator + map_integrity_error).
    create_request = inline_serializer(
        name=_make_serializer_name(target_tipo, "CreateRequest"),
        fields={
            "testo": serializers.CharField(required=False, allow_blank=True, allow_null=True),
            "testo_md": serializers.CharField(required=False, allow_blank=True, allow_null=True),
            "anchor_tipo": serializers.CharField(required=False),
            "posizione": serializers.CharField(required=False),
            "seq": serializers.IntegerField(required=False),
            "visibile": serializers.BooleanField(required=False),
            "solo_stampa": serializers.BooleanField(required=False),
            "id_stile": serializers.IntegerField(required=False),
            "id_lingua": serializers.IntegerField(required=False),
            "meta": serializers.JSONField(required=False),
            "target_riga_id": serializers.IntegerField(required=False),
        },
    )
    patch_request = inline_serializer(
        name=_make_serializer_name(target_tipo, "PatchRequest"),
        fields={
            "testo": serializers.CharField(required=False, allow_blank=True, allow_null=True),
            "testo_md": serializers.CharField(required=False, allow_blank=True, allow_null=True),
            "anchor_tipo": serializers.CharField(required=False),
            "posizione": serializers.CharField(required=False),
            "seq": serializers.IntegerField(required=False),
            "visibile": serializers.BooleanField(required=False),
            "solo_stampa": serializers.BooleanField(required=False),
            "id_stile": serializers.IntegerField(required=False),
            "id_lingua": serializers.IntegerField(required=False),
            "meta": serializers.JSONField(required=False),
        },
    )
    list_response = inline_serializer(
        name=_make_serializer_name(target_tipo, "ListResponse"),
        fields={
            "data": serializers.DictField(),
            "meta": serializers.DictField(required=False),
        },
    )
    detail_response = inline_serializer(
        name=_make_serializer_name(target_tipo, "DetailResponse"),
        fields={
            "data": serializers.DictField(),
            "meta": serializers.DictField(required=False),
        },
    )

    _area = area_funzionale
    _model_perm = model_permission
    _is_search = is_search_endpoint
    _parent_param = parent_path_param

    class NoteListCreateView(DomainAPIView):
        """List + create note su un documento padre.

        URL pattern atteso:
            /<area>/<entita>/<parent_id>/note/
        """

        area_funzionale = _area
        is_search_endpoint = _is_search
        # ⭐ La lista a catalogo della tabella-madre (`vendite.note`, D-2,
        #    2026-10-31), col perimetro dell'emittente: il documento lo porta,
        #    e il FE lo passa come lasciapassare del cancello.
        # ⚠️ Letterale perche' il presidio del perimetro legge il codice dal
        #    sorgente. La fabbrica oggi la montano le sole partizioni di
        #    `vendite.note` (`apps/vendite/api/note_views.py`); il repository
        #    NON lo verifica (`lista_codice` lo ricava dalla partizione, e
        #    accetta anche `catalogo.note`). ⛔ Montarla su un'altra tabella-
        #    madre vuole il codice parametrico qui, o cancello e ricerca
        #    girerebbero su due liste diverse.
        # ⚠️ Il cancello vale anche per il POST (`initial()`): il FE manda
        #    l'emittente anche sulla creazione (`makeNotesApi`).
        lista_codice = "vendite.note"
        lista_emittente_param = "emittente_fiscale_id"
        if _model_perm is not None:
            model_permission = _model_perm

        @extend_schema(
            parameters=[
                param_ricerca_full(),
                OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
                OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
                OpenApiParameter(
                    name="emittente_fiscale_id", type=int,
                    location=OpenApiParameter.QUERY, required=False,
                    description="L'emittente del documento: scioglie il cancello di perimetro della lista.",
                ),
                OpenApiParameter(
                    name="target_riga_id", type=int,
                    location=OpenApiParameter.QUERY, required=False,
                    description="Filtra le note di una specifica riga.",
                ),
                OpenApiParameter(
                    name="include_invisible", type=bool,
                    location=OpenApiParameter.QUERY, required=False,
                    description="Default True; passare False per filtrare visibile=TRUE.",
                ),
                *parametri_finestra(),
            ],
            responses={200: list_response},
        )
        # Scopo: Restituisce la lista paginata note del documento padre.
        def get(self, request: Request, **path_kwargs: Any) -> JsonResponse:
            target_id = int(path_kwargs[_parent_param])
            qp = request.query_params
            raw_riga = qp_str(qp.get("target_riga_id"))
            target_riga_id = (
                qp_int_strict(raw_riga, "target_riga_id", default=0)
                if raw_riga is not None else None
            )
            include_invisible = qp_bool_optional(qp.get("include_invisible"), "include_invisible", default=True)
            # Finestra (`limit`/`offset`, dal 2026-10-21 un dialetto solo),
            # ricerca e ordinamento (dal 2026-10-31) in una lettura: senza
            # `order_by` vale l'ordine di partenza delle note.
            p = parse_list_params(qp, default_order="")
            limit, offset = p["limit"], p["offset"]

            svc = service_factory()
            results, total = svc.list_note(
                target_id=target_id,
                target_riga_id=target_riga_id,
                include_invisible=include_invisible,
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=limit,
                offset=offset,
            )
            return success_response(envelope_da_offset(results, total, limit=limit, offset=offset))

        @extend_schema(request=create_request, responses={200: detail_response})
        # Scopo: Crea una nuova nota sul documento padre. Idempotency-Key obbligatoria.
        def post(self, request: Request, **path_kwargs: Any) -> JsonResponse:
            target_id = int(path_kwargs[_parent_param])
            auth_user_id = get_actor_user_id(request)

            def _handler(payload: dict[str, Any]) -> dict[str, Any]:
                svc = service_factory()
                return svc.crea_nota(
                    target_id=target_id,
                    payload=payload,
                    auth_user_id=auth_user_id,
                )

            return handle_post_json(
                request, handler=_handler,
                require_idempotency_key=True,
            )

    class NoteDetailView(DomainAPIView):
        """Get + patch + delete singola nota.

        URL pattern atteso:
            /<area>/<entita>/<parent_id>/note/<note_id>/
        """

        area_funzionale = _area
        if _model_perm is not None:
            model_permission = _model_perm

        @extend_schema(responses={200: detail_response})
        # Scopo: Restituisce il dettaglio di una nota (anti-tampering id<->target).
        def get(
            self, request: Request, *, note_id: int, **path_kwargs: Any,
        ) -> JsonResponse:
            del request
            target_id = int(path_kwargs[_parent_param])
            svc = service_factory()
            return success_response(svc.get_nota(note_id=note_id, target_id=target_id))

        @extend_schema(request=patch_request, responses={200: detail_response})
        # Scopo: Aggiorna parzialmente una nota. target_riga_id immutabile.
        def patch(
            self, request: Request, *, note_id: int, **path_kwargs: Any,
        ) -> JsonResponse:
            target_id = int(path_kwargs[_parent_param])
            auth_user_id = get_actor_user_id(request)
            svc = service_factory()
            updated = svc.aggiorna_nota(
                note_id=note_id,
                target_id=target_id,
                patch=corpo_oggetto(request),
                auth_user_id=auth_user_id,
            )
            return success_response(updated)

        @extend_schema(responses={200: inline_serializer(
            name=_make_serializer_name(target_tipo, "DeleteResponse"),
            fields={"data": serializers.DictField()},
        )})
        # Scopo: Elimina (hard delete) una nota. 404 se gia' inesistente.
        def delete(
            self, request: Request, *, note_id: int, **path_kwargs: Any,
        ) -> JsonResponse:
            del request
            target_id = int(path_kwargs[_parent_param])
            svc = service_factory()
            svc.elimina_nota(note_id=note_id, target_id=target_id)
            return success_response({"deleted": True})

    # Rinomina le classi per debugging/admin/openapi (drf-spectacular usa il
    # nome di classe come operationId quando non specificato).
    NoteListCreateView.__name__ = _make_view_name(target_tipo, "ListCreateView")
    NoteListCreateView.__qualname__ = NoteListCreateView.__name__
    NoteDetailView.__name__ = _make_view_name(target_tipo, "DetailView")
    NoteDetailView.__qualname__ = NoteDetailView.__name__

    return NoteListCreateView, NoteDetailView
