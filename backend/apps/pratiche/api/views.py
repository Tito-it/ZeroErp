# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: APIView modulo pratiche — endpoint REST per pratiche, flussi,
#        giornale, prerequisiti, canali e generazione cross-pratica.
# ------------------------------------------------------------

from typing import Any
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI, MAX_LIMIT
from apps.core.api.base_views import DomainAPIView

from apps.core.api.endpoint_helpers import get_risorsa_umana_id, handle_post_json
from apps.core.api.payload_validators import (
    pagina_da_query,
    optional_bool,
    optional_istante,
    qp_iso_date_optional,
    corpo_oggetto,
    optional_int,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_strict,
    qp_str,
)
from apps.core.api.openapi_params import descrizione_order_by, param_ricerca_full
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.pratiche.db.pratiche_repository import FLUSSI_ORDER_COLS, PraticheRepository
from apps.pratiche.services import generazione_service, pratiche_service


# ⛔ I campi obbligatori del corpo si leggono dal BB, non con `payload["x"]`:
#    un campo assente era un KeyError, cioe' un 500 `E_GENERICO`, per un errore
#    di chi chiama (2026-10-20). Il codice e' quello che ogni pagina documenta.
_V_PRATICA = PayloadValidator(validation_code="E_PRATICA_VALIDATION")
_V_FLUSSO = PayloadValidator(validation_code="E_FLUSSO_VALIDATION")
_V_ID = PayloadValidator(validation_code="E_INVALID_ID")


# Alias locale: la verifica ownership flusso-pratica e' centralizzata nel service.
_get_flusso_verificato = pratiche_service.verifica_flusso_pratica


# ================================================================== #
# Pratiche — lista, dettaglio, creazione, aggiornamento               #
# ================================================================== #


