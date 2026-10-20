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
#        ⭐ FORMA 3 dal 2026-10-20 (brief-db-grammatica-unica-documenti
#        §12.10.4): `ordine.origine.etichetta`, il nome del tipo d'origine come
#        lo legge una persona (`config.sorgenti.etichetta`). Prima la carta
#        stampava `origine.tipo`, cioe' un codice (`OFFERTA_COMMERCIALE`). Il
#        render gira con `StrictUndefined`: un modello che legge la chiave nuova,
#        reso da un builder che non la produce, fallisce. Per questo e' una
#        forma nuova e non una chiave in piu' (precedente: fattura 3 → 4).
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

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA
from apps.core.services.testata_guard import testata_o_not_found
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
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    shape_indirizzi_context,
)

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class OrdineDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti ORDINE_VENDITA (conferma d'ordine)."""

    CODE = SORGENTE_ORDINE_VENDITA
    # La forma dei dati prodotti: sede unica (vedi DocumentContextBuilder).
    CONTEXT_VERSION = 3

    # Tipi indirizzo ammessi nell'ambito ORDINE_VENDITA (`config.tipi_indirizzi_allowed`).
    # Dichiarati qui e non letti a runtime: il context deve essere
    # deterministico a parita' di documento (il `context_hash` governa il dedup),
    # e una modifica di configurazione non puo' cambiare la forma di un contesto
    # gia' generato.
    _INDIRIZZI_CODICI: tuple[str, ...] = ("CON", "FATT")

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

        testata = testata_o_not_found(
            self._repo.get_ordine, sorgente_id,
            code=E_NOT_FOUND, message="Ordine non trovato per generazione documento.",
            id_name="ordine_id", function_name="OrdineDocumentContextBuilder.build",
        )

        # Numeri pronti per la stampa (2026-08-04): vedi `_number_formatting`.
        # Le quantita' evase/residue sono misure quanto quella ordinata: se
        # una si legge «99,00» e l'altra «99.000000» la riga non si confronta.
        righe = [
            formatta_campi(
                r,
                misure=("quantita", "qta_operativa", "factor_to_base", "prezzo_unitario",
                        "sconto_percentuale", "qta_evasa_operativa", "qta_residua_operativa"),
                importi=("iva_aliquota", "importo_riga"),
            )
            for r in self._repo.list_righe(sorgente_id)
        ]
        riepilogo_iva = [
            formatta_campi(
                r,
                importi=("iva_aliquota", "imponibile", "imposta", "arrotondamento",
                         "totale_riga"),
            )
            for r in self._repo.list_riepilogo_iva(sorgente_id)
        ]

        return {
            "ordine": self._shape_ordine(testata),
            "cliente": self._shape_cliente(testata),
            # Indirizzi congelati del documento (2026-08-05): il dato era gia'
            # catturato in `vendite.ordini_indirizzi` ma non arrivava al
            # template, che percio' non poteva stamparlo — una conferma
            # d'ordine senza luogo di consegna. Forma unica cross-dominio
            # (slot fissi): vedi `shape_indirizzi_context`.
            "indirizzi": shape_indirizzi_context(
                self._repo.list_indirizzi(sorgente_id),
                codici_ammessi=self._INDIRIZZI_CODICI,
            ),
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
                # v2 (2026-08-05): aggiunto il blocco `indirizzi`.
                # v3 (2026-10-20): `ordine.origine.etichetta`.
                "context_version": self.CONTEXT_VERSION,
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
            # `denominazione` aggiunta il 2026-08-03: il contesto portava solo
            # id e codice, quindi il template non aveva un nome da stampare e
            # ripiegava sul codice — a video usciva
            # «Emittente fiscale PGTAP-EF-20260126172242554».
            # Stesso nome di chiave della fattura (`emittente.denominazione`),
            # cosi' chi scrive un template usa un nome solo su tutti i
            # documenti. Fonte: `emittente_ragione_sociale` della vista, cioe'
            # la ragione sociale del SOGGETTO emittente — la stessa che la
            # fattura congela nello snapshot di intestazione.
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_ragione_sociale"),
            },
            "pagamento": {
                "modalita_codice": testata.get("modalita_pagamento_codice"),
                "termine_codice": testata.get("termine_pagamento_codice"),
            },
            # `tipo` e' il codice della sorgente (per chi lo confronta),
            # `etichetta` il nome da stampare. Le tre chiavi ci sono sempre,
            # `None` senza origine: il template le legge sotto StrictUndefined.
            "origine": {
                "tipo": testata.get("documento_origine_tipo"),
                "codice": testata.get("documento_origine_codice"),
                "etichetta": testata.get("documento_origine_etichetta"),
            },
            "agente_denominazione": testata.get("agente_denominazione"),
            "totali": {
                "imponibile": format_importo(testata.get("imponibile_tot"), campo="imponibile_tot"),
                "sconto": format_importo(testata.get("sconto_tot"), campo="sconto_tot"),
                "iva": format_importo(testata.get("iva_tot"), campo="iva_tot"),
                "documento": format_importo(testata.get("totale_doc"), campo="totale_doc"),
                "valuta_codice": testata.get("valuta_codice"),
                # Misura, non denaro (vedi gemello in fattura).
                "tasso_cambio": format_misura(testata.get("tasso_cambio"), campo="tasso_cambio"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" (soggetto via soggetto_ruolo diretto +
    #        billing account). Denominazione/id fiscale gia' denormalizzati
    #        in vista (`ragione_sociale_completa`/`id_fiscale_univoco_cf_piva`).
    #        Il BA sull'ordine e' NOT NULL e il ruolo e' il suo
    #        (`fk_ordini_ba_cliente`): le due vie portano allo stesso cliente.
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
