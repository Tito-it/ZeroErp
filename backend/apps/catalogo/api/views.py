# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view catalogo per lista, dettaglio e lookup articoli/UoM.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from uuid import UUID

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.catalogo.services.catalogo_service import (
    fn_create_articolo,
    fn_create_componente,
    fn_create_uom_tipo,
    fn_create_uom_operativa,
    fn_create_unita_misura,
    fn_delete_uom_operativa,
    fn_disattiva_articolo,
    fn_disattiva_unita_misura,
    fn_get_articolo_form_defaults,
    fn_get_uom_tipo,
    fn_riattiva_articolo,
    fn_get_articolo,
    fn_get_unita_misura,
    fn_list_componenti,
    fn_list_componenti_pagina,
    fn_list_articoli,
    fn_list_uom_operative,
    fn_list_uom_operative_pagina,
    fn_list_uom_tipi,
    fn_list_unita_misura,
    fn_lookup_articoli,
    fn_lookup_articoli_ammessi,
    fn_update_articolo,
    fn_update_uom_tipo,
    fn_update_uom_operativa,
    fn_update_unita_misura,
    fn_list_conversioni,
    fn_get_conversione,
    fn_create_conversione,
    fn_update_conversione,
    fn_get_chiusura_componente,
    fn_chiudi_componente,
)
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_uuid,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.search_validators import require_min_search_length
from apps.core.api.success_responses import success_response
from apps.core.api.openapi_params import param_ricerca_full
from apps.catalogo.db.catalogo_bom_repository import COMPONENTI_SORT_COLUMNS
from apps.ui.api.lista_figlia_views import build_lista_figlia_views


# Scopo: Definisce in un solo punto i campi write articolo per schema API.
# for_create=True abilita codice e uom_id come obbligatori (NOT NULL DDL).
# for_create=False (PATCH) li esclude entrambi: sono immutabili dopo create
# (lock di colonna a DB su catalogo.articoli, `E_CODICE_NON_MODIFICABILE`).
def _articolo_write_fields(*, for_create: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "descrizione": serializers.CharField(required=False),
        "descrizione_breve": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "tipo_voce_id": serializers.IntegerField(required=False, allow_null=True),
        "gruppo_voce_id": serializers.IntegerField(required=False, allow_null=True),
        "spesa_id": serializers.IntegerField(required=False, allow_null=True),
        "iva_id": serializers.IntegerField(required=False, allow_null=True),
        "conto_contabile_vendita_id": serializers.IntegerField(required=False, allow_null=True),
        "conto_contabile_acquisto_id": serializers.IntegerField(required=False, allow_null=True),
        "is_composito": serializers.BooleanField(required=False),
        "is_solo_componente": serializers.BooleanField(required=False),
        "requires_serial": serializers.BooleanField(required=False),
        "requires_lotto": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }
    if for_create:
        fields = {
            "codice": serializers.CharField(required=True),
            "uom_id": serializers.IntegerField(required=True),
            **fields,
        }
    return fields


# Scopo: Definisce i campi write UoM operativa per schema API.
def _uom_write_fields(*, include_uom_id: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "factor_to_base": serializers.DecimalField(required=False, max_digits=18, decimal_places=6),
        "is_sell_uom": serializers.BooleanField(required=False),
        "is_purchase_uom": serializers.BooleanField(required=False),
        "is_logistic_uom": serializers.BooleanField(required=False),
        "qty_step": serializers.DecimalField(required=False, max_digits=18, decimal_places=6, allow_null=True),
        "max_decimals": serializers.IntegerField(required=False, allow_null=True),
        "forbid_fraction": serializers.BooleanField(required=False),
        "gtin": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "valido_dal": serializers.DateField(required=False, allow_null=True),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }
    if include_uom_id:
        fields = {"uom_id": serializers.IntegerField(required=True), **fields}
    return fields


# Scopo: Definisce i campi write componente BoM per schema API.
# ⚠️ Solo la CREATE: dal 2026-11-10 un legame non si aggiorna (la PATCH e'
#    ritirata, la fine passa dal verbo `…/chiudi/`).
def _componente_write_fields() -> dict[str, serializers.Field]:
    return {
        "componente_id": serializers.UUIDField(required=True),
        "coeff_qta": serializers.DecimalField(required=False, max_digits=18, decimal_places=6),
        "obbligatorio": serializers.BooleanField(required=False),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }


