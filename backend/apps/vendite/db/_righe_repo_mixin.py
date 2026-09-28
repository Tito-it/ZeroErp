# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per la lettura delle RIGHE di un documento
#        di vendita dalla sua vista `vw_<doc>_righe_dettaglio`: la lista
#        paginata (lista configurabile), la lettura completa (chi ha bisogno
#        di tutte le righe), la riga singola e il conteggio.
#        Estrazione regola-del-2 (brief-db-liste-righe-documento, lotto A,
#        2026-09-28): preventivo, ordine, DDT e reso avevano ciascuno la sua
#        query, e tre di esse proiettavano a mano in Python le stesse colonne
#        che la vista ora porta (D-8.6: la vista E' la sorgente). Sulla stessa
#        forma dei mixin gemelli (`RiepilogoIvaRepositoryMixin`,
#        `ComponentiRepositoryMixin`).
#
# ⭐ LE VISTE NON FILTRANO E NON ORDINANO (per progetto: `COMMENT` delle
#    viste). Il filtro `attivo IS TRUE` e l'ordine del documento li mette
#    questo BB, in un punto solo per le tre letture: prima ogni query li
#    riscriveva, e la riga singola non filtrava affatto.
#
# ⚠️ Scope emittente: le viste sono `security_invoker` e le tabelle in RLS;
#    la testata la verifica il service prima di leggere le righe («leggi
#    prima la testata»: fuori perimetro e' un 404, non una lista vuota).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from django.db import connection

from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    colonne_identita,
    fetch_paged_with_total,
    fetchone_scalar,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)

# ⭐ Le colonne ordinabili GEMELLE delle righe commerciali (preventivo, ordine,
#    DDT: liste 97-99, «stessi codici, etichette e priorita'», §3.2 del brief).
#    Una dichiarazione sola perche' e' un significato solo: tre whitelist
#    scritte a parte divergerebbero alla prima colonna aggiunta. Ogni
#    documento aggiunge le SUE date di consegna (il DDT non ne ha).
#    Le chiavi sono i `campo_sorgente` del catalogo, e le viste le espongono
#    con lo stesso nome: identita'.
COLONNE_RIGHE_COMMERCIALI: dict[str, str] = colonne_identita(
    "articolo_codice", "descrizione", "qta_operativa", "importo_riga",
    "prezzo_unitario", "uom_codice", "sconto_percentuale", "iva_descrizione",
)
# Le colonne di ricerca gemelle (le `ricercabile_full = t` delle liste 97-99).
RICERCA_RIGHE_COMMERCIALI: tuple[str, ...] = ("articolo_codice", "descrizione")


