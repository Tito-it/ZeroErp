# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.contratti (CRUD v5 — F2-BE-06).
#        Espone: testata + righe + utility 1:1 + cambio stato.
#        I trigger DB sono autoritativi per le coerenze cross-table
#        (modalita' C, tipo/classe utenza, overlap); il service
#        traduce gli errori P0001 in codici applicativi consumati
#        dal frontend via error envelope uniforme.
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
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
    qp_bool_optional,
)
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._riga_erogazioni_views import RigaErogazioniView
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.db.contratti_repository import ContrattoRigheListaRepository
from apps.vendite.services import contratti_service
from apps.vendite.services.contratti_service import ContrattiService
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._schema_da_contratto import schema_da_contratto
from apps.vendite.api._componenti_schema import (
    COMPONENTE_PATCH_REQUEST,
    COMPONENTI_LIST_PARAMETERS,
    COMPONENTI_LIST_RESPONSE,
    PREVIEW_COMPONENTI_REQUEST,
    PREVIEW_COMPONENTI_RESPONSE,
)

# Codice lista configurabile (ui.lista_definizione) per contratti.
_LISTA_CODICE_CONTRATTI = "vendite.contratti"


# =================================================================
# Lista + creazione testata
# =================================================================


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
# La utility 1:1 del contratto: creazione e modifica hanno contratti propri.
_UTILITY_CREATE_REQUEST = schema_da_contratto(
    "VenditeContrattoUtilityCreateReq", contratti_service.UTILITY_CREATE_KEYS,
)
_UTILITY_UPDATE_REQUEST = schema_da_contratto(
    "VenditeContrattoUtilityUpdateReq", contratti_service.UTILITY_UPDATE_KEYS,
)
# La classe, non l'istanza: una per uso (l'istanza legata a un campo non si
# riusa, e due classi con lo stesso nome fanno uno schema sbagliato).
_UTILITY_CREATE_CLS = type(_UTILITY_CREATE_REQUEST)
_UTILITY_UPDATE_CLS = type(_UTILITY_UPDATE_REQUEST)
_CONTRATTO_CREATE_REQUEST = schema_da_contratto(
    "VenditeContrattoCreateReq", contratti_service.CREATE_KEYS_TESTATA,
    obbligatorie=("billing_account_id", "istanza_utility_id", "utility_id", "valido_dal"),
    speciali={"utility": _UTILITY_CREATE_CLS(required=False, allow_null=True)},
)


_CONTRATTO_PATCH_REQUEST = schema_da_contratto(
    "VenditeContrattoPatchReq", contratti_service.UPDATE_KEYS_CONTRATTO,
    # La scheda inline: le sole chiavi del form, la coppia e' della testata.
    speciali={"utility": _UTILITY_UPDATE_CLS(required=False, allow_null=True)},
)


