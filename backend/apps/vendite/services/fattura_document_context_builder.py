# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente FATTURA (stampa/ristampa della fattura). Compone il
#        dizionario di contesto consumato dal template HTML del motore
#        documentale (render_service.render_pdf).
#
#        Sesto dominio cablato sul motore `documenti` dopo
#        preventivo/offerta/contratto/ordine/DDT (clone strutturale di
#        `ordine_document_context_builder`, regola del 2 — memoria
#        feedback_regola_del_2_estrai_bb). Differenze FATTURA:
#         - `CODE = "FATTURA"` (= config.sorgenti.codice_interno + tipo
#           documento + colonna `template_documenti.context_builder_code`,
#           tutti allineati, sorgente id 10);
#         - la fattura NON si "emette" da UI: è già prodotta dalla pipeline
#           di fatturazione. Il builder alimenta solo stampa/ristampa (nessuna
#           transizione di stato → la view factory è istanziata SENZA emetti);
#         - i read stanno in `VenditeRepository` (nessun repository fattura
#           dedicato), accanto a `list_lotto_fatture`;
#         - `riepilogo_iva` letto dalla tabella REALE
#           `vendite.fatture_riepiloghi_iva` (non da una vista derivata come
#           per gli ordini): la fattura fissa il riepilogo fiscale al momento
#           dell'emissione, il builder lo legge tale e quale.
#
#        Confine v1 (allineato agli altri domini):
#         - il builder NON applica scope/permessi: responsabilità del caller
#           (view di dominio con permessi `vendite_*` nel path web; canale
#           l'identita' dell'utente tecnico nel path worker C-2b);
#         - il builder NON conosce il template HTML: fornisce solo dati
#           strutturati formattabili lato Jinja; nessun calcolo fiscale in
#           Python (imponibile/imposta/totali sono già mantenuti dalla
#           pipeline sulle tabelle fattura).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._number_formatting import (
    format_importo,
    format_misura,
    formatta_campi,
)
from apps.documenti.services.context_builders._date_formatting import (
    format_date_it,
    format_date_iso,
)
from apps.documenti.services.context_builders.base import (
    DocumentContextBuilder,
)
from apps.documenti.services.context_builders.registry import register_builder
from apps.vendite.db.vendite_repository import VenditeRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class FatturaDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti FATTURA (stampa/ristampa fattura)."""

    CODE = "FATTURA"

    # Scopo: Iniezione opzionale del repository per testabilità (mock). In
    #        runtime il default va benissimo: l'istanza è singleton di processo
    #        (registry).
    def __init__(self, repo: VenditeRepository | None = None) -> None:
        self._repo = repo or VenditeRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id della fattura.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_fattura_testata` (None → NOT_FOUND);
    #         3. righe + riepilogo IVA (tabella reale fatture_riepiloghi_iva);
    #         4. compone shape stabile (versione 1) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = self._repo.get_fattura_testata(sorgente_id)
        ErrorManager.require(
            testata is not None,
            code=E_NOT_FOUND,
            message="Fattura non trovata per generazione documento.",
            detail=f"fattura_id={sorgente_id}",
        )
        assert testata is not None

        # Numeri pronti per la stampa (2026-08-04): dal repository arrivano
        # con la scala della colonna (`7.000000`), qui prendono il formato
        # italiano. Misure e importi seguono due regole diverse — vedi
        # `_number_formatting`.
        righe = [
            formatta_campi(
                r,
                misure=("quantita", "qta_operativa", "factor_to_base", "prezzo_unitario",
                        "sconto_percentuale"),
                importi=("iva_aliquota", "importo_riga", "imponibile_riga"),
            )
            for r in self._repo.list_fattura_righe(sorgente_id)
        ]
        riepilogo_iva = [
            formatta_campi(
                r,
                importi=("iva_aliquota", "imponibile", "imposta", "arrotondamento",
                         "totale_riga"),
            )
            for r in self._repo.list_fattura_riepilogo_iva(sorgente_id)
        ]
        scadenze = self._repo.list_fattura_scadenze(sorgente_id)

        return {
            "fattura": self._shape_fattura(testata),
            "cliente": self._shape_cliente(testata),
            "righe": righe,
            "riepilogo_iva": riepilogo_iva,
            "scadenze": [self._shape_scadenza(s) for s in scadenze],
            # `_meta`: parametri di rendering stabili a parità di chiamata
            # (locale, utente). NON inserire qui timestamp/random: il
            # `context_hash` deve restare deterministico per il dedup logico
            # (orchestrator). Il tempo di generazione è tracciato lato DB da
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

    # Scopo: Estrae il sotto-dict "fattura" stabile dalla testata (numero
    #        fiscale, date IT/ISO, stato/tipo doc fiscale, emittente, totali).
    #        I totali sono raggruppati in una shape esplicita per il template
    #        (`fattura.totali.imponibile`).
    def _shape_fattura(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "serie": testata.get("serie"),
            "anno": testata.get("anno"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "data_contabilizzazione": format_date_it(
                testata.get("data_contabilizzazione")
            ),
            "tipo_doc": {
                "id": testata.get("tipo_doc_fiscale_id"),
                "codice_interno": testata.get("tipo_doc_fiscale_codice"),
                "descrizione": testata.get("tipo_doc_fiscale_descrizione"),
            },
            "stato": {
                "id": testata.get("stato_doc_fiscale_id"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            # Intestazione emittente (chi emette la fattura): dallo SNAPSHOT
            # congelato `fatture.emittente_snapshot` (Fase 2 satelliti,
            # 2026-07-31 — ristampa conforme: l'anagrafica puo' cambiare, il
            # documento no). Le chiavi piatte sono derivate dal jsonb in
            # `get_fattura_testata`; `sede` e' il display dell'indirizzo
            # annidato, risolto a DB sui due layer RUOLO→SOGGETTO al momento
            # dello snapshot. `piva` = id fiscale univoco (P.IVA per le
            # imprese); `cf` = codice fiscale. Tutto None se lo snapshot manca
            # (fattura pre-Fase 1): nessun fallback per decisione (§9 piano).
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_denominazione"),
                "piva": testata.get("emittente_piva"),
                "cf": testata.get("emittente_cf"),
                "sede": testata.get("emittente_sede"),
            },
            "bollo_applicato": testata.get("bollo_applicato"),
            "totali": {
                "imponibile": format_importo(testata.get("imponibile_tot")),
                "imposta": format_importo(testata.get("imposta_tot")),
                # alias `iva` (nome usato dal template) dell'imposta totale
                "iva": format_importo(testata.get("imposta_tot")),
                "sconto": format_importo(testata.get("sconto_tot")),
                "bollo": format_importo(testata.get("bollo_importo")),
                "arrotondamento": format_importo(testata.get("arrotondamento_attuale")),
                "documento": format_importo(testata.get("totale_doc")),
                "a_pagare": format_importo(testata.get("totale_a_pagare")),
                "valuta_codice": testata.get("valuta_codice"),
                # Il tasso di cambio e' una MISURA, non denaro: `1.00000000`
                # si legge «1,00», ma un cambio 0,8732 conserva le sue cifre.
                "tasso_cambio": format_misura(testata.get("tasso_cambio")),
            },
            # Campi «ricchi» del template. Chiavi SEMPRE presenti (StrictUndefined
            # → chiave mancante = errore); il template le guarda con {% if %},
            # quindi None = riga omessa. `agente`/`origine` NON sono mantenuti
            # come dato di testata di questa fattura (reseller/sorgente polimorfa
            # a NULL) → restano None finché il flusso a monte non li popola
            # (documentato nel brief). `pagamento` è sorgentato (JOIN sotto).
            "agente_denominazione": testata.get("agente_denominazione"),
            "origine": {
                "codice": testata.get("origine_codice"),
                "tipo": testata.get("origine_tipo"),
            },
            "pagamento": {
                "modalita_codice": testata.get("pagamento_modalita_codice"),
                "termine_codice": testata.get("pagamento_termine_codice"),
            },
            # Utility del servizio fatturato (dal billing account → config.utilities).
            "utility": {
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" dallo SNAPSHOT congelato
    #        `fatture.cliente_snapshot` (chiavi piatte derivate in
    #        `get_fattura_testata`) + indirizzo di fatturazione dalla riga
    #        `FATT` del satellite `fatture_indirizzi`. Ristampa conforme:
    #        nessuna lettura live dell'anagrafica.
    #        ⚠️ `billing_account_id`/`ba_codice` sono il BA *padre* (D-P), non
    #        il conto del consumatore nelle gerarchie.
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "soggetto_ruolo_id": testata.get("cliente_soggetto_ruolo_id"),
            "soggetto_id": testata.get("soggetto_id"),
            "denominazione": testata.get("ragione_sociale_completa"),
            "id_fiscale": testata.get("id_fiscale_univoco_cf_piva"),
            # Display dello snapshot FATT congelato. None se assente (fattura
            # pre-snapshot, nessun fallback — §9); chiave sempre presente
            # (StrictUndefined); il template la guarda con {% if %}.
            "indirizzo": testata.get("cliente_indirizzo"),
            "billing_account_id": testata.get("billing_account_id"),
            "ba_codice": testata.get("ba_codice"),
        }

    # Scopo: Sotto-dict "scadenza" (rata del piano pagamenti). Chiavi stabili
    #        attese dal template (`nr`/`data`/`importo`/`modalita_codice`); tutte
    #        presenti (il motore usa StrictUndefined → una chiave mancante è
    #        errore di render). `modalita_codice` dal jsonb meta se presente.
    def _shape_scadenza(self, s: dict[str, Any]) -> dict[str, Any]:
        meta = s.get("meta") or {}
        return {
            "nr": s.get("numero_rata"),
            "data": format_date_it(s.get("data_scadenza")),
            "data_iso": format_date_iso(s.get("data_scadenza")),
            "importo": format_importo(s.get("importo")),
            "modalita_codice": meta.get("modalita_codice"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Niente auto-discovery via signal.
register_builder(FatturaDocumentContextBuilder())
