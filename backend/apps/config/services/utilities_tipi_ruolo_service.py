# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per la matrice config.utilities_tipi_ruolo.
#        Espone CRUD admin con validazione payload, mapping IntegrityError
#        sui codici errore centralizzati e lookup di utilizzo della riga
#        matrice da parte degli emittenti fiscali.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.api.constants import DEFAULT_LIMIT
from apps.config.db.utilities_tipi_ruolo_repository import (
    _ORDER_COLS,
    UtilitiesTipiRuoloRepository,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)


# Codici errore (registrati in apps/core/services/error_policies.py)
E_CONFIG_VALIDATION = "E_CONFIG_VALIDATION"
E_CONFIG_MATRICE_NOT_FOUND = "E_CONFIG_MATRICE_NOT_FOUND"
E_CONFIG_MATRICE_DUPLICATA = "E_CONFIG_MATRICE_DUPLICATA"
E_CONFIG_MATRICE_FK = "E_CONFIG_MATRICE_FK"

# Mapping vincoli DB -> codici errore applicativi. Nomi completi
# (review V6-B1): il match e' word-boundary, prefissi generici non
# matchano piu' i nomi estesi.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_utilities_tipi_ruolo_utility_tipo_ruolo": (
        E_CONFIG_MATRICE_DUPLICATA,
        "Esiste gia' una riga matrice per questa coppia utility/tipo ruolo.",
    ),
}
# Il terzo elemento e' il campo del form (presidio C2, §3-ter).
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_utilities_tipi_ruolo_utility": (
        E_CONFIG_MATRICE_FK,
        "Utility inesistente.",
        "utility_id",
    ),
    "fk_utilities_tipi_ruolo_tipo_ruolo": (
        E_CONFIG_MATRICE_FK,
        "Tipo ruolo inesistente.",
        "tipo_ruolo_id",
    ),
}

# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS`), unica fonte di verita' —
# stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Era una copia a
# mano: su offerte la stessa copia aveva gia' divergito in entrambi i versi.
_ORDER_BY_VALIDI: frozenset[str] = frozenset(_ORDER_COLS)

# Chiavi ammesse in payload create (FK + flag opzionale).
_CREATE_KEYS: frozenset[str] = frozenset({"utility_id", "tipo_ruolo_id", "attivo"})

# Chiavi ammesse in payload update: solo `attivo`. Le FK sono immutabili.
_UPDATE_KEYS: frozenset[str] = frozenset({"attivo"})


class UtilitiesTipiRuoloService:
    """Service admin per la matrice utilities x tipi_ruolo."""

    def __init__(self) -> None:
        self._repo = UtilitiesTipiRuoloRepository()
        self._v = PayloadValidator(validation_code=E_CONFIG_VALIDATION)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice con validazione order_by/dir.
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        utility_id: int | None = None,
        tipo_ruolo_id: int | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "utility_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_VALIDI, order_dir=order_dir)
        return self._repo.list_matrice(
            search=search,
            attivo=attivo,
            utility_id=utility_id,
            tipo_ruolo_id=tipo_ruolo_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

    # Scopo: Dettaglio singola riga matrice; solleva not found se assente.
    def get_matrice(self, record_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        result = testata_o_not_found(
            self._repo.get_matrice, record_id,
            code=E_CONFIG_MATRICE_NOT_FOUND, message="Riga matrice utilities/ruoli non trovata.",
            id_name="record_id", function_name="utilities_tipi_ruolo_service.get_matrice",
        )
        return result

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova riga di matrice. Valida le FK come interi positivi
    #        e mappa eventuali violazioni UNIQUE/FK su codici errore parlanti.
    def create_matrice(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload, allowed=_CREATE_KEYS, message="Payload matrice non valido."
        )

        utility_id = self._v.require_positive_int(payload, "utility_id")
        tipo_ruolo_id = self._v.require_positive_int(payload, "tipo_ruolo_id")
        attivo = self._v.optional_bool(payload, "attivo")

        try:
            new_id = self._repo.create_matrice(
                utility_id=utility_id,
                tipo_ruolo_id=tipo_ruolo_id,
                attivo=attivo,
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_CONFIG_VALIDATION,
                fallback_message="Violazione vincolo DB su matrice utilities/ruoli.",
                context={
                    "utility_id": utility_id,
                    "tipo_ruolo_id": tipo_ruolo_id,
                },
            )
        # Rumoroso se la riga appena inserita non viene trovata: solleva
        # E_CONFIG_MATRICE_NOT_FOUND invece di nascondere il bug con un dict
        # parziale.
        return self.get_matrice(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una riga matrice (solo flag attivo). Le FK sono
    #        immutabili: tentativi di modificarle vengono rifiutati con
    #        E_CONFIG_VALIDATION.
    def update_matrice(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        self._v.reject_keys(
            payload,
            forbidden=frozenset({"utility_id", "tipo_ruolo_id"}),
            reason="Le colonne utility_id e tipo_ruolo_id sono immutabili.",
            context_extra={"record_id": record_id},
        )
        self._v.validate_allowed_keys(
            payload, allowed=_UPDATE_KEYS, message="Payload matrice non valido."
        )

        attivo = self._v.optional_bool(payload, "attivo")
        ErrorManager.require(
            attivo is not None,
            code=E_CONFIG_VALIDATION,
            message="Nessun campo aggiornabile fornito.",
            detail="Per la matrice utility/tipo_ruolo l'unico campo modificabile e' 'attivo'.",
            context={"record_id": record_id},
        )
        assert attivo is not None

        updated = self._repo.update_matrice_attivo(record_id, attivo)
        ErrorManager.require(
            updated,
            code=E_CONFIG_MATRICE_NOT_FOUND,
            message="Riga matrice utilities/ruoli non trovata.",
            context={"record_id": record_id},
        )
        return self.get_matrice(record_id)

    # =================================================================
    # Utilizzo (emittenti fiscali)
    # =================================================================

    # Scopo: Restituisce conteggio + lista paginata degli emittenti che
    #        hanno gia' un override per la stessa coppia (utility, EF) della
    #        riga matrice indicata (lista `config.utilities_tipi_ruolo_usage`).
    #        Solo letture. Ricerca e ordinamento li risolve il repository sulla
    #        sua whitelist; la direzione estranea la rifiuta il BB SQL (400).
    def list_usage(
        self,
        record_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        # Valida l'esistenza della riga matrice prima di leggere usage.
        self.get_matrice(record_id)
        return self._repo.list_emittenti_usage(
            record_id,
            search=search, order_by=order_by, order_dir=order_dir,
            limit=limit, offset=offset,
        )

