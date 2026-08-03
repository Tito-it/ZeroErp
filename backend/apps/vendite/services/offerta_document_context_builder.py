# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente OFFERTA_COMMERCIALE. Compone il dizionario di contesto
#        consumato dal template HTML del motore documentale.
#
#        L'offerta commerciale e' lo specchio strutturale del contratto
#        (testata con listino + variazione globale modalita' A/B/C +
#        utility 1:1), ma le "righe" del documento sono le **eccezioni**
#        negoziate (mirror di `contratti_righe`): OVERRIDE / ESCLUSIONE /
#        AGGIUNTA, eventualmente con componenti BoM.
#
#        Confine v1 (decisione 2026-05-27 con Tid):
#         - il documento mostra SOLO le eccezioni, non il listino effettivo
#           completo (a DB non esiste una preview listino offerta analoga a
#           `ContrattiRepository.list_righe_preview`); il listino base
#           resta una fase 2 (servira' una fn DB dedicata);
#         - il builder NON applica scope/permessi: responsabilita' del
#           caller (orchestrator + view di dominio con permessi vendite);
#         - il builder NON conosce il template HTML: fornisce solo dati
#           strutturati e formattabili lato Jinja.
# ------------------------------------------------------------

from __future__ import annotations

import json
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
from apps.vendite.db.offerte_repository import OfferteRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class OffertaDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti OFFERTA_COMMERCIALE."""

    CODE = "OFFERTA_COMMERCIALE"

    # Scopo: Iniezione opzionale del repository per testabilita' mock-only.
    def __init__(self, repo: OfferteRepository | None = None) -> None:
        self._repo = repo or OfferteRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id dell'offerta.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_offerta` (None -> NOT_FOUND);
    #         3. eccezioni (righe documentali v1) + utility 1:1;
    #         4. compone shape stabile (versione 1) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = self._repo.get_offerta(sorgente_id)
        ErrorManager.require(
            testata is not None,
            code=E_NOT_FOUND,
            message="Offerta commerciale non trovata per generazione documento.",
            detail=f"offerta_id={sorgente_id}",
        )
        assert testata is not None

        eccezioni = self._repo.list_eccezioni(sorgente_id)
        utility = self._repo.get_utility(sorgente_id)

        return {
            "offerta": self._shape_offerta(testata),
            "cliente": self._shape_cliente(testata),
            "utility": utility,
            "eccezioni": self._shape_eccezioni(eccezioni),
            # `_meta` qui e' una sezione del context (non
            # `documenti_generati.meta`). Deve restare deterministica:
            # niente timestamp/random; la data generazione vive nel DB.
            "_meta": {
                "locale": locale,
                "auth_user_id": auth_user_id,
                "context_version": 1,
                "context_code": self.CODE,
                "righe_source": "OFFERTE_ECCEZIONI",
            },
        }

    # =================================================================
    # Helpers privati di shaping
    # =================================================================

    # Scopo: Estrae il sotto-dict "offerta" stabile dalla testata. La
    #        repository ritorna gia' campi denormalizzati; qui li
    #        raggruppiamo per rendere il template HTML leggibile.
    def _shape_offerta(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "codice": testata.get("codice"),
            "validita_dal": format_date_it(testata.get("validita_dal")),
            "validita_dal_iso": format_date_iso(testata.get("validita_dal")),
            "validita_al": format_date_it(testata.get("validita_al")),
            "validita_al_iso": format_date_iso(testata.get("validita_al")),
            "data_emissione": format_date_it(testata.get("data_emissione")),
            "data_emissione_iso": format_date_iso(testata.get("data_emissione")),
            "data_accettazione": format_date_it(testata.get("data_accettazione")),
            "data_rifiuto": format_date_it(testata.get("data_rifiuto")),
            "motivazione_rifiuto": testata.get("motivazione_rifiuto"),
            "revisione_numero": testata.get("revisione_numero"),
            "revisione_padre_id": testata.get("revisione_padre_id"),
            "stato": {
                "id": testata.get("stato_doc_offerta_id"),
                "codice": testata.get("stato_codice_interno"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            # Chiave rinominata `descrizione` → `ragione_sociale` il 2026-08-03,
            # a valle del template: la versione PUBBLICATA di `OffertaComm`
            # legge `.get("ragione_sociale") or .get("descrizione")`, quindi il
            # passaggio e' assorbito da entrambi i lati e non c'e' finestra di
            # render rotto. Era l'ultimo punto in cui sopravviveva il nome
            # vecchio: il corpo del template vive a DB
            # (`documenti.template_documenti_versioni`), non in questo repo, e
            # rinominare qui prima di la' avrebbe fatto fallire il render con
            # `StrictUndefined` — non svuotato il campo.
            "emittente_fiscale": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "ragione_sociale": testata.get("emittente_ragione_sociale"),
            },
            "utility_ref": {
                "id": testata.get("utility_id"),
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_display"),
            },
            "listino": {
                "id": testata.get("listino_id"),
                "codice": testata.get("listino_codice"),
                "descrizione": testata.get("listino_descrizione"),
                "versione_id": testata.get("listino_versione_id"),
                "versione_codice": testata.get("listino_versione_codice"),
            },
            "pricing": {
                "modalita": self._resolve_modalita(testata),
                "tipo_variazione_globale": testata.get("tipo_variazione_globale"),
                "valore_variazione_globale": _format_decimal_6(
                    testata.get("valore_variazione_globale")
                ),
            },
            "contratto": {
                "id": testata.get("contratto_id"),
                "numero": testata.get("contratto_numero"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" minimo, allineato ai builder preventivo/
    #        contratto (billing_account + denominazione + id fiscale).
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "billing_account_id": testata.get("billing_account_id"),
            "billing_account_codice": testata.get("ba_codice"),
            "denominazione": testata.get("billing_account_display"),
            "id_fiscale": testata.get("id_fiscale"),
        }

    # Scopo: Deriva la modalita' pricing leggibile dal dato dell'offerta,
    #        speculare al builder contratto. A = listino con variazione
    #        globale, B = listino con sole eccezioni, C = nessun listino.
    def _resolve_modalita(self, testata: dict[str, Any]) -> str:
        if testata.get("listino_id") is None:
            return "C"
        if testata.get("tipo_variazione_globale") is not None:
            return "A"
        return "B"

    # Scopo: Normalizza le righe-eccezione formattando i campi decimali
    #        prezzo (e i prezzi dei componenti BoM annidati) a 6 cifre,
    #        coerente col builder contratto. Il blob `componenti` puo'
    #        arrivare gia' come lista di dict (psycopg con encoder jsonb)
    #        oppure come stringa JSON (driver/lateral con jsonb_agg): in
    #        quest'ultimo caso lo deserializziamo prima dello shape, cosi'
    #        il template Jinja itera su dict (non sui caratteri di una
    #        stringa, errore "'str object' has no attribute 'get'"). Stesso
    #        fix gia' presente lato FE come `coerceJsonbToArray`.
    def _shape_eccezioni(
        self, eccezioni: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        shaped: list[dict[str, Any]] = []
        for riga in eccezioni:
            r = dict(riga)
            for field in ("prezzo_unitario", "quantita", "qta_operativa"):
                if field in r:
                    r[field] = _format_decimal_6(r.get(field))
            r["componenti"] = self._coerce_componenti(r.get("componenti"))
            shaped.append(r)
        return shaped

    # Scopo: Normalizza il blob componenti BoM (jsonb_agg) a lista di dict
    #        formattati. Accetta lista nativa, stringa JSON o valori
    #        sentinella vuoti (None / '[]'); ritorna sempre una lista.
    def _coerce_componenti(self, value: Any) -> list[dict[str, Any]]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                return []
        if not isinstance(value, list):
            return []
        return [self._shape_componente(dict(c)) for c in value if isinstance(c, dict)]

    # Scopo: Formatta i campi prezzo/quantita di un componente BoM annidato.
    def _shape_componente(self, comp: dict[str, Any]) -> dict[str, Any]:
        for field in ("prezzo_unitario", "quantita", "coeff_qta_snapshot"):
            if field in comp:
                comp[field] = _format_decimal_6(comp.get(field))
        return comp


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
register_builder(OffertaDocumentContextBuilder())
