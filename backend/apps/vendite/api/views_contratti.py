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

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
)
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.services.contratti_service import ContrattiService

# Codice lista configurabile (ui.lista_definizione) per contratti.
_LISTA_CODICE_CONTRATTI = "vendite.contratti"


# =================================================================
# Lista + creazione testata
# =================================================================


_CONTRATTO_CREATE_REQUEST = inline_serializer(
    name="VenditeContrattoCreateReq",
    fields={
        # Post brief simmetria 2026-05-26: opzionale. Se omesso il trigger DB
        # `trgfn_contratti_default_emittente` lo deriva dalla GUC
        # `app.current_user_id` (operatore non-admin). L'admin globale lo
        # specifica esplicitamente; il guard DB rifiuta coppie BA<->EF
        # incoerenti.
        "emittente_fiscale_id": serializers.IntegerField(required=False, allow_null=True),
        "billing_account_id": serializers.IntegerField(),
        "istanza_utility_id": serializers.IntegerField(),
        "utility_id": serializers.IntegerField(),
        "ambito": serializers.CharField(required=False),
        "valido_dal": serializers.DateField(),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "parent_contratto_id": serializers.IntegerField(required=False, allow_null=True),
        "data": serializers.DateField(required=False),
        "listino_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "utility": serializers.DictField(required=False),
    },
)


