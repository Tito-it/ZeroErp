# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per `ui.lista_definizione`.
#
#        Fase 1 (read-only, helper composizione preset):
#          - list_definizioni()        — lista per Select header
#                                         "Lista corrente"
#          - list_colonne_lista(id)    — catalogo colonne grezzo (no
#                                         filtro permessi: amministrazione)
#
#        Fase 2 — DEF-5b (CRUD SUPER_ADMIN):
#          - list_definizioni_admin()  — lista completa (include disattivate)
#          - get_definizione(id)       — dettaglio singolo
#          - create_definizione(...)   — INSERT + validazione payload
#          - update_definizione(...)   — PATCH campi mutabili
#          - delete_definizione(id)    — DELETE con mapping RESTRICT FK
#
#        Validazione payload via PayloadValidator + map_integrity_error
#        per UNIQUE codice / FK RESTRICT (in uso) / trigger guard
#        E_UI_VISTA_SQL_NON_TROVATA. Il workflow draft (creare con
#        attivo=false, attivare dopo aver creato la view) e' supportato
#        nativamente dal trigger DB: nessun relax richiesto.
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
E_DEFINIZIONE_VALIDATION = "E_UI_DEFINIZIONE_VALIDAZIONE"
E_DEFINIZIONE_NOT_FOUND = "E_UI_DEFINIZIONE_NON_TROVATA"
E_DEFINIZIONE_IN_USE = "E_UI_DEFINIZIONE_IN_USO"

# Whitelist chiavi del payload create. Tutti i campi sono opzionali
# tranne i tre obbligatori (codice/descrizione/schema_dati): vista_sql
# e note possono essere NULL, attivo default TRUE applicativo.
#
# 🚫 `multi_emittente` NON entra qui, e NON e' una dimenticanza.
#    E' un flag che dichiara una CAPACITA' DEL SOFTWARE — «questa lista sa
#    dire da quale emittente arriva ogni riga» — non una preferenza di chi
#    amministra: si accende SOLO dal seed (`80_data/.../lista_definizione.csv`),
#    insieme (o dopo) al lavoro che la rende vera, cioe' la colonna emittente
#    a catalogo. Un interruttore in interfaccia lo trasformerebbe da registro
#    di debito che cala in elenco di eccezioni che cresce.
#    Presidiato su tre strati: il TRIGGER DB
#    (`ui.trgfn_lista_definizione_guard_multi_emittente`, che rifiuta la
#    scrittura da qualunque ruolo non proprietario → `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE`),
#    il test `ListaDefinizioneMultiEmittenteFuoriScritturaTests` (che presidia
#    TUTTI e quattro i punti di questo file e del repository che elencano
#    campi scrivibili, non la sola whitelist), e questo commento.
#    Decisione Tid 2026-08-17 · brief-db-perimetro-emittente-liste-e-gerarchia-ba
#    §7 decisione 3, Q1, §11.5.
CREATE_KEYS: frozenset[str] = frozenset(
    {
        "codice",
        "descrizione",
        "schema_dati",
        "vista_sql",
        "note",
        "attivo",
    }
)

# Whitelist chiavi del payload update. Comprende anche `codice`: la
# UNIQUE constraint DB intercetta i conflitti (mappata via
# map_integrity_error). `schema_dati` ammesso in update perche' la
# tabella non ha trigger di immutabilita'.
UPDATE_KEYS: frozenset[str] = CREATE_KEYS

_MAX_CODICE_LEN = 80
_MAX_DESCRIZIONE_LEN = 200
_MAX_SCHEMA_DATI_LEN = 80
_MAX_VISTA_SQL_LEN = 120
_MAX_NOTE_LEN = 4000

# Mapping vincoli DB -> codice + messaggio applicativo. Allineato a
# 20260506-02 (UNIQUE codice) e alle FK con RESTRICT default sulle
# tabelle che referenziano lista_definizione (lista_colonna,
# lista_preset, lista_preferenza_utente).
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_ui_lista_definizione_codice": (
        E_DEFINIZIONE_VALIDATION,
        "Esiste gia' una definizione con questo codice.",
        "codice",
    ),
}

