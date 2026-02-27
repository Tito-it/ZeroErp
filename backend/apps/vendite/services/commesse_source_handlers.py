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
- BaseSourceHandler  — logica condivisa _process_rows (zero duplicazione)
- HandlerPreventivi  — preventivi accettati → commesse
- HandlerOrdini      — ordini confermati → commesse
- HandlerContratti   — contratti attivi → commesse
- HandlerDdt         — DDT vendita → commesse
- HandlerConsumi     — consumi utility → commesse mensili AUTO (fan-out 1→N)

Architettura:
  Tutte le 5 fn_list_*_da_pushare SQL restituiscono 26 colonne condivise
  normalizzate in PushableRow. _process_rows è l'unico punto di
  orchestrazione: cicla le righe, crea/riusa commesse e upsert attivita.
"""

import dataclasses
import logging
from abc import ABC
from dataclasses import dataclass, field
from typing import Any

from apps.vendite.db.commesse_repository import (
    POLICY_FATTURAZIONE_DA_DOCUMENTO,
    TIPO_COMMESSA_AUTO,
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
)

logger = logging.getLogger(__name__)


@dataclass
class HandlerResult:
    """Risultato di un singolo handler all'interno di un run orchestratore."""

    handler_name: str
    sorgente_codice: str = ""
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
    """Logica condivisa per tutti gli handler sorgente.

    Ogni handler concreto dichiara:
    - ``name``            — stringa identificativa (es. "HandlerPreventivi")
    - ``sorgente_codice`` — codice config.sorgenti (es. "PREVENTIVO")

    e implementa ``run()`` delegando a ``_process_rows()``.
    """

    name: str
    sorgente_codice: str

    def __init__(self, repo: CommesseRepository) -> None:
        self._repo = repo

    def run(self, *, dry_run: bool = False) -> HandlerResult:
        """Esegue la sincronizzazione della sorgente verso commesse_attivita."""
        return self._process_rows(dry_run=dry_run)

    # --- Logica condivisa ---

    def _process_rows(
        self,
        *,
        dry_run: bool = False,
        competenza_mese=None,
        billing_account_id=None,
        limit=None,
    ) -> HandlerResult:
        """Ciclo principale: fetch → get_or_create_commessa → link → upsert.

        Usa cache locale per evitare chiamate DB ridondanti a get_or_create_commessa
        quando piu` righe appartengono alla stessa commessa (stessi parametri chiave).
        """
        result = HandlerResult(handler_name=self.name, sorgente_codice=self.sorgente_codice)
        rows = self._repo.fetch_pushable_rows(
            self.sorgente_codice,
            competenza_mese=competenza_mese,
            billing_account_id=billing_account_id,
            limit=limit,
        )

        # Cache locale: evita round-trip DB ripetuti per la stessa commessa.
        commessa_cache: dict[tuple, int] = {}

        for row in rows:
            try:
                expanded = self._expand_rows(row)
                tipo_commessa = self._extract_tipo_commessa(row)
                policy_fatturazione = self._extract_policy_fatturazione(row)

                cache_key = (
                    row.billing_account_id,
                    row.utility_id,
                    tipo_commessa,
                    policy_fatturazione,
                    row.fatturazione_immediata,
                    row.emittente_soggetto_ruolo_id,
                    row.competenza_dal,
                    row.competenza_al,
                )

                if cache_key in commessa_cache:
                    commessa_id = commessa_cache[cache_key]
                else:
                    commessa_id = self._repo.get_or_create_commessa(
                        billing_account_id=row.billing_account_id,
                        utility_id=row.utility_id,
                        tipo_commessa=tipo_commessa,
                        policy_fatturazione=policy_fatturazione,
                        fatturazione_immediata=row.fatturazione_immediata,
                        emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id,
                        competenza_dal=row.competenza_dal,
                        competenza_al=row.competenza_al,
                    )
                    commessa_cache[cache_key] = commessa_id

                self._repo.link_sorgente(
                    commessa_id=commessa_id,
                    sorgente_tipo_id=row.sorgente_tipo_id,
                    sorgente_uid=row.sorgente_uid,
                )

                for exp in expanded:
                    inp = self._build_attivita_input(commessa_id, exp)
                    if not dry_run:
                        self._repo.upsert_attivita(inp)
                    result.created += 1

            except Exception as exc:
                msg = f"Errore riga segment_key={row.segment_key}: {type(exc).__name__}: {exc}"
                logger.exception(msg)
                result.errors.append(msg)

        return result

    def _expand_rows(self, row: PushableRow) -> list[PushableRow]:
        """Hook per fan-out 1→N. Default: 1:1 pass-through."""
        return [row]

    @staticmethod
    def _extract_tipo_commessa(row: PushableRow) -> str:
        """#6: tipo_commessa da meta, default TIPO_COMMESSA_AUTO."""
        if isinstance(row.meta, dict):
            return row.meta.get("tipo_commessa", TIPO_COMMESSA_AUTO)
        return TIPO_COMMESSA_AUTO

    @staticmethod
    def _extract_policy_fatturazione(row: PushableRow) -> str:
        """#6: policy_fatturazione da meta, default POLICY_FATTURAZIONE_DA_DOCUMENTO."""
        if isinstance(row.meta, dict):
            return row.meta.get("policy_fatturazione", POLICY_FATTURAZIONE_DA_DOCUMENTO)
        return POLICY_FATTURAZIONE_DA_DOCUMENTO

    def _build_attivita_input(
        self, commessa_id: int, row: PushableRow
    ) -> CommessaAttivitaInput:
        """Costruisce CommessaAttivitaInput da PushableRow con default corretti."""
        return CommessaAttivitaInput(
            commessa_id=commessa_id,
            segment_key=row.segment_key,
            quantita=row.quantita or 0,
            competenza_mese=row.competenza_mese,
            articolo_id=row.articolo_id,
            prezzo_snapshot=row.prezzo_snapshot,
            uom_id=row.uom_id,
            tipo_doc_fiscale_id=row.tipo_doc_fiscale_id,
            valuta_id=row.valuta_id,
            prezzo_bloccato=row.prezzo_bloccato,
            pricing_mode=row.pricing_mode,
            tipo_movimento=row.tipo_movimento,
            tipo_consumo=row.tipo_consumo,
            istanza_utility_id=row.istanza_utility_id,
            data_attivita=row.data_attivita,
            competenza_dal=row.competenza_dal,
            competenza_al=row.competenza_al,
            qta_operativa=row.qta_operativa,
            uom_operativa_id=row.uom_operativa_id,
            factor_to_base=row.factor_to_base,
            sorgente_tipo_id=row.sorgente_tipo_id,
            sorgente_uid=row.sorgente_uid,
            meta=row.meta,
        )


