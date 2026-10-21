# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti — read-only v1: lista template,
#        dettaglio template, lista versioni, dettaglio versione.
#        CRUD admin (POST/PATCH/DELETE) atterra in PR successive
#        con `post_permission = documenti_template_manage`.
#        Tutte le view usano DomainAPIView con
#        `area_funzionale = documenti` e supportano i livelli
#        TUTTO/LETTURA standard.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import HttpResponse, HttpResponseNotModified, JsonResponse
from django.utils.http import parse_etags
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
)
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from rest_framework.parsers import FormParser, MultiPartParser

from apps.documenti.services.context_builders.registry import builder_registrati
from apps.documenti.services.template_admin_service import TemplateAdminService
from apps.documenti.services.template_asset_admin_service import (
    TemplateAssetAdminService,
)
from apps.documenti.services.template_service import TemplateService
from apps.documenti.services.template_versioni_admin_service import (
    TemplateVersioniAdminService,
)


class ApiTemplateList(DomainAPIView):
    """
    GET /api/v1/documenti/templates/ — lista paginata template.
    POST /api/v1/documenti/templates/ — crea testata template (Tranche E).
    """

    area_funzionale = "documenti"
    is_search_endpoint = True
    lista_codice = "documenti.template_documenti"
    # Azione processo richiesta dal POST (Decisione 75 + seed DB id azione=11+).
    post_permission = "documenti_template_manage"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="tipo_documento_output_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="sorgente_tipo_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="emittente_fiscale_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="standard", type=bool, location=OpenApiParameter.QUERY, required=False,
                description="Solo i modelli standard (true) o solo quelli delle aziende (false).",
            ),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="DocumentiTemplateListResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Ritorna lista paginata template visibili all'utente (scope EF).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        params = parse_list_params(qp, default_order="codice")
        # Colonne e soglia le decide il catalogo della lista (BB nel
        # repository): tabella di configurazione, niente 400 (Tid, 2026-09-24).

        result = TemplateService().list_templates(
            request.user,
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            tipo_documento_output_id=qp_int_optional(request.query_params.get("tipo_documento_output_id"), "tipo_documento_output_id"),
            sorgente_tipo_id=qp_int_optional(request.query_params.get("sorgente_tipo_id"), "sorgente_tipo_id"),
            emittente_fiscale_id=qp_int_optional(request.query_params.get("emittente_fiscale_id"), "emittente_fiscale_id"),
            standard=qp_bool_optional(request.query_params.get("standard"), "standard"),
            search=params["search"],
            order_by=params["order_by"],
            order_dir=params["order_dir"],
            limit=params["limit"],
            offset=params["offset"],
        )
        envelope = paginated_envelope(
            result["results"], result["total_count"], params["page"], params["limit"]
        )
        return success_response(envelope)

    @extend_schema(
        request=inline_serializer(
            name="DocumentiTemplateCreateRequest",
            fields={
                "tipo_documento_output_id": serializers.IntegerField(),
                "sorgente_tipo_id": serializers.IntegerField(),
                "emittente_fiscale_id": serializers.IntegerField(),
                "codice": serializers.CharField(),
                "codice_interno": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "context_builder_code": serializers.CharField(),
                "file_name_pattern": serializers.CharField(required=False, allow_null=True),
                "is_default": serializers.BooleanField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiTemplateCreateResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Crea testata template. Permesso azione `documenti_template_manage`.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            return TemplateAdminService().create_template(request.user, payload)
        return handle_post_json(request, handler=_handler)


class ApiContextBuilders(DomainAPIView):
    """
    GET /api/v1/documenti/context-builders/ — i builder di contesto
    registrati nel backend, con la forma dei dati che producono oggi.
    """

    area_funzionale = "documenti"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="DocumentiContextBuildersResponse",
                fields={
                    "data": inline_serializer(
                        name="DocumentiContextBuildersData",
                        fields={
                            "results": serializers.ListField(
                                child=inline_serializer(
                                    name="DocumentiContextBuilder",
                                    fields={
                                        "codice": serializers.CharField(),
                                        "versione_contesto": serializers.IntegerField(),
                                    },
                                )
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: La tendina «Context builder» del template legge il REGISTRO:
    #        fino al 2026-10-03 il frontend ne teneva una copia scritta a mano
    #        (con un flag «registrato» anch'esso a mano), da tenere allineata.
    #        Il registro e' di processo (`VenditeConfig.ready()`), non del DB.
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": builder_registrati()})


class ApiTemplateRisoluzione(DomainAPIView):
    """
    GET /api/v1/documenti/templates/risoluzione/ — con che cosa stampa ogni
    azienda del perimetro, per ogni documento.
    """

    area_funzionale = "documenti"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Solo questa azienda (il filtro della lista).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="DocumentiTemplateRisoluzioneResponse",
                fields={
                    "data": inline_serializer(
                        name="DocumentiTemplateRisoluzioneData",
                        fields={
                            "results": serializers.ListField(
                                child=inline_serializer(
                                    name="DocumentiTemplateRisoluzioneRiga",
                                    fields={
                                        "emittente_fiscale_id": serializers.IntegerField(),
                                        "emittente_fiscale_codice": serializers.CharField(),
                                        "emittente_ragione_sociale": serializers.CharField(allow_null=True),
                                        "tipo_documento_output_id": serializers.IntegerField(),
                                        "tipo_documento_output_descrizione": serializers.CharField(),
                                        "sorgente_tipo_id": serializers.IntegerField(),
                                        "sorgente_tipo_descrizione": serializers.CharField(),
                                        "esito": serializers.ChoiceField(choices=[
                                            "EMITTENTE", "STANDARD", "SENZA_PREDEFINITO", "NON_RISOLTO",
                                        ]),
                                        "template_documento_id": serializers.IntegerField(allow_null=True),
                                        "template_codice": serializers.CharField(allow_null=True),
                                        "template_versione_id": serializers.IntegerField(allow_null=True),
                                        "modelli_stampabili": serializers.IntegerField(),
                                    },
                                )
                            ),
                            "total_count": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Il pannello sopra la lista Modelli documento: per ogni azienda,
    #        quali documenti stampano con lo standard e quali si fermano perche'
    #        l'azienda ha modelli suoi ma nessun predefinito (brief-db-modelli-
    #        documento-standard §6). L'esito e' del DB (K-5), la stessa regola
    #        della stampa; qui il perimetro delle aziende.
    def get(self, request: Request) -> JsonResponse:
        result = TemplateService().list_risoluzione_emittenti(
            request.user,
            emittente_fiscale_id=qp_int_optional(
                request.query_params.get("emittente_fiscale_id"), "emittente_fiscale_id",
            ),
        )
        return success_response(result)


class ApiTemplateDetail(DomainAPIView):
    """
    GET /api/v1/documenti/templates/<id>/ — dettaglio template.
    PATCH /api/v1/documenti/templates/<id>/ — aggiorna testata (Tranche E).
    """

    area_funzionale = "documenti"
    # Azione processo richiesta dal PATCH (Decisione 75).
    patch_permission = "documenti_template_manage"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="DocumentiTemplateDetailResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Ritorna dettaglio template per id (404 se fuori scope EF).
    def get(self, request: Request, template_id: int) -> JsonResponse:
        result = TemplateService().get_template(request.user, int(template_id))
        return success_response(result)

    @extend_schema(
        request=inline_serializer(
            name="DocumentiTemplatePatchRequest",
            fields={
                "codice": serializers.CharField(required=False),
                "codice_interno": serializers.CharField(required=False),
                "descrizione": serializers.CharField(required=False),
                "context_builder_code": serializers.CharField(required=False),
                "file_name_pattern": serializers.CharField(required=False, allow_null=True),
                "is_default": serializers.BooleanField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiTemplatePatchResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Aggiorna testata template. Immutabili (output/sorgente/emittente)
    #        rifiutate dal service con E_DOCUMENTI_VALIDATION.
    def patch(self, request: Request, template_id: int) -> JsonResponse:
        result = TemplateAdminService().update_template(
            request.user, int(template_id), dict(corpo_oggetto(request))
        )
        return success_response(result)


class ApiTemplatePersonalizza(DomainAPIView):
    """POST /api/v1/documenti/templates/<id>/personalizza/ — copia di uno standard per un emittente."""

    area_funzionale = "documenti"
    post_permission = "documenti_template_manage"

    @extend_schema(
        request=inline_serializer(
            name="DocumentiTemplatePersonalizzaRequest",
            fields={
                "emittente_fiscale_id": serializers.IntegerField(),
                # Assente o null: decide il DB (D-6) — predefinita se l'azienda
                # non ne ha gia' una sua per il documento.
                "is_default": serializers.BooleanField(required=False, allow_null=True),
                # Assenti o null: quelli dello standard.
                "codice": serializers.CharField(required=False, allow_null=True),
                "codice_interno": serializers.CharField(required=False, allow_null=True),
                "descrizione": serializers.CharField(required=False, allow_null=True),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiTemplatePersonalizzaResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Crea il modello dell'emittente dallo standard `template_id`, con
    #        la prima versione in BOZZA che ne dichiara l'origine
    #        (brief-db-modelli-documento-standard §6, D-2). La copia la fa la
    #        funzione madre del DB (§10.3 K-6). Ritorna il modello nuovo.
    def post(self, request: Request, template_id: int) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            return TemplateAdminService().personalizza_template(
                request.user, int(template_id), payload,
            )
        return handle_post_json(request, handler=_handler)


class ApiTemplateVersioniList(DomainAPIView):
    """
    GET /api/v1/documenti/templates/<id>/versioni/ — versioni del template.
    POST /api/v1/documenti/templates/<id>/versioni/ — crea versione BOZZA (Tranche F).
    """

    area_funzionale = "documenti"
    post_permission = "documenti_template_manage"
    is_search_endpoint = True
    lista_codice = "documenti.template_versioni"
    # ⭐ Le versioni si aprono DENTRO il drawer del template, che e' di UN
    #    emittente: la lista a catalogo non e' certificata multi-emittente
    #    (`multi_emittente = f`), e senza questa riga il cancello chiederebbe al
    #    super admin su «Tutti» di scegliere l'emittente del template che ha
    #    gia' aperto.
    # ⭐ Il modello STANDARD non ha un emittente (brief-db-modelli-documento-
    #    standard §11.2 B-6): il frontend non manda il parametro, e il cancello
    #    decide come per una lista senza emittente suo (la distinta di
    #    `catalogo`): chi vede piu' aziende ne sceglie una. Le versioni non
    #    hanno RLS e lo standard si legge da tutti: non c'e' altro da fare qui.
    # ⚠️ Il cancello vale per OGNI metodo della view, anche il POST che crea
    #    una versione: il frontend manda il parametro in query su entrambi.
    # ⚠️ Non filtra: le righe le fissa il template nel path (e il service ne
    #    verifica la visibilita' con lo scope, 404 fuori perimetro).
    lista_emittente_param = "emittente_fiscale_id"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="stato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "L'emittente del template, gia' fissato dal drawer che apre "
                    "la lista: scioglie il cancello di perimetro, non filtra."
                ),
            ),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="DocumentiVersioniListResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Lista paginata delle versioni del template (proiezione leggera,
    #        no html), col contratto di lista standard: `limit`/`offset`,
    #        `order_by`/`order_dir` sulla whitelist del repository, `search`
    #        dal catalogo, envelope `paginated_envelope`.
    def get(self, request: Request, template_id: int) -> JsonResponse:
        stato = request.query_params.get("stato")
        # ⚠️ `default_order=""` e non "versione": senza `order_by` deve
        #    decidere il repository (`versione DESC`, la piu' recente in cima,
        #    come il preset). Una chiave qui arriverebbe senza verso e
        #    ripiegherebbe ASC — la lista aperta dalla versione 1.
        p = parse_list_params(request.query_params, default_order="")
        result = TemplateService().list_versioni(
            request.user,
            int(template_id),
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            stato=stato.strip().upper() if stato else None,
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(
            result["results"], result["total_count"], p["page"], p["limit"],
        ))

    @extend_schema(
        request=inline_serializer(
            name="DocumentiVersioneCreateRequest",
            fields={
                "titolo": serializers.CharField(),
                "html_template": serializers.CharField(),
                "render_engine_id": serializers.IntegerField(),
                # La forma dei dati che la versione legge: obbligatoria,
                # senza default (vedi il `versione_contesto_builder` del
                # dettaglio template per la forma che il builder produce).
                "versione_contesto": serializers.IntegerField(min_value=1),
                "formato_template": serializers.CharField(required=False),
                "css_template": serializers.CharField(required=False, allow_null=True),
                "markdown_template": serializers.CharField(required=False, allow_null=True),
                "page_format": serializers.CharField(required=False),
                "page_orientation": serializers.CharField(required=False),
                "margin_top_mm": serializers.FloatField(required=False),
                "margin_right_mm": serializers.FloatField(required=False),
                "margin_bottom_mm": serializers.FloatField(required=False),
                "margin_left_mm": serializers.FloatField(required=False),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False),
                "context_schema": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiVersioneCreateResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Crea versione BOZZA. Numero versione calcolato come MAX+1.
    def post(self, request: Request, template_id: int) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            return TemplateVersioniAdminService().create_versione(
                request.user, int(template_id), payload
            )
        return handle_post_json(request, handler=_handler)


class ApiTemplateVersioneDetail(DomainAPIView):
    """
    GET /api/v1/documenti/templates/<id>/versioni/<vid>/ — dettaglio versione.
    PATCH /api/v1/documenti/templates/<id>/versioni/<vid>/ — aggiorna BOZZA (Tranche F).
    DELETE /api/v1/documenti/templates/<id>/versioni/<vid>/ — elimina BOZZA (Tranche F).
    """

    area_funzionale = "documenti"
    patch_permission = "documenti_template_manage"
    delete_permission = "documenti_template_manage"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="DocumentiVersioneDetailResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Ritorna dettaglio versione (incluso payload HTML/CSS/markdown).
    def get(
        self, request: Request, template_id: int, versione_id: int
    ) -> JsonResponse:
        result = TemplateService().get_versione(
            request.user, int(template_id), int(versione_id)
        )
        return success_response(result)

    @extend_schema(
        request=inline_serializer(
            name="DocumentiVersionePatchRequest",
            fields={
                "titolo": serializers.CharField(required=False),
                "html_template": serializers.CharField(required=False),
                "css_template": serializers.CharField(required=False, allow_null=True),
                "markdown_template": serializers.CharField(required=False, allow_null=True),
                "render_engine_id": serializers.IntegerField(required=False),
                "versione_contesto": serializers.IntegerField(required=False, min_value=1),
                "formato_template": serializers.CharField(required=False),
                "page_format": serializers.CharField(required=False),
                "page_orientation": serializers.CharField(required=False),
                "margin_top_mm": serializers.FloatField(required=False),
                "margin_right_mm": serializers.FloatField(required=False),
                "margin_bottom_mm": serializers.FloatField(required=False),
                "margin_left_mm": serializers.FloatField(required=False),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False),
                "context_schema": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiVersionePatchResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Aggiorna versione BOZZA. Trigger DB A1 blocca update su PUBBLICATA.
    def patch(
        self, request: Request, template_id: int, versione_id: int
    ) -> JsonResponse:
        result = TemplateVersioniAdminService().update_versione(
            request.user,
            int(template_id),
            int(versione_id),
            dict(corpo_oggetto(request)),
        )
        return success_response(result)

    @extend_schema(
        responses={
            204: inline_serializer(
                name="DocumentiVersioneDeleteResponse",
                fields={"data": serializers.DictField()},
            )
        },
    )
    # Scopo: Elimina versione BOZZA. Trigger DB A2 blocca non-BOZZA o gia' usate.
    def delete(
        self, request: Request, template_id: int, versione_id: int
    ) -> JsonResponse:
        TemplateVersioniAdminService().delete_versione(
            request.user, int(template_id), int(versione_id)
        )
        return success_response({"deleted": True, "versione_id": int(versione_id)})


class ApiTemplateVersioneClona(DomainAPIView):
    """POST /api/v1/documenti/templates/<id>/versioni/<vid>/clona/ — clone (Tranche F)."""

    area_funzionale = "documenti"
    post_permission = "documenti_template_manage"

    @extend_schema(
        request=inline_serializer(
            name="DocumentiVersioneClonaRequest",
            fields={
                "titolo": serializers.CharField(required=False),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiVersioneClonaResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Clona una versione esistente (qualunque stato) in nuova BOZZA.
    def post(
        self, request: Request, template_id: int, versione_id: int
    ) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            return TemplateVersioniAdminService().clone_versione(
                request.user, int(template_id), int(versione_id), payload
            )
        return handle_post_json(request, handler=_handler)


class ApiTemplateVersionePubblica(DomainAPIView):
    """POST /api/v1/documenti/templates/<id>/versioni/<vid>/pubblica/ — publish (Tranche F)."""

    area_funzionale = "documenti"
    post_permission = "documenti_template_manage"

    @extend_schema(
        request=inline_serializer(
            name="DocumentiVersionePubblicaRequest",
            fields={
                "valido_dal": serializers.DateField(),
                "valido_al": serializers.DateField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiVersionePubblicaResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Transizione atomica BOZZA -> PUBBLICATA. valido_dal obbligatorio.
    def post(
        self, request: Request, template_id: int, versione_id: int
    ) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            return TemplateVersioniAdminService().pubblica_versione(
                request.user, int(template_id), int(versione_id), payload
            )
        return handle_post_json(request, handler=_handler)


# =================================================================
# Asset documentali (Tranche G)
# =================================================================


class ApiAssetList(DomainAPIView):
    """
    GET /api/v1/documenti/asset/ — lista paginata asset.
    POST /api/v1/documenti/asset/ — upload nuovo asset (multipart) (Tranche G).

    L'upload usa multipart/form-data: campo `file` (binario) + campi
    `metadati` come JSON string nella stessa request, oppure i singoli
    campi anagrafici (codice, codice_interno, descrizione, asset_tipo_id,
    emittente_fiscale_id, ...) come parti form. La view accetta entrambi.
    """

    area_funzionale = "documenti"
    is_search_endpoint = True
    lista_codice = "documenti.template_asset"
    post_permission = "documenti_asset_manage"
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="asset_tipo_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="emittente_fiscale_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="utilizzabili", type=bool, location=OpenApiParameter.QUERY, required=False,
                description=(
                    "true = solo gli asset che il render accetta oggi (attivi e "
                    "validi oggi), la stessa regola di `asset:<codice_interno>`; "
                    "false = solo gli altri; assente = tutti."
                ),
            ),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="DocumentiAssetListResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Lista paginata asset visibili nello scope EF dell'utente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        params = parse_list_params(qp, default_order="codice")
        # Colonne e soglia le decide il catalogo della lista (BB nel
        # repository): tabella di configurazione, niente 400 (Tid, 2026-09-24).

        result = TemplateService().list_asset(
            request.user,
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            asset_tipo_id=qp_int_optional(request.query_params.get("asset_tipo_id"), "asset_tipo_id"),
            emittente_fiscale_id=qp_int_optional(request.query_params.get("emittente_fiscale_id"), "emittente_fiscale_id"),
            utilizzabili=qp_bool_optional(request.query_params.get("utilizzabili"), "utilizzabili"),
            search=params["search"],
            order_by=params["order_by"],
            order_dir=params["order_dir"],
            limit=params["limit"],
            offset=params["offset"],
        )
        envelope = paginated_envelope(
            result["results"], result["total_count"], params["page"], params["limit"]
        )
        return success_response(envelope)

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                name="DocumentiAssetUploadRequest",
                fields={
                    "file": serializers.FileField(),
                    "codice": serializers.CharField(),
                    "codice_interno": serializers.CharField(),
                    "descrizione": serializers.CharField(),
                    "asset_tipo_id": serializers.IntegerField(),
                    "emittente_fiscale_id": serializers.IntegerField(),
                    "valido_dal": serializers.DateField(required=False),
                    "valido_al": serializers.DateField(required=False),
                    "attivo": serializers.BooleanField(required=False),
                },
            )
        },
        responses={
            200: inline_serializer(
                name="DocumentiAssetUploadResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Upload nuovo asset (file binario + metadati anagrafici).
    def post(self, request: Request) -> JsonResponse:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message="Campo 'file' mancante nel multipart/form-data.",
            )
        metadati = self._extract_metadati(request)
        result = TemplateAssetAdminService().upload_asset(
            request.user,
            metadati=metadati,
            file_bytes=uploaded.read(),
            client_mime_type=uploaded.content_type or "",
            client_file_name=uploaded.name or "",
        )
        return success_response(result)

    # Scopo: Estrae i metadati dal form multipart, normalizzando i tipi
    #        primitivi. Multipart di default consegna ogni campo come
    #        stringa: convertiamo qui per allinearci al contratto JSON
    #        del service (int, bool, ecc.). Conversioni "permissive":
    #        validazione fine demandata al PayloadValidator del service.
    def _extract_metadati(self, request: Request) -> dict:
        raw = dict(corpo_oggetto(request))
        metadati: dict = {}
        # Form multipart: i valori arrivano come liste in alcuni framework;
        # normalizziamo a singolo valore.
        for key, value in raw.items():
            if key == "file":
                continue
            if isinstance(value, list):
                value = value[0] if value else None
            metadati[key] = value
        # Conversioni esplicite (best-effort: il service rivalida).
        for int_key in ("asset_tipo_id", "emittente_fiscale_id"):
            if int_key in metadati and metadati[int_key] is not None:
                try:
                    metadati[int_key] = int(metadati[int_key])
                except (TypeError, ValueError):
                    pass  # lascia stringa: il service rifiutera' con messaggio parlante
        # ⭐ Il flag del multipart dal BB unico dei booleani del trasporto
        #    (`qp_bool_optional`, decisione A6 di Tid, brief-be-verifica-
        #    documentazione-api): solo `true`/`false`, ogni altro valore e' un
        #    400 col campo. ⛔ Fino al 2026-10-21 un valore fuori vocabolario
        #    valeva `false` in silenzio (e anche `""`: l'asset nasceva spento).
        #    Vuoto = assente: decide il default del service.
        if "attivo" in metadati and isinstance(metadati["attivo"], str):
            attivo = qp_bool_optional(metadati["attivo"], "attivo")
            if attivo is None:
                del metadati["attivo"]
            else:
                metadati["attivo"] = attivo
        return metadati


class ApiAssetDetail(DomainAPIView):
    """
    GET /api/v1/documenti/asset/<id>/ — dettaglio asset.
    PATCH /api/v1/documenti/asset/<id>/ — aggiorna metadati asset (Tranche G).

    No DELETE: trigger DB A3 blocca cancellazione fisica. Per "rimuovere"
    un asset, PATCH `attivo=false` o `valido_al=<data passata>`.
    """

    area_funzionale = "documenti"
    patch_permission = "documenti_asset_manage"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="DocumentiAssetDetailResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Ritorna dettaglio asset (404 se fuori scope EF).
    def get(self, request: Request, asset_id: int) -> JsonResponse:
        result = TemplateService().get_asset(request.user, int(asset_id))
        return success_response(result)

    @extend_schema(
        request=inline_serializer(
            name="DocumentiAssetPatchRequest",
            fields={
                "descrizione": serializers.CharField(required=False),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="DocumentiAssetPatchResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Aggiorna metadati asset (no sostituzione file). Trigger DB A4
    #        blocca comunque modifiche a storage_key/sha256/file_size/mime/file_name.
    def patch(self, request: Request, asset_id: int) -> JsonResponse:
        result = TemplateAssetAdminService().update_asset_metadati(
            request.user, int(asset_id), dict(corpo_oggetto(request))
        )
        return success_response(result)


class ApiAssetFileDownload(DomainAPIView):
    """
    GET /api/v1/documenti/asset/<id>/file/ — download binario asset.
    """

    area_funzionale = "documenti"

    @extend_schema(
        responses={200: bytes},
    )
    # Scopo: Restituisce il file originale dell'asset come attachment.
    def get(self, request: Request, asset_id: int) -> HttpResponse:
        result = TemplateService().download_asset(request.user, int(asset_id))
        response = HttpResponse(
            result["file_bytes"],
            content_type=result["mime_type"],
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{result["file_name"]}"'
        )
        response["Content-Length"] = str(result["size_bytes"])
        return response


class ApiAssetMiniatura(DomainAPIView):
    """
    GET /api/v1/documenti/asset/<id>/miniatura/ — miniatura di un asset
    immagine (PNG di lato al massimo `LATO_MINIATURA`; SVG cosi' com'e').
    """

    area_funzionale = "documenti"

    @extend_schema(
        responses={200: bytes, 304: None},
    )
    # Scopo: Restituisce la miniatura inline, con `ETag` e
    #        `Cache-Control: private, no-cache`: il browser la riusa, ma la
    #        rivalida a ogni richiesta (304 se l'asset e' lo stesso), cosi'
    #        lo scope si ricontrolla sempre e un altro utente dello stesso
    #        browser non la riceve dalla cache.
    def get(self, request: Request, asset_id: int) -> HttpResponse:
        result = TemplateService().miniatura_asset(
            request.user, int(asset_id),
            etag_noti=parse_etags(request.headers.get("If-None-Match", "")),
        )
        response: HttpResponse
        if result["file_bytes"] is None:
            response = HttpResponseNotModified()
        else:
            response = HttpResponse(
                result["file_bytes"], content_type=result["mime_type"],
            )
        response["ETag"] = result["etag"]
        response["Cache-Control"] = "private, no-cache"
        return response
