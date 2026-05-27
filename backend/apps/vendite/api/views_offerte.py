# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.offerte_commerciali (CRUD iniziale).
#        Espone: testata + cambio stato (emetti/registra-esito/annulla) +
#        eccezioni + utility 1:1. State machine enforced dal trigger DB
#        trgfn_offerte_commerciali_guard_transizione; il service traduce
#        gli errori P0001 in ServiceError che il middleware converte in
#        error envelope uniforme.
#
#        Stato 2026-05-25: tutti gli endpoint del ciclo offerta esposti.
#        Codice `OFC-*` automatico via trigger DB; `crea-revisione/`,
#        `revisioni/`, `push-contratto/` cablati end-to-end. Niente
#        endpoint "non ancora cablato" residuo.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.vendite.services.offerte_service import OfferteService


# Scopo: Converte un query param intero opzionale (None se assente o vuoto).
def _qp_int_optional(raw: str | None, name: str) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name}_invalid") from exc


# =================================================================
# Schemas inline per drf-spectacular
# =================================================================


_OFFERTA_CREATE_REQUEST = inline_serializer(
    name="VenditeOffertaCreateReq",
    fields={
        # Step 5 atterrato 2026-05-25: `codice` generato dal trigger DB
        # (BEFORE INSERT). Non va piu' nel payload — rifiutato come
        # unknown_key dalla whitelist applicativa.
        "emittente_fiscale_id": serializers.IntegerField(),
        "billing_account_id": serializers.IntegerField(),
        "istanza_utility_id": serializers.IntegerField(),
        "utility_id": serializers.IntegerField(),
        "listino_id": serializers.IntegerField(),
        "listino_versione_id": serializers.IntegerField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "validita_dal": serializers.DateField(),
        "validita_al": serializers.DateField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


_OFFERTA_PATCH_REQUEST = inline_serializer(
    name="VenditeOffertaPatchReq",
    fields={
        "emittente_fiscale_id": serializers.IntegerField(required=False),
        "billing_account_id": serializers.IntegerField(required=False),
        "istanza_utility_id": serializers.IntegerField(required=False),
        "utility_id": serializers.IntegerField(required=False),
        "listino_id": serializers.IntegerField(required=False),
        "listino_versione_id": serializers.IntegerField(required=False, allow_null=True),
        "valore_variazione_globale": serializers.DecimalField(
            max_digits=10, decimal_places=4, required=False, allow_null=True,
        ),
        "tipo_variazione_globale": serializers.CharField(required=False, allow_null=True),
        "validita_dal": serializers.DateField(required=False),
        "validita_al": serializers.DateField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


_ESITO_REQUEST = inline_serializer(
    name="VenditeOffertaEsitoReq",
    fields={
        # Esito cliente da EMESSA: ACCETTATA (motivazione opzionale) oppure
        # RIFIUTATA (motivazione obbligatoria).
        "esito": serializers.ChoiceField(choices=["ACCETTATA", "RIFIUTATA"]),
        "motivazione": serializers.CharField(required=False, allow_blank=True),
    },
)


_ANNULLA_REQUEST = inline_serializer(
    name="VenditeOffertaAnnullaReq",
    fields={"motivazione": serializers.CharField()},
)


_ECCEZIONE_CREATE_REQUEST = inline_serializer(
    name="VenditeOffertaEccezioneCreateReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        "tipo_eccezione": serializers.ChoiceField(
            choices=["OVERRIDE", "ESCLUSIONE", "AGGIUNTA"],
        ),
        "tipo_erogazione": serializers.CharField(required=False),
        "fonte_quantita_attesa": serializers.CharField(),
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


_ECCEZIONE_PATCH_REQUEST = inline_serializer(
    name="VenditeOffertaEccezionePatchReq",
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


_UTILITY_CREATE_REQUEST = inline_serializer(
    name="VenditeOffertaUtilityCreateReq",
    fields={
        "istanza_utility_id": serializers.IntegerField(),
        "utility_id": serializers.IntegerField(),
        "istanza_dati_precontrattuali_id": serializers.IntegerField(
            required=False, allow_null=True,
        ),
        "tipo_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "param_1_num": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "param_2_txt": serializers.CharField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


_UTILITY_PATCH_REQUEST = inline_serializer(
    name="VenditeOffertaUtilityPatchReq",
    fields={
        "istanza_dati_precontrattuali_id": serializers.IntegerField(
            required=False, allow_null=True,
        ),
        "tipo_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
        "param_1_num": serializers.DecimalField(
            max_digits=18, decimal_places=6, required=False, allow_null=True,
        ),
        "param_2_txt": serializers.CharField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
    },
)


# =================================================================
# Lista + creazione testata
# =================================================================


class ApiOfferteList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_offerte_list",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su codice e ragione sociale BA (>=3 char)."),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="BOZZA | EMESSA | ACCETTATA | RIFIUTATA | ANNULLATA | SUPERATA"),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="validita_dal_min", type=str, required=False,
                             description="Data ISO YYYY-MM-DD. Nessun default backend."),
            OpenApiParameter(name="validita_dal_max", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="codice | validita_dal | validita_al | data_emissione | "
                                         "billing_account_display | stato_codice | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeOfferteListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata offerte con filtri standard.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data_insert")
        svc = OfferteService()
        results, total = svc.list_offerte(
            search=p["search"],
            billing_account_id=_qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
            stato_codice_interno=qp_str(qp.get("stato_codice_interno")),
            utility_id=_qp_int_optional(qp.get("utility_id"), "utility_id"),
            listino_id=_qp_int_optional(qp.get("listino_id"), "listino_id"),
            validita_dal_min=qp_str(qp.get("validita_dal_min")),
            validita_dal_max=qp_str(qp.get("validita_dal_max")),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_OFFERTA_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuova offerta in stato BOZZA. Il `codice` arriva dal payload
    #        finche' il team DB non chiude step 5 (sistema_codici).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=OfferteService().crea_offerta)


# =================================================================
# Dettaglio + PATCH + DELETE testata
# =================================================================


class ApiOffertaDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio offerta (testata + eccezioni + utility 1:1).
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        return success_response(OfferteService().get_offerta(offerta_id))

    @extend_schema(
        request=_OFFERTA_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna testata offerta (solo in BOZZA, guard lato service).
    def patch(self, request: Request, offerta_id: int) -> JsonResponse:
        return success_response(
            OfferteService().aggiorna_offerta(offerta_id, request.data or {})
        )

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeOffertaDeleteResp",
                fields={"data": serializers.DictField()},
            )
        },
    )
    # Scopo: Cancella offerta (hard delete, solo BOZZA). Annullamento
    #        di processo via endpoint dedicato `/annulla/`.
    def delete(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        OfferteService().elimina_offerta(offerta_id)
        return success_response({"deleted": True, "offerta_id": offerta_id})


# =================================================================
# Cambio stato (emetti / registra-esito / annulla)
# =================================================================


# `ApiOffertaEmetti` e' stato spostato in `offerte_documenti_views.py`:
# l'emissione (BOZZA -> EMESSA) ora genera+persiste il documento e gli
# eventuali allegati in una transazione atomica (decisione 2026-05-27).


class ApiOffertaRegistraEsito(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_ESITO_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaEsitoResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: EMESSA -> ACCETTATA o RIFIUTATA. Motivazione obbligatoria su
    #        RIFIUTATA. Routing per esito gestito dal service (`registra_esito`);
    #        la view e' sottile per ridurre logica business in API layer.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        body = request.data or {}
        return success_response(
            OfferteService().registra_esito(
                offerta_id,
                esito=body.get("esito", ""),
                motivazione=body.get("motivazione"),
            )
        )


class ApiOffertaAnnulla(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_ANNULLA_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaAnnullaResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: BOZZA -> ANNULLATA. Motivazione obbligatoria. Annullamento
    #        post-EMESSA non ammesso (state machine DB).
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        body = request.data or {}
        motivazione = body.get("motivazione", "")
        return success_response(
            OfferteService().annulla(offerta_id, motivazione=motivazione)
        )


# =================================================================
# Revisioni (Step 6-7 brief DB, atterrati 2026-05-25)
# =================================================================


class ApiOffertaCreaRevisione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=None,
        responses={200: inline_serializer(
            name="VenditeOffertaCreaRevisioneResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: EMESSA -> crea rev.N+1 (BOZZA). La fn DB
    #        `fn_crea_revisione_offerta` copia testata + eccezioni attive +
    #        utility 1:1 e marca la rev.N corrente come SUPERATA via
    #        trigger AFTER INSERT. Ritorna la nuova rev.N+1.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        # Audit: username Django se autenticato (pattern progetto via
        # `is_authenticated`: `AnonymousUser` ha `username=""`, non None, e
        # `bool(request.user)` e' True per anonimi — affidarci a `request.user`
        # truthy farebbe scrivere stringa vuota in audit. La fn DB ha
        # COALESCE(p_user, CURRENT_USER) come fallback per p_user NULL.
        user = (
            request.user.username if request.user.is_authenticated else None
        )
        return success_response(
            OfferteService().crea_revisione(offerta_id, user=user)
        )


_PUSH_CONTRATTO_REQUEST = inline_serializer(
    name="VenditeOffertaPushContrattoReq",
    fields={
        # Pratica opzionale: se valorizzata, il contratto viene inserito
        # come sorgente collegata in `pratiche.pratiche_sorgenti`.
        "pratica_id": serializers.IntegerField(required=False, allow_null=True),
    },
)


class ApiOffertaPushContratto(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_PUSH_CONTRATTO_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaPushContrattoResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: ACCETTATA -> contratto DRAFT (Step 8). Idempotente per
    #        costruzione: doppia chiamata fallisce con
    #        E_OFFERTA_CONTRATTO_GIA_GENERATO. Ritorna id+numero+uid del
    #        contratto DRAFT generato — il FE puo' navigare al
    #        `ContrattoDrawer` via `contratto_id`.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        body = request.data or {}
        pratica_id_raw = body.get("pratica_id")
        pratica_id: int | None = None
        if pratica_id_raw is not None:
            # Coercion lato view per accettare sia `7` (int) sia `"7"` (string,
            # ad es. da QSearchParams o body urlencoded). Conversione errata ->
            # ServiceError 400 strutturato (no ValueError raw: bypasserebbe
            # l'error envelope del middleware).
            try:
                pratica_id = int(pratica_id_raw)
            except (TypeError, ValueError) as exc:
                from apps.core.services.error_manager import ErrorManager
                ErrorManager.raise_error(
                    code="E_VENDITE_VALIDATION",
                    message="pratica_id non valido.",
                    detail=f"atteso intero positivo, ricevuto {pratica_id_raw!r}",
                    context={"pratica_id": pratica_id_raw},
                    cause=exc,
                )
        return success_response(
            OfferteService().push_a_contratto(
                offerta_id, pratica_id=pratica_id
            )
        )


class ApiOffertaRevisioni(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaRevisioniListResp",
            fields={"data": serializers.ListField()},
        )},
    )
    # Scopo: Lista catena revisioni che condividono il root (rev.1) con
    #        l'offerta passata. Output ordinato per `revisione_numero`.
    #        Lettura libera in ogni stato.
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        return success_response(OfferteService().list_revisioni(offerta_id))


# =================================================================
# Eccezioni
# =================================================================


class ApiOffertaEccezioni(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaEccezioniListResp",
            fields={"data": serializers.ListField()},
        )},
    )
    # Scopo: Lista eccezioni di un'offerta (lettura libera).
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        return success_response(OfferteService().list_eccezioni(offerta_id))

    @extend_schema(
        request=_ECCEZIONE_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaEccezioneCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un'eccezione (solo in BOZZA). `auth_user_id` viene passato
    # al service per risolvere l'emittente_sr_id su articolo composito
    # (precedenza emittente esplicito sulla testata > operatore loggato).
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        return success_response(
            OfferteService().crea_eccezione(
                offerta_id, request.data or {},
                auth_user_id=get_scope_user_id(request),
            )
        )


class ApiOffertaEccezioneDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_ECCEZIONE_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaEccezionePatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna un'eccezione (solo se offerta in BOZZA).
    def patch(
        self, request: Request, offerta_id: int, eccezione_id: int
    ) -> JsonResponse:
        return success_response(
            OfferteService().aggiorna_eccezione(
                offerta_id, eccezione_id, request.data or {}
            )
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaEccezioneDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cancella un'eccezione (solo se offerta in BOZZA).
    def delete(
        self, request: Request, offerta_id: int, eccezione_id: int
    ) -> JsonResponse:
        del request
        OfferteService().elimina_eccezione(offerta_id, eccezione_id)
        return success_response({"deleted": True, "eccezione_id": eccezione_id})


# =================================================================
# Componenti BoM eccezione (mirror contratti, simmetria 2026-05-26)
# =================================================================
# Pattern simmetrico contratti:
#   POST /eccezioni/preview-componenti/        -> ComponentiDialog FE pre-save
#   GET  /eccezioni/<eid>/componenti/          -> EDIT panel post-save
#   PATCH/DELETE /eccezioni/<eid>/componenti/<cid>/  -> CRUD singolo


_ECCEZIONE_PREVIEW_COMPONENTI_REQUEST = inline_serializer(
    name="VenditeOffertaEccezionePreviewComponentiReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
        "quantita": serializers.DecimalField(
            max_digits=22, decimal_places=10, required=True,
        ),
    },
)


_ECCEZIONE_COMPONENTE_PATCH_REQUEST = inline_serializer(
    name="VenditeOffertaEccezioneComponentePatchReq",
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


class ApiOffertaEccezionePreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/offerte/<id>/eccezioni/preview-componenti/

    Read-only: ritorna i componenti BoM con prezzo suggerito dal resolver
    bundle-aware per pre-popolare il ComponentiDialog FE PRIMA del save di
    una eccezione padre composita. Mirror di
    `ApiContrattoRigaPreviewComponenti`.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=_ECCEZIONE_PREVIEW_COMPONENTI_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaEccezionePreviewComponentiResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        auth_user_id = get_scope_user_id(request)

        def _handler(payload: dict[str, object]) -> list[dict[str, object]]:
            articolo_id = str(payload.get("articolo_id") or "")
            uom_raw = payload.get("uom_operativa_id")
            uom_operativa_id = int(uom_raw) if uom_raw not in (None, "") else None
            quantita = payload.get("quantita")
            return OfferteService().preview_componenti_eccezione(
                offerta_id,
                articolo_id=articolo_id,
                uom_operativa_id=uom_operativa_id,
                quantita=quantita,
                auth_user_id=auth_user_id,
            )

        return handle_post_json(request, handler=_handler)


class ApiOffertaEccezioneComponentiList(DomainAPIView):
    """GET /api/v1/vendite/offerte/<id>/eccezioni/<eid>/componenti/

    Lista componenti BoM persistiti sull'eccezione composita. Mirror di
    `ApiContrattoRigaComponentiList`. Query param `solo_attivi` default true.
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
            name="VenditeOffertaEccezioneComponentiListResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    def get(
        self, request: Request, offerta_id: int, eccezione_id: int,
    ) -> JsonResponse:
        solo_attivi_raw = request.query_params.get("solo_attivi", "true")
        solo_attivi = str(solo_attivi_raw).lower() not in ("false", "0", "no", "off")
        return success_response(
            OfferteService().list_componenti_eccezione(
                offerta_id, eccezione_id, solo_attivi=solo_attivi,
            )
        )


class ApiOffertaEccezioneComponenteDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/offerte/<id>/eccezioni/<eid>/componenti/<cid>/

    CRUD singolo componente BoM eccezione offerta. Mirror di
    `ApiContrattoRigaComponenteDetail`. Match URL anti-tampering:
    `offerta_id` + `eccezione_id` + `componente_id` devono essere coerenti.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=_ECCEZIONE_COMPONENTE_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaEccezioneComponentePatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def patch(
        self, request: Request, offerta_id: int, eccezione_id: int,
        componente_id: int,
    ) -> JsonResponse:
        return success_response(
            OfferteService().update_componente_eccezione(
                offerta_id, eccezione_id, componente_id, dict(request.data),
            )
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaEccezioneComponenteDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def delete(
        self, request: Request, offerta_id: int, eccezione_id: int,
        componente_id: int,
    ) -> JsonResponse:
        del request
        return success_response(
            OfferteService().delete_componente_eccezione(
                offerta_id, eccezione_id, componente_id,
            )
        )


# =================================================================
# Utility 1:1
# =================================================================


class ApiOffertaUtility(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaUtilityGetResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Legge il record utility 1:1 dell'offerta (None se non ancora creato).
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        return success_response(OfferteService().get_utility(offerta_id))

    @extend_schema(
        request=_UTILITY_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea record utility 1:1 (UNIQUE offerta_id). Solo in BOZZA.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        return success_response(
            OfferteService().crea_utility(offerta_id, request.data or {})
        )


class ApiOffertaUtilityDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_UTILITY_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaUtilityPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi business utility (tipo/classe utenza, param_*).
    #        Solo in BOZZA.
    def patch(
        self, request: Request, offerta_id: int, utility_id: int
    ) -> JsonResponse:
        return success_response(
            OfferteService().aggiorna_utility(
                offerta_id, utility_id, request.data or {}
            )
        )
