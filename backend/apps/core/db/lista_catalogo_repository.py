# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: lettura minima del CATALOGO delle liste per il cancello di perimetro
#        emittente — le DUE colonne che dicono se una lista ha un perimetro e se
#        lo sa dichiarare (`perimetro_emittente`, `multi_emittente`).
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

from typing import NamedTuple

from django.db import connection


# ⭐ DUE DOMANDE, DUE COLONNE, e vanno lette insieme (§12.1, 2026-09-02):
#
#   `perimetro_emittente`  le righe di questa lista appartengono a un emittente?
#                          — natura del DATO. `false` su un catalogo globale.
#   `multi_emittente`      se ci appartengono, la lista sa dire a quale?
#                          — capacita' conquistata, e certificata.
#
# ⛔ Non e' un enum a tre valori: legarle in un flag solo significa rispondere a
#    due domande in AND, e poi non riuscire piu' a invertirne una. E' la ragione
#    per cui la lista delle famiglie non e' diventata `multi_emittente = true`:
#    avrebbe dichiarato di saper dire un emittente che non esiste, e sarebbe
#    comparsa in `dbops.vw_liste_multi_emittente_non_certificate` — che due
#    pgTAP vogliono vuota.
class FlagPerimetroLista(NamedTuple):
    multi_emittente: bool
    perimetro_emittente: bool


# Scopo: legge le due colonne di perimetro di una lista dal suo codice stabile.
# Risultato: la coppia dal catalogo, oppure None se la lista non esiste o non
#        e' attiva — che il chiamante deve distinguere da «due False».
#
# ⚠️ `None` NON si normalizza qui. Sono due cose diverse: «la lista dichiara di
#        non saper reggere piu' emittenti» (il cancello scatta) e «questa lista
#        non esiste» (None, che e' un errore di configurazione del chiamante —
#        un `lista_codice` scritto male sulla view — e va trattato come tale,
#        non come un divieto).
#
# ⚠️ E i due valori tornano NOMINATI, non in una tupla nuda: sono due booleani
#        adiacenti con significati opposti, e invertirli non solleverebbe
#        niente — aprirebbe una lista che va chiusa, o viceversa.
def fetch_flag_perimetro(lista_codice: str) -> FlagPerimetroLista | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT multi_emittente, perimetro_emittente "
            "FROM ui.lista_definizione "
            "WHERE codice = %s AND attivo = TRUE",
            [lista_codice],
        )
        row = cursor.fetchone()
    if not row:
        return None
    return FlagPerimetroLista(multi_emittente=bool(row[0]), perimetro_emittente=bool(row[1]))
