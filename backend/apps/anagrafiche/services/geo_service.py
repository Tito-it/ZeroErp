# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione geografica (toponomastica, comuni,
#        province, regioni, stati, indirizzi).
#        Validazione, orchestrazione, IntegrityError — le view restano sottili.
#        Ref: docs/it/dev/api.md (sezione 6 Layering)
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.anagrafiche.db.geo_repository import GeoRepository
from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import (
    create_with_dedup as _create_with_dedup,
    require_str as _require_str,
    update_with_dedup as _update_with_dedup,
)


# Scopo: Il pre-check della VIA di un indirizzo normalizzato: uno stradario
#        esistente (id positivo), oppure i quattro campi di una via nuova (tipo
#        strada, nome, comune, CAP) che `anagrafiche.fn_create_indirizzo` usa
#        per l'upsert dello stradario. Messaggi per l'operatore, prima di
#        scrivere: il DB li rifiuterebbe con un errore meno parlante.
#        Lo chiamano la creazione del dettaglio (qui) e gli indirizzi di ruolo
#        (`SoggettiService.create_indirizzi_ruolo`), che alla madre passano la
#        via da risolvere.
def richiedi_via(payload: dict) -> None:
    stradario_id = optional_int(payload, "stradario_id")
    if stradario_id is not None:
        ErrorManager.require(stradario_id > 0, code=E_ANAG_VALIDAZIONE, message="stradario_id non valido.")
        return
    toponomastica_id = optional_int(payload, "toponomastica_id")
    comune_id = optional_int(payload, "comune_id")
    codice_postale_id = optional_int(payload, "codice_postale_id")
    ErrorManager.require(toponomastica_id is not None and toponomastica_id > 0,
                         code=E_ANAG_VALIDAZIONE, message="Tipo strada obbligatorio per via nuova.")
    ErrorManager.require(bool((payload.get("descrizione_via") or "").strip()),
                         code=E_ANAG_VALIDAZIONE, message="Nome via obbligatorio.")
    ErrorManager.require(comune_id is not None and comune_id > 0,
                         code=E_ANAG_VALIDAZIONE, message="Comune obbligatorio per via nuova.")
    ErrorManager.require(codice_postale_id is not None and codice_postale_id > 0,
                         code=E_ANAG_VALIDAZIONE, message="CAP obbligatorio per via nuova.")


_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)


# Scopo: i campi delle PATCH di geo si leggono per PRESENZA col BB
#        `PayloadValidator.campi_per_presenza`: una chiave presente si scrive
#        (anche `null`, che svuota un campo nullable), una chiave assente non
#        si tocca; chiavi fuori contratto e PATCH senza campi sono un 400.
# ⛔ Fino al 2026-10-20 le sei PATCH di geo passavano tutto da `dynamic_update`
#    (None = «non toccare»): il drawer manda `null` per un campo svuotato, e
#    svuotare l'ISO2 di uno stato o la palazzina di un indirizzo rispondeva
#    «salvato» senza scrivere; una chiave ignota si scartava; un PATCH vuoto
#    rispondeva 404 su un record che esiste; `{"attivo": null}` spegneva
#    l'indirizzo (brief-be-verifica-documentazione-api §A2, §B2, §B3).
#    `max_len` dei testi e' la lunghezza della colonna (doc dbzero): oltre, il
#    DB rispondeva 22001, cioe' un 500.
_CAMPI_NON_MODIFICABILI = "Campi non modificabili."