# FK RESTRICT (NO ACTION default): la cancellazione fallisce se ci
# sono righe figlie. La tabella padre e' lista_definizione, quindi
# l'errore e' "in uso" -> 409.
_FK_RESTRICT_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_lista_colonna_lista_definizione": (
        E_DEFINIZIONE_IN_USE,
        "Definizione in uso da colonne del catalogo: rimuovere prima le colonne.",
    ),
    "fk_lista_preset_lista_definizione": (
        E_DEFINIZIONE_IN_USE,
        "Definizione in uso da preset: rimuovere prima i preset.",
    ),
    "fk_lista_preferenza_utente_lista_definizione": (
        E_DEFINIZIONE_IN_USE,
        "Definizione in uso da preferenze utente: rimuoverle prima oppure disattivare la lista.",
    ),
}


class ListaDefinizioneAdminService:
    """Facade gestione lista_definizione (read Fase 1 + CRUD Fase 2)."""

    def __init__(self, repo: UiAdminRepository | None = None) -> None:
        self._repo = repo or UiAdminRepository()
        self._v = PayloadValidator(validation_code=E_DEFINIZIONE_VALIDATION)

    # =================================================================
    # Read - Fase 1 (helper composizione preset)
    # =================================================================

    # Scopo: Lista delle definizioni di lista attive. Pre-popola il
    #        Select "Lista corrente" della pagina admin Fase 1.
    def list_definizioni(self) -> list[dict[str, Any]]:
        return self._repo.list_definizioni()

    # Scopo: Catalogo colonne grezzo di una lista (no filtro permessi:
    #        amministrazione tecnica). 404 se la lista non esiste o non
    #        e' attiva.
    def list_colonne_lista(self, lista_id: int) -> list[dict[str, Any]]:
        ErrorManager.require(
            self._repo.get_definizione(lista_id) is not None,
            code=E_LISTA_NOT_FOUND,
            message="Lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return self._repo.list_colonne_by_lista(lista_id)

    # =================================================================
    # Read - Fase 2 (pagina tecnica SUPER_ADMIN)
    # =================================================================

    # Scopo: Lista completa definizioni (include disattivate) per la
    #        pagina tecnica `/amm-software/personalizzazioni-liste-tecniche`,
    #        con il conteggio totale accanto alle righe.
    # ⭐ Forma `{results, count}` — la variante offset-based gia' documentata in
    #    `api.md` §Paginazione. Qui non c'e' paginazione: il `count` non serve a
    #    impaginare, serve a DICHIARARE quante righe esistono, in modo che il
    #    client possa verificare di averle tutte invece di assumerlo.
    # ⛔ `count` viene da una query SUA (`count_definizioni_admin`), non da
    #    `len(results)`: derivarlo dalle righe sposterebbe la tautologia dal
    #    frontend al backend senza toglierla.
    def list_definizioni_admin(self) -> dict[str, Any]:
        return {
            "results": self._repo.list_definizioni_admin(),
            "count": self._repo.count_definizioni_admin(),
        }

    # Scopo: Dettaglio singolo per id (campi completi, anche disattivate).
    #        404 se id inesistente. Usato post-create/post-update e dal
    #        master-detail per popolare il drawer.
    def get_definizione(self, lista_id: int) -> dict[str, Any]:
        result = testata_o_not_found(
            self._repo.get_definizione_admin, lista_id,
            code=E_DEFINIZIONE_NOT_FOUND, message="Definizione lista non trovata.",
            id_name="lista_id", function_name="lista_definizione_admin_service.get_definizione",
        )
        return result

    # =================================================================
    # Create / Update / Delete - Fase 2
    # =================================================================

    # Scopo: Crea una nuova definizione. Valida payload, applica defaults
    #        applicativi e mappa eventuali violazioni unique/FK/trigger.
    #        Il trigger DB E_UI_VISTA_SQL_NON_TROVATA passa attraverso
    #        come errore parlante senza ulteriori traduzioni.
    def create_definizione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload,
            allowed=CREATE_KEYS,
            message="Payload definizione lista non valido.",
        )
        data = self._build_create_data(payload)

        try:
            new_id = self._repo.create_definizione(
                data, user_insert=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_DEFINIZIONE_VALIDATION,
                fallback_message="Violazione vincolo DB su definizione lista.",
                context={
                    "codice": data.get("codice"),
                },
            )
        return self.get_definizione(new_id)

    # Scopo: Aggiorna definizione sui soli campi presenti nel payload.
    #        Tutti i campi ESPOSTI sono mutabili (nessun immutabile per
    #        design): cambiare `vista_sql` su lista esistente passa per il
    #        trigger guard come per la create.
    # ⚠️ «Tutti» si riferisce ai sei della whitelist, e c'e' UNA colonna della
    #        tabella deliberatamente fuori: `multi_emittente`. Non e' un campo
    #        che questo service ha dimenticato di esporre — e' l'unica
    #        eccezione a questa frase, e il perche' e' scritto accanto a
    #        `CREATE_KEYS`. Chi riallinea le whitelist «per coerenza» legga
    #        prima quello.
    def update_definizione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        lista_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(lista_id, field="lista_id")
        # 404 unificato: legge il dettaglio per validare l'id.
        self.get_definizione(lista_id)

        self._v.validate_allowed_keys(
            payload,
            allowed=UPDATE_KEYS,
            message="Payload definizione lista non valido.",
        )
        data = self._build_update_data(payload)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_definizione(
                lista_id, data, user_update=user_label(user)
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_DEFINIZIONE_VALIDATION,
                fallback_message="Violazione vincolo DB su definizione lista.",
                context={"lista_id": lista_id},
            )
        ErrorManager.require(
            updated,
            code=E_DEFINIZIONE_NOT_FOUND,
            message="Definizione lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return self.get_definizione(lista_id)

    # Scopo: Cancella definizione. Le FK RESTRICT su lista_colonna,
    #        lista_preset e lista_preferenza_utente bloccano la DELETE
    #        nativamente: l'errore IntegrityError viene mappato a
    #        E_UI_DEFINIZIONE_IN_USO con messaggio parlante. Soft-disable
    #        via PATCH attivo=false e' l'alternativa raccomandata.
    def delete_definizione(self, lista_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(lista_id, field="lista_id")
        # 404 unificato: assicura che l'id esista prima di tentare DELETE.
        self.get_definizione(lista_id)

        try:
            deleted = self._repo.delete_definizione(lista_id)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                fk_constraints=_FK_RESTRICT_CONSTRAINTS,
                fallback_code=E_DEFINIZIONE_IN_USE,
                fallback_message=(
                    "Definizione in uso: rimuovere i riferimenti oppure disattivarla."
                ),
                context={"lista_id": lista_id},
            )
        ErrorManager.require(
            deleted,
            code=E_DEFINIZIONE_NOT_FOUND,
            message="Definizione lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return {"deleted": True, "id": lista_id}

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Normalizza il payload create. Applica default applicativo
    #        attivo=True. Tutti i campi opzionali vista_sql/note vengono
    #        accettati come stringa vuota -> NULL (pattern null_vs_empty).
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["descrizione"] = self._v.require_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
        )
        data["schema_dati"] = self._v.require_string(
            payload, "schema_dati", max_len=_MAX_SCHEMA_DATI_LEN
        )
        data["vista_sql"] = self._v.optional_string(
            payload, "vista_sql", max_len=_MAX_VISTA_SQL_LEN
        )
        data["note"] = self._v.optional_string(
            payload, "note", max_len=_MAX_NOTE_LEN
        )

        attivo = self._v.optional_bool(payload, "attivo")
        data["attivo"] = bool(attivo) if attivo is not None else True

        return data

    # Scopo: Normalizza il payload update sui soli campi presenti. Le
    #        chiavi assenti non finiscono nel data => l'UPDATE preserva
    #        il valore corrente.
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
        if "schema_dati" in payload:
            data["schema_dati"] = self._v.require_string(
                payload, "schema_dati", max_len=_MAX_SCHEMA_DATI_LEN
            )
        if "vista_sql" in payload:
            data["vista_sql"] = self._v.optional_string(
                payload, "vista_sql", max_len=_MAX_VISTA_SQL_LEN
            )
        if "note" in payload:
            data["note"] = self._v.optional_string(
                payload, "note", max_len=_MAX_NOTE_LEN
            )
        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                value is not None,
                code=E_DEFINIZIONE_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            data["attivo"] = bool(value)
        return data