class ApiContrattiExportView(DomainAPIView):
    """GET /api/v1/vendite/contratti/export/?formato=csv|xlsx

    Genera un file CSV o Excel con i contratti filtrati dalla query string
    (stessi parametri del list endpoint). Hard cap 10.000 righe — sopra
    solleva E_UI_EXPORT_LIMIT_EXCEEDED (422). Usa il renderer generico
    `ListaExportService` (DEF-1) e il catalogo colonne `vendite.contratti`
    per coerenza con la DataTable a video (colonne nascoste escluse, ordine
    utente rispettato).

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata
    prima della view.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")
    is_search_endpoint = True
    lista_codice = "vendite.contratti"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_doc_contratto_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="ambito", type=str, required=False),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="scadenza_mese", type=str, required=False,
                             description="YYYY-MM"),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)

        p = parse_list_params(qp, default_order="data")
        stato_id = qp_int_optional(qp.get("stato_doc_contratto_id"), "stato_doc_contratto_id")
        utility_id = qp_int_optional(qp.get("utility_id"), "utility_id")
        listino_id = qp_int_optional(qp.get("listino_id"), "listino_id")
        ba_id = qp_int_optional(qp.get("billing_account_id"), "billing_account_id")
        ambito = qp_str(qp.get("ambito"))
        data_da = qp_iso_date_optional(qp.get("data_da"), "data_da")
        data_a = qp_iso_date_optional(qp.get("data_a"), "data_a")
        scadenza_mese = qp_str(qp.get("scadenza_mese"))

        svc = ContrattiService()
        results, total = svc.list_contratti(
            search=p["search"],
            billing_account_id=ba_id,
            stato_doc_contratto_id=stato_id,
            utility_id=utility_id,
            ambito=ambito,
            listino_id=listino_id,
            data_da=data_da,
            data_a=data_a,
            scadenza_mese=scadenza_mese,
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
        )
        filtri_applicati = svc.resolve_filtri_export_label(
            ambito=ambito,
            stato_doc_contratto_id=stato_id,
            utility_id=utility_id,
            listino_id=listino_id,
            billing_account_id=ba_id,
            data_da=data_da,
            data_a=data_a,
            scadenza_mese=scadenza_mese,
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_CONTRATTI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiContrattiList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")
    is_search_endpoint = True
    lista_codice = "vendite.contratti"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_doc_contratto_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="ambito", type=str, required=False,
                             description="COMMODITY | COMMERCIO"),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO YYYY-MM-DD. Nessun default backend."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="numero | data | valido_dal | valido_al | "
                                         "ba_ragione_sociale | stato_codice | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeContrattiListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata contratti con filtri standard. Scope emittente
    #        applicato lato repository via `fn_get_emittenti_scope_pk_ids`
    #        (post brief simmetria 2026-05-26).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        svc = ContrattiService()
        results, total = svc.list_contratti(
            search=p["search"],
            billing_account_id=qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
            stato_doc_contratto_id=qp_int_optional(qp.get("stato_doc_contratto_id"), "stato_doc_contratto_id"),
            utility_id=qp_int_optional(qp.get("utility_id"), "utility_id"),
            ambito=qp_str(qp.get("ambito")),
            listino_id=qp_int_optional(qp.get("listino_id"), "listino_id"),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            scadenza_mese=qp_str(qp.get("scadenza_mese")),
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_CONTRATTO_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuovo contratto. Numero generato dal service; stato DRAFT.
    def post(self, request: Request) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return handle_post_json(
            request,
            handler=lambda payload: ContrattiService().create_contratto(
                payload, auth_user_id=auth_user_id,
            ),
        )


class ApiContrattoDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio contratto (testata + utility 1:1 + righe).
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        del request
        return success_response(ContrattiService().get_contratto(contratto_id))

    @extend_schema(
        request=_CONTRATTO_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi mutabili. Numero/identificativi/stato immutabili
    #        in PATCH (cambio stato via endpoint dedicato). auth_user_id
    #        propagato al gate L2 sulla variazione globale (§3-bis-E).
    def patch(self, request: Request, contratto_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return success_response(
            ContrattiService().update_contratto(
                contratto_id, corpo_oggetto(request),
                auth_user_id=auth_user_id,
            )
        )


# =================================================================
# Cambio stato
# =================================================================


_CONTRATTO_STATO_REQUEST = inline_serializer(
    name="VenditeContrattoStatoReq",
    fields={
        "codice_interno": serializers.CharField(),
        "valido_al": serializers.DateField(
            required=False, allow_null=True,
            help_text="Opzionale: data fine validita' (cessazione contestuale al cambio stato).",
        ),
        "legami_confermati": serializers.IntegerField(
            required=False, allow_null=True,
            help_text="Verso ANNULLATO: quanti legami si sono visti nella finestra di conferma.",
        ),
    },
)


class ApiContrattoCambiaStato(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        request=_CONTRATTO_STATO_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoStatoResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato del contratto (DRAFT -> ATTIVO -> CESSATO).
    #        Se valido_al e' fornito, applica anche PATCH valido_al nella
    #        stessa transazione (caso d'uso: dialog "Cessa contratto" che
    #        chiede la data al click). Trigger DB fa fail-fast su
    #        attivazione modalita' C incompleta.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        body = corpo_oggetto(request)
        codice = body.get("codice_interno", "")
        valido_al_raw = body.get("valido_al")
        valido_al = parse_iso_date(valido_al_raw) if valido_al_raw else None
        return success_response(
            ContrattiService().cambia_stato(
                contratto_id,
                codice_interno=codice,
                valido_al=valido_al,
                user=request.user,
                legami_confermati=body.get("legami_confermati"),
            )
        )


# =================================================================
# Righe contratto
# =================================================================


_RIGA_CREATE_REQUEST = schema_da_contratto(
    "VenditeContrattoRigaCreateReq", contratti_service.CREATE_KEYS_RIGA,
    obbligatorie=("articolo_id", "tipo_eccezione"),
)


_RIGA_PATCH_REQUEST = schema_da_contratto(
    "VenditeContrattoRigaPatchReq", contratti_service.UPDATE_KEYS_RIGA,
)


class ApiContrattoRigheList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        request=_RIGA_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge una riga al contratto. Auto-init componenti se
    # articolo composito (modello unificato BoM 2026-05-13).
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().create_riga(
                contratto_id, corpo_oggetto(request),
                auth_user_id=get_actor_user_id(request),
            )
        )


class ApiContrattoContestoPricing(DomainAPIView):
    """GET /api/v1/vendite/contratti/<id>/contesto-pricing/

    Ritorna il contesto pricing applicato al contratto: forma (con/senza
    listino), riferimento listino e versione (FISSATA se ATTIVO, CORRENTE se
    DRAFT), variazione globale, categoria cliente. Mutuato dal pattern
    preventivi (`/preventivi/<id>/contesto-pricing/`) per la simmetria UI:
    il drawer contratto mostra un badge informativo nell'header.

    Pura lettura, nessun side-effect. Area `vendite` livello LETTURA.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoContestoPricingResp",
            fields={"data": inline_serializer(
                name="VenditeContrattoContestoPricingData",
                fields={
                    "contratto_id": serializers.IntegerField(),
                    "forma": serializers.CharField(
                        help_text="'con_listino' | 'senza_listino'",
                    ),
                    "stato_codice_interno": serializers.CharField(),
                    "listino_id": serializers.IntegerField(allow_null=True),
                    "listino_codice": serializers.CharField(allow_null=True),
                    "listino_descrizione": serializers.CharField(allow_null=True),
                    "listino_versione_id": serializers.IntegerField(allow_null=True),
                    "listino_versione_codice": serializers.CharField(allow_null=True),
                    "listino_versione_fissata": serializers.BooleanField(),
                    "listino_versione_corrente_id": serializers.IntegerField(allow_null=True),
                    "listino_versione_corrente_codice": serializers.CharField(allow_null=True),
                    "drift_versione_listino": serializers.BooleanField(),
                    "tipo_variazione_globale": serializers.CharField(allow_null=True),
                    "valore_variazione_globale": serializers.DecimalField(
                        max_digits=12, decimal_places=4, allow_null=True,
                    ),
                    "categoria_cliente_id": serializers.IntegerField(allow_null=True),
                    "categoria_cliente_codice": serializers.CharField(allow_null=True),
                    "categoria_cliente_descrizione": serializers.CharField(allow_null=True),
                },
            )},
        )},
    )
    # Scopo: Restituisce via GET il contesto pricing del contratto.
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        del request
        data = ContrattiService().get_contesto_pricing(contratto_id)
        return success_response(data or {})


