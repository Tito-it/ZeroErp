# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: APIView modulo pratiche — endpoint REST per pratiche, flussi,
#        giornale, prerequisiti, canali e generazione cross-pratica.
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.endpoint_helpers import get_risorsa_umana_id, handle_post_json
from apps.core.api.payload_validators import optional_int, paginated_envelope, parse_list_params, qp_int_strict, qp_str
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.services import generazione_service, pratiche_service


# Alias locale: la verifica ownership flusso-pratica e' centralizzata nel service.
_get_flusso_verificato = pratiche_service.verifica_flusso_pratica


# ================================================================== #
# Pratiche — lista, dettaglio, creazione, aggiornamento               #
# ================================================================== #


class ApiPraticheList(DomainAPIView):
    area_funzionale = "pratiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=True, description="ID emittente fiscale (obbligatorio)."),
            OpenApiParameter(name="stato", type=str, required=False, description="Filtro codice_interno stato pratica."),
            OpenApiParameter(name="tipo_prestazione_id", type=int, required=False, description="Filtro tipo prestazione."),
            OpenApiParameter(name="soggetto_id", type=str, required=False, description="Filtro UUID soggetto."),
            OpenApiParameter(name="limit", type=int, required=False, description="Righe per pagina (default 50, max 200)."),
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

        p = parse_list_params(qp, default_order="data_insert", default_limit=50)
        stato = qp_str(qp.get("stato"))
        tipo_prestazione_id = optional_int({"v": qp.get("tipo_prestazione_id")}, "v")
        soggetto_id = qp_str(qp.get("soggetto_id"))
        data_da = qp_str(qp.get("data_da"))
        data_a = qp_str(qp.get("data_a"))

        items, total = pratiche_service.cerca_pratiche(
            emittente_fiscale_id=emittente_fiscale_id,
            stato_codice_interno=stato,
            tipo_prestazione_id=tipo_prestazione_id,
            soggetto_id=soggetto_id,
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratica_id = pratiche_service.crea_pratica(
                emittente_fiscale_id=int(payload["emittente_fiscale_id"]),
                tipo_prestazione_id=int(payload["tipo_prestazione_id"]),
                # Opzionale: assente -> default NORMALE risolto dal service.
                priorita_id=optional_int(payload, "priorita_id"),
                soggetto_id=str(payload["soggetto_id"]) if payload.get("soggetto_id") else None,
                soggetto_ruolo_id=optional_int(payload, "soggetto_ruolo_id"),
                istanza_utility_id=optional_int(payload, "istanza_utility_id"),
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratiche_service.cambia_stato_pratica(pratica_id, str(payload["nuovo_stato"]))
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
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
    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False, description="Righe per pagina (default 100, max 200)."),
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
        limit = optional_int({"v": qp.get("limit", "100")}, "v") or 100
        offset = optional_int({"v": qp.get("offset", "0")}, "v") or 0

        items, total = pratiche_service.get_giornale(pratica_id, limit=limit, offset=offset)
        return success_response({"count": total, "results": items})




# ================================================================== #
# Flussi — lista, dettaglio, creazione, stato                         #
# ================================================================== #


class ApiPraticaPercorso(DomainAPIView):
    area_funzionale = "pratiche"

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
    @extend_schema(
        responses={200: inline_serializer(
            name="PraticaFlussiListResponse",
            fields={
                "data": inline_serializer(name="PraticaFlussiListData", fields={
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce via GET i flussi di una pratica.
    def get(self, request: Request, pratica_id: int) -> JsonResponse:
        repo = PraticheRepository()
        flussi = repo.list_flussi(pratica_id)
        return success_response({"results": flussi})

    @extend_schema(
        request=inline_serializer(
            name="FlussoCreateRequest",
            fields={
                "template_flusso_id": serializers.IntegerField(required=False, allow_null=True),
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            flusso_id = pratiche_service.crea_flusso(
                pratica_id=pratica_id,
                template_flusso_id=optional_int(payload, "template_flusso_id"),
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
        # Verifica ownership flusso-pratica prima di procedere.
        repo = PraticheRepository()
        _get_flusso_verificato(repo, pratica_id, flusso_id)

        def _handler(payload: dict[str, object]) -> dict[str, object]:
            nuovo_stato = str(payload["nuovo_stato"])
            if nuovo_stato == "COMPLETATO":
                ErrorManager.require(
                    "esito" in payload and payload["esito"],
                    code="E_FLUSSO_VALIDATION",
                    message="esito obbligatorio per completamento flusso",
                )
                pratiche_service.completa_flusso(
                    flusso_id,
                    esito=str(payload["esito"]),
                    note_esito=payload.get("note_esito"),
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

        def _handler(payload: dict[str, object]) -> dict[str, object]:
            nuova_pratica_id = generazione_service.genera_pratica_manuale(
                flusso_id, int(payload["regola_id"]),
            )
            return {"pratica_id": nuova_pratica_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaFlussoPraticheGenerate(DomainAPIView):
    area_funzionale = "pratiche"
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            sospensione_id = pratiche_service.sospendi_pratica(
                pratica_id,
                str(payload.get("motivo", "")),
                data_riattivazione_prevista=payload.get("data_riattivazione_prevista"),
            )
            return {"sospensione_id": sospensione_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)




class ApiPraticaRiattiva(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "riattiva_pratica"
    @extend_schema(
        request=inline_serializer(
            name="PraticaRiattivaRequest",
            fields={},
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratiche_service.riattiva_pratica(pratica_id)
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
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
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratiche_service.riattiva_flusso(pratica_id, flusso_id)
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)




# ================================================================== #
# Sospensioni e calcoli tempo — lettura                                #
# ================================================================== #


class ApiPraticaSospensioni(DomainAPIView):
    area_funzionale = "pratiche"
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
            contenuto=str(request.data.get("contenuto", "")),
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

        def _handler(payload: dict[str, object]) -> dict[str, object]:
            assegnato = pratiche_service.prendi_in_carico(flusso_id, risorsa_umana_id)
            return {"assegnato": assegnato, "status": "ok"}

        return handle_post_json(request, handler=_handler)


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
                template_flusso_id=int(payload["template_flusso_id"]),
                unita_organizzativa_id=int(payload["unita_organizzativa_id"]),
                risorsa_umana_id=int(payload["risorsa_umana_id"]),
                attivo=bool(payload.get("attivo", True)),
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


