# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#          - enum tipo_colonna / tipo_dato / allineamento / origine_campo
#            (drift risk con DB)
#          - lista_id e codice immutabili in update (codice dal giro 4 di
#            brief-db-revisione-ui, BE12: preferenze e preset cercano la
#            colonna per codice)
#          - i DEFAULT dei flag derivati dal modello, solo quando il client
#            non li manda (vedi `_build_create_data`)
#
#        Validazione lato DB (la regola sta li', il service la mappa sul campo):
#          - UNIQUE (lista_id, codice) -> map_integrity_error
#          - FK: lista_colonna_permesso ON DELETE CASCADE (i permessi
#            vanno con la colonna); lista_preset_colonna NO ACTION (una
#            colonna in un preset non si cancella, Q18 di
#            brief-db-revisione-ui) -> E_UI_COLONNA_IN_USO
#          - trigger guard valida_campo_sorgente -> E_UI_CAMPO_SORGENTE_NON_TROVATO,
#            E_UI_LINEAGE_NON_DICHIARATA (una colonna LINEAGE su una lista
#            che non dichiara `legge_lineage`)
#          - i CHECK del giro 4 (U24, U25, la lineage): un'azione non ha campo
#            sorgente; senza campo sorgente non si esporta; una colonna della
#            genealogia non si filtra, non si ordina e non si cerca.
#            ⛔ Il service non li ricopia piu' (fino al giro 4 forzava
#            `esportabile=False` sulle azioni, decisione 6 _def.md, quando la
#            regola era `chk_ui_lista_colonna_azione_non_esportabile`, ora
#            ritirato): un valore esplicito contrario e' un 400 sul campo.
#
#        Soft-block DELETE: prima del DELETE il service conta le preferenze
#        utente che nominano la colonna per codice nel JSONB
#        `configurazione->colonne`, poi i preset che la compongono, e blocca
#        con E_UI_COLONNA_IN_USO. Soft-disable via PATCH `attivo=false`
#        resta il gesto ordinario (decisione 5 _def.md).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.ui.db.ui_admin_repository import UiAdminRepository

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
# Enum `ui.origine_campo_lista` (giro 4, U26, Q15): da dove la colonna prende
# il dato, la relazione della lista o la genealogia dei documenti.
_ORIGINI_CAMPO: frozenset[str] = frozenset({"VISTA", "LINEAGE"})

# Whitelist chiavi payload create. lista_id arriva dal path della view.
CREATE_KEYS: frozenset[str] = frozenset(
    {
        "codice",
        "etichetta",
        "etichetta_estesa",
        "etichetta_i18n_key",
        "campo_sorgente",
        "origine_campo",
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

# Whitelist update: gli stessi campi, senza `codice` (immutabile dal giro 4,
# lucchetto DB `E_UI_COLONNA_CODICE_IMMUTABILE`). `lista_id` non c'e' comunque:
# arriva dal path.
UPDATE_KEYS: frozenset[str] = CREATE_KEYS - {"codice"}

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

# I CHECK del giro 4 di brief-db-revisione-ui, ognuno sul campo che lo
# risolve. `chk_ui_lista_colonna_azione_non_esportabile` e' ritirato: lo dicono
# gia' i primi due insieme (regola del 2, lato DB).
_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_ui_lista_colonna_azione_senza_campo": (
        E_COLONNA_VALIDATION,
        "Una colonna di tipo 'azione' non ha campo sorgente.",
        "campo_sorgente",
    ),
    "chk_ui_lista_colonna_senza_campo_non_esportabile": (
        E_COLONNA_VALIDATION,
        "Senza campo sorgente la colonna non si puo' esportare.",
        "esportabile",
    ),
    "chk_ui_lista_colonna_lineage_solo_mostrata": (
        E_COLONNA_VALIDATION,
        "Una colonna della genealogia dei documenti si mostra soltanto: "
        "non e' filtrabile, ordinabile ne' ricercabile.",
        "origine_campo",
    ),
    "chk_lista_colonna_campo_sorgente_non_vuoto": (
        E_COLONNA_VALIDATION,
        "Il campo sorgente, se indicato, non puo' essere vuoto.",
        "campo_sorgente",
    ),
}

