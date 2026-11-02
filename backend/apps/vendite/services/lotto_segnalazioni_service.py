# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura del riepilogo segnalazioni lotto e del verdetto `fermo` (a DB dal 2026-09-19) per il blocco avanzamento step.
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
    # ⭐ Dal 2026-09-19 i due booleani sono lo STESSO valore, `summary["fermo"]`,
    #    letto dal DB: i conteggi qui sopra descrivono, non decidono.
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

    # Scopo: Legge lo stato aggregato del lotto — i conteggi per la frase del
    # banner e il VERDETTO `fermo`, che dal 2026-09-19 nasce a DB
    # (`20260919-01/-02`, D-V1 di Tid: «la regola va a DB»).
    # ⭐ Il verdetto ha TRE addendi — almeno una critica viva, fatture con
    # stato_esecuzione='ERRORE' nella tabella ponte (guard unificata PRE-1), e
    # dal 2026-09-12 (D2) i documenti presi in carico il cui ULTIMO esito e'
    # `ERRORE` — ma la formula vive in `vendite.vw_lotti_segnalazioni_summary`,
    # la sede unica che legge anche il presidio `dbops.vw_lotti_fermi_da_guardare`
    # (digest, pannello «Processi automatici», pallino). Qui si TRASPORTA:
    # `is_error = blocks_next_step = fermo`. Fino a quel giorno la stessa
    # somma era scritta qui in Python — due sedi per un verdetto, e la
    # divergenza al primo addendo nuovo sarebbe stata muta: banner verde su un
    # lotto che il digest chiama fermo (o il contrario), senza nessun test
    # che lo veda.
    # ⚠️ I conteggi restano nel risultato per la FRASE (banner, `detail` del
    # rifiuto del runner, payload di `PIPELINE_COMPLETED`), non per la
    # decisione: un addendo nuovo si aggiunge nella vista e arriva qui da solo.
    # ⚠️ `blocks_next_step` significa NON AVANZARE allo step successivo — non
    # «non eseguire nulla»: il RILANCIO dello stesso step e' ammesso (D-Q p.1)
    # e la distinzione la applica il runner, che qui legge solo il verdetto.
    # E' la via d'uscita del terzo addendo: correggo, rilancio, il pull rivede
    # il documento e scrive l'esito nuovo.
    def evaluate_lotto_status(self, lotto_id: int) -> LottoSignalStatus:
        summary = self.repository.get_lotto_segnalazioni_summary(lotto_id)
        critical_count = summary["fatture_critical_count"] + summary["lotto_critical_count"]
        warning_count = summary["fatture_warning_count"] + summary["lotto_warning_count"]
        # Nel dominio attuale il terzo livello e` "I" (info), usato come attention operativa.
        attention_count = summary["lotto_info_count"]
        stato_esecuzione_errore_count = summary["fatture_stato_esecuzione_errore_count"]
        esiti_errore_count = summary["esiti_stato_esecuzione_errore_count"]
        # ⛔ Il verdetto si LEGGE, non si ricalcola dai tre addendi qui sopra.
        fermo = bool(summary["fermo"])
        return LottoSignalStatus(
            critical_count=critical_count,
            warning_count=warning_count,
            attention_count=attention_count,
            fatture_stato_esecuzione_errore_count=stato_esecuzione_errore_count,
            esiti_stato_esecuzione_errore_count=esiti_errore_count,
            is_error=fermo,
            blocks_next_step=fermo,
            summary=summary,
        )
