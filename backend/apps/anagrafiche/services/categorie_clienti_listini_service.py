# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per la matrice anagrafiche.categorie_clienti_listini.
#        Matrice pricing STADIO 2 del resolver v5: categoria x utility x
#        emittente x classe_utenza (opz) -> listino con variazione opzionale
#        (PERCENTUALE | VALORE_FISSO | NULL).
#
#        Validazione strict lato service:
#        - FK positive int (categoria, utility, emittente, listino)
#        - classe_utenza_id NULLABLE (sentinel fallback = NULL)
#        - tipo_variazione enum {PERCENTUALE|VALORE_FISSO} o NULL
#        - valore_variazione Decimal coerente con tipo_variazione
#        - valido_dal date obbligatoria, valido_al date opzionale (>= dal)
#
#        Vincoli DB (anticipati con messaggi parlanti dove possibile):
#        - ex_categ_cli_listini_no_overlap (EXCLUDE gist su quadrupla + range)
#        - chk_categ_cli_listini_variazione_coerente (tipo+valore entrambi
#          NULL o entrambi NOT NULL)
#        - chk_categ_cli_listini_valido_al_ge_dal
#
#        Riferimento: sviluppo-listini-v5 §4.2.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError

from apps.core.api.constants import DEFAULT_LIMIT
from apps.anagrafiche.db.categorie_clienti_listini_repository import (
    _ORDER_COLS,
    CategorieClientiListiniRepository,
)
from apps.anagrafiche.error_codes import (
    E_ANAG_FK,
    E_ANAG_MATRICE_OVERLAP,
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.non_editable_fields_helper import (
    compute_non_editable_fields,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)


# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS`), unica fonte di verita' —
# stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Era una copia a
# mano: su offerte la stessa copia aveva gia' divergito in entrambi i versi.
_ORDER_BY_VALIDI: frozenset[str] = frozenset(_ORDER_COLS)

# Chiavi ammesse in create: tutte le dimensioni + listino + variazione + date.
_CREATE_KEYS: frozenset[str] = frozenset({
    "categoria_cliente_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "classe_utenza_id",
    "listino_id",
    "tipo_variazione",
    "valore_variazione",
    "valido_dal",
    "valido_al",
    "meta",
    "attivo",
})

# Chiavi ammesse in update: le 4+1 dimensioni sono IMMUTABILI (la riga
# identifica semanticamente un match specifico categoria-utility-emittente-
# classe; cambiarle vorrebbe dire rimpiazzare la riga, operazione esplicita).
_UPDATE_KEYS: frozenset[str] = frozenset({
    "listino_id",
    "tipo_variazione",
    "valore_variazione",
    "valido_dal",
    "valido_al",
    "meta",
    "attivo",
})

# FK dimensionali immutabili — rifiutate in PATCH con messaggio esplicito.
_IMMUTABLE_DIMENSIONS: frozenset[str] = frozenset({
    "categoria_cliente_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "classe_utenza_id",
})

# Valori ammessi per tipo_variazione (coerenti con CHECK DB
# chk_categ_cli_listini_tipo_variazione).
_TIPI_VARIAZIONE: frozenset[str] = frozenset({"PERCENTUALE", "VALORE_FISSO"})

# Mappa codice -> (descrizione, ordering) per lookup statico tipo_variazione
# (Fase 4 — A7). Single source of truth lato Python: la tabella
# `config.tipi_variazione_categoria` non esiste, l'enum e' un CHECK constraint.
# Ordering "default-first" allineato a UX (PERCENTUALE caso piu' frequente).
_TIPI_VARIAZIONE_DESCRIZIONI: tuple[tuple[str, str, int], ...] = (
    ("PERCENTUALE", "Variazione percentuale (%)", 1),
    ("VALORE_FISSO", "Variazione a valore fisso", 2),
)

# Gap rispetto al registro DB `dbops.vw_non_editable_fields` (Fase 4).
# Le 4 dimensioni sono semanticamente immutabili (cambiare la quadrupla
# significa rimpiazzare la riga, non modificarla — vedi `_IMMUTABLE_DIMENSIONS`).
# Sono gia' rifiutate dal payload PATCH lato service, ma il FE consuma
# `non_editable_fields` per disabilitare i Select nel drawer di edit.
_NON_EDITABLE_GAPS: tuple[str, ...] = (
    "categoria_cliente_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "classe_utenza_id",
)

# Limiti numerici per valore_variazione. Il DB e' numeric(10,4) -> max
# |99999.9999|. Qui non restringiamo: lasciamo al DB il bound tecnico e
# al UX una validazione di range business (es. percentuali in [-100, +100]).
# valore_variazione e' Decimal ma accettiamo int/float/stringa numerica.


_MESSAGE = "Payload matrice categoria/listino non valido."


# Mapping vincoli DB -> codici errore applicativi.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    # L'EXCLUDE si manifesta come ExclusionViolation, di norma loggata dal
    # driver come "conflicting key value violates exclusion constraint".
    # Matchiamo il nome del vincolo per dare un messaggio esplicito.
    "ex_categ_cli_listini_no_overlap": (
        E_ANAG_MATRICE_OVERLAP,
        "Esiste gia' una riga attiva che si sovrappone per questa quadrupla "
        "(categoria, utility, emittente, classe utenza) nel periodo indicato.",
    ),
}

