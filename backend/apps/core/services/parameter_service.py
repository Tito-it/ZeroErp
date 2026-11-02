# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per parametri di sistema con risoluzione override.
#        Facade riutilizzabile da qualsiasi dominio per leggere
#        valori da config.parameters + config.parameter_overrides.
#        Supporta: risoluzione singola/multipla, lista per utente,
#        CRUD override personale utente.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db.parameter_repository import IMPOSTAZIONI_ORDER_COLUMNS, ParameterRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params


# Scopo: L'esito di un upsert di override: l'id, oppure 404
#        `E_PARAMETER_NOT_FOUND` se il parametro non esiste (il repository torna
#        None). Una sede per i tre livelli.
# ⛔ Fino al 2026-09-28 un codice inesistente arrivava all'INSERT con
#    `parameter_id` NULL: violazione NOT NULL, cioe' `E_DATABASE` 400 col
#    messaggio tecnico nascosto (E-9 dell'analisi difetti doc API core).
def _parametro_esistente(override_id: int | None, parameter_code: str) -> int:
    ErrorManager.require(
        override_id is not None,
        code="E_PARAMETER_NOT_FOUND",
        message=f"Parametro '{parameter_code}' non trovato.",
    )
    assert override_id is not None
    return override_id


class ParameterService:
    """Facade per parametri di sistema con risoluzione override."""

    def __init__(self) -> None:
        self._repo = ParameterRepository()

    # Scopo: Risolve un singolo parametro con override per l'utente.
    #        Lancia errore se il parametro non esiste o non ha valore.
    #        `categoria_cliente_id` opzionale: se fornito attiva il livello
    #        della cascata "categoria_cliente" (tra user e group), usato
    #        per soglie commerciali che dipendono dalla categoria del cliente.
    def get_parameter(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
    ) -> str:
        value = self._repo.get_parameter(
            code, django_user_id, group_ids, emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
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
        categoria_cliente_id: int | None = None,
    ) -> int:
        value = self.get_parameter(
            code, django_user_id, group_ids, emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
        )
        try:
            return int(value)
        except (ValueError, TypeError):
            ErrorManager.raise_error(
                code="E_PARAMETER_VALIDATION",
                message=f"Parametro '{code}' non convertibile a intero.",
                detail=f"Valore attuale: '{value}'",
            )

    # Scopo: Risolve un singolo parametro e lo converte a Decimal.
    #        Utile per parametri numerici non-id (percentuali, soglie, limiti).
    #        Raise E_PARAMETER_VALIDATION se il valore non e' convertibile —
    #        coerente con get_parameter_int; un parametro decimal malformato
    #        e' uno stato inconsistente del sistema che va corretto, non
    #        ignorato silenziosamente.
    def get_parameter_decimal(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
    ) -> Decimal:
        value = self.get_parameter(
            code, django_user_id, group_ids, emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
        )
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            ErrorManager.raise_error(
                code="E_PARAMETER_VALIDATION",
                message=f"Parametro '{code}' non convertibile a decimale.",
                detail=f"Valore attuale: '{value}'",
            )

    # Scopo: Il DEFAULT di un parametro di tipo data (`YYYY-MM-DD`), letto nudo:
    #        nessuna cascata di override. Per i limiti uguali per tutti, dove
    #        un override non ha un caso d'uso (vedi
    #        `ParameterRepository.get_default_value`).
    # ⛔ Fail-loud con `E_CONFIG_MANCANTE` su tutte e tre le forme di guasto
    #    (assente, vuoto, non ISO), come `script.fn_data_operativa`: il rimedio
    #    ce l'ha chi amministra la configurazione, non chi ha fatto la
    #    richiesta. A DB non c'e' un guard sul formato (D-2 del brief
    #    parametro-data-minima-ritardo-dashboard): il presidio e' qui.
    def get_default_date(self, code: str) -> date:
        value = self._repo.get_default_value(code)
        ErrorManager.require(
            value is not None and value.strip() != "",
            code="E_CONFIG_MANCANTE",
            message=f"Parametro '{code}' assente o senza valore.",
        )
        assert value is not None
        value = value.strip()
        try:
            return date.fromisoformat(value)
        except ValueError:
            ErrorManager.raise_error(
                code="E_CONFIG_MANCANTE",
                message=f"Parametro '{code}' non e' una data ISO (YYYY-MM-DD).",
                detail=f"Valore attuale: '{value}'",
            )

    # Scopo: Risolve N parametri in un colpo con override utente.
    #        Restituisce dizionario {code: valore}. I parametri non trovati
    #        vengono esclusi dal risultato (nessun errore).
    def get_defaults(
        self,
        codes: list[str],
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
    ) -> dict[str, str]:
        return self._repo.get_parameters(
            codes, django_user_id, group_ids, emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
        )

    # Scopo: Restituisce la lista completa dei parametri con i valori a ogni
    #        livello di scope e il valore risolto finale per l'utente.
    #        `categoria_cliente_id` opzionale (post brief DB 2026-05-19,
    #        migration 20260519-01): se valorizzato attiva il livello
    #        categoria_cliente fra user e group nella cascata visualizzata
    #        ed espone `categoria_cliente_value` + `categoria_cliente_override_id`
    #        nelle righe risultato.
    def list_parameters_for_user(
        self,
        django_user_id: int,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        # La pagina della lista `config.parametri_impostazioni` (dal 2026-10-31).
        if order_by:
            order_by, order_dir = validate_order_params(
                order_by, order_dir,
                allowed_columns=frozenset(IMPOSTAZIONI_ORDER_COLUMNS),
                error_code="E_VALIDATION_INPUT",
                nullable=True,
                function_name="core.parameter_service.list_parameters_for_user",
            )
        return self._repo.list_for_user(
            django_user_id, group_ids, emittente_fiscale_id,
            categoria_cliente_id=categoria_cliente_id,
            search=search, order_by=order_by, order_dir=order_dir,
            limit=limit, offset=offset,
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
        return _parametro_esistente(
            self._repo.upsert_user_override(parameter_code, django_user_id, value),
            parameter_code,
        )

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
        return _parametro_esistente(
            self._repo.upsert_emittente_override(
                parameter_code, emittente_fiscale_id, value,
            ),
            parameter_code,
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

    # Scopo: Crea o aggiorna un override a livello categoria_cliente per un
    #        parametro. Riservato agli admin (check di permesso a carico della
    #        view). Post brief DB 2026-05-19: chiude lato write il livello
    #        categoria_cliente della cascata (read gia' attiva via
    #        list_parameters_for_user).
    def upsert_categoria_cliente_override(
        self,
        parameter_code: str,
        categoria_cliente_id: int,
        value: str,
    ) -> int:
        ErrorManager.require(
            bool(parameter_code and parameter_code.strip()),
            code="E_PARAMETER_VALIDATION",
            message="Codice parametro obbligatorio.",
        )
        ErrorManager.require(
            categoria_cliente_id is not None and categoria_cliente_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID categoria cliente obbligatorio.",
        )
        return _parametro_esistente(
            self._repo.upsert_categoria_cliente_override(
                parameter_code, categoria_cliente_id, value,
            ),
            parameter_code,
        )

    # Scopo: Rimuove un override a livello categoria_cliente.
    def delete_categoria_cliente_override(
        self,
        override_id: int,
        categoria_cliente_id: int,
    ) -> bool:
        ErrorManager.require(
            override_id is not None and override_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID override obbligatorio.",
        )
        ErrorManager.require(
            categoria_cliente_id is not None and categoria_cliente_id > 0,
            code="E_PARAMETER_VALIDATION",
            message="ID categoria cliente obbligatorio.",
        )
        deleted = self._repo.delete_categoria_cliente_override(
            override_id, categoria_cliente_id,
        )
        ErrorManager.require(
            deleted,
            code="E_PARAMETER_NOT_FOUND",
            message="Override categoria cliente non trovato.",
        )
        return deleted

    # Scopo: Risolve l'emittente_fiscale_id dell'utente dal bridge HR.
    def get_emittente_fiscale_id_for_user(self, auth_user_id: int) -> int | None:
        return self._repo.get_emittente_fiscale_id_for_user(auth_user_id)
