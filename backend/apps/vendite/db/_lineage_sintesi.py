# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le colonne del grafo (frontiera, discendenti, transito, radice…) per le
#        righe di una lista documento, lette da
#        `vendite.fn_documento_lineage_sintesi` per le SOLE chiavi delle righe
#        e unite riga per riga. Sede unica per le sette liste documento e, per
#        costruzione, per il loro export (che chiama gli stessi metodi di
#        repository con `limit=EXPORT_MAX_ROWS + 1`).
# ------------------------------------------------------------

# PERCHE' ESISTE (brief-db-lineage-seminata-per-chiave §8.1, B1, 2026-10-11).
# Fino al `20261011-97` le sette viste di lista portavano le 8 colonne del
# grafo, e le portavano calcolando la lineage di TUTTI i documenti del sistema
# a ogni pagina. Il DB le ha tolte dalle viste: ora la pagina si legge senza,
# e le colonne del grafo arrivano DOPO la paginazione, per le chiavi della
# pagina (o, nell'export, di tutte le righe, a blocchi — D-B3).
#
# ⭐ Quali colonne vengono dalla sintesi lo dice la regola D-B2, applicata qui
#    sulla STRUTTURA e non su un elenco: tutte le colonne della sintesi che la
#    riga della vista NON ha. Nessun nome di colonna e' scritto in questo file:
#    una colonna nuova della sintesi arriva alle liste senza toccare il backend,
#    e una colonna che la vista torna a esporre vince sulla sintesi (la vista e'
#    la riga, la sintesi la completa).
# ⚠️ La coppia `(tipo_id, uid)` e' la CHIAVE del nodo, non un dato: non si
#    unisce. Su ordini, contratti, DDT, resi e fatture `uid` e' l'`id` reso a
#    testo, e scriverlo nella riga come `uid` direbbe una cosa falsa.
# ⚠️ Quale campo della riga e' la chiave del nodo lo dice `config.sorgenti.
#    key_selector` (`uid` per preventivi e offerte, `id` per gli altri): la
#    convenzione del grafo, letta (`SorgentiRepository`) e non ricopiata.
# ⛔ Una riga che la sintesi non restituisce ha comunque TUTTE le colonne, a
#    NULL: la forma della riga non dipende dal contenuto, e l'export e il chip
#    leggono chiavi che ci sono sempre.

from typing import Any

from django.db import connection

from apps.config.db.sorgenti_repository import SorgentiRepository
from apps.core.db._helpers import rows_to_list

# Le colonne-chiave del nodo nel risultato della sintesi: servono all'unione,
# non vanno nella riga.
_CHIAVE_NODO: frozenset[str] = frozenset({"tipo_id", "uid"})

# Ampiezza di un blocco di chiavi per chiamata (D-B3): una pagina a video sta
# in un blocco; l'export (fino a EXPORT_MAX_ROWS) ne fa piu' d'uno.
BLOCCO_SINTESI = 500


# Scopo: Completa in place le righe di una lista documento con le colonne della
#        sintesi lineage che la riga non ha.
# Perimetro: `tipo_codice_interno` e' il tipo del documento nel grafo
#        (`config.sorgenti.codice_interno`: PREVENTIVO, OFFERTA_COMMERCIALE,
#        ORDINE_VENDITA, CONTRATTO, DDT_VENDITA, RESO_VENDITA, FATTURA).
#        Sola lettura; la sintesi e' SECURITY INVOKER, quindi la RLS del
#        chiamante vale anche qui.
# Risultato atteso: niente (come `list.sort`): le righe si completano IN PLACE,
#        stesso oggetto e stesso ordine, ognuna con le colonne della sintesi in
#        piu'. Zero righe = zero chiamate.
def unisci_sintesi_lineage(
    righe: list[dict[str, Any]], *, tipo_codice_interno: str
) -> None:
    if not righe:
        return

    sorgente = SorgentiRepository().get_sorgente_attiva(tipo_codice_interno)
    if sorgente is None:
        # Seed di config.sorgenti incoerente col codice: errore di
        # programmazione, non un caso da far passare con le colonne vuote.
        raise ValueError(f"sorgente lineage non configurata: {tipo_codice_interno!r}")
    tipo_id = sorgente["id"]
    campo_chiave = sorgente["key_selector"]

    chiavi = [str(riga[campo_chiave]) for riga in righe]

    sintesi: dict[str, dict[str, Any]] = {}
    colonne: list[str] = []
    with connection.cursor() as cursor:
        for inizio in range(0, len(chiavi), BLOCCO_SINTESI):
            blocco = chiavi[inizio:inizio + BLOCCO_SINTESI]
            cursor.execute(
                """
                SELECT l.*
                  FROM vendite.fn_documento_lineage_sintesi(%s::bigint[], %s::text[]) l
                """,
                [[tipo_id] * len(blocco), blocco],
            )
            colonne = [c.name for c in cursor.description]
            for letto in rows_to_list(cursor):
                sintesi[str(letto["uid"])] = letto

    for riga, chiave in zip(righe, chiavi, strict=True):
        nodo = sintesi.get(chiave)
        for colonna in colonne:
            if colonna in _CHIAVE_NODO or colonna in riga:
                continue
            riga[colonna] = None if nodo is None else nodo[colonna]
