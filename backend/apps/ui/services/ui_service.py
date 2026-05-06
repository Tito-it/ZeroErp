# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di lettura per personalizzazioni liste — espone:
#        - get_lista_config(): wrapper su `ui.fn_resolve_lista_config`
#          con derivazione automatica `emittente_fiscale_id` (1:1
#          operatore->emittente via PermissionResolver) e traduzione
#          DatabaseError P0001 in ServiceError.
#        - get_catalogo(): catalogo colonne per la modale di
#          personalizzazione (filtra colonne BLOCCATE riusando
#          get_lista_config — single source of truth permessi).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, NoReturn

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.ui_repository import UiRepository

__all__ = ["UiService", "E_UI_LISTA_NON_TROVATA", "E_UI_GENERIC_FAILED"]


# Codici errore registrati in apps/core/services/error_policies.py.
E_UI_LISTA_NON_TROVATA = "E_UI_LISTA_NON_TROVATA"
E_UI_GENERIC_FAILED = "E_UI_GENERIC_FAILED"  # fallback per DatabaseError ignote

# Marker substring per riconoscere errori del DB. Stessa strategia di
# `pricing_service._KNOWN_DB_ERROR_MARKERS`: il codice originale e'
# preservato anche quando passa dal MESSAGE_TEXT del RAISE.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (E_UI_LISTA_NON_TROVATA, ("E_UI_LISTA_NON_TROVATA",)),
)


class UiService:
    """Facade lettura schema `ui`."""

    def __init__(self, repository: UiRepository | None = None) -> None:
        self._repo = repository or UiRepository()

    # Scopo: Risolve la configurazione effettiva di una lista per l'utente
    #        autenticato. Deriva `emittente_fiscale_id` 1:1 dall'utente via
    #        `PermissionResolver.get_emittente_for_user` (admin globale ->
    #        None: la fn DB lo gestisce). Cattura DatabaseError P0001 e
    #        traduce in ServiceError preservando il codice originale.
    def get_lista_config(
        self,
        user: Any,
        lista_codice: str,
    ) -> dict[str, Any]:
        emittente_fiscale_id = PermissionResolver.get_emittente_for_user(user)
        try:
            config = self._repo.resolve_lista_config(
                lista_codice=lista_codice,
                auth_user_id=user.id,
                emittente_fiscale_id=emittente_fiscale_id,
            )
        except DatabaseError as exc:
            self._raise_db_error(
                exc,
                context={
                    "lista_codice": lista_codice,
                    "auth_user_id": user.id,
                },
                function_name="ui_service.get_lista_config",
            )

        # Difensivo: la fn DB solleva sempre E_UI_LISTA_NON_TROVATA via
        # fn_log_and_raise_error quando il codice non esiste; questo path
        # e' raggiungibile solo per regressioni del contratto fn.
        if not config:
            ErrorManager.raise_error(
                code=E_UI_LISTA_NON_TROVATA,
                message="Lista non trovata.",
                detail=f"codice lista: '{lista_codice}'",
                context={"lista_codice": lista_codice},
            )

        return config

    # Scopo: Catalogo colonne per la modale di personalizzazione.
    #        Strategia: riusa get_lista_config() — il suo risultato
    #        contiene gia' tutte le colonne del catalogo non BLOCCATE
    #        (la fn DB Step 3 fa il merge automatico delle nuove colonne
    #        e Step 5 rimuove le BLOCCATE). Poi arricchisce con i metadati
    #        ricchi del catalogo (etichetta, gruppo, formato, ecc.) che la
    #        fn DB non espone. 2 round-trip totali, error handling
    #        centralizzato in get_lista_config.
    def get_catalogo(
        self,
        user: Any,
        lista_codice: str,
    ) -> dict[str, Any]:
        # 1. Risoluzione (404 + permessi) — riusato per non duplicare logica.
        config = self.get_lista_config(user, lista_codice)
        codici_visibili = {
            c.get("codice")
            for c in (config.get("colonne") or [])
            if c.get("codice") is not None
        }

        # 2. Metadati ricchi delle colonne (single query con JOIN).
        colonne_meta = self._repo.list_colonne_by_codice(lista_codice)

        # 3. Arricchimento per intersezione: tieni solo i metadati delle
        #    colonne effettivamente visibili al profilo utente. Le colonne
        #    sensibili senza grant cadono qui — la modale non puo' offrire
        #    l'attivazione di una colonna proibita.
        colonne_visibili = [
            c for c in colonne_meta if c["codice"] in codici_visibili
        ]

        return {"colonne": colonne_visibili}

    # Scopo: Traduzione DatabaseError P0001 (raise_exception del DB) in
    #        ServiceError con codice originale preservato. `function_name`
    #        e' parametrizzato per il logging DB: ogni caller passa il
    #        proprio fully-qualified name.
    def _raise_db_error(
        self,
        exc: DatabaseError,
        *,
        context: dict[str, Any],
        function_name: str,
    ) -> NoReturn:
        msg = str(exc)
        matched_code: str | None = None
        for code_candidate, markers in _KNOWN_DB_ERROR_MARKERS:
            if all(marker in msg for marker in markers):
                matched_code = code_candidate
                break
        code = matched_code or E_UI_GENERIC_FAILED
        ErrorManager.raise_error(
            code=code,
            message="Errore risoluzione lista.",
            detail=msg,
            context=context,
            cause=exc,
            log_to_db=True,
            function_name=function_name,
        )
