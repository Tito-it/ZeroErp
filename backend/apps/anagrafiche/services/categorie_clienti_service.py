# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per anagrafiche.categorie_clienti.
#        CRUD con validazione payload, normalizzazione campi opzionali,
#        mapping IntegrityError (UNIQUE codice) su codici errore parlanti.
#        Riferimento: sviluppo-listini-v5 §4.1 (la categoria e' contenitore
#        commerciale: la politica di pricing vive altrove, qui solo anagrafica).
#        Helper payload delegati a apps.core.services.payload_helpers
#        (V6-B1, sviluppo-listini-v6 §2.2).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.api.constants import DEFAULT_LIMIT
from apps.anagrafiche.db.categorie_clienti_repository import (
    _ORDER_COLS,
    CategorieClientiRepository,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)


# Codici errore (registrati in apps/core/services/error_policies.py)
E_ANAG_VALIDAZIONE = "E_ANAG_VALIDAZIONE"
E_ANAG_DUPLICATO = "E_ANAG_DUPLICATO"
E_ANAG_NOT_FOUND = "E_ANAG_NOT_FOUND"

# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS`), unica fonte di verita' —
# stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Era una copia a
# mano: su offerte la stessa copia aveva gia' divergito in entrambi i versi.
_ORDER_BY_VALIDI: frozenset[str] = frozenset(_ORDER_COLS)

# Chiavi ammesse in payload create (anagrafica completa).
_CREATE_KEYS: frozenset[str] = frozenset({
    "codice",
    "descrizione",
    "partecipa_promo",
    "ordinamento",
    "meta",
    "attivo",
})

# Chiavi ammesse in payload update: `codice` e' immutabile (vincolo progetto:
# il codice e' identificatore business che non si rinomina, coerentemente con
# listini, articoli e altre anagrafiche).
_UPDATE_KEYS: frozenset[str] = frozenset({
    "descrizione",
    "partecipa_promo",
    "ordinamento",
    "meta",
    "attivo",
})


# Limite di lunghezza descrittivo; il DB ha varchar senza bound esplicito ma
# il contratto UI resta ragionevole.
_MAX_CODICE_LEN = 32
_MAX_DESCRIZIONE_LEN = 255


# Mapping vincoli DB -> codici errore applicativi.
_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    "uq_categorie_clienti_codice": (
        E_ANAG_DUPLICATO,
        "Esiste gia' una categoria cliente con questo codice.",
        "codice",
    ),
}


class CategorieClientiService:
    """Service admin per anagrafiche.categorie_clienti."""

    def __init__(self) -> None:
        self._repo = CategorieClientiRepository()
        # Validator condiviso per tutti i payload di questo service.
        self._v = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata con validazione order_by.
    def list_categorie(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        partecipa_promo: bool | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "ordinamento",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_VALIDI, order_dir=order_dir)
        return self._repo.list_categorie(
            search=search,
            attivo=attivo,
            partecipa_promo=partecipa_promo,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

    # Scopo: Dettaglio singola categoria; solleva not found se assente.
    def get_categoria(self, record_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        result = testata_o_not_found(
            self._repo.get_categoria, record_id,
            code=E_ANAG_NOT_FOUND, message="Categoria cliente non trovata.",
            id_name="record_id", function_name="categorie_clienti_service.get_categoria",
        )
        return result

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova categoria cliente. codice e descrizione obbligatori,
    #        altri campi opzionali con default DB.
    def create_categoria(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload,
            allowed=_CREATE_KEYS,
            message="Payload categoria cliente non valido.",
        )
        data = self._build_create_data(payload)

        try:
            new_id = self._repo.create_categoria(data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_ANAG_VALIDAZIONE,
                fallback_message="Violazione vincolo DB su categoria cliente.",
                # Il campo da accendere nel form NON sta qui: lo porta la mappa
                # dei vincoli (terzo elemento della tupla), perche' dipende da
                # QUALE vincolo ha fatto match e non dalla chiamata.
                context={"codice": data.get("codice")},
            )
        return self.get_categoria(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una categoria sui soli campi modificabili. codice
    #        immutabile: tentativo rifiutato con VALIDAZIONE.
    def update_categoria(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        # codice immutabile: rifiuta prima di qualsiasi altra validazione.
        if "codice" in payload:
            ErrorManager.raise_error(
                code=E_ANAG_VALIDAZIONE,
                message="Il codice della categoria e' immutabile.",
                detail="Per rinominare una categoria disattivare la vecchia e crearne una nuova.",
                context={"record_id": record_id},
            )
        self._v.validate_allowed_keys(
            payload,
            allowed=_UPDATE_KEYS,
            message="Payload categoria cliente non valido.",
        )
        data = self._build_update_data(payload)

        self._v.require_campi_da_aggiornare(
            data,
            context={"allowed_keys": sorted(_UPDATE_KEYS)},
        )

        try:
            updated = self._repo.update_categoria(record_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_ANAG_VALIDAZIONE,
                fallback_message="Violazione vincolo DB su categoria cliente.",
                context={"record_id": record_id},
            )
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Categoria cliente non trovata.",
            context={"record_id": record_id},
        )
        return self.get_categoria(record_id)

    # =================================================================
    # Helpers privati — composizione dict per repository
    # =================================================================

    # Scopo: Compone il dict da passare al repository per create, validando
    #        ogni campo. codice e descrizione obbligatori; flag/ordinamento/meta
    #        opzionali con default DB quando non presenti.
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["descrizione"] = self._v.require_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
        )
        partecipa = self._v.optional_bool(payload, "partecipa_promo")
        if partecipa is not None:
            data["partecipa_promo"] = partecipa
        ordinamento = self._v.optional_smallint(payload, "ordinamento")
        if ordinamento is not None:
            data["ordinamento"] = ordinamento
        attivo = self._v.optional_bool(payload, "attivo")
        if attivo is not None:
            data["attivo"] = attivo
        meta = self._v.optional_meta(payload)
        if meta is not None:
            data["meta"] = meta
        return data

    # Scopo: Compone il dict per update ignorando chiavi assenti.
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "descrizione" in payload:
            data["descrizione"] = self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
            )
        if "partecipa_promo" in payload:
            value = self._v.optional_bool(payload, "partecipa_promo")
            ErrorManager.require(
                value is not None,
                code=E_ANAG_VALIDAZIONE,
                message="Il campo 'partecipa_promo' non puo' essere NULL.",
                context={"field": "partecipa_promo"},
            )
            data["partecipa_promo"] = value
        if "ordinamento" in payload:
            ordinamento = self._v.optional_smallint(payload, "ordinamento")
            ErrorManager.require(
                ordinamento is not None,
                code=E_ANAG_VALIDAZIONE,
                message="Il campo 'ordinamento' non puo' essere NULL.",
                context={"field": "ordinamento"},
            )
            data["ordinamento"] = ordinamento
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
            # meta assente nel payload: non aggiorna; meta esplicitamente {}
            # (o dict valido) aggiorna.
            if meta is not None:
                data["meta"] = meta
        return data