_CONTRATTO_PATCH_REQUEST = inline_serializer(
    name="VenditeContrattoPatchReq",
    fields={
        "ambito": serializers.CharField(required=False),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "parent_contratto_id": serializers.IntegerField(required=False, allow_null=True),
        "data": serializers.DateField(required=False),
        "listino_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
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
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="search", type=str, required=False),
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
        )
        filtri_applicati = svc.resolve_filtri_export_label(
            search=p["search"],
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
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su numero contratto e ragione sociale BA."),
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
        return handle_post_json(request, handler=ContrattiService().create_contratto)


class ApiContrattoDetail(DomainAPIView):
    area_funzionale = "vendite"

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
        auth_user_id = request.user.id if request.user.is_authenticated else None
        return success_response(
            ContrattiService().update_contratto(
                contratto_id, request.data,
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
    },
)


class ApiContrattoCambiaStato(DomainAPIView):
    area_funzionale = "vendite"

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
        body = request.data or {}
        codice = body.get("codice_interno", "")
        valido_al_raw = body.get("valido_al")
        valido_al = parse_iso_date(valido_al_raw) if valido_al_raw else None
        return success_response(
            ContrattiService().cambia_stato(
                contratto_id,
                codice_interno=codice,
                valido_al=valido_al,
                user=request.user,
            )
        )


# =================================================================
# Righe contratto
# =================================================================


_RIGA_CREATE_REQUEST = inline_serializer(
    name="VenditeContrattoRigaCreateReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        # Refactor modalita 2026-05-15: tipo_eccezione obbligatorio.
        # OVERRIDE = prezzo personalizzato per articolo del listino.
        # ESCLUSIONE = articolo del listino non disponibile (prezzo NULL).
        # AGGIUNTA = articolo fuori-listino aggiunto al contratto.
        "tipo_eccezione": serializers.ChoiceField(
            choices=["OVERRIDE", "ESCLUSIONE", "AGGIUNTA"],
        ),
        "tipo_erogazione": serializers.CharField(required=False),
        "fonte_quantita_attesa": serializers.CharField(required=False),
        "periodicita": serializers.CharField(required=False),
        "generazione_canone": serializers.CharField(required=False),
        "competenza_canone": serializers.CharField(required=False),
        "prezzo_unitario": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "quantita": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "qta_operativa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "factor_to_base": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False,
        ),
        "ordine": serializers.IntegerField(required=False),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


_RIGA_PATCH_REQUEST = inline_serializer(
    name="VenditeContrattoRigaPatchReq",
    fields={
        "tipo_erogazione": serializers.CharField(required=False),
        "fonte_quantita_attesa": serializers.CharField(required=False),
        "periodicita": serializers.CharField(required=False),
        "generazione_canone": serializers.CharField(required=False),
        "competenza_canone": serializers.CharField(required=False),
        "prezzo_unitario": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "quantita": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "qta_operativa": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "factor_to_base": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False,
        ),
        "ordine": serializers.IntegerField(required=False),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


class ApiContrattoRigheList(DomainAPIView):
    area_funzionale = "vendite"

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
                contratto_id, request.data,
                auth_user_id=get_scope_user_id(request),
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
                    "stato_codice": serializers.CharField(),
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


class ApiContrattoRighePreview(DomainAPIView):
    """GET preview righe applicate dal contratto.

    Modalita' A: tutte le righe del listino con prezzo finale = prezzo
    listino + variazione globale (origine='DA_LISTINO').

    Modalita' B: tutte le righe del listino, con override applicato dove
    presente in contratti_righe (origine='OVERRIDE') o variazione globale
    sulle altre (origine='DA_LISTINO').

    Modalita' C: lista righe vuota (le righe vivono in contratti_righe e
    sono lette dall'endpoint standard /righe/).

    Endpoint readonly: il FE lo usa per mostrare l'anteprima dei prezzi
    applicati al cliente senza duplicare la formula di calcolo.
    """

    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeContrattoRighePreviewResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce envelope con testata sintetica + righe preview.
    def get(self, request: Request, contratto_id: int) -> JsonResponse:
        del request
        return success_response(
            ContrattiService().list_righe_preview(contratto_id)
        )


class ApiContrattoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"

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
        del contratto_id  # riga_id e' identificatore globale; contratto_id solo per coerenza URL.
        auth_user_id = request.user.id if request.user.is_authenticated else None
        return success_response(
            ContrattiService().update_riga(
                riga_id, request.data, auth_user_id=auth_user_id,
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
        del request, contratto_id
        ContrattiService().delete_riga(riga_id)
        return success_response({"deleted": True, "id": riga_id})


# =================================================================
# Utility 1:1
# =================================================================


_UTILITY_REQUEST = inline_serializer(
    name="VenditeContrattoUtilityReq",
    fields={
        "istanza_dati_precontrattuali_id": serializers.IntegerField(required=False, allow_null=True),
        "tipo_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "param_1_num": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "param_2_txt": serializers.CharField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


class ApiContrattoUtility(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_UTILITY_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea la riga utility 1:1 per il contratto.
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().create_utility(contratto_id, request.data)
        )

    @extend_schema(
        request=_UTILITY_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoUtilityPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna la riga utility (istanza/utility immutabili).
    def patch(self, request: Request, contratto_id: int) -> JsonResponse:
        return success_response(
            ContrattiService().update_utility(contratto_id, request.data)
        )


# =================================================================
# Componenti BoM riga contratto (modello unificato 2026-05-13)
# =================================================================
# Pattern simmetrico preventivi:
#   POST /righe/preview-componenti/    -> ComponentiDialog FE pre-save
#   GET  /righe/<rid>/componenti/      -> EDIT panel post-save
#   PATCH/DELETE /righe/<rid>/componenti/<cid>/  -> CRUD singolo componente


_RIGA_PREVIEW_COMPONENTI_REQUEST = inline_serializer(
    name="VenditeContrattoRigaPreviewComponentiReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "quantita": serializers.DecimalField(
            max_digits=22, decimal_places=10, required=True,
        ),
    },
)


class ApiContrattoRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/contratti/<id>/righe/preview-componenti/

    Read-only: ritorna i componenti BoM con prezzo suggerito dal resolver
    bundle-aware per pre-popolare il ComponentiDialog FE PRIMA del save
    di una riga padre composita. Specchio simmetrico di
    `ApiPreventivoRigaPreviewComponenti`.

    Nessun side-effect (fn DB STABLE). Area `vendite` LETTURA sufficiente.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=_RIGA_PREVIEW_COMPONENTI_REQUEST,
        responses={200: inline_serializer(
            name="VenditeContrattoRigaPreviewComponentiResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    def post(self, request: Request, contratto_id: int) -> JsonResponse:
        # Cattura auth_user_id PRIMA dell'handler chiuso: il service risolve
        # internamente l'emittente (precedenza testata > operatore), evitando
        # accesso a membri privati dal caller.
        auth_user_id = get_scope_user_id(request)

        def _handler(payload: dict[str, object]) -> list[dict[str, object]]:
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="solo_attivi", type=bool, default=True,
                description=(
                    "Default true: solo componenti attivi. Se false include "
                    "anche opzionali disattivati (EDIT panel)."
                ),
            ),
        ],
        responses={200: inline_serializer(
            name="VenditeContrattoRigaComponentiListResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    def get(
        self, request: Request, contratto_id: int, riga_id: int,
    ) -> JsonResponse:
        solo_attivi_raw = request.query_params.get("solo_attivi", "true")
        solo_attivi = str(solo_attivi_raw).lower() not in ("false", "0", "no", "off")
        return success_response(
            ContrattiService().list_componenti_riga(
                contratto_id, riga_id, solo_attivi=solo_attivi,
            )
        )


# Schema OpenAPI allineato a `COMPONENTE_UPDATE_ALLOWED` (whitelist mixin
# `ComponentiRepositoryMixin`). Tutti i campi sono opzionali e applicati in
# delta. Campi struttura (`componente_id`, `articolo_componente_id`,
# `coeff_qta_snapshot`, `riga_contratto_id`, `quantita`) sono silenziosamente
# ignorati dal mixin (defense-in-depth).
_RIGA_COMPONENTE_PATCH_REQUEST = inline_serializer(
    name="VenditeContrattoRigaComponentePatchReq",
    fields={
        "prezzo_unitario": serializers.DecimalField(
            max_digits=22, decimal_places=10, required=False, allow_null=True,
        ),
        "iva_id": serializers.IntegerField(required=False, allow_null=True),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "factor_to_base": serializers.DecimalField(
            max_digits=22, decimal_places=10, required=False, allow_null=True,
        ),
        "qta_operativa": serializers.DecimalField(
            max_digits=22, decimal_places=10, required=False, allow_null=True,
        ),
        "origine_prezzo": serializers.CharField(required=False, allow_null=True),
        "prezzo_resolver_context": serializers.JSONField(
            required=False, allow_null=True,
        ),
        "stato_approvazione_prezzo": serializers.CharField(
            required=False, allow_null=True,
        ),
        "pratica_approvazione_prezzo_id": serializers.IntegerField(
            required=False, allow_null=True,
        ),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "ordine": serializers.IntegerField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    },
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

    @extend_schema(
        request=_RIGA_COMPONENTE_PATCH_REQUEST,
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
                contratto_id, riga_id, componente_id, dict(request.data),
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