# ── Righe: la lista configurabile `vendite.contratto_righe` (103) ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto D). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⚠️ `GET …/righe/` resta la lettura delle righe PERSISTITE (e il POST di
#    creazione): la lista e' su `…/righe/lista/`, e legge le righe OPERATIVE
#    dalla funzione. L'anteprima intera `…/righe-preview/` e' ritirata il
#    2026-10-04 (brief-db-liste-righe-documento §9.15): il drawer leggeva da
#    li', e ora legge questa lista.
_ContrattoRigheLista, _ContrattoRigheListaExport = build_lista_figlia_views(
    schema_prefix="ContrattoRighe",
    operation_id="vendite_contratti_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="contratto_id",
    model_permission=("vendite", "contratto"),
    pagina_call=lambda documento_id, **kw: ContrattiService().list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=ContrattoRigheListaRepository.righe_colonne_ordinabili(),
    ordine_assente=ContrattoRigheListaRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiContrattoRigheListaView(_ContrattoRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.contratto_righe"


class ApiContrattoRigheListaExportView(_ContrattoRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.contratto_righe"


class ApiContrattoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        request=_RIGA_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna una riga (articolo_id immutabile). `auth_user_id`
    # serve al workflow L3 (gate L1+L2+L3 quando PATCH tocca prezzo_unitario).
    def patch(self, request: Request, contratto_id: int, riga_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return success_response(
            ContrattiService().update_riga(
                contratto_id, riga_id, corpo_oggetto(request), auth_user_id=auth_user_id,
            )
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoRigaDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cancella una riga (FK note_contratto blocca via trigger).
    def delete(self, request: Request, contratto_id: int, riga_id: int) -> JsonResponse:
        del request
        ContrattiService().delete_riga(contratto_id, riga_id)
        return success_response({"deleted": True, "id": riga_id})


# =================================================================
# Utility 1:1
# =================================================================




class ApiContrattoUtility(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        request=_UTILITY_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea la riga utility 1:1 per il contratto.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().create_utility(contratto_id, corpo_oggetto(request))
        )

    @extend_schema(
        request=_UTILITY_UPDATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna la riga utility (istanza/utility immutabili).
    def patch(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().update_utility(contratto_id, corpo_oggetto(request))
        )


# =================================================================
# Componenti BoM riga contratto (modello unificato 2026-05-13)
# =================================================================
# Pattern simmetrico preventivi:
#   POST /righe/preview-componenti/    -> ComponentiDialog FE pre-save
#   GET  /righe/<rid>/componenti/      -> EDIT panel post-save
#   PATCH/DELETE /righe/<rid>/componenti/<cid>/  -> CRUD singolo componente


class ApiContrattoRigaErogazioni(RigaErogazioniView):
    """GET /api/v1/vendite/contratti/<id>/righe/erogazioni/?articolo_id=<uuid>

    Come si puo' erogare l'articolo su una riga del contratto: le combinazioni
    ammesse col default in testa (base `RigaErogazioniView`, gemella
    dell'offerta).
    """

    model_permission = ("vendite", "contratto")
    url_kwarg = "contratto_id"

    # Scopo: le combinazioni dal service del contratto.
    def elenco(self, documento_id: int, articolo_id: Any) -> list[dict[str, Any]]:
        return ContrattiService().list_erogazioni_riga(documento_id, articolo_id)


class ApiContrattoRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/contratti/<id>/righe/preview-componenti/

    Read-only: ritorna i componenti BoM con prezzo suggerito dal resolver
    bundle-aware per pre-popolare il ComponentiDialog FE PRIMA del save
    di una riga padre composita. Specchio simmetrico di
    `ApiPreventivoRigaPreviewComponenti`.

    Nessun side-effect (fn DB STABLE). Area `vendite` LETTURA sufficiente.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=PREVIEW_COMPONENTI_REQUEST,
        responses={200: PREVIEW_COMPONENTI_RESPONSE},
    )
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        # Cattura auth_user_id PRIMA dell'handler chiuso: il service risolve
        # internamente l'emittente (precedenza testata > operatore), evitando
        # accesso a membri privati dal caller.
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> list[dict[str, Any]]:
            articolo_id = str(payload.get("articolo_id") or "")
            uom_raw = payload.get("uom_operativa_id")
            uom_operativa_id = int(uom_raw) if uom_raw not in (None, "") else None
            quantita = payload.get("quantita")
            return ContrattiService().preview_componenti_riga(
                contratto_id,
                articolo_id=articolo_id,
                uom_operativa_id=uom_operativa_id,
                quantita=quantita,
                auth_user_id=auth_user_id,
            )

        return handle_post_json(request, handler=_handler)


class ApiContrattoRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/

    Lista componenti BoM persistiti su `contratti_righe_componenti` per la
    riga padre composita. Specchio simmetrico di `ApiPreventivoRigaComponentiList`.

    Query param `solo_attivi` (bool, default `true`): se `false` include
    anche opzionali disattivati (usato dall'EDIT panel FE per riattivazione).

    Area `vendite` LETTURA sufficiente.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        parameters=COMPONENTI_LIST_PARAMETERS,
        responses={200: COMPONENTI_LIST_RESPONSE},
    )
    def get(
        self, request: Request, contratto_id: int, riga_id: int,
    ) -> JsonResponse:
        # Il BB dei flag di trasporto (§A6), come i gemelli DDT e ordini.
        solo_attivi = qp_bool_optional(request.query_params.get("solo_attivi"), "solo_attivi", default=True)
        return success_response(
            ContrattiService().list_componenti_riga(
                contratto_id, riga_id, solo_attivi=solo_attivi,
            )
        )


class ApiContrattoRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/<cid>/

    CRUD singolo componente BoM riga contratto. Specchio simmetrico di
    `ApiPreventivoRigaComponenteDetail`. Match URL anti-tampering:
    `contratto_id` + `riga_id` + `componente_id` devono essere coerenti.

    Area `vendite` LETTURA + azione `prezzo_override_manuale` per UPDATE
    prezzo (TODO Sprint E: oggi accettiamo qualsiasi UPDATE su contratto
    DRAFT, il trigger DB PENDING guard e' safety net).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        request=COMPONENTE_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaComponentePatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def patch(
        self, request: Request, contratto_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ContrattiService().update_componente_riga(
                contratto_id, riga_id, componente_id, corpo_oggetto(request),
                auth_user_id=get_actor_user_id(request),
            )
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoRigaComponenteDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def delete(
        self, request: Request, contratto_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        del request
        return success_response(
            ContrattiService().delete_componente_riga(
                contratto_id, riga_id, componente_id,
            )
        )


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Contratto",
    url_kwarg="contratto_id",
    list_call=lambda contratto_id: contratti_service.list_indirizzi(contratto_id),
    upsert_call=lambda contratto_id, payload: contratti_service.upsert_indirizzo(
        contratto_id, payload),
    delete_call=lambda contratto_id, indirizzo_id: contratti_service.delete_indirizzo(
        contratto_id, indirizzo_id),
    model_permission=("vendite", "contratto"),
)
ApiContrattoIndirizzi = _indirizzi_views.lista
ApiContrattoIndirizzoDetail = _indirizzi_views.detail
