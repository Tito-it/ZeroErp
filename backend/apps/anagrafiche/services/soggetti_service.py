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
from apps.anagrafiche.db.conti_bancari_repository import ContiBancariRepository
from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.core.db.lookup_repository import LookupRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import (
    create_with_dedup,
    optional_str,
    require_str,
    update_with_dedup,
)
from apps.anagrafiche.services.cf_validator_it import genera_cf_it, valida_cf_congruenza_it


class SoggettiService:
    """Service per gestione soggetti completa."""

    def __init__(self) -> None:
        self._repo = SoggettiRepository()
        self._ind = IndirizziRepository()
        self._conti = ContiBancariRepository()
        self._lookup = LookupRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata soggetti.
    def list_soggetti(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_soggetti(**params)

    # Scopo: Dettaglio soggetto con contatti, indirizzi, ruoli e dati societari.
    #        Obiettivo: restituire tutto il necessario per popolare il drawer.
    #        emittente_ids filtra i ruoli CL per scope emittente (None = nessun filtro).
    def get_soggetto(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        soggetto = self._repo.get_soggetto(soggetto_id)
        ErrorManager.require(soggetto is not None, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
        assert soggetto is not None
        soggetto["contatti"] = self._repo.get_soggetto_contatti(soggetto_id)
        soggetto["indirizzi"] = self._repo.get_soggetto_indirizzi(soggetto_id)
        soggetto["ruoli"] = self._repo.get_soggetto_ruoli(soggetto_id, emittente_ids)
        soggetto["dati_societari"] = self._repo.get_dati_societari(soggetto_id)
        soggetto["conti_bancari"] = self._conti.list_conti_soggetto(soggetto_id)
        return soggetto

    # =================================================================
    # Creazione soggetto (orchestratore)
    # =================================================================

    # Scopo: Crea soggetto completo (PF o PG) con contatto e indirizzi.
    #        Determina il path (PF/PG) dal tipo_soggetto_dettaglio_id.
    #        Se auto_clone=True, clona il primo indirizzo per i tipi obbligatori mancanti.
    #        Tutto in una transazione: i trigger DEFERRED verificano al COMMIT.
    #        Risultato: UUID del soggetto creato.
    def create_soggetto(self, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction

        tipo_id = optional_int(payload, "tipo_soggetto_dettaglio_id")
        ErrorManager.require(tipo_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto obbligatorio.")
        assert tipo_id is not None

        natura = self._repo.get_natura_by_tipo_id(tipo_id)
        ErrorManager.require(natura is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto non valido.")
        assert natura is not None

        with transaction.atomic():
            if natura == "PF":
                soggetto_id = self._create_pf(payload)
            else:
                soggetto_id = self._create_pg(payload, tipo_id)

            indirizzi = self._collect_indirizzi(payload)
            if payload.get("auto_clone", True) and indirizzi:
                self._apply_auto_clone(indirizzi, tipo_id)
            self._create_indirizzi_batch(soggetto_id, indirizzi)

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

    # Scopo: Elimina contatto con ownership check.
    def delete_contatto(self, soggetto_id: str, contatto_id: int) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_contatto(contatto_id, soggetto_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato.")
        return {"deleted": True}

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_indirizzi(soggetto_id)

    # Scopo: Crea indirizzo soggetto con validazione tipo.
    def create_indirizzo_soggetto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction
        self._require_soggetto_exists(soggetto_id)
        with transaction.atomic():
            sog_id, _ = self._create_indirizzo(soggetto_id, payload)
        return {"id": sog_id}

    # Scopo: Sostituisce un indirizzo soggetto: elimina il vecchio, crea il nuovo.
    #        Per l'utente e' una "modifica", ma dietro e' delete + create
    #        perche' indirizzi_dettaglio e' condiviso.
    def replace_indirizzo_soggetto(
        self, soggetto_id: str, indirizzo_soggetto_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        from django.db import transaction
        self._require_soggetto_exists(soggetto_id)
        with transaction.atomic():
            deleted = self._repo.delete_indirizzo_soggetto(indirizzo_soggetto_id, soggetto_id)
            ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Indirizzo soggetto non trovato.")
            sog_id, _ = self._create_indirizzo(soggetto_id, payload)
        return {"id": sog_id}

    # Scopo: Elimina un indirizzo soggetto.
    def delete_indirizzo_soggetto(self, soggetto_id: str, indirizzo_soggetto_id: int) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_indirizzo_soggetto(indirizzo_soggetto_id, soggetto_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Indirizzo soggetto non trovato.")
        return {"deleted": True}

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli di un soggetto con filtro scope emittente su CL.
    def get_soggetto_ruoli(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_ruoli(soggetto_id, emittente_ids)

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
    # Utility
    # =================================================================

    # Scopo: Validazione CF (congruenza + duplicato) e P.IVA (duplicato).
    #        Ritorna warnings e errors per feedback immediato nel frontend.
    def valida_cf_piva(self, payload: dict[str, Any]) -> dict[str, Any]:
        from datetime import date as _date

        warnings: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []

        cf = (payload.get("codice_fiscale") or "").strip().upper()
        piva = (payload.get("partita_iva") or "").strip().upper()
        sesso = (payload.get("sesso") or "").strip().upper() or None
        data_nascita_raw = payload.get("data_nascita")
        comune_nascita_id = optional_int(payload, "comune_nascita_id")

        # --- Validazione congruenza CF ---
        if cf and len(cf) == 16:
            data_nascita = None
            if data_nascita_raw:
                if isinstance(data_nascita_raw, str):
                    try:
                        data_nascita = _date.fromisoformat(data_nascita_raw)
                    except ValueError:
                        pass
                else:
                    data_nascita = data_nascita_raw

            codice_catastale = None
            if comune_nascita_id:
                codice_catastale = self._repo.get_codice_catastale(comune_nascita_id)

            cf_errors = valida_cf_congruenza_it(
                cf,
                data_nascita=data_nascita,
                sesso=sesso,
                codice_catastale_comune=codice_catastale,
            )
            for e in cf_errors:
                errors.append({"field": "codice_fiscale", "message": e})

            # Duplicato CF
            existing = self._repo.find_by_codice_fiscale(cf)
            if existing:
                warnings.append({
                    "field": "codice_fiscale",
                    "message": f"CF gia' presente: {existing['ragione_sociale_completa']} ({existing['codice']})",
                })

        # --- Duplicato P.IVA ---
        if piva and len(piva) >= 11:
            existing = self._repo.find_by_partita_iva(piva)
            if existing:
                warnings.append({
                    "field": "partita_iva",
                    "message": f"P.IVA gia' presente: {existing['ragione_sociale_completa']} ({existing['codice']})",
                })

        return {"errors": errors, "warnings": warnings}

    # Scopo: Genera codice fiscale italiano da dati anagrafici.
    def genera_cf(self, payload: dict[str, Any]) -> dict[str, Any]:
        from datetime import date as _date

        cognome = require_str(payload, "cognome", "Cognome obbligatorio.")
        nome = require_str(payload, "nome", "Nome obbligatorio.")
        sesso = require_str(payload, "sesso", "Sesso obbligatorio.")
        comune_id = optional_int(payload, "comune_nascita_id")
        ErrorManager.require(
            comune_id is not None and comune_id > 0,
            code=E_ANAG_VALIDAZIONE,
            message="Comune di nascita obbligatorio.",
        )
        assert comune_id is not None

        data_nascita_raw = payload.get("data_nascita")
        ErrorManager.require(
            data_nascita_raw is not None,
            code=E_ANAG_VALIDAZIONE,
            message="Data di nascita obbligatoria.",
        )
        if isinstance(data_nascita_raw, str):
            data_nascita = _date.fromisoformat(data_nascita_raw)
        else:
            data_nascita = data_nascita_raw

        codice_catastale = self._repo.get_codice_catastale(comune_id)
        ErrorManager.require(
            codice_catastale is not None,
            code=E_ANAG_VALIDAZIONE,
            message="Codice catastale non trovato per il comune selezionato.",
        )
        assert codice_catastale is not None

        cf = genera_cf_it(cognome, nome, data_nascita, sesso, codice_catastale)
        return {"codice_fiscale": cf}

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
                stato_iso2=optional_str(payload, "stato_iso2"),
                comune_nascita_id=optional_int(payload, "comune_nascita_id"),
                tipo_contatto_id=optional_int(contatto, "tipo_contatto_id"),
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
                stato_iso2=optional_str(payload, "stato_iso2"),
                forma_giuridica_id=optional_int(dati_soc, "forma_giuridica_id"),
                id_prov_iscri_rea=optional_int(dati_soc, "id_prov_iscri_rea"),
                iscrizione_rea=optional_str(dati_soc, "iscrizione_rea"),
                capitale_sociale=dati_soc.get("capitale_sociale"),
                socio_unico=optional_str(dati_soc, "socio_unico"),
                liquidazione=optional_str(dati_soc, "liquidazione"),
                destinatario_fe=optional_str(dati_soc, "destinatario_fe"),
                pec_fatturazione=optional_str(dati_soc, "pec_fatturazione"),
                codice_sdi=optional_str(dati_soc, "codice_sdi"),
                tipo_contatto_id=optional_int(contatto, "tipo_contatto_id"),
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

    # Scopo: Raccoglie indirizzi dal payload (supporta sia "indirizzi" array che "indirizzo" singolo).
    def _collect_indirizzi(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw = payload.get("indirizzi")
        indirizzi = list(raw) if isinstance(raw, list) else []
        indirizzo_singolo = payload.get("indirizzo")
        if indirizzo_singolo and isinstance(indirizzo_singolo, dict):
            indirizzi.append(indirizzo_singolo)
        return [ind for ind in indirizzi if isinstance(ind, dict)]

    # Scopo: Auto-clona il primo indirizzo per i tipi obbligatori mancanti.
    #        Policy di dominio: se l'utente compila solo un indirizzo,
    #        gli obbligatori non compilati ricevono una copia.
    def _apply_auto_clone(self, indirizzi: list[dict[str, Any]], tipo_id: int) -> None:
        matrice = self._lookup.list_matrice_indirizzi(tipo_id)
        tipi_presenti = {ind.get("tipo_indirizzo_codice") for ind in indirizzi}
        primo = indirizzi[0]
        for m in matrice:
            if m["obbligatorio"] and m["codice"] not in tipi_presenti:
                indirizzi.append({**primo, "tipo_indirizzo_codice": m["codice"]})

    # Scopo: Crea indirizzi in batch con riuso dettaglio per clonati.
    #        Il primo indirizzo normalizzato risolve il dettaglio, i successivi
    #        (con stesso stradario+civico) riusano lo stesso indirizzo_dettaglio_id.
    def _create_indirizzi_batch(self, soggetto_id: str, indirizzi: list[dict[str, Any]]) -> None:
        resolved_det_id: int | None = None
        for i, ind in enumerate(indirizzi):
            if resolved_det_id and not ind.get("indirizzo_libero") and not ind.get("indirizzo_dettaglio_id"):
                indirizzi[i] = ind = dict(ind, indirizzo_dettaglio_id=resolved_det_id)
            _, det_id = self._create_indirizzo(soggetto_id, ind)
            if resolved_det_id is None and det_id is not None:
                resolved_det_id = det_id

    # Scopo: Dispatch creazione indirizzo soggetto — il payload determina il path.
    def _create_indirizzo(self, soggetto_id: str, payload: dict[str, Any]) -> tuple[int, int | None]:
        tipo_codice = require_str(payload, "tipo_indirizzo_codice",
                                  "Codice tipo indirizzo obbligatorio.")

        if optional_str(payload, "indirizzo_libero"):
            return self._create_indirizzo_libero(soggetto_id, payload, tipo_codice), None

        det_id = self._resolve_indirizzo_dettaglio(payload)
        sog_id = create_with_dedup(
            lambda: self._repo.crea_indirizzo_soggetto(
                soggetto_id,
                tipo_indirizzo_codice=tipo_codice,
                indirizzo_dettaglio_id=det_id,
            ),
            "Indirizzo duplicato per questo soggetto.",
        )
        return sog_id, det_id

    # Scopo: Crea indirizzo libero (estero / libera forma).
    def _create_indirizzo_libero(self, soggetto_id: str, payload: dict[str, Any],
                                 tipo_codice: str) -> int:
        return create_with_dedup(
            lambda: self._repo.crea_indirizzo_soggetto(
                soggetto_id,
                tipo_indirizzo_codice=tipo_codice,
                indirizzo_libero=optional_str(payload, "indirizzo_libero"),
                stato_id=optional_int(payload, "stato_id"),
            ),
            "Indirizzo duplicato per questo soggetto.",
        )

    # Scopo: Risolve indirizzo_dettaglio_id dal payload.
    #        Se il payload ha gia' indirizzo_dettaglio_id, lo usa.
    #        Altrimenti risolve stradario (esistente o nuovo) e crea dettaglio.
    def _resolve_indirizzo_dettaglio(self, payload: dict[str, Any]) -> int:
        det_id = optional_int(payload, "indirizzo_dettaglio_id")
        if det_id is not None:
            return det_id

        stradario_id = optional_int(payload, "stradario_id")
        if stradario_id is None:
            stradario_id = self._create_stradario_da_generale(payload)
        assert stradario_id is not None

        det_id = self._ind.create_indirizzo_dettaglio(
            stradario_id=stradario_id,
            civico=optional_int(payload, "civico"),
            estensione_civico=(payload.get("estensione_civico") or "").strip() or None,
            palazzina=(payload.get("palazzina") or "").strip() or None,
            scala=(payload.get("scala") or "").strip() or None,
            piano=(payload.get("piano") or "").strip() or None,
            interno=(payload.get("interno") or "").strip() or None,
        )
        assert det_id is not None
        return det_id

    # Scopo: Crea stradario locale da stradario_generale (via nuova).
    #        Valida toponomastica, descrizione, comune, CAP.
    def _create_stradario_da_generale(self, payload: dict[str, Any]) -> int:
        toponomastica_id = optional_int(payload, "toponomastica_id")
        descrizione_via = (payload.get("descrizione_via") or "").strip()
        comune_id = optional_int(payload, "comune_id")
        codice_postale_id = optional_int(payload, "codice_postale_id")

        ErrorManager.require(toponomastica_id is not None and toponomastica_id > 0,
                             code=E_ANAG_VALIDAZIONE, message="Tipo strada obbligatorio.")
        assert toponomastica_id is not None
        ErrorManager.require(bool(descrizione_via),
                             code=E_ANAG_VALIDAZIONE, message="Nome via obbligatorio.")
        ErrorManager.require(comune_id is not None and comune_id > 0,
                             code=E_ANAG_VALIDAZIONE, message="Comune obbligatorio.")
        assert comune_id is not None
        ErrorManager.require(codice_postale_id is not None and codice_postale_id > 0,
                             code=E_ANAG_VALIDAZIONE, message="CAP obbligatorio.")
        assert codice_postale_id is not None

        return self._ind.get_or_create_stradario(
            toponomastica_id=toponomastica_id, descrizione_via=descrizione_via,
            comune_id=comune_id, codice_postale_id=codice_postale_id,
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
