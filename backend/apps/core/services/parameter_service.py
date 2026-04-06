# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per parametri di sistema con risoluzione override.
#        Facade riutilizzabile da qualsiasi dominio per leggere
#        valori da config.parameters + config.parameter_overrides.
#        Supporta: risoluzione singola/multipla, lista per utente,
#        CRUD override personale utente.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.db.parameter_repository import ParameterRepository
from apps.core.services.error_manager import ErrorManager


class ParameterService:
    """Facade per parametri di sistema con risoluzione override."""

    def __init__(self) -> None:
        self._repo = ParameterRepository()

    # Scopo: Risolve un singolo parametro con override per l'utente.
    #        Lancia errore se il parametro non esiste o non ha valore.
    def get_parameter(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> str:
        value = self._repo.get_parameter(
            code, django_user_id, group_ids, emittente_fiscale_id,
        )
        ErrorManager.require(
            value is not None,
            code="E_PARAMETER_NOT_FOUND",
            message=f"Parametro '{code}' non trovato o senza valore.",
        )
        assert value is not None
        return value

    # Scopo: Risolve un singolo parametro e lo converte a intero.
    #        Utile per parametri che contengono ID (es. DEFAULT_IVA_ID).
    def get_parameter_int(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> int:
        value = self.get_parameter(
            code, django_user_id, group_ids, emittente_fiscale_id,
        )
        try:
            return int(value)
        except (ValueError, TypeError):
            ErrorManager.raise_error(
                code="E_PARAMETER_VALIDATION",
                message=f"Parametro '{code}' non convertibile a intero.",
                detail=f"Valore attuale: '{value}'",
            )
            raise  # unreachable, per type checker

    # Scopo: Risolve N parametri in un colpo con override utente.
    #        Restituisce dizionario {code: valore}. I parametri non trovati
    #        vengono esclusi dal risultato (nessun errore).
    def get_defaults(
        self,
        codes: list[str],
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, str]:
        return self._repo.get_parameters(
            codes, django_user_id, group_ids, emittente_fiscale_id,
        )

    # Scopo: Restituisce la lista completa dei parametri con i valori a ogni
    #        livello di scope e il valore risolto finale per l'utente.
    def list_parameters_for_user(
        self,
        django_user_id: int,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> list[dict]:
        return self._repo.list_for_user(
            django_user_id, group_ids, emittente_fiscale_id,
        )

    # Scopo: Crea o aggiorna un override personale dell'utente per un parametro.
    def upsert_user_override(
        self,
        parameter_code: str,
        django_user_id: int,
        value: str,
    ) -> int:
        ErrorManager.require(
            bool(parameter_code and parameter_code.strip()),
            code="E_PARAMETER_VALIDATION",
            message="Codice parametro obbligatorio.",
        )
        ErrorManager.require(
            django_user_id is not None and django_user_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID utente obbligatorio.",
        )
        return self._repo.upsert_user_override(parameter_code, django_user_id, value)

    # Scopo: Rimuove un override personale dell'utente.
    def delete_user_override(
        self,
        override_id: int,
        django_user_id: int,
    ) -> bool:
        ErrorManager.require(
            override_id is not None and override_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID override obbligatorio.",
        )
        deleted = self._repo.delete_user_override(override_id, django_user_id)
        ErrorManager.require(
            deleted,
            code="E_PARAMETER_NOT_FOUND",
            message="Override non trovato o non appartenente all'utente.",
        )
        return deleted

    # Scopo: Crea o aggiorna un override a livello emittente per un parametro.
    #        Riservato agli admin: il check di permesso e' a carico della view.
    def upsert_emittente_override(
        self,
        parameter_code: str,
        emittente_fiscale_id: int,
        value: str,
    ) -> int:
        ErrorManager.require(
            bool(parameter_code and parameter_code.strip()),
            code="E_PARAMETER_VALIDATION",
            message="Codice parametro obbligatorio.",
        )
        ErrorManager.require(
            emittente_fiscale_id is not None and emittente_fiscale_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID emittente fiscale obbligatorio.",
        )
        return self._repo.upsert_emittente_override(
            parameter_code, emittente_fiscale_id, value,
        )

    # Scopo: Rimuove un override a livello emittente.
    def delete_emittente_override(
        self,
        override_id: int,
        emittente_fiscale_id: int,
    ) -> bool:
        ErrorManager.require(
            override_id is not None and override_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID override obbligatorio.",
        )
        ErrorManager.require(
            emittente_fiscale_id is not None and emittente_fiscale_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID emittente fiscale obbligatorio.",
        )
        deleted = self._repo.delete_emittente_override(override_id, emittente_fiscale_id)
        ErrorManager.require(
            deleted,
            code="E_PARAMETER_NOT_FOUND",
            message="Override emittente non trovato.",
        )
        return deleted

    # Scopo: Risolve l'emittente_fiscale_id dell'utente dal bridge HR.
    def get_emittente_fiscale_id_for_user(self, auth_user_id: int) -> int | None:
        return self._repo.get_emittente_fiscale_id_for_user(auth_user_id)
