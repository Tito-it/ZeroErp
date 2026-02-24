# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler sorgente per CommessaPushOrchestrator.
#        Ogni handler sa come leggere la propria sorgente e
#        tradurla in chiamate CommesseRepository.
# ------------------------------------------------------------

"""
Handler registrati:
- BaseSourceHandler  — interfaccia astratta
- HandlerPreventivi  — preventivi LIBERO → commesse
- HandlerOrdini      — ordini confermati → commesse
- HandlerConsumi     — consumi utility   → commesse mensili AUTO

Nota: i tre handler concreti sono stub. La query di selezione
sorgente va implementata quando il team DB fornirà:
  - fn_list_preventivi_da_pushare
  - fn_list_ordini_da_pushare
  - fn_list_consumi_da_pushare
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from apps.vendite.db.commesse_repository import CommesseRepository


@dataclass
class HandlerResult:
    """Risultato di un singolo handler all'interno di un run orchestratore."""

    handler_name: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Serializza per commesse_push_log.risultato (JSONB)."""
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
        }


class BaseSourceHandler(ABC):
    """Interfaccia comune per tutti gli handler sorgente.

    Ogni handler concreto dichiara un attributo di classe ``name``
    (stringa che identifica la sorgente, es. "HandlerPreventivi")
    e implementa ``run()``.
    """

    name: str  # class-level identifier — da sovrascrivere nelle sottoclassi

    def __init__(self, repo: CommesseRepository) -> None:
        self._repo = repo

    @abstractmethod
    def run(self, *, dry_run: bool = False) -> HandlerResult:
        """Esegue la sincronizzazione della sorgente verso commesse_attivita.

        Deve essere idempotente: chiamate successive producono lo stesso
        stato finale (upsert su segment_key).
        """


class HandlerPreventivi(BaseSourceHandler):
    """Sincronizza preventivi LIBERO → commesse.

    Per ogni preventivo eleggibile:
      1. get_or_create_commessa (billing_account dal preventivo)
      2. link_sorgente (tipo=PREVENTIVO, uid=codice_preventivo)
      3. upsert_attivita per ogni riga preventivo

    DB richiesto (team DB): fn_list_preventivi_da_pushare
      Deve restituire per ogni riga: billing_account_id, utility_id,
      emittente_soggetto_ruolo_id, competenza_dal/al, articolo_id,
      uom_id, quantita, prezzo_snapshot, tipo_doc_fiscale_id, valuta_id,
      listino_versione_id, sorgente_tipo_id, sorgente_uid, segment_key.
    """

    name = "HandlerPreventivi"

    def run(self, *, dry_run: bool = False) -> HandlerResult:
        # TODO: implementare dopo rilascio fn_list_preventivi_da_pushare
        #
        # rows = ... SELECT ... FROM vendite.fn_list_preventivi_da_pushare()
        # for row in rows:
        #     commessa_id = self._repo.get_or_create_commessa(
        #         billing_account_id=row.billing_account_id, ...
        #     )
        #     self._repo.link_sorgente(
        #         commessa_id=commessa_id,
        #         sorgente_tipo_id=row.sorgente_tipo_id,
        #         sorgente_uid=row.sorgente_uid,
        #     )
        #     if not dry_run:
        #         self._repo.upsert_attivita(CommessaAttivitaInput(...))
        raise NotImplementedError(
            "HandlerPreventivi: richiede fn_list_preventivi_da_pushare (team DB)"
        )


class HandlerOrdini(BaseSourceHandler):
    """Sincronizza ordini confermati → commesse.

    Struttura analoga a HandlerPreventivi.

    DB richiesto (team DB): fn_list_ordini_da_pushare
      Stessa firma di fn_list_preventivi_da_pushare ma per ordini confermati.
    """

    name = "HandlerOrdini"

    def run(self, *, dry_run: bool = False) -> HandlerResult:
        # TODO: implementare dopo rilascio fn_list_ordini_da_pushare
        raise NotImplementedError(
            "HandlerOrdini: richiede fn_list_ordini_da_pushare (team DB)"
        )


class HandlerConsumi(BaseSourceHandler):
    """Sincronizza consumi utility → commesse mensili AUTO.

    Crea una commessa per ogni coppia (billing_account, utility, mese)
    con tipo_commessa="AUTO", poi upsert delle righe consumo.

    DB richiesto (team DB): fn_list_consumi_da_pushare
      Deve restituire consumi aggregati per mese pronti per upsert.
    """

    name = "HandlerConsumi"

    def run(self, *, dry_run: bool = False) -> HandlerResult:
        # TODO: implementare dopo rilascio fn_list_consumi_da_pushare
        raise NotImplementedError(
            "HandlerConsumi: richiede fn_list_consumi_da_pushare (team DB)"
        )
