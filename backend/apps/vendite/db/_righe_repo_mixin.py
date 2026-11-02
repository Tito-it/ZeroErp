# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: le righe dei documenti di VENDITA lette dalla loro vista
#        `vw_<doc>_righe_dettaglio`: le dichiarazioni gemelle delle righe
#        commerciali (colonne ordinabili e di ricerca delle liste 97-99) e,
#        per le righe che stanno in una TABELLA con `id` e `attivo`
#        (preventivo, ordine, DDT, reso), la riga singola e il conteggio.
#        ⭐ La LETTURA (pagina e lettura completa) e' il BB core
#        `apps.core.db.righe_lista_mixin` dal 2026-10-04: e' nata qui (lotto A
#        del brief-db-liste-righe-documento, 2026-09-28) ed e' salita in core
#        quando la distinta del catalogo ne aveva una seconda copia (§9.16).
#
# ⭐ LE VISTE NON FILTRANO E NON ORDINANO (per progetto: `COMMENT` delle
#    viste): filtro `attivo IS TRUE` e ordine del documento li mette il BB.
#
# ⚠️ Scope emittente: le viste sono `security_invoker` e le tabelle in RLS;
#    la testata la verifica il service prima di leggere le righe («leggi
#    prima la testata»: fuori perimetro e' un 404, non una lista vuota).
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date
from typing import Any, ClassVar

from django.db import connection, transaction

from apps.core.db._helpers import (
    colonne_identita,
    fetchone_scalar,
    row_to_dict,
)
from apps.core.db.righe_lista_mixin import RigheListaCompletaMixin

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


class RigheDocumentoRepositoryMixin(RigheListaCompletaMixin):
    """Le righe di un documento che stanno in una TABELLA con `id` e `attivo`
    (preventivo, ordine, DDT, reso): alla lettura del BB core
    (`RigheListaCompletaMixin`) aggiunge la riga singola e il conteggio.

    In piu' degli attributi del BB, le sottoclassi definiscono:

    - ``_righe_tabella``: nome FQN della tabella delle righe
      (``"vendite.ordini_righe"``): solo per il CONTEGGIO, vedi `count_righe`.
    """

    _righe_tabella: str
    # Le date di consegna che le righe di QUESTO documento portano
    # (brief-db-date-consegna-righe-in-blocco, D-4): colonna -> `None`, oppure
    # la coppia (check di riga, `reason` del motivo che fa SALTARE la riga).
    # E' l'unica cosa che `scrivi_data_consegna` sa del documento; un
    # documento senza date (DDT, reso) lascia il dizionario vuoto.
    _righe_date_consegna: ClassVar[dict[str, tuple[str, str] | None]] = {}

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

    # Scopo: le colonne di data di consegna che le righe di questo documento
    #        portano: la whitelist di `scrivi_data_consegna`, letta dal service
    #        per validare la richiesta senza toccare l'attributo di classe.
    @classmethod
    def colonne_date_consegna(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._righe_date_consegna))

    # Scopo: scrive UNA data di consegna sulle righe attive del documento, in un
    #        solo UPDATE (brief-db-date-consegna-righe-in-blocco §5, §8). Serve
    #        all'utility «Aggiorna date di consegna» e al verbo per riga
    #        (`riga_id`): la stessa scrittura, regola del 2.
    # ⭐ Il giudice resta il DB, riga per riga: lock di stato, guard di riga.
    #    L'unica selezione fatta qui e' saltare le righe il cui motivo e' quello
    #    dichiarato in `_righe_date_consegna` (BF-1: la riga gia' spedita). Un
    #    motivo di STATO non fa saltare niente: la riga va all'UPDATE e il lock
    #    la rifiuta col suo 409, invece di un «0 aggiornate» muto.
    # ⚠️ Con `riga_id` non si salta nulla: sulla riga singola il rifiuto e' la
    #    risposta giusta, e lo dice il guard col suo codice.
    # ⭐ `anteprima` esegue lo STESSO UPDATE in un savepoint e lo annulla: i
    #    lock e il guard girano davvero, quindi un rifiuto arriva prima della
    #    domanda di conferma, e i numeri sono quelli che la scrittura dara'.
    #    Fino al 2026-10-12 contava con una SELECT a parte, che non passava dai
    #    trigger: diceva «5 righe» e poi la scrittura prendeva il 409.
    # Ritorna: {"aggiornate": n, "saltate": m}. Con `anteprima` nulla resta scritto.
    def scrivi_data_consegna(
        self,
        documento_id: int,
        colonna: str,
        data: date | None,
        *,
        riga_id: int | None = None,
        solo_vuote: bool = False,
        anteprima: bool = False,
    ) -> dict[str, int]:
        if colonna not in self._righe_date_consegna:
            raise ValueError(f"{self._righe_tabella}: colonna non ammessa {colonna!r}")
        regola_salto = self._righe_date_consegna[colonna]
        params: list[Any] = []
        if regola_salto is None or riga_id is not None:
            saltata = "false"
        else:
            check_fn, motivo = regola_salto
            saltata = f"COALESCE({check_fn}(r.id) @> %s::jsonb, false)"
            params.append(json.dumps([{"reason": motivo}]))
        filtri = [f"r.{self._righe_fk_documento} = %s", "r.attivo IS TRUE"]
        params.append(documento_id)
        if riga_id is not None:
            filtri.append("r.id = %s")
            params.append(riga_id)
        if solo_vuote:
            filtri.append(f"r.{colonna} IS NULL")
        candidate = f"""
            WITH candidate AS (
                SELECT r.id, {saltata} AS saltata
                  FROM {self._righe_tabella} r
                 WHERE {" AND ".join(filtri)}
            )
        """  # noqa: S608 — tabella, FK, colonna e check da attributi di classe (colonna in whitelist); valori come parametri
        sql = candidate + f"""
            , scritte AS (
                UPDATE {self._righe_tabella} t
                   SET {colonna} = %s
                  FROM candidate c
                 WHERE t.id = c.id
                   AND NOT c.saltata
                RETURNING t.id
            )
            SELECT (SELECT COUNT(*) FROM scritte),
                   (SELECT COUNT(*) FROM candidate WHERE saltata)
        """  # noqa: S608 — come sopra
        params.append(data)
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            if anteprima:
                # Il savepoint si annulla all'uscita: i trigger hanno giudicato,
                # niente resta scritto.
                transaction.set_rollback(True)
            return {"aggiornate": int(row[0]), "saltate": int(row[1])}

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
