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
# ⭐ DUE LIVELLI (lotto C, 2026-09-28). `RigheListaMixin` e' la lettura: la
#    lista paginata e la lettura completa, su una vista qualunque che porti le
#    righe di UN documento. `RigheDocumentoRepositoryMixin` ci aggiunge cio'
#    che vale per le righe che stanno in una TABELLA con `id` e `attivo`
#    (preventivo, ordine, DDT, reso): riga singola e conteggio. La fattura usa
#    solo il primo: le sue righe di lista vengono da `vw_fattura_righe_lista`,
#    dove il padre di un kit non ha un `id` e la chiave e' `riga_key`, e non
#    c'e' `attivo` da filtrare.
#
# ⭐ LA SORGENTE PUO' ESSERE UNA FUNZIONE (lotto D, 2026-09-30). Le righe del
#    contratto non stanno in una vista: le calcola
#    `vendite.fn_contratto_righe_preview(contratto)` (listino + eccezioni), e la
#    lista 103 ha `vista_sql` NULL. Con `_righe_funzione` il BB legge da
#    `fn(documento) v`: la funzione e' gia' del documento, quindi niente FK da
#    filtrare. Il resto — ricerca, ordinamento, pagina, totale — e' lo stesso.
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
    jsonb_out,
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


class RigheListaMixin:
    """Building block della LETTURA delle righe di un documento da una vista:
    la pagina della lista configurabile e la lettura completa.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_righe_vista``: nome FQN della vista (``"vendite.vw_ordini_righe_dettaglio"``);
    - ``_righe_fk_documento``: colonna FK al documento (``"ordine_id"``);
    - ``_righe_ordine_documento``: l'ordine del DOCUMENTO, colonna di
      posizione (``"riga_nr"``; ``"ordine"`` sul preventivo). E' l'ordine di
      partenza della lista e quello della lettura completa;
    - ``_righe_ordinamento``: whitelist `campo_sorgente -> colonna` delle
      colonne `ordinabile = t` della lista a catalogo;
    - ``_righe_ricerca``: la `RicercaFull` della lista a catalogo.

    E possono ridefinire:

    - ``_righe_colonne_desc``: chiavi della whitelist che partono DESC (le
      date, regola di Tid del 2026-09-02). Default nessuna;
    - ``_righe_chiave``: la colonna che identifica la riga, spareggio di ogni
      ordinamento (default ``"id"``; ``"riga_key"`` sulla fattura);
    - ``_righe_solo_attive``: filtra ``attivo IS TRUE`` (default ``True``; la
      vista delle righe di fattura non ha `attivo`);
    - ``_righe_ordine_documento_extra``: colonne che seguono
      ``_righe_ordine_documento`` nell'ordine del documento, sempre crescenti
      (default nessuna; ``("riga_nr",)`` sulla fattura, dove l'ordine e'
      ``ordinamento, riga_nr``);
    - ``_righe_funzione``: nome FQN di una funzione ``fn(documento_id)`` che
      restituisce le righe del documento, al posto di ``_righe_vista`` e
      ``_righe_fk_documento`` (default ``None``; il contratto:
      ``"vendite.fn_contratto_righe_preview"``).
    - ``_righe_jsonb``: colonne jsonb della sorgente, consegnate DECODIFICATE
      (default nessuna; ``("componenti",)`` sulla fattura). Fuori dall'ORM il
      cursor le rende come testo: una lista consegnata come stringa la
      scorre un carattere alla volta chi la legge — il drawer fattura
      disegnava una riga per carattere sotto un kit (2026-10-01).
    """

    _righe_vista: str
    _righe_funzione: str | None = None
    _righe_fk_documento: str
    _righe_ordine_documento: str
    _righe_ordinamento: Mapping[str, str]
    _righe_ricerca: RicercaFull
    _righe_colonne_desc: Collection[str] = ()
    _righe_chiave: str = "id"
    _righe_solo_attive: bool = True
    _righe_ordine_documento_extra: tuple[str, ...] = ()
    _righe_jsonb: tuple[str, ...] = ()

    # Scopo: una sorgente sola per classe. Vista e funzione insieme non si
    #        rifiutano da sole: vincerebbe la funzione in silenzio, e la vista
    #        dichiarata sarebbe una bugia per chi legge la classe.
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls._righe_funzione is not None and "_righe_vista" in vars(cls):
            raise TypeError(
                f"{cls.__name__}: `_righe_vista` e `_righe_funzione` sono "
                "alternative, se ne dichiara una sola"
            )

    # Scopo: le chiavi ordinabili della lista, per chi le deve DIRE (la doc
    #        OpenAPI della view). Una sede: la whitelist che il BB applica.
    @classmethod
    def righe_colonne_ordinabili(cls) -> tuple[str, ...]:
        return tuple(cls._righe_ordinamento)

    # Scopo: l'ordine di partenza della lista, per chi lo deve DIRE (la doc
    #        OpenAPI della view), letto dagli attributi con cui il BB ordina:
    #        una frase ricopiata a mano accanto divergerebbe al primo cambio.
    @classmethod
    def righe_ordine_di_partenza(cls) -> str:
        colonne = (cls._righe_ordine_documento, *cls._righe_ordine_documento_extra, cls._righe_chiave)
        return ", ".join(f"`{c}`" for c in colonne) + "."

    # Scopo: la sorgente comune alle due letture: il `FROM` (alias `v`), le
    #        condizioni che la restringono al documento e alle sole righe
    #        attive dove la sorgente le distingue, e i loro parametri. Una
    #        funzione del documento e' gia' ristretta: nessuna condizione sua.
    #        Ritorna (from_sql, condizioni, params).
    def _righe_da(self, documento_id: int) -> tuple[str, list[str], list[Any]]:
        if self._righe_funzione is not None:
            from_sql, conditions = f"{self._righe_funzione}(%s) v", []
        else:
            from_sql = f"{self._righe_vista} v"
            conditions = [f"v.{self._righe_fk_documento} = %s"]
        if self._righe_solo_attive:
            conditions.append("v.attivo IS TRUE")
        return from_sql, conditions, [documento_id]

    # Scopo: la clausola WHERE di un elenco di condizioni, anche vuoto.
    @staticmethod
    def _righe_where(conditions: list[str]) -> str:
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Scopo: l'ordine del DOCUMENTO come elenco di colonne qualificate
    #        (`v.ordinamento, v.riga_nr`), per la lettura completa.
    def _righe_ordine_documento_sql(self) -> str:
        colonne = (self._righe_ordine_documento, *self._righe_ordine_documento_extra)
        return ", ".join(f"v.{c}" for c in colonne)

    # Scopo: TUTTE le righe del documento, nell'ordine del documento.
    #        Per chi le usa tutte insieme: i generatori di stampa,
    #        i dialog di evasione e riconsegna (che mostrano anche le righe
    #        chiuse, come consuntivo). ⛔ Non e' la lista a video: quella e'
    #        `list_righe_pagina`.
    def list_righe(self, documento_id: int) -> list[dict[str, Any]]:
        from_sql, conditions, params = self._righe_da(documento_id)
        sql = f"""
            SELECT v.*
              FROM {from_sql}
             {self._righe_where(conditions)}
             ORDER BY {self._righe_ordine_documento_sql()}, v.{self._righe_chiave}
        """  # noqa: S608 — sorgente, FK e colonne d'ordine sono attributi di classe costanti; valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return self._decodifica_jsonb(rows_to_list(cursor))

    # Scopo: le colonne `_righe_jsonb` da testo a oggetto, NULL compreso
    #        (`jsonb_out`: un JSON rotto esplode, il tipo della colonna lo
    #        garantisce). Una sede per la lettura completa e per la pagina.
    def _decodifica_jsonb(self, righe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for riga in righe:
            for colonna in self._righe_jsonb:
                if colonna in riga:
                    riga[colonna] = jsonb_out(riga[colonna])
        return righe

    # Scopo: una PAGINA delle righe del documento, per la lista
    #        configurabile: ricerca libera dal catalogo, ordinamento dalla
    #        whitelist, ordine del documento quando nessuno chiede altro.
    #        Ritorna `(righe, totale)`; il totale e' un COUNT indipendente
    #        dalle righe consegnate (api.md §«Il `count` non si deriva MAI
    #        dalle righe che stai consegnando»).
    # ⚠️ `max_limit`: la lista resta al cap standard (`MAX_LIMIT`, fonte
    #    unica in core); l'export passa il suo tetto
    #    (EXPORT_MAX_ROWS + 1) per accorgersi di un file troncato.
    # ⭐ L'ordine del documento a piu' colonne (fattura: `ordinamento,
    #    riga_nr`): la prima e' il default del BB e prende il verso; le altre
    #    entrano nello spareggio, prima della chiave, e restano CRESCENTI (il
    #    BB mette il verso solo in coda). E' voluto: `riga_nr` e' la posizione
    #    DENTRO un gruppo di `ordinamento` (la capofila e le sue parti di
    #    plafond), che si legge in avanti qualunque sia il verso della lista.
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
            tiebreak=", ".join(
                [f"v.{c}" for c in self._righe_ordine_documento_extra]
                + [f"v.{self._righe_chiave}"]
            ),
            colonne_desc=self._righe_colonne_desc,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)
        from_sql, conditions, params = self._righe_da(documento_id)
        add_ricerca_full_condition(conditions, params, search, self._righe_ricerca)
        from_where = f"FROM {from_sql} {self._righe_where(conditions)}"
        righe, totale = fetch_paged_with_total(
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
        return self._decodifica_jsonb(righe), totale


class RigheDocumentoRepositoryMixin(RigheListaMixin):
    """Le righe di un documento che stanno in una TABELLA con `id` e `attivo`
    (preventivo, ordine, DDT, reso): alla lettura di `RigheListaMixin` aggiunge
    la riga singola e il conteggio.

    In piu' degli attributi di `RigheListaMixin`, le sottoclassi definiscono:

    - ``_righe_tabella``: nome FQN della tabella delle righe
      (``"vendite.ordini_righe"``): solo per il CONTEGGIO, vedi `count_righe`.
    """

    _righe_tabella: str

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
