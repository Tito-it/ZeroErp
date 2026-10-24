# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per `ui.lista_colonna` — Blocco F Fase 2 DEF-5b.
#
#        Operazioni esposte:
#          - list_colonne_admin(lista_id) — lista completa per pagina tecnica
#          - get_colonna(colonna_id)      — dettaglio singolo
#          - create_colonna(lista_id, ..) — INSERT con validazione enum + UX
#          - update_colonna(colonna_id, ..) — PATCH (lista_id immutabile)
#          - delete_colonna(colonna_id, *, force=False)
#                                          — DELETE con soft-block preferenze
#
#        Validazione lato Python:
#          - whitelist chiavi payload via PayloadValidator
#          - enum tipo_colonna / tipo_dato / allineamento (drift risk con DB)
#          - vincolo CHECK chk_ui_lista_colonna_azione_non_esportabile:
#            forziamo `esportabile=False` quando `tipo_colonna='azione'`
#            (silently normalize, decisione 6 _def.md) per evitare errore
#            tardivo del DB e UX rotta lato form.
#          - lista_id immutabile in update (no spostamenti cross-lista)
#
#        Validazione lato DB:
#          - UNIQUE (lista_id, codice) -> map_integrity_error
#          - FK CASCADE su lista_preset_colonna / lista_colonna_permesso
#          - trigger guard valida_campo_sorgente -> E_UI_CAMPO_SORGENTE_NON_TROVATO
#          - CHECK chk_ui_lista_colonna_azione_non_esportabile (defense in depth)
#
#        Soft-block DELETE: il service conta le preferenze utente che
#        referenziano la colonna per codice nel JSONB
#        `configurazione->colonne` e blocca con E_UI_COLONNA_IN_USO.
#        Soft-disable via PATCH `attivo=false` resta l'alternativa
#        raccomandata (decisione 5 _def.md).
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

E_LISTA_NOT_FOUND = "E_UI_LISTA_NON_TROVATA"
E_DEFINIZIONE_NOT_FOUND = "E_UI_DEFINIZIONE_NON_TROVATA"
E_COLONNA_VALIDATION = "E_UI_COLONNA_VALIDAZIONE"
E_COLONNA_NOT_FOUND = "E_UI_COLONNA_NON_TROVATA"
E_COLONNA_IN_USE = "E_UI_COLONNA_IN_USO"

# DRIFT RISK: gli enum DB sono `ui.tipo_colonna`, `ui.tipo_dato`,
# `ui.allineamento_colonna`. Aggiungere/rimuovere un valore qui senza
# toccare il DB rompe l'INSERT/UPDATE con InvalidTextRepresentation.
# La duplicazione e' accettata perche' il DB e' single source di verita'
# (FK enum garantisce check finale): qui filtriamo presto per dare un
# errore parlante.
_TIPI_COLONNA: frozenset[str] = frozenset(
    {"identificatore", "informazione", "azione"}
)
_TIPI_DATO: frozenset[str] = frozenset(
    {"string", "numeric", "date", "datetime", "boolean", "enum"}
)
_ALLINEAMENTI: frozenset[str] = frozenset({"left", "right", "center"})

# Whitelist chiavi payload create. lista_id arriva dal path della view.
CREATE_KEYS: frozenset[str] = frozenset(
    {
        "codice",
        "etichetta",
        "etichetta_estesa",
        "etichetta_i18n_key",
        "campo_sorgente",
        "tipo_colonna",
        "tipo_dato",
        "formato",
        "larghezza_default",
        "ordine_default",
        "allineamento",
        "gruppo",
        "gruppo_ordine",
        "filtrabile",
        "ordinabile",
        "esportabile",
        "ricercabile_full",
        "sensibile",
        "attivo",
    }
)

# Whitelist update: gli stessi campi + esclusione lista_id (immutabile,
# non comparirebbe comunque nel payload). Il `codice` cambia con UNIQUE
# check DB.
UPDATE_KEYS: frozenset[str] = CREATE_KEYS

