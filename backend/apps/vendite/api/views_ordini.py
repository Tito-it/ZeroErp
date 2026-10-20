# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.ordini (scheletro CRUD + conferma + push singolo).
#        Espone: lista DEF-8 + export, testata CRUD, righe + componenti BoM,
#        conferma (DRAFT->CONFERMATO) e push singolo a commessa. La transizione
#        di stato e' enforced dal trigger DB trgfn_ordini_guard_transizione_*;
#        il service traduce gli errori P0001 in ServiceError -> envelope uniforme.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id, get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool,
    qp_int_optional,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._list_filters_helpers import extract_doc_list_filters
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.api.riepilogo_iva_views import build_riepilogo_iva_view
from apps.vendite.services import ordini_service
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._componenti_schema import (
    COMPONENTE_PATCH_REQUEST,
    COMPONENTI_LIST_PARAMETERS,
    COMPONENTI_LIST_RESPONSE,
    PREVIEW_COMPONENTI_REQUEST,
    PREVIEW_COMPONENTI_RESPONSE,
    componenti_overrides_field,
)
from apps.vendite.api._date_consegna_schema import DATE_CONSEGNA_REQUEST, DATE_CONSEGNA_RESPONSE
from apps.vendite.api._schema_da_contratto import (
    CAMBIA_STATO_CON_CONFERMA_REQUEST,
    schema_da_contratto,
)

# Codice lista configurabile (catalogo ui.lista_definizione id=7). Usato
# dall'export per risolvere colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_ORDINI = "vendite.ordini"


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
_ORDINE_CREATE_REQUEST = schema_da_contratto(
    "VenditeOrdineCreateReq", ordini_service.CREATE_KEYS_ORDINE,
)
_ORDINE_UPDATE_REQUEST = schema_da_contratto(
    "VenditeOrdineUpdateReq", ordini_service.UPDATE_KEYS_ORDINE,
)
_ORDINE_RIGA_CREATE_REQUEST = schema_da_contratto(
    "VenditeOrdineRigaCreateReq", ordini_service.CREATE_KEYS_RIGA,
    obbligatorie=("articolo_id",),
    speciali={"componenti_overrides": componenti_overrides_field()},
)
_ORDINE_RIGA_UPDATE_REQUEST = schema_da_contratto(
    "VenditeOrdineRigaUpdateReq", ordini_service.UPDATE_KEYS_RIGA,
)
# La promessa di consegna di una riga: `null` la toglie.
_ORDINE_RIGA_DATA_CONSEGNA_CONFERMATA_REQUEST = inline_serializer(
    name="VenditeOrdineRigaDataConsegnaConfermataReq",
    fields={
        "data_consegna_confermata": serializers.DateField(
            allow_null=True, help_text="AAAA-MM-GG, oppure null per togliere la promessa.",
        ),
    },
)
_ORDINE_RIGA_DATA_CONSEGNA_CONFERMATA_RESPONSE = inline_serializer(
    name="VenditeOrdineRigaDataConsegnaConfermataResp",
    fields={
        "data": inline_serializer(
            name="VenditeOrdineRigaDataConsegnaConfermataData",
            fields={
                "ordine_id": serializers.IntegerField(),
                "riga_id": serializers.IntegerField(),
                "data_consegna_confermata": serializers.DateField(allow_null=True),
            },
        ),
    },
)
# Evasione parziale: la forma che legge `_parse_righe_evasione`.
_ORDINE_GENERA_DDT_REQUEST = inline_serializer(
    name="VenditeOrdineGeneraDdtReq",
    fields={
        "righe": serializers.ListField(
            required=False,
            help_text="Omessa: evade tutto il residuo dell'ordine.",
            child=inline_serializer(
                name="VenditeOrdineRigaDaEvadere",
                fields={
                    "ordine_riga_id": serializers.IntegerField(),
                    "qta_da_evadere": serializers.DecimalField(
                        max_digits=22, decimal_places=10,
                        required=False, allow_null=True,
                    ),
                },
            ),
        ),
    },
)
_ORDINE_RESPONSE = inline_serializer(
    name="VenditeOrdineResp", fields={"data": serializers.DictField()},
)
_ORDINE_LISTA_RESPONSE = inline_serializer(
    name="VenditeOrdineListaResp",
    fields={"data": serializers.ListField(child=serializers.DictField())},
)

