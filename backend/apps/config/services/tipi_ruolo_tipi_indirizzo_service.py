# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per la matrice config.tipi_ruolo_tipi_indirizzo.
#        Espone CRUD admin con validazione payload, mapping IntegrityError
#        sui codici errore centralizzati. Pattern identico a
#        utilities_tipi_ruolo_service.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.config.db.tipi_ruolo_tipi_indirizzo_repository import (
    TipiRuoloTipiIndirizzoRepository,
)
from apps.core.services.error_manager import ErrorManager


# Codici errore (registrati in apps/core/services/error_policies.py)
E_CONFIG_VALIDATION = "E_CONFIG_VALIDATION"
E_CONFIG_MATRICE_NOT_FOUND = "E_CONFIG_MATRICE_NOT_FOUND"
E_CONFIG_MATRICE_DUPLICATA = "E_CONFIG_MATRICE_DUPLICATA"
E_CONFIG_MATRICE_FK = "E_CONFIG_MATRICE_FK"

# Whitelist colonne ammesse per ORDER BY (riflette repository).
_ORDER_BY_VALIDI: frozenset[str] = frozenset({
    "tipo_ruolo_codice",
    "tipo_ruolo_descrizione",
    "tipo_indirizzo_codice",
    "tipo_indirizzo_descrizione",
    "obbligatorio",
    "attivo",
    "data_insert",
    "data_update",
})

# Chiavi ammesse in payload create.
_CREATE_KEYS: frozenset[str] = frozenset({
    "tipo_ruolo_id", "tipo_indirizzo_id", "obbligatorio",
    "fallback_tipo_indirizzo_id", "attivo",
})

# Chiavi ammesse in payload update: attivo, obbligatorio, fallback. FK immutabili.
_UPDATE_KEYS: frozenset[str] = frozenset({
    "attivo", "obbligatorio", "fallback_tipo_indirizzo_id",
})

# FK immutabili — tentativi di modifica rifiutati.
_IMMUTABLE_FKS: frozenset[str] = frozenset({"tipo_ruolo_id", "tipo_indirizzo_id"})


