# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from apps.config.db.utilities_tipi_ruolo_repository import (
    UtilitiesTipiRuoloRepository,
)
from apps.core.services.error_manager import ErrorManager


# Codici errore (registrati in apps/core/services/error_policies.py)
E_CONFIG_VALIDATION = "E_CONFIG_VALIDATION"
E_CONFIG_MATRICE_NOT_FOUND = "E_CONFIG_MATRICE_NOT_FOUND"
E_CONFIG_MATRICE_DUPLICATA = "E_CONFIG_MATRICE_DUPLICATA"
E_CONFIG_MATRICE_FK = "E_CONFIG_MATRICE_FK"

# Whitelist colonne ammesse per ORDER BY (riflette repository).
_ORDER_BY_VALIDI: frozenset[str] = frozenset({
    "utility_codice",
    "utility_descrizione",
    "tipo_ruolo_codice",
    "tipo_ruolo_descrizione",
    "attivo",
    "data_insert",
    "data_update",
})

# Chiavi ammesse in payload create (FK + flag opzionale).
_CREATE_KEYS: frozenset[str] = frozenset({"utility_id", "tipo_ruolo_id", "attivo"})

# Chiavi ammesse in payload update: solo `attivo`. Le FK sono immutabili.
_UPDATE_KEYS: frozenset[str] = frozenset({"attivo"})


class UtilitiesTipiRuoloService:
    """Service admin per la matrice utilities x tipi_ruolo."""

    def __init__(self) -> None:
        self._repo = UtilitiesTipiRuoloRepository()

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
        limit: int = 25,
        offset: int = 0,
        order_by: str = "utility_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ErrorManager.require(
            order_by in _ORDER_BY_VALIDI,
            code=E_CONFIG_VALIDATION,
            message="Parametri ordinamento non validi.",
            detail=f"order_by deve essere uno tra: {', '.join(sorted(_ORDER_BY_VALIDI))}",
            context={"order_by": order_by},
        )
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
        self._guard_id(record_id, field="record_id")
        result = self._repo.get_matrice(record_id)
        ErrorManager.require(
            result is not None,
            code=E_CONFIG_MATRICE_NOT_FOUND,
            message="Riga matrice utilities/ruoli non trovata.",
            context={"record_id": record_id},
        )
        assert result is not None
        return result

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova riga di matrice. Valida le FK come interi positivi
    #        e mappa eventuali violazioni UNIQUE/FK su codici errore parlanti.
    def create_matrice(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_keys(payload, allowed=_CREATE_KEYS)

        utility_id = self._extract_required_id(payload, "utility_id")
        tipo_ruolo_id = self._extract_required_id(payload, "tipo_ruolo_id")
        attivo = self._extract_optional_bool(payload, "attivo")

        try:
            new_id = self._repo.create_matrice(
                utility_id=utility_id,
                tipo_ruolo_id=tipo_ruolo_id,
                attivo=attivo,
            )
        except IntegrityError as exc:
            self._raise_integrity_error(
                exc,
                context={
                    "utility_id": utility_id,
                    "tipo_ruolo_id": tipo_ruolo_id,
                },
            )
            raise  # pragma: no cover — _raise_integrity_error sempre solleva
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
        self._guard_id(record_id, field="record_id")
        # Rifiuta tentativi di modifica delle FK (immutabili)
        forbidden = sorted(k for k in payload if k in {"utility_id", "tipo_ruolo_id"})
        ErrorManager.require(
            not forbidden,
            code=E_CONFIG_VALIDATION,
            message="Le colonne utility_id e tipo_ruolo_id sono immutabili.",
            detail=f"Campi non modificabili: {', '.join(forbidden)}",
            context={"forbidden_keys": forbidden, "record_id": record_id},
        )
        self._validate_keys(payload, allowed=_UPDATE_KEYS)

        attivo = self._extract_optional_bool(payload, "attivo")
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
    #        riga matrice indicata. Solo letture.
    def list_usage(
        self,
        record_id: int,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        # Valida l'esistenza della riga matrice prima di leggere usage.
        self.get_matrice(record_id)
        return self._repo.list_emittenti_usage(record_id, limit=limit, offset=offset)

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Verifica che le chiavi del payload siano nella whitelist consentita.
    @staticmethod
    def _validate_keys(payload: dict[str, Any], *, allowed: frozenset[str]) -> None:
        unknown = sorted(k for k in payload if k not in allowed)
        ErrorManager.require(
            not unknown,
            code=E_CONFIG_VALIDATION,
            message="Payload matrice non valido.",
            detail=f"Campi non supportati: {', '.join(unknown)}",
            context={"unknown_keys": unknown},
        )

    # Scopo: Verifica che un id sia int positivo, altrimenti solleva validation.
    @staticmethod
    def _guard_id(value: Any, *, field: str) -> None:
        ErrorManager.require(
            isinstance(value, int) and not isinstance(value, bool) and value > 0,
            code=E_CONFIG_VALIDATION,
            message=f"Identificatore '{field}' non valido.",
            context={field: value},
        )

    # Scopo: Estrae un id obbligatorio dal payload come int positivo.
    @staticmethod
    def _extract_required_id(payload: dict[str, Any], key: str) -> int:
        raw = payload.get(key)
        ErrorManager.require(
            raw is not None,
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' obbligatorio.",
            context={key: raw},
        )
        # Accetta int o stringa numerica; rifiuta bool e altri tipi.
        if isinstance(raw, bool):
            ErrorManager.raise_error(
                code=E_CONFIG_VALIDATION,
                message=f"Campo '{key}' deve essere un intero.",
                context={key: raw},
            )
        if isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and raw.strip().isdigit():
            value = int(raw.strip())
        else:
            ErrorManager.raise_error(
                code=E_CONFIG_VALIDATION,
                message=f"Campo '{key}' deve essere un intero positivo.",
                context={key: raw},
            )
            raise AssertionError("unreachable")  # pragma: no cover
        ErrorManager.require(
            value > 0,
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' deve essere un intero positivo.",
            context={key: value},
        )
        return value

    # Scopo: Estrae un bool opzionale dal payload (None se assente).
    @staticmethod
    def _extract_optional_bool(payload: dict[str, Any], key: str) -> bool | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if isinstance(value, bool):
            return value
        # Accetta solo bool stretti per evitare ambiguita' tipo "0"/"false".
        ErrorManager.raise_error(
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' deve essere booleano.",
            context={key: value},
        )
        raise AssertionError("unreachable")  # pragma: no cover

    # Scopo: Mappa un IntegrityError su un codice errore parlante.
    #        UNIQUE → DUPLICATA, FK → FK, altrimenti VALIDATION.
    @staticmethod
    def _raise_integrity_error(exc: IntegrityError, *, context: dict[str, Any]) -> None:
        msg = str(exc).lower()
        if "uq_utilities_tipi_ruolo" in msg or "unique" in msg:
            ErrorManager.raise_error(
                code=E_CONFIG_MATRICE_DUPLICATA,
                message="Esiste gia' una riga matrice per questa coppia utility/tipo ruolo.",
                detail=str(exc),
                context=context,
                cause=exc,
            )
        if "foreign key" in msg or "fk_utilities_tipi_ruolo" in msg:
            ErrorManager.raise_error(
                code=E_CONFIG_MATRICE_FK,
                message="Utility o tipo ruolo inesistente.",
                detail=str(exc),
                context=context,
                cause=exc,
            )
        ErrorManager.raise_error(
            code=E_CONFIG_VALIDATION,
            message="Violazione vincolo DB su matrice utilities/ruoli.",
            detail=str(exc),
            context=context,
            cause=exc,
        )
