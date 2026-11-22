# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: lettura minima del CATALOGO delle liste per le due cose che la base
#        view decide prima di servire i dati: il cancello di perimetro emittente
#        (le DUE colonne che dicono se una lista ha un perimetro e se lo sa
#        dichiarare, `perimetro_emittente` e `multi_emittente`) e l'ordinamento
#        di partenza (`fetch_ordinamento_lista`, BE25 (2) di brief-db-revisione-ui) e la misura
#        di partenza (`fetch_misura_lista`, BE10).
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

from apps.core.db._helpers import fetchone_scalar, jsonb_out


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


# Scopo: legge le due colonne di perimetro di una lista dal suo codice stabile,
#        dal BB del DB `ui.fn_lista_da_codice` (U39 di brief-db-revisione-ui,
#        Q23): «lista accesa per codice» ha una sede sola.
# Risultato: la coppia dal catalogo. Lista assente o spenta: 404
#        `E_UI_LISTA_NON_TROVATA` dal BB, che si propaga — e' un `lista_codice`
#        scritto male sulla view, un errore di configurazione del chiamante, e
#        NON va confuso con «due False» (il cancello che scatta).
#
# ⚠️ E i due valori tornano NOMINATI, non in una tupla nuda: sono due booleani
#        adiacenti con significati opposti, e invertirli non solleverebbe
#        niente — aprirebbe una lista che va chiusa, o viceversa.
# ⚠️ `SELECT … FROM`: `SELECT ui.fn_lista_da_codice(…)` da' la riga intera come
#        una tupla in un campo solo.
def fetch_flag_perimetro(lista_codice: str) -> FlagPerimetroLista:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT multi_emittente, perimetro_emittente "
            "FROM ui.fn_lista_da_codice(%s)",
            [lista_codice],
        )
        row = cursor.fetchone()
    # La funzione restituisce una riga o solleva: una riga mancante e' un
    # contratto del DB cambiato, non un caso da gestire.
    assert row is not None
    return FlagPerimetroLista(multi_emittente=bool(row[0]), perimetro_emittente=bool(row[1]))


# Scopo: l'ordinamento di partenza di una lista per un utente, come lo risolve il
#        DB: `ui.fn_ordinamento_lista` (giro 2 di brief-db-revisione-ui), la sola
#        sede dell'ordinamento risolto — quello del preset di base, senza le voci
#        delle colonne che l'utente non puo' ordinare, ognuna col suo campo
#        sorgente. Ritorna l'elenco `[{col, dir, campo_sorgente}]`, vuoto se il
#        preset non ne dichiara (o non c'e' un preset di base).
# ⚠️ Sta qui per la stessa ragione di `fetch_flag_perimetro`: la legge
#    `DomainAPIView`, e `core` non importa `ui`.
# ⚠️ Lista assente o spenta: `E_UI_LISTA_NON_TROVATA` dal BB del DB, che si
#    propaga — e' un errore di dichiarazione della view, non un ripiego.
def fetch_ordinamento_lista(
    lista_codice: str, *, auth_user_id: int, emittente_fiscale_id: int | None,
) -> list[dict[str, str]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ui.fn_ordinamento_lista(%s, %s, %s)",
            [lista_codice, auth_user_id, emittente_fiscale_id],
        )
        row = cursor.fetchone()
    voci = jsonb_out(row[0]) if row and row[0] is not None else []
    return list(voci) if isinstance(voci, list) else []


# Scopo: quante righe per pagina mostra una lista a un utente, come lo risolve
#        il DB: `ui.fn_misura_lista` (BE10 di brief-db-revisione-ui, giro 6a),
#        gemella di `ui.fn_ordinamento_lista` e con la stessa regola della
#        configurazione della lista (`ui.fn_misura_pagina_risolta`: preferenza,
#        preset di base, default dell'uso). Mai `NULL`.
# ⚠️ Lista assente o spenta: `E_UI_LISTA_NON_TROVATA` dal BB del DB, che si
#    propaga, come per l'ordinamento.
def fetch_misura_lista(
    lista_codice: str, *, auth_user_id: int, emittente_fiscale_id: int | None,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ui.fn_misura_lista(%s, %s, %s)",
            [lista_codice, auth_user_id, emittente_fiscale_id],
        )
        return int(fetchone_scalar(cursor))