class TipiRuoloTipiIndirizzoService:
    """Service admin per la matrice tipi_ruolo x tipi_indirizzo."""

    def __init__(self) -> None:
        self._repo = TipiRuoloTipiIndirizzoRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice con validazione order_by/dir.
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        tipo_ruolo_id: int | None = None,
        tipo_indirizzo_id: int | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "tipo_ruolo_descrizione",
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
            tipo_ruolo_id=tipo_ruolo_id,
            tipo_indirizzo_id=tipo_indirizzo_id,
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
            message="Riga matrice indirizzi/ruoli non trovata.",
            context={"record_id": record_id},
        )
        assert result is not None
        return result

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova riga di matrice.
    def create_matrice(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_keys(payload, allowed=_CREATE_KEYS)

        tipo_ruolo_id = self._extract_required_id(payload, "tipo_ruolo_id")
        tipo_indirizzo_id = self._extract_required_id(payload, "tipo_indirizzo_id")
        obbligatorio = self._extract_optional_bool(payload, "obbligatorio")
        attivo = self._extract_optional_bool(payload, "attivo")
        fallback_tipo_indirizzo_id = self._extract_optional_id(payload, "fallback_tipo_indirizzo_id")

        try:
            new_id = self._repo.create_matrice(
                tipo_ruolo_id=tipo_ruolo_id,
                tipo_indirizzo_id=tipo_indirizzo_id,
                obbligatorio=obbligatorio,
                fallback_tipo_indirizzo_id=fallback_tipo_indirizzo_id,
                attivo=attivo,
            )
        except IntegrityError as exc:
            self._raise_integrity_error(
                exc,
                context={
                    "tipo_ruolo_id": tipo_ruolo_id,
                    "tipo_indirizzo_id": tipo_indirizzo_id,
                },
            )
            raise  # pragma: no cover
        return self.get_matrice(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una riga matrice (attivo, obbligatorio, fallback).
    #        FK immutabili.
    def update_matrice(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._guard_id(record_id, field="record_id")
        # Rifiuta tentativi di modifica delle FK
        forbidden = sorted(k for k in payload if k in _IMMUTABLE_FKS)
        ErrorManager.require(
            not forbidden,
            code=E_CONFIG_VALIDATION,
            message="Le colonne tipo_ruolo_id e tipo_indirizzo_id sono immutabili.",
            detail=f"Campi non modificabili: {', '.join(forbidden)}",
            context={"forbidden_keys": forbidden, "record_id": record_id},
        )
        self._validate_keys(payload, allowed=_UPDATE_KEYS)

        fields: dict[str, Any] = {}
        attivo = self._extract_optional_bool(payload, "attivo")
        if attivo is not None:
            fields["attivo"] = attivo
        obbligatorio = self._extract_optional_bool(payload, "obbligatorio")
        if obbligatorio is not None:
            fields["obbligatorio"] = obbligatorio
        if "fallback_tipo_indirizzo_id" in payload:
            raw = payload["fallback_tipo_indirizzo_id"]
            fields["fallback_tipo_indirizzo_id"] = int(raw) if raw is not None else None

        ErrorManager.require(
            bool(fields),
            code=E_CONFIG_VALIDATION,
            message="Nessun campo aggiornabile fornito.",
            context={"record_id": record_id},
        )

        try:
            updated = self._repo.update_matrice(record_id, fields)
        except IntegrityError as exc:
            self._raise_integrity_error(exc, context={"record_id": record_id})
            raise  # pragma: no cover
        ErrorManager.require(
            updated,
            code=E_CONFIG_MATRICE_NOT_FOUND,
            message="Riga matrice indirizzi/ruoli non trovata.",
            context={"record_id": record_id},
        )
        return self.get_matrice(record_id)

    # =================================================================
    # Helpers privati
    # =================================================================

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

    @staticmethod
    def _guard_id(value: Any, *, field: str) -> None:
        ErrorManager.require(
            isinstance(value, int) and not isinstance(value, bool) and value > 0,
            code=E_CONFIG_VALIDATION,
            message=f"Identificatore '{field}' non valido.",
            context={field: value},
        )

    @staticmethod
    def _extract_required_id(payload: dict[str, Any], key: str) -> int:
        raw = payload.get(key)
        ErrorManager.require(
            raw is not None,
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' obbligatorio.",
            context={key: raw},
        )
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

    @staticmethod
    def _extract_optional_id(payload: dict[str, Any], key: str) -> int | None:
        raw = payload.get(key)
        if raw is None:
            return None
        if isinstance(raw, bool):
            ErrorManager.raise_error(
                code=E_CONFIG_VALIDATION,
                message=f"Campo '{key}' deve essere un intero.",
                context={key: raw},
            )
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.strip().isdigit():
            return int(raw.strip())
        ErrorManager.raise_error(
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' deve essere un intero positivo o null.",
            context={key: raw},
        )
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _extract_optional_bool(payload: dict[str, Any], key: str) -> bool | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if isinstance(value, bool):
            return value
        ErrorManager.raise_error(
            code=E_CONFIG_VALIDATION,
            message=f"Campo '{key}' deve essere booleano.",
            context={key: value},
        )
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _raise_integrity_error(exc: IntegrityError, *, context: dict[str, Any]) -> None:
        msg = str(exc).lower()
        if "uq_tipi_ruolo_tipi_indirizzo" in msg or "unique" in msg:
            ErrorManager.raise_error(
                code=E_CONFIG_MATRICE_DUPLICATA,
                message="Esiste gia' una riga matrice per questa coppia tipo ruolo/tipo indirizzo.",
                detail=str(exc),
                context=context,
                cause=exc,
            )
        if "foreign key" in msg or "fk_" in msg:
            ErrorManager.raise_error(
                code=E_CONFIG_MATRICE_FK,
                message="Tipo ruolo, tipo indirizzo o fallback inesistente.",
                detail=str(exc),
                context=context,
                cause=exc,
            )
        ErrorManager.raise_error(
            code=E_CONFIG_VALIDATION,
            message="Violazione vincolo DB su matrice indirizzi/ruoli.",
            detail=str(exc),
            context=context,
            cause=exc,
        )
