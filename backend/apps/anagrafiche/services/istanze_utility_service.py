# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per il lookup delle forniture (istanze_utilities, una riga per
#        billing account) riutilizzabile cross-dominio: la scelta del cliente
#        per fornitura nel preventivo e nella pratica. Valida i parametri di
#        ricerca, applica le regole di dominio (min lunghezza query, cap
#        risultati) e delega al repository.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository
from apps.core.services.error_manager import ErrorManager

_MIN_QUERY_LENGTH = 2
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20


class IstanzeUtilityService:
    """Facade per operazioni di lookup istanze_utilities."""

    # Scopo: Esegue lookup istanze_utilities per autocomplete con regole di
    #        dominio. Valida query min 2 char, cap limit a 50, delega a
    #        repository con scope emittente gia' risolto dal chiamante (view).
    # Perimetro: sola lettura. Ritorna lista arricchita + total_count per
    #        gestione UI "affina la ricerca" quando total > limit.
    # Risultato: dict {results, total_count, limit} pronto per success_response.
    def search_lookup(
        self,
        *,
        q: str,
        utility_id: int | None = None,
        soggetto_id: str | None = None,
        soggetto_ruolo_id: int | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.istanze_utility_service.search_lookup"
        cleaned_q = q.strip() if isinstance(q, str) else ""
        # Con un perimetro contestuale (soggetto e/o ruolo) il set e' gia'
        # ristretto e bounded: q vuota e' ammessa cosi' la tendina puo'
        # listare le istanze al click senza digitazione (drawer pratiche).
        # Senza perimetro resta la soglia minima (ricerca globale).
        ha_perimetro = bool(soggetto_id) or soggetto_ruolo_id is not None
        ErrorManager.require(
            ha_perimetro or len(cleaned_q) >= _MIN_QUERY_LENGTH,
            code="E_ANAG_VALIDAZIONE",
            message="Parametro di ricerca troppo corto.",
            detail=f"q deve avere almeno {_MIN_QUERY_LENGTH} caratteri (salvo filtro soggetto/ruolo).",
            context={"q_len": len(cleaned_q)},
            function_name=function_name,
            log_to_db=False,
        )

        # Cap di sicurezza sul limit — il default e' 20, max 50.
        if limit is None or limit <= 0:
            effective_limit = _DEFAULT_LIMIT
        else:
            effective_limit = min(int(limit), _MAX_LIMIT)

        repository = IstanzeUtilityRepository()
        results, total_count = repository.search_lookup(
            q=cleaned_q,
            utility_id=utility_id,
            soggetto_id=soggetto_id,
            soggetto_ruolo_id=soggetto_ruolo_id,
            emittente_ids=emittente_ids,
            limit=effective_limit,
        )

        return {
            "results": results,
            "total_count": total_count,
            "limit": effective_limit,
        }

    # Scopo: Recupera una singola istanza_utility per restore dell'AutoComplete
    #        in modalita' edit (evita round-trip aggiuntivi nel frontend).
    # Perimetro: sola lettura, nello scope emittente del chiamante (lo stesso
    #        della ricerca). Solleva E_ANAG_NOT_FOUND se inesistente O fuori
    #        scope: un id fuori perimetro non rivela di esistere.
    # Risultato: dict riga arricchita pronta per success_response.
    def get_lookup_by_id(
        self, istanza_utility_id: int, *, emittente_ids: list[int] | None,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.istanze_utility_service.get_lookup_by_id"
        # Esclude bool (sottoclasse di int in Python).
        valid_id = (
            isinstance(istanza_utility_id, int)
            and not isinstance(istanza_utility_id, bool)
            and istanza_utility_id > 0
        )
        ErrorManager.require(
            valid_id,
            code="E_ANAG_VALIDAZIONE",
            message="istanza_utility_id non valido.",
            detail="istanza_utility_id deve essere un intero positivo.",
            context={"istanza_utility_id": istanza_utility_id},
            function_name=function_name,
            log_to_db=False,
        )
        repository = IstanzeUtilityRepository()
        result = repository.get_lookup_by_id(
            istanza_utility_id, emittente_ids=emittente_ids,
        )
        ErrorManager.require(
            result is not None,
            code="E_ANAG_NOT_FOUND",
            message="Istanza utility non trovata.",
            detail=f"Nessuna istanza_utility con id={istanza_utility_id} nel perimetro dell'utente.",
            context={"istanza_utility_id": istanza_utility_id},
            function_name=function_name,
            log_to_db=False,
        )
        assert result is not None
        return result