class RigheDocumentoRepositoryMixin:
    """Building block lettura righe per repository documento.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_righe_vista``: nome FQN della vista (``"vendite.vw_ordini_righe_dettaglio"``);
    - ``_righe_tabella``: nome FQN della tabella delle righe
      (``"vendite.ordini_righe"``): solo per il CONTEGGIO, vedi `count_righe`;
    - ``_righe_fk_documento``: colonna FK al documento (``"ordine_id"``);
    - ``_righe_ordine_documento``: l'ordine del DOCUMENTO, colonna di
      posizione (``"riga_nr"``; ``"ordine"`` sul preventivo). E' l'ordine di
      partenza della lista e quello della lettura completa;
    - ``_righe_ordinamento``: whitelist `campo_sorgente -> colonna` delle
      colonne `ordinabile = t` della lista a catalogo;
    - ``_righe_ricerca``: la `RicercaFull` della lista a catalogo;
    - ``_righe_colonne_desc``: chiavi della whitelist che partono DESC (le
      date, regola di Tid del 2026-09-02). Default nessuna.
    """

    _righe_vista: str
    _righe_tabella: str
    _righe_fk_documento: str
    _righe_ordine_documento: str
    _righe_ordinamento: Mapping[str, str]
    _righe_ricerca: RicercaFull
    _righe_colonne_desc: Collection[str] = ()

    # Scopo: le chiavi ordinabili della lista, per chi le deve DIRE (la doc
    #        OpenAPI della view). Una sede: la whitelist che il BB applica.
    @classmethod
    def righe_colonne_ordinabili(cls) -> tuple[str, ...]:
        return tuple(cls._righe_ordinamento)

    # Scopo: QUANTE righe attive ha il documento: il `righe_count` del
    #        dettaglio e i guard «senza righe» (elimina, conferma).
    #        ⭐ Una sede per una domanda: fino al 2026-09-28 era scritta in tre
    #        forme — `count_righe` (DDT, reso), `count_righe_attive`
    #        (preventivo) e `len(list_righe(...))` (ordine, e l'elimina di DDT
    #        e preventivo), cioe' leggere la vista intera per contarla.
    # ⚠️ Sulla TABELLA e non sulla vista: la vista porta decodifiche e
    #    calcolati per riga (quella del reso chiama tre funzioni per riga), che
    #    a un conteggio non servono. Il perimetro non cambia: chi chiama ha gia'
    #    letto la testata («leggi prima la testata»), e il filtro e' lo stesso
    #    `attivo IS TRUE` delle letture.
    def count_righe(self, documento_id: int) -> int:
        sql = f"""
            SELECT COUNT(*)
              FROM {self._righe_tabella}
             WHERE {self._righe_fk_documento} = %s
               AND attivo IS TRUE
        """  # noqa: S608 — tabella e FK sono attributi di classe costanti; valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return int(fetchone_scalar(cursor))

    # Scopo: TUTTE le righe attive del documento, nell'ordine del documento.
    #        Per chi le usa tutte insieme: i generatori di stampa,
    #        i dialog di evasione e riconsegna (che mostrano anche le righe
    #        chiuse, come consuntivo). ⛔ Non e' la lista a video: quella e'
    #        `list_righe_pagina`.
    def list_righe(self, documento_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT v.*
              FROM {self._righe_vista} v
             WHERE v.{self._righe_fk_documento} = %s
               AND v.attivo IS TRUE
             ORDER BY v.{self._righe_ordine_documento}, v.id
        """  # noqa: S608 — vista, FK e colonna d'ordine sono attributi di classe costanti; valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return rows_to_list(cursor)

    # Scopo: una riga attiva per id, con la stessa proiezione della lista.
    #        ⭐ Prima ogni repository la rifaceva a mano, e due su quattro
    #        mancavano di colonne che la lista aveva (evaso e residuo
    #        sull'ordine, importo sul DDT).
    def get_riga(self, riga_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT v.*
              FROM {self._righe_vista} v
             WHERE v.id = %s
               AND v.attivo IS TRUE
        """  # noqa: S608 — vista costante di classe; valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return row_to_dict(cursor)

    # Scopo: una PAGINA delle righe attive del documento, per la lista
    #        configurabile: ricerca libera dal catalogo, ordinamento dalla
    #        whitelist, ordine del documento quando nessuno chiede altro.
    #        Ritorna `(righe, totale)`; il totale e' un COUNT indipendente
    #        dalle righe consegnate (api.md §«Il `count` non si deriva MAI
    #        dalle righe che stai consegnando»).
    # ⚠️ `max_limit`: la lista resta al cap standard (`MAX_LIMIT`, fonte
    #    unica in core); l'export passa il suo tetto
    #    (EXPORT_MAX_ROWS + 1) per accorgersi di un file troncato.
    def list_righe_pagina(
        self,
        documento_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int = 0,
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=self._righe_ordinamento,
            default=f"v.{self._righe_ordine_documento}",
            tiebreak="v.id",
            colonne_desc=self._righe_colonne_desc,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)
        conditions = [f"v.{self._righe_fk_documento} = %s", "v.attivo IS TRUE"]
        params: list[Any] = [documento_id]
        add_ricerca_full_condition(conditions, params, search, self._righe_ricerca)
        from_where = f"FROM {self._righe_vista} v WHERE {' AND '.join(conditions)}"
        return fetch_paged_with_total(
            f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali e dal BB della ricerca, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )
