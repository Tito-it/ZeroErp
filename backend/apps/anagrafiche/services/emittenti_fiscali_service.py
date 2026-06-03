# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione emittenti fiscali (ruolo EF).
#        Orchestrazione creazione (ruolo EF + insert) in transazione atomica.
#        CRUD, lista paginata, update. Riservato ad amministratori.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.anagrafiche.db.emittenti_fiscali_repository import (
    EmittentiFiscaliBillingAccountRepository,
    EmittentiFiscaliRepository,
    EmittentiFiscaliUtilitiesRepository,
)
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import (
    create_with_constraint_mapping,
    create_with_dedup,
    extract_optional_fields,
    optional_str,
    require_found,
    require_str,
)
from apps.core.api.payload_validators import optional_bool, optional_int, optional_uuid
from apps.core.services.error_manager import ErrorManager
from apps.core.services.non_editable_fields_helper import (
    compute_non_editable_fields,
)


# Gap rispetto al registro DB `dbops.vw_non_editable_fields` (Fase 4 — A9).
# `codice` e `soggetto_id` sono semanticamente immutabili sull'emittente
# fiscale: cambiarli equivale a creare un altro emittente.
_EMITTENTE_NON_EDITABLE_GAPS: tuple[str, ...] = ("codice", "soggetto_id")


