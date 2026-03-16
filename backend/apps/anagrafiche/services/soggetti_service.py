# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione soggetti (PF/PG/ENTE).
#        Orchestrazione creazione soggetto + contatto + indirizzo + dati societari
#        in una transazione. I trigger DEFERRED verificano al COMMIT.
#        Ref: docs/it/dev/api.md (sezione Layering)
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import (
    create_with_dedup,
    optional_str,
    require_str,
    update_with_dedup,
)
from apps.anagrafiche.services.cf_validator_it import valida_cf_congruenza_it


class SoggettiService:
    """Service per gestione soggetti completa."""

    def __init__(self) -> None:
        self._repo = SoggettiRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata soggetti.
    def list_soggetti(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_soggetti(**params)

    # Scopo: Dettaglio soggetto con contatti, indirizzi, ruoli e dati societari.
    #        Obiettivo: restituire tutto il necessario per popolare il drawer.
    def get_soggetto(self, soggetto_id: str) -> dict[str, Any]:
        soggetto = self._repo.get_soggetto(soggetto_id)
        ErrorManager.require(soggetto is not None, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
        assert soggetto is not None
        soggetto["contatti"] = self._repo.get_soggetto_contatti(soggetto_id)
        soggetto["indirizzi"] = self._repo.get_soggetto_indirizzi(soggetto_id)
        soggetto["ruoli"] = self._repo.get_soggetto_ruoli(soggetto_id)
        soggetto["dati_societari"] = self._repo.get_dati_societari(soggetto_id)
        return soggetto

    # =================================================================
    # Creazione soggetto (orchestratore)
    # =================================================================

    # Scopo: Crea soggetto completo (PF o PG) con contatto e indirizzo.
    #        Determina il path (PF/PG) dal tipo_soggetto_dettaglio_id.
    #        Tutto in una transazione: i trigger DEFERRED verificano al COMMIT.
    #        Perimetro: soggetto + contatto default + indirizzo (se fornito).
    #        Risultato: UUID del soggetto creato.
    def create_soggetto(self, payload: dict[str, Any]) -> dict[str, Any]:
        tipo_id = optional_int(payload, "tipo_soggetto_dettaglio_id")
        ErrorManager.require(tipo_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto obbligatorio.")
        assert tipo_id is not None

        # Determina natura dal tipo (via repository)
        natura = self._repo.get_natura_by_tipo_id(tipo_id)
        ErrorManager.require(natura is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto non valido.")
        assert natura is not None

        if natura == "PF":
            soggetto_id = self._create_pf(payload)
        else:
            soggetto_id = self._create_pg(payload, tipo_id)

        # Indirizzi (opzionali nel payload, obbligatori se matrice lo richiede
        # — il trigger DEFERRED verifichera' al COMMIT).
        # Supporta sia array "indirizzi" che singolo "indirizzo" per comodita'.
        indirizzi = payload.get("indirizzi") or []
        indirizzo_singolo = payload.get("indirizzo")
        if indirizzo_singolo and isinstance(indirizzo_singolo, dict):
            indirizzi.append(indirizzo_singolo)
        for ind in indirizzi:
            if isinstance(ind, dict):
                self._create_indirizzo(soggetto_id, ind)

        return {"id": soggetto_id}

    # =================================================================
    # Aggiornamento soggetto
    # =================================================================

    # Scopo: Aggiorna campi soggetto.
    def update_soggetto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return update_with_dedup(
            lambda: self._repo.update_soggetto(soggetto_id, payload),
            "Codice fiscale o partita IVA duplicata.",
            "Soggetto non trovato.",
        )

    # =================================================================
    # Contatti
    # =================================================================

    # Scopo: Lista contatti di un soggetto.
    def get_soggetto_contatti(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_contatti(soggetto_id)

    # Scopo: Crea contatto per un soggetto con validazione.
    def create_contatto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        nominativo = require_str(payload, "nominativo", "Nominativo contatto obbligatorio.")
        return self._repo.crea_contatto(
            soggetto_id,
            nominativo=nominativo,
            email=optional_str(payload, "email"),
            telefono=optional_str(payload, "telefono"),
            cellulare=optional_str(payload, "cellulare"),
            pec=optional_str(payload, "pec"),
            tipo_contatto_id=optional_int(payload, "tipo_contatto_id"),
            unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
            note=optional_str(payload, "note"),
        )

    # Scopo: Aggiorna contatto esistente con verifica ownership.
    def update_contatto(self, contatto_id: int, payload: dict[str, Any],
                        soggetto_id: str | None = None) -> dict[str, Any]:
        updated = self._repo.update_contatto(contatto_id, payload, soggetto_id=soggetto_id)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato.")
        return {"updated": True}

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_indirizzi(soggetto_id)

    # Scopo: Crea indirizzo soggetto con validazione tipo.
    def create_indirizzo_soggetto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        indirizzo_id = self._create_indirizzo(soggetto_id, payload)
        return {"id": indirizzo_id}

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli di un soggetto.
    def get_soggetto_ruoli(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_ruoli(soggetto_id)

    # Scopo: Assegna ruolo a soggetto (idempotente).
    def assign_ruolo(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        codice_ruolo = require_str(payload, "codice_ruolo", "Codice ruolo obbligatorio.")
        ruolo_id = create_with_dedup(
            lambda: self._repo.assign_ruolo(soggetto_id, codice_ruolo),
            "Ruolo gia' assegnato.",
        )
        return {"id": ruolo_id}

    # =================================================================
    # Metodi interni
    # =================================================================

    # Scopo: Crea soggetto PF via building block DB.
    #        Include validazione congruenza CF con dati anagrafici (data, sesso, comune).
    def _create_pf(self, payload: dict[str, Any]) -> str:
        cognome = require_str(payload, "cognome", "Cognome obbligatorio.")
        nome = require_str(payload, "nome", "Nome obbligatorio.")
        codice_fiscale = require_str(payload, "codice_fiscale", "Codice fiscale obbligatorio.")

        # Validazione congruenza CF con dati anagrafici
        self._valida_cf_congruenza(payload, codice_fiscale)

        contatto = payload.get("contatto") or {}
        require_str(contatto, "nominativo", "Nominativo contatto obbligatorio.")
        email_addr = optional_str(contatto, "email") or ""

        soggetto_id = create_with_dedup(
            lambda: self._repo.crea_soggetto_pf(
                cognome=cognome, nome=nome, codice_fiscale=codice_fiscale,
                email=email_addr,
                data_nascita=optional_str(payload, "data_nascita"),
                sesso=payload.get("sesso", "M") or "M",
                stato_iso2=payload.get("stato_iso2", "IT") or "IT",
            ),
            "Soggetto con questo codice fiscale gia' esistente.",
        )

        self._update_contatto_default(soggetto_id, contatto,
                                      contatto.get("nominativo", f"{cognome} {nome}"))
        return soggetto_id

    # Scopo: Crea soggetto PG/ENTE via building block DB.
    #        Obiettivo: INSERT soggetto + contatto default + dati societari
    #        (se policy lo richiede). I trigger DEFERRED verificano al COMMIT.
    def _create_pg(self, payload: dict[str, Any], tipo_id: int) -> str:
        ragione_sociale = require_str(payload, "ragione_sociale", "Ragione sociale obbligatoria.")

        contatto = payload.get("contatto") or {}
        require_str(contatto, "nominativo", "Nominativo contatto obbligatorio.")
        email_addr = optional_str(contatto, "email") or ""

        dati_soc = payload.get("dati_societari") or {}

        soggetto_id = create_with_dedup(
            lambda: self._repo.crea_soggetto_pg(
                ragione_sociale=ragione_sociale,
                tipo_soggetto_dettaglio_id=tipo_id,
                email=email_addr,
                codice_fiscale=optional_str(payload, "codice_fiscale"),
                partita_iva=optional_str(payload, "partita_iva"),
                stato_iso2=payload.get("stato_iso2", "IT") or "IT",
                forma_giuridica_id=optional_int(dati_soc, "forma_giuridica_id"),
                id_prov_iscri_rea=optional_int(dati_soc, "id_prov_iscri_rea"),
                iscrizione_rea=optional_str(dati_soc, "iscrizione_rea"),
                capitale_sociale=dati_soc.get("capitale_sociale"),
                socio_unico=dati_soc.get("socio_unico", "SU") or "SU",
                liquidazione=dati_soc.get("liquidazione", "LN") or "LN",
                destinatario_fe=optional_str(dati_soc, "destinatario_fe"),
                pec_fatturazione=optional_str(dati_soc, "pec_fatturazione"),
                codice_sdi=optional_str(dati_soc, "codice_sdi"),
            ),
            "Soggetto PG con CF/PIVA duplicata.",
        )

        self._update_contatto_default(soggetto_id, contatto,
                                      contatto.get("nominativo", ragione_sociale))
        return soggetto_id

    # Scopo: Aggiorna il contatto default creato dalla funzione DB con i campi aggiuntivi.
    def _update_contatto_default(self, soggetto_id: str, contatto: dict, default_nominativo: str) -> None:
        if not contatto:
            return
        contatti = self._repo.get_soggetto_contatti(soggetto_id)
        if contatti:
            self._repo.update_contatto(contatti[0]["id"], {
                "nominativo": contatto.get("nominativo", default_nominativo),
                "telefono": optional_str(contatto, "telefono"),
                "cellulare": optional_str(contatto, "cellulare"),
                "pec": optional_str(contatto, "pec"),
                "tipo_contatto_id": optional_int(contatto, "tipo_contatto_id"),
                "unita_organizzativa_id": optional_int(contatto, "unita_organizzativa_id"),
                "note": optional_str(contatto, "note"),
            })

    # Scopo: Crea indirizzo soggetto dal payload (normalizzato o libero).
    def _create_indirizzo(self, soggetto_id: str, payload: dict[str, Any]) -> int:
        tipo_codice = require_str(payload, "tipo_indirizzo_codice",
                                  "Codice tipo indirizzo obbligatorio.")
        return create_with_dedup(
            lambda: self._repo.crea_indirizzo_soggetto(
                soggetto_id,
                tipo_indirizzo_codice=tipo_codice,
                indirizzo_dettaglio_id=optional_int(payload, "indirizzo_dettaglio_id"),
                indirizzo_libero=optional_str(payload, "indirizzo_libero"),
                stato_id=optional_int(payload, "stato_id"),
                comune_id=optional_int(payload, "comune_id"),
                codice_postale_id=optional_int(payload, "codice_postale_id"),
            ),
            "Indirizzo duplicato per questo soggetto.",
        )

    # Scopo: Validazione congruenza CF italiano con dati anagrafici (data, sesso, comune).
    #        Non blocca se i dati opzionali non sono forniti — valida solo quelli presenti.
    def _valida_cf_congruenza(self, payload: dict[str, Any], codice_fiscale: str) -> None:
        from datetime import date as date_type

        data_nascita = None
        dn_str = optional_str(payload, "data_nascita")
        if dn_str:
            try:
                data_nascita = date_type.fromisoformat(dn_str)
            except ValueError:
                pass

        sesso = payload.get("sesso")

        codice_catastale = None
        comune_id = optional_int(payload, "comune_nascita_id") or optional_int(payload, "comune_id")
        if comune_id:
            codice_catastale = self._repo.get_codice_catastale(comune_id)

        errors = valida_cf_congruenza_it(
            codice_fiscale,
            data_nascita=data_nascita,
            sesso=sesso,
            codice_catastale_comune=codice_catastale,
        )
        if errors:
            ErrorManager.require(False, code=E_ANAG_VALIDAZIONE,
                                 message=" ".join(errors))

    # Scopo: Guard leggero — verifica che il soggetto esista (SELECT 1).
    def _require_soggetto_exists(self, soggetto_id: str) -> None:
        exists = self._repo.exists_soggetto(soggetto_id)
        ErrorManager.require(exists, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
