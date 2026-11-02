# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per le tabelle `*_indirizzi` dei documenti
#        (modello simmetrico su 6 ambiti: preventivi/offerte/ordini/ddt/
#        contratti/fatture — brief-db-indirizzi-documenti-simmetria-e-cascata).
#        Estrazione regola-del-2: il CRUD era gia' clonato sui preventivi e
#        sarebbe stato replicato su altri 4 domini.
#
#        Modello: snapshot JSONB congelato + origine soft (origine_indirizzo_id
#        / origine_soggetto_ruolo_id, FK SET NULL), UNIQUE uno-per-tipo.
#        La whitelist tipi per ambito e' governata a DB (trigger
#        trgfn_tipi_indirizzi_only_allowed su config.tipi_indirizzi_allowed,
#        fail-closed). Lo snapshot dal picker e' composto SERVER-SIDE via
#        `script.fn_snapshot_indirizzo` (D-5): il client non scrive mai lo
#        snapshot per gli indirizzi anagrafici, solo per l'una-tantum (D-4).
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list


# Scopo: `snapshot` sempre oggetto in TUTTE le uscite del mixin: lo decodifica
#        il lettore comune, qui il NULL diventa `{}` (service e FE lavorano con
#        un oggetto).
def _snapshot_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    row["snapshot"] = row.get("snapshot") or {}
    return row


