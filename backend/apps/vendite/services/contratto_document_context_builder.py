# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from typing import Any

from apps.config.sorgenti import SORGENTE_CONTRATTO
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._number_formatting import (
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
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    shape_indirizzi_context,
)

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class ContrattoDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti CONTRATTO."""

    CODE = SORGENTE_CONTRATTO
    # La forma dei dati prodotti: sede unica (vedi DocumentContextBuilder).
    CONTEXT_VERSION = 2

    # Tipi indirizzo ammessi nell'ambito CONTRATTO
    # (`config.tipi_indirizzi_allowed`). Dichiarati qui e non letti a runtime:
    # il context deve essere deterministico a parita' di documento (il
    # `context_hash` governa il dedup), e una modifica di configurazione non
    # puo' cambiare la forma di un contesto gia' generato.
    _INDIRIZZI_CODICI: tuple[str, ...] = ("CON", "FATT", "FORNITURA")

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

        testata = testata_o_not_found(
            self._repo.get_contratto, sorgente_id,
            code=E_NOT_FOUND, message="Contratto non trovato per generazione documento.",
            id_name="contratto_id", function_name="ContrattoDocumentContextBuilder.build",
        )

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
            # Indirizzi congelati del documento (2026-08-05): il dato era gia'
            # catturato in `vendite.contratti_indirizzi` ma non arrivava al
            # template, che percio' non poteva stamparlo. Forma unica
            # cross-dominio (slot fissi): vedi `shape_indirizzi_context`.
            "indirizzi": shape_indirizzi_context(
                self._repo.list_indirizzi(sorgente_id),
                codici_ammessi=self._INDIRIZZI_CODICI,
            ),
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
                # v2 (2026-08-05): aggiunto il blocco `indirizzi`.
                "context_version": self.CONTEXT_VERSION,
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
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            "utility": {
                "id": testata.get("utility_id"),
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            # Aggiunto il 2026-08-03 insieme a ordine/DDT/preventivo: il
            # contesto contratto non aveva affatto l'emittente, mentre la
            # testata lo espone per intero. Il modello di template in
            # `manual/template_contratto_iniziale.md` ci aveva messo la stringa
            # cablata «Emittente fiscale demo» — un segnaposto che, copiato in
            # un template pubblicato, finisce stampato su un documento al
            # cliente (e' successo su quattro template). Stessa chiave di
            # fattura/ordine/DDT/preventivo: un nome solo su tutti i documenti.
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_ragione_sociale"),
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

    # Scopo: righe con i numeri pronti per la stampa. Fino al 2026-08-04 qui
    #        c'era un `_format_decimal_6` locale che forzava SEMPRE sei
    #        decimali: `120.000000` per un canone di 120 euro. Ora vale la
    #        regola comune a tutti i documenti (minimo 2, massimo 6, senza
    #        zeri superflui), quindi «120,00» ma «0,153» dove i decimali sono
    #        davvero significativi — che era la ragione per cui quei sei
    #        decimali erano stati messi.
    def _shape_righe(self, righe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            formatta_campi(
                r,
                misure=("prezzo_finale", "prezzo_unitario", "override_prezzo",
                        "quantita", "qta_operativa", "quantita_fissa", "factor_to_base"),
            )
            for r in righe
        ]


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry centrale.
register_builder(ContrattoDocumentContextBuilder())