# Scopo: normalizza le `righe` da evadere dal body di genera-ddt. Assente/null =
#        tutto il residuo dell'ordine (None). Lista vuota = errore esplicito: NON
#        deve degradare silenziosamente a "tutto" (un client che intende "nessuna
#        riga" otterrebbe l'evasione completa). Ogni voce =
#        {ordine_riga_id, qta_da_evadere} in unita' operativa (qta passata
#        intatta alla fn DB fn_genera_ddt_da_ordine).
def _parse_righe_evasione(
    payload: dict[str, Any],
) -> list[dict[str, Any]] | None:
    righe = payload.get("righe")
    if righe is None:
        return None
    ErrorManager.require(
        isinstance(righe, list) and len(righe) > 0,
        code="E_DDT_VALIDAZIONE",
        message="righe non valido: lista non vuota di {ordine_riga_id, "
                "qta_da_evadere}, oppure omettere il campo per evadere tutto "
                "il residuo.",
        detail=f"righe={righe!r}",
        function_name="apps.vendite.api.views_ordini._parse_righe_evasione",
    )
    assert isinstance(righe, list)
    out: list[dict[str, Any]] = []
    for r in righe:
        ErrorManager.require(
            isinstance(r, dict) and r.get("ordine_riga_id") is not None,
            code="E_DDT_VALIDAZIONE",
            message="Ogni riga richiede ordine_riga_id.",
            detail=f"riga={r!r}",
            function_name="apps.vendite.api.views_ordini._parse_righe_evasione",
        )
        assert isinstance(r, dict)
        out.append({
            "ordine_riga_id": int(r["ordine_riga_id"]),
            "qta_da_evadere": r.get("qta_da_evadere"),
        })
    return out


