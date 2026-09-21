# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per CRUD generico tabelle config.
#        Validazione rel in whitelist, errori DB tradotti, metadata.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db.config_crud_repository import ConfigCrudRepository
from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.dbops_repository import _REL_CONSENTITE
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import translate_db_errors

E_CONFIG_VALIDATION = "E_CORE_VALIDATION"
E_CONFIG_NOT_FOUND = "E_ANAG_NOT_FOUND"
E_CONFIG_DUPLICATO = "E_ANAG_DUPLICATO"


def _parse_rel(rel: str) -> tuple[str, str]:
    """Valida rel e restituisce (schema, table)."""
    ErrorManager.require(
        rel in _REL_CONSENTITE,
        code=E_CONFIG_VALIDATION,
        message=f"Tabella '{rel}' non consentita.",
    )
    schema, table = rel.split(".", 1)
    return schema, table


# Scopo: Le mappe vincolo → (codice, messaggio, campo) di `translate_db_errors`,
#        LETTE dal catalogo della tabella invece che scritte a mano per 90
#        tabelle. Fino al 2026-09-21 ogni IntegrityError era «Record gia'
#        esistente» — un CHECK violato, una FK sbagliata, un NOT NULL: tutti
#        «duplicato». Il campo si dichiara SOLO sui vincoli a una colonna
#        (`map_integrity_error`: un campo inventato accende l'input sbagliato).
def _mappe_vincoli(vincoli: list[dict[str, Any]]) -> dict[str, dict[str, tuple]]:
    mappe: dict[str, dict[str, tuple]] = {"unique": {}, "fk": {}, "check": {}}
    for v in vincoli:
        colonne = v["columns"]
        campo = colonne[0] if len(colonne) == 1 else None
        # Un CHECK di tabella senza colonne (`conkey` NULL) ha l'elenco vuoto:
        # si nomina il solo vincolo, non «per  (vincolo …)».
        elenco = ", ".join(colonne)
        su = f" per {elenco}" if elenco else ""
        if v["type"] == "unique":
            voce: tuple = (E_CONFIG_DUPLICATO, f"Esiste gia' un record con lo stesso valore di {elenco}.")
        elif v["type"] == "fk":
            voce = (E_CONFIG_VALIDATION, f"Il riferimento indicato in {elenco} non esiste.")
        else:
            voce = (E_CONFIG_VALIDATION, f"Valore non ammesso{su} (vincolo {v['name']}).")
        mappe[v["type"]][v["name"]] = voce + ((campo,) if campo else ())
    return mappe


class ConfigCrudService:
    """Service CRUD generico per tabelle config whitelisted."""

    def __init__(self) -> None:
        self._repo = ConfigCrudRepository()
        self._meta = ConfigMetadataRepository()

    # Scopo: Lista tabelle disponibili.
    def list_tables(self) -> list[dict[str, str]]:
        return ConfigCrudRepository.list_available_tables()

    # Scopo: Metadata colonne di una tabella.
    def get_metadata(self, rel: str) -> list[dict[str, Any]]:
        schema, table = _parse_rel(rel)
        return self._meta.get_table_columns(schema, table)

    # Scopo: Dettaglio record.
    def get_record(self, rel: str, record_id: int) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        result = self._repo.get_record(schema, table, record_id)
        ErrorManager.require(result is not None, code=E_CONFIG_NOT_FOUND, message="Record non trovato.")
        assert result is not None
        return result

    # Scopo: Il traduttore degli errori DB per UNA operazione su UNA tabella:
    #        IntegrityError → il vincolo violato col suo campo (mappe dal
    #        catalogo), P0001 dei trigger → il codice che il DB dichiara
    #        (`CODICE_NON_MODIFICABILE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`, …).
    def _db_errors(self, op: str, rel: str, schema: str, table: str) -> Any:
        mappe = _mappe_vincoli(self._meta.get_table_constraints(schema, table))
        return translate_db_errors(
            context={"op": f"config_crud.{op}", "rel": rel},
            fallback_code=E_CONFIG_VALIDATION,
            fallback_message="Il record viola un vincolo della tabella.",
            unique_constraints=mappe["unique"],
            fk_constraints=mappe["fk"],
            check_constraints=mappe["check"],
        )

    # Scopo: Crea record; gli errori DB arrivano tradotti, col campo.
    def create_record(self, rel: str, payload: dict[str, Any]) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        with self._db_errors("create", rel, schema, table):
            return self._repo.create_record(schema, table, payload)

    # Scopo: Aggiorna record; gli errori DB arrivano tradotti, col campo.
    def update_record(self, rel: str, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        with self._db_errors("update", rel, schema, table):
            updated = self._repo.update_record(schema, table, record_id, payload)
        ErrorManager.require(updated, code=E_CONFIG_NOT_FOUND, message="Record non trovato.")
        return {"updated": True}
