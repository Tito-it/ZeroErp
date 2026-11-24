# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'utente Django dato il suo id, in un posto solo: `None` se l'id e'
#        `None` (nessuna query) o se l'utente non c'e'. Il rifiuto lo decide il
#        chiamante, col codice del suo dominio: un 404 per l'utente letto da un
#        URL, il blocco del gate prezzi, la validazione del preventivo, l'azienda
#        fallita del giro della coda stampa.
#
# ⭐ Regola del 2 (ok Tid, 2026-11-24): la stessa lettura
#    `get_user_model().objects.get(pk=...)` stava in sette sedi (gate prezzi x2,
#    approvazioni prezzo, componenti, preventivi, permessi effettivi/audit,
#    drenatore della coda stampa, comando di provisioning), ciascuna col suo
#    `except DoesNotExist`. Una passava `pk=None` a Django con un
#    `type: ignore`, contando sul fatto che diventasse `IS NULL`.
# ⛔ Il BB non solleva: un codice d'errore comune a domini diversi sarebbe la
#    risposta sbagliata per almeno uno, e chiederebbe una policy nuova al DB.
#    Unifica la LETTURA, non il rifiuto.
# ------------------------------------------------------------

from __future__ import annotations

from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User


def utente_per_id(auth_user_id: int | None) -> User | None:
    if auth_user_id is None:
        return None
    modello = get_user_model()
    try:
        return cast(User, modello.objects.get(pk=auth_user_id))
    except modello.DoesNotExist:
        return None
