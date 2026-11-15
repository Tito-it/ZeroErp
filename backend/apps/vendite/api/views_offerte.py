# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.offerte_commerciali (CRUD iniziale).
#        Espone: testata + cambio stato (emetti/registra-esito/annulla) +
#        eccezioni + utility 1:1. Lo stato lo scrivono i verbi DB
#        (`fn_cambia_stato_offerta`, `fn_annulla_offerta`, brief-modello-
#        documento-vendita §13); il permesso del passaggio dalla riga della
#        matrice (`PassaggioDocumento`); il service traduce gli errori P0001
#        in ServiceError che il middleware converte in error envelope uniforme.
#
#        Stato 2026-05-25: tutti gli endpoint del ciclo offerta esposti.
#        Codice `OFC-*` automatico via trigger DB; `crea-revisione/`,
#        `revisioni/`, `push-contratto/` cablati end-to-end. Niente
#        endpoint "non ancora cablato" residuo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.permissions import PassaggioDocumento
from apps.core.api.endpoint_helpers import get_actor_user_id, get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_bool,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._riga_erogazioni_views import RigaErogazioniView
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.db.offerte_repository import TESTATA_OFFERTE, OffertaRigheListaRepository
from apps.vendite.services import offerte_service
from apps.vendite.services.offerte_service import OfferteService
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._schema_da_contratto import schema_da_contratto
from apps.vendite.api._componenti_schema import (
    COMPONENTE_PATCH_REQUEST,
    COMPONENTI_LIST_PARAMETERS,
    COMPONENTI_LIST_RESPONSE,
    PREVIEW_COMPONENTI_REQUEST,
    PREVIEW_COMPONENTI_RESPONSE,
)

# Codice lista configurabile (catalogo ui.lista_definizione id=6). Usato
# dall'export per risolvere colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_OFFERTE = "vendite.offerte"


# =================================================================
# Schemas inline per drf-spectacular
# =================================================================

# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
_UTILITY_CREATE_REQUEST = schema_da_contratto(
    "VenditeOffertaUtilityCreateReq", offerte_service.CREATE_KEYS_UTILITY,
    obbligatorie=("istanza_utility_id", "utility_id"),
)
_UTILITY_PATCH_REQUEST = schema_da_contratto(
    "VenditeOffertaUtilityPatchReq", offerte_service.UPDATE_KEYS_UTILITY,
)
# La classe, non l'istanza: una per uso (vedi views_contratti).
_UTILITY_CREATE_CLS = type(_UTILITY_CREATE_REQUEST)
_OFFERTA_CREATE_REQUEST = schema_da_contratto(
    "VenditeOffertaCreateReq", offerte_service.CREATE_KEYS_OFFERTA,
    obbligatorie=(
        "emittente_fiscale_id", "billing_account_id", "istanza_utility_id",
        "utility_id", "listino_id", "validita_dal",
    ),
    speciali={"utility": _UTILITY_CREATE_CLS(required=False, allow_null=True)},
)
_OFFERTA_PATCH_REQUEST = schema_da_contratto(
    "VenditeOffertaPatchReq", offerte_service.UPDATE_KEYS_OFFERTA,
    # La utility in modifica e' un upsert: si valida col contratto di creazione.
    speciali={"utility": _UTILITY_CREATE_CLS(required=False, allow_null=True)},
)
_ECCEZIONE_CREATE_REQUEST = schema_da_contratto(
    "VenditeOffertaEccezioneCreateReq", offerte_service.CREATE_KEYS_ECCEZIONE,
    # La fonte non e' fra le obbligatorie: l'ESCLUSIONE nasce senza (2026-10-04),
    # e sulle righe che si fatturano la riempie il trigger DB dall'erogazione.
    obbligatorie=("articolo_id", "tipo_eccezione"),
)
_ECCEZIONE_PATCH_REQUEST = schema_da_contratto(
    "VenditeOffertaEccezionePatchReq", offerte_service.UPDATE_KEYS_ECCEZIONE,
)






_ESITO_REQUEST = inline_serializer(
    name="VenditeOffertaEsitoReq",
    fields={
        # Esito cliente da EMESSA: ACCETTATA (motivazione rifiutata dal verbo,
        # E_OFFERTA_MOTIVAZIONE_NON_AMMESSA) oppure RIFIUTATA (motivazione
        # obbligatoria: lo dice la riga del passaggio, al verbo,
        # E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA). Le parole le dice il service
        # (`ESITI`), non una copia qui.
        "esito": serializers.ChoiceField(choices=sorted(offerte_service.ESITI)),
        "motivazione": serializers.CharField(required=False, allow_blank=True, allow_null=True),
    },
)


_ANNULLA_REQUEST = inline_serializer(
    name="VenditeOffertaAnnullaReq",
    fields={
        "motivazione": serializers.CharField(
            help_text="Obbligatoria (E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA, dalla riga del passaggio).",
        ),
        "legami_confermati": serializers.IntegerField(
            required=False, allow_null=True,
            help_text=(
                "Quanti legami si sono visti nella finestra di conferma (la revisione "
                "precedente che torna emessa). Assente al primo tentativo."
            ),
        ),
    },
)










# =================================================================
# Lista + creazione testata
# =================================================================


class ApiOfferteList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")
    is_search_endpoint = True
    lista_codice = "vendite.offerte"

    @extend_schema(
        operation_id="vendite_offerte_list",
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="BOZZA | EMESSA | ACCETTATA | RIFIUTATA | ANNULLATA | SUPERATA"),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="validita_dal_min", type=str, required=False,
                             description="Data ISO YYYY-MM-DD. Nessun default backend."),
            OpenApiParameter(name="validita_dal_max", type=str, required=False),
            OpenApiParameter(name="solo_ultima_revisione", type=bool, required=False,
                             description="Default true: solo la revisione non rimpiazzata "
                                         "per lineage (vw_offerte_commerciali_lista.is_superata "
                                         "IS FALSE). Passa false per vedere lo storico completo "
                                         "delle revisioni. ATTENZIONE: filtra sulla POSIZIONE "
                                         "nella catena, non sullo stato — le offerte ANNULLATE "
                                         "restano visibili e filtrabili per stato."),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             # Derivata dalla whitelist del repository: era un
                             # elenco scritto a mano e aveva gia' divergito.
                             description="campo_sorgente colonna catalogo 'vendite.offerte' ("
                                         + " | ".join(sorted(offerte_service._ORDER_BY_OFFERTE))
                                         + "). 'revisione_numero' non ordinabile."),
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
            billing_account_id=qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
            stato_codice_interno=qp_str(qp.get("stato_codice_interno")),
            utility_id=qp_int_optional(qp.get("utility_id"), "utility_id"),
            listino_id=qp_int_optional(qp.get("listino_id"), "listino_id"),
            validita_dal_min=qp_str(qp.get("validita_dal_min")),
            validita_dal_max=qp_str(qp.get("validita_dal_max")),
            solo_ultima_revisione=qp_bool_optional(qp.get("solo_ultima_revisione"), "solo_ultima_revisione", default=True),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            auth_user_id=get_scope_user_id(request),
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


