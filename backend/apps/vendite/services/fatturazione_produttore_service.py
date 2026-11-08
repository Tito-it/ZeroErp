# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PRODUTTORE del giro di fatturazione notturno. Non fattura: per ogni
#        azienda servita dal processo `run_fatturazione_batch` ACCODA un lavoro
#        `FATTURAZIONE_GIRO`, con l'identita' dell'utente tecnico di quella
#        azienda.
# Note: ⭐ Perche' la coda e non un giro in-process (che sarebbe stato piu'
#        corto): la coda porta ritentativi, backoff e isolamento per riga. Un
#        emittente che fallisce fallisce DA SOLO e riprova; prima una corsa sola
#        attraversava tutte le aziende e un inciampo poteva fermarle tutte.
#        ⛔ E nessun canale `BYPASSRLS`: ogni lavoro gira dentro il perimetro del
#        proprio badge. E' il punto del cantiere «nessun processo senza
#        operatore» — il batch era l'ultimo a scavalcare i muri fra le aziende.
#        ⚠️ Il perimetro lo decide il BADGE, non il lavoro: si accoda per gli
#        emittenti che hanno un utente tecnico. Chi non ce l'ha NON viene
#        servito, e il produttore lo DICE — senza quella riga sarebbe un giro
#        che chiude «FATTO» avendo saltato un'azienda intera (D-9).
#        Brief: work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md §lotto 3
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from typing import Any

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.coda_lavori.repository import (
    ORIGINE_CRON,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.giro_per_azienda import giro_per_azienda
from apps.core.services.processi import PROCESSO_RUN_FATTURAZIONE_BATCH
from apps.vendite.services._fatturazione_job_helpers import (
    JOB_TYPE_FATTURAZIONE_GIRO,
    chiave_idempotenza_giro,
)


# Scopo: Accoda un giro di fatturazione per OGNI azienda servita dal processo
#        `run_fatturazione_batch`, nella corsia indicata e per la competenza
#        indicata. Ritorna l'esito aggregato per il run-log e la console.
#
# ⭐ La CHIAVE di dedup e' `tipo : corsia : competenza : perimetro`, composta dal
#    building block condiviso con il verbo dell'applicazione. La corsia c'e'
#    perche' senza di lei due giri della stessa azienda e dello stesso mese ma di
#    corsia diversa sarebbero lo stesso lavoro, e il secondo verrebbe scartato
#    senza dirlo: una delle due corsie semplicemente non fatturerebbe.
# ⚠️ `emittente_ids` porta la PK dell'emittente, che e' la convenzione di
#    `scope_key_da_emittenti` e della whitelist — NON il `soggetto_ruolo_id`.
#    Sono due numeri diversi per la stessa azienda, e scambiarli produce un
#    perimetro che non trova niente ([[feedback_emittente_pk_vs_soggetto_ruolo]]).
# ⛔ Un accodamento che fallisce non ferma gli altri: il lavoro delle altre
#    aziende e' gia' buono, e buttarlo perche' la terza e' andata storta sarebbe
#    peggio del difetto.
def accoda_giri_fatturazione(
    *,
    modalita: str,
    competenza: date,
    fino_a_stato: str | None = None,
    processi_repo: ProcessiRepository | None = None,
    coda_repo: CodaLavoriRepository | None = None,
    on_emittente: Callable[[Mapping[str, Any], int | None, Exception | None], None] | None = None,
) -> dict[str, Any]:
    coda_repo = coda_repo or CodaLavoriRepository()

    # Scopo: accoda il giro di UN badge, gia' dentro la sua identita'.
    # ⛔ DENTRO l'identita' del badge, ed e' la correzione di BE10 (c): dal giro
    #    5a la porta `fn_accoda_lavoro`, da una sessione dell'applicazione,
    #    accoda un lavoro OPERATORE solo a nome di chi e' in sessione. Fuori da
    #    un'identita' ogni azienda tornava `E_CODA_SCOPE_ALTRUI`, e il giro
    #    notturno non accodava niente.
    def _accoda(badge: Mapping[str, Any]) -> int:
        payload: dict[str, Any] = {
            "competenza_mese": competenza.isoformat(),
            # ⭐ La corsia viaggia nel payload E nella chiave: l'handler la legge
            #    da qui invece di dedurla, cosi' cio' che e' stato deduplicato e
            #    cio' che verra' eseguito sono la stessa cosa.
            "modalita": modalita,
        }
        if fino_a_stato:
            payload["fino_a_stato"] = fino_a_stato
        # ⛔ Nessuna `data_documento` qui, ed e' una scelta: il giro NOTTURNO non
        #    dichiara la data del documento — la decide la politica del registro
        #    (OGGI / FINE_MESE_COMPETENZA). Un parametro che nessuno passa
        #    sembrerebbe un'opzione e sarebbe solo superficie morta; il giorno in
        #    cui il cron dovesse dichiararla, si aggiunge insieme all'argomento
        #    CLI che la fornisce.

        emittente_ids = [badge["emittente_fiscale_id"]]
        # ⚠️ Calcolata UNA volta: la stessa chiave va nello scope (token di
        #    ownership del polling) e nella chiave di dedup. Due chiamate
        #    sarebbero due occasioni di divergere.
        scope_key = scope_key_da_emittenti(emittente_ids)
        return coda_repo.accoda(
            job_type=JOB_TYPE_FATTURAZIONE_GIRO,
            payload=payload,
            run_as=RUN_AS_OPERATORE,
            scope={
                "auth_user_id": badge["auth_user_id"],
                "username": badge["username"],
                "identita_id": badge["identita_id"],
                # Congelato: il worker esegue minuti dopo, e senza questo
                # valore girerebbe in modalita' globale.
                "emittente_attivo_id": badge["emittente_fiscale_id"],
                "emittente_ids": emittente_ids,
                "scope_key": scope_key,
            },
            idempotency_key=chiave_idempotenza_giro(
                job_type=JOB_TYPE_FATTURAZIONE_GIRO,
                competenza=competenza,
                scope_key=scope_key,
                corsia=modalita,
            ),
            origine=ORIGINE_CRON,
        )

    # ⭐ Il giro (roster, identita', isolamento, non serviti) e' il BB
    #    `giro_per_azienda` (regola del 2, 2026-11-07).
    giro = giro_per_azienda(
        PROCESSO_RUN_FATTURAZIONE_BATCH,
        _accoda,
        evento="fatturazione.accodamento",
        on_badge=on_emittente,
        processi_repo=processi_repo,
    )
    accodati = [
        {
            "emittente_codice": badge["emittente_codice"],
            "emittente_fiscale_id": badge["emittente_fiscale_id"],
            "job_id": job_id,
        }
        for badge, job_id in giro.serviti
    ]

    return {
        "modalita": modalita,
        "competenza": competenza.isoformat(),
        "accodati": len(accodati),
        "giri": accodati,
        "falliti": giro.falliti,
        # ⭐ Il numero che rompe il silenzio: aziende attive che nessun badge
        #    copre. Il loro mese NON viene fatturato, e senza questa riga il run
        #    chiuderebbe «FATTO» sembrando completo.
        "emittenti_non_serviti": giro.non_serviti,
    }
