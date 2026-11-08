# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `QueueDrainEngine` — il LOOP di drenaggio generico e riusabile,
#        costruito UNA volta (design §4a). Possiede la policy di
#        reaper → claim (batch misto per priorità) → per-item best-effort →
#        tally → retry con backoff. È parametrizzato da un `QueueBackend`
#        (SQL tipizzato per-coda) e da una callback `per_item` (il lavoro:
#        dispatch-handler per la coda generica, render per la stampa). Nessun
#        SQL qui: solo orchestrazione. Riusato sia da `dbops.coda_lavori` sia,
#        a convergenza, da `fatture_stampa_coda`.
#
#        ⚠️ CONFINE con `apps/core/services/fan_out.py` (D-1 del brief fan-out,
#        2026-08-09). I due motori si somigliano — «per ogni item isola l'errore
#        e prosegui» — e la scelta di NON unificarli e' deliberata: qui l'item
#        vive in una coda DUREVOLE, sopravvive al run e va riclamato, posseduto
#        e ritentato con backoff; li' la lista e' EFFIMERA (scoperta, consumata
#        una volta, e chi resta indietro si ritrova alla prossima scoperta).
#        Regola pratica: se l'item deve essere ritrovato DOPO il run, e' roba di
#        questo motore; se basta riscoprirlo, e' `run_fan_out`.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from apps.core.services.error_manager import ServiceError

from .backend import QueueBackend, QueueItem

logger = logging.getLogger(__name__)

# Backoff esponenziale con cap sui retry (brief DB §6: `run_after = now()+f(tentativi)`
# per non affamare il poll con un poison-job che ritenta a ogni giro). Il motore
# decide l'intervallo; il backend lo applica col clock DB (`now()+interval`).
_BACKOFF_BASE_SECONDI = 60
_BACKOFF_CAP_SECONDI = 3600

# Chiave con cui un handler dichiara, nel `context` del suo `ServiceError`, che
# il fallimento e' DETERMINISTICO: riprovare produrrebbe lo stesso esito, quindi
# il motore va in ERRORE subito invece di bruciare i tentativi con backoff.
# Casi tipici: payload malformato, perimetro che non contiene lavoro fatturabile.
# Costante esportata e non letterale duplicato: la chiave vive in due moduli
# (chi la scrive e chi la legge) e un refuso la renderebbe muta, non rotta.
CONTEXT_KEY_TERMINALE = "terminale"

# I CONTATORI dell'esito di un drenaggio (`QueueDrainEngine.drain`, e il
# drenatore della stampa che ne ricalca la forma): sono le chiavi che il giro
# per azienda somma (`EsitoGiroPerAzienda.totali`). Sede unica — erano due
# tuple identiche, una per drenatore, e aggiungere un contatore in una sola
# l'avrebbe tolto in silenzio dal totale dell'altra.
CHIAVI_ESITO_DRENAGGIO: tuple[str, ...] = (
    "recuperate", "claimate", "fatto", "errore", "riprovabili",
)


# Scopo: Costruisce il `context` di un ServiceError terminale, con eventuali
#        campi diagnostici del chiamante. Zucchero, ma evita che la chiave si
#        propaghi come stringa nei domini.
def contesto_terminale(**extra: Any) -> dict[str, Any]:
    return {CONTEXT_KEY_TERMINALE: True, **extra}


# Scopo: secondi di attesa prima del prossimo tentativo, esponenziale cappato
#        (1ª ritenta ~1m, poi 2m, 4m… fino a 1h).
def backoff_secondi_default(prossimo_tentativo: int) -> int:
    return min(
        _BACKOFF_BASE_SECONDI * (2 ** max(0, prossimo_tentativo - 1)),
        _BACKOFF_CAP_SECONDI,
    )


