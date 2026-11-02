# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La configurazione che gunicorn carica da solo dalla directory di
#        lavoro (`backend/` per `bin/start-gunicorn.sh`, `/app` nel
#        Dockerfile). Porta i presidi di avvio: un backend configurato in modo
#        non sicuro non parte.
# Note: ⚠️ Bind, worker e timeout restano dove sono (riga di comando dei due
#       lanciatori): qui solo i controlli, che leggono i valori EFFETTIVI.
# ------------------------------------------------------------

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# La directory di `manage.py`, la stessa di questo file (`backend/`, `/app`).
_BACKEND = Path(__file__).resolve().parent


# Scopo: Prima di creare i worker, verifica che il timeout stia sotto la soglia
#        di ripresa delle Idempotency-Key (BE-5, `soglia_idempotenza`), in un
#        processo FIGLIO usa e getta (`manage.py verifica_presidi_avvio`).
# ⛔ Mai `django.setup()` qui (brief-modello-documento-vendita §15.17.3, ok di
#    Tid 2026-10-31): fino ad allora il master caricava Django e i moduli
#    dell'applicazione, i worker nati da un `kill -HUP` li ereditavano, e il
#    codice nuovo non entrava. Il master resta senza codice applicativo, e un
#    HUP torna a caricare tutto da capo.
# ⭐ La modalita' forte spenta la giudica il figlio, che legge i settings.
def _verifica_presidi(server: Any) -> None:
    worker_class = server.cfg.worker_class
    env = {**os.environ}
    env.setdefault("DJANGO_SETTINGS_MODULE", "zeroerp_backend.settings")
    esito = subprocess.run(  # noqa: S603 — argomenti nostri, nessun input esterno
        [
            sys.executable, str(_BACKEND / "manage.py"), "verifica_presidi_avvio",
            "--timeout", str(int(server.cfg.timeout)),
            "--worker-class", f"{worker_class.__module__}.{worker_class.__qualname__}",
        ],
        cwd=_BACKEND, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    if esito.returncode != 0:
        # L'ultima riga di stderr e' l'errore (CommandError o la coda di un
        # traceback); sopra ci sono i log dell'avvio di Django nel figlio.
        righe = esito.stderr.strip().splitlines()
        raise RuntimeError(
            "Presidi di avvio non superati: "
            + (righe[-1] if righe else f"uscita {esito.returncode}")
        )


# Scopo: All'avvio del master: un rifiuto e' un backend che non parte.
def on_starting(server: Any) -> None:
    _verifica_presidi(server)


# Scopo: Al `kill -HUP`: gunicorn rilegge la configurazione (timeout e worker
#        compresi) e chiama questo hook PRIMA di creare i worker nuovi.
# ⛔ Senza, un timeout alzato e ricaricato con un HUP passava il presidio, che
#    girava solo al primo avvio. Un rifiuto qui ferma il master (gunicorn
#    chiude sulle eccezioni del suo ciclo): la stessa regola dell'avvio, perche'
#    la configurazione che ne uscirebbe e' quella non sicura.
def on_reload(server: Any) -> None:
    _verifica_presidi(server)
