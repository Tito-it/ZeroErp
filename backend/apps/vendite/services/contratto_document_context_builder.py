# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente CONTRATTO. Compone il dizionario di contesto consumato
#        dal template HTML del motore documentale.
#
#        Confine v1:
#         - il builder NON applica scope/permessi: la responsabilita' e'
#           del caller (orchestrator + view di dominio);
#         - per i contratti in modalita' A/B le righe stampabili arrivano
#           dalla preview listino+override, cosi' il documento mostra le
#           condizioni effettive anche quando `contratti_righe` contiene
#           solo override mirati;
#         - per la modalita' C le righe stampabili sono `contratti_righe`.
# ------------------------------------------------------------

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._date_formatting import (
    format_date_it,
    format_date_iso,
)
from apps.documenti.services.context_builders.base import (
    DocumentContextBuilder,
)
from apps.documenti.services.context_builders.registry import register_builder
from apps.vendite.db.contratti_repository import ContrattiRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class ContrattoDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti CONTRATTO."""

    CODE = "CONTRATTO"

    # Scopo: Iniezione opzionale del repository per testabilita' mock-only.
    def __init__(self, repo: ContrattiRepository | None = None) -> None:
        self._repo = repo or ContrattiRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id del contratto.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_contratto` (None -> NOT_FOUND);
    #         3. righe contratto + utility snapshot;
    #         4. righe documentali: preview listino per modalita' A/B,
    #            righe contratto native per modalita' C;
    #         5. compone shape stabile (versione 1) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = self._repo.get_contratto(sorgente_id)
        ErrorManager.require(
            testata is not None,
            code=E_NOT_FOUND,
            message="Contratto non trovato per generazione documento.",
            detail=f"contratto_id={sorgente_id}",
        )
        assert testata is not None

        righe_contratto = self._repo.list_righe(sorgente_id)
        utility = self._repo.get_utility(sorgente_id)
        righe_preview = (
            self._repo.list_righe_preview(sorgente_id)
            if testata.get("listino_id") is not None
            else []
        )
        righe_documento = self._shape_righe(righe_preview or righe_contratto)

        return {
            "contratto": self._shape_contratto(testata),
            "cliente": self._shape_cliente(testata),
            "utility": utility,
            "righe": righe_documento,
            "righe_contratto": self._shape_righe(righe_contratto),
            "righe_preview": self._shape_righe(righe_preview),
            # `_meta` qui e' una sezione del context, non
            # `documenti_generati.meta`. Deve restare deterministica:
            # niente timestamp/random; la data generazione vive nel DB.
            "_meta": {
                "locale": locale,
                "auth_user_id": auth_user_id,
                "context_version": 1,
                "context_code": self.CODE,
                "righe_source": (
                    "PREVIEW_LISTINO"
                    if righe_preview
                    else "CONTRATTI_RIGHE"
                ),
            },
        }

    # =================================================================
    # Helpers privati di shaping
    # =================================================================

    # Scopo: Estrae il sotto-dict "contratto" stabile dalla testata.
    #        La repository ritorna gia' campi denormalizzati; qui li
    #        raggruppiamo per rendere il template HTML leggibile.
    def _shape_contratto(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "valido_dal": format_date_it(testata.get("valido_dal")),
            "valido_dal_iso": format_date_iso(testata.get("valido_dal")),
            "valido_al": format_date_it(testata.get("valido_al")),
            "valido_al_iso": format_date_iso(testata.get("valido_al")),
            "ambito": testata.get("ambito"),
            "parent_contratto_id": testata.get("parent_contratto_id"),
            "stato": {
                "id": testata.get("stato_doc_contratto_id"),
                "codice": testata.get("stato_codice"),
                "codice_interno": testata.get("stato_codice"),
                "descrizione": testata.get("stato_descrizione"),
            },
            "utility": {
                "id": testata.get("utility_id"),
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            "listino": {
                "id": testata.get("listino_id"),
                "codice": testata.get("listino_codice"),
                "descrizione": testata.get("listino_descrizione"),
            },
            "pricing": {
                "modalita": self._resolve_modalita(testata),
                "tipo_variazione_globale": testata.get("tipo_variazione_globale"),
                "valore_variazione_globale": testata.get("valore_variazione_globale"),
            },
            "categoria_cliente_snapshot": {
                "id": testata.get("categoria_cliente_id_snapshot"),
                "codice": testata.get("categoria_cliente_snapshot_codice"),
                "descrizione": testata.get("categoria_cliente_snapshot_descrizione"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" minimo, allineato al builder preventivo.
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "billing_account_id": testata.get("billing_account_id"),
            "billing_account_codice": testata.get("ba_codice"),
            "denominazione": testata.get("ba_ragione_sociale"),
        }

    # Scopo: Deriva la modalita' pricing leggibile dal dato contrattuale.
    #        A = listino con variazione globale, B = listino con override,
    #        C = nessun listino, righe tutte negoziate.
    def _resolve_modalita(self, testata: dict[str, Any]) -> str:
        if testata.get("listino_id") is None:
            return "C"
        if testata.get("tipo_variazione_globale") is not None:
            return "A"
        return "B"

    def _shape_righe(self, righe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        shaped: list[dict[str, Any]] = []
        for riga in righe:
            r = dict(riga)
            for field in ("prezzo_finale", "prezzo_unitario", "override_prezzo"):
                if field in r:
                    r[field] = _format_decimal_6(r.get(field))
            shaped.append(r)
        return shaped


def _format_decimal_6(value: Any) -> str | None:
    if value is None:
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    return f"{dec:.6f}"


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry centrale.
register_builder(ContrattoDocumentContextBuilder())
