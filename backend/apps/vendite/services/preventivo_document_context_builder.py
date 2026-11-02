# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from collections.abc import Mapping

from typing import Any

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._number_formatting import (
    format_importo,
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
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    shape_indirizzi_context,
)

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class PreventivoDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti PREVENTIVO."""

    CODE = SORGENTE_PREVENTIVO
    # La forma dei dati prodotti: sede unica (vedi DocumentContextBuilder).
    CONTEXT_VERSION = 2

    # Tipi indirizzo ammessi nell'ambito PREVENTIVO
    # (`config.tipi_indirizzi_allowed`: FATT, CON, FORNITURA, RES — stesso
    # insieme di OFFERTA_COMMERCIALE). Dichiarati qui e non letti a runtime: il context
    # deve essere deterministico a parita' di documento (il `context_hash`
    # governa il dedup), e una modifica di configurazione non puo' cambiare la
    # forma di un contesto gia' generato.
    _INDIRIZZI_CODICI: tuple[str, ...] = ("CON", "FATT", "FORNITURA", "RES")

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
    #         4. compone shape stabile (versione 2) usata dai template HTML.
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = testata_o_not_found(
            self._repo.get_preventivo, sorgente_id,
            code=E_NOT_FOUND, message="Preventivo non trovato per generazione documento.",
            id_name="preventivo_id", function_name="PreventivoDocumentContextBuilder.build",
        )

        # Numeri pronti per la stampa (2026-08-04, segnalazione di Tid: la
        # quantita' usciva «5.000000»). I valori arrivavano grezzi dal
        # repository, cioe' con la scala della colonna: qui prendono il
        # formato italiano, come le date poco piu' sotto. Misure e importi
        # seguono due regole diverse — vedi `_number_formatting`.
        righe = [
            formatta_campi(
                r,
                misure=("quantita", "qta_operativa", "prezzo_unitario", "sconto_percentuale"),
                importi=("importo_riga", "iva_aliquota"),
            )
            for r in self._repo.list_righe(sorgente_id)
        ]
        riepilogo_iva = [
            formatta_campi(
                r,
                importi=("iva_aliquota", "imponibile", "imposta", "arrotondamento", "totale_riga"),
            )
            for r in self._repo.list_riepilogo_iva(sorgente_id)
        ]
        return {
            "preventivo": self._shape_preventivo(testata),
            "cliente": self._shape_cliente(testata),
            # Indirizzi congelati del documento. Dal 2026-08-16 (context v2)
            # nella forma unica cross-dominio `shape_indirizzi_context`: slot
            # con nome e chiavi fisse, non piu' la lista da scorrere della v1.
            # Era l'ultimo dominio a slot rimasto fuori dal BB — la promessa
            # di «una forma sola» (brief-db-template-preventivo-indirizzi
            # §7.2) valeva su 4 builder su 6. Il context_hash dei preventivi
            # gia' generati cambia: e' ammesso, sono documenti di test e non
            # siamo in produzione (decisione di Tid 2026-08-16, §11.3 di
            # brief-db-indirizzi-su-ordini-contratti-offerte).
            #
            # Il template che legge questa forma e' la **v4** del Preventivo,
            # pubblicata dal DB lo stesso giorno (changeSet 20260816-01/-02) e
            # provata da Tid sulla stampa: la v3 iterava `indirizzi` come lista
            # e con un dict avrebbe fatto fallire il render (StrictUndefined).
            # Il template stampa il solo slot `consegna`, dentro il riquadro
            # Cliente come gli altri cinque: e' il template a scegliere cosa
            # stampare, il contesto espone tutti i tipi ammessi dall'ambito.
            # Cantiere: brief-db-template-preventivo-slot (work-done).
            "indirizzi": shape_indirizzi_context(
                self._repo.list_indirizzi(sorgente_id),
                codici_ammessi=self._INDIRIZZI_CODICI,
            ),
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
                # v2 (2026-08-16): `indirizzi` passa da lista a slot con nome
                # (forma unica cross-dominio).
                "context_version": self.CONTEXT_VERSION,
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
    def _shape_preventivo(self, testata: Mapping[str, Any]) -> dict[str, Any]:
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
            # Aggiunto il 2026-08-03: il contesto preventivo non aveva affatto
            # l'emittente, e il template pubblicato stampava la stringa cablata
            # «Emittente fiscale demo» su ogni preventivo. Stessa forma di
            # fattura/ordine/DDT — un nome solo di chiave su tutti i documenti.
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_ragione_sociale"),
            },
            "termine_pagamento": {
                "id": testata.get("termine_pagamento_id"),
                "descrizione": testata.get("termine_pagamento_descrizione"),
            },
            "totali": {
                "imponibile": format_importo(testata.get("totale_imponibile"), campo="totale_imponibile"),
                "iva": format_importo(testata.get("totale_iva"), campo="totale_iva"),
                "documento": format_importo(testata.get("totale_documento"), campo="totale_documento"),
                "valuta_id": testata.get("valuta_id"),
                "valuta_codice": testata.get("valuta_codice"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Sotto-dict "cliente" minimo (billing_account + denominazione).
    #        v1: niente espansione completa di soggetti/indirizzi cliente —
    #        bastano denominazione + id per il template iniziale; futuro
    #        in Fase B se serve P.IVA/CF/sede legale strutturati.
    def _shape_cliente(self, testata: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "billing_account_id": testata.get("billing_account_id"),
            "denominazione": testata.get("cliente_denominazione"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Memoria del progetto:
# niente auto-discovery via signal Django.
register_builder(PreventivoDocumentContextBuilder())