class GeoService:
    """Service per gestione entita' geografiche."""

    def __init__(self) -> None:
        self._geo = GeoRepository()
        self._ind = IndirizziRepository()

    # =================================================================
    # Toponomastica
    # =================================================================

    # Scopo: Lista paginata toponomastica.
    def list_toponomastica(self, **params) -> tuple[list, int]:
        return self._geo.list_toponomastica(**params)

    # Scopo: Dettaglio toponomastica.
    def get_toponomastica(self, pk: int) -> dict:
        result = self._geo.get_toponomastica(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Tipo strada non trovato.")
        assert result is not None
        return result

    # Scopo: Crea tipo strada con validazione e dedup.
    def create_toponomastica(self, payload: dict) -> dict:
        descrizione = _require_str(payload, "descrizione", "Descrizione obbligatoria.")
        return _create_with_dedup(
            lambda: self._geo.create_toponomastica(descrizione=descrizione),
            "Tipo strada gia' esistente.",
        )

    # Scopo: Aggiorna tipo strada con validazione e dedup.
    def update_toponomastica(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={"descrizione": (False, 100)}, flag=frozenset({"attivo"}),
        )
        return _update_with_dedup(
            lambda: self._geo.update_toponomastica(pk, campi),
            "Tipo strada gia' esistente.",
            "Tipo strada non trovato.",
        )

    # =================================================================
    # Comuni
    # =================================================================

    # Scopo: Lista paginata comuni.
    def list_comuni(self, **params) -> tuple[list, int]:
        return self._geo.list_comuni(**params)

    # Scopo: Crea comune con validazione e dedup.
    def create_comune(self, payload: dict) -> dict:
        descrizione = _require_str(payload, "descrizione", "Descrizione comune obbligatoria.")
        return _create_with_dedup(
            lambda: self._geo.create_comune(descrizione=descrizione, provincia_id=optional_int(payload, "provincia_id")),
            "Comune gia' esistente.",
        )

    # =================================================================
    # Codici Postali (CAP)
    # =================================================================

    # Scopo: Lista paginata codici postali.
    def list_codici_postali_paginated(self, **params) -> tuple[list, int]:
        return self._geo.list_codici_postali(**params)

    # Scopo: Dettaglio codice postale.
    def get_codice_postale(self, pk: int) -> dict:
        result = self._geo.get_codice_postale(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Codice postale non trovato.")
        assert result is not None
        return result

    # Scopo: Crea codice postale con validazione.
    def create_codice_postale(self, payload: dict) -> dict:
        codice = _require_str(payload, "codice", "Codice CAP obbligatorio.")
        comune_id = optional_int(payload, "comune_id")
        ErrorManager.require(comune_id is not None and comune_id > 0, code=E_ANAG_VALIDAZIONE, message="Comune obbligatorio.")
        assert comune_id is not None
        return _create_with_dedup(
            lambda: self._geo.create_codice_postale(codice=codice, comune_id=comune_id),
            "Codice postale gia' esistente.",
        )

    # Scopo: Aggiorna codice postale.
    def update_codice_postale(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={"codice": (False, 50)}, interi={"comune_id": False},
        )
        return _update_with_dedup(
            lambda: self._geo.update_codice_postale(pk, campi),
            "Codice postale gia' esistente.",
            "Codice postale non trovato.",
        )

    # =================================================================
    # Province
    # =================================================================

    # Scopo: Lista paginata province.
    def list_province(self, **params) -> tuple[list, int]:
        return self._geo.list_province_paginated(**params)

    # Scopo: Lista province per dropdown.
    def lookup_province(self) -> list:
        return self._geo.list_province()

    # Scopo: Dettaglio provincia.
    def get_provincia(self, pk: int) -> dict:
        result = self._geo.get_provincia(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Provincia non trovata.")
        assert result is not None
        return result

    # Scopo: Crea provincia con validazione e dedup.
    def create_provincia(self, payload: dict) -> dict:
        descrizione = _require_str(payload, "descrizione", "Descrizione obbligatoria.")
        sigla = _require_str(payload, "sigla", "Sigla obbligatoria.")
        return _create_with_dedup(
            lambda: self._geo.create_provincia(descrizione=descrizione, sigla=sigla, regione_id=optional_int(payload, "regione_id")),
            "Sigla provincia gia' esistente.",
        )

    # Scopo: Aggiorna provincia con validazione e dedup.
    def update_provincia(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={"descrizione": (False, 80), "sigla": (False, 10)},
            maiuscoli=frozenset({"sigla"}), interi={"regione_id": True},
        )
        return _update_with_dedup(
            lambda: self._geo.update_provincia(pk, campi),
            "Sigla provincia gia' esistente.",
            "Provincia non trovata.",
        )

    # =================================================================
    # Regioni
    # =================================================================

    # Scopo: Lista paginata regioni.
    def list_regioni(self, **params) -> tuple[list, int]:
        return self._geo.list_regioni(**params)

    # Scopo: Lista regioni per dropdown.
    def lookup_regioni(self, stato_id: int | None = None) -> list:
        return self._geo.list_regioni_lookup(stato_id=stato_id)

    # Scopo: Dettaglio regione.
    def get_regione(self, pk: int) -> dict:
        result = self._geo.get_regione(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Regione non trovata.")
        assert result is not None
        return result

    # Scopo: Crea regione con validazione e dedup.
    def create_regione(self, payload: dict) -> dict:
        descrizione = _require_str(payload, "descrizione", "Descrizione obbligatoria.")
        return _create_with_dedup(
            lambda: self._geo.create_regione(descrizione=descrizione, stato_id=optional_int(payload, "stato_id")),
            "Regione gia' esistente.",
        )

    # Scopo: Aggiorna regione con validazione e dedup.
    def update_regione(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={"descrizione": (False, None)}, interi={"stato_id": False},
        )
        return _update_with_dedup(
            lambda: self._geo.update_regione(pk, campi),
            "Regione gia' esistente.",
            "Regione non trovata.",
        )

    # =================================================================
    # Stati
    # =================================================================

    # Scopo: Lista paginata stati.
    def list_stati(self, **params) -> tuple[list, int]:
        return self._geo.list_stati(**params)

    # Scopo: Lista stati per dropdown.
    def lookup_stati(self) -> list:
        return self._geo.list_stati_lookup()

    # Scopo: Dettaglio stato.
    def get_stato(self, pk: int) -> dict:
        result = self._geo.get_stato(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Stato non trovato.")
        assert result is not None
        return result

    # Scopo: Crea stato con validazione e dedup.
    def create_stato(self, payload: dict) -> dict:
        descrizione = _require_str(payload, "descrizione", "Descrizione obbligatoria.")
        return _create_with_dedup(
            lambda: self._geo.create_stato(
                descrizione=descrizione,
                codice_iso2=payload.get("codice_iso2"),
                codice_iso3=payload.get("codice_iso3"),
                sigla_stato=payload.get("sigla_stato"),
                codice_telefonico=payload.get("codice_telefonico"),
                continente=payload.get("continente"),
            ),
            "Stato gia' esistente.",
        )

    # Scopo: Aggiorna stato con validazione e dedup.
    def update_stato(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={
                "descrizione": (False, 100), "codice_iso2": (True, 2), "codice_iso3": (True, 3),
                "sigla_stato": (True, 10), "codice_telefonico": (True, 10), "continente": (True, 50),
            },
            maiuscoli=frozenset({"codice_iso2", "codice_iso3", "sigla_stato"}),
        )
        return _update_with_dedup(
            lambda: self._geo.update_stato(pk, campi),
            "Stato gia' esistente.",
            "Stato non trovato.",
        )

    # =================================================================
    # Indirizzi dettaglio
    # =================================================================

    # Scopo: Check duplicato indirizzo via fn_check_indirizzo_duplicato (DB).
    #        La funzione DB gestisce normalizzazione, LIKE prefix e exact_match.
    #        Python e' passante: chiama la funzione, formatta il risultato.
    #        Due flussi: stradario_id diretto, oppure stradario_generale_id + comune_id.
    def check_indirizzo_duplicato(self, payload: dict) -> dict[str, Any]:
        stradario_id = optional_int(payload, "stradario_id")
        stradario_generale_id = optional_int(payload, "stradario_generale_id")
        comune_id = optional_int(payload, "comune_id")
        warnings: list[dict[str, Any]] = []
        # Serve almeno stradario_id oppure stradario_generale_id + comune_id
        if not stradario_id and not (stradario_generale_id and comune_id):
            return {"warnings": warnings}

        existing = self._ind.find_duplicato(
            stradario_id=stradario_id,
            civico=optional_int(payload, "civico"),
            estensione_civico=(payload.get("estensione_civico") or "").strip() or None,
            palazzina=(payload.get("palazzina") or "").strip() or None,
            scala=(payload.get("scala") or "").strip() or None,
            piano=(payload.get("piano") or "").strip() or None,
            interno=(payload.get("interno") or "").strip() or None,
            stradario_generale_id=stradario_generale_id,
            comune_id=comune_id,
            codice_postale_id=optional_int(payload, "codice_postale_id"),
        )
        if existing:
            label = existing["indirizzo_normalizzato"]
            comune = (existing.get("descrizione_comune") or "").strip()
            if comune:
                label = f"{label}, {comune}"
            exact = existing["exact_match"]
            msg = f"Indirizzo gia' presente: {label}" if exact else f"Indirizzo simile trovato: {label}"
            warnings.append({
                "field": "indirizzo",
                "message": msg,
                "indirizzo_dettaglio_id": existing["indirizzo_dettaglio_id"] if exact else None,
                "exact_match": exact,
            })
        return {"warnings": warnings}

    # Scopo: Lista paginata indirizzi.
    def list_indirizzi(self, **params) -> tuple[list, int]:
        return self._ind.list_indirizzi_dettaglio(**params)

    # Scopo: Dettaglio indirizzo.
    def get_indirizzo(self, pk: int) -> dict[str, Any]:
        result = self._ind.get_indirizzo_dettaglio(pk)
        ErrorManager.require(result is not None, code=E_ANAG_NOT_FOUND, message="Indirizzo non trovato.")
        assert result is not None
        return result

    # Scopo: Crea indirizzo. Le validazioni "via nuova" restano lato service; la
    # composizione (upsert stradario ×2 + get_or_create dettaglio) vive in una
    # sola funzione madre atomica anagrafiche.fn_create_indirizzo (fix #13).
    def create_indirizzo(self, payload: dict) -> dict[str, Any]:
        indirizzo_id = self.crea_dettaglio_indirizzo(payload)
        detail = self._ind.get_indirizzo_dettaglio(indirizzo_id)
        return detail or {"id": indirizzo_id}

    # Scopo: Il dettaglio (via + civico) di un indirizzo dal payload: il
    #        pre-check della via, poi la madre atomica
    #        `anagrafiche.fn_create_indirizzo` (get_or_create: lo stesso
    #        payload ritrova lo stesso dettaglio). Ritorna l'id del dettaglio.
    # ⭐ Sede unica (2026-10-18, 2b-2 del brief-db-processi-accensione-per-
    #    ambiente): la usa anche `SoggettiService` per gli indirizzi di soggetto
    #    e di ruolo, che fino ad allora ne tenevano una copia non atomica
    #    (`_create_stradario_da_generale` + `create_indirizzo_dettaglio`).
    def crea_dettaglio_indirizzo(self, payload: dict) -> int:
        richiedi_via(payload)
        # Fix analisi-fix-transazioni #13 (Classe D): upsert stradario (×2, solo
        # via nuova) + get_or_create del dettaglio in UNA sola fn madre atomica.
        # Prima erano get_or_create_stradario + create_indirizzo_dettaglio
        # separati → righe stradario di registro orfane se il dettaglio falliva.
        return self._ind.create_indirizzo_atomico(
            stradario_id=optional_int(payload, "stradario_id"),
            toponomastica_id=optional_int(payload, "toponomastica_id"),
            descrizione_via=(payload.get("descrizione_via") or "").strip() or None,
            comune_id=optional_int(payload, "comune_id"),
            codice_postale_id=optional_int(payload, "codice_postale_id"),
            civico=optional_int(payload, "civico"),
            estensione_civico=(payload.get("estensione_civico") or "").strip() or None,
            palazzina=(payload.get("palazzina") or "").strip() or None,
            scala=(payload.get("scala") or "").strip() or None,
            piano=(payload.get("piano") or "").strip() or None,
            interno=(payload.get("interno") or "").strip() or None,
        )

    # Scopo: Aggiorna dettagli civico indirizzo.
    def update_indirizzo(self, pk: int, payload: dict) -> dict:
        campi = _V.campi_per_presenza(
            payload, message=_CAMPI_NON_MODIFICABILI,
            testi={
                "estensione_civico": (True, 10), "palazzina": (True, 50), "scala": (True, 10),
                "piano": (True, 10), "interno": (True, 10),
            },
            interi={"civico": True},
            flag=frozenset({"attivo"}),
        )
        updated = self._ind.update_indirizzo_dettaglio(pk, campi)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND, message="Indirizzo non trovato.")
        return {"updated": True}

    # =================================================================
    # Codici postali
    # =================================================================

    # Scopo: Lista CAP per comune.
    def list_codici_postali(self, comune_id: int) -> list:
        ErrorManager.require(comune_id > 0, code=E_ANAG_VALIDAZIONE, message="comune_id obbligatorio.")
        return self._ind.list_codici_postali_by_comune(comune_id)
