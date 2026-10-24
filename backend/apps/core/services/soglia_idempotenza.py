# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio fra il timeout del server web e la soglia di ripresa di
#        una Idempotency-Key (BE-5 di brief-be-verifica-documentazione-api,
#        2026-10-24). Lo chiama `gunicorn.conf.py` all'avvio: un rapporto
#        sbagliato e' un backend che non parte.
# Note: ⭐ Perche'. La ripresa di una key ATOMICA rimasta `in_progress` e'
#       sicura solo perche' nessuna richiesta vive piu' del timeout di
#       gunicorn: oltre `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` chi lavorava e'
#       morto senza commit. Alzando il timeout sopra la soglia, una richiesta
#       ancora viva verrebbe ripresa da un reinvio e l'operazione girerebbe due
#       volte in parallelo. Fino a quel giorno la relazione stava solo in un
#       commento del changeSet 20261023-04.
#       ⚠️ Il presidio legge il timeout EFFETTIVO del processo (la `cfg` di
#       gunicorn), non una variabile d'ambiente: i lanciatori sono due
#       (`bin/start-gunicorn.sh` e il `CMD` del Dockerfile), e ognuno lo
#       scrive a modo suo.
# ------------------------------------------------------------

from __future__ import annotations

from gunicorn.workers.sync import SyncWorker

from apps.core.services.parameter_service import ParameterService

CODICE_SOGLIA = "SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI"

# Lo spazio fra la richiesta piu' lunga possibile e la soglia: copre il tempo
# fra la prenotazione della key e l'inizio dell'handler, e l'orologio del
# database contro quello del worker (proposta del brief §I.7.4, BE-5).
MARGINE_SECONDI = 30

# L'unico tipo di worker in cui `timeout` e' il tetto di UNA richiesta: il
# worker che non risponde al battito per `timeout` secondi viene ucciso, e un
# worker sync risponde solo fra una richiesta e l'altra. In `gthread` o nei
# worker asincroni il battito continua mentre la richiesta lavora, e il tetto
# non c'e'.
# ⚠️ Si confronta la CLASSE risolta, non il nome scritto: `-k sync` e
#    `-k gunicorn.workers.sync.SyncWorker` sono lo stesso worker.
_WORKER_CON_TETTO = SyncWorker


class SogliaIdempotenzaNonSicura(RuntimeError):
    """Il server web non garantisce che la soglia di ripresa sia sicura."""


# Scopo: Rifiuta la configurazione in cui una richiesta ancora viva potrebbe
#        essere ripresa da un reinvio. Solleva `SogliaIdempotenzaNonSicura`
#        col motivo, o `E_CONFIG_MANCANTE` se la soglia a DB e' rotta.
# ⛔ `timeout_secondi = 0` per gunicorn vuol dire «nessun timeout»: nessun
#    tetto, quindi nessuna soglia e' sicura.
def verifica_soglia_contro_timeout(*, timeout_secondi: int, worker_class: type) -> None:
    if not issubclass(worker_class, _WORKER_CON_TETTO):
        raise SogliaIdempotenzaNonSicura(
            f"gunicorn con worker '{worker_class.__name__}': il timeout non e' il tetto "
            f"di una richiesta, e la ripresa delle Idempotency-Key ({CODICE_SOGLIA}) non "
            "e' sicura. Usare worker 'sync' (guida «Le operazioni che non si ripetono»)."
        )
    if timeout_secondi <= 0:
        raise SogliaIdempotenzaNonSicura(
            "gunicorn senza timeout (0): nessuna richiesta ha un tetto, e la ripresa "
            f"delle Idempotency-Key ({CODICE_SOGLIA}) non e' sicura."
        )
    soglia = ParameterService().get_default_int_positivo(CODICE_SOGLIA)
    if soglia < timeout_secondi + MARGINE_SECONDI:
        raise SogliaIdempotenzaNonSicura(
            f"{CODICE_SOGLIA} = {soglia}s non sta sopra il timeout di gunicorn "
            f"({timeout_secondi}s) di almeno {MARGINE_SECONDI}s: una richiesta ancora "
            "viva potrebbe essere ripresa da un reinvio, ed eseguita due volte. "
            "Alzare la soglia o abbassare il timeout, insieme."
        )
