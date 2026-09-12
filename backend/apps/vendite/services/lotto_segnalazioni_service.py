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
    # ⭐ IL TERZO ADDENDO DEL VERDETTO (2026-09-12, D2): i documenti presi in
    #    carico il cui ultimo esito e' `ERRORE`. Puo' essere > 0 con
    #    `critical_count == 0`: e' il caso che prima chiudeva COMPLETATO.
    esiti_stato_esecuzione_errore_count: int
    is_error: bool
    blocks_next_step: bool
    summary: LottoSegnalazioniSummary


# I tre livelli di segnalazione, nel vocabolario del DB (`status` di
# `fatture_log` / `fatturazione_lotti_log`). Stanno QUI, accanto a chi li
# aggrega, e non nella view o nel client: sono la stessa scala che i conteggi
# del riepilogo separano (`critical` / `warning` / `attention`).
# ⚠️ 'I' esiste solo sulle segnalazioni di LOTTO — il riepilogo conta
# `lotto_info_count` e non ha il gemello per le fatture.
LIVELLO_CRITICO = "C"
LIVELLO_AVVISO = "W"
LIVELLO_ATTENZIONE = "I"
LIVELLI_SEGNALAZIONE: tuple[str, ...] = (
    LIVELLO_CRITICO,
    LIVELLO_AVVISO,
    LIVELLO_ATTENZIONE,
)


class LottoSegnalazioniService:
    """Valuta lo stato segnalazioni del lotto per decidere se bloccare lo step successivo."""

    # Scopo: Inizializza servizio segnalazioni con repository dominio.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Calcola stato aggregato del lotto con regola di blocco su TRE
    # addendi: almeno un critical attivo, fatture con stato_esecuzione='ERRORE'
    # nella tabella ponte (guard unificata PRE-1), e — dal 2026-09-12 (D2 del
    # brief «il rilancio dello step non rivede le proprie commesse») — documenti
    # presi in carico il cui ULTIMO esito (`fatturazione_lotti_esiti`) e'
    # `ERRORE`.
    # ⭐ Perche' il terzo: il runner ritira le proprie bandiere all'avvio di ogni
    # rerun («chi alza la bandiera la abbassa»). Se il giro non rivede un
    # documento — righe passate a RIFIUTATA/ANNULLATA, trattenute nel frattempo
    # da un altro lotto — nessuno le rialza, e l'unica traccia durevole, l'esito
    # ERRORE sul documento, non fermava niente: il lotto usciva COMPLETATO con
    # un documento preso in carico e ancora in errore. Un esito e' un FATTO, e
    # un lotto non e' a posto per sottrazione. `ESCLUSO` non conta: e' la via
    # d'uscita, l'operatore ha DICHIARATO che quel documento esce dal giro.
    # ⚠️ `blocks_next_step` significa NON AVANZARE allo step successivo — non
    # «non eseguire nulla»: il RILANCIO dello stesso step e' ammesso (D-Q p.1)
    # e la distinzione la applica il runner, che qui legge solo i conteggi.
    # E' proprio la via d'uscita del terzo addendo: correggo, rilancio, il pull
    # rivede il documento e scrive l'esito nuovo.
    def evaluate_lotto_status(self, lotto_id: int) -> LottoSignalStatus:
        summary = self.repository.get_lotto_segnalazioni_summary(lotto_id)
        critical_count = summary["fatture_critical_count"] + summary["lotto_critical_count"]
        warning_count = summary["fatture_warning_count"] + summary["lotto_warning_count"]
        # Nel dominio attuale il terzo livello e` "I" (info), usato come attention operativa.
        attention_count = summary["lotto_info_count"]
        stato_esecuzione_errore_count = summary["fatture_stato_esecuzione_errore_count"]
        esiti_errore_count = summary["esiti_stato_esecuzione_errore_count"]
        is_error = (
            critical_count > 0
            or stato_esecuzione_errore_count > 0
            or esiti_errore_count > 0
        )
        return LottoSignalStatus(
            critical_count=critical_count,
            warning_count=warning_count,
            attention_count=attention_count,
            fatture_stato_esecuzione_errore_count=stato_esecuzione_errore_count,
            esiti_stato_esecuzione_errore_count=esiti_errore_count,
            is_error=is_error,
            blocks_next_step=is_error,
            summary=summary,
        )