# --- Handler concreti ---


class HandlerPreventivi(BaseSourceHandler):
    """Sincronizza preventivi accettati → commesse."""

    name = "HandlerPreventivi"
    sorgente_codice = "PREVENTIVO"


class HandlerOrdini(BaseSourceHandler):
    """Sincronizza ordini confermati → commesse (#1: ORDINE_VENDITA)."""

    name = "HandlerOrdini"
    sorgente_codice = "ORDINE_VENDITA"


class HandlerContratti(BaseSourceHandler):
    """Sincronizza contratti attivi → commesse (#8 nuovo)."""

    name = "HandlerContratti"
    sorgente_codice = "CONTRATTO"


class HandlerDdt(BaseSourceHandler):
    """Sincronizza DDT vendita → commesse (#8 nuovo)."""

    name = "HandlerDdt"
    sorgente_codice = "DDT_VENDITA"


@dataclass(frozen=True)
class ComponenteConsumabile:
    """Struttura per espansione componenti consumo (fan-out 1→N)."""

    codice: str
    articolo_id: Any
    quantita: Any
    prezzo: Any
    uom_id: int | None


class HandlerConsumi(BaseSourceHandler):
    """Sincronizza consumi utility → commesse mensili AUTO (#9: fan-out 1→N).

    Ogni riga consumo base viene espansa in N componenti tramite
    _expand_rows(). _fetch_componenti resta stub — richiede fn DB
    per lookup componenti da catalogo/utility.
    """

    name = "HandlerConsumi"
    sorgente_codice = "ATTIVITA_CONSUMI"

    def _expand_rows(self, row: PushableRow) -> list[PushableRow]:
        """Fan-out: espande una riga consumo base in N righe componente."""
        componenti = self._fetch_componenti(row)
        if not componenti:
            return [row]
        return [
            dataclasses.replace(
                row,
                segment_key=f"{row.segment_key}:COMP:{comp.codice}",
                articolo_id=comp.articolo_id,
                quantita=comp.quantita,
                prezzo_snapshot=comp.prezzo,
                uom_id=comp.uom_id,
            )
            for comp in componenti
        ]

    @staticmethod
    def _fetch_componenti(_row: PushableRow) -> list[ComponenteConsumabile]:
        """Stub: fn DB per lookup componenti utility non ancora disponibile."""
        return []