class ApiPraticheList(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    is_search_endpoint = True
    lista_codice = "pratiche.pratiche"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=True, description="ID emittente fiscale (obbligatorio)."),
            OpenApiParameter(name="stato", type=str, required=False, description="Filtro codice_interno stato pratica."),
            OpenApiParameter(name="tipo_prestazione_id", type=int, required=False, description="Filtro tipo prestazione."),
            OpenApiParameter(name="soggetto_id", type=str, required=False, description="Filtro UUID soggetto."),
            OpenApiParameter(name="soggetto_ruolo_id", type=int, required=False, description="Lente contesto: pratiche del ruolo soggetto (esclusiva con istanza/interne)."),
            OpenApiParameter(name="istanza_utility_id", type=int, required=False, description="Lente contesto: pratiche dell'istanza utility (esclusiva con ruolo/interne)."),
            OpenApiParameter(name="solo_interne", type=bool, required=False, description="Lente contesto: solo pratiche interne, senza soggetto (esclusiva con ruolo/istanza)."),
            OpenApiParameter(name="priorita_id", type=int, required=False, description="Filtro priorita' pratica."),
            OpenApiParameter(name="risorsa_umana_id", type=int, required=False, description="Filtro operatore assegnato."),
            OpenApiParameter(name="limit", type=int, required=False, description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT})."),
            OpenApiParameter(name="offset", type=int, required=False, description="Offset paginazione (default 0)."),
        ],
        responses={200: inline_serializer(
            name="PraticheListResponse",
            fields={
                "data": inline_serializer(name="PraticheListData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato delle pratiche con filtri.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        emittente_fiscale_id = qp_int_strict(qp.get("emittente_fiscale_id"), "emittente_fiscale_id", default=0)
        ErrorManager.require(
            emittente_fiscale_id > 0,
            code="E_PRATICA_VALIDATION",
            message="emittente_fiscale_id obbligatorio",
        )

        p = parse_list_params(qp, default_order="data_insert")
        stato = qp_str(qp.get("stato"))
        tipo_prestazione_id = optional_int({"v": qp.get("tipo_prestazione_id")}, "v")
        soggetto_id = qp_str(qp.get("soggetto_id"))
        # Lente di contesto canonica (D1): mutua esclusivita' validata nel
        # service (codice catalogo DB 484).
        soggetto_ruolo_id = optional_int({"v": qp.get("soggetto_ruolo_id")}, "v")
        istanza_utility_id = optional_int({"v": qp.get("istanza_utility_id")}, "v")
        solo_interne = qp_bool_optional(qp.get("solo_interne"), "solo_interne") or False
        # Fix 2026-06-12: la dashboard inviava priorita_id/risorsa_umana_id da
        # sempre, ma la view non li leggeva (filtri silenziosamente ignorati).
        priorita_id = optional_int({"v": qp.get("priorita_id")}, "v")
        risorsa_umana_id = optional_int({"v": qp.get("risorsa_umana_id")}, "v")
        data_da = qp_iso_date_optional(qp.get("data_da"), "data_da")
        data_a = qp_iso_date_optional(qp.get("data_a"), "data_a")

        items, total = pratiche_service.cerca_pratiche(
            emittente_fiscale_id=emittente_fiscale_id,
            stato_codice_interno=stato,
            tipo_prestazione_id=tipo_prestazione_id,
            soggetto_id=soggetto_id,
            soggetto_ruolo_id=soggetto_ruolo_id,
            istanza_utility_id=istanza_utility_id,
            solo_interne=solo_interne,
            priorita_id=priorita_id,
            risorsa_umana_id=risorsa_umana_id,
            search=p["search"],
            data_da=data_da,
            data_a=data_a,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(items, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="PraticheCreateRequest",
            fields={
                "emittente_fiscale_id": serializers.IntegerField(),
                "tipo_prestazione_id": serializers.IntegerField(),
                "priorita_id": serializers.IntegerField(required=False, allow_null=True),
                "soggetto_id": serializers.UUIDField(required=False, allow_null=True),
                "soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
                "istanza_utility_id": serializers.IntegerField(required=False, allow_null=True),
                "billing_account_id": serializers.IntegerField(
                    required=False, allow_null=True,
                    help_text=(
                        "Il cliente di cui parla la pratica (ruolo CLIENTE). Deve essere "
                        "del soggetto_ruolo_id; con il solo BA l'istanza e' la sua."
                    ),
                ),
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
                "canale_origine_id": serializers.IntegerField(required=False, allow_null=True),
                "descrizione": serializers.CharField(required=False, allow_null=True),
                "data_scadenza": serializers.DateField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PraticheCreateResponse",
            fields={"data": inline_serializer(name="PraticheCreateData", fields={
                "pratica_id": serializers.IntegerField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per creare una nuova pratica.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratica_id = pratiche_service.crea_pratica(
                emittente_fiscale_id=_V_PRATICA.require_positive_int(payload, "emittente_fiscale_id"),
                tipo_prestazione_id=_V_PRATICA.require_positive_int(payload, "tipo_prestazione_id"),
                # Opzionale: assente -> default NORMALE risolto dal service.
                priorita_id=optional_int(payload, "priorita_id"),
                soggetto_id=str(payload["soggetto_id"]) if payload.get("soggetto_id") else None,
                soggetto_ruolo_id=optional_int(payload, "soggetto_ruolo_id"),
                istanza_utility_id=optional_int(payload, "istanza_utility_id"),
                # Il cliente a grana fine (D-9): con il solo BA l'istanza e' la sua.
                billing_account_id=optional_int(payload, "billing_account_id"),
                risorsa_umana_id=optional_int(payload, "risorsa_umana_id"),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                canale_origine_id=optional_int(payload, "canale_origine_id"),
                descrizione=payload.get("descrizione"),
                data_scadenza=payload.get("data_scadenza"),
                meta=payload.get("meta"),
            )
            return {"pratica_id": pratica_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaDetail(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET il dettaglio di una pratica.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        repo = PraticheRepository()
        pratica = repo.get_pratica(pratica_id)
        ErrorManager.require(
            pratica is not None,
            code="E_PRATICA_NOT_FOUND",
            message=f"Pratica {pratica_id} non trovata",
        )
        assert pratica is not None
        return success_response(pratica)

    @extend_schema(
        request=inline_serializer(
            name="PraticaUpdateRequest",
            fields={
                "descrizione": serializers.CharField(required=False, allow_null=True),
                "data_scadenza": serializers.DateField(required=False, allow_null=True),
                "soggetto_id": serializers.UUIDField(required=False, allow_null=True),
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PraticaUpdateResponse",
            fields={"data": inline_serializer(name="PraticaUpdateData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP PATCH per aggiornare una pratica.
    def patch(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.aggiorna_pratica(pratica_id, dict(payload))
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Pratiche — stato e assegnazione                                     #
# ================================================================== #


class ApiPraticaStato(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_pratica"
    @extend_schema(
        request=inline_serializer(
            name="PraticaStatoRequest",
            fields={"nuovo_stato": serializers.CharField()},
        ),
        responses={200: inline_serializer(
            name="PraticaStatoResponse",
            fields={"data": inline_serializer(name="PraticaStatoData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per cambiare stato pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.cambia_stato_pratica(
                pratica_id, _V_PRATICA.require_string(payload, "nuovo_stato"),
            )
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaAssegnazione(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "assegna_pratica"
    @extend_schema(
        request=inline_serializer(
            name="PraticaAssegnazioneRequest",
            fields={
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PraticaAssegnazioneResponse",
            fields={"data": inline_serializer(name="PraticaAssegnazioneData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per assegnare una pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.assegna_pratica(
                pratica_id,
                risorsa_umana_id=optional_int(payload, "risorsa_umana_id"),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
            )
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Giornale                                                            #
# ================================================================== #


class ApiPraticaGiornale(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False, description=f"Righe per pagina (default {DEFAULT_LIMIT_EVENTI}, max {MAX_LIMIT})."),
            OpenApiParameter(name="offset", type=int, required=False, description="Offset paginazione (default 0)."),
        ],
        responses={200: inline_serializer(
            name="PraticaGiornaleResponse",
            fields={
                "data": inline_serializer(name="PraticaGiornaleData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET il giornale di bordo della pratica (con tx_id).
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp, default_limit=DEFAULT_LIMIT_EVENTI)

        items, total = pratiche_service.get_giornale(pratica_id, limit=limit, offset=offset)
        return success_response({"count": total, "results": items})




# ================================================================== #
# Flussi — lista, dettaglio, creazione, stato                         #
# ================================================================== #


class ApiPraticaPercorso(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaPercorsoResponse",
            fields={
                "data": inline_serializer(name="PraticaPercorsoData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Percorso suggerito della pratica (template_flussi + stato di
    # istanziazione di ciascuno) per la roadmap FE.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        return success_response({"results": pratiche_service.get_percorso(pratica_id)})


class ApiPraticaFlussiList(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    is_search_endpoint = True
    lista_codice = "pratiche.flussi"
    # ⭐ Il tab «Flussi» vive DENTRO il drawer di una pratica, e una pratica ha
    #    UN emittente: e' la richiesta a fissarlo (`emittente_fiscale_id`, la
    #    PK — lo stesso nome del filtro della lista pratiche). Senza questa
    #    riga il cancello rifiuterebbe (422) chi ha piu' emittenti nello scope,
    #    chiedendogli di scegliere l'emittente di una pratica gia' aperta: la
    #    lista NON e' certificata `multi_emittente` (nessuna colonna dice di
    #    quale emittente e' la riga) — brief-db-liste-datatable-grezze §4.1.
    # ⚠️ Il parametro scioglie SOLO l'ambiguita' della schermata: le righe le
    #    decide la pratica nel path, sotto la sua RLS. Non e' un filtro.
    lista_emittente_param = "emittente_fiscale_id"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, required=False,
                description=(
                    "Emittente (PK) della pratica aperta: scioglie il cancello di "
                    "perimetro per chi ha piu' emittenti nello scope. Non filtra."
                ),
            ),
            OpenApiParameter(name="limit", type=int, required=False, description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT})."),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description=descrizione_order_by(FLUSSI_ORDER_COLS, "Default: sequenza."),
            ),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="PraticaFlussiListResponse",
            fields={
                "data": inline_serializer(name="PraticaFlussiListData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: la lista `pratiche.flussi` di una pratica — paginata, ordinabile
    #        sulla whitelist, con la ricerca del catalogo. L'ordine di partenza
    #        e' la posizione del flusso nella pratica (`sequenza`).
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="sequenza")
        results, total = PraticheRepository().list_flussi_pagina(
            pratica_id,
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="FlussoCreateRequest",
            fields={
                "template_flusso_id": serializers.IntegerField(required=True, allow_null=False),
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
                "sequenza": serializers.IntegerField(required=False),
                "data_scadenza": serializers.DateField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="FlussoCreateResponse",
            fields={"data": inline_serializer(name="FlussoCreateData", fields={
                "flusso_id": serializers.IntegerField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per creare un flusso.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            flusso_id = pratiche_service.crea_flusso(
                pratica_id=pratica_id,
                # Obbligatorio (workflow v2): il service fa il guard fail-fast
                # E_FLUSSO_VALIDATION se assente/non valido. optional_int tollera
                # il missing → None, che il guard del service rifiuta.
                template_flusso_id=optional_int(payload, "template_flusso_id"),  # type: ignore[arg-type]
                risorsa_umana_id=optional_int(payload, "risorsa_umana_id"),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                sequenza=int(payload.get("sequenza", 0)),
                data_scadenza=payload.get("data_scadenza"),
                meta=payload.get("meta"),
            )
            return {"flusso_id": flusso_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaFlussoDetail(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET il dettaglio di un flusso.
    def get(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        repo = PraticheRepository()
        flusso = _get_flusso_verificato(repo, pratica_id, flusso_id)
        return success_response(flusso)




class ApiFlussoPratica(DomainAPIView):
    """`GET /api/v1/pratiche/flussi/<flusso_id>/pratica/` — dove vive un flusso.

    ⭐ L'unica rotta dei flussi NON annidata sotto la pratica, e serve a chi il
    flusso lo nomina **da fuori**: il primo caso reale e' il BERSAGLIO di un
    errore (`E_FLUSSI_*`, roll-out del 2026-08-24), che porta l'id del flusso e
    nient'altro. La dashboard, senza `pratica_id`, non saprebbe dove aprirlo.

    ⚠️ Risponde un id, non il flusso: il dettaglio resta uno solo, con la sua
    verifica di appartenenza. Vedi `pratiche_service.pratica_di_flusso`.
    """

    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoPraticaResponse",
            fields={"data": inline_serializer(
                name="FlussoPraticaData",
                fields={"pratica_id": serializers.IntegerField()},
            )},
        )},
    )
    # Scopo: Restituisce l'id della pratica a cui il flusso appartiene.
    def get(self, request: Request, flusso_id: int) -> JsonResponse:
        return success_response(
            {"pratica_id": pratiche_service.pratica_di_flusso(flusso_id)}
        )


class ApiPraticaFlussoStato(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_flusso"
    @extend_schema(
        request=inline_serializer(
            name="FlussoStatoRequest",
            fields={
                "nuovo_stato": serializers.CharField(),
                "esito": serializers.CharField(required=False, allow_null=True),
                "note_esito": serializers.CharField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="FlussoStatoResponse",
            fields={"data": inline_serializer(name="FlussoStatoData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per cambiare stato flusso.
    # Obiettivo: gestisce sia avvio (IN_CORSO) che completamento (COMPLETATO con esito).
    def post(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        # Verifica ownership flusso-pratica prima di procedere; ne riusa lo stato
        # corrente per instradare il completamento (CONTESTUALE da DA_ESEGUIRE).
        repo = PraticheRepository()
        flusso = _get_flusso_verificato(repo, pratica_id, flusso_id)
        stato_corrente = (flusso or {}).get("stato_codice_interno")

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            nuovo_stato = _V_FLUSSO.require_string(payload, "nuovo_stato")
            if nuovo_stato == "COMPLETATO":
                ErrorManager.require(
                    "esito" in payload and payload["esito"],
                    code="E_FLUSSO_VALIDATION",
                    message="esito obbligatorio per completamento flusso",
                    context={"field": "esito"},
                )
                # L'esito arriva dall'operatore: gli esiti di ramo (calcolati
                # dal dominio, es. bivio SMISTAMENTO, is_verdetto=false) non
                # sono selezionabili a mano — errore parlante prima di toccare
                # il flusso. Riusa il repo dell'ownership check.
                pratiche_service.require_esito_selezionabile_operatore(
                    str(payload["esito"]), repo=repo,
                )
                # Guard simmetrico: uno step il cui esito e' CALCOLATO dal dominio
                # (modalita_esito = DOMINIO, es. SMISTAMENTO) non si completa dal
                # percorso operatore — va chiuso dall'azione di dominio dedicata
                # (completa_smistamento). Errore parlante prima del guard DB (id 504).
                pratiche_service.require_completamento_operatore_ammesso(
                    flusso_id, repo=repo,
                )
                acting_user = getattr(request.user, "username", None) or None
                # Contesto d'azione opzionale (es. modalita/competenza di
                # fatturazione all'accettazione): inoltrato agli handler di
                # completamento, non persistito sul flusso.
                meta_raw = payload.get("meta")
                meta = meta_raw if isinstance(meta_raw, dict) else None
                if stato_corrente == "DA_ESEGUIRE":
                    # Modalita CONTESTUALE: avvio + esito in un'unica azione
                    # (DA_ESEGUIRE → IN_CORSO → COMPLETATO, stessa tx).
                    pratiche_service.avvia_e_completa_flusso(
                        flusso_id,
                        esito=str(payload["esito"]),
                        note_esito=payload.get("note_esito"),
                        user=acting_user,
                        meta=meta,
                    )
                else:
                    pratiche_service.completa_flusso(
                        flusso_id,
                        esito=str(payload["esito"]),
                        note_esito=payload.get("note_esito"),
                        # user acting (p_user): inoltrato agli handler di completamento
                        # (es. post_smistamento) per audit nelle fn DB di dominio.
                        user=acting_user,
                        meta=meta,
                    )
            elif nuovo_stato == "IN_CORSO":
                # user acting (p_user §8.5): username se disponibile, altrimenti
                # None → le fn DB ricadono su CURRENT_USER.
                pratiche_service.avvia_flusso(
                    flusso_id,
                    user=getattr(request.user, "username", None) or None,
                )
            else:
                # Transizione generica via service (wrappata in @transaction.atomic).
                pratiche_service.cambia_stato_flusso(flusso_id, nuovo_stato)
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Prerequisiti e canali                                               #
# ================================================================== #


class ApiPraticaFlussoPrerequisiti(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoPrerequisitiResponse",
            fields={
                "data": inline_serializer(name="FlussoPrerequisitiData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET i prerequisiti del template flusso con flag soddisfatto.
    def get(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        repo = PraticheRepository()
        flusso = _get_flusso_verificato(repo, pratica_id, flusso_id)
        if flusso["template_flusso_id"] is None:
            return success_response({"results": []})

        risultati = pratiche_service.verifica_prerequisiti(pratica_id, flusso["template_flusso_id"])
        return success_response({"results": risultati})




class ApiPraticaFlussoCanali(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoCanaliResponse",
            fields={
                "data": inline_serializer(name="FlussoCanaliData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET i canali abilitati per il template del flusso.
    def get(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        repo = PraticheRepository()
        flusso = _get_flusso_verificato(repo, pratica_id, flusso_id)
        if flusso["template_flusso_id"] is None:
            return success_response({"results": []})

        canali = pratiche_service.get_canali_disponibili(flusso["template_flusso_id"])
        return success_response({"results": canali})




# ================================================================== #
# Generazione cross-pratica                                           #
# ================================================================== #


class ApiPraticaFlussoRegoleGenerazione(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoRegoleGenerazioneResponse",
            fields={
                "data": inline_serializer(name="FlussoRegoleGenerazioneData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET le regole di generazione applicabili al flusso.
    def get(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        repo = PraticheRepository()
        _get_flusso_verificato(repo, pratica_id, flusso_id)
        regole = generazione_service.get_regole_applicabili(flusso_id)
        return success_response({"results": regole})




class ApiPraticaFlussoGenera(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "genera_pratica_manuale"
    @extend_schema(
        request=inline_serializer(
            name="FlussoGeneraRequest",
            fields={"regola_id": serializers.IntegerField()},
        ),
        responses={200: inline_serializer(
            name="FlussoGeneraResponse",
            fields={"data": inline_serializer(name="FlussoGeneraData", fields={
                "pratica_id": serializers.IntegerField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per generazione manuale pratica.
    def post(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        # Verifica ownership flusso-pratica prima di procedere.
        repo = PraticheRepository()
        _get_flusso_verificato(repo, pratica_id, flusso_id)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            nuova_pratica_id = generazione_service.genera_pratica_manuale(
                flusso_id, _V_ID.require_positive_int(payload, "regola_id"),
            )
            return {"pratica_id": nuova_pratica_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaFlussoPraticheGenerate(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoPraticheGenerateResponse",
            fields={
                "data": inline_serializer(name="FlussoPraticheGenerateData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET le pratiche generate dal flusso.
    def get(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        repo = PraticheRepository()
        _get_flusso_verificato(repo, pratica_id, flusso_id)
        pratiche = generazione_service.get_pratiche_generate(flusso_id)
        return success_response({"results": pratiche})




# ================================================================== #
# Sospensioni pratica                                                  #
# ================================================================== #


class ApiPraticaSospendi(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "sospendi_pratica"
    @extend_schema(
        request=inline_serializer(
            name="PraticaSospendiRequest",
            fields={
                "motivo": serializers.CharField(),
                # data_inizio opzionale (ISO datetime): data/ora manuale, anche
                # retroattiva. Se assente il DB usa NOW(). Difesa a DB: guard a10
                # rifiuta date future, EXCLUDE rifiuta periodi sovrapposti.
                "data_inizio": serializers.DateTimeField(required=False, allow_null=True),
                "data_riattivazione_prevista": serializers.DateField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PraticaSospendiResponse",
            fields={"data": inline_serializer(name="PraticaSospendiData", fields={
                "sospensione_id": serializers.IntegerField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per sospendere una pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            sospensione_id = pratiche_service.sospendi_pratica(
                pratica_id,
                str(payload.get("motivo", "")),
                data_riattivazione_prevista=payload.get("data_riattivazione_prevista") or None,
                data_inizio=optional_istante(payload, "data_inizio"),
            )
            return {"sospensione_id": sospensione_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaRiattiva(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "riattiva_pratica"
    @extend_schema(
        request=inline_serializer(
            name="PraticaRiattivaRequest",
            fields={
                # data_fine opzionale (ISO datetime): data/ora manuale di
                # riattivazione, anche retroattiva. Se assente il DB usa NOW().
                "data_fine": serializers.DateTimeField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PraticaRiattivaResponse",
            fields={"data": inline_serializer(name="PraticaRiattivaData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per riattivare una pratica sospesa.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.riattiva_pratica(
                pratica_id,
                data_fine=optional_istante(payload, "data_fine"),
            )
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Sospensioni flusso                                                   #
# ================================================================== #


class ApiPraticaFlussoSospendi(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "sospendi_flusso"
    @extend_schema(
        request=inline_serializer(
            name="FlussoSospendiRequest",
            fields={
                "motivo": serializers.CharField(),
                "data_riattivazione_prevista": serializers.DateField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="FlussoSospendiResponse",
            fields={"data": inline_serializer(name="FlussoSospendiData", fields={
                "sospensione_id": serializers.IntegerField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per sospendere un singolo flusso.
    def post(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            sospensione_id = pratiche_service.sospendi_flusso(
                pratica_id,
                flusso_id,
                str(payload.get("motivo", "")),
                data_riattivazione_prevista=payload.get("data_riattivazione_prevista"),
            )
            return {"sospensione_id": sospensione_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaFlussoRiattiva(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "riattiva_flusso"
    @extend_schema(
        request=inline_serializer(
            name="FlussoRiattivaRequest",
            fields={},
        ),
        responses={200: inline_serializer(
            name="FlussoRiattivaResponse",
            fields={"data": inline_serializer(name="FlussoRiattivaData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per riattivare un flusso sospeso.
    def post(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.riattiva_flusso(pratica_id, flusso_id)
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Sospensioni e calcoli tempo — lettura                                #
# ================================================================== #


class ApiPraticaSospensioni(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaSospensioniResponse",
            fields={
                "data": inline_serializer(name="PraticaSospensioniData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET le sospensioni di una pratica.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        items = pratiche_service.get_sospensioni(pratica_id)
        return success_response({"results": items})




class ApiPraticaCalcoliTempo(DomainAPIView):
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")
    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaCalcoliTempoResponse",
            fields={
                "data": inline_serializer(name="PraticaCalcoliTempoData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET i calcoli tempo di una pratica.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        items = pratiche_service.get_calcoli_tempo(pratica_id)
        return success_response({"results": items})




# ================================================================== #
# Note pratiche — CRUD                                                  #
# ================================================================== #


class ApiPraticaNoteList(DomainAPIView):
    """GET lista note pratica, POST crea nota."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaNoteListResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Lista note della pratica con tipo nota display.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        items = pratiche_service.get_note_pratica(pratica_id)
        return success_response({"results": items})

    @extend_schema(
        request=inline_serializer(name="PraticaNotaCreateReq", fields={
            "tipo_nota_codice": serializers.CharField(),
            "contenuto": serializers.CharField(),
        }),
        responses={200: inline_serializer(
            name="PraticaNotaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nota per la pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            nota_id = pratiche_service.crea_nota_pratica(
                pratica_id=pratica_id,
                tipo_nota_codice=str(payload.get("tipo_nota_codice", "")),
                contenuto=str(payload.get("contenuto", "")),
            )
            return {"nota_id": nota_id, "status": "ok"}
        return handle_post_json(request, handler=_handler)


class ApiPraticaNotaDetail(DomainAPIView):
    """PATCH aggiorna nota, DELETE elimina nota."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        request=inline_serializer(name="PraticaNotaUpdateReq", fields={
            "contenuto": serializers.CharField(),
        }),
        responses={200: inline_serializer(
            name="PraticaNotaUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna il contenuto di una nota.
    def patch(self, request: Request, pratica_id: int, nota_id: int) -> JsonResponse:
        pratiche_service.aggiorna_nota_pratica(
            nota_id=nota_id,
            pratica_id=pratica_id,
            contenuto=str(corpo_oggetto(request).get("contenuto", "")),
        )
        return success_response({"updated": True})

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaNotaDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina una nota.
    def delete(self, request: Request, pratica_id: int, nota_id: int) -> JsonResponse:
        pratiche_service.elimina_nota_pratica(nota_id=nota_id, pratica_id=pratica_id)
        return success_response({"deleted": True})


# ================================================================== #
# Allegati pratiche — CRUD (senza upload file)                          #
# ================================================================== #


class ApiPraticaAllegatiList(DomainAPIView):
    """GET lista allegati pratica, POST crea record allegato."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaAllegatiListResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Lista allegati della pratica con tipo allegato display.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        items = pratiche_service.get_allegati_pratica(pratica_id)
        return success_response({"results": items})

    @extend_schema(
        request=inline_serializer(name="PraticaAllegatoCreateReq", fields={
            "tipo_allegato_codice": serializers.CharField(),
            "nome_file": serializers.CharField(),
            "percorso": serializers.CharField(required=False),
            "mime_type": serializers.CharField(required=False),
            "dimensione": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="PraticaAllegatoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un record allegato (metadati, senza upload file).
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            allegato_id = pratiche_service.crea_allegato_pratica(
                pratica_id=pratica_id,
                tipo_allegato_codice=str(payload.get("tipo_allegato_codice", "")),
                nome_file=str(payload.get("nome_file", "")),
                percorso=payload.get("percorso"),
                mime_type=payload.get("mime_type"),
                dimensione=optional_int(payload, "dimensione"),
            )
            return {"allegato_id": allegato_id, "status": "ok"}
        return handle_post_json(request, handler=_handler)


class ApiPraticaAllegatoDetail(DomainAPIView):
    """DELETE elimina allegato (allegati immutabili — no PATCH)."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaAllegatoDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina un allegato.
    def delete(self, request: Request, pratica_id: int, allegato_id: int) -> JsonResponse:
        pratiche_service.elimina_allegato_pratica(allegato_id=allegato_id, pratica_id=pratica_id)
        return success_response({"deleted": True})


# ================================================================== #
# Coda lavoro operatore                                                #
# ================================================================== #


class ApiCodaLavoro(DomainAPIView):
    """GET coda lavoro dell'operatore corrente su tre livelli."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=True, description="ID emittente fiscale (obbligatorio)."),
        ],
        responses={200: inline_serializer(
            name="CodaLavoroResponse",
            fields={
                "data": inline_serializer(name="CodaLavoroData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET la coda di lavoro dell'operatore autenticato.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        emittente_fiscale_id = qp_int_strict(qp.get("emittente_fiscale_id"), "emittente_fiscale_id", default=0)
        ErrorManager.require(
            emittente_fiscale_id > 0,
            code="E_PRATICA_VALIDATION",
            message="emittente_fiscale_id obbligatorio",
        )

        risorsa_umana_id = get_risorsa_umana_id(request)
        ErrorManager.require(
            risorsa_umana_id is not None and risorsa_umana_id > 0,
            code="E_PRATICA_VALIDATION",
            message="Operatore non associato a una risorsa umana",
        )
        assert risorsa_umana_id is not None

        items = pratiche_service.get_coda_lavoro(risorsa_umana_id, emittente_fiscale_id)
        return success_response({"results": items})


# ================================================================== #
# Prendi in carico flusso                                              #
# ================================================================== #


class ApiPrendiInCarico(DomainAPIView):
    """POST prendi in carico un flusso DA_ESEGUIRE."""
    area_funzionale = "pratiche"
    model_permission = ("pratiche", "pratica")

    @extend_schema(
        request=inline_serializer(
            name="PrendiInCaricoRequest",
            fields={},
        ),
        responses={200: inline_serializer(
            name="PrendiInCaricoResponse",
            fields={"data": inline_serializer(name="PrendiInCaricoData", fields={
                "assegnato": serializers.BooleanField(),
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per prendere in carico un flusso.
    def post(self, request: Request, flusso_id: int) -> JsonResponse:
        risorsa_umana_id = get_risorsa_umana_id(request)
        ErrorManager.require(
            risorsa_umana_id is not None and risorsa_umana_id > 0,
            code="E_PRATICA_VALIDATION",
            message="Operatore non associato a una risorsa umana",
        )
        assert risorsa_umana_id is not None

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            assegnato = pratiche_service.prendi_in_carico(flusso_id, risorsa_umana_id)
            return {"assegnato": assegnato, "status": "ok"}

        return handle_post_json(request, handler=_handler)


class ApiPraticaFlussoAssegnazione(DomainAPIView):
    """POST assegna un flusso a un operatore e/o a un reparto."""
    area_funzionale = "pratiche"
    post_permission = "assegna_pratica"

    @extend_schema(
        request=inline_serializer(
            name="FlussoAssegnazioneRequest",
            fields={
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="FlussoAssegnazioneResponse",
            fields={"data": inline_serializer(name="FlussoAssegnazioneData", fields={
                "status": serializers.CharField(),
            })},
        )},
    )
    # Scopo: Gestisce la richiesta HTTP POST per assegnare un flusso.
    # I flag set_* derivano dalla presenza della chiave nel payload: chiave
    # assente = non toccare; valore None = de-assegna (azzera).
    def post(self, request: Request, pratica_id: int, flusso_id: int) -> JsonResponse:
        # Verifica ownership flusso-pratica (E_FLUSSO_OWNERSHIP), come gli altri
        # endpoint di scrittura flusso: il flusso dell'URL deve appartenere alla
        # pratica dell'URL.
        repo = PraticheRepository()
        _get_flusso_verificato(repo, pratica_id, flusso_id)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.assegna_flusso(
                flusso_id,
                risorsa_umana_id=optional_int(payload, "risorsa_umana_id"),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                set_risorsa="risorsa_umana_id" in payload,
                set_unita="unita_organizzativa_id" in payload,
            )
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)


class ApiOperatoriReparto(DomainAPIView):
    """GET operatori (risorse umane attive) di un reparto, per il picker di assegnazione."""
    area_funzionale = "pratiche"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="unita_organizzativa_id",
                type=int,
                required=True,
                description="ID del reparto di cui elencare gli operatori attivi.",
            ),
        ],
        responses={200: inline_serializer(
            name="OperatoriRepartoResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET gli operatori attivi di un reparto.
    def get(self, request: Request) -> JsonResponse:
        unita_organizzativa_id = qp_int_strict(
            request.query_params.get("unita_organizzativa_id"),
            "unita_organizzativa_id",
            0,
        )
        items = pratiche_service.list_operatori_reparto(unita_organizzativa_id)
        return success_response({"results": items})


# ================================================================== #
# Competenze flussi — admin CRUD                                       #
# ================================================================== #


class ApiCompetenzeFlussiList(DomainAPIView):
    """GET lista competenze, POST crea competenza."""
    area_funzionale = "pratiche"

    @extend_schema(
        responses={200: inline_serializer(
            name="CompetenzeFlussiListResp",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET la matrice competenze flussi con display fields.
    def get(self, request: Request) -> JsonResponse:
        items = pratiche_service.get_competenze_flussi()
        return success_response({"results": items})

    @extend_schema(
        request=inline_serializer(name="CompetenzaFlussoCreateReq", fields={
            "template_flusso_id": serializers.IntegerField(),
            "unita_organizzativa_id": serializers.IntegerField(),
            "risorsa_umana_id": serializers.IntegerField(),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="CompetenzaFlussoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una competenza flusso (operazione admin).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            competenza_id = pratiche_service.crea_competenza_flusso(
                template_flusso_id=_V_ID.require_positive_int(payload, "template_flusso_id"),
                unita_organizzativa_id=_V_ID.require_positive_int(payload, "unita_organizzativa_id"),
                risorsa_umana_id=_V_ID.require_positive_int(payload, "risorsa_umana_id"),
                attivo=optional_bool(payload, "attivo", default=True),
            )
            return {"competenza_id": competenza_id, "status": "ok"}
        return handle_post_json(request, handler=_handler)


class ApiCompetenzaFlussoDetail(DomainAPIView):
    """DELETE elimina competenza."""
    area_funzionale = "pratiche"

    @extend_schema(
        responses={200: inline_serializer(
            name="CompetenzaFlussoDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina una competenza flusso (operazione admin).
    def delete(self, request: Request, competenza_id: int) -> JsonResponse:
        pratiche_service.elimina_competenza_flusso(competenza_id)
        return success_response({"deleted": True})


# ================================================================== #
# Formule tempo — lettura                                              #
# ================================================================== #


class ApiFormuleTempo(DomainAPIView):
    area_funzionale = "pratiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tipo_prestazione_id", type=int, required=True, description="ID tipo prestazione (obbligatorio)."),
        ],
        responses={200: inline_serializer(
            name="FormuleTempoResponse",
            fields={
                "data": inline_serializer(name="FormuleTempoData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET le formule tempo attive per un tipo prestazione.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        tipo_prestazione_id = optional_int({"v": qp.get("tipo_prestazione_id")}, "v")
        ErrorManager.require(
            tipo_prestazione_id is not None and tipo_prestazione_id > 0,
            code="E_INVALID_ID",
            message="tipo_prestazione_id obbligatorio e > 0",
        )
        assert tipo_prestazione_id is not None

        items = pratiche_service.get_formule_tempo(tipo_prestazione_id)
        return success_response({"results": items})


