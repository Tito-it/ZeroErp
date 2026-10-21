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
from apps.core.api.openapi_params import risposta_lookup
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import (
    optional_int,
    parse_list_params,
    qp_int_strict,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.core.db.lookup_repository import LookupRepository


class LookupTipiSoggettoDettaglioView(DomainAPIView):
    """Lista tipi soggetto dettaglio con natura e policy."""
    skip_area_check = True

    @extend_schema(
        responses={200: risposta_lookup("TipiSoggettoDettaglioResponse")},
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
        responses={200: risposta_lookup("TipiRuoliPerNaturaResponse")},
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
        responses={200: risposta_lookup("FormeGiuridicheResponse")},
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
        responses={200: risposta_lookup("MatriceIndirizziResponse")},
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
        responses={200: risposta_lookup("MatriceIndirizziRuoloResponse")},
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
        responses={200: risposta_lookup("UtilitiesPerRuoloResponse")},
    )
    # Scopo: Restituisce le utility ammesse per il tipo ruolo passato in path,
    # con filtro strict basato sulla matrice config.utilities_tipi_ruolo.
    def get(self, request: Request, tipo_ruolo_codice: str) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_utilities_per_ruolo(tipo_ruolo_codice)
        return success_response({"results": results})


class LookupUtilitiesPerEmittenteView(DomainAPIView):
    """Utility per popolare la combo "Utility" del FE.

    Regola: le utility **ammesse per il ruolo emittente fiscale** (`EF`) in
    `config.utilities_tipi_ruolo`, uguali per ogni operatore. «Per emittente»
    nel nome della rotta vuol dire il **ruolo** EF, non l'emittente attivo.

    ⛔ Non filtra con `anagrafiche.emittenti_fiscali_utilities`: quella e' la
    tabella opzionale dei PARAMETRI di fatturazione per (emittente, utility),
    non l'elenco delle utility dell'emittente (dettaglio nel repository,
    `list_utilities_per_emittente`). Fino al 2026-10-14 la usava come filtro.

    Filtro orthogonale `?ruolo=CL|FO|...`:

    - se fornito, applica intersezione con `config.utilities_tipi_ruolo`
      per il ruolo del soggetto target (utile sul drawer cliente per
      mostrare solo utility ammesse per i CLIENTI).
    - se omesso, nessuna intersezione (preventivi, listini, ecc. dove
      non c'e' un ruolo soggetto specifico).

    Default lato FE: `useUtilityDefaultId` legge il parametro
    `DEFAULT_UTILITY` (catena user/group/emittente/sistema) e fa match
    `codice_interno -> id` sul set ritornato qui.
    """
    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="ruolo",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Codice ruolo soggetto (es. CL, FO). Se omesso, ritorna tutte le utility ammesse per il ruolo EF.",
                required=False,
            ),
        ],
        responses={200: risposta_lookup("UtilitiesPerEmittenteResponse")},
    )
    # Scopo: Restituisce le utility ammesse per il ruolo EF; se `ruolo` e'
    #        fornito, intersecate con quelle ammesse per il ruolo del soggetto.
    def get(self, request: Request) -> JsonResponse:
        ruolo = (request.query_params.get("ruolo") or "").strip().upper() or None
        results = LookupRepository().list_utilities_per_emittente(ruolo)
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
        responses={200: risposta_lookup("ContiContabiliLookupResponse")},
    )
    # Scopo: Lista conti contabili filtrati per tipo (A/V) per le combo articolo.
    def get(self, request: Request) -> JsonResponse:
        tipo = (request.query_params.get("tipo") or "").strip().upper() or None
        repo = LookupRepository()
        results = repo.list_conti_contabili(tipo=tipo)
        return success_response({"results": results})


class LookupTipiEntitaView(DomainAPIView):
    """GET /api/v1/core/lookup/tipi-entita/ — il vocabolario di `config.tipi_entita`.

    Lookup dedicato (api.md §Lookup dedicato): la tabella ha PK `codice` testo
    e nessun `id`/`descrizione`, quindi il generico non la serve; e cio' che
    il client vuole e' l'`etichetta_key` che il DB DICHIARA per ogni tipo, non
    una descrizione — l'etichetta si risolve nei locales (`labelOrCode`).
    ⭐ Nasce il 2026-09-19 perche' la tendina «Entita'» del giornale
    trasversale si era ricopiata sette codici a mano, e il catalogo ne aveva
    gia' nove: un vocabolario del DB si legge, non si specchia.
    Cross-dominio (`skip_area_check`): lo consumano vendite, amm-software e,
    in prospettiva, il resolver dei bersagli di `core`.
    """
    skip_area_check = True

    @extend_schema(
        responses={200: risposta_lookup("TipiEntitaLookupResponse", riga=inline_serializer(
            name="TipoEntitaLookupRow",
            fields={
                "codice": serializers.CharField(),
                "etichetta_key": serializers.CharField(),
                "key_selector": serializers.CharField(),
            },
        ))},
    )
    # Scopo: Restituisce i tipi di entita' vivi, con l'indirizzo i18n dichiarato dal DB.
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": LookupRepository().list_tipi_entita()})


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
    # ⛔ `schema` e `tabella` sono obbligatori: assenti o vuoti → 400
    #    `E_VALIDATION_INPUT`. Fino al 2026-10-14 valevano "" e la risposta era
    #    «non configurato», cioe' un «scrivi il codice a mano» detto a una
    #    domanda mai fatta (§6 di analisi-be-difetti-emersi-verifica-doc-api-core).
    def get(self, request: Request) -> JsonResponse:
        schema = qp_str(request.query_params.get("schema"))
        tabella = qp_str(request.query_params.get("tabella"))
        if not schema or not tabella:
            mancanti = [nome for nome, valore in (("schema", schema), ("tabella", tabella)) if not valore]
            raise ValueError(f"Parametri obbligatori mancanti: {', '.join(mancanti)}.")
        colonna = qp_str(request.query_params.get("colonna")) or "codice"
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
        p = parse_list_params(request.query_params, default_limit=20, max_limit=100)

        repo = LookupRepository()
        results, total_count = repo.search_comuni(
            search=p["search"], limit=p["limit"], offset=p["offset"],
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
        responses={200: risposta_lookup("StradarioSearchResponse")},
    )
    # Scopo: Ricerca vie per autocomplete. Chiama script.fn_search_stradario.
    # Il frontend usa questo endpoint dopo che l'utente ha selezionato un comune.
    # Restituisce stradario_id, via_completa, comune, provincia, CAP.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        comune_id = optional_int(qp, "comune_id")
        search = qp_str(qp.get("search"))
        limit = min(qp_int_strict(qp.get("limit"), "limit", 30), 100)

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
        responses={200: risposta_lookup("StradarioGeneraleSearchResponse")},
    )
    # Scopo: Ricerca vie su stradario_generale per autocomplete via nuova.
    # L'utente cerca una via in tutta Italia, poi sceglie comune e CAP separatamente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = qp_str(qp.get("search"))
        toponomastica_id = optional_int(qp, "toponomastica_id")
        limit = min(qp_int_strict(qp.get("limit"), "limit", 30), 100)

        repo = LookupRepository()
        results = repo.search_stradario_generale(
            search=search, toponomastica_id=toponomastica_id, limit=limit,
        )
        return success_response({"results": results})
