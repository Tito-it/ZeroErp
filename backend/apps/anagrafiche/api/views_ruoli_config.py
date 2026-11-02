# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint config-resolver per tipo ruolo.
#        Restituisce nature ammesse e tipi soggetto dettaglio
#        con requisiti CF/PIVA per un dato ruolo anagrafico.
#        Usato dal SoggettoResolver frontend.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository


class RuoliConfigResolverView(DomainAPIView):
    """GET configurazione resolver per tipo ruolo."""

    # Lookup cross-dominio: lo consuma `anagrafiche/components/SoggettoResolver.vue`,
    # cioe' i drawer di TUTTI i domini che scelgono o creano un soggetto. Stessa
    # famiglia di `SoggettiRuoliLookupView` (skip + JWT, niente area): e' sola
    # lettura di configurazione, senza dati di soggetti.
    # ⛔ E NON dichiara `area_funzionale`: la catena legge lo skip solo se
    #    l'area non si risolve. Fino al 2026-09-12 dichiarava anche
    #    `area_funzionale = "anagrafiche"` e lo skip era MUTO — serviva la
    #    LETTURA su anagrafiche per aprire un drawer di vendite. Decisione di
    #    Tid (2026-09-12): vale lo skip. Presidiato da
    #    `core/tests/test_skip_area_check_registro.py`.
    skip_area_check = True

    @extend_schema(
        summary="Configurazione resolver per tipo ruolo",
        description=(
            "Restituisce le nature soggetto ammesse e i tipi soggetto dettaglio "
            "con requisiti CF/PIVA per il tipo ruolo indicato. "
            "Usato dal SoggettoResolver per adattare ricerca e form di creazione."
        ),
        responses={
            200: inline_serializer(
                name="RuoliConfigResolverResponse",
                fields={
                    "data": inline_serializer(
                        name="RuoliConfigResolverData",
                        fields={
                            "tipo_ruolo": serializers.CharField(),
                            "tipo_ruolo_descrizione": serializers.CharField(),
                            "nature_ammesse": serializers.ListField(
                                child=serializers.CharField(),
                                help_text="Nature soggetto ammesse: PF, PG, ENTE.",
                            ),
                            "tipi_soggetto_dettaglio": serializers.ListField(
                                child=serializers.DictField(),
                                help_text="Tipi dettaglio con cf_obbligatorio, piva_obbligatoria.",
                            ),
                            "default_tipo_soggetto_dettaglio_id": serializers.IntegerField(
                                allow_null=True,
                                help_text=(
                                    "Id del tipo_soggetto_dettaglio default per questo "
                                    "ruolo, risolto via config.parameters "
                                    "(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>). "
                                    "None se non configurato — il frontend fallback al "
                                    "primo elemento di tipi_soggetto_dettaglio."
                                ),
                            ),
                            "min_search_length": serializers.IntegerField(
                                help_text=(
                                    "Lunghezza minima della search per attivare la "
                                    "lookup soggetti: la soglia della lista "
                                    "`anagrafiche.soggetti` a catalogo "
                                    "(`ricerca_min_caratteri`), che la ricerca usa."
                                ),
                            ),
                        },
                    ),
                },
            ),
            404: inline_serializer(
                name="RuoliConfigResolverNotFound",
                fields={"error": serializers.DictField()},
            ),
        },
    )
    # Scopo: Restituisce la configurazione resolver per un tipo ruolo.
    def get(self, request: Request, tipo_ruolo_codice: str) -> JsonResponse:
        repo = SoggettiRepository()
        result = repo.get_config_resolver(tipo_ruolo_codice.upper())
        if result is None:
            from apps.core.services.service_errors import ServiceError

            raise ServiceError(
                code="E_ANAG_NOT_FOUND",
                message="Tipo ruolo non trovato.",
                detail=f"Nessun tipo ruolo attivo con codice '{tipo_ruolo_codice}'.",
            )
        return success_response(result)