_ARTICOLO_CREATE_REQUEST = inline_serializer(
    name="CatalogoArticoloCreateRequest",
    fields=_articolo_write_fields(for_create=True),
)

_ARTICOLO_PATCH_REQUEST = inline_serializer(
    name="CatalogoArticoloPatchRequest",
    fields={
        **_articolo_write_fields(for_create=False),
        # R-BE-1: la correzione di struttura nello stesso PATCH, in una
        # transazione. La giudica il verbo del DB (SUPER_ADMIN, colonne ammesse).
        "correzione_struttura": serializers.DictField(
            required=False,
            help_text=(
                "Solo SUPER_ADMIN: {colonna: valore} delle colonne strutturali da correggere "
                "(quelle di `struttura_correggibile`), anche su un articolo usato. Si applica "
                "prima dell'aggiornamento, nella stessa transazione."
            ),
        ),
    },
)

_UOM_CREATE_REQUEST = inline_serializer(
    name="CatalogoUomOperativaCreateRequest",
    fields=_uom_write_fields(include_uom_id=True),
)

_UOM_PATCH_REQUEST = inline_serializer(
    name="CatalogoUomOperativaPatchRequest",
    fields=_uom_write_fields(include_uom_id=False),
)

_COMPONENTE_CREATE_REQUEST = inline_serializer(
    name="CatalogoComponenteCreateRequest",
    fields=_componente_write_fields(),
)