class IndirizziDocumentoRepositoryMixin:
    """Building block CRUD indirizzi documento per repository sorgente.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_indirizzi_table``: nome FQN tabella (es. ``"vendite.ddt_indirizzi"``).
    - ``_indirizzi_fk_documento``: colonna FK al documento (es. ``"ddt_id"``).
    - ``_indirizzi_documento``: il documento, col codice di
      ``config.sorgenti`` (costanti ``SORGENTE_*`` di
      ``apps/config/sorgenti.py``: ``DDT_VENDITA``, ``ORDINE_VENDITA``,
      ``OFFERTA_COMMERCIALE``, ``PREVENTIVO``, ``CONTRATTO``). Un codice solo
      per due usi: l'ambito della whitelist ``config.tipi_indirizzi_allowed``
      (FK verso le sorgenti) e il selettore di
      ``vendite.fn_doc_indirizzo_default``. Fino al 2026-10-20 l'ambito era
      un attributo a parte col plurale (``ORDINI``, ``OFFERTE``…), ritirato
      col sotto-giro 2d di brief-db-grammatica-unica-documenti (G-6).

    Chi e' il cliente del documento non lo sa piu' il mixin: lo legge il DB
    (``script.fn_get_cliente_testata_documento``), che tiene anche la regola
    «un indirizzo d'anagrafica e' del cliente del documento»
    (brief-db-indirizzi-documento-seguono-il-cliente).
    """

    _indirizzi_table: str
    _indirizzi_fk_documento: str
    _indirizzi_documento: str

    # Scopo: Tipi indirizzo ammessi per l'ambito del documento (slot del
    #        pannello FE): il GET li restituisce insieme alle righe cosi' la
    #        UI disegna uno slot per tipo senza conoscere la whitelist.
    def list_tipi_indirizzo_ammessi(self) -> list[dict[str, Any]]:
        sql = """
            SELECT ti.id AS tipo_indirizzo_id,
                   ti.codice_interno AS tipo_indirizzo_codice_interno,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   a.obbligatorio
              FROM config.tipi_indirizzi_allowed a
              JOIN config.tipi_indirizzi ti ON ti.id = a.tipo_indirizzo_id
             WHERE a.ambito = %s
               AND a.attivo IS TRUE
             ORDER BY a.obbligatorio DESC, ti.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [self._indirizzi_documento])
            return rows_to_list(cursor)

    # Scopo: Indirizzi del documento con tipo denormalizzato (drawer + PDF
    #        context builder). Shape superset del vecchio list preventivi
    #        (aggiunto il codice interno del tipo, additivo).
    def list_indirizzi(self, documento_id: int) -> list[dict[str, Any]]:
        fk = self._indirizzi_fk_documento
        sql = f"""
            SELECT di.id,
                   di.{fk},
                   di.tipo_indirizzo_id,
                   ti.codice_interno AS tipo_indirizzo_codice_interno,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   di.snapshot,
                   di.origine_indirizzo_id,
                   di.origine_soggetto_ruolo_id,
                   tio.codice_interno AS origine_tipo_indirizzo_codice_interno,
                   tio.descrizione AS origine_tipo_indirizzo_descrizione
              FROM {self._indirizzi_table} di
              LEFT JOIN config.tipi_indirizzi ti ON ti.id = di.tipo_indirizzo_id
              LEFT JOIN anagrafiche.indirizzi ai ON ai.id = di.origine_indirizzo_id
              LEFT JOIN config.tipi_indirizzi tio ON tio.id = ai.tipo_indirizzo_id
             WHERE di.{fk} = %s
             ORDER BY di.tipo_indirizzo_id
        """  # noqa: S608 — tabella/colonne da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return [_snapshot_to_dict(r) for r in rows_to_list(cursor)]

    # Scopo: Riempie lo slot di default del documento dall'anagrafica del suo
    #        cliente, SOLO se e' vuoto: `vendite.fn_doc_indirizzo_default`.
    #        Quale slot e quale ripiego e' un dato
    #        (`config.tipi_indirizzi_allowed.slot_default` /
    #        `ripiego_tipo_indirizzo_id`), la risoluzione e' quella di
    #        `script.fn_resolve_indirizzo_documento`. Torna True se ha scritto.
    #        ⚠️ Non e' best-effort: un errore del DB sale, e il chiamante lo
    #        mette nella stessa transazione della creazione.
    def riempi_indirizzo_default(self, documento_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_doc_indirizzo_default(%s, %s)",
                [self._indirizzi_documento, documento_id],
            )
            row = cursor.fetchone()
            return bool(row and row[0])

    # Scopo: Compone server-side lo snapshot canonico da un indirizzo
    #        anagrafico di ruolo (D-5, single source DB). Ritorna
    #        {snapshot, origine_soggetto_ruolo_id}; la fn solleva
    #        E_INDIRIZZO_SNAPSHOT_NOT_FOUND su id inesistente.
    def snapshot_from_origine(self, origine_indirizzo_id: int) -> dict[str, Any]:
        sql = "SELECT snapshot, origine_soggetto_ruolo_id FROM script.fn_snapshot_indirizzo(%s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [origine_indirizzo_id])
            row = row_to_dict(cursor)
            assert row is not None  # la fn alza errore, non torna vuoto
            return _snapshot_to_dict(row)

    # Scopo: Upsert uno-per-tipo (INSERT o sostituzione dello slot). Il
    #        trigger whitelist a DB valida il tipo per l'ambito.
    def upsert_indirizzo(
        self,
        *,
        documento_id: int,
        tipo_indirizzo_id: int,
        snapshot: dict[str, Any],
        origine_indirizzo_id: int | None = None,
        origine_soggetto_ruolo_id: int | None = None,
    ) -> dict[str, Any]:
        fk = self._indirizzi_fk_documento
        sql = f"""
            INSERT INTO {self._indirizzi_table} (
                {fk}, tipo_indirizzo_id, snapshot,
                origine_indirizzo_id, origine_soggetto_ruolo_id
            ) VALUES (%s, %s, %s::jsonb, %s, %s)
            ON CONFLICT ({fk}, tipo_indirizzo_id)
            DO UPDATE SET
                snapshot = EXCLUDED.snapshot,
                origine_indirizzo_id = EXCLUDED.origine_indirizzo_id,
                origine_soggetto_ruolo_id = EXCLUDED.origine_soggetto_ruolo_id
            RETURNING id, {fk}, tipo_indirizzo_id, snapshot,
                      origine_indirizzo_id, origine_soggetto_ruolo_id
        """  # noqa: S608 — tabella/colonne da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                documento_id,
                tipo_indirizzo_id,
                json.dumps(snapshot),
                origine_indirizzo_id,
                origine_soggetto_ruolo_id,
            ])
            row = row_to_dict(cursor)
            assert row is not None
            return _snapshot_to_dict(row)

    # Scopo: Rimuove uno slot indirizzo (hard delete: snapshot congelato senza
    #        storicita' propria; il vincolo di obbligatorieta' e' verificato
    #        dal guard DB all'emissione, non qui). Ritorna True se rimosso.
    def delete_indirizzo(self, documento_id: int, indirizzo_row_id: int) -> bool:
        fk = self._indirizzi_fk_documento
        sql = f"""
            DELETE FROM {self._indirizzi_table}
             WHERE id = %s AND {fk} = %s
            RETURNING id
        """  # noqa: S608 — tabella/colonne da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_row_id, documento_id])
            return cursor.fetchone() is not None
