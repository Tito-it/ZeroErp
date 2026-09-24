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
from apps.core.db.lookup_repository import LookupRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.service_errors import ServiceError

_MIN_QUERY_LENGTH = 2
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20

# Codici ruolo soggetto ammessi per l'endpoint utilities-per-BA.
# Allineato con il dominio del param p_ruolo_codice_soggetto della
# funzione SQL anagrafiche.fn_lookup_utilities_per_ba.
_ALLOWED_RUOLI_BA = frozenset({"CL", "FO", "GE"})


class BillingAccountService:
    """Facade per operazioni di lookup billing_account."""

    # Scopo: Esegue lookup billing_account per autocomplete con regole di dominio.
    #        Valida query min 2 char, cap limit a 50, risolve lo scope
    #        emittente dell'utente e delega al repository.
    # ⛔ Lo scope lo risolve il SERVICE, non il chiamante (2026-09-24). Fino a
    #    quel giorno lo passavano la view e il tool dell'AI, ciascuno per conto
    #    suo, e l'avevano risolto in due modi: la view coi soggetto_ruolo_id, il
    #    tool con le PK — numeri di due tabelle diverse, confrontati in silenzio.
    #    Quale id vuole la query e' un fatto della QUERY
    #    (`script.fn_check_ba_visible_for_emittenti` confronta col soggetto-ruolo
    #    dell'emittente): per questo si decide qui, accanto a lei, e il
    #    chiamante passa solo l'utente.
    # Perimetro: sola lettura. Ritorna lista arricchita + total_count per
    #        gestione UI "affina la ricerca" quando total > limit.
    # Risultato: dict {results, total_count} pronto per success_response.
    def search_lookup(
        self,
        *,
        user: Any,
        q: str,
        utility_id: int | None = None,
        solo_validi: bool = True,
        valid_at: date | None = None,
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

        # Scope emittente: None = nessuna restrizione (superuser), [] = nessun
        # emittente autorizzato (nessun BA), altrimenti i soggetto_ruolo_id.
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(user, cache={})

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

    # Scopo: Lista utility "guidate da emittente" per un billing account
    #        (refactor operatore-emittenti, sez. 3 del WIP).
    #        Applica scope check sull'emittente fiscale del BA prima di
    #        delegare al lookup repository:
    #          - superuser → bypass scope
    #          - user_emittente_id NULL (admin globale o "0 emittenti")
    #            → no check, vede tutto
    #          - operatore con emittente assegnato → BA deve appartenere
    #            allo stesso emittente, altrimenti E_PERMESSO_NEGATO (403)
    # Perimetro: sola lettura.
    # Risultato: dict {results: [...]} pronto per success_response.
    def list_utilities_for_ba(
        self,
        *,
        billing_account_id: int,
        ruolo_codice_soggetto: str,
        user_emittente_id: int | None,
        is_superuser: bool = False,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.list_utilities_for_ba"

        # billing_account_id arriva sempre dall'URL converter <int:...>
        # nelle view: nessuna validazione manuale qui.
        # Validazione ruolo: whitelist a 3 valori, normalizzata upper.
        cleaned_ruolo = (ruolo_codice_soggetto or "").strip().upper()
        ErrorManager.require(
            cleaned_ruolo in _ALLOWED_RUOLI_BA,
            code="E_ANAG_VALIDAZIONE",
            message="Ruolo soggetto non valido per BA utilities.",
            detail=f"ruolo deve essere uno di {sorted(_ALLOWED_RUOLI_BA)}.",
            context={"ruolo": ruolo_codice_soggetto},
            function_name=function_name,
            log_to_db=False,
        )

        repository = BillingAccountRepository()

        # 404 esplicito su BA inesistente per non leakare 403 sugli id
        # non validi (la fn_get_emittente_fiscale_pk farebbe fallback al
        # default globale e maschererebbe l'errore).
        if not repository.exists(billing_account_id):
            raise ServiceError(
                code="E_ANAG_NOT_FOUND",
                message="Billing account non trovato.",
                detail=f"Nessun billing_account con id={billing_account_id}.",
            )

        # Scope check sull'emittente del BA. Bypass per superuser e per
        # admin globale / "0 emittenti" (user_emittente_id is None).
        if not is_superuser and user_emittente_id is not None:
            ba_emittente_id = repository.get_emittente_fiscale_id(billing_account_id)
            if ba_emittente_id != user_emittente_id:
                raise ServiceError(
                    code="E_PERMESSO_NEGATO",
                    message=(
                        "Billing account fuori dallo scope emittente "
                        "dell'utente corrente."
                    ),
                )

        results = LookupRepository().list_utilities_per_billing_account(
            billing_account_id=billing_account_id,
            ruolo_codice_soggetto=cleaned_ruolo,
        )
        return {"results": results}

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
