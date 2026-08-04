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

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class PreventivoDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti PREVENTIVO."""

    CODE = "PREVENTIVO"

    # Chiavi degli indirizzi documento nel context (shape v1 pre-mixin):
    # solo dati del documento/snapshot congelato, niente decodifiche
    # live-JOIN del drawer FE (vedi commento in build_context).
    _INDIRIZZI_CONTEXT_KEYS: tuple[str, ...] = (
        "id", "preventivo_id", "tipo_indirizzo_id",
        "tipo_indirizzo_descrizione", "snapshot",
        "origine_indirizzo_id", "origine_soggetto_ruolo_id",
    )

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
        # Proiezione STABILE degli indirizzi documento: il mixin condiviso
        # aggiunge chiavi per il drawer FE (tipo_indirizzo_codice,
        # origine_tipo_indirizzo_*) derivate da JOIN LIVE su dati mutabili
        # (anagrafiche.indirizzi, FK SET NULL) — fuori dal context PDF, che
        # dipende solo dallo snapshot congelato. La whitelist replica la
        # shape v1 pre-mixin: il context_hash resta stabile per i documenti
        # gia' generati.
        indirizzi = [
            {k: r.get(k) for k in self._INDIRIZZI_CONTEXT_KEYS}
            for r in self._repo.list_indirizzi(sorgente_id)
        ]

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
                "imponibile": format_importo(testata.get("totale_imponibile")),
                "iva": format_importo(testata.get("totale_iva")),
                "documento": format_importo(testata.get("totale_documento")),
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
