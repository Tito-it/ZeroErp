# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.api.constants import DEFAULT_LIMIT
from apps.config.db.tipi_ruolo_tipi_indirizzo_repository import (
    _ORDER_COLS,
    TipiRuoloTipiIndirizzoRepository,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.non_editable_fields_helper import (
    compute_non_editable_fields,
)
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
# (review V6-B1): il match e' word-boundary.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_tipi_ruolo_tipi_indirizzo_tipo_ruolo_tipo": (
        E_CONFIG_MATRICE_DUPLICATA,
        "Esiste gia' una riga matrice per questa coppia tipo ruolo/tipo indirizzo.",
    ),
}
# Il terzo elemento e' il campo del form (presidio C2, §3-ter): la voce composta
# «tipo ruolo O tipo indirizzo» resta a due, non ha UN campo.
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_tipi_ruolo_tipi_indirizzo_tipo_ruolo": (
        E_CONFIG_MATRICE_FK,
        "Tipo ruolo o tipo indirizzo inesistente.",
    ),
    "fk_tipi_ruolo_tipi_indirizzo_fallback_tipo": (
        E_CONFIG_MATRICE_FK,
        "Tipo indirizzo fallback inesistente.",
        "fallback_tipo_indirizzo_id",
    ),
}

# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS`), unica fonte di verita' —
# stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Era una copia a
# mano: su offerte la stessa copia aveva gia' divergito in entrambi i versi.
_ORDER_BY_VALIDI: frozenset[str] = frozenset(_ORDER_COLS)

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

# Gap rispetto al registro DB `dbops.vw_non_editable_fields` (Fase 4 — A9).
# Le 2 dimensioni della matrice (ruolo, tipo_indirizzo) sono semanticamente
# immutabili (cambiarle = rimpiazzare la riga, vedi `_IMMUTABLE_FKS`).
# Esposte come metadata per il drawer di edit FE.
_NON_EDITABLE_GAPS: tuple[str, ...] = (
    "tipo_indirizzo_id",
    "tipo_ruolo_id",
)


