# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di scrittura per `ui.lista_preferenza_utente` —
#        valida JSONB in ingresso (whitelist chiavi anti-injection),
#        UPSERT preferenza con snapshot del preset di base
#        (`preset_base_id` + `preset_base_data_update` per badge DEF-2),
#        delete idempotente.
#        Nessuna logica di dominio: la cascata e il filtro permessi
#        vivono nella fn DB.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.ui_repository import UiRepository

__all__ = [
    "ListaPreferenzaService",
    "E_UI_LISTA_NON_TROVATA",
    "E_UI_PREFERENZA_VALIDAZIONE",
    "E_UI_PREFERENZA_NON_TROVATA",
]


E_UI_LISTA_NON_TROVATA = "E_UI_LISTA_NON_TROVATA"
E_UI_PREFERENZA_VALIDAZIONE = "E_UI_PREFERENZA_VALIDAZIONE"
E_UI_PREFERENZA_NON_TROVATA = "E_UI_PREFERENZA_NON_TROVATA"

# Whitelist root del payload preferenza.
_PAYLOAD_KEYS = frozenset(
    {"colonne", "ordinamento", "filtri", "pagina_dimensione"}
)
# Whitelist di una singola colonna nella preferenza.
_COLONNA_KEYS = frozenset(
    {"codice", "ordine", "larghezza", "visibile", "fissata"}
)