class QueueDrainEngine:
    """Motore di drenaggio generico su un `QueueBackend`.

    Il `per_item(item)` esegue il lavoro e ritorna il `result` (dict); solleva
    `ServiceError` (o altro) su fallimento. Il motore traduce l'esito in
    transizione di stato via il backend, applicando la policy di retry/backoff.
    Best-effort per-riga: il fallimento di UN item non ferma gli altri; il
    fallimento di una scrittura di stato (backend) invece propaga (la run va
    marcata fallita, non mascherata).
    """

    # Scopo: Inizializza il motore su un backend + la callback di lavoro.
    def __init__(
        self,
        backend: QueueBackend,
        *,
        per_item: Callable[[QueueItem], dict[str, Any] | None],
        backoff_secondi: Callable[[int], int] = backoff_secondi_default,
    ) -> None:
        self._backend = backend
        self._per_item = per_item
        self._backoff = backoff_secondi

    # Scopo: Un giro di drenaggio. Perimetro: (1) reaper opzionale delle righe
    #        IN_CORSO stantie; (2) claim di ≤ `limit` item; (3) per ciascuno il
    #        lavoro best-effort + transizione di stato. Risultato: esito
    #        aggregato per il run-log e la console.
    def drain(
        self,
        *,
        limit: int,
        stale_minuti: int,
        on_item_esito: Callable[[QueueItem, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        recuperate = (
            self._backend.reap_stale(stale_minuti=stale_minuti)
            if stale_minuti > 0 else 0
        )
        items = self._backend.claim(limit=limit)

        fatto = 0
        errore = 0        # → ERRORE terminale (soglia raggiunta)
        riprovabili = 0   # → PENDING con backoff (ritenteranno)
        for item in items:
            esito = self._lavora_item(item)
            if esito["esito"] == "fatto":
                fatto += 1
            elif esito["esito"] == "errore":
                errore += 1
            else:
                riprovabili += 1
            if on_item_esito is not None:
                on_item_esito(item, esito)

        return {
            "recuperate": recuperate,
            "claimate": len(items),
            "fatto": fatto,
            "errore": errore,
            "riprovabili": riprovabili,
            "limit": limit,
        }

    # Scopo: Lavora un singolo item. Best-effort: cattura il fallimento del
    #        lavoro, decide terminale-vs-retry (soglia tentativi) e persiste lo
    #        stato. Le scritture di stato NON sono catturate (se il DB non
    #        risponde, la run fallisce onestamente).
    def _lavora_item(self, item: QueueItem) -> dict[str, Any]:
        try:
            result = self._per_item(item)
        except ServiceError as exc:
            errore: dict[str, Any] = {
                "code": exc.code,
                "message": str(exc.message or exc),
                "detail": exc.detail,
            }
            # Il `context` dell'handler viene PERSISTITO in `ultimo_errore`:
            # e' il dettaglio strutturato del fallimento (es. un motivo per
            # gruppo non servito) e senza questa riga andrebbe perso — il
            # repository serializza con `json.dumps(default=str)`, quindi
            # date/Decimal degradano a stringa invece di far saltare la
            # scrittura di stato.
            if exc.context:
                errore["context"] = exc.context
            return self._registra_errore(
                item,
                errore,
                # Fallimento DETERMINISTICO dichiarato dall'handler: si va in
                # ERRORE subito, senza consumare i tentativi. Ritentare un
                # payload malformato o un perimetro non fatturabile riproduce lo
                # stesso esito N volte, tiene il job «in corso» a video e scrive
                # N volte lo stesso errore. `context` e' il canale gia'
                # esistente su ServiceError; NON si usa `retryable`, che nel
                # progetto significa «l'utente puo' riprovare con altri dati»
                # (envelope API) — semantica diversa da «il motore ritenti».
                terminale_forzato=bool(exc.context.get(CONTEXT_KEY_TERMINALE)),
            )
        except Exception as exc:  # resilienza per-riga voluta
            # Eccezione non prevista: nessuna dichiarazione, quindi si assume
            # transitoria e valgono i tentativi (comportamento storico).
            return self._registra_errore(
                item, {"code": type(exc).__name__, "message": str(exc)},
            )
        self._backend.mark_done(item.id, result=result or {})
        return {"esito": "fatto", "job_type": item.job_type}

    # Scopo: Traduce un fallimento in transizione ERRORE (terminale) o PENDING
    #        con backoff (retry), secondo la soglia tentativi del work-item —
    #        salvo `terminale_forzato`, con cui l'handler dichiara che riprovare
    #        non cambierebbe nulla.
    def _registra_errore(
        self,
        item: QueueItem,
        errore: dict[str, Any],
        *,
        terminale_forzato: bool = False,
    ) -> dict[str, Any]:
        terminale = terminale_forzato or item.tentativi + 1 >= item.max_tentativi
        retry_after = None if terminale else self._backoff(item.tentativi + 1)
        self._backend.mark_error(
            item.id, errore=errore, retry_after_secondi=retry_after,
        )
        logger.warning(
            "coda_lavori.item_fallito id=%s job_type=%s code=%s terminale=%s",
            item.id, item.job_type, errore.get("code"), terminale,
        )
        return {
            "esito": "errore" if terminale else "riprovabile",
            "job_type": item.job_type,
            "code": errore.get("code"),
        }
