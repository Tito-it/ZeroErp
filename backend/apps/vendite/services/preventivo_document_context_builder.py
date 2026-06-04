# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente PREVENTIVO (Tranche J). Compone il dizionario di
#        contesto consumato dal template HTML del motore documentale
#        (Tranche I -> render_service.render_pdf).
#
#        Pattern (coerente con `pipeline_task_registry_impl` di vendite):
#         - definizione classe builder con `CODE = "PREVENTIVO"`;
#         - registrazione esplicita via `register_builder(...)` a fine
#           modulo, eseguita all'import (l'import e' triggerato da
#           `VenditeConfig.ready()`);
#         - lookup dati via `PreventiviRepository`: testata, righe,
#           riepilogo IVA, indirizzi (gia' rese dal dominio vendite).
#
#        Confine v1:
#         - il builder NON applica scope/permessi: la responsabilita'
#           e' del caller (orchestrator + view di dominio Tranche K
#           con permessi `vendite_*`);
#         - il builder NON conosce il template HTML: si limita a
#           fornire dati strutturati e formattabili lato Jinja
#           (`{{ preventivo.numero }}`, `{% for r in righe %}`...).
# ------------------------------------------------------------

from __future__ import annotations

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
from apps.vendite.db.preventivi_repository import PreventiviRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class PreventivoDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti PREVENTIVO."""

    CODE = "PREVENTIVO"

    # Scopo: Iniezione opzionale del repository per testabilita' (mock).
    #        In runtime il default va benissimo: l'istanza e' singleton di
    #        processo (registry).
    def __init__(self, repo: PreventiviRepository | None = None) -> None:
        self._repo = repo or PreventiviRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id del preventivo.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_preventivo` (None -> NOT_FOUND);
    #         3. righe + riepilogo IVA + indirizzi;
    #         4. compone shape stabile (versione 1) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = self._repo.get_preventivo(sorgente_id)
        ErrorManager.require(
            testata is not None,
            code=E_NOT_FOUND,
            message="Preventivo non trovato per generazione documento.",
            detail=f"preventivo_id={sorgente_id}",
        )
        assert testata is not None

        righe = self._repo.list_righe(sorgente_id)
        riepilogo_iva = self._repo.list_riepilogo_iva(sorgente_id)
        indirizzi = self._repo.list_indirizzi(sorgente_id)

        return {
            "preventivo": self._shape_preventivo(testata),
            "cliente": self._shape_cliente(testata),
            "indirizzi": indirizzi,
            "righe": righe,
            "riepilogo_iva": riepilogo_iva,
            # `_meta` qui e' una sezione del context (non confondere con
            # `documenti_generati.meta`): contiene parametri di rendering
            # stabili a parita' di chiamata (locale, utente). NON inserire
            # qui timestamp/random: `context_hash` deve essere deterministico
            # per consentire dedup logico (Tranche I orchestrator). Il
            # tempo della generazione e' gia' tracciato lato DB da
            # `documenti_generati.generato_at`.
            "_meta": {
                "locale": locale,
                "auth_user_id": auth_user_id,
                "context_version": 1,
                "context_code": self.CODE,
            },
        }

    # =================================================================
    # Helpers privati di shaping
    # =================================================================

    # Scopo: Estrae il sotto-dict "preventivo" stabile dalla testata. La
    #        repository ritorna gia' campi denormalizzati (stato_codice,
    #        stato_descrizione, valuta_codice, ecc.); qui li raggruppiamo
    #        in una shape dedicata per usi piu' espliciti dal template
    #        (`preventivo.totali.imponibile` invece di `totale_imponibile`
    #        a top-level).
    def _shape_preventivo(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "rev": testata.get("rev"),
            "is_attiva": testata.get("is_attiva"),
            "has_next_revision": testata.get("has_next_revision"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "validita_dal": format_date_it(testata.get("validita_dal")),
            "validita_dal_iso": format_date_iso(testata.get("validita_dal")),
            "validita_al": format_date_it(testata.get("validita_al")),
            "validita_al_iso": format_date_iso(testata.get("validita_al")),
            "competenza_mese": format_date_it(testata.get("competenza_mese")),
            "competenza_mese_iso": format_date_iso(testata.get("competenza_mese")),
            "fatturazione_immediata": testata.get("fatturazione_immediata"),
            "stato": {
                "id": testata.get("stato_doc_preventivo_id"),
                "codice": testata.get("stato_codice"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            "utility": {
                "id": testata.get("utility_id"),
                "descrizione": testata.get("utility_descrizione"),
            },
            "termine_pagamento": {
                "id": testata.get("termine_pagamento_id"),
                "descrizione": testata.get("termine_pagamento_descrizione"),
            },
            "totali": {
                "imponibile": testata.get("totale_imponibile"),
                "iva": testata.get("totale_iva"),
                "documento": testata.get("totale_documento"),
                "valuta_id": testata.get("valuta_id"),
                "valuta_codice": testata.get("valuta_codice"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" minimo (billing_account + denominazione).
    #        v1: niente espansione completa di soggetti/indirizzi cliente —
    #        bastano denominazione + id per il template iniziale; futuro
    #        in Fase B se serve P.IVA/CF/sede legale strutturati.
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "billing_account_id": testata.get("billing_account_id"),
            "denominazione": testata.get("cliente_denominazione"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Memoria del progetto:
# niente auto-discovery via signal Django.
register_builder(PreventivoDocumentContextBuilder())