class ApiArticoliList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")
    is_search_endpoint = True
    lista_codice = "catalogo.articoli"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="is_composito", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="tipo_voce_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="gruppo_voce_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="listino_tipologia_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="data_da", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoArticoliListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce via GET la lista paginata articoli con filtri e ricerca.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="descrizione")
        # Colonne e soglia le decide il catalogo della lista (BB nel
        # repository). ⛔ Nessun 400 sotto soglia (brief-db-be-fe-ricerca-
        # soglia-per-lista §6 a, Tid 2026-09-26).

        results, total = fn_list_articoli(
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            is_composito=qp_bool_optional(request.query_params.get("is_composito"), "is_composito"),
            tipo_voce_id=qp_int_optional(request.query_params.get("tipo_voce_id"), "tipo_voce_id"),
            gruppo_voce_id=qp_int_optional(request.query_params.get("gruppo_voce_id"), "gruppo_voce_id"),
            listino_tipologia_id=qp_int_optional(request.query_params.get("listino_tipologia_id"), "listino_tipologia_id"),
            search=p["search"],
            data_da=qp_iso_date_optional(request.query_params.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(request.query_params.get("data_a"), "data_a"),
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_ARTICOLO_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea un nuovo articolo e restituisce il dettaglio completo.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_articolo)


class ApiArticoloDetail(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloDetailResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il dettaglio singolo di un articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_get_articolo(articolo_id))

    @extend_schema(
        request=_ARTICOLO_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna un articolo sui soli campi presenti, con codice immutabile.
    def patch(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return success_response(fn_update_articolo(articolo_id, corpo_oggetto(request)))


class ApiArticoloDisattiva(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        request=inline_serializer(name="CatalogoArticoloDisattivaRequest", fields={}),
        responses={
            200: inline_serializer(
                name="CatalogoArticoloDisattivaResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Disattiva soft un articolo e restituisce il dettaglio aggiornato.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda _payload: fn_disattiva_articolo(articolo_id))


class ApiArticoliFormDefaults(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoliFormDefaultsResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce i defaults per il form di creazione articolo (Fase 8 — A5).
    #        Centralizza il consumo dei parametri (oggi: DEFAULT_IVA, che
    #        porta il `codice_interno` dell'aliquota e non il suo id) e
    #        ritorna al FE valori gia' risolti.
    def get(self, request: Request) -> JsonResponse:
        from apps.core.api.views_parameters import get_user_context
        from apps.core.services.parameter_service import ParameterService

        ctx = get_user_context(request, ParameterService())
        return success_response(fn_get_articolo_form_defaults(**ctx))


class ApiArticoloRiattiva(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        request=inline_serializer(name="CatalogoArticoloRiattivaRequest", fields={}),
        responses={
            200: inline_serializer(
                name="CatalogoArticoloRiattivaResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Riattiva un articolo (Fase 7) e restituisce il dettaglio aggiornato.
    #        Idempotente su articolo gia' attivo (no-op DB, ritorna dettaglio).
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda _payload: fn_riattiva_articolo(articolo_id))


# I parametri di pagina delle liste figlie dell'articolo (2026-10-31): le UoM
# (`catalogo.articolo_uom`) e le note (`catalogo.note`, come `vendite.note`).
_PARAMETRI_LISTA_FIGLIA = [
    param_ricerca_full(),
    OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
]


# Scopo: dai parametri di lista quelli della pagina.
def _lista_pagina_da(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p[k] for k in ("search", "order_by", "order_dir", "limit", "offset")}


class ApiArticoloUomList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")
    is_search_endpoint = True
    # ⚠️ Nessun `lista_codice`: `catalogo.articolo_uom` e' globale (come le
    #    note dell'articolo, vedi sopra).

    @extend_schema(
        parameters=_PARAMETRI_LISTA_FIGLIA,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: La pagina delle UoM operative dell'articolo (lista
    #        `catalogo.articolo_uom`, dal 2026-10-31), coi campi non
    #        modificabili del form di riga accanto alla busta.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="")
        results, total, non_editable = fn_list_uom_operative_pagina(articolo_id, **_lista_pagina_da(p))
        busta = paginated_envelope(results, total, p["page"], p["limit"])
        busta["non_editable_fields"] = non_editable
        return success_response(busta)

    @extend_schema(
        request=_UOM_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiunge una UoM operativa all'articolo.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_uom_operativa(articolo_id, payload))


class ApiArticoloUomLookup(DomainAPIView):
    # Lookup cross-dominio sulle UoM operative di un articolo: usato come
    # autocomplete dai drawer riga di vendite (preventivi, contratti, listini,
    # promo articoli) che non possono richiedere LETTURA su catalogo solo per
    # popolare un combo. Stesso pattern di ApiArticoliLookup: JWT + scope dati
    # gia' implicito (le UoM operative sono fisse per articolo, niente filtro
    # per utente). I CRUD admin catalogo restano su ApiArticoloUomList.
    skip_area_check = True

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomLookupResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce le UoM operative di un articolo (lookup cross-dominio).
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_list_uom_operative(articolo_id))


class ApiArticoloUomDetail(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        request=_UOM_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna una UoM operativa dell'articolo.
    def patch(self, request: Request, articolo_id: UUID, uom_op_id: int) -> JsonResponse:
        return success_response(fn_update_uom_operativa(articolo_id, uom_op_id, corpo_oggetto(request)))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina una UoM operativa dell'articolo.
    def delete(self, request: Request, articolo_id: UUID, uom_op_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_uom_operativa(articolo_id, uom_op_id))


class ApiArticoloComponentiList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponentiListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Lista i componenti BoM dell'articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_list_componenti(articolo_id))

    @extend_schema(
        request=_COMPONENTE_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiunge un componente BoM all'articolo.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_componente(articolo_id, payload))


# ── La distinta come lista configurabile `catalogo.articolo_componenti` ──
# (brief-db-liste-righe-documento, lotto C, 2026-09-28). Pagina ed export dal
# factory condiviso `build_lista_figlia_views` (regola del 2 fra domini: e'
# la stessa coppia delle righe dei documenti di vendita).
# ⭐ SU UN PERCORSO SUO, `…/componenti/lista/`, e non su `…/componenti/`: il
#    cancello di perimetro (`lista_codice`) scatta su ogni metodo della view
#    che lo dichiara, e `…/componenti/` serve anche il POST di creazione.
#    `GET …/componenti/` resta la lettura completa.
# ⚠️ Nessun `lista_emittente_param`: la distinta non ha un emittente suo (e'
#    «per azienda», D-8.2, come `catalogo.articoli`), quindi chi vede piu'
#    emittenti lo sceglie come per la lista degli articoli.


# Scopo: il filtro proprio della distinta, «in vigore al» (None: tutte le
#        versioni). Lo leggono pagina ed export dalla stessa funzione.
def _filtri_componenti(qp) -> dict[str, Any]:
    return {"valido_al": qp_iso_date_optional(qp.get("valido_al"), "valido_al")}


_ComponentiLista, _ComponentiListaExport = build_lista_figlia_views(
    schema_prefix="CatalogoArticoloComponenti",
    operation_id="catalogo_articoli_componenti_lista",
    area_funzionale="catalogo",
    url_kwarg="articolo_id",
    model_permission=("catalogo", "articolo"),
    pagina_call=lambda articolo_id, **kw: fn_list_componenti_pagina(articolo_id, **kw),
    colonne_ordinabili=COMPONENTI_SORT_COLUMNS,
    ordine_assente="valido_dal DESC.",
    filtri=_filtri_componenti,
    parametri_filtri=[
        OpenApiParameter(
            name="valido_al", type=str, required=False,
            description=(
                "Data (YYYY-MM-DD): solo le righe in vigore a quella data o dopo "
                "(senza fine, o con fine da quel giorno). Assente: tutte le versioni."
            ),
        ),
    ],
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiArticoloComponentiLista(_ComponentiLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "catalogo.articolo_componenti"


class ApiArticoloComponentiListaExport(_ComponentiListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "catalogo.articolo_componenti"


# ⛔ Un legame NON si aggiorna e NON si cancella (2026-11-10): la rotta
#    `…/componenti/<id>/` e' ritirata. La distinta e' una storia (trigger
#    d'immutabilita', BE11 di brief-db-revisione-catalogo), e l'unica cosa che di
#    un legame cambia, la fine, passa dal verbo qui sotto: la PATCH su
#    `valido_al` era una seconda strada per la stessa scrittura, e su un legame
#    con prezzi bundle riceveva un avviso che non sapeva confermare.


# ⭐ La chiusura di un legame coi suoi prezzi bundle (BE19 di
#    brief-db-revisione-catalogo, giro 3): il lettore della finestra di
#    conferma e il verbo, l'UNICA strada per chiudere un legame: la conferma
#    ripete la STESSA chiamata con la dichiarazione (`useForzaturaConfermata`).
class ApiArticoloComponenteChiusura(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="valido_al", type=str, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteChiusuraResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: I prezzi bundle che la chiusura alla data `valido_al` tocca, e il
    #        loro numero da dichiarare nella conferma.
    def get(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        return success_response(
            fn_get_chiusura_componente(articolo_id, comp_id, dict(request.query_params.items())),
        )


class ApiArticoloComponenteChiudi(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "articolo")

    @extend_schema(
        request=inline_serializer(
            name="CatalogoArticoloComponenteChiudiRequest",
            fields={
                "valido_al": serializers.DateField(),
                "prezzi_confermati": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteChiudiResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Chiude il legame alla data, coi suoi prezzi bundle, dal verbo del DB.
    def post(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        return handle_post_json(
            request, handler=lambda payload: fn_chiudi_componente(articolo_id, comp_id, payload),
        )


# I filtri della ricerca LIBERA (consultazioni): con `documento` non si
# accettano, la regola della riga la dice il DB.
_FILTRI_LIBERI_LOOKUP = ("attivo", "is_composito", "gestito_a_magazzino", "solo_oneri")

# I filtri RITIRATI il 2026-10-14 (brief-db-articoli-ammessi-per-documento §9.6):
# erano la copia dei guard per le righe di documento. Un chiamante che li manda
# ancora crede di filtrare e riceve tutto: un 400 che li nomina, non il silenzio
# (uno smoke e' rimasto verde cosi', senza provare niente).
_FILTRI_RITIRATI_LOOKUP = ("is_solo_componente", "escludi_destinazione")


class ApiArticoliLookup(DomainAPIView):
    # Lookup cross-dominio per autocomplete: preventivi/contratti/listini lo
    # usano dall'area vendite, righe ordine/fattura dall'area acquisti, ecc.
    # Coerente col pattern degli altri lookup di selezione (vedi core/api/
    # views_lookup.py): JWT obbligatorio + throttling search bastano. L'area
    # `catalogo` resta protetta sui CRUD veri (list dettagliata, create/update).
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="documento",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Picker di una RIGA di documento: il codice di config.tipi_entita "
                    "(PREVENTIVO, ORDINE_VENDITA, DDT_VENDITA, OFFERTA_COMMERCIALE, "
                    "CONTRATTO, LISTINO_VERSIONE, ARTICOLO per la distinta, "
                    "PROMO_ARTICOLO). Con questo parametro gli articoli li sceglie "
                    "catalogo.fn_articoli_ammessi, la stessa check dei guard: ogni "
                    "riga porta `motivo` (null = ammesso), prima gli ammessi. Non si "
                    "combina coi filtri liberi (attivo, is_composito, "
                    "gestito_a_magazzino, solo_oneri)."
                ),
            ),
            OpenApiParameter(
                name="documento_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Con `documento`: l'id della testata (o della versione di listino).",
            ),
            OpenApiParameter(
                name="tipo_eccezione",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Con `documento` OFFERTA_COMMERCIALE o CONTRATTO: AGGIUNTA, OVERRIDE o ESCLUSIONE.",
            ),
            OpenApiParameter(
                name="articolo_padre_id",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Con `documento` ARTICOLO: il padre della distinta.",
            ),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="is_composito", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="gestito_a_magazzino",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Solo articoli gestiti a magazzino (o solo quelli che non "
                    "lo sono, se false). Assente = nessun filtro. Lo passa il "
                    "picker di riga di inventari e rettifiche: un articolo non "
                    "gestito si salva, ma il piano lo marca NON_POSTABILE."
                ),
            ),
            OpenApiParameter(
                name="solo_oneri",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Solo articoli-onere (con causale_onere_id valorizzato). "
                    "Aggiunge causale_onere_id/_codice/_descrizione ai risultati. "
                    "Alimenta la porta oneri della commessa."
                ),
            ),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="CatalogoArticoliLookupResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il lookup articoli per autocomplete cross-dominio.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = qp_str(qp.get("search"))
        require_min_search_length(search, field_name="search")

        for ritirato in _FILTRI_RITIRATI_LOOKUP:
            if ritirato in qp:
                raise ValueError(f"{ritirato}_ritirato")
        limit = qp_int_strict(qp.get("limit"), "limit", 20)

        # ⭐ La riga di un documento: gli articoli li sceglie il DB
        #    (brief-db-articoli-ammessi-per-documento §9.6, Lotto 4). Nessun
        #    filtro libero accanto: la regola non la sceglie il chiamante, e un
        #    filtro in piu' nasconderebbe un articolo che il guard accetta.
        documento = qp_str_upper(qp.get("documento"))
        if documento is not None:
            if any(qp_str(qp.get(k)) is not None for k in _FILTRI_LIBERI_LOOKUP):
                raise ValueError("documento_con_filtri_liberi")
            return success_response(fn_lookup_articoli_ammessi(
                documento=documento,
                documento_id=qp_int_optional(qp.get("documento_id"), "documento_id"),
                search=search,
                tipo_eccezione=qp_str_upper(qp.get("tipo_eccezione")),
                articolo_padre_id=optional_uuid(
                    {"articolo_padre_id": qp.get("articolo_padre_id")}, "articolo_padre_id",
                ),
                limit=limit,
            ))

        data = fn_lookup_articoli(
            search=search,
            attivo=qp_bool_optional(qp.get("attivo"), "attivo", default=True),
            is_composito=qp_bool_optional(qp.get("is_composito"), "is_composito"),
            gestito_a_magazzino=qp_bool_optional(qp.get("gestito_a_magazzino"), "gestito_a_magazzino"),
            # Gli articoli-onere sono pochi (uno per causale) e si presentano
            # come tendina, non come autocomplete: il filtro vive senza `search`.
            solo_oneri=qp_bool_optional(qp.get("solo_oneri"), "solo_oneri", default=False),
            limit=limit,
        )
        return success_response(data)


    # Nota: il lookup UoM usa l'endpoint generico /api/v1/core/lookup/codici/?rel=catalogo.unita_misura


# --- CRUD Tipologie UoM ---


class ApiUomTipiList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "uom_tipi")
    is_search_endpoint = True
    lista_codice = "catalogo.uom_tipi"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoUomTipiListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce lista paginata tipologie UoM.
    def get(self, request: Request) -> JsonResponse:
        # Tabella di configurazione: niente 400 sotto soglia (Tid, 2026-09-23 —
        # brief-be-ricerca-full-liste-residue §6); la soglia e' del catalogo.
        p = parse_list_params(request.query_params, default_order="descrizione")
        results, total = fn_list_uom_tipi(
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUomTipoCreateRequest",
            fields={
                "codice": serializers.CharField(required=True),
                "codice_interno": serializers.CharField(required=True),
                "descrizione": serializers.CharField(required=True),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUomTipoCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nuova tipologia UoM.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_uom_tipo)


class ApiUomTipoDetail(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "uom_tipi")

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoUomTipoDetailResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce dettaglio singola tipologia UoM.
    def get(self, request: Request, tipo_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_uom_tipo(tipo_id))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUomTipoPatchRequest",
            fields={
                "descrizione": serializers.CharField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUomTipoUpdateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna una tipologia UoM.
    def patch(self, request: Request, tipo_id: int) -> JsonResponse:
        return success_response(fn_update_uom_tipo(tipo_id, corpo_oggetto(request)))


# --- CRUD Unita' di Misura ---


class ApiUnitaMisuraList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "unita_misura")
    is_search_endpoint = True
    lista_codice = "catalogo.unita_misura"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce lista paginata unita' di misura.
    def get(self, request: Request) -> JsonResponse:
        # Tabella di configurazione a codici corti (`KG`, `PZ`): la soglia la
        # dichiara il catalogo, niente 400 sotto soglia (Tid, 2026-09-23).
        p = parse_list_params(request.query_params, default_order="codice")
        results, total = fn_list_unita_misura(
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUnitaMisuraCreateRequest",
            fields={
                "codice": serializers.CharField(required=True),
                "descrizione": serializers.CharField(required=True),
                "descrizione_fattura": serializers.CharField(required=False, allow_blank=True, allow_null=True),
                "tipo_uom_id": serializers.IntegerField(required=True),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nuova unita' di misura.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_unita_misura)


class ApiUnitaMisuraDetail(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "unita_misura")

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraDetailResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce dettaglio singola unita' di misura.
    def get(self, request: Request, uom_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_unita_misura(uom_id))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUnitaMisuraPatchRequest",
            fields={
                "descrizione": serializers.CharField(required=False),
                "descrizione_fattura": serializers.CharField(required=False, allow_blank=True, allow_null=True),
                "tipo_uom_id": serializers.IntegerField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraUpdateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna una unita' di misura.
    def patch(self, request: Request, uom_id: int) -> JsonResponse:
        return success_response(fn_update_unita_misura(uom_id, corpo_oggetto(request)))


class ApiUnitaMisuraDisattiva(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "unita_misura")

    @extend_schema(
        request=inline_serializer(name="CatalogoUnitaMisuraDisattivaRequest", fields={}),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraDisattivaResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Disattiva una unita' di misura.
    def post(self, request: Request, uom_id: int) -> JsonResponse:
        return handle_post_json(request, handler=lambda _payload: fn_disattiva_unita_misura(uom_id))


# =================================================================
# Conversioni UoM
# =================================================================

class ApiConversioniList(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "unita_misura")
    is_search_endpoint = True
    lista_codice = "catalogo.conversioni_uom"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False, description="Filtro attivo (null=tutti)"),
            OpenApiParameter(name="uom_id", type=int, required=False, description="Filtra conversioni per UoM (from o to)"),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoConversioniListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Lista paginata conversioni UoM, allineata alle due sorelle UoM
    #        (`ApiUomTipiList`/`ApiUnitaMisuraList`): stessi query param, stesso
    #        envelope paginato. Filtro opzionale uom_id per le conversioni di
    #        una specifica UoM (sotto-drawer).
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="uom_from_codice")
        results, total = fn_list_conversioni(
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            uom_id=qp_int_optional(request.query_params.get("uom_id"), "uom_id"),
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoConversioneCreateRequest",
            fields={
                "uom_from_id": serializers.IntegerField(required=True),
                "uom_to_id": serializers.IntegerField(required=True),
                "fattore": serializers.DecimalField(max_digits=18, decimal_places=6, required=True),
                "valido_dal": serializers.DateField(required=False, allow_null=True),
                "valido_al": serializers.DateField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoConversioneCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nuova conversione UoM.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_conversione)


class ApiConversioneDetail(DomainAPIView):
    area_funzionale = "catalogo"
    model_permission = ("catalogo", "unita_misura")

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoConversioneDetailResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce dettaglio singola conversione UoM.
    def get(self, request: Request, conv_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_conversione(conv_id))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoConversionePatchRequest",
            fields={
                "fattore": serializers.DecimalField(max_digits=18, decimal_places=6, required=False),
                "valido_dal": serializers.DateField(required=False, allow_null=True),
                "valido_al": serializers.DateField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoConversioneUpdateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna una conversione UoM.
    def patch(self, request: Request, conv_id: int) -> JsonResponse:
        return success_response(fn_update_conversione(conv_id, corpo_oggetto(request)))