class ApiOrdiniList(DomainAPIView):
    """GET/POST /api/v1/vendite/ordini/ — lista paginata + create BOZZA."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")
    is_search_endpoint = True
    lista_codice = "vendite.ordini"

    @extend_schema(
        operation_id="vendite_ordini_list",
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="codice_interno stato (DRAFT | CONFERMATO | ...)"),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO; default anno-1."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo 'vendite.ordini' "
                                         "(numero | data | ragione_sociale_completa | "
                                         "ba_codice | utility_codice | totale_doc | "
                                         "fatturazione_trigger | stato_descrizione)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeOrdiniListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata ordini con filtri standard + scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        f = extract_doc_list_filters(qp, with_utility=True)
        results, total = ordini_service.list_ordini_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_ORDINE_CREATE_REQUEST,
        responses={200: _ORDINE_RESPONSE},
    )
    # Scopo: Crea nuovo ordine in stato BOZZA (DRAFT).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ordini_service.crea_ordine)


class ApiOrdiniExportView(DomainAPIView):
    """GET /api/v1/vendite/ordini/export/?formato=csv|xlsx (DEF-1).

    NB: parametro `formato` (italiano), NON `format` (magic param DRF —
    memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")
    is_search_endpoint = True
    lista_codice = "vendite.ordini"

    @extend_schema(
        operation_id="vendite_ordini_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Export CSV/XLSX della lista ordini. Filtri identici al list endpoint;
    #        fetcha fino a EXPORT_MAX_ROWS+1 per intercettare l'overflow.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = extract_doc_list_filters(qp, with_utility=True)
        results, total = ordini_service.list_ordini_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **f,
        )
        filtri_applicati = ordini_service.resolve_filtri_export_label(
            stato_codice=f["stato_codice"],
            billing_account_id=f["billing_account_id"],
            utility_id=f["utility_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_ORDINI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiOrdineDetail(DomainAPIView):
    """GET/PATCH/DELETE /api/v1/vendite/ordini/<ordine_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        responses={200: _ORDINE_RESPONSE},
    )
    # Scopo: Dettaglio testata ordine + capability.
    def get(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.get_ordine(int(ordine_id)))

    @extend_schema(
        request=_ORDINE_UPDATE_REQUEST,
        responses={200: _ORDINE_RESPONSE},
    )
    # Scopo: Aggiorna testata ordine (quali campi in quale stato lo decide il
    #        lock di testata del DB). PATCH usa request.data
    #        (api.md §handle_post_json vs request.data): DRF ha gia' parsato il
    #        body; handle_post_json rileggerebbe il raw consumato.
    def patch(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(
            ordini_service.aggiorna_ordine(int(ordine_id), dict(corpo_oggetto(request))),
        )

    @extend_schema(
        responses={200: _ORDINE_RESPONSE},
    )
    # Scopo: Hard-delete ordine (abbandono bozza, solo DRAFT).
    def delete(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.elimina_ordine(int(ordine_id)))


class ApiOrdinePerPratica(DomainAPIView):
    """`GET /api/v1/vendite/ordini/per-pratica/?pratica_id=<id>`: risolve
    l'ordine COLLEGATO a una pratica (agganciato da PostSmistamentoHandler).
    Alimenta gli step a valle del percorso (CONFERMA_ORDINE / INVIO_COMMESSA)
    che aprono l'OrdiniDrawer su quell'ordine. Ritorna `{"ordine_id": <id|null>}`."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="pratica_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={200: inline_serializer(
            name="OrdinePerPraticaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request) -> JsonResponse:
        pratica_id = qp_int_optional(request.query_params.get("pratica_id"), "pratica_id")
        ErrorManager.require(
            pratica_id is not None,
            code="E_PRATICA_ID_OBBLIGATORIO",
            message="pratica_id obbligatorio.",
        )
        assert pratica_id is not None
        return success_response(ordini_service.get_ordine_per_pratica(pratica_id))


class ApiOrdineConferma(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/conferma/ (DRAFT->CONFERMATO)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=None,
        responses={200: _ORDINE_RESPONSE},
    )
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        user = getattr(request.user, "username", None) or None
        return success_response(ordini_service.conferma(int(ordine_id), user=user))


class ApiOrdinePush(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/push/ — push singolo a commessa."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=None,
        responses={200: _ORDINE_RESPONSE},
    )
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        user = getattr(request.user, "username", None) or None
        return success_response(ordini_service.push_a_commessa(int(ordine_id), user=user))


class ApiOrdineCambiaStato(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/cambia-stato/ — transizione di
    stato data-driven (es. annulla). Body: `stato_codice` (= `target_state`
    dell'azione). L'ammissibilita' e' validata dal trigger guard DB."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=CAMBIA_STATO_CON_CONFERMA_REQUEST,
        responses={200: _ORDINE_RESPONSE},
    )
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.cambia_stato(
                int(ordine_id), payload.get("stato_codice"),
                legami_confermati=payload.get("legami_confermati"),
            ),
        )


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    list_call=lambda ordine_id: ordini_service.list_indirizzi(ordine_id),
    upsert_call=lambda ordine_id, payload: ordini_service.upsert_indirizzo(
        ordine_id, payload),
    delete_call=lambda ordine_id, indirizzo_id: ordini_service.delete_indirizzo(
        ordine_id, indirizzo_id),
    model_permission=("vendite", "ordine"),
)
ApiOrdineIndirizzi = _indirizzi_views.lista
ApiOrdineIndirizzoDetail = _indirizzi_views.detail


# View dal factory condiviso `build_riepilogo_iva_view` (estrazione
# regola-del-2 dei cloni preventivi/ordini/ddt). La closure legge il global
# di modulo a call-time: i patch dei test sul service restano validi.
ApiOrdineRiepilogoIva = build_riepilogo_iva_view(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    list_call=lambda ordine_id: ordini_service.list_riepilogo_iva(ordine_id),
    doc="""GET /api/v1/vendite/ordini/<id>/riepilogo-iva/

    Restituisce il riepilogo IVA dell'ordine: una riga per gruppo aliquota
    (natura/esigibilita/split sempre NULL) con imponibile e imposta aggregati
    e arrotondati a 2 decimali sull'aggregato per aliquota (regola fiscale:
    DPR 633/72 art. 21 + DM 24/12/93, identica ai preventivi). Lettura pura
    dalla view derivata `vendite.vw_ordini_riepilogo_iva_dettaglio`, nessun
    side-effect: i totali di testata sono mantenuti dal trigger su ordini_righe
    via fn_ricalcola_totali_ordine.

    Area `vendite` livello LETTURA sufficiente.
    """,
    model_permission=("vendite", "ordine"),
)


class ApiOrdineRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/ordini/<ordine_id>/righe/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        responses={200: _ORDINE_LISTA_RESPONSE},
    )
    # Scopo: Lista righe dell'ordine.
    def get(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.list_righe(int(ordine_id)))

    @extend_schema(
        request=_ORDINE_RIGA_CREATE_REQUEST,
        responses={200: _ORDINE_RESPONSE},
    )
    # Scopo: Aggiunge una riga (solo DRAFT). Pricing via BB condiviso.
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.gestisci_riga(
                int(ordine_id), payload, auth_user_id=auth_user_id,
            ),
        )


class ApiOrdineRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=_ORDINE_RIGA_UPDATE_REQUEST,
        responses={200: _ORDINE_RESPONSE},
    )
    def patch(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ordini_service.aggiorna_riga(
                int(ordine_id), int(riga_id), dict(corpo_oggetto(request)),
                auth_user_id=get_actor_user_id(request),
            ),
        )

    @extend_schema(
        responses={200: _ORDINE_RESPONSE},
    )
    def delete(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ordini_service.elimina_riga(int(ordine_id), int(riga_id)),
        )


class ApiOrdineRigaDataConsegnaConfermata(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/data-consegna-confermata/.

    La promessa di consegna di una riga, anche dopo la conferma dell'ordine
    (brief-db-testata-dopo-emissione, fase 1). In quali stati si cambia lo dice
    il DB (lock delle righe); l'azione si spegne prima con la capability
    `can_edit_data_consegna_confermata` del dettaglio.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=_ORDINE_RIGA_DATA_CONSEGNA_CONFERMATA_REQUEST,
        responses={200: _ORDINE_RIGA_DATA_CONSEGNA_CONFERMATA_RESPONSE},
    )
    def post(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.cambia_data_consegna_confermata(
                int(ordine_id), int(riga_id), payload,
            ),
        )


class ApiOrdineRigheDateConsegna(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/righe/date-consegna/.

    «Aggiorna date di consegna»: una data su piu' righe, richiesta o
    confermata, TUTTE o SOLO_VUOTE (brief-db-date-consegna-righe-in-blocco).
    Le righe gia' spedite si saltano; ogni altro rifiuto e' del DB.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(request=DATE_CONSEGNA_REQUEST, responses={200: DATE_CONSEGNA_RESPONSE})
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.aggiorna_date_consegna(
                int(ordine_id), payload,
            ),
        )


class ApiOrdineRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/righe/preview-componenti/.

    Preview read-only dei componenti BoM per il drawer riga (pre-save).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=PREVIEW_COMPONENTI_REQUEST,
        responses={200: PREVIEW_COMPONENTI_RESPONSE},
    )
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)

        # Ritorna la LISTA nuda dei componenti (contratto condiviso col
        # ComponentiDialog FE: `response.data.data` = array). NON avvolgere in
        # {"componenti": ...} — il dialog fa `for...of` sull'array (mirror
        # contratti/preventivi).
        def _handler(payload: dict[str, Any]) -> list[dict[str, Any]]:
            return ordini_service.preview_componenti_riga(
                int(ordine_id),
                articolo_id=str(payload.get("articolo_id")),
                uom_operativa_id=payload.get("uom_operativa_id"),
                quantita=payload.get("quantita"),
                auth_user_id=auth_user_id,
            )

        return handle_post_json(request, handler=_handler)


class ApiOrdineRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/componenti/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        parameters=COMPONENTI_LIST_PARAMETERS,
        responses={200: COMPONENTI_LIST_RESPONSE},
    )
    def get(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        solo_attivi = qp_bool(request.query_params.get("solo_attivi"), default=True)
        return success_response(
            ordini_service.list_componenti_riga(
                int(ordine_id), int(riga_id), solo_attivi=solo_attivi,
            ),
        )


class ApiOrdineRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /.../righe/<riga_id>/componenti/<componente_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(request=COMPONENTE_PATCH_REQUEST, responses={200: dict})
    # Scopo: Aggiorna un componente BoM (prezzo/attivo/meta, solo DRAFT).
    def patch(
        self, request: Request, ordine_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ordini_service.update_componente(
                int(ordine_id), int(riga_id), int(componente_id), dict(corpo_oggetto(request)),
                auth_user_id=get_actor_user_id(request),
            ),
        )

    @extend_schema(
        responses={200: _ORDINE_RESPONSE},
    )
    def delete(
        self, request: Request, ordine_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ordini_service.delete_componente(
                int(ordine_id), int(riga_id), int(componente_id),
            ),
        )


class ApiOrdineGeneraDdt(DomainAPIView):
    """`POST /api/v1/vendite/ordini/<ordine_id>/genera-ddt/` — evasione: genera
    un DDT (DRAFT) dall'ordine copiando lo snapshot righe/componenti + il
    fulfillment riga<->riga e proiettando lo stato ordine (CONFERMATO /
    PARZIALMENTE_EVASO / EVASO). L'endpoint vive nel dominio SORGENTE (ordine),
    la logica sta in `ddt_service` (stesso app vendite, come genera-ordine sta
    nei preventivi). Body opzionale `{righe: [{ordine_riga_id, qta_da_evadere}]}`
    (unita' operativa) per l'evasione parziale/selettiva; assente = tutto il
    residuo."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        request=_ORDINE_GENERA_DDT_REQUEST,
        responses={200: inline_serializer(
            name="OrdineGeneraDdtResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera un DDT da evasione dell'ordine. Delega a ddt_service (import
    #        locale per evitare cicli). Ritorna {ddt_id, numero, ordine_id}.
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        from apps.vendite.services import ddt_service

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ddt_service.crea_ddt_da_ordine(
                int(ordine_id), _parse_righe_evasione(payload),
            )
        return handle_post_json(request, handler=_handler)


# ── Righe: la lista configurabile `vendite.ordine_righe` ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto A). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⚠️ `GET …/righe/` resta la lettura COMPLETA: la lista e' su `…/righe/lista/`.
_OrdineRigheLista, _OrdineRigheListaExport = build_lista_figlia_views(
    schema_prefix="OrdineRighe",
    operation_id="vendite_ordini_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="ordine_id",
    model_permission=('vendite', 'ordine'),
    pagina_call=lambda documento_id, **kw: ordini_service.list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=OrdiniRepository.righe_colonne_ordinabili(),
    ordine_assente=OrdiniRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiOrdineRigheListaView(_OrdineRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.ordine_righe"


class ApiOrdineRigheListaExportView(_OrdineRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.ordine_righe"
