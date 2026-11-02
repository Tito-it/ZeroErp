# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per `ui.lista_preset` + composizione
#        `ui.lista_preset_colonna` (Blocco F Fase 1).
#
#        Operazioni esposte:
#          - list_preset(lista_id)       — lettura preset di una lista
#          - get_preset(preset_id)       — dettaglio singolo preset
#          - create_preset(payload)      — INSERT testata
#          - update_preset(preset_id,..) — PATCH testata (campi mutabili)
#          - delete_preset(preset_id)    — DELETE (CASCADE su composizione)
#          - list_preset_colonne(...)    — lettura composizione
#          - replace_preset_colonne(...) — PUT atomico composizione
#
#        Validazione:
#          - whitelist chiavi payload via PayloadValidator
#          - campi immutabili (lista_id/ambito/profilo/emittente) accettati
#            solo in CREATE
#          - integrita' ambito_refs / unicita' codice / partial UNIQUE
#            is_default delegate al DB (mappate via map_integrity_error)
#
#        Niente filtro scope emittente lato service: il Blocco F e'
#        ammesso solo a SUPER_ADMIN o azioni `ui_preset_manage` /
#        `ui_permesso_manage`. Lo scope viene applicato a livello view
#        tramite la base class (vedi views_admin.py).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services._audit import user_label

E_PRESET_VALIDATION = "E_UI_PRESET_VALIDAZIONE"
E_PRESET_NOT_FOUND = "E_UI_PRESET_NON_TROVATO"
E_LISTA_NOT_FOUND = "E_UI_LISTA_NON_TROVATA"

# DRIFT RISK: questi valori devono restare allineati all'enum DB
# `ui.ambito_preset` (definito in 20260506-01-02-create-enum-ui-ambito-preset).
# Aggiungere/rimuovere un valore qui senza toccare il DB (o viceversa)
# rompe l'INSERT/UPDATE con InvalidTextRepresentation. La duplicazione e'
# accettata perche' il DB e' single source di verita' (FK enum garantisce
# il check finale): qui filtriamo presto per dare un errore parlante.
_AMBITI_AMMESSI: frozenset[str] = frozenset(
    {"sistema", "emittente_fiscale", "ruolo"}
)

# Whitelist chiavi del payload create. Comprende immutabili (`lista_id`,
# `ambito`, `profilo_accesso_id`, `emittente_fiscale_id`) + mutabili.
CREATE_KEYS: frozenset[str] = frozenset(
    {
        "lista_id",
        "codice",
        "descrizione",
        "ambito",
        "profilo_accesso_id",
        "emittente_fiscale_id",
        "is_default",
        "pagina_dimensione",
        "ordinamento_default",
        "filtri_default",
        "attivo",
    }
)

# Whitelist chiavi del payload update. Esclude gli immutabili. Per
# cambiare ambito/refs si crea un nuovo preset.
UPDATE_KEYS: frozenset[str] = frozenset(
    {
        "codice",
        "descrizione",
        "is_default",
        "pagina_dimensione",
        "ordinamento_default",
        "filtri_default",
        "attivo",
    }
)

_MAX_CODICE_LEN = 80
_MAX_DESCRIZIONE_LEN = 200

# Mapping vincoli DB -> codice + messaggio applicativo. I nomi sono
# allineati a 20260506-04 (CHECK + UNIQUE + partial UNIQUE).
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_ui_lista_preset_lista_codice": (
        E_PRESET_VALIDATION,
        "Esiste gia' un preset con questo codice per la lista.",
        "codice",
    ),
    "uq_ui_lista_preset_default": (
        E_PRESET_VALIDATION,
        "Esiste gia' un preset di default per (lista, ambito, profilo, emittente).",
    ),
}

_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_lista_preset_lista_definizione": (
        E_PRESET_VALIDATION,
        "lista_id non valido (FK su ui.lista_definizione).",
    ),
    "fk_lista_preset_profili_accesso": (
        E_PRESET_VALIDATION,
        "profilo_accesso_id non valido (FK su config.profili_accesso).",
    ),
    "fk_lista_preset_emittenti_fiscali": (
        E_PRESET_VALIDATION,
        "emittente_fiscale_id non valido (FK su anagrafiche.emittenti_fiscali).",
    ),
}

