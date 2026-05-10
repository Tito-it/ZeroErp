# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per lookup anagrafiche e config cross-dominio.
#        Endpoint: tipi soggetto dettaglio, matrice indirizzi,
#        autocomplete comuni, search stradario.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.core.db.lookup_repository import LookupRepository


class LookupTipiSoggettoDettaglioView(DomainAPIView):
    """Lista tipi soggetto dettaglio con natura e policy."""
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="TipiSoggettoDettaglioResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce i tipi soggetto dettaglio con natura, CF/PIVA/dati societari policy.
    # Il frontend usa questi dati per guidare la visibilita' dei campi nel SoggettoForm.
    def get(self, request: Request) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_tipi_soggetto_dettaglio()
        return success_response({"results": results})


class LookupTipiRuoliPerNaturaView(DomainAPIView):
    """Tipi ruolo ammessi filtrati per natura soggetto."""
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="natura_soggetto", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="TipiRuoliPerNaturaResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce tipi ruolo ammessi per la natura, filtrati dalla matrice.
    def get(self, request: Request) -> JsonResponse:
        natura = request.query_params.get("natura_soggetto") or None
        repo = LookupRepository()
        results = repo.list_tipi_ruoli_per_natura(natura_soggetto=natura)
        return success_response({"results": results})


class LookupFormeGiuridicheView(DomainAPIView):
    """Forme giuridiche con policy REA e capitale sociale."""
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tipo_soggetto_dettaglio_id", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="FormeGiuridicheResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce forme giuridiche con policy, opzionalmente filtrate per tipo soggetto.
    def get(self, request: Request) -> JsonResponse:
        tipo_id = optional_int({"v": request.query_params.get("tipo_soggetto_dettaglio_id")}, "v")
        repo = LookupRepository()
        results = repo.list_forme_giuridiche(tipo_soggetto_dettaglio_id=tipo_id)
        return success_response({"results": results})


class LookupMatriceIndirizziView(DomainAPIView):
    """Matrice indirizzi ammessi per un tipo soggetto dettaglio."""
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="MatriceIndirizziResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la matrice tipi indirizzo ammessi/obbligatori per un tipo
    # soggetto dettaglio. Il frontend usa questi dati per mostrare i form indirizzo
    # corretti in base al tipo di soggetto selezionato.
    def get(self, request: Request, tipo_soggetto_dettaglio_id: int) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_matrice_indirizzi(tipo_soggetto_dettaglio_id)
        return success_response({"results": results})


class LookupMatriceIndirizziRuoloView(DomainAPIView):
    """Matrice indirizzi ammessi per un tipo ruolo (codice_interno)."""
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="MatriceIndirizziRuoloResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    def get(self, request: Request, tipo_ruolo_codice: str) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_matrice_indirizzi_ruolo(tipo_ruolo_codice)
        return success_response({"results": results})


class LookupUtilitiesPerRuoloView(DomainAPIView):
    """Utility ammesse per un tipo ruolo (codice_interno).

    Filtraggio strict: restituisce solo utility con riga ATTIVA in
    `config.utilities_tipi_ruolo` per il codice interno del ruolo.
    Riusabile cross-dominio (EF, FO, CL, ...).
    """
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="UtilitiesPerRuoloResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce le utility ammesse per il tipo ruolo passato in path,
    # con filtro strict basato sulla matrice config.utilities_tipi_ruolo.
    def get(self, request: Request, tipo_ruolo_codice: str) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_utilities_per_ruolo(tipo_ruolo_codice)
        return success_response({"results": results})


