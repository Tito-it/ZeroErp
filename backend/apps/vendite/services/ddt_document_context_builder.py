# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente DDT_VENDITA (stampa DDT accompagnatorio). Compone il
#        dizionario di contesto consumato dal template HTML del motore
#        documentale (render_service.render_pdf).
#
#        Quinto dominio cablato sul motore `documenti` dopo
#        preventivo/offerta/contratto/ordine (clone strutturale di
#        `ordine_document_context_builder`, regola del 2 — memoria
#        feedback_regola_del_2_estrai_bb). Differenze DDT:
#         - `CODE = "DDT_VENDITA"` (= sorgente + tipo documento + colonna
#           `template_documenti.context_builder_code`, tutti allineati);
#         - documento di TRASPORTO: niente totali/riepilogo IVA in testata
#           (i prezzi riga restano nel contesto: il template decide se
#           stamparli — l'accompagnatorio standard non li riporta);
#         - blocco `trasporto` (causale, aspetto beni, porto, colli, pesi,
#           volume, targa, autista, tracking, partenza/consegna prevista)
#           + `mittente`/`vettore` denormalizzati dalla vista;
#         - provenienza upstream = ordine di vendita (`ordine_origine_*`).
#
#        Confine (allineato alla famiglia):
#         - il builder NON applica scope/permessi: responsabilita' del
#           caller (orchestrator + view di dominio con permessi `vendite_*`);
#         - il builder NON conosce il template HTML: fornisce solo dati
#           strutturati formattabili lato Jinja.
#
#        v2 (2026-07-12): blocco `indirizzi.consegna` dallo snapshot
#        congelato `ddt_indirizzi` (slot CON — unico tipo ammesso in ambito
#        DDT). All'emissione il CON e' garantito dal guard DB
#        (`E_INDIRIZZO_DOC_OBBLIGATORIO`); in anteprima DRAFT puo' mancare
#        -> `consegna = None`, il template degrada senza blocco indirizzo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.config.sorgenti import SORGENTE_DDT_VENDITA
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._number_formatting import (
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
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    shape_indirizzi_context,
)

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class DdtDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti DDT_VENDITA (DDT accompagnatorio)."""

    CODE = SORGENTE_DDT_VENDITA
    # La forma dei dati prodotti: sede unica (vedi DocumentContextBuilder).
    CONTEXT_VERSION = 2

    # Scopo: Iniezione opzionale del repository per testabilita' (mock).
    #        In runtime il default va benissimo: l'istanza e' singleton di
    #        processo (registry).
    def __init__(self, repo: DdtRepository | None = None) -> None:
        self._repo = repo or DdtRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id del DDT.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_ddt` (None -> NOT_FOUND);
    #         3. righe attive (con decodifiche articolo/uom/iva);
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
            self._repo.get_ddt, sorgente_id,
            code=E_NOT_FOUND, message="DDT non trovato per generazione documento.",
            id_name="ddt_id", function_name="DdtDocumentContextBuilder.build",
        )

        # Numeri pronti per la stampa (2026-08-04): vedi `_number_formatting`.
        righe = [
            formatta_campi(
                r,
                misure=("quantita", "qta_operativa", "factor_to_base"),
                importi=("importo_riga",),
            )
            for r in self._repo.list_righe(sorgente_id)
        ]

        return {
            "ddt": self._shape_ddt(testata),
            "destinatario": self._shape_destinatario(testata),
            "indirizzi": self._shape_indirizzi(sorgente_id),
            "trasporto": self._shape_trasporto(testata),
            "righe": righe,
            # `_meta`: parametri di rendering stabili a parita' di chiamata
            # (locale, utente). NON inserire qui timestamp/random: il
            # `context_hash` deve restare deterministico per il dedup logico
            # (orchestrator). Il tempo di generazione e' tracciato lato DB da
            # `documenti_generati.generato_at`.
            "_meta": {
                "locale": locale,
                "auth_user_id": auth_user_id,
                "context_version": self.CONTEXT_VERSION,
                "context_code": self.CODE,
            },
        }

    # =================================================================
    # Helpers privati di shaping
    # =================================================================

    # Scopo: Estrae il sotto-dict "ddt" stabile dalla testata. La vista
    #        `vw_ddt_lista` ritorna gia' campi denormalizzati (stato_*,
    #        valuta_codice, emittente_fiscale_codice, ordine_origine_*);
    #        qui li raggruppiamo in una shape esplicita per il template.
    #        NB: `numero` e' NULL in DRAFT (assegnato a EMESSO dal trigger):
    #        l'anteprima in bozza mostra il fallback del template.
    def _shape_ddt(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "serie": testata.get("serie"),
            "anno": testata.get("anno"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "stato": {
                "id": testata.get("stato_doc_ddt_id"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            "utility": {
                "id": testata.get("utility_id"),
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            # `denominazione` aggiunta il 2026-08-03, stesso difetto dell'ordine:
            # senza un nome il template ripiegava sul codice e stampava
            # «Emittente fiscale PGTAP-EF-2026...». Chiave allineata a fattura e
            # ordine — un nome solo per tutti i documenti.
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_ragione_sociale"),
            },
            "valuta_codice": testata.get("valuta_codice"),
            "origine": {
                "ordine_id": testata.get("ordine_origine_id"),
                "ordine_numero": testata.get("ordine_origine_numero"),
                "sorgente_codice_interno": testata.get("sorgente_codice_interno"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "destinatario" (soggetto via soggetto_ruolo NOT NULL +
    #        billing account). Denominazione/id fiscale gia' denormalizzati
    #        in vista. Il DDT usa la semantica "destinatario" (non "cliente"):
    #        e' chi RICEVE la merce, coincidente col cliente del BA nel caso
    #        standard ma potenzialmente diverso (consegna a terzi).
    def _shape_destinatario(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "soggetto_ruolo_id": testata.get("destinatario_soggetto_ruolo_id"),
            "soggetto_id": testata.get("destinatario_soggetto_id"),
            "denominazione": testata.get("destinatario_denominazione"),
            "id_fiscale": testata.get("id_fiscale_univoco_cf_piva"),
            "billing_account_id": testata.get("billing_account_id"),
            "ba_codice": testata.get("ba_codice"),
        }

    # Tipi indirizzo ammessi nell'ambito DDT_VENDITA (`config.tipi_indirizzi_allowed`,
    # ambito DDT_VENDITA = solo `CON`, obbligatorio). Dichiarati qui e non letti a
    # runtime: il context deve essere deterministico a parita' di documento.
    _INDIRIZZI_CODICI: tuple[str, ...] = ("CON",)

    # Scopo: Sotto-dict "indirizzi" dallo snapshot congelato `ddt_indirizzi`
    #        (`consegna` = slot CON, chiavi fisse + `display_compatto`; None se
    #        lo slot manca, es. anteprima in DRAFT).
    #        Dal 2026-08-05 la forma vive nel BB condiviso
    #        `shape_indirizzi_context`: era nata qui ed e' ora la forma di tutti
    #        i domini. Output invariato — `context_hash` dei DDT gia' generati
    #        resta quello di prima.
    def _shape_indirizzi(self, ddt_id: int) -> dict[str, Any]:
        return shape_indirizzi_context(
            self._repo.list_indirizzi(ddt_id),
            codici_ammessi=self._INDIRIZZI_CODICI,
        )

    # Scopo: Sotto-dict "trasporto": il cuore dell'accompagnatorio. Causale,
    #        aspetto beni, porto (modalita addebito), logistica (colli, pesi,
    #        volume, targa, autista, tracking) + mittente/vettore denormalizzati
    #        + orari partenza/consegna prevista.
    def _shape_trasporto(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "causale": {
                "id": testata.get("causale_trasporto_id"),
                "codice": testata.get("causale_trasporto_codice"),
                "descrizione": testata.get("causale_trasporto_descrizione"),
            },
            "aspetto_beni": {
                "id": testata.get("aspetto_bene_id"),
                "codice": testata.get("aspetto_bene_codice"),
                "descrizione": testata.get("aspetto_bene_descrizione"),
            },
            "porto_codice": testata.get("modalita_addebito_trasporto_codice"),
            "mittente_denominazione": testata.get("mittente_denominazione"),
            "vettore_denominazione": testata.get("vettore_denominazione"),
            # ⚠️ `num_colli` NON si formatta: e' un conteggio, e «12,00 colli»
            # sarebbe una lettura sbagliata. Pesi e volume invece sono misure.
            "num_colli": testata.get("num_colli"),
            "peso_lordo": format_misura(testata.get("peso_lordo"), campo="peso_lordo"),
            "peso_netto": format_misura(testata.get("peso_netto"), campo="peso_netto"),
            "volume": format_misura(testata.get("volume"), campo="volume"),
            "targa": testata.get("targa"),
            "autista": testata.get("autista"),
            "tracking_code": testata.get("tracking_code"),
            "data_ora_partenza": testata.get("data_ora_partenza"),
            "data_ora_consegna_prev": testata.get("data_ora_consegna_prev"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Niente auto-discovery via signal.
register_builder(DdtDocumentContextBuilder())