_MAX_CODICE_LEN = 80
_MAX_ETICHETTA_LEN = 120
_MAX_ETICHETTA_ESTESA_LEN = 200
_MAX_I18N_KEY_LEN = 120
_MAX_CAMPO_SORGENTE_LEN = 80
_MAX_FORMATO_LEN = 60
_MAX_GRUPPO_LEN = 60
_MAX_LARGHEZZA = 4000
_MAX_ORDINE = 100000

# Mapping vincoli DB -> codice + messaggio applicativo.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_ui_lista_colonna_lista_codice": (
        E_COLONNA_VALIDATION,
        "Esiste gia' una colonna con questo codice nella lista.",
        "codice",
    ),
}

_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_lista_colonna_lista_definizione": (
        E_COLONNA_VALIDATION,
        "lista_id non valido (FK su ui.lista_definizione).",
    ),
}

_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_ui_lista_colonna_azione_non_esportabile": (
        E_COLONNA_VALIDATION,
        "Le colonne di tipo 'azione' non possono essere esportabili.",
    ),
}


class ListaColonnaAdminService:
    """Facade CRUD ui.lista_colonna (Blocco F Fase 2 DEF-5b)."""

    def __init__(self, repo: UiAdminRepository | None = None) -> None:
        self._repo = repo or UiAdminRepository()
        self._v = PayloadValidator(validation_code=E_COLONNA_VALIDATION)

    # =================================================================
    # Read
    # =================================================================

    # Scopo: Lista colonne admin di una lista (incluse disattivate,
    #        campi completi). 404 se lista_id non esiste in
    #        lista_definizione (anche disattivata: la pagina tecnica
    #        deve poter editare colonne di liste soft-disabled).
    # ⭐ Forma `{results, count}`: il `count` non impagina, DICHIARA quante
    #    righe esistono, cosi' il client puo' verificare di averle tutte invece
    #    di assumerlo (guard `troncamentoSospetto` di `<ListaConfigurabile>` in
    #    modalita' `paginata: false`). ⛔ Viene da una query SUA, non da
    #    `len(results)`: derivarlo dalle righe sposterebbe la tautologia dal
    #    frontend al backend senza toglierla.
    def list_colonne_admin(self, lista_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(lista_id, field="lista_id")
        ErrorManager.require(
            self._repo.get_definizione_admin(lista_id) is not None,
            code=E_DEFINIZIONE_NOT_FOUND,
            message="Definizione lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return {
            "results": self._repo.list_colonne_by_lista_admin(lista_id),
            "count": self._repo.count_colonne_by_lista_admin(lista_id),
        }

    # Scopo: Dettaglio colonna per id. 404 se inesistente.
    def get_colonna(self, colonna_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(colonna_id, field="colonna_id")
        result = testata_o_not_found(
            self._repo.get_colonna_admin, colonna_id,
            code=E_COLONNA_NOT_FOUND, message="Colonna lista non trovata.",
            id_name="colonna_id", function_name="lista_colonna_admin_service.get_colonna",
        )
        return result

    # =================================================================
    # Create / Update / Delete
    # =================================================================

    # Scopo: Crea una nuova colonna nella lista indicata. lista_id
    #        arriva dal path della view (non dal payload).
    def create_colonna(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        lista_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(lista_id, field="lista_id")
        ErrorManager.require(
            self._repo.get_definizione_admin(lista_id) is not None,
            code=E_DEFINIZIONE_NOT_FOUND,
            message="Definizione lista non trovata.",
            detail=f"lista_id={lista_id}",
        )

        self._v.validate_allowed_keys(
            payload,
            allowed=CREATE_KEYS,
            message="Payload colonna lista non valido.",
        )
        data = self._build_create_data(lista_id, payload)

        try:
            new_id = self._repo.create_colonna(
                data, user_insert=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_COLONNA_VALIDATION,
                fallback_message="Violazione vincolo DB su colonna lista.",
                context={
                    "lista_id": lista_id,
                    "codice": data.get("codice"),
                },
            )
        return self.get_colonna(new_id)

    # Scopo: Aggiorna colonna sui soli campi presenti nel payload.
    #        lista_id NON e' in whitelist (immutabile) — per spostare
    #        una colonna fra liste si cancella e ricrea.
    def update_colonna(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        colonna_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(colonna_id, field="colonna_id")
        # 404 + caricamento corrente per UX vincoli (es. tipo_colonna
        # passa da informazione -> azione -> serve forzare esportabile=
        # False anche se non passato dal client).
        current = self.get_colonna(colonna_id)

        # Reject espliciti per immutabili: dare messaggio parlante prima
        # della whitelist.
        if "lista_id" in payload:
            ErrorManager.raise_error(
                code=E_COLONNA_VALIDATION,
                message="Campo immutabile presente in payload update.",
                detail="lista_id non aggiornabile",
            )

        self._v.validate_allowed_keys(
            payload,
            allowed=UPDATE_KEYS,
            message="Payload colonna lista non valido.",
        )
        data = self._build_update_data(payload, current=current)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_colonna(
                colonna_id, data, user_update=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_COLONNA_VALIDATION,
                fallback_message="Violazione vincolo DB su colonna lista.",
                context={"colonna_id": colonna_id},
            )
        ErrorManager.require(
            updated,
            code=E_COLONNA_NOT_FOUND,
            message="Colonna lista non trovata.",
            detail=f"colonna_id={colonna_id}",
        )
        return self.get_colonna(colonna_id)

    # Scopo: Cancella colonna. Soft-block applicativo se ci sono
    #        preferenze utente che referenziano il `codice` colonna nel
    #        JSONB configurazione->colonne. La FK CASCADE su
    #        lista_preset_colonna / lista_colonna_permesso fa il pulito
    #        automatico. Soft-disable disponibile via PATCH attivo=false.
    def delete_colonna(self, colonna_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(colonna_id, field="colonna_id")
        # 404 + serve il codice + lista_id per il count preferenze.
        current = self.get_colonna(colonna_id)

        n_pref = self._repo.count_preferenze_referenced_by_colonna(
            lista_id=int(current["lista_id"]),
            codice=str(current["codice"]),
        )
        ErrorManager.require(
            n_pref == 0,
            code=E_COLONNA_IN_USE,
            message=(
                "La colonna e' in uso da preferenze utente. Disattivala con "
                "attivo=false invece di eliminarla."
            ),
            detail=(
                f"preferenze_count={n_pref}, lista_id={current['lista_id']}, "
                f"codice={current['codice']!r}"
            ),
            context={
                "colonna_id": colonna_id,
                "preferenze_count": n_pref,
            },
        )

        try:
            deleted = self._repo.delete_colonna(colonna_id)
        except IntegrityError as exc:
            # Eventuali FK aggiuntive future non CASCADE: messaggio parlante.
            map_integrity_error(
                exc,
                fallback_code=E_COLONNA_IN_USE,
                fallback_message=(
                    "La colonna e' in uso. Rimuovere i riferimenti oppure disattivarla."
                ),
                context={"colonna_id": colonna_id},
            )
        ErrorManager.require(
            deleted,
            code=E_COLONNA_NOT_FOUND,
            message="Colonna lista non trovata.",
            detail=f"colonna_id={colonna_id}",
        )
        return {"deleted": True, "id": colonna_id}

    # =================================================================
    # Helpers privati - validazione payload
    # =================================================================

    # Scopo: Normalizza il payload create. Applica defaults applicativi
    #        e forza il vincolo CHECK azione_non_esportabile lato BE
    #        (decisione 6 _def.md).
    def _build_create_data(
        self,
        lista_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"lista_id": lista_id}
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["etichetta"] = self._v.require_string(
            payload, "etichetta", max_len=_MAX_ETICHETTA_LEN
        )
        data["etichetta_estesa"] = self._v.optional_string(
            payload, "etichetta_estesa", max_len=_MAX_ETICHETTA_ESTESA_LEN
        )
        data["etichetta_i18n_key"] = self._v.optional_string(
            payload, "etichetta_i18n_key", max_len=_MAX_I18N_KEY_LEN
        )
        data["campo_sorgente"] = self._v.optional_string(
            payload, "campo_sorgente", max_len=_MAX_CAMPO_SORGENTE_LEN
        )

        tipo_colonna = self._v.require_string(payload, "tipo_colonna")
        ErrorManager.require(
            tipo_colonna in _TIPI_COLONNA,
            code=E_COLONNA_VALIDATION,
            message="Valore 'tipo_colonna' non ammesso.",
            detail=f"valore='{tipo_colonna}', ammessi={sorted(_TIPI_COLONNA)!r}",
        )
        data["tipo_colonna"] = tipo_colonna

        tipo_dato = self._v.require_string(payload, "tipo_dato")
        ErrorManager.require(
            tipo_dato in _TIPI_DATO,
            code=E_COLONNA_VALIDATION,
            message="Valore 'tipo_dato' non ammesso.",
            detail=f"valore='{tipo_dato}', ammessi={sorted(_TIPI_DATO)!r}",
        )
        data["tipo_dato"] = tipo_dato

        data["formato"] = self._v.optional_string(
            payload, "formato", max_len=_MAX_FORMATO_LEN
        )
        data["larghezza_default"] = self._bounded_optional_int(
            payload, "larghezza_default", max_value=_MAX_LARGHEZZA
        )

        ordine = self._v.require_positive_int(payload, "ordine_default")
        ErrorManager.require(
            ordine <= _MAX_ORDINE,
            code=E_COLONNA_VALIDATION,
            message="Campo 'ordine_default' fuori range.",
            detail=f"max={_MAX_ORDINE}",
        )
        data["ordine_default"] = ordine

        allineamento = (
            self._v.require_string(payload, "allineamento")
            if "allineamento" in payload
            else "left"
        )
        ErrorManager.require(
            allineamento in _ALLINEAMENTI,
            code=E_COLONNA_VALIDATION,
            message="Valore 'allineamento' non ammesso.",
            detail=(
                f"valore='{allineamento}', ammessi={sorted(_ALLINEAMENTI)!r}"
            ),
        )
        data["allineamento"] = allineamento

        data["gruppo"] = self._v.optional_string(
            payload, "gruppo", max_len=_MAX_GRUPPO_LEN
        )
        data["gruppo_ordine"] = self._bounded_optional_int(
            payload, "gruppo_ordine", max_value=_MAX_ORDINE
        )

        for flag, default in (
            ("filtrabile", True),
            ("ordinabile", True),
            ("esportabile", True),
            ("ricercabile_full", False),
            ("sensibile", False),
            ("attivo", True),
        ):
            value = self._v.optional_bool(payload, flag)
            data[flag] = bool(value) if value is not None else default

        # Vincolo CHECK applicato lato BE (decisione 6 _def.md): le
        # colonne di tipo 'azione' non possono essere esportabili. Se
        # l'utente passa esportabile=True esplicitamente, lo
        # silenziamo per coerenza UX (no errore tardivo dal DB).
        if data["tipo_colonna"] == "azione":
            data["esportabile"] = False

        return data

    # Scopo: Normalizza il payload update sui soli campi presenti.
    #        Quando cambia tipo_colonna verso 'azione' applichiamo la
    #        normalizzazione esportabile=False anche se non e' nel
    #        payload (decisione 6).
    def _build_update_data(
        self,
        payload: dict[str, Any],
        *,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "codice" in payload:
            data["codice"] = self._v.require_string(
                payload, "codice", max_len=_MAX_CODICE_LEN
            )
        if "etichetta" in payload:
            data["etichetta"] = self._v.require_string(
                payload, "etichetta", max_len=_MAX_ETICHETTA_LEN
            )
        if "etichetta_estesa" in payload:
            data["etichetta_estesa"] = self._v.optional_string(
                payload, "etichetta_estesa", max_len=_MAX_ETICHETTA_ESTESA_LEN
            )
        if "etichetta_i18n_key" in payload:
            data["etichetta_i18n_key"] = self._v.optional_string(
                payload, "etichetta_i18n_key", max_len=_MAX_I18N_KEY_LEN
            )
        if "campo_sorgente" in payload:
            data["campo_sorgente"] = self._v.optional_string(
                payload, "campo_sorgente", max_len=_MAX_CAMPO_SORGENTE_LEN
            )
        if "tipo_colonna" in payload:
            value = self._v.require_string(payload, "tipo_colonna")
            ErrorManager.require(
                value in _TIPI_COLONNA,
                code=E_COLONNA_VALIDATION,
                message="Valore 'tipo_colonna' non ammesso.",
                detail=f"valore='{value}', ammessi={sorted(_TIPI_COLONNA)!r}",
            )
            data["tipo_colonna"] = value
        if "tipo_dato" in payload:
            value = self._v.require_string(payload, "tipo_dato")
            ErrorManager.require(
                value in _TIPI_DATO,
                code=E_COLONNA_VALIDATION,
                message="Valore 'tipo_dato' non ammesso.",
                detail=f"valore='{value}', ammessi={sorted(_TIPI_DATO)!r}",
            )
            data["tipo_dato"] = value
        if "formato" in payload:
            data["formato"] = self._v.optional_string(
                payload, "formato", max_len=_MAX_FORMATO_LEN
            )
        if "larghezza_default" in payload:
            data["larghezza_default"] = self._bounded_optional_int(
                payload, "larghezza_default", max_value=_MAX_LARGHEZZA
            )
        if "ordine_default" in payload:
            ordine = self._v.require_positive_int(payload, "ordine_default")
            ErrorManager.require(
                ordine <= _MAX_ORDINE,
                code=E_COLONNA_VALIDATION,
                message="Campo 'ordine_default' fuori range.",
                detail=f"max={_MAX_ORDINE}",
            )
            data["ordine_default"] = ordine
        if "allineamento" in payload:
            value = self._v.require_string(payload, "allineamento")
            ErrorManager.require(
                value in _ALLINEAMENTI,
                code=E_COLONNA_VALIDATION,
                message="Valore 'allineamento' non ammesso.",
                detail=(
                    f"valore='{value}', ammessi={sorted(_ALLINEAMENTI)!r}"
                ),
            )
            data["allineamento"] = value
        if "gruppo" in payload:
            data["gruppo"] = self._v.optional_string(
                payload, "gruppo", max_len=_MAX_GRUPPO_LEN
            )
        if "gruppo_ordine" in payload:
            data["gruppo_ordine"] = self._bounded_optional_int(
                payload, "gruppo_ordine", max_value=_MAX_ORDINE
            )

        for flag in (
            "filtrabile", "ordinabile", "esportabile",
            "ricercabile_full", "sensibile", "attivo",
        ):
            if flag in payload:
                valore_flag = self._v.optional_bool(payload, flag)
                ErrorManager.require(
                    valore_flag is not None,
                    code=E_COLONNA_VALIDATION,
                    message=f"Il campo '{flag}' non puo' essere NULL.",
                    detail=f"field={flag}",
                )
                data[flag] = bool(valore_flag)

        # Normalize esportabile su tipo_colonna='azione': considera il
        # tipo_colonna nuovo (se presente nel payload) o quello corrente.
        # ⚠️ Solo se il client ha chiesto qualcosa: il valore DERIVATO non e' un
        #    campo, e con `{}` faceva passare il controllo del PATCH vuoto e
        #    scriveva `data_update` (2026-10-20, brief-be-verifica-
        #    documentazione-api §A2).
        tipo_colonna_finale = data.get("tipo_colonna", current["tipo_colonna"])
        if tipo_colonna_finale == "azione" and data:
            data["esportabile"] = False

        return data

    # Scopo: Estrae intero positivo opzionale + bound check su valore
    #        massimo. Per campi come `larghezza_default` e `gruppo_ordine`
    #        dove un valore fuori scala segnala un errore di copia/incolla
    #        piu' che un caso d'uso reale.
    def _bounded_optional_int(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        max_value: int,
    ) -> int | None:
        value = self._v.optional_positive_int(payload, key)
        if value is None:
            return None
        ErrorManager.require(
            value <= max_value,
            code=E_COLONNA_VALIDATION,
            message=f"Campo '{key}' fuori range.",
            detail=f"max={max_value}",
        )
        return value