class LookupUtilitiesPerEmittenteView(DomainAPIView):
    """Utility per popolare la combo "Utility" del FE.

    Regola di business:

    - **Operatore con emittente fiscale**: vede SOLO le utility configurate
      nella matrice `anagrafiche.emittenti_fiscali_utilities` per il proprio
      emittente. Le utility globali non attivate sul suo EF non sono
      visibili. Il pattern impedisce all'operatore di selezionare utility
      che il proprio emittente non gestisce.
    - **Super-admin senza emittente** (cross-emittente, configurazioni di
      sistema, audit): vede TUTTE le utility con ruolo EF — niente filtro
      matrice perche' non e' associato a uno specifico emittente.

    Filtro orthogonale `?ruolo=CL|FO|...`:

    - se fornito, applica intersezione con `config.utilities_tipi_ruolo`
      per il ruolo del soggetto target (utile sul drawer cliente per
      mostrare solo utility ammesse per i CLIENTI).
    - se omesso, nessuna intersezione (preventivi, listini, ecc. dove
      non c'e' un ruolo soggetto specifico).

    Default lato FE: `useUtilityDefaultId` legge il parametro
    `DEFAULT_UTILITY` (catena user/group/emittente/sistema) e fa match
    `codice_interno -> id` sul set ritornato qui. Il default e' quindi
    automaticamente coerente con il filtro applicato (l'operatore non
    riceve come default un'utility che non avrebbe potuto vedere).
    """
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="ruolo",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Codice ruolo soggetto (es. CL, FO). Se omesso, ritorna tutte le utility EF dell'emittente.",
                required=False,
            ),
        ],
        responses={200: inline_serializer(
            name="UtilitiesPerEmittenteResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce utility configurate per l'emittente dell'utente.
    #        Se ruolo fornito, applica intersezione con ruolo soggetto.
    #        Super-admin senza emittente -> tutte le utility EF (fallback).
    def get(self, request: Request) -> JsonResponse:
        from apps.core.services.parameter_service import ParameterService

        ruolo = (request.query_params.get("ruolo") or "").strip().upper() or None

        # Risolve emittente dell'utente corrente (stessa catena di parameter settings).
        # Se None (es. super-admin cross-emittente), si delega alla repo che
        # ritorna tutte le utility EF (eventualmente filtrate per ruolo).
        svc = ParameterService()
        emittente_fiscale_id = svc.get_emittente_fiscale_id_for_user(request.user.id)

        repo = LookupRepository()
        results = repo.list_utilities_per_emittente(emittente_fiscale_id, ruolo)
        return success_response({"results": results})


class LookupContiContabiliView(DomainAPIView):
    """Lookup dedicato conti contabili con filtro tipo (A=Acquisto, V=Vendita).

    Endpoint dedicato (non generico) perche' espone il campo `tipo_conto`
    che il lookup generico `/core/lookup/codici/?rel=config.conti_contabili`
    non restituisce. Usato dall'ArticoloDrawer per alimentare le combo
    conto_contabile_vendita (tipo=V) e conto_contabile_acquisto (tipo=A).
    """
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="tipo",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtro tipo conto: 'A' (acquisto) o 'V' (vendita). Omesso = tutti.",
                required=False,
            ),
        ],
        responses={200: inline_serializer(
            name="ContiContabiliLookupResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Lista conti contabili filtrati per tipo (A/V) per le combo articolo.
    def get(self, request: Request) -> JsonResponse:
        tipo = (request.query_params.get("tipo") or "").strip().upper() or None
        repo = LookupRepository()
        results = repo.list_conti_contabili(tipo=tipo)
        return success_response({"results": results})


class LookupSistemaCodiciView(DomainAPIView):
    """GET verifica configurazione sistema codici per schema/tabella/colonna."""
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="schema", type=str, required=True),
            OpenApiParameter(name="tabella", type=str, required=True),
            OpenApiParameter(name="colonna", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="SistemaCodiciResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Verifica se esiste configurazione sistema codici.
    #        Se configurato: auto=true, il codice viene generato dal DB.
    #        Se non configurato: auto=false, il codice deve essere inserito manualmente.
    def get(self, request: Request) -> JsonResponse:
        schema = request.query_params.get("schema", "")
        tabella = request.query_params.get("tabella", "")
        colonna = request.query_params.get("colonna", "codice")
        repo = LookupRepository()
        config = repo.get_sistema_codici(schema, tabella, colonna)
        if config:
            return success_response({
                "auto": config["usa_sequenza"],
                "prefisso": config["prefisso"],
                "separatore": config["separatore"],
                "lunghezza_numero": config["lunghezza_numero"],
            })
        return success_response({"auto": False})


class LookupComuniView(DomainAPIView):
    """Autocomplete comuni con ricerca ILIKE."""
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca ILIKE su denominazione comune."),
            OpenApiParameter(name="limit", type=int, required=False,
                             description="Righe massime (default 20, max 100)."),
            OpenApiParameter(name="offset", type=int, required=False,
                             description="Offset paginazione (default 0)."),
        ],
        responses={200: inline_serializer(
            name="ComuniAutocompleteResponse",
            fields={
                "data": inline_serializer(name="ComuniAutocompleteData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Ricerca comuni per autocomplete. Accetta search ILIKE su denominazione.
    # Restituisce id, descrizione, provincia_sigla con paginazione.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = (qp.get("search") or "").strip() or None
        limit = min(qp_int(qp.get("limit"), 20), 100)
        offset = qp_int(qp.get("offset"), 0)

        repo = LookupRepository()
        results, total_count = repo.search_comuni(
            search=search, limit=limit, offset=offset,
        )
        return success_response({"count": total_count, "results": results})


class SearchStradarioView(DomainAPIView):
    """Autocomplete vie (stradario) per comune."""
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="comune_id", type=int, required=False,
                             description="ID comune per filtrare le vie."),
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su toponimo + denominazione via."),
            OpenApiParameter(name="limit", type=int, required=False,
                             description="Righe massime (default 30, max 100)."),
        ],
        responses={200: inline_serializer(
            name="StradarioSearchResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Ricerca vie per autocomplete. Chiama script.fn_search_stradario.
    # Il frontend usa questo endpoint dopo che l'utente ha selezionato un comune.
    # Restituisce stradario_id, via_completa, comune, provincia, CAP.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        comune_id = optional_int(qp, "comune_id")
        search = (qp.get("search") or "").strip() or None
        limit = min(qp_int(qp.get("limit"), 30), 100)

        repo = LookupRepository()
        results = repo.search_stradario(
            comune_id=comune_id, search=search, limit=limit,
        )
        return success_response({"results": results})


class SearchStradarioGeneraleView(DomainAPIView):
    """Autocomplete vie su stradario_generale (senza comune/CAP) per via nuova."""
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=True,
                             description="Ricerca su indirizzo_normalizzato (min 2 caratteri)."),
            OpenApiParameter(name="toponomastica_id", type=int, required=False,
                             description="Filtro opzionale per tipo strada."),
            OpenApiParameter(name="limit", type=int, required=False,
                             description="Righe massime (default 30, max 100)."),
        ],
        responses={200: inline_serializer(
            name="StradarioGeneraleSearchResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Ricerca vie su stradario_generale per autocomplete via nuova.
    # L'utente cerca una via in tutta Italia, poi sceglie comune e CAP separatamente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = (qp.get("search") or "").strip() or None
        toponomastica_id = optional_int(qp, "toponomastica_id")
        limit = min(qp_int(qp.get("limit"), 30), 100)

        repo = LookupRepository()
        results = repo.search_stradario_generale(
            search=search, toponomastica_id=toponomastica_id, limit=limit,
        )
        return success_response({"results": results})