class ApiOfferteExportView(DomainAPIView):
    """GET /api/v1/vendite/offerte/export/?formato=csv|xlsx

    Genera un file CSV o Excel con le offerte commerciali filtrate dalla query
    string (stessi parametri del list endpoint). Hard cap EXPORT_MAX_ROWS righe —
    sopra solleva E_UI_EXPORT_LIMIT_EXCEEDED (422). Usa il renderer generico
    `ListaExportService` (DEF-1) e il catalogo colonne `vendite.offerte` per
    coerenza con la DataTable a video (colonne nascoste escluse, ordine utente
    rispettato).

    NB: il parametro si chiama `formato` (italiano), NON `format` — magic
    parameter DRF (memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")
    is_search_endpoint = True
    lista_codice = "vendite.offerte"

    @extend_schema(
        operation_id="vendite_offerte_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="validita_dal_min", type=str, required=False),
            OpenApiParameter(name="validita_dal_max", type=str, required=False),
            OpenApiParameter(name="solo_ultima_revisione", type=bool, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Export CSV/XLSX della lista offerte. Riusa la coda invariante
    #        `build_export_response` (DEF-1). Filtri identici al list endpoint;
    #        fetcha fino a EXPORT_MAX_ROWS+1 per intercettare l'overflow.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data_insert")

        billing_account_id = qp_int_optional(qp.get("billing_account_id"), "billing_account_id")
        stato_codice_interno = qp_str(qp.get("stato_codice_interno"))
        utility_id = qp_int_optional(qp.get("utility_id"), "utility_id")
        listino_id = qp_int_optional(qp.get("listino_id"), "listino_id")
        validita_dal_min = qp_str(qp.get("validita_dal_min"))
        validita_dal_max = qp_str(qp.get("validita_dal_max"))
        solo_ultima_revisione = qp_bool_optional(qp.get("solo_ultima_revisione"), "solo_ultima_revisione", default=True)

        svc = OfferteService()
        results, total = svc.list_offerte(
            search=p["search"],
            billing_account_id=billing_account_id,
            stato_codice_interno=stato_codice_interno,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            solo_ultima_revisione=solo_ultima_revisione,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            # Stesso perimetro della lista: l'export e' la porta piu' larga.
            auth_user_id=get_scope_user_id(request),
        )
        filtri_applicati = svc.resolve_filtri_export_label(
            stato_codice_interno=stato_codice_interno,
            billing_account_id=billing_account_id,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            solo_ultima_revisione=solo_ultima_revisione,
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_OFFERTE,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


# =================================================================
# Dettaglio + PATCH + DELETE testata
# =================================================================


class ApiOffertaDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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
    # Scopo: Aggiorna testata offerta. Quali campi in quale stato lo decide il
    #        lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`).
    def patch(self, request: Request, offerta_id: int) -> JsonResponse:
        return success_response(
            OfferteService().aggiorna_offerta(offerta_id, corpo_oggetto(request))
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
    model_permission = ("vendite", "offerta_commerciale")
    # L'azione del passaggio (stato corrente -> `esito`) dalla riga della
    # matrice, la stessa che legge il verbo: oggi accetta e rifiuta non ne
    # hanno, e decide il livello sul documento (M-3, guida §6; §13.6 punto 5).
    # Il permesso guarda la riga verso lo stato che il verbo scrive (dal
    # vocabolario, per il ruolo dell'esito), non verso la parola dell'API.
    post_passaggio = PassaggioDocumento(
        testata=TESTATA_OFFERTE, documento_kwarg="offerta_id", campo_stato="esito",
        stato_del_campo=offerte_service.RUOLO_DEGLI_ESITI,
    )

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
        body = corpo_oggetto(request)
        return success_response(
            OfferteService().registra_esito(
                offerta_id,
                esito=body.get("esito", ""),
                motivazione=body.get("motivazione"),
            )
        )


class ApiOffertaAnnulla(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")
    # L'azione dalla riga del passaggio verso lo stato d'annullo, chiesto al
    # vocabolario a ogni richiesta: l'annullo dell'accettata chiede
    # `emetti_offerta`, quello della bozza il solo livello sul documento
    # (M-3, M-4; §13.6 punto 5).
    post_passaggio = PassaggioDocumento(
        testata=TESTATA_OFFERTE, documento_kwarg="offerta_id", stato_del_modello="annullo",
    )

    @extend_schema(
        request=_ANNULLA_REQUEST,
        responses={200: inline_serializer(
            name="VenditeOffertaAnnullaResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: -> ANNULLATA, da BOZZA o da ACCETTATA, dal verbo
    #        `vendite.fn_annulla_offerta`. Motivazione obbligatoria (la dice il
    #        DB). Da quali stati e a quali condizioni lo dice il DB (transizioni
    #        e guard: da ACCETTATA, nessun contratto o ordine vivo a valle).
    #        L'annullo di una revisione che riapre la precedente si conferma:
    #        il primo tentativo risponde E_DOC_ANNULLO_CON_LEGAMI
    #        (`confirm_and_retry`), il secondo dichiara `legami_confermati`.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        body = corpo_oggetto(request)
        return success_response(
            OfferteService().annulla(
                offerta_id,
                motivazione=body.get("motivazione"),
                legami_confermati=body.get("legami_confermati"),
            )
        )


# =================================================================
# Revisioni (Step 6-7 brief DB, atterrati 2026-05-25)
# =================================================================


class ApiOffertaCreaRevisione(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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


class ApiOffertaGeneraOrdine(DomainAPIView):
    """`POST /api/v1/vendite/offerte/<id>/genera-ordine/` (conversione §7.4)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

    @extend_schema(
        request=None,
        responses={200: inline_serializer(
            name="VenditeOffertaGeneraOrdineResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera un ordine DRAFT da un'offerta ACCETTATA: il verbo DB
    #        `vendite.fn_genera_ordine_da_offerta` (testata, provenienza, righe
    #        espanse coi prezzi negoziati, componenti BoM), via ordini_service.
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        from apps.vendite.services import ordini_service

        return success_response(
            ordini_service.crea_ordine_da_offerta(offerta_id)
        )


_PUSH_CONTRATTO_REQUEST = inline_serializer(
    name="VenditeOffertaPushContrattoReq",
    fields={
        # Pratica opzionale: se valorizzata, il contratto viene inserito
        # come sorgente collegata in `pratiche.pratiche_sorgenti`.
        "pratica_id": serializers.IntegerField(required=False, allow_null=True),
        # Successione su overlap: se True e c'e' un contratto sovrapposto,
        # lo chiude (valido_al = nuovo valido_dal - 1) e crea il nuovo;
        # se False (default), su overlap fallisce con
        # E_CONTRATTO_OVERLAP_ESISTENTE (il FE mostra il contratto in
        # conflitto e richiama con chiudi_esistente=true su conferma).
        "chiudi_esistente": serializers.BooleanField(required=False, default=False),
    },
)


class ApiOffertaPushContratto(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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
    #
    #        Successione su overlap: `chiudi_esistente=true` chiude il
    #        contratto sovrapposto e crea il nuovo; default false fallisce
    #        con E_CONTRATTO_OVERLAP_ESISTENTE (vedi
    #        ApiOffertaContrattoSovrapposto per il preview del conflitto).
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        body = corpo_oggetto(request)
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
        # ⛔ Dal BB, non `bool(...)`: `bool("false")` e' True, e la successione
        #    CHIUDE il contratto esistente. Un non-booleano e' un 400.
        chiudi_esistente = optional_bool(body, "chiudi_esistente", default=False)
        return success_response(
            OfferteService().push_a_contratto(
                offerta_id,
                pratica_id=pratica_id,
                chiudi_esistente=chiudi_esistente,
            )
        )


class ApiOffertaContrattoSovrapposto(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeOffertaContrattoSovrappostoResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Ritorna il contratto attivo sovrapposto a quello generabile
    #        dall'offerta (o null). Read-only: alimenta il dialog FE di
    #        successione dopo che il push ha restituito
    #        E_CONTRATTO_OVERLAP_ESISTENTE. Risposta: { contratto: {...}|null }.
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        del request
        contratto = OfferteService().get_contratto_sovrapposto(offerta_id)
        return success_response({"contratto": contratto})


class ApiOffertaRevisioni(DomainAPIView):
    area_funzionale = "vendite"
    # Come la gemella `ApiPreventivoRevisioniList`: l'override d'OGGETTO
    # dell'operatore conta anche qui (senza, si risale solo all'area). Stesso
    # nome di modello delle note dell'offerta (`note_views`).
    model_permission = ("vendite", "offerta_commerciale")
    lista_codice = "vendite.offerta_revisioni"
    # ⭐ Il tab vive DENTRO il drawer di un'offerta, che ha gia' il suo
    #    emittente: la lista a catalogo e' `perimetro_emittente = t` e
    #    `multi_emittente = f`, quindi senza questa riga chi vede piu'
    #    emittenti (il super admin su «Tutti») riceverebbe
    #    E_UI_LISTA_EMITTENTE_DA_SCEGLIERE a drawer gia' aperto. PK
    #    (`emittenti_fiscali.id`), come `v.emittente_fiscale_id`.
    lista_emittente_param = "emittente_fiscale_id"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, required=False,
                description=(
                    "Emittente del documento (PK). Lo legge SOLO il cancello di "
                    "perimetro, per chi vede più emittenti: non filtra le righe "
                    "(la catena è di un emittente solo) e non allarga niente — "
                    "la visibilità resta allo scope e alla RLS."
                ),
            ),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="revisione_numero (default) | data_emissione"),
            OpenApiParameter(name="order_dir", type=str, required=False,
                             description="asc | desc (assente: asc; desc sulle date)"),
        ],
        responses={200: inline_serializer(
            name="VenditeOffertaRevisioniListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista PAGINATA della catena revisioni che condividono la radice
    #        (rev.1) con l'offerta passata, default `revisione_numero` ASC.
    #        Mirror di `ApiPreventivoRevisioniList`. Lettura libera in ogni stato.
    def get(self, request: Request, offerta_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="revisione_numero")
        results, total = OfferteService().list_revisioni(
            offerta_id,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


# =================================================================
# Righe: la lista configurabile `vendite.offerta_righe` (106)
# =================================================================
# Pagina ed export dal factory condiviso `build_lista_figlia_views`, come le
# righe del contratto (brief-db-righe-esclusione-solo-non-si-vende §8.1). La
# closure legge il global di modulo a call-time: i patch dei test sul service
# restano validi.
# ⚠️ `GET …/eccezioni/` resta la lettura delle eccezioni SCRITTE (e il POST di
#    creazione): la lista e' su `…/righe/lista/`, e legge le righe OPERATIVE
#    (listino + eccezioni) dalla funzione, coi verbi del DB.
_OffertaRigheLista, _OffertaRigheListaExport = build_lista_figlia_views(
    schema_prefix="OffertaRighe",
    operation_id="vendite_offerte_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="offerta_id",
    model_permission=("vendite", "offerta_commerciale"),
    pagina_call=lambda documento_id, **kw: OfferteService().list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=OffertaRigheListaRepository.righe_colonne_ordinabili(),
    ordine_assente=OffertaRigheListaRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiOffertaRigheListaView(_OffertaRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.offerta_righe"


class ApiOffertaRigheListaExportView(_OffertaRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.offerta_righe"


# =================================================================
# Eccezioni
# =================================================================


class ApiOffertaEccezioni(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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
                offerta_id, corpo_oggetto(request),
                auth_user_id=get_actor_user_id(request),
            )
        )


class ApiOffertaEccezioneDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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
                offerta_id, eccezione_id, corpo_oggetto(request),
                auth_user_id=get_actor_user_id(request),
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


class ApiOffertaRigaErogazioni(RigaErogazioniView):
    """GET /api/v1/vendite/offerte/<id>/righe/erogazioni/?articolo_id=<uuid>

    Come si puo' erogare l'articolo su una riga dell'offerta: le combinazioni
    ammesse col default in testa (base `RigaErogazioniView`, gemella del
    contratto).
    """

    model_permission = ("vendite", "offerta_commerciale")
    url_kwarg = "offerta_id"

    # Scopo: le combinazioni dal service dell'offerta.
    def elenco(self, documento_id: int, articolo_id: Any) -> list[dict[str, Any]]:
        return OfferteService().list_erogazioni_riga(documento_id, articolo_id)


class ApiOffertaEccezionePreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/offerte/<id>/eccezioni/preview-componenti/

    Read-only: ritorna i componenti BoM con prezzo suggerito dal resolver
    bundle-aware per pre-popolare il ComponentiDialog FE PRIMA del save di
    una eccezione padre composita. Mirror di
    `ApiContrattoRigaPreviewComponenti`.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=PREVIEW_COMPONENTI_REQUEST,
        responses={200: PREVIEW_COMPONENTI_RESPONSE},
    )
    def post(self, request: Request, offerta_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> list[dict[str, Any]]:
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
    model_permission = ("vendite", "offerta_commerciale")

    @extend_schema(
        parameters=COMPONENTI_LIST_PARAMETERS,
        responses={200: COMPONENTI_LIST_RESPONSE},
    )
    def get(
        self, request: Request, offerta_id: int, eccezione_id: int,
    ) -> JsonResponse:
        # Il BB dei flag di trasporto (§A6), come i gemelli DDT e ordini.
        solo_attivi = qp_bool_optional(request.query_params.get("solo_attivi"), "solo_attivi", default=True)
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
    model_permission = ("vendite", "offerta_commerciale")

    @extend_schema(
        request=COMPONENTE_PATCH_REQUEST,
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
                offerta_id, eccezione_id, componente_id, corpo_oggetto(request),
                auth_user_id=get_actor_user_id(request),
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
    model_permission = ("vendite", "offerta_commerciale")

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
            OfferteService().crea_utility(offerta_id, corpo_oggetto(request))
        )


class ApiOffertaUtilityDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

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
                offerta_id, utility_id, corpo_oggetto(request)
            )
        )


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Offerta",
    url_kwarg="offerta_id",
    list_call=lambda offerta_id: offerte_service.list_indirizzi(offerta_id),
    upsert_call=lambda offerta_id, payload: offerte_service.upsert_indirizzo(
        offerta_id, payload),
    delete_call=lambda offerta_id, indirizzo_id: offerte_service.delete_indirizzo(
        offerta_id, indirizzo_id),
    model_permission=("vendite", "offerta_commerciale"),
)
ApiOffertaIndirizzi = _indirizzi_views.lista
ApiOffertaIndirizzoDetail = _indirizzi_views.detail
