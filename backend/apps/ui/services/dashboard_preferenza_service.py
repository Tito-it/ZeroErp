# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di scrittura per `ui.dashboard_preferenza_utente` —
#        il corpo deve essere un oggetto con almeno una chiave (la forma la
#        giudica il guard del DB), UPSERT col preset di base di oggi (lo
#        snapshot lo scrive il DB), delete idempotente, «ignora» del banner
#        preset aggiornato.
#        Gemello di `ListaPreferenzaService`.
#
#        Forma della `configurazione` persistita (la giudica
#        `ui.fn_check_forma_configurazione`):
#            {"widget": [{"codice", "ordine", "visibile"}],
#             "dimensione_max": int}
#        La preferenza porta SOLO il codice widget (brief DB §3d): tutti
#        gli altri campi (etichetta, deep_link, contatore_key, soglia)
#        sono riletti freschi dal catalogo dalla fn di risoluzione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.dashboard_repository import DashboardRepository
from apps.ui.services._preferenza import (
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    preset_base_id_di_oggi,
    richiedi_preferenza_non_vuota,
)

__all__ = [
    "DashboardPreferenzaService",
    "E_UI_DASHBOARD_NON_TROVATA",
    "E_UI_PREFERENZA_VALIDAZIONE",
    "E_UI_PREFERENZA_NON_TROVATA",
]


E_UI_DASHBOARD_NON_TROVATA = "E_UI_DASHBOARD_NON_TROVATA"

# ⛔ Nessuna whitelist e nessun tetto qui: chiavi, voci, codici doppi e il
#    tetto 1-100 di `dimensione_max` li giudica il guard del DB
#    (`E_UI_CONFIGURAZIONE_FORMA`, BE8 e BE11 di brief-db-revisione-ui).


class DashboardPreferenzaService:
    """Facade scrittura preferenza utente per una dashboard."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self._repo = repository or DashboardRepository()

    # Scopo: Risolve `dashboard_codice -> dashboard_id` con 404 parlante
    #        se la dashboard non esiste o non e' attiva.
    def _require_dashboard_id(self, dashboard_codice: str) -> int:
        dashboard_id = self._repo.get_dashboard_id(dashboard_codice)
        ErrorManager.require(
            dashboard_id is not None,
            code=E_UI_DASHBOARD_NON_TROVATA,
            message="Dashboard non trovata.",
            detail=f"codice dashboard: '{dashboard_codice}'",
            context={"dashboard_codice": dashboard_codice},
        )
        assert dashboard_id is not None
        return dashboard_id

    # Scopo: UPSERT preferenza utente per (auth_user, dashboard_codice).
    #        Valida il JSONB, legge il preset di base di oggi dalla risoluzione
    #        (per il badge "preset aggiornato") e materializza il record.
    def upsert(
        self,
        user: Any,
        dashboard_codice: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # 1. Dashboard deve esistere
        dashboard_id = self._require_dashboard_id(dashboard_codice)

        # 2. Un oggetto con almeno una chiave; la forma la giudica il DB
        configurazione = self._validate_payload(payload)

        # 3. Il preset di base di oggi, dalla risoluzione (stesso emittente
        #    della lettura della dashboard: la base salvata e' quella che
        #    l'utente vede). Lo snapshot lo scrive il trigger del DB.
        emittente_id = PermissionResolver.get_emittente_for_user(user)
        preset_id = preset_base_id_di_oggi(
            self._repo.resolve_dashboard_config(
                dashboard_codice=dashboard_codice,
                auth_user_id=user.id,
                emittente_fiscale_id=emittente_id,
            )
        )

        # 4. UPSERT
        pref_id = self._repo.upsert_preferenza(
            auth_user_id=user.id,
            dashboard_id=dashboard_id,
            configurazione=configurazione,
            preset_base_id=preset_id,
        )

        return {
            "id": pref_id,
            "preset_base_id": preset_id,
        }

    # Scopo: Elimina preferenza per (user, dashboard_codice). Idempotente:
    #        200 anche se non esisteva. Solleva E_UI_DASHBOARD_NON_TROVATA
    #        se la dashboard stessa non esiste (protezione path errati).
    def delete(
        self,
        user: Any,
        dashboard_codice: str,
    ) -> dict[str, Any]:
        dashboard_id = self._require_dashboard_id(dashboard_codice)

        deleted = self._repo.delete_preferenza(
            auth_user_id=user.id,
            dashboard_id=dashboard_id,
        )
        return {"deleted": deleted}

    # Scopo: «Ignora» del banner preset aggiornato: riallinea lo snapshot
    #        del preset di base (come `ListaPreferenzaService`). Il flag
    #        `preset_aggiornato` della fn torna FALSE finche' il contenuto
    #        del preset non cambia di nuovo.
    def ignore_preset_update(
        self,
        user: Any,
        dashboard_codice: str,
    ) -> dict[str, Any]:
        dashboard_id = self._require_dashboard_id(dashboard_codice)

        ignored = self._repo.riallinea_snapshot_base(
            auth_user_id=user.id,
            dashboard_id=dashboard_id,
        )
        ErrorManager.require(
            ignored,
            code=E_UI_PREFERENZA_NON_TROVATA,
            message="Preferenza utente non trovata per questa dashboard.",
            detail=(
                "Nessuna preferenza salvata per "
                f"(user_id={user.id}, codice='{dashboard_codice}')."
            ),
            context={"dashboard_codice": dashboard_codice},
        )

        return {"ignored": True}

    # Scopo: La configurazione da salvare: il corpo cosi' com'e', se e' un
    #        oggetto con almeno una chiave (BB `richiedi_preferenza_non_vuota`).
    #        La forma, codici doppi e tetto 1-100 di `dimensione_max` compresi,
    #        la giudica il DB (vedi il BB).
    def _validate_payload(self, payload: Any) -> dict[str, Any]:
        return richiedi_preferenza_non_vuota(
            payload, message="Preferenza dashboard non valida.",
        )
