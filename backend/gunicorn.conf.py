# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
from typing import Any


# Scopo: Prima di creare i worker, verifica che il timeout stia sotto la soglia
#        di ripresa delle Idempotency-Key (BE-5, `soglia_idempotenza`).
# ⭐ Vale solo con la modalita' forte accesa: spenta, la funzione che legge la
#    soglia non viene mai chiamata.
# ⚠️ La connessione aperta per leggere la soglia si chiude prima del fork: un
#    socket ereditato dai worker sarebbe condiviso fra processi.
def _verifica_presidi(server: Any) -> None:
    import django

    # Lo stesso modulo di `zeroerp_backend/wsgi.py`, che qui non e' ancora
    # stato importato. `django.setup()` e' idempotente: al reload non rifa' niente.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zeroerp_backend.settings")
    django.setup()
    from django.conf import settings
    from django.db import connections

    from apps.core.services.soglia_idempotenza import verifica_soglia_contro_timeout

    if not getattr(settings, "API_STRONG_IDEMPOTENCY_ENABLED", False):
        return
    try:
        verifica_soglia_contro_timeout(
            timeout_secondi=int(server.cfg.timeout),
            worker_class=server.cfg.worker_class,
        )
    finally:
        connections.close_all()


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