class ListaPreferenzaService:
    """Facade scrittura preferenza utente per una lista."""

    def __init__(self, repository: UiRepository | None = None) -> None:
        self._repo = repository or UiRepository()
        self._validator = PayloadValidator(
            validation_code=E_UI_PREFERENZA_VALIDAZIONE,
        )

    # Scopo: Risolve `lista_codice -> lista_id` con errore parlante 404
    #        `E_UI_LISTA_NON_TROVATA` se la lista non esiste / non e' attiva.
    #        Pattern centralizzato (helper privato) per non duplicare la
    #        guardia in ogni metodo del service.
    def _require_lista_id(self, lista_codice: str) -> int:
        lista_id = self._repo.get_lista_id(lista_codice)
        ErrorManager.require(
            lista_id is not None,
            code=E_UI_LISTA_NON_TROVATA,
            message="Lista non trovata.",
            detail=f"codice lista: '{lista_codice}'",
            context={"lista_codice": lista_codice},
        )
        assert lista_id is not None
        return lista_id

    # Scopo: UPSERT preferenza utente per (auth_user, lista_codice).
    #        Valida la struttura JSONB in ingresso, calcola lo snapshot
    #        del preset di base e materializza il record. Ritorna l'id
    #        della preferenza salvata.
    def upsert(
        self,
        user: Any,
        lista_codice: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # 1. Lista deve esistere
        lista_id = self._require_lista_id(lista_codice)

        # 2. Whitelist + tipi del payload
        configurazione = self._validate_payload(payload)

        # 3. Snapshot preset di base coerente con la cascata della fn DB
        emittente_id = PermissionResolver.get_emittente_for_user(user)
        preset_id, preset_data_update = self._repo.get_preset_base_snapshot(
            lista_id=lista_id,
            auth_user_id=user.id,
            emittente_fiscale_id=emittente_id,
        )

        # 4. UPSERT
        pref_id = self._repo.upsert_preferenza(
            auth_user_id=user.id,
            lista_id=lista_id,
            configurazione=configurazione,
            preset_base_id=preset_id,
            preset_base_data_update=preset_data_update,
        )

        return {
            "id": pref_id,
            "preset_base_id": preset_id,
        }

    # Scopo: Elimina preferenza per (user, lista_codice). Idempotente:
    #        ritorna anche se la preferenza non esisteva. Solleva
    #        E_UI_LISTA_NON_TROVATA se la lista stessa non esiste
    #        (caso patologico: protezione contro path errati).
    def delete(
        self,
        user: Any,
        lista_codice: str,
    ) -> dict[str, Any]:
        lista_id = self._require_lista_id(lista_codice)

        deleted = self._repo.delete_preferenza(
            auth_user_id=user.id,
            lista_id=lista_id,
        )
        return {"deleted": deleted}

    # Scopo: Tombstone "Ignora banner preset aggiornato" (DEF-2). Setta
    #        `preset_aggiornato_ignored_at = NOW()` sulla preferenza utente.
    #        Il flag `preset_aggiornato` di `fn_resolve_lista_config` torna
    #        FALSE finche' il preset non viene modificato di nuovo
    #        (`preset.data_update > ignored_at`).
    #        Solleva E_UI_LISTA_NON_TROVATA se la lista non esiste e
    #        E_UI_PREFERENZA_NON_TROVATA se l'utente non ha ancora una
    #        preferenza (caso patologico: il banner non sarebbe visibile,
    #        ma chiamata diretta da retry/script va comunque rifiutata).
    def ignore_preset_update(
        self,
        user: Any,
        lista_codice: str,
    ) -> dict[str, Any]:
        lista_id = self._require_lista_id(lista_codice)

        ignored = self._repo.set_preset_aggiornato_ignored(
            auth_user_id=user.id,
            lista_id=lista_id,
        )
        ErrorManager.require(
            ignored,
            code=E_UI_PREFERENZA_NON_TROVATA,
            message="Preferenza utente non trovata per questa lista.",
            detail=(
                "Nessuna preferenza salvata per "
                f"(user_id={user.id}, codice='{lista_codice}')."
            ),
            context={"lista_codice": lista_codice},
        )

        return {"ignored": True}

    # Scopo: Valida il payload contro le whitelist e ritorna il dict
    #        normalizzato pronto per il salvataggio JSONB. Difende da
    #        chiavi extra (anti-injection) e tipi sbagliati.
    def _validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            ErrorManager.raise_error(
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza lista non valida.",
                detail="Il payload deve essere un oggetto JSON.",
            )

        self._validator.validate_allowed_keys(
            payload, allowed=_PAYLOAD_KEYS,
            message="Preferenza lista non valida.",
        )

        config: dict[str, Any] = {}

        # colonne: lista di oggetti normalizzati
        colonne_raw = payload.get("colonne")
        if colonne_raw is not None:
            config["colonne"] = self._validator.voci(
                colonne_raw, self._validate_colonna, campo="colonne",
                message="Preferenza lista non valida.",
            )

        # ordinamento: lista di oggetti {col, dir}; trasparente al BE
        ordinamento = payload.get("ordinamento")
        if ordinamento is not None:
            ErrorManager.require(
                isinstance(ordinamento, list),
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza lista non valida.",
                detail="Il campo 'ordinamento' deve essere una lista.",
            )
            config["ordinamento"] = ordinamento

        # filtri: dict trasparente (formato deciso col componente Vue, §10.1.2)
        filtri = payload.get("filtri")
        if filtri is not None:
            ErrorManager.require(
                isinstance(filtri, dict),
                code=E_UI_PREFERENZA_VALIDAZIONE,
                message="Preferenza lista non valida.",
                detail="Il campo 'filtri' deve essere un oggetto.",
            )
            config["filtri"] = filtri

        # pagina_dimensione: qui solo la FORMA (un intero). Quali misure sono
        # ammesse lo dice il catalogo `ui.misure_pagina`, e lo fa rispettare il
        # guard a DB sulla preferenza (`E_UI_MISURA_PAGINA_NON_AMMESSA`, 400
        # dal middleware). ⛔ Il vecchio tetto `MAX_LIMIT` era una seconda
        # regola, diversa dal catalogo: ammetteva 37, che il paginatore non
        # offre.
        pagina_dim = self._validator.optional_positive_int(
            payload, key="pagina_dimensione",
            message="Preferenza lista non valida.",
        )
        if pagina_dim is not None:
            config["pagina_dimensione"] = pagina_dim

        return config

    # Scopo: Legge una colonna della preferenza (lettore di `PayloadValidator.voci`,
    #        che ha gia' giudicato la forma: un oggetto). Whitelist chiavi,
    #        codice obbligatorio, ordine/larghezza int, visibile/fissata bool.
    def _validate_colonna(
        self, raw: dict[str, Any], idx: int,
    ) -> dict[str, Any]:
        self._validator.validate_allowed_keys(
            raw, allowed=_COLONNA_KEYS,
            message=f"colonne[{idx}]: campi non supportati.",
        )

        codice = self._validator.require_string(
            raw, key="codice",
            message=f"colonne[{idx}]: 'codice' obbligatorio.",
        )
        out: dict[str, Any] = {"codice": codice}

        ordine = self._validator.optional_positive_int(
            raw, key="ordine",
            message=f"colonne[{idx}]: 'ordine' deve essere intero positivo.",
        )
        if ordine is not None:
            out["ordine"] = ordine

        larghezza = self._validator.optional_positive_int(
            raw, key="larghezza",
            message=f"colonne[{idx}]: 'larghezza' deve essere intero positivo.",
        )
        if larghezza is not None:
            out["larghezza"] = larghezza

        visibile = self._validator.optional_bool(raw, key="visibile")
        if visibile is not None:
            out["visibile"] = visibile

        fissata = self._validator.optional_bool(raw, key="fissata")
        if fissata is not None:
            out["fissata"] = fissata

        return out