class TipiRuoloTipiIndirizzoService:
    """Service admin per la matrice tipi_ruolo x tipi_indirizzo."""

    def __init__(self) -> None:
        self._repo = TipiRuoloTipiIndirizzoRepository()
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
        tipo_ruolo_id: int | None = None,
        tipo_indirizzo_id: int | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "tipo_ruolo_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_VALIDI, order_dir=order_dir)
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
    #        Arricchito con `non_editable_fields` + `fallback_options`
    #        (Fase 4 — A9/A10): il FE costruisce il drawer di edit usando
    #        questi metadata, niente round-trip aggiuntivo per la lookup
    #        dei tipi indirizzo candidati come fallback.
    def get_matrice(self, record_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        result = testata_o_not_found(
            self._repo.get_matrice, record_id,
            code=E_CONFIG_MATRICE_NOT_FOUND, message="Riga matrice indirizzi/ruoli non trovata.",
            id_name="record_id", function_name="tipi_ruolo_tipi_indirizzo_service.get_matrice",
        )
        result["non_editable_fields"] = self.get_non_editable_fields()
        result["fallback_options"] = self._compute_fallback_options(
            tipo_ruolo_id=result["tipo_ruolo_id"],
            tipo_indirizzo_id=result["tipo_indirizzo_id"],
        )
        return result

    # Scopo: Lista `non_editable_fields` per la matrice (Fase 4 — A9).
    def get_non_editable_fields(self) -> list[str]:
        return compute_non_editable_fields(
            "config", "tipi_ruolo_tipi_indirizzo",
            gaps=_NON_EDITABLE_GAPS,
        )

    # Scopo: Calcola la lista dei tipi indirizzo candidati come fallback per
    #        la riga (tipo_ruolo_id, tipo_indirizzo_id) (Fase 4 — A10).
    #        Esclude:
    #          - self-reference (un tipo non puo' essere fallback di se stesso);
    #          - cicli: se la catena di fallback del candidato C porta al
    #            tipo corrente, C creerebbe un loop A->B->...->A.
    #
    #        Carica una sola volta la sotto-matrice del ruolo dal repo e
    #        costruisce la mappa `tipo_indirizzo_id -> fallback_id` in
    #        memoria. La detection ciclo via DFS con `visited` set ferma
    #        anche cicli pre-esistenti senza dipendere dal `depth limit`.
    def _compute_fallback_options(
        self,
        *,
        tipo_ruolo_id: int,
        tipo_indirizzo_id: int,
    ) -> list[dict[str, Any]]:
        rows = self._repo.list_fallback_chain_for_ruolo(tipo_ruolo_id)
        fallback_map: dict[int, int | None] = {
            r["tipo_indirizzo_id"]: r["fallback_tipo_indirizzo_id"] for r in rows
        }

        def leads_to_self(start_id: int) -> bool:
            visited: set[int] = set()
            cur: int | None = start_id
            while cur is not None and cur not in visited:
                if cur == tipo_indirizzo_id:
                    return True
                visited.add(cur)
                cur = fallback_map.get(cur)
            return False

        options: list[dict[str, Any]] = []
        for r in rows:
            candidate_id = r["tipo_indirizzo_id"]
            if candidate_id == tipo_indirizzo_id:
                continue  # self-reference
            if leads_to_self(candidate_id):
                continue  # cycle
            options.append({
                "tipo_indirizzo_id": candidate_id,
                "codice": r["codice"],
                "descrizione": r["descrizione"],
            })
        return options

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova riga di matrice.
    def create_matrice(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload, allowed=_CREATE_KEYS, message="Payload matrice non valido."
        )

        tipo_ruolo_id = self._v.require_positive_int(payload, "tipo_ruolo_id")
        tipo_indirizzo_id = self._v.require_positive_int(payload, "tipo_indirizzo_id")
        obbligatorio = self._v.optional_bool(payload, "obbligatorio")
        attivo = self._v.optional_bool(payload, "attivo")
        fallback_tipo_indirizzo_id = self._v.optional_positive_int(
            payload, "fallback_tipo_indirizzo_id"
        )

        try:
            new_id = self._repo.create_matrice(
                tipo_ruolo_id=tipo_ruolo_id,
                tipo_indirizzo_id=tipo_indirizzo_id,
                obbligatorio=obbligatorio,
                fallback_tipo_indirizzo_id=fallback_tipo_indirizzo_id,
                attivo=attivo,
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_CONFIG_VALIDATION,
                fallback_message="Violazione vincolo DB su matrice indirizzi/ruoli.",
                context={
                    "tipo_ruolo_id": tipo_ruolo_id,
                    "tipo_indirizzo_id": tipo_indirizzo_id,
                },
            )
        return self.get_matrice(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una riga matrice (attivo, obbligatorio, fallback).
    #        FK immutabili.
    def update_matrice(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        self._v.reject_keys(
            payload,
            forbidden=_IMMUTABLE_FKS,
            reason="Le colonne tipo_ruolo_id e tipo_indirizzo_id sono immutabili.",
            context_extra={"record_id": record_id},
        )
        self._v.validate_allowed_keys(
            payload, allowed=_UPDATE_KEYS, message="Payload matrice non valido."
        )

        fields: dict[str, Any] = {}
        attivo = self._v.optional_bool(payload, "attivo")
        if attivo is not None:
            fields["attivo"] = attivo
        obbligatorio = self._v.optional_bool(payload, "obbligatorio")
        if obbligatorio is not None:
            fields["obbligatorio"] = obbligatorio
        if "fallback_tipo_indirizzo_id" in payload:
            # optional_positive_int: None se assente/None esplicito, altrimenti int > 0
            fields["fallback_tipo_indirizzo_id"] = self._v.optional_positive_int(
                payload, "fallback_tipo_indirizzo_id"
            )

        self._v.require_campi_da_aggiornare(
            fields,
            context={"record_id": record_id},
        )

        try:
            updated = self._repo.update_matrice(record_id, fields)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_CONFIG_VALIDATION,
                fallback_message="Violazione vincolo DB su matrice indirizzi/ruoli.",
                context={"record_id": record_id},
            )
        ErrorManager.require(
            updated,
            code=E_CONFIG_MATRICE_NOT_FOUND,
            message="Riga matrice indirizzi/ruoli non trovata.",
            context={"record_id": record_id},
        )
        return self.get_matrice(record_id)
