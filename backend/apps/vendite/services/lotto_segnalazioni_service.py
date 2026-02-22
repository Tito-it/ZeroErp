# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Valutazione riepilogo segnalazioni lotto e regola di blocco avanzamento step.
# ------------------------------------------------------------


from dataclasses import dataclass

from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import LottoSegnalazioniSummary


@dataclass(frozen=True)
class LottoSignalStatus:
    critical_count: int
    warning_count: int
    attention_count: int
    fatture_stato_esecuzione_errore_count: int
    is_error: bool
    blocks_next_step: bool
    summary: LottoSegnalazioniSummary


class LottoSegnalazioniService:
    """Valuta lo stato segnalazioni del lotto per decidere se bloccare lo step successivo."""

    # Scopo: Inizializza servizio segnalazioni con repository dominio.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Calcola stato aggregato del lotto con regola di blocco su presenza di almeno un critical attivo
    # o di fatture con stato_esecuzione='ERRORE' nella tabella ponte (guard unificata PRE-1).
    def evaluate_lotto_status(self, lotto_id: int) -> LottoSignalStatus:
        summary = self.repository.get_lotto_segnalazioni_summary(lotto_id)
        critical_count = summary["fatture_critical_count"] + summary["lotto_critical_count"]
        warning_count = summary["fatture_warning_count"] + summary["lotto_warning_count"]
        # Nel dominio attuale il terzo livello e` "I" (info), usato come attention operativa.
        attention_count = summary["lotto_info_count"]
        stato_esecuzione_errore_count = self.repository.count_fatture_stato_esecuzione_errore(lotto_id)
        is_error = critical_count > 0 or stato_esecuzione_errore_count > 0
        return LottoSignalStatus(
            critical_count=critical_count,
            warning_count=warning_count,
            attention_count=attention_count,
            fatture_stato_esecuzione_errore_count=stato_esecuzione_errore_count,
            is_error=is_error,
            blocks_next_step=is_error,
            summary=summary,
        )
