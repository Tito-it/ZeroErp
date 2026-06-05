# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente ORDINE_VENDITA (stampa conferma d'ordine). Compone il
#        dizionario di contesto consumato dal template HTML del motore
#        documentale (render_service.render_pdf).
#
#        Quarto dominio cablato sul motore `documenti` dopo
#        preventivo/offerta/contratto (clone strutturale di
#        `preventivo_document_context_builder`, regola del 2 — memoria
#        feedback_regola_del_2_estrai_bb). Differenze ordine:
#         - `CODE = "ORDINE_VENDITA"` (= sorgente + tipo documento + colonna
#           `template_documenti.context_builder_code`, tutti allineati);
#         - niente revisioni (`rev`) ne' listino in testata;
#         - asse OdV-specifico `fatturazione_trigger`;
#         - provenienza upstream (`documento_origine_*`) e agente.
#
#        Confine v1 (allineato a offerta/preventivo v1):
#         - il builder NON applica scope/permessi: responsabilita' del
#           caller (orchestrator + view di dominio con permessi `vendite_*`);
#         - il builder NON conosce il template HTML: fornisce solo dati
#           strutturati formattabili lato Jinja;
#         - `riepilogo_iva` aggregato esposto via la vista DB derivata
#           `vw_ordini_riepilogo_iva_dettaglio` (stessa formula dei preventivi:
#           imponibile/imposta ROUND 2 per gruppo aliquota): il builder legge,
#           nessun calcolo IVA in Python. I totali di testata (`*_tot`) sono
#           mantenuti dal trigger DB via fn_ricalcola_totali_ordine e coincidono
#           per costruzione con la somma del riepilogo.
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
from apps.vendite.db.ordini_repository import OrdiniRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class OrdineDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti ORDINE_VENDITA (conferma d'ordine)."""

    CODE = "ORDINE_VENDITA"

    # Scopo: Iniezione opzionale del repository per testabilita' (mock).
    #        In runtime il default va benissimo: l'istanza e' singleton di
    #        processo (registry).
    def __init__(self, repo: OrdiniRepository | None = None) -> None:
        self._repo = repo or OrdiniRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id dell'ordine.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_ordine` (None -> NOT_FOUND);
    #         3. righe + riepilogo IVA aggregato (vista derivata DB);
    #         4. compone shape stabile (versione 1) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = self._repo.get_ordine(sorgente_id)
        ErrorManager.require(
            testata is not None,
            code=E_NOT_FOUND,
            message="Ordine non trovato per generazione documento.",
            detail=f"ordine_id={sorgente_id}",
        )
        assert testata is not None

        righe = self._repo.list_righe(sorgente_id)
        riepilogo_iva = self._repo.list_riepilogo_iva(sorgente_id)

        return {
            "ordine": self._shape_ordine(testata),
            "cliente": self._shape_cliente(testata),
            "righe": righe,
            "riepilogo_iva": riepilogo_iva,
            # `_meta`: parametri di rendering stabili a parita' di chiamata
            # (locale, utente). NON inserire qui timestamp/random: il
            # `context_hash` deve restare deterministico per il dedup logico
            # (orchestrator). Il tempo di generazione e' tracciato lato DB da
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

    # Scopo: Estrae il sotto-dict "ordine" stabile dalla testata. La vista
    #        `vw_ordini_lista` ritorna gia' campi denormalizzati (stato_*,
    #        valuta_codice, *_tot, ecc.); qui li raggruppiamo in una shape
    #        esplicita per il template (`ordine.totali.imponibile`).
    def _shape_ordine(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "serie": testata.get("serie"),
            "anno": testata.get("anno"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "fatturazione_trigger": testata.get("fatturazione_trigger"),
            "canale_origine": testata.get("canale_origine"),
            "stato": {
                "id": testata.get("stato_doc_ordine_id"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            "utility": {
                "id": testata.get("utility_id"),
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
            },
            "pagamento": {
                "modalita_codice": testata.get("modalita_pagamento_codice"),
                "termine_codice": testata.get("termine_pagamento_codice"),
            },
            "origine": {
                "tipo": testata.get("documento_origine_tipo"),
                "codice": testata.get("documento_origine_codice"),
            },
            "agente_denominazione": testata.get("agente_denominazione"),
            "totali": {
                "imponibile": testata.get("imponibile_tot"),
                "sconto": testata.get("sconto_tot"),
                "iva": testata.get("iva_tot"),
                "documento": testata.get("totale_doc"),
                "valuta_codice": testata.get("valuta_codice"),
                "tasso_cambio": testata.get("tasso_cambio"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" (soggetto via soggetto_ruolo diretto +
    #        billing account). Denominazione/id fiscale gia' denormalizzati
    #        in vista (`ragione_sociale_completa`/`id_fiscale_univoco_cf_piva`),
    #        valorizzati anche per i prospect senza BA.
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "soggetto_ruolo_id": testata.get("soggetto_ruolo_id"),
            "soggetto_id": testata.get("soggetto_id"),
            "denominazione": testata.get("ragione_sociale_completa"),
            "id_fiscale": testata.get("id_fiscale_univoco_cf_piva"),
            "billing_account_id": testata.get("billing_account_id"),
            "ba_codice": testata.get("ba_codice"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Niente auto-discovery via signal.
register_builder(OrdineDocumentContextBuilder())
