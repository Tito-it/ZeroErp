# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per il lookup billing_account riutilizzabile cross-dominio.
#        Valida i parametri di ricerca, applica le regole di dominio
#        (min lunghezza query, cap risultati) e delega al repository.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.services.error_manager import ErrorManager

_MIN_QUERY_LENGTH = 2
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20


class BillingAccountService:
    """Facade per operazioni di lookup billing_account."""

    # Scopo: Esegue lookup billing_account per autocomplete con regole di dominio.
    #        Valida query min 2 char, cap limit a 50, delega a repository con
    #        scope emittente gia' risolto dal chiamante (view).
    # Perimetro: sola lettura. Ritorna lista arricchita + total_count per
    #        gestione UI "affina la ricerca" quando total > limit.
    # Risultato: dict {results, total_count} pronto per success_response.
    def search_lookup(
        self,
        *,
        q: str,
        utility_id: int | None = None,
        solo_validi: bool = True,
        valid_at: date | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.search_lookup"
        cleaned_q = q.strip() if isinstance(q, str) else ""
        ErrorManager.require(
            len(cleaned_q) >= _MIN_QUERY_LENGTH,
            code="E_ANAG_VALIDAZIONE",
            message="Parametro di ricerca troppo corto.",
            detail=f"q deve avere almeno {_MIN_QUERY_LENGTH} caratteri.",
            context={"q_len": len(cleaned_q)},
            function_name=function_name,
            log_to_db=False,
        )

        # Cap di sicurezza sul limit — il default e' 20, max 50.
        if limit is None or limit <= 0:
            effective_limit = _DEFAULT_LIMIT
        else:
            effective_limit = min(int(limit), _MAX_LIMIT)

        repository = BillingAccountRepository()
        results, total_count = repository.search_lookup(
            q=cleaned_q,
            utility_id=utility_id,
            solo_validi=solo_validi,
            valid_at=valid_at,
            emittente_ids=emittente_ids,
            limit=effective_limit,
        )

        return {
            "results": results,
            "total_count": total_count,
            "limit": effective_limit,
        }

    # Scopo: Recupera un singolo billing_account per restore dell'AutoComplete
    #        in modalita' edit (evita round-trip aggiuntivi nel frontend).
    # Perimetro: sola lettura. Solleva E_ANAG_NOT_FOUND se inesistente.
    # Risultato: dict riga arricchita pronta per success_response.
    def get_lookup_by_id(self, billing_account_id: int) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.get_lookup_by_id"
        # Esclude bool (sottoclasse di int in Python): True/False non sono id validi.
        valid_id = (
            isinstance(billing_account_id, int)
            and not isinstance(billing_account_id, bool)
            and billing_account_id > 0
        )
        ErrorManager.require(
            valid_id,
            code="E_ANAG_VALIDAZIONE",
            message="billing_account_id non valido.",
            detail="billing_account_id deve essere un intero positivo.",
            context={"billing_account_id": billing_account_id},
            function_name=function_name,
            log_to_db=False,
        )
        repository = BillingAccountRepository()
        result = repository.get_lookup_by_id(billing_account_id)
        ErrorManager.require(
            result is not None,
            code="E_ANAG_NOT_FOUND",
            message="Billing account non trovato.",
            detail=f"Nessun billing_account con id={billing_account_id}.",
            context={"billing_account_id": billing_account_id},
            function_name=function_name,
            log_to_db=False,
        )
        assert result is not None
        return result
