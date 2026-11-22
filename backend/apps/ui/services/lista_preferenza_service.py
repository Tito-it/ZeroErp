# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di scrittura per `ui.lista_preferenza_utente` —
#        il corpo deve essere un oggetto con almeno una chiave (la forma la
#        giudica il guard del DB), UPSERT preferenza col preset di base di oggi (`preset_base_id`,
#        dalla risoluzione; lo snapshot del badge DEF-2 lo scrive il DB),
#        delete idempotente.
#        Nessuna logica di dominio: la cascata e il filtro permessi
#        vivono nella fn DB.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.ui_repository import UiRepository
from apps.ui.services._preferenza import (
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    preset_base_id_di_oggi,
    richiedi_preferenza_non_vuota,
)

__all__ = [
    "ListaPreferenzaService",
    "E_UI_LISTA_NON_TROVATA",
    "E_UI_PREFERENZA_VALIDAZIONE",
    "E_UI_PREFERENZA_NON_TROVATA",
]


E_UI_LISTA_NON_TROVATA = "E_UI_LISTA_NON_TROVATA"

# ⛔ Nessuna whitelist qui: chiavi e voci ammesse le giudica il guard del DB
#    (`E_UI_CONFIGURAZIONE_FORMA`). `ordinamento` e `filtri` sono usciti dalla
#    preferenza (Q38/Q39 §6 di brief-db-revisione-ui, giro 2 del 2026-11-21):
#    nel corpo sono un 400 del DB, come ogni chiave non ammessa.


class ListaPreferenzaService:
    """Facade scrittura preferenza utente per una lista."""

    def __init__(self, repository: UiRepository | None = None) -> None:
        self._repo = repository or UiRepository()

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
    #        Valida la struttura JSONB in ingresso, legge il preset di base
    #        di oggi dalla risoluzione e materializza il record. Ritorna l'id
    #        della preferenza salvata.
    def upsert(
        self,
        user: Any,
        lista_codice: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # 1. Lista deve esistere
        lista_id = self._require_lista_id(lista_codice)

        # 2. Un oggetto con almeno una chiave; la forma la giudica il DB
        configurazione = self._validate_payload(payload)

        # 3. Il preset di base di oggi, dalla risoluzione (stesso emittente
        #    di `UiService.get_lista_config`: la base salvata e' quella che
        #    l'utente vede). Lo snapshot lo scrive il trigger del DB.
        emittente_id = PermissionResolver.get_emittente_for_user(user)
        preset_id = preset_base_id_di_oggi(
            self._repo.resolve_lista_config(
                lista_codice=lista_codice,
                auth_user_id=user.id,
                emittente_fiscale_id=emittente_id,
            )
        )

        # 4. UPSERT
        pref_id = self._repo.upsert_preferenza(
            auth_user_id=user.id,
            lista_id=lista_id,
            configurazione=configurazione,
            preset_base_id=preset_id,
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

    # Scopo: «Ignora» del banner preset aggiornato (DEF-2). Riallinea lo
    #        snapshot del preset di base al contenuto di oggi (il DB lo
    #        riscrive quando la preferenza nomina `preset_base_id`): il flag
    #        `preset_aggiornato` di `fn_resolve_lista_config` torna FALSE
    #        finche' il contenuto del preset non cambia di nuovo, chiave per
    #        chiave (`preset_aggiornato_chiavi`).
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

        ignored = self._repo.riallinea_snapshot_base(
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

    # Scopo: La configurazione da salvare: il corpo cosi' com'e', se e' un
    #        oggetto con almeno una chiave (BB `richiedi_preferenza_non_vuota`).
    #        La forma la giudica il DB (vedi il BB).
    def _validate_payload(self, payload: Any) -> dict[str, Any]:
        return richiedi_preferenza_non_vuota(
            payload, message="Preferenza lista non valida.",
        )