# ⭐ Il terzo elemento e' il CAMPO del form (chiave del payload, `_CREATE_KEYS`):
#    arriva al client in `error.fields` e accende il picker della FK violata
#    (presidio C2, brief-be-presidio-ui-action-e-canale-campi §3-ter).
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_categ_cli_listini_categoria": (
        E_ANAG_FK,
        "Categoria cliente inesistente.",
        "categoria_cliente_id",
    ),
    "fk_categ_cli_listini_utility": (
        E_ANAG_FK,
        "Utility inesistente.",
        "utility_id",
    ),
    "fk_categ_cli_listini_emittente": (
        E_ANAG_FK,
        "Emittente (soggetto_ruolo) inesistente.",
        "emittente_soggetto_ruolo_id",
    ),
    "fk_categ_cli_listini_classe_utenza": (
        E_ANAG_FK,
        "Classe utenza inesistente.",
        "classe_utenza_id",
    ),
    "fk_categ_cli_listini_listino": (
        E_ANAG_FK,
        "Listino inesistente.",
        "listino_id",
    ),
}


class CategorieClientiListiniService:
    """Service admin per la matrice categoria x listino (pricing STADIO 2)."""

    def __init__(self) -> None:
        self._repo = CategorieClientiListiniRepository()
        self._v = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice con filtri dimensionali + validita'.
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        categoria_cliente_id: int | None = None,
        utility_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        listino_id: int | None = None,
        valid_at: date | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "valido_dal",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_VALIDI, order_dir=order_dir)
        return self._repo.list_matrice(
            search=search,
            attivo=attivo,
            categoria_cliente_id=categoria_cliente_id,
            utility_id=utility_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            listino_id=listino_id,
            valid_at=valid_at,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

    # Scopo: Dettaglio singola riga matrice; solleva not found se assente.
    #        Arricchito con `non_editable_fields` (Fase 4 — A9): il FE
    #        usa la lista per disabilitare i Select dimensionali in edit.
    def get_matrice(self, record_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        result = testata_o_not_found(
            self._repo.get_matrice, record_id,
            code=E_ANAG_NOT_FOUND, message="Riga matrice categoria/listino non trovata.",
            id_name="record_id", function_name="categorie_clienti_listini_service.get_matrice",
        )
        result["non_editable_fields"] = self.get_non_editable_fields()
        return result

    # Scopo: Lookup statico dei tipi di variazione ammessi (Fase 4 — A7).
    #        Single source of truth in `_TIPI_VARIAZIONE_DESCRIZIONI`.
    #        Niente DB: enum tecnico fisso (CHECK constraint), 2 codici.
    #        L'invariante "descrizioni copre l'enum" e' garantita dal test
    #        `test_list_tipi_variazione_coverage` (CI), non a runtime.
    def list_tipi_variazione(self) -> list[dict[str, Any]]:
        return [
            {"codice": codice, "descrizione": descrizione, "ordering": ordering}
            for codice, descrizione, ordering in _TIPI_VARIAZIONE_DESCRIZIONI
        ]

    # Scopo: Lista `non_editable_fields` per la matrice (Fase 4 — A9).
    #        Le 4 dimensioni (categoria, utility, emittente, classe) sono
    #        semanticamente immutabili (vedi _IMMUTABLE_DIMENSIONS). Esposte
    #        come metadata via helper centrale (registro DB + gap dominio).
    def get_non_editable_fields(self) -> list[str]:
        return compute_non_editable_fields(
            "anagrafiche", "categorie_clienti_listini",
            gaps=_NON_EDITABLE_GAPS,
        )

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova riga matrice. Valida FK, enum variazione,
    #        coerenza tipo/valore, coerenza date. Mappa UNIQUE/FK/EXCLUDE
    #        su codici errore parlanti.
    def create_matrice(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS, message=_MESSAGE)
        data = self._build_create_data(payload)

        try:
            new_id = self._repo.create_matrice(data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_ANAG_VALIDAZIONE,
                fallback_message="Violazione vincolo DB su matrice categoria/listino.",
                context={
                    "categoria_cliente_id": data.get("categoria_cliente_id"),
                    "utility_id": data.get("utility_id"),
                    "emittente_soggetto_ruolo_id": data.get("emittente_soggetto_ruolo_id"),
                },
            )
        return self.get_matrice(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una riga matrice. Le 4+1 dimensioni sono immutabili:
    #        tentativo rifiutato con messaggio esplicito. Campi mutabili:
    #        listino, variazione (tipo+valore), validita, meta, attivo.
    def update_matrice(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        self._v.reject_keys(
            payload,
            forbidden=_IMMUTABLE_DIMENSIONS,
            reason="Le dimensioni della matrice sono immutabili.",
            detail_prefix=(
                "Per cambiare categoria/utility/emittente/classe_utenza, "
                "disattivare la riga corrente e crearne una nuova. Campi rifiutati"
            ),
            context_extra={"record_id": record_id},
        )
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS, message=_MESSAGE)
        data = self._build_update_data(payload)

        self._v.require_campi_da_aggiornare(
            data,
            context={"allowed_keys": sorted(_UPDATE_KEYS)},
        )

        try:
            updated = self._repo.update_matrice(record_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_ANAG_VALIDAZIONE,
                fallback_message="Violazione vincolo DB su matrice categoria/listino.",
                context={"record_id": record_id},
            )
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Riga matrice categoria/listino non trovata.",
            context={"record_id": record_id},
        )
        return self.get_matrice(record_id)

    # =================================================================
    # Helpers privati — composizione dict per repository
    # =================================================================

    # Scopo: Compone il dict per create validando ogni campo.
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {
            "categoria_cliente_id": self._v.require_positive_int(
                payload, "categoria_cliente_id"
            ),
            "utility_id": self._v.require_positive_int(payload, "utility_id"),
            "emittente_soggetto_ruolo_id": self._v.require_positive_int(
                payload, "emittente_soggetto_ruolo_id"
            ),
            "listino_id": self._v.require_positive_int(payload, "listino_id"),
            "valido_dal": self._v.require_date(payload, "valido_dal", message=_MESSAGE),
        }
        classe_utenza = self._v.optional_positive_int(payload, "classe_utenza_id")
        # classe_utenza_id sempre inviata al repo: None = fallback generico
        # (coerente con semantica "match valido per ogni classe").
        data["classe_utenza_id"] = classe_utenza

        valido_al = self._v.optional_date(payload, "valido_al", message=_MESSAGE)
        if "valido_al" in payload:
            data["valido_al"] = valido_al
        # L'ordine delle date (valido_al non precede valido_dal) lo giudica il
        # DB: guard comune `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL
        # col campo `valido_al` (dal 2026-09-23). Non si ripete qui.

        tipo, valore = self._extract_variazione_pair(payload)
        if tipo is not None or "tipo_variazione" in payload:
            data["tipo_variazione"] = tipo
        if valore is not None or "valore_variazione" in payload:
            data["valore_variazione"] = valore

        attivo = self._v.optional_bool(payload, "attivo")
        if attivo is not None:
            data["attivo"] = attivo
        meta = self._v.optional_meta(payload)
        if meta is not None:
            data["meta"] = meta
        return data

    # Scopo: Compone il dict per update ignorando chiavi assenti. Valida
    #        coerenza variazione quando almeno uno dei due campi arriva.
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "listino_id" in payload:
            data["listino_id"] = self._v.require_positive_int(payload, "listino_id")
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.require_date(
                payload, "valido_dal", message=_MESSAGE
            )
        if "valido_al" in payload:
            data["valido_al"] = self._v.optional_date(
                payload, "valido_al", message=_MESSAGE
            )
        # L'ordine delle date (valido_al non precede valido_dal) lo giudica il
        # DB: guard comune `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL
        # col campo `valido_al` (dal 2026-09-23). Non si ripete qui.

        if "tipo_variazione" in payload or "valore_variazione" in payload:
            tipo, valore = self._extract_variazione_pair(payload)
            data["tipo_variazione"] = tipo
            data["valore_variazione"] = valore

        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                value is not None,
                code=E_ANAG_VALIDAZIONE,
                message="Il campo 'attivo' non puo' essere NULL.",
                context={"field": "attivo"},
            )
            data["attivo"] = value
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — type coercion dominio-specifici
    # =================================================================

    # Scopo: Estrae e valida la coppia (tipo_variazione, valore_variazione)
    #        con coerenza semantica (entrambi NULL o entrambi valorizzati).
    #        Il DB ha il check equivalente: qui anticipiamo per UX.
    def _extract_variazione_pair(
        self, payload: dict[str, Any]
    ) -> tuple[str | None, Decimal | None]:
        # Estrazione tipo_variazione: None o codice del vocabolario — la lettura
        # e' del BB `PayloadValidator`, il vocabolario resta qui (specchio del
        # CHECK di `categorie_clienti_listini`: due valori, non i tre di promo).
        tipo = self._v.optional_enum(
            payload, "tipo_variazione", allowed=_TIPI_VARIAZIONE, message=_MESSAGE,
        )

        # Estrazione valore_variazione: None o Decimal — la coercizione (bool e
        # NaN rifiutati) e' del BB `PayloadValidator`.
        valore = self._v.optional_decimal(payload, "valore_variazione", message=_MESSAGE)

        # Coerenza: entrambi None o entrambi valorizzati.
        ErrorManager.require(
            (tipo is None) == (valore is None),
            code=E_ANAG_VALIDAZIONE,
            message=_MESSAGE,
            detail=(
                "tipo_variazione e valore_variazione devono essere entrambi "
                "valorizzati oppure entrambi nulli."
            ),
            context={"tipo_variazione": tipo, "valore_variazione": valore},
        )
        return tipo, valore
