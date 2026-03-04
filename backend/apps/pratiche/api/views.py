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
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.services import generazione_service, pratiche_service
from apps.pratiche.types import FlussoRow


# Scopo: Recupera un flusso verificando esistenza e appartenenza alla pratica.
# Evita duplicazione del pattern get+check+ownership in ogni view nested.
def _get_flusso_verificato(
    repo: PraticheRepository, pratica_id: int, flusso_id: int,
) -> FlussoRow:
    flusso = repo.get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None
    ErrorManager.require(
        flusso["pratica_id"] == pratica_id,
        code="E_FLUSSO_OWNERSHIP",
        message=f"Flusso {flusso_id} non appartiene alla pratica {pratica_id}",
    )
    return flusso


# ================================================================== #
# Pratiche — lista, dettaglio, creazione, aggiornamento               #
# ================================================================== #


class ApiPraticheList(APIView):
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=True, description="ID emittente fiscale (obbligatorio)."),
            OpenApiParameter(name="stato", type=str, required=False, description="Filtro codice_interno stato pratica."),
            OpenApiParameter(name="tipo_prestazione_id", type=int, required=False, description="Filtro tipo prestazione."),
            OpenApiParameter(name="soggetto_id", type=str, required=False, description="Filtro UUID soggetto."),
            OpenApiParameter(name="solo_interna", type=bool, required=False, description="Filtro flag solo_interna."),
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
        emittente_fiscale_id = optional_int({"v": qp.get("emittente_fiscale_id")}, "v")
        ErrorManager.require(
            emittente_fiscale_id is not None and emittente_fiscale_id > 0,
            code="E_PRATICA_VALIDATION",
            message="emittente_fiscale_id obbligatorio",
        )
        assert emittente_fiscale_id is not None

        stato = qp.get("stato") or None
        tipo_prestazione_id = optional_int({"v": qp.get("tipo_prestazione_id")}, "v")
        soggetto_id = qp.get("soggetto_id") or None
        solo_interna_raw = qp.get("solo_interna")
        solo_interna = None
        if solo_interna_raw is not None:
            solo_interna = solo_interna_raw.lower() in ("true", "1")
        limit = optional_int({"v": qp.get("limit", "50")}, "v") or 50
        offset = optional_int({"v": qp.get("offset", "0")}, "v") or 0

        items, total = pratiche_service.cerca_pratiche(
            emittente_fiscale_id=emittente_fiscale_id,
            stato_codice_interno=stato,
            tipo_prestazione_id=tipo_prestazione_id,
            soggetto_id=soggetto_id,
            solo_interna=solo_interna,
            limit=limit,
            offset=offset,
        )
        return success_response({"count": total, "results": items})

    @extend_schema(
        request=inline_serializer(
            name="PraticheCreateRequest",
            fields={
                "emittente_fiscale_id": serializers.IntegerField(),
                "tipo_prestazione_id": serializers.IntegerField(),
                "priorita_id": serializers.IntegerField(),
                "soggetto_id": serializers.UUIDField(required=False, allow_null=True),
                "risorsa_umana_id": serializers.IntegerField(required=False, allow_null=True),
                "unita_organizzativa_id": serializers.IntegerField(required=False, allow_null=True),
                "canale_origine_id": serializers.IntegerField(required=False, allow_null=True),
                "solo_interna": serializers.BooleanField(required=False),
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
                priorita_id=int(payload["priorita_id"]),
                soggetto_id=str(payload["soggetto_id"]) if payload.get("soggetto_id") else None,
                risorsa_umana_id=optional_int(payload, "risorsa_umana_id"),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                canale_origine_id=optional_int(payload, "canale_origine_id"),
                solo_interna=bool(payload.get("solo_interna", False)),
                descrizione=payload.get("descrizione"),
                data_scadenza=payload.get("data_scadenza"),
                meta=payload.get("meta"),
            )
            return {"pratica_id": pratica_id, "status": "ok"}

        return handle_post_json(request, handler=_handler)


class ApiPraticheListV1(ApiPraticheList):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


class ApiPraticaDetail(APIView):
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


class ApiPraticaDetailV1(ApiPraticaDetail):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


# ================================================================== #
# Pratiche — stato e assegnazione                                     #
# ================================================================== #


class ApiPraticaStato(APIView):
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


class ApiPraticaStatoV1(ApiPraticaStato):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_pratica"


class ApiPraticaAssegnazione(APIView):
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


class ApiPraticaAssegnazioneV1(ApiPraticaAssegnazione):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"
    post_permission = "assegna_pratica"


# ================================================================== #
# Giornale                                                            #
# ================================================================== #


class ApiPraticaGiornale(APIView):
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


class ApiPraticaGiornaleV1(ApiPraticaGiornale):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


# ================================================================== #
# Flussi — lista, dettaglio, creazione, stato                         #
# ================================================================== #


class ApiPraticaFlussiList(APIView):
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


class ApiPraticaFlussiListV1(ApiPraticaFlussiList):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


class ApiPraticaFlussoDetail(APIView):
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


class ApiPraticaFlussoDetailV1(ApiPraticaFlussoDetail):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


class ApiPraticaFlussoStato(APIView):
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
                pratiche_service.avvia_flusso(flusso_id)
            else:
                # Transizione generica via service (wrappata in @transaction.atomic).
                pratiche_service.cambia_stato_flusso(flusso_id, nuovo_stato)
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)


class ApiPraticaFlussoStatoV1(ApiPraticaFlussoStato):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_flusso"


# ================================================================== #
# Prerequisiti e canali                                               #
# ================================================================== #


class ApiPraticaFlussoPrerequisiti(APIView):
    @extend_schema(
        responses={200: inline_serializer(
            name="FlussoPrerequistiResponse",
            fields={
                "data": inline_serializer(name="FlussoPrerequistiData", fields={
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


class ApiPraticaFlussoPrerequistiV1(ApiPraticaFlussoPrerequisiti):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


class ApiPraticaFlussoCanali(APIView):
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


class ApiPraticaFlussoCanaliV1(ApiPraticaFlussoCanali):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


# ================================================================== #
# Generazione cross-pratica                                           #
# ================================================================== #


class ApiPraticaFlussoRegoleGenerazione(APIView):
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


class ApiPraticaFlussoRegoleGenerazioneV1(ApiPraticaFlussoRegoleGenerazione):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"


class ApiPraticaFlussoGenera(APIView):
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


class ApiPraticaFlussoGeneraV1(ApiPraticaFlussoGenera):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"
    post_permission = "genera_pratica_manuale"


class ApiPraticaFlussoPraticheGenerate(APIView):
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


class ApiPraticaFlussoPraticheGenerateV1(ApiPraticaFlussoPraticheGenerate):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "pratiche"