_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_ui_lista_preset_ambito_refs": (
        E_PRESET_VALIDATION,
        "Ambito incoerente con i riferimenti: 'sistema' richiede entrambi NULL, "
        "'ruolo' richiede profilo_accesso_id NOT NULL, 'emittente_fiscale' richiede "
        "emittente_fiscale_id NOT NULL.",
    ),
}


class ListaPresetAdminService:
    """Facade scrittura preset lista (Blocco F admin)."""

    def __init__(self, repo: UiAdminRepository | None = None) -> None:
        self._repo = repo or UiAdminRepository()
        self._v = PayloadValidator(validation_code=E_PRESET_VALIDATION)

    # =================================================================
    # Read
    # =================================================================

    # Scopo: Lista preset di una lista. 404 (E_UI_LISTA_NON_TROVATA) se
    #        lista_id non esiste o non e' attivo.
    # ⭐ Forma `{results, count}` — vedi la nota su `list_colonne_admin`:
    #    conteggio da query SUA, mai `len(results)`.
    def list_preset(self, lista_id: int) -> dict[str, Any]:
        self._guard_lista_exists(lista_id)
        return {
            "results": self._repo.list_preset_by_lista(lista_id),
            "count": self._repo.count_preset_by_lista(lista_id),
        }

    # Scopo: Dettaglio singolo preset. 404 (E_UI_PRESET_NON_TROVATO) se
    #        l'id non esiste. Usato da get post-create / post-update.
    def get_preset(self, preset_id: int) -> dict[str, Any]:
        result = testata_o_not_found(
            self._repo.get_preset, preset_id,
            code=E_PRESET_NOT_FOUND, message="Preset lista non trovato.",
            id_name="preset_id", function_name="lista_preset_admin_service.get_preset",
        )
        return result

    # =================================================================
    # Create / Update / Delete - testata
    # =================================================================

    # Scopo: Crea un nuovo preset (testata). Valida payload, applica
    #        defaults applicativi, esegue INSERT e mappa eventuali
    #        violazioni unique/FK/CHECK su codici applicativi parlanti.
    def create_preset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload,
            allowed=CREATE_KEYS,
            message="Payload preset non valido.",
        )
        data = self._build_create_data(payload)
        # Lista deve esistere e essere attiva (404 unificato).
        self._guard_lista_exists(data["lista_id"])

        try:
            new_id = self._repo.create_preset(
                data, user_insert=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_PRESET_VALIDATION,
                fallback_message="Violazione vincolo DB su preset lista.",
                context={
                    "lista_id": data.get("lista_id"),
                    "codice": data.get("codice"),
                    "ambito": data.get("ambito"),
                },
            )
        return self.get_preset(new_id)

    # Scopo: Aggiorna preset sui soli campi presenti nel payload. Reject
    #        di campi immutabili PRIMA della validazione altri campi per
    #        messaggio parlante.
    def update_preset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        preset_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(preset_id, field="preset_id")
        # 404 unificato: legge il dettaglio per validare l'id.
        self.get_preset(preset_id)

        immutabili = {
            "lista_id", "ambito", "profilo_accesso_id", "emittente_fiscale_id"
        }
        intersect = sorted(set(payload.keys()) & immutabili)
        if intersect:
            ErrorManager.raise_error(
                code=E_PRESET_VALIDATION,
                message="Campi immutabili presenti in payload update.",
                detail=f"campi non aggiornabili={intersect!r}",
            )

        self._v.validate_allowed_keys(
            payload,
            allowed=UPDATE_KEYS,
            message="Payload preset non valido.",
        )
        data = self._build_update_data(payload)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_preset(
                preset_id, data, user_update=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_PRESET_VALIDATION,
                fallback_message="Violazione vincolo DB su preset lista.",
                context={"preset_id": preset_id},
            )
        ErrorManager.require(
            updated,
            code=E_PRESET_NOT_FOUND,
            message="Preset lista non trovato.",
            detail=f"preset_id={preset_id}",
        )
        return self.get_preset(preset_id)

    # Scopo: Cancella preset. ON DELETE SET NULL su lista_preferenza_utente
    #        (DB-2) preserva le preferenze: il badge "preset aggiornato"
    #        sparira' e l'utente lavorera' direttamente sul catalogo grezzo
    #        finche' non sceglie un altro preset.
    def delete_preset(self, preset_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(preset_id, field="preset_id")
        deleted = self._repo.delete_preset(preset_id)
        ErrorManager.require(
            deleted,
            code=E_PRESET_NOT_FOUND,
            message="Preset lista non trovato.",
            detail=f"preset_id={preset_id}",
        )
        return {"deleted": True, "id": preset_id}

    # =================================================================
    # Composizione preset (lista_preset_colonna)
    # =================================================================

    # Scopo: Restituisce la composizione del preset (ordine colonne +
    #        flag visibilita'/larghezza/fissata). 404 se preset assente.
    def list_preset_colonne(self, preset_id: int) -> list[dict[str, Any]]:
        self._v.guard_positive_int(preset_id, field="preset_id")
        # Garantisce 404 esplicito se l'id non esiste, evitando di tornare
        # lista vuota ambigua.
        self.get_preset(preset_id)
        return self._repo.list_preset_colonne(preset_id)

    # Scopo: Replace atomico della composizione di un preset. Valida il
    #        payload (lista di colonne con campi obbligatori), poi delega
    #        alla repository la transazione DELETE+INSERT.
    def replace_preset_colonne(
        self,
        preset_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(preset_id, field="preset_id")
        # 404 se preset inesistente.
        self.get_preset(preset_id)

        self._v.validate_allowed_keys(
            payload,
            allowed=frozenset({"colonne"}),
            message="Payload composizione preset non valido.",
        )
        # Una lista di voci, ogni voce un oggetto (BB): assente e' un 400, mai
        # «vuota» — la composizione si sostituisce in blocco.
        normalized = self._v.voci(
            payload.get("colonne"), self._validate_colonna_row, campo="colonne",
        )
        seen_colonne: set[int] = set()
        for idx, row in enumerate(normalized):
            if row["colonna_id"] in seen_colonne:
                ErrorManager.raise_error(
                    code=E_PRESET_VALIDATION,
                    message="Colonna duplicata nella composizione preset.",
                    detail=f"colonne[{idx}] colonna_id={row['colonna_id']} ripetuta",
                )
            seen_colonne.add(row["colonna_id"])

        try:
            inserted = self._repo.replace_preset_colonne(
                preset_id, normalized
            )
        except IntegrityError as exc:
            # FK su ui.lista_colonna o PK preset+colonna: messaggio generico
            # (la duplicazione e' gia' bloccata da seen_colonne).
            map_integrity_error(
                exc,
                fallback_code=E_PRESET_VALIDATION,
                fallback_message="Violazione vincolo DB su composizione preset.",
                context={"preset_id": preset_id},
            )
        return {"preset_id": preset_id, "inserted": inserted}

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Normalizza il payload create. Applica defaults applicativi
    #        (is_default=False, attivo=True). I campi JSONB
    #        ordinamento_default/filtri_default sono accettati come
    #        liste/dict; conversione a JSON la fa il repository.
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["lista_id"] = self._v.require_positive_int(payload, "lista_id")
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["descrizione"] = self._v.require_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
        )
        ambito = self._v.require_string(payload, "ambito")
        ErrorManager.require(
            ambito in _AMBITI_AMMESSI,
            code=E_PRESET_VALIDATION,
            message="Ambito preset non valido.",
            detail=f"ambito='{ambito}', ammessi={sorted(_AMBITI_AMMESSI)!r}",
        )
        data["ambito"] = ambito

        # Refs condizionali. Il CHECK DB e' la guard finale: qui
        # accettiamo coerenze ovvie e lasciamo il resto al CHECK.
        if ambito == "ruolo":
            data["profilo_accesso_id"] = self._v.require_positive_int(
                payload, "profilo_accesso_id",
                message="profilo_accesso_id obbligatorio quando ambito='ruolo'.",
            )
            data["emittente_fiscale_id"] = None
        elif ambito == "emittente_fiscale":
            data["emittente_fiscale_id"] = self._v.require_positive_int(
                payload, "emittente_fiscale_id",
                message="emittente_fiscale_id obbligatorio quando ambito='emittente_fiscale'.",
            )
            data["profilo_accesso_id"] = None
        else:  # sistema
            data["profilo_accesso_id"] = None
            data["emittente_fiscale_id"] = None

        is_default = self._v.optional_bool(payload, "is_default")
        data["is_default"] = bool(is_default) if is_default is not None else False

        attivo = self._v.optional_bool(payload, "attivo")
        data["attivo"] = bool(attivo) if attivo is not None else True

        # pagina_dimensione: qui solo la FORMA (un intero). Quali misure sono
        # ammesse lo dice il catalogo `ui.misure_pagina`, e lo fa rispettare
        # il DB (guard + FK: `E_UI_MISURA_PAGINA_NON_AMMESSA`, 400 dal
        # middleware). ⛔ Nessun tetto qui: era una seconda regola, diversa dal
        # catalogo (ammetteva 37, che il paginatore non offre).
        pag_dim = self._v.optional_positive_int(payload, "pagina_dimensione")
        if pag_dim is not None:
            data["pagina_dimensione"] = pag_dim

        if "ordinamento_default" in payload:
            value = payload["ordinamento_default"]
            ErrorManager.require(
                value is None or isinstance(value, list),
                code=E_PRESET_VALIDATION,
                message="ordinamento_default deve essere una lista o null.",
            )
            data["ordinamento_default"] = value

        if "filtri_default" in payload:
            value = payload["filtri_default"]
            ErrorManager.require(
                value is None or isinstance(value, dict),
                code=E_PRESET_VALIDATION,
                message="filtri_default deve essere un oggetto o null.",
            )
            data["filtri_default"] = value

        return data

    # Scopo: Normalizza il payload update sui soli campi mutabili
    #        presenti. Salta chiavi assenti per non sovrascrivere.
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "codice" in payload:
            data["codice"] = self._v.require_string(
                payload, "codice", max_len=_MAX_CODICE_LEN
            )
        if "descrizione" in payload:
            data["descrizione"] = self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
            )
        if "is_default" in payload:
            value = self._v.optional_bool(payload, "is_default")
            ErrorManager.require(
                value is not None,
                code=E_PRESET_VALIDATION,
                message="Il campo 'is_default' non puo' essere NULL.",
                detail="field=is_default",
            )
            data["is_default"] = bool(value)
        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                value is not None,
                code=E_PRESET_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            data["attivo"] = bool(value)
        if "pagina_dimensione" in payload:
            # Solo la forma: l'ammissibilita' la decide il catalogo a DB
            # (vedi `_build_create_data`). NULL = «il default».
            data["pagina_dimensione"] = self._v.optional_positive_int(
                payload, "pagina_dimensione"
            )
        if "ordinamento_default" in payload:
            value = payload["ordinamento_default"]
            ErrorManager.require(
                value is None or isinstance(value, list),
                code=E_PRESET_VALIDATION,
                message="ordinamento_default deve essere una lista o null.",
            )
            data["ordinamento_default"] = value
        if "filtri_default" in payload:
            value = payload["filtri_default"]
            ErrorManager.require(
                value is None or isinstance(value, dict),
                code=E_PRESET_VALIDATION,
                message="filtri_default deve essere un oggetto o null.",
            )
            data["filtri_default"] = value
        return data

    # Scopo: Valida una singola riga di composizione preset.
    def _validate_colonna_row(
        self, raw: dict[str, Any], idx: int,
    ) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            raw,
            allowed=frozenset({
                "colonna_id", "ordine", "larghezza",
                "visibile", "fissata",
            }),
            message=f"colonne[{idx}]: campi non supportati.",
        )
        out: dict[str, Any] = {
            "colonna_id": self._v.require_positive_int(
                raw, "colonna_id",
                message=f"colonne[{idx}]: 'colonna_id' obbligatorio.",
            ),
            "ordine": self._v.require_positive_int(
                raw, "ordine",
                message=f"colonne[{idx}]: 'ordine' obbligatorio (intero positivo).",
            ),
        }
        larghezza = self._v.optional_positive_int(
            raw, "larghezza",
            message=f"colonne[{idx}]: 'larghezza' deve essere intero positivo.",
        )
        if larghezza is not None:
            out["larghezza"] = larghezza
        visibile = self._v.optional_bool(raw, "visibile")
        out["visibile"] = bool(visibile) if visibile is not None else True
        fissata = self._v.optional_bool(raw, "fissata")
        out["fissata"] = bool(fissata) if fissata is not None else False
        return out

    # Scopo: Verifica che `lista_id` esista e sia attivo, sollevando
    #        E_UI_LISTA_NON_TROVATA altrimenti.
    def _guard_lista_exists(self, lista_id: int) -> None:
        ErrorManager.require(
            self._repo.get_definizione(lista_id) is not None,
            code=E_LISTA_NOT_FOUND,
            message="Lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
