# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di lettura per le dashboard configurabili — espone:
#        - get_dashboard_config(): wrapper su
#          `ui.fn_resolve_dashboard_config` con derivazione automatica
#          `emittente_fiscale_id` e traduzione DatabaseError P0001 in
#          ServiceError.
#        - get_catalogo(): pool widget selezionabili per la modale di
#          personalizzazione. Riusa get_dashboard_config come single
#          source of truth dei permessi: la fn DB fa gia' il merge dei
#          widget nuovi (visibile=FALSE) e il filtro area/azione, quindi
#          il pool e' esattamente `widget[]` — la modale non puo'
#          offrire un widget proibito.
#        Gemello di `UiService` per le liste.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.dashboard_repository import DashboardRepository

__all__ = [
    "DashboardService",
    "E_UI_DASHBOARD_NON_TROVATA",
    "E_UI_GENERIC_FAILED",
]


# Codici errore registrati in apps/core/services/error_policies.py.
E_UI_DASHBOARD_NON_TROVATA = "E_UI_DASHBOARD_NON_TROVATA"
E_UI_GENERIC_FAILED = "E_UI_GENERIC_FAILED"  # fallback DatabaseError ignote

# Marker substring per riconoscere errori del DB: il codice originale
# sopravvive anche passando dal MESSAGE_TEXT del RAISE.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (E_UI_DASHBOARD_NON_TROVATA, ("E_UI_DASHBOARD_NON_TROVATA",)),
)


class DashboardService:
    """Facade lettura dashboard configurabili (schema `ui`)."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self._repo = repository or DashboardRepository()

    # Scopo: Risolve la configurazione effettiva della dashboard per
    #        l'utente autenticato. `emittente_fiscale_id` derivato 1:1
    #        dall'utente (admin globale -> None: la fn DB lo gestisce).
    # Risultato: dict `{widget[], dimensione_max, widget_nuovi,
    #        preset_aggiornato}` gia' filtrato per permessi.
    def get_dashboard_config(
        self,
        user: Any,
        dashboard_codice: str,
    ) -> dict[str, Any]:
        emittente_fiscale_id = PermissionResolver.get_emittente_for_user(user)
        try:
            config = self._repo.resolve_dashboard_config(
                dashboard_codice=dashboard_codice,
                auth_user_id=user.id,
                emittente_fiscale_id=emittente_fiscale_id,
            )
        except DatabaseError as exc:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=_KNOWN_DB_ERROR_MARKERS,
                fallback_code=E_UI_GENERIC_FAILED,
                message="Errore risoluzione dashboard.",
                context={
                    "dashboard_codice": dashboard_codice,
                    "auth_user_id": user.id,
                },
                function_name="ui_service.dashboard.get_dashboard_config",
            )

        # Difensivo: la fn DB solleva sempre E_UI_DASHBOARD_NON_TROVATA
        # quando il codice non esiste; questo path e' raggiungibile solo
        # per regressioni del contratto fn.
        if not config:
            ErrorManager.raise_error(
                code=E_UI_DASHBOARD_NON_TROVATA,
                message="Dashboard non trovata.",
                detail=f"codice dashboard: '{dashboard_codice}'",
                context={"dashboard_codice": dashboard_codice},
            )

        return config

    # Scopo: Pool widget selezionabili per la modale di personalizzazione.
    #        A differenza delle liste NON serve una seconda query di
    #        catalogo: la fn DB arricchisce gia' ogni widget con i campi
    #        freschi di `ui.widget` (etichetta, i18n key, tipo, deep_link,
    #        contatore_key, soglia) e include i widget non visibili
    #        (merge §4 con `visibile=FALSE`). Il pool e' quindi la lista
    #        completa restituita, gia' depurata dai widget proibiti.
    def get_catalogo(
        self,
        user: Any,
        dashboard_codice: str,
    ) -> dict[str, Any]:
        config = self.get_dashboard_config(user, dashboard_codice)
        return {
            "widget": config.get("widget") or [],
            "dimensione_max": config.get("dimensione_max"),
        }