# Il rifiuto della colonna che sta in un preset: lo dicono il controllo
# preventivo (coi codici dei preset) e la FK NO ACTION, se il preset nasce
# fra il controllo e il DELETE.
_MSG_COLONNA_IN_PRESET = (
    "La colonna fa parte di un preset. Toglila prima dai preset, oppure "
    "disattivala con attivo=false invece di eliminarla."
)


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
            new_id = self._repo.create_colonna(data)
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
        colonna_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(colonna_id, field="colonna_id")
        # 404 unificato prima di leggere il payload.
        self.get_colonna(colonna_id)

        # Reject espliciti per immutabili: dare messaggio parlante prima
        # della whitelist.
        for immutabile in ("lista_id", "codice"):
            if immutabile in payload:
                ErrorManager.raise_error(
                    code=E_COLONNA_VALIDATION,
                    message="Campo immutabile presente in payload update.",
                    detail=f"{immutabile} non aggiornabile",
                    fields=(immutabile,),
                )

        self._v.validate_allowed_keys(
            payload,
            allowed=UPDATE_KEYS,
            message="Payload colonna lista non valido.",
        )
        data = self._build_update_data(payload)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_colonna(colonna_id, data)
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

    # Scopo: Cancella colonna. Due soft-block prima del DELETE, ognuno col
    #        suo messaggio: le preferenze utente che nominano il `codice`
    #        nel JSONB configurazione->colonne (nessuna FK le protegge), e
    #        i preset che compongono la colonna (FK NO ACTION, Q18: il
    #        messaggio li nomina, perche' vanno tolti prima da li'). I
    #        permessi di colonna vanno a cascata e non fermano niente.
    #        ⚠️ Una colonna nata dal seed salta i due controlli: non si
    #        cancella comunque, e il rifiuto vero e' quello del DB
    #        (E_SEED_RIGA_NON_CANCELLABILE, trigger BEFORE DELETE, che a DB
    #        scatta prima della FK). Rimandare l'operatore a togliere la
    #        colonna dai preset, per farlo poi fermare dal seed, sarebbe
    #        un rimedio falso. Soft-disable via PATCH attivo=false.
    def delete_colonna(self, colonna_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(colonna_id, field="colonna_id")
        # 404 + serve il codice + lista_id per il count preferenze.
        current = self.get_colonna(colonna_id)

        if not current.get("nata_dal_seed"):
            self._richiedi_colonna_non_in_uso(colonna_id, current)

        try:
            deleted = self._repo.delete_colonna(colonna_id)
        except IntegrityError as exc:
            # La FK NO ACTION dei preset, se un preset e' nato fra il
            # controllo preventivo e il DELETE; il ripiego per FK future.
            # ⭐ Le FK dei preset verso la colonna sono DUE dal giro 2b di
            #    brief-db-revisione-ui (U14): quella sulla sola colonna e la
            #    composita (colonna, lista), entrambe NO ACTION. Quale delle
            #    due scatti per prima non e' un contratto: dicono la stessa
            #    cosa, e hanno lo stesso rifiuto.
            map_integrity_error(
                exc,
                fk_constraints={
                    "fk_lista_preset_colonna_lista_colonna": (
                        E_COLONNA_IN_USE, _MSG_COLONNA_IN_PRESET,
                    ),
                    "fk_ui_lista_preset_colonna_colonna_della_lista": (
                        E_COLONNA_IN_USE, _MSG_COLONNA_IN_PRESET,
                    ),
                },
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

    # Scopo: I due soft-block della cancellazione di una colonna, nell'ordine
    #        in cui l'operatore li risolve: le preferenze utente (che nessuna
    #        FK protegge), poi i preset che la compongono (FK NO ACTION).
    #        Ognuno solleva E_UI_COLONNA_IN_USO col suo messaggio; quello dei
    #        preset li nomina per codice.
    def _richiedi_colonna_non_in_uso(
        self, colonna_id: int, current: dict[str, Any],
    ) -> None:
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

        preset = self._repo.preset_con_colonna(colonna_id)
        ErrorManager.require(
            not preset,
            code=E_COLONNA_IN_USE,
            message=(
                f"{_MSG_COLONNA_IN_PRESET} Preset: {', '.join(preset)}."
            ),
            detail=(
                f"preset={preset!r}, lista_id={current['lista_id']}, "
                f"codice={current['codice']!r}"
            ),
            context={
                "colonna_id": colonna_id,
                "preset": preset,
            },
        )

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
        data["origine_campo"] = (
            self._origine_campo(payload) if "origine_campo" in payload else "VISTA"
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

        # ⭐ I DEFAULT seguono il modello, e valgono SOLO per il flag che il
        #    client non manda: una colonna senza dato non si esporta (U25),
        #    una della genealogia si mostra soltanto (CHECK della lineage).
        #    Non e' una copia della regola: un valore esplicito contrario
        #    arriva al DB, che lo rifiuta sul campo (`_CHECK_CONSTRAINTS`).
        ha_dato = data["campo_sorgente"] is not None
        della_vista = data["origine_campo"] != "LINEAGE"
        for flag, default in (
            ("filtrabile", della_vista),
            ("ordinabile", della_vista),
            ("esportabile", ha_dato),
            ("ricercabile_full", False),
            ("sensibile", False),
            ("attivo", True),
        ):
            value = self._v.optional_bool(payload, flag)
            data[flag] = bool(value) if value is not None else default

        return data

    # Scopo: Legge `origine_campo` contro l'enum `ui.origine_campo_lista`.
    def _origine_campo(self, payload: dict[str, Any]) -> str:
        value = self._v.require_string(payload, "origine_campo")
        ErrorManager.require(
            value in _ORIGINI_CAMPO,
            code=E_COLONNA_VALIDATION,
            message="Valore 'origine_campo' non ammesso.",
            detail=f"valore='{value}', ammessi={sorted(_ORIGINI_CAMPO)!r}",
        )
        return value

    # Scopo: Normalizza il payload update sui soli campi presenti. Nessun
    #        valore derivato: i vincoli fra campi (azione senza campo,
    #        senza campo non esportabile, genealogia solo mostrata) li
    #        giudica il DB, sul valore finale della riga.
    def _build_update_data(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
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
        if "origine_campo" in payload:
            data["origine_campo"] = self._origine_campo(payload)
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
