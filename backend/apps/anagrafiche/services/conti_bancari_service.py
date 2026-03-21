# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione conti bancari.
#        Orchestrazione registro IBAN (get_or_create), legami
#        soggetto ↔ conto, legami ruolo ↔ conto, lookup filiali.
#        Ref: docs/it/guide/gestione-conti-bancari.md
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import Any

_IBAN_RE = re.compile(r'^[A-Z0-9]{15,34}$')

from apps.core.api.payload_validators import optional_bool, optional_int
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db.conti_bancari_repository import ContiBancariRepository
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_CONTO_NOT_FOUND,
    E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.anagrafiche.services._validators import (
    create_with_dedup,
    optional_str,
    require_str,
    update_with_dedup,
)


class ContiBancariService:
    """Service per gestione conti bancari: registro, legami soggetto/ruolo, filiali."""

    def __init__(self) -> None:
        self._repo = ContiBancariRepository()
        self._soggetti = SoggettiRepository()

    # =================================================================
    # Lookup registro IBAN e filiali
    # =================================================================

    # Scopo: Ricerca IBAN nel registro per autocomplete.
    def search_conti_bancari(self, search: str, limit: int = 10) -> list[dict[str, Any]]:
        search = (search or "").strip()
        if len(search) < 2:
            return []
        return self._repo.search_conti_bancari(search, limit)

    # Scopo: Ricerca filiali bancarie per autocomplete.
    def search_bank_branches(self, search: str, limit: int = 10) -> list[dict[str, Any]]:
        search = (search or "").strip()
        if len(search) < 2:
            return []
        return self._repo.search_bank_branches(search, limit)

    # =================================================================
    # Conti bancari soggetto
    # =================================================================

    # Scopo: Lista conti bancari associati a un soggetto.
    def list_conti_soggetto(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.list_conti_soggetto(soggetto_id)

    # Scopo: Crea legame soggetto ↔ conto bancario.
    #        Obiettivo: riceve IBAN + dati dal frontend, risolve (get_or_create)
    #        il registro, poi crea il legame. Transazione atomica.
    #        Risultato: dict con id del legame creato.
    def create_conto_soggetto(
        self, soggetto_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        from django.db import transaction

        self._require_soggetto_exists(soggetto_id)
        conto_bancario_id = self._resolve_conto_bancario(payload)
        legame_payload = self._extract_legame_payload(payload)

        with transaction.atomic():
            result = create_with_dedup(
                lambda: self._repo.create_conto_soggetto(
                    soggetto_id,
                    conto_bancario_id=conto_bancario_id,
                    **legame_payload,
                ),
                "Conto bancario gia' associato a questo soggetto per lo stesso uso.",
            )
        return result

    # Scopo: Aggiorna legame soggetto ↔ conto con ownership check.
    def update_conto_soggetto(
        self, soggetto_id: str, conto_soggetto_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        return update_with_dedup(
            lambda: self._repo.update_conto_soggetto(
                conto_soggetto_id, soggetto_id, payload,
            ),
            "Conto bancario gia' associato a questo soggetto per lo stesso uso.",
            "Associazione conto bancario non trovata.",
        )

    # Scopo: Elimina legame soggetto ↔ conto con ownership check.
    def delete_conto_soggetto(
        self, soggetto_id: str, conto_soggetto_id: int,
    ) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_conto_soggetto(conto_soggetto_id, soggetto_id)
        ErrorManager.require(
            deleted, code=E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
            message="Associazione conto bancario non trovata.",
        )
        return {"deleted": True}

    # =================================================================
    # Conti bancari ruolo
    # =================================================================

    # Scopo: Lista conti bancari associati a un ruolo, inclusi i conti
    #        ereditati dal soggetto (con flag fonte per la UI).
    def list_conti_ruolo(self, soggetto_ruolo_id: int) -> dict[str, Any]:
        conti_ruolo = self._repo.list_conti_ruolo(soggetto_ruolo_id)
        conti_ereditati = self._repo.list_conti_ereditati_ruolo(soggetto_ruolo_id)
        return {
            "conti_ruolo": conti_ruolo,
            "conti_ereditati": conti_ereditati,
        }

    # Scopo: Crea legame ruolo ↔ conto bancario.
    #        Stessa logica di create_conto_soggetto ma per ruolo.
    def create_conto_ruolo(
        self, soggetto_ruolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        from django.db import transaction

        conto_bancario_id = self._resolve_conto_bancario(payload)
        legame_payload = self._extract_legame_payload(payload)

        with transaction.atomic():
            result = create_with_dedup(
                lambda: self._repo.create_conto_ruolo(
                    soggetto_ruolo_id,
                    conto_bancario_id=conto_bancario_id,
                    **legame_payload,
                ),
                "Conto bancario gia' associato a questo ruolo per lo stesso uso.",
            )
        return result

    # Scopo: Aggiorna legame ruolo ↔ conto con ownership check.
    def update_conto_ruolo(
        self, soggetto_ruolo_id: int, conto_ruolo_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return update_with_dedup(
            lambda: self._repo.update_conto_ruolo(
                conto_ruolo_id, soggetto_ruolo_id, payload,
            ),
            "Conto bancario gia' associato a questo ruolo per lo stesso uso.",
            "Associazione conto bancario non trovata.",
        )

    # Scopo: Elimina legame ruolo ↔ conto con ownership check.
    def delete_conto_ruolo(
        self, soggetto_ruolo_id: int, conto_ruolo_id: int,
    ) -> dict[str, Any]:
        deleted = self._repo.delete_conto_ruolo(conto_ruolo_id, soggetto_ruolo_id)
        ErrorManager.require(
            deleted, code=E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
            message="Associazione conto bancario non trovata.",
        )
        return {"deleted": True}

    # =================================================================
    # Metodi interni
    # =================================================================

    # Scopo: Risolve conto_bancario_id dal payload.
    #        Se il payload ha gia' conto_bancario_id, lo usa direttamente.
    #        Altrimenti usa IBAN per get_or_create nel registro.
    #        Risultato: conto_bancario_id valido.
    def _resolve_conto_bancario(self, payload: dict[str, Any]) -> int:
        conto_id = optional_int(payload, "conto_bancario_id")
        if conto_id is not None:
            # Verifica che il conto esista
            conto = self._repo.get_conto_bancario(conto_id)
            ErrorManager.require(
                conto is not None, code=E_ANAG_CONTO_NOT_FOUND,
                message="Conto bancario non trovato nel registro.",
            )
            return conto_id

        # Risolve da IBAN — valida formato prima dell'INSERT
        iban = require_str(payload, "iban", "IBAN obbligatorio.")
        iban_norm = iban.upper().replace(" ", "")
        ErrorManager.require(
            bool(_IBAN_RE.match(iban_norm)),
            code=E_ANAG_VALIDAZIONE,
            message="IBAN non valido: deve contenere da 15 a 34 caratteri alfanumerici.",
        )
        bank_branch_id = optional_int(payload, "bank_branch_id")
        ErrorManager.require(
            bank_branch_id is not None and bank_branch_id > 0,
            code=E_ANAG_VALIDAZIONE,
            message="Filiale bancaria obbligatoria.",
        )
        assert bank_branch_id is not None

        conto_id, _created = self._repo.get_or_create_conto_bancario(
            iban=iban,
            bic_swift=optional_str(payload, "bic_swift"),
            bank_branch_id=bank_branch_id,
            intestatario_predefinito=optional_str(payload, "intestatario_predefinito"),
        )
        return conto_id

    # Scopo: Estrae i campi del legame (soggetto o ruolo) dal payload.
    #        Separa i dati registro (iban, bic, banca) dai dati legame (uso, predefinito, ecc.).
    #        Per i booleani controlla la presenza della chiave nel payload:
    #        optional_bool ritorna sempre bool (mai None), quindi non si puo'
    #        distinguere "non inviato" da "inviato come False" dal valore di ritorno.
    def _extract_legame_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        _USI_VALIDI = {"INCASSO", "PAGAMENTO", "RIMBORSO", "GENERICO"}
        result: dict[str, Any] = {}

        uso = optional_str(payload, "uso")
        if uso:
            uso_upper = uso.upper().strip()
            ErrorManager.require(
                uso_upper in _USI_VALIDI,
                code=E_ANAG_VALIDAZIONE,
                message=f"Tipo d'uso non valido: {uso}. Valori ammessi: INCASSO, PAGAMENTO, RIMBORSO, GENERICO.",
            )
            result["uso"] = uso_upper

        # Booleani: includi solo se la chiave e' presente nel payload
        for bool_key in ("predefinito", "verificato", "bloccato"):
            if bool_key in payload:
                result[bool_key] = optional_bool(payload, bool_key)

        # Stringhe/date opzionali
        for str_key in ("valido_dal", "valido_al", "intestazione_dichiarata"):
            val = optional_str(payload, str_key)
            if val is not None:
                result[str_key] = val

        return result

    # Scopo: Guard leggero — verifica che il soggetto esista.
    def _require_soggetto_exists(self, soggetto_id: str) -> None:
        exists = self._soggetti.exists_soggetto(soggetto_id)
        ErrorManager.require(exists, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
