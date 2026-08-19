# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: lettura minima del CATALOGO delle liste per il cancello di perimetro
#        emittente — oggi una colonna sola, `ui.lista_definizione.multi_emittente`.
#
# ⚠️ Perche' sta in `apps/core/db/` e non in `apps/ui/db/`, dove il catalogo
#        delle liste ha la sua sede naturale: il consumatore e'
#        `DomainAPIView` (`apps/core/api/base_views.py`), e **`core` non puo'
#        importare `ui`** — la direzione degli anelli ammette dominio → ui
#        (i domini importano gia' `ui.api.export_helpers`), non il contrario.
#        Un import core → ui legherebbe la base view di TUTTI gli endpoint a
#        un'app di presentazione.
#        La dipendenza che resta e' verso lo **schema DB**, non verso il codice
#        Python: e' la stessa che `lookup_repository` ha su nove schemi.
#
# ⚠️ Non duplica `UiRepository.resolve_lista_config`, che risolve la CASCATA
#        completa (preferenza/preset/catalogo + merge colonne + permessi) ed e'
#        molto piu' cara: qui serve un solo booleano, e serve **prima** di
#        servire i dati, non per costruire una schermata.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


# Scopo: legge il flag `multi_emittente` di una lista dal suo codice stabile.
# Risultato: True/False dal catalogo, oppure None se la lista non esiste o non
#        e' attiva — che il chiamante deve distinguere da False.
#
# ⚠️ `None` NON si normalizza a False qui. Sono due cose diverse: «la lista
#        dichiara di non saper reggere piu' emittenti» (False, il cancello
#        scatta) e «questa lista non esiste» (None, che e' un errore di
#        configurazione del chiamante — un `lista_codice` scritto male sulla
#        view — e va trattato come tale, non come un divieto).
def fetch_multi_emittente(lista_codice: str) -> bool | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT multi_emittente FROM ui.lista_definizione "
            "WHERE codice = %s AND attivo = TRUE",
            [lista_codice],
        )
        row = cursor.fetchone()
    if not row:
        return None
    return bool(row[0])
