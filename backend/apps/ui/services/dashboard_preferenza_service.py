# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di scrittura per `ui.dashboard_preferenza_utente` —
#        valida il JSONB in ingresso (whitelist chiavi anti-injection),
#        UPSERT con snapshot del preset di base, delete idempotente,
#        tombstone "ignora banner preset aggiornato".
#        Gemello di `ListaPreferenzaService`.
#
#        Forma della `configurazione` persistita (contratto fn DB):
#            {"widget": [{"codice", "ordine", "visibile"}],
#             "dimensione_max": int}
#        La preferenza porta SOLO il codice widget (brief DB §3d): tutti
#        gli altri campi (etichetta, deep_link, contatore_key, soglia)
#        sono riletti freschi dal catalogo dalla fn di risoluzione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.dashboard_repository import DashboardRepository
from apps.ui.services._preferenza import (
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    richiedi_preferenza_non_vuota,
)

__all__ = [
    "DashboardPreferenzaService",
    "E_UI_DASHBOARD_NON_TROVATA",
    "E_UI_PREFERENZA_VALIDAZIONE",
    "E_UI_PREFERENZA_NON_TROVATA",
]


E_UI_DASHBOARD_NON_TROVATA = "E_UI_DASHBOARD_NON_TROVATA"

# Whitelist root del payload preferenza dashboard.
_PAYLOAD_KEYS = frozenset({"widget", "dimensione_max"})
# Whitelist di un singolo widget nella preferenza (§3d: solo il codice
# identifica; ordine/visibile sono lo stato di layout scelto dall'utente).
_WIDGET_KEYS = frozenset({"codice", "ordine", "visibile"})

# Tetto difensivo sul numero di widget accettati in un salvataggio. Non e'
# il `dimensione_max` del preset (che limita quanti se ne MOSTRANO): e' una
# guardia anti-payload-abnorme, coerente col fatto che il pool reale e'
# comunque limitato da catalogo + permessi.
_MAX_WIDGET_PAYLOAD = 100


class DashboardPreferenzaService:
    """Facade scrittura preferenza utente per una dashboard."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self._repo = repository or DashboardRepository()
        self._validator = PayloadValidator(
            validation_code=E_UI_PREFERENZA_VALIDAZIONE,
        )

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
    #        Valida il JSONB, calcola lo snapshot del preset di base
    #        (per il badge "preset aggiornato") e materializza il record.
    def upsert(
        self,
        user: Any,
        dashboard_codice: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # 1. Dashboard deve esistere
        dashboard_id = self._require_dashboard_id(dashboard_codice)

        # 2. Whitelist + tipi del payload
        configurazione = self._validate_payload(payload)

        # 3. Snapshot preset di base coerente con la cascata della fn DB
        emittente_id = PermissionResolver.get_emittente_for_user(user)
        preset_id, preset_data_update = self._repo.get_preset_base_snapshot(
            dashboard_id=dashboard_id,
            auth_user_id=user.id,
            emittente_fiscale_id=emittente_id,
        )

        # 4. UPSERT
        pref_id = self._repo.upsert_preferenza(
            auth_user_id=user.id,
            dashboard_id=dashboard_id,
            configurazione=configurazione,
            preset_base_id=preset_id,
            preset_base_data_update=preset_data_update,
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

    # Scopo: Tombstone "Ignora banner preset aggiornato". Il flag
    #        `preset_aggiornato` della fn torna FALSE finche' il preset
    #        non viene modificato di nuovo.
    def ignore_preset_update(
        self,
        user: Any,
        dashboard_codice: str,
    ) -> dict[str, Any]:
        dashboard_id = self._require_dashboard_id(dashboard_codice)

        ignored = self._repo.set_preset_aggiornato_ignored(
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

    # Scopo: Valida il payload contro le whitelist e ritorna il dict
    #        normalizzato pronto per il salvataggio JSONB.
    def _validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            ErrorManager.raise_error(
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza dashboard non valida.",
                detail="Il payload deve essere un oggetto JSON.",
            )

        self._validator.validate_allowed_keys(
            payload, allowed=_PAYLOAD_KEYS,
            message="Preferenza dashboard non valida.",
        )

        config: dict[str, Any] = {}

        # widget: lista di oggetti normalizzati
        widget_raw = payload.get("widget")
        if widget_raw is not None:
            # Il tetto PRIMA di leggere le voci: un elenco smisurato non si
            # scorre. La forma (lista, ogni voce un oggetto) la giudica il BB.
            ErrorManager.require(
                not isinstance(widget_raw, list) or len(widget_raw) <= _MAX_WIDGET_PAYLOAD,
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza dashboard non valida.",
                detail=(
                    "Numero massimo di widget per salvataggio: "
                    f"{_MAX_WIDGET_PAYLOAD}."
                ),
            )
            widget = self._validator.voci(
                widget_raw, self._validate_widget, campo="widget",
                message="Preferenza dashboard non valida.",
            )
            # Codice duplicato = layout ambiguo: la fn DB fa JOIN sul
            # codice e produrrebbe la stessa card due volte.
            codici = [w["codice"] for w in widget]
            ErrorManager.require(
                len(codici) == len(set(codici)),
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza dashboard non valida.",
                detail="Codici widget duplicati nella preferenza.",
            )
            config["widget"] = widget

        # dimensione_max: int positivo, tetto allineato alla guardia payload
        dimensione_max = self._validator.optional_positive_int(
            payload, key="dimensione_max",
            message="Preferenza dashboard non valida.",
        )
        if dimensione_max is not None:
            ErrorManager.require(
                dimensione_max <= _MAX_WIDGET_PAYLOAD,
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza dashboard non valida.",
                detail=(
                    "dimensione_max massima ammessa: "
                    f"{_MAX_WIDGET_PAYLOAD}"
                ),
            )
            config["dimensione_max"] = dimensione_max

        # Ogni chiave e' facoltativa, ma una preferenza senza chiavi si toglie
        # col DELETE (BB `richiedi_preferenza_non_vuota`).
        return richiedi_preferenza_non_vuota(
            config, message="Preferenza dashboard non valida.",
        )

    # Scopo: Valida un singolo widget della preferenza. Whitelist chiavi,
    #        codice obbligatorio, ordine int positivo, visibile bool.
    def _validate_widget(self, raw: dict[str, Any], idx: int) -> dict[str, Any]:
        self._validator.validate_allowed_keys(
            raw, allowed=_WIDGET_KEYS,
            message=f"widget[{idx}]: campi non supportati.",
        )

        codice = self._validator.require_string(
            raw, key="codice",
            message=f"widget[{idx}]: 'codice' obbligatorio.",
        )
        out: dict[str, Any] = {"codice": codice}

        ordine = self._validator.optional_positive_int(
            raw, key="ordine",
            message=f"widget[{idx}]: 'ordine' deve essere intero positivo.",
        )
        if ordine is not None:
            out["ordine"] = ordine

        visibile = self._validator.optional_bool(raw, key="visibile")
        if visibile is not None:
            out["visibile"] = visibile

        return out
