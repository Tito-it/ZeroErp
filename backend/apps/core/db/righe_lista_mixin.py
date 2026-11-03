# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per la LETTURA delle righe di un padre —
#        le righe di un documento di vendita, la distinta di un articolo —
#        da una vista o da una funzione del padre: la PAGINA della lista
#        configurabile e, per chi ne ha bisogno, la lettura COMPLETA.
#        Nato in `vendite/db/_righe_repo_mixin.py` (brief-db-liste-righe-
#        documento, lotto A, 2026-09-28) per preventivo, ordine, DDT e reso.
#        ⭐ Portato in core il 2026-10-04 (regola del 2 fra domini, ok Tid,
#        §9.16 del brief): `CatalogoBomRepository` ne rifaceva a mano la
#        lettura paginata (vista, ricerca, whitelist, spareggio,
#        `fetch_paged_with_total`) e la lettura completa. Restano in vendite
#        le dichiarazioni che sono di quel dominio (colonne gemelle delle
#        righe commerciali, riga singola e conteggio sulla tabella).
#
# ⭐ DUE LIVELLI, e la ragione e' un consumatore che non deve avere tutto.
#    `RigheListaMixin` e' la sola PAGINA; `RigheListaCompletaMixin` ci
#    aggiunge la lettura completa (`list_righe`). Il contratto prende solo il
#    primo: la sua lettura completa e' `ContrattiRepository.list_righe_preview`
#    (stampa, conteggio), e una seconda ereditata dal BB era codice senza
#    consumatori (§9.10).
#
# ⭐ LE VISTE NON FILTRANO E NON ORDINANO (per progetto: `COMMENT` delle
#    viste). Il filtro `attivo IS TRUE` e l'ordine del padre li mette questo
#    BB, in un punto solo per le due letture.
#
# ⭐ LA SORGENTE PUO' ESSERE UNA FUNZIONE (lotto D, 2026-09-30). Le righe del
#    contratto le calcola `vendite.fn_contratto_righe_preview(contratto)`:
#    con `_righe_funzione` il BB legge da `fn(padre) v`, gia' ristretta al
#    padre. Il resto — ricerca, ordinamento, pagina, totale — e' lo stesso.
#
# ⚠️ Scope: le viste sono `security_invoker` e le tabelle in RLS; il padre lo
#    verifica il service prima di leggere le righe («leggi prima la testata»,
#    BB `apps.core.services.testata_guard.pagina_dopo_testata`): fuori
#    perimetro e' un 404, non una lista vuota.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from django.db import connection

from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    limiti_pagina,
    rows_to_list,
    sql_order_clause,
)


