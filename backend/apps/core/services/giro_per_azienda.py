# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL GIRO PER AZIENDA di un processo di dominio headless: per ogni
#        utente tecnico del processo (il roster), un lavoro dentro la SUA
#        identità, con l'errore isolato per azienda; e insieme, le aziende che
#        nessun utente tecnico copre. È la forma che drenatore della stampa,
#        giro delle email, produttore della fatturazione e drenatore della coda
#        lavori ricopiavano ciascuno a modo suo.
# Note: ⭐ Regola del 2, ok Tid 2026-11-07 (BE10 di brief-db-revisione-dbops):
#        le copie erano tre, e già divergenti nei nomi (`falliti`,
#        `emittenti_falliti`, `badge_falliti`) e nell'ordine delle letture.
#        Il BB tiene il GIRO; il lavoro e il riepilogo restano al chiamante,
#        perché ciascuno somma cose diverse e ha già un esito che altri leggono.
#        ⛔ Il perimetro lo decide il BADGE, non il lavoro: un'azienda senza
#        utente tecnico non viene servita, ed è una decisione (D-9). Per questo
#        l'esito porta `non_serviti`: distingue «non c'era niente» da «non ho
#        guardato».
#        ⛔ Un'azienda che fallisce non ferma le altre: il loro lavoro è già
#        buono, e buttarlo via perché la terza è andata storta sarebbe peggio.
#        ⛔ Nessun canale di sistema qui dentro: ogni lavoro gira con
#        l'identità del badge, o non gira.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from apps.core.db.processi_repository import ProcessiRepository, RigaRoster
from apps.core.services.coda_lavori.context import operator_identity_context

logger = logging.getLogger(__name__)

T = TypeVar("T")


# Scopo: L'esito del giro. `serviti` in ordine di roster, ognuno col risultato
#        del lavoro; `falliti` con la frase dell'errore; `non_serviti` sono i
#        codici delle aziende attive senza utente tecnico.
# ⭐ Due assenze diverse, tenute separate: «non ha un badge» si ripara creando
#    l'utente tecnico, «il badge non ha funzionato» guardando l'errore.
@dataclass
class EsitoGiroPerAzienda(Generic[T]):
    serviti: list[tuple[RigaRoster, T]] = field(default_factory=list)
    falliti: list[dict[str, str]] = field(default_factory=list)
    non_serviti: list[str] = field(default_factory=list)
    roster_vuoto: bool = False


# Scopo: Esegue `lavoro(badge)` per ogni utente tecnico di `processo_codice`,
#        dentro `operator_identity_context` di quel badge, con l'emittente
#        attivo congelato sul suo. `on_badge(badge, risultato, errore)` per la
#        console del chiamante; `evento` è il prefisso del log di un'azienda
#        fallita.
# ⚠️ L'emittente ATTIVO si dichiara anche se il badge ne ha uno solo: evita che
#    il lavoro giri in modalità globale il giorno in cui l'utente ne avesse due.
def giro_per_azienda(
    processo_codice: str,
    lavoro: Callable[[RigaRoster], T],
    *,
    evento: str,
    on_badge: Callable[[RigaRoster, T | None, Exception | None], None] | None = None,
    processi_repo: ProcessiRepository | None = None,
) -> EsitoGiroPerAzienda[T]:
    processi_repo = processi_repo or ProcessiRepository()
    roster = processi_repo.roster_processo(processo_codice)
    esito: EsitoGiroPerAzienda[T] = EsitoGiroPerAzienda(roster_vuoto=not roster)

    for badge in roster:
        try:
            with operator_identity_context(
                badge["auth_user_id"],
                username=badge["username"],
                identita_id=badge["identita_id"],
                emittente_attivo_id=badge["emittente_fiscale_id"],
            ):
                risultato = lavoro(badge)
        except Exception as exc:  # isolamento per azienda voluto
            logger.warning(
                "%s.azienda_fallita emittente=%s badge=%s errore=%s",
                evento, badge["emittente_codice"], badge["username"], exc,
                exc_info=True,
            )
            esito.falliti.append({
                "emittente_codice": badge["emittente_codice"], "errore": str(exc),
            })
            if on_badge is not None:
                on_badge(badge, None, exc)
            continue
        esito.serviti.append((badge, risultato))
        if on_badge is not None:
            on_badge(badge, risultato, None)

    esito.non_serviti = [
        e["emittente_codice"]
        for e in processi_repo.emittenti_non_serviti(processo_codice)
    ]
    return esito