class EmittentiFiscaliService:
    """Service per gestione emittenti fiscali (Amm. Software)."""

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata emittenti fiscali.
    def list_emittenti_fiscali(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_emittenti_fiscali(**params)

    # Scopo: Dettaglio completo di un emittente fiscale.
    #        Arricchito con `non_editable_fields` (Fase 4 — A9):
    #        il FE costruisce il drawer di edit usando questi metadata,
    #        coerente con altre matrici amm-software.
    def get_emittente(self, emittente_id: int) -> dict[str, Any]:
        emittente = require_found(
            self._repo.get_emittente(emittente_id), "Emittente fiscale non trovato.")
        emittente["non_editable_fields"] = self.get_non_editable_fields()
        return emittente

    # Scopo: Lista `non_editable_fields` per anagrafica emittente (Fase 4 — A9).
    def get_non_editable_fields(self) -> list[str]:
        return compute_non_editable_fields(
            "anagrafiche", "emittenti_fiscali",
            gaps=_EMITTENTE_NON_EDITABLE_GAPS,
        )

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea un emittente fiscale completo in una transazione atomica.
    #        Obiettivo: associa il soggetto al ruolo EF e crea il record emittente.
    #        Perimetro: validazione soggetto_id (con P.IVA obbligatoria), codice e
    #        descrizione, get_or_create ruolo, insert emittente con campi opzionali.
    #        Risultato: dict con id dell'emittente e soggetto_ruolo_id.
    #        Nota: il primo emittente creato attiva il trigger default_bootstrap che
    #        popola automaticamente il default mapping in emittenti_fiscali_billing_account.
    def crea_emittente(self, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_id = optional_uuid(payload, "soggetto_id")
        ErrorManager.require(
            soggetto_id is not None,
            code=E_ANAG_VALIDAZIONE,
            message="soggetto_id obbligatorio.",
        )
        assert soggetto_id is not None
        soggetto_id = str(soggetto_id)

        # Validazione P.IVA del soggetto: requisito legale per emissione fatture
        # tramite SDI. Un soggetto privato (solo CF) non puo' essere emittente fiscale.
        partita_iva = self._repo.get_soggetto_partita_iva(soggetto_id)
        ErrorManager.require(
            bool(partita_iva),
            code=E_ANAG_VALIDAZIONE,
            message="L'emittente fiscale richiede un soggetto con Partita IVA.",
        )

        # Campi obbligatori dell'emittente
        codice = require_str(payload, "codice", "Codice emittente obbligatorio.")
        descrizione = require_str(payload, "descrizione", "Descrizione emittente obbligatoria.")

        # Campi opzionali (incluso attivo se passato dal payload, default DB true)
        emittente_data = self._extract_emittente_data(payload)

        # Atomic: ruolo EF e insert emittente devono essere consistenti — se fallisce
        # l'insert dopo aver creato il ruolo, il rollback evita ruoli orfani.
        with transaction.atomic():
            soggetto_ruolo_id = self._repo.get_or_create_ruolo_emittente(soggetto_id)
            result = create_with_constraint_mapping(
                lambda: {"id": self._repo.create_emittente(
                    soggetto_ruolo_id=soggetto_ruolo_id,
                    codice=codice,
                    descrizione=descrizione,
                    **emittente_data,
                )},
                {
                    "uq_emittenti_fiscali_ruolo": "Esiste gia' un emittente fiscale per questo soggetto.",
                    "uq:codice": "Esiste gia' un emittente fiscale con questo codice.",
                },
            )

        return {
            "id": result["id"],
            "soggetto_ruolo_id": soggetto_ruolo_id,
        }

    # Scopo: Estrae i campi opzionali dell'emittente dal payload.
    def _extract_emittente_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        # bool a None = "non fornito" → lasciar usare il default DB.
        return extract_optional_fields(
            payload,
            ints=("valuta_id",),
            bools=("attivo", "bollo_auto"),
            strings=("regime_fiscale_rf", "rounding_policy"),
            numeric=("bollo_soglia",),
        )

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna campi editabili dell'emittente fiscale.
    #        Il campo codice e' bloccato dal trigger DB e viene ignorato se presente nel payload.
    def update_emittente(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        # Verifica che l'emittente esista
        self.get_emittente(emittente_id)
        # Copia difensiva: il repo normalizza stringhe vuote -> None e non deve mutare
        # request.data della view (che potrebbe essere riusato dal middleware di logging).
        updated = self._repo.update_emittente(emittente_id, dict(payload))
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Emittente fiscale non trovato o nessun campo modificato.",
        )
        return {"updated": True}

    # =================================================================
    # Helper interno: risolve emittente_id -> soggetto_ruolo_id (con guard)
    # =================================================================

    # Scopo: Risolve il soggetto_ruolo_id partendo dall'emittente_id.
    #        Usato dai metodi sub-resource (BA mapping, utilities) per validare
    #        l'esistenza dell'emittente padre prima di operare sui figli.
    def _resolve_soggetto_ruolo_id(self, emittente_id: int) -> int:
        soggetto_ruolo_id = self._repo.get_soggetto_ruolo_id(emittente_id)
        ErrorManager.require(
            soggetto_ruolo_id is not None,
            code=E_ANAG_NOT_FOUND,
            message="Emittente fiscale non trovato.",
        )
        assert soggetto_ruolo_id is not None
        return soggetto_ruolo_id


# Scopo: Helper condiviso per i sub-resource service. Risolve il soggetto_ruolo_id
#        del padre e verifica che il record figlio appartenga effettivamente al padre.
#        Solleva ServiceError E_ANAG_NOT_FOUND in entrambi i casi mancanti.
#        Estratto per evitare duplicazione in elimina_mapping/aggiorna_record/elimina_record.
def _verify_record_ownership(parent_service, repo, emittente_id, record_id, not_found_message):
    soggetto_ruolo_id = parent_service._resolve_soggetto_ruolo_id(emittente_id)
    ErrorManager.require(
        repo.belongs_to_emittente(record_id, soggetto_ruolo_id),
        code=E_ANAG_NOT_FOUND,
        message=not_found_message,
    )
    return soggetto_ruolo_id


# =================================================================
# Service Mapping BA -> emittente fiscale
# =================================================================


class EmittentiFiscaliBillingAccountService:
    """Service per mapping BA -> emittente fiscale.

    Endpoint sub-resource montati sotto un emittente padre. Usa
    EmittentiFiscaliService._resolve_soggetto_ruolo_id per validare
    l'esistenza dell'emittente padre prima di ogni operazione.
    """

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliBillingAccountRepository()
        self._parent = EmittentiFiscaliService()

    # Scopo: Lista paginata mapping BA per un emittente con search.
    #        Ogni riga arricchita con `can_remove=True` (Fase 4 — A7).
    #        Il BA mapping non ha PATCH (solo CREATE/DELETE), quindi
    #        `can_update`/`can_configure` non sono applicabili: il pattern
    #        slot/override si limita a "esiste/non esiste". Espongo
    #        `can_remove` come capability esplicita per allineare la UI col
    #        pattern utility (delega gating al BE invece di derivarlo dalla
    #        presenza del record).
    def list_mapping(
        self,
        emittente_id: int,
        *,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "billing_account_codice",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        rows, total = self._repo.list_by_emittente(
            soggetto_ruolo_id,
            search=search,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )
        for row in rows:
            row["can_remove"] = True
        return rows, total

    # Scopo: Crea un nuovo mapping BA->emittente.
    #        Se billing_account_id e' None nel payload, viene creato il default globale
    #        (is_default=true). Il CHECK constraint DB garantisce coerenza.
    #        I trigger DB (default_guard) impediscono piu' di un default.
    def crea_mapping(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        billing_account_id = optional_int(payload, "billing_account_id")
        result = create_with_dedup(
            lambda: {"id": self._repo.create_mapping(soggetto_ruolo_id, billing_account_id)},
            duplicate_message=(
                "Mapping gia' presente: questo billing account e' gia' associato "
                "a un emittente, oppure il default globale esiste gia'."
            ),
        )
        return {
            "id": result["id"],
            "emittente_id": emittente_id,
            "billing_account_id": billing_account_id,
            "is_default": billing_account_id is None,
        }

    # Scopo: Elimina un mapping. Verifica che appartenga all'emittente padre.
    def elimina_mapping(self, emittente_id: int, mapping_id: int) -> dict[str, Any]:
        _verify_record_ownership(
            self._parent, self._repo, emittente_id, mapping_id,
            "Mapping non trovato per l'emittente indicato.",
        )
        deleted = self._repo.delete_mapping(mapping_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Mapping non trovato.")
        return {"deleted": True}

    # Scopo: Riepilogo mapping BA dell'emittente (has_default + count_specifici).
    #        Esposto al FE come bypass della dipendenza dalla pagina corrente:
    #        senza summary, il check "esiste gia' un default" puo' fallire se
    #        il record default non e' nella pagina visualizzata.
    def summary_mapping(self, emittente_id: int) -> dict[str, Any]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        return self._repo.summary_by_emittente(soggetto_ruolo_id)


# =================================================================
# Service Utilities per emittente fiscale
# =================================================================


class EmittentiFiscaliUtilitiesService:
    """Service per la matrice emittente_fiscale x utility (parametri fatturazione).

    Sub-resource montato sotto un emittente padre. Espone CRUD sui record utility
    e una lista di utility ammesse per il ruolo EF (lookup combo).
    """

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliUtilitiesRepository()
        self._parent = EmittentiFiscaliService()

    # Scopo: Lista record utility per un emittente.
    #        Ogni riga arricchita con capability data-driven (Fase 4 — A7):
    #          - `can_configure`: slot vuoto + emittente attivo + utility attiva
    #            (l'admin puo' creare la configurazione)
    #          - `can_update`: record configurato (l'admin puo' modificare i parametri)
    #          - `can_remove`: record configurato (l'admin puo' rimuovere)
    #        Il FE usa queste capability per gating UI invece di derivare da
    #        `record_id`. L'autorita' resta il trigger DB
    #        (`child_requires_active_parent`, `guard_utility_tipo_ruolo`).
    def list_records(self, emittente_id: int) -> list[dict[str, Any]]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        emittente = self._parent._repo.get_emittente(emittente_id)
        emittente_attivo = bool(emittente and emittente.get("attivo"))

        rows = self._repo.list_by_emittente(soggetto_ruolo_id)
        for row in rows:
            is_configured = row.get("record_id") is not None
            utility_attiva = bool(row.get("utility_attiva", False))
            row["can_configure"] = (
                (not is_configured) and emittente_attivo and utility_attiva
            )
            row["can_update"] = is_configured
            row["can_remove"] = is_configured
        return rows

    # Scopo: Crea un record utility per l'emittente.
    #        Campi obbligatori: utility_id, arrotondamento_importi_dec, metodo_arrotondamento_importi.
    def crea_record(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        utility_id = optional_int(payload, "utility_id")
        ErrorManager.require(
            utility_id is not None,
            code=E_ANAG_VALIDAZIONE,
            message="utility_id obbligatorio.",
        )
        assert utility_id is not None

        arrot_dec = optional_int(payload, "arrotondamento_importi_dec")
        ErrorManager.require(
            arrot_dec is not None,
            code=E_ANAG_VALIDAZIONE,
            message="arrotondamento_importi_dec obbligatorio.",
        )
        assert arrot_dec is not None

        metodo = optional_str(payload, "metodo_arrotondamento_importi")
        ErrorManager.require(
            bool(metodo),
            code=E_ANAG_VALIDAZIONE,
            message="metodo_arrotondamento_importi obbligatorio.",
        )
        assert metodo is not None

        attivo = optional_bool(payload, "attivo") if payload.get("attivo") is not None else None

        result = create_with_dedup(
            lambda: {"id": self._repo.create_record(
                emittente_soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
                arrotondamento_importi_dec=arrot_dec,
                metodo_arrotondamento_importi=metodo,
                minimo_soglia_min=payload.get("minimo_soglia_min"),
                minimo_soglia_max=payload.get("minimo_soglia_max"),
                attivo=attivo,
            )},
            duplicate_message="Esiste gia' un record utility per questa coppia (emittente, utility).",
        )
        return {"id": result["id"]}

    # Scopo: Aggiorna un record utility (delta update).
    def aggiorna_record(self, emittente_id: int, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _verify_record_ownership(
            self._parent, self._repo, emittente_id, record_id,
            "Record utility non trovato per l'emittente indicato.",
        )
        updated = self._repo.update_record(record_id, dict(payload))
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Record utility non trovato o nessun campo modificato.",
        )
        return {"updated": True}

    # Scopo: Elimina un record utility per id.
    def elimina_record(self, emittente_id: int, record_id: int) -> dict[str, Any]:
        _verify_record_ownership(
            self._parent, self._repo, emittente_id, record_id,
            "Record utility non trovato per l'emittente indicato.",
        )
        deleted = self._repo.delete_record(record_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Record utility non trovato.")
        return {"deleted": True}