class RigheListaMixin:
    """La PAGINA delle righe di un padre, per la lista configurabile.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_righe_vista``: nome FQN della vista (``"vendite.vw_ordini_righe_dettaglio"``);
    - ``_righe_fk_documento``: colonna FK al padre (``"ordine_id"``, ``"prodotto_id"``);
    - ``_righe_ordine_documento``: l'ordine del PADRE, colonna di posizione
      (``"riga_nr"``; ``"ordine"`` sul preventivo; ``"valido_dal"`` sulla
      distinta; ``"sezione_documento"`` su ordine, bolla e fattura, dove la
      vista mette gli oneri dopo gli articoli). E' l'ordine di partenza della
      lista e quello della lettura completa;
    - ``_righe_ordinamento``: whitelist `campo_sorgente -> colonna` delle
      colonne `ordinabile = t` della lista a catalogo;
    - ``_righe_ricerca``: la `RicercaFull` della lista a catalogo.

    E possono ridefinire:

    - ``_righe_ordine_documento_desc``: l'ordine del padre parte dal fondo
      (default ``False``; ``True`` sulla distinta: la versione piu' recente in
      cima);
    - ``_righe_colonne_desc``: chiavi della whitelist che partono DESC (le
      date, regola di Tid del 2026-09-02). Default nessuna;
    - ``_righe_chiave``: la colonna che identifica la riga, spareggio di ogni
      ordinamento (default ``"id"``; ``"riga_key"`` su fattura e contratto);
    - ``_righe_solo_attive``: filtra ``attivo IS TRUE`` (default ``True``);
    - ``_righe_ordine_documento_extra``: colonne che seguono
      ``_righe_ordine_documento`` nell'ordine del padre, sempre crescenti
      (default nessuna; ``("riga_nr",)`` su ordine e bolla,
      ``("ordinamento", "riga_nr")`` sulla fattura);
    - ``_righe_funzione``: nome FQN di una funzione ``fn(padre_id)`` che
      restituisce le righe, al posto di ``_righe_vista`` e
      ``_righe_fk_documento`` (default ``None``);

    E il gancio ``_righe_filtri`` per i filtri PROPRI di una lista (la distinta
    ha «in vigore al»): vedi sotto.
    """

    _righe_vista: str
    _righe_funzione: str | None = None
    _righe_fk_documento: str
    _righe_ordine_documento: str
    _righe_ordine_documento_desc: bool = False
    _righe_ordinamento: Mapping[str, str]
    _righe_ricerca: RicercaFull
    _righe_colonne_desc: Collection[str] = ()
    _righe_chiave: str = "id"
    _righe_solo_attive: bool = True
    _righe_ordine_documento_extra: tuple[str, ...] = ()

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
        prima = f"`{cls._righe_ordine_documento}`"
        if cls._righe_ordine_documento_desc:
            prima += " decrescente"
        altre = (*cls._righe_ordine_documento_extra, cls._righe_chiave)
        return ", ".join([prima, *(f"`{c}`" for c in altre)]) + "."

    # Scopo: la sorgente comune alle due letture: il `FROM` (alias `v`), le
    #        condizioni che la restringono al padre e alle sole righe attive
    #        dove la sorgente le distingue, e i loro parametri. Una funzione
    #        del padre e' gia' ristretta: nessuna condizione sua.
    #        Ritorna (from_sql, condizioni, params).
    def _righe_da(self, documento_id: Any) -> tuple[str, list[str], list[Any]]:
        if self._righe_funzione is not None:
            from_sql, conditions = f"{self._righe_funzione}(%s) v", []
        else:
            from_sql = f"{self._righe_vista} v"
            conditions = [f"v.{self._righe_fk_documento} = %s"]
        if self._righe_solo_attive:
            conditions.append("v.attivo IS TRUE")
        return from_sql, conditions, [documento_id]

    # Scopo: i filtri PROPRI della lista (oltre a ricerca e ordinamento), che
    #        la sottoclasse traduce in condizioni sulla sorgente `v`. Il
    #        default non ne conosce nessuno.
    # ⛔ Un filtro che la classe non conosce e' un ERRORE, non si ignora: una
    #    lista che scarta in silenzio il filtro chiesto risponde righe che
    #    l'operatore crede filtrate. Un valore `None` vale «non filtrare».
    def _righe_filtri(
        self, conditions: list[str], params: list[Any], filtri: Mapping[str, Any],
    ) -> None:
        sconosciuti = sorted(k for k, v in filtri.items() if v is not None)
        if sconosciuti:
            raise TypeError(
                f"{type(self).__name__}: filtri di lista non dichiarati: {sconosciuti}"
            )

    # Scopo: la clausola WHERE di un elenco di condizioni, anche vuoto.
    @staticmethod
    def _righe_where(conditions: list[str]) -> str:
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Scopo: una PAGINA delle righe del padre, per la lista configurabile:
    #        ricerca libera dal catalogo, ordinamento dalla whitelist, ordine
    #        del padre quando nessuno chiede altro, filtri propri della lista
    #        (`**filtri`, gancio `_righe_filtri`). Ritorna `(righe, totale)`;
    #        il totale e' un COUNT indipendente dalle righe consegnate (api.md
    #        §«Il `count` non si deriva MAI dalle righe che stai consegnando»).
    # ⚠️ `max_limit`: la lista resta al cap standard (`MAX_LIMIT`, fonte
    #    unica in core); l'export passa il suo tetto (EXPORT_MAX_ROWS + 1)
    #    per accorgersi di un file troncato.
    # ⭐ L'ordine del padre a piu' colonne (fattura: `ordinamento, riga_nr`):
    #    la prima e' il default del BB e prende il verso; le altre entrano
    #    nello spareggio, prima della chiave, e restano CRESCENTI (il BB mette
    #    il verso solo in coda). E' voluto: `riga_nr` e' la posizione DENTRO un
    #    gruppo di `ordinamento`, che si legge in avanti qualunque sia il verso.
    def list_righe_pagina(
        self,
        documento_id: Any,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int = 0,
        max_limit: int = MAX_LIMIT,
        **filtri: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=self._righe_ordinamento,
            default=f"v.{self._righe_ordine_documento}",
            default_desc=self._righe_ordine_documento_desc,
            tiebreak=", ".join(
                [f"v.{c}" for c in self._righe_ordine_documento_extra]
                + [f"v.{self._righe_chiave}"]
            ),
            colonne_desc=self._righe_colonne_desc,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)
        from_sql, conditions, params = self._righe_da(documento_id)
        self._righe_filtri(conditions, params, filtri)
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
        )
        return righe, totale


class RigheListaCompletaMixin(RigheListaMixin):
    """Alla pagina di `RigheListaMixin` aggiunge la lettura COMPLETA delle
    righe del padre, nell'ordine del padre: per chi le usa tutte insieme."""

    # Scopo: l'ordine del PADRE come elenco di colonne qualificate
    #        (`v.ordinamento, v.riga_nr`; `v.valido_dal DESC` sulla distinta).
    def _righe_ordine_documento_sql(self) -> str:
        prima = f"v.{self._righe_ordine_documento}"
        if self._righe_ordine_documento_desc:
            prima += " DESC"
        return ", ".join([prima, *(f"v.{c}" for c in self._righe_ordine_documento_extra)])

    # Scopo: TUTTE le righe del padre, nell'ordine del padre. Per chi le usa
    #        tutte insieme: i generatori di stampa, i dialog di evasione e
    #        riconsegna, il dettaglio dell'articolo. ⛔ Non e' la lista a
    #        video: quella e' `list_righe_pagina`.
    def list_righe(self, documento_id: Any) -> list[dict[str, Any]]:
        from_sql, conditions, params = self._righe_da(documento_id)
        sql = f"""
            SELECT v.*
              FROM {from_sql}
             {self._righe_where(conditions)}
             ORDER BY {self._righe_ordine_documento_sql()}, v.{self._righe_chiave}
        """  # noqa: S608 — sorgente, FK e colonne d'ordine sono attributi di classe costanti; valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)
