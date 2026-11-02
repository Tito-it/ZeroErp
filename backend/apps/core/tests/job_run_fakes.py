# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `registered_job` finto per i test dei management command.
# Note: Modulo di supporto ai test, non un modulo di test: il nome non comincia
#       per `test` apposta, cosi' il runner non lo raccoglie.
# ------------------------------------------------------------

"""Perche' esiste, ed e' un difetto misurato — non igiene.

`registered_job` scrive DAVVERO su `maintenance.job_run_log`: apre la riga con
`fn_job_run_start` e la chiude con `fn_job_run_end`. Un test che esegue un
command senza sostituirlo lascia quindi righe **vere** nel giornale dei run — e
un test che prova il percorso d'errore ci lascia una riga **rossa**.

⛔ Misurato il 2026-09-05: `sync_auth_user_active` aveva **93 corse OK e 31
fallite in un giorno**, tutte del test suite. Finche' un fallimento non lasciava
traccia (`fn_run_and_log` scriveva e il `RAISE` faceva rollback) nessuno se ne
accorgeva; dal changeSet `20260905-36` la traccia resta, e quelle 31 righe hanno
acceso `maintenance.vw_job_run_da_guardare` — un presidio che DEVE restare vuoto.

⭐ Il punto non e' che il presidio sia rumoroso: e' che un presidio sempre acceso
smette di essere letto, e il giorno in cui un job fallira' DAVVERO nessuno
distinguera' la sua riga dal rumore dei test. E' lo stesso difetto che il team DB
ha chiuso con DB-2 sulle viste dei processi, ricomparso su una vista appena nata
e per mano nostra.

⚠️ Il precedente giusto c'era gia': `test_run_fatturazione_batch_command` lo
sostituisce da sempre. Questo modulo e' quella stessa forma, in un posto solo —
seconda occorrenza, quindi si estrae invece di ricopiarla.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock


# Scopo: un `registered_job` sostitutivo che NON tocca il database, piu' il
#        manico su cui il test puo' asserire (`set_meta`, `set_rows_affected`)
#        e gli argomenti con cui il command si e' registrato.
#
# ⚠️ `acquired` e' il pezzo che serve ai command con anti-overlap: a `False` il
#    corpo va saltato, ed e' il ramo «un altro giro e' gia' in corso».
#
# Ritorna: `(context_manager, handle, catturato)` — `catturato` si riempie alla
#          chiamata con `{"job_id": ..., "kwargs": {...}}`, cosi' un test puo'
#          provare CHE COSA il command ha dichiarato (per esempio il
#          `processo_codice`) senza scrivere sul giornale vero.
def fake_registered_job(*, acquired: bool = True):
    handle = MagicMock()
    handle.acquired = acquired
    catturato: dict = {}

    @contextmanager
    def _cm(job_id=None, **kwargs):
        catturato["job_id"] = job_id
        catturato["kwargs"] = kwargs
        yield handle

    return _cm, handle, catturato


# Scopo: la forma per chi NON deve asserire sulla registrazione — la maggioranza
#        dei test di command, a cui serve solo che il giornale non venga scritto.
#        Ritorna il solo context manager, pronto per `@patch(..., new=...)`.
#
# ⛔ Esiste perche' l'alternativa era `fake_registered_job()[0]`, che butta via
#    handle e catturato: un indice nudo in un decoratore non dice a chi legge che
#    quei due pezzi ESISTONO e che qui non servono. Due nomi, due intenzioni.
# ⚠️ Ogni chiamata costruisce un manico NUOVO. Condividerne uno fra piu' test
#    farebbe accumulare le chiamate registrate sul mock, e il secondo test
#    vedrebbe le tracce del primo: si condivide una FABBRICA, non un oggetto con
#    stato.
def registered_job_muto(*, acquired: bool = True):
    return fake_registered_job(acquired=acquired)[0]
