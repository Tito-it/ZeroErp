# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione matrice indirizzi per ruolo.
#        CRUD config.tipi_ruolo_tipi_indirizzo con logica attivo/valido_al.
#        In creazione valido_dal = oggi, attivo = true.
#        In update le chiavi (tipo_ruolo_id, tipo_indirizzo_id) non sono modificabili.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.matrice_indirizzi_repository import MatriceIndirizziRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import create_with_dedup
from apps.core.api.payload_validators import optional_bool, optional_int
from apps.core.services.error_manager import ErrorManager


class MatriceIndirizziService:
    """Service per gestione matrice indirizzi per ruolo."""

    def __init__(self) -> None:
        self._repo = MatriceIndirizziRepository()

    # Scopo: Lista paginata regole matrice.
    def list_regole(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_matrice(**params)

    # Scopo: Dettaglio singola regola.
    def get_regola(self, regola_id: int) -> dict[str, Any]:
        regola = self._repo.get_regola(regola_id)
        ErrorManager.require(regola is not None, code=E_ANAG_NOT_FOUND,
                             message="Regola matrice non trovata.")
        assert regola is not None
        return regola

    # Scopo: Crea regola matrice.
    #        tipo_ruolo_id e tipo_indirizzo_id obbligatori.
    #        valido_dal impostato a oggi dal repository.
    def crea_regola(self, payload: dict[str, Any]) -> dict[str, Any]:
        tipo_ruolo_id = optional_int(payload, "tipo_ruolo_id")
        ErrorManager.require(tipo_ruolo_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="tipo_ruolo_id obbligatorio.")

        tipo_indirizzo_id = optional_int(payload, "tipo_indirizzo_id")
        ErrorManager.require(tipo_indirizzo_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="tipo_indirizzo_id obbligatorio.")

        obbligatorio = optional_bool(payload, "obbligatorio")
        fallback_id = optional_int(payload, "fallback_tipo_indirizzo_id")

        # Guard: fallback diverso dal tipo indirizzo (check DB chk_tipi_ruolo_tipi_indirizzo_fallback_not_self,
        # ma messaggio user-friendly)
        if fallback_id is not None and fallback_id == tipo_indirizzo_id:
            ErrorManager.require(False, code=E_ANAG_VALIDAZIONE,
                                 message="Il fallback non puo' essere uguale al tipo indirizzo.")

        result = create_with_dedup(
            lambda: {"id": self._repo.create_regola(
                tipo_ruolo_id=tipo_ruolo_id,
                tipo_indirizzo_id=tipo_indirizzo_id,
                obbligatorio=obbligatorio,
                fallback_tipo_indirizzo_id=fallback_id,
            )},
            duplicate_message="Esiste gia' una regola per questo ruolo e tipo indirizzo.",
        )
        return result

    # Scopo: Aggiorna regola matrice.
    #        Le chiavi (tipo_ruolo_id, tipo_indirizzo_id) non sono modificabili.
    #        Logica attivo/valido_al gestita dal repository.
    def update_regola(self, regola_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        regola = self.get_regola(regola_id)

        # Filtra solo i campi ammessi
        data: dict[str, Any] = {}
        for key in ["obbligatorio", "attivo"]:
            val = payload.get(key)
            if val is not None:
                data[key] = bool(val)

        fallback_id = optional_int(payload, "fallback_tipo_indirizzo_id")
        if "fallback_tipo_indirizzo_id" in payload:
            # Guard: fallback diverso dal tipo indirizzo della riga
            if fallback_id is not None and fallback_id == regola["tipo_indirizzo_id"]:
                ErrorManager.require(False, code=E_ANAG_VALIDAZIONE,
                                     message="Il fallback non puo' essere uguale al tipo indirizzo.")
            data["fallback_tipo_indirizzo_id"] = fallback_id

        updated = self._repo.update_regola(regola_id, data)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Regola non trovata o nessun campo modificato.")
        return {"updated": True}
