# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from apps.core.db._helpers import coerce_jsonb_dict, row_to_dict, rows_to_list


# Scopo: Il driver restituisce il jsonb `snapshot` come stringa raw: qui viene
#        normalizzato a dict in TUTTE le uscite del mixin, cosi' service e FE
#        lavorano sempre con un oggetto (mai doppio parsing client-side).
def _snapshot_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    row["snapshot"] = coerce_jsonb_dict(row.get("snapshot"))
    return row


class IndirizziDocumentoRepositoryMixin:
    """Building block CRUD indirizzi documento per repository sorgente.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_indirizzi_table``: nome FQN tabella (es. ``"vendite.ddt_indirizzi"``).
    - ``_indirizzi_fk_documento``: colonna FK al documento (es. ``"ddt_id"``).
    - ``_indirizzi_ambito``: ambito whitelist in config.tipi_indirizzi_allowed
      (es. ``"DDT"``).
    - ``_indirizzi_documento_table``: tabella testata del documento (es.
      ``"vendite.ddt"``), per il guard di ownership del picker.
    - ``_indirizzi_doc_sr_column`` (opzionale): colonna soggetto_ruolo NATIVA
      della testata quando il dominio ce l'ha (ordini ``soggetto_ruolo_id``,
      ddt ``destinatario_soggetto_ruolo_id``). Ha priorita' sul BA: e'
      l'identita' che il FE usa per il picker, e regge anche i documenti
      con billing_account NULL (ordine prospect, DDT da evasione di ordine
      senza BA). None = risoluzione solo via billing_account.
    """

    _indirizzi_table: str
    _indirizzi_fk_documento: str
    _indirizzi_ambito: str
    _indirizzi_documento_table: str
    _indirizzi_doc_sr_column: str | None = None

    # Scopo: soggetto_ruolo del CLIENTE/DESTINATARIO del documento, ancora
    #        unica per guard ownership picker e auto-assegnazione default:
    #        colonna nativa della testata se il dominio la dichiara
    #        (fallback BA), altrimenti solo via billing_account. LEFT JOIN:
    #        un documento senza BA con colonna nativa resta risolvibile.
    #        None se documento inesistente o soggetto_ruolo non risolvibile.
    def get_soggetto_ruolo_documento(self, documento_id: int) -> int | None:
        col = self._indirizzi_doc_sr_column
        sr_expr = f"COALESCE(d.{col}, ba.soggetto_ruolo_id)" if col \
            else "ba.soggetto_ruolo_id"
        sql = f"""
            SELECT {sr_expr}
              FROM {self._indirizzi_documento_table} d
              LEFT JOIN anagrafiche.billing_account ba
                ON ba.id = d.billing_account_id
             WHERE d.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Tipi indirizzo ammessi per l'ambito del documento (slot del
    #        pannello FE): il GET li restituisce insieme alle righe cosi' la
    #        UI disegna uno slot per tipo senza conoscere la whitelist.
    def list_tipi_indirizzo_ammessi(self) -> list[dict[str, Any]]:
        sql = """
            SELECT ti.id AS tipo_indirizzo_id,
                   ti.codice_interno AS tipo_indirizzo_codice,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   a.obbligatorio
              FROM config.tipi_indirizzi_allowed a
              JOIN config.tipi_indirizzi ti ON ti.id = a.tipo_indirizzo_id
             WHERE a.ambito = %s
               AND a.attivo IS TRUE
             ORDER BY a.obbligatorio DESC, ti.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [self._indirizzi_ambito])
            return rows_to_list(cursor)

    # Scopo: Indirizzi del documento con tipo denormalizzato (drawer + PDF
    #        context builder). Shape superset del vecchio list preventivi
    #        (aggiunto tipo_indirizzo_codice, additivo).
    def list_indirizzi(self, documento_id: int) -> list[dict[str, Any]]:
        fk = self._indirizzi_fk_documento
        sql = f"""
            SELECT di.id,
                   di.{fk},
                   di.tipo_indirizzo_id,
                   ti.codice_interno AS tipo_indirizzo_codice,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   di.snapshot,
                   di.origine_indirizzo_id,
                   di.origine_soggetto_ruolo_id,
                   tio.codice_interno AS origine_tipo_indirizzo_codice,
                   tio.descrizione AS origine_tipo_indirizzo_descrizione
              FROM {self._indirizzi_table} di
              LEFT JOIN config.tipi_indirizzi ti ON ti.id = di.tipo_indirizzo_id
              LEFT JOIN anagrafiche.indirizzi ai ON ai.id = di.origine_indirizzo_id
              LEFT JOIN config.tipi_indirizzi tio ON tio.id = ai.tipo_indirizzo_id
             WHERE di.{fk} = %s
             ORDER BY di.tipo_indirizzo_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return [_snapshot_to_dict(r) for r in rows_to_list(cursor)]

    # Scopo: Primo indirizzo di RUOLO del cliente per priorita' di tipo
    #        (es. ['CON','FATT']: consegna, altrimenti fatturazione — regola
    #        default UX v2). Preferisce la riga generica (istanza NULL).
    #        None se il ruolo non ha indirizzi dei tipi richiesti.
    def find_indirizzo_ruolo_per_tipi(
        self, soggetto_ruolo_id: int, tipi_codici: list[str],
    ) -> int | None:
        sql = """
            SELECT i.id
              FROM anagrafiche.indirizzi i
              JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
             WHERE i.soggetto_ruolo_id = %s
               AND ti.codice_interno = ANY(%s)
             ORDER BY array_position(%s::text[], ti.codice_interno),
                      i.istanza_utility_id NULLS FIRST
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, tipi_codici, tipi_codici])
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Snapshot dal layer SOGGETTO (vw_indirizzi_resolved_soggetto) per
    #        priorita' di tipo: usato dall'auto-assegnazione quando il RUOLO
    #        non ha l'indirizzo (gli indirizzi soggetto non hanno riga in
    #        anagrafiche.indirizzi -> nessun aggancio origine possibile).
    #        Match su codice_interno IMMUTABILE (la vista espone il codice
    #        mutabile). None se il soggetto non ha indirizzi dei tipi chiesti.
    def find_snapshot_soggetto_per_tipi(
        self, soggetto_ruolo_id: int, tipi_codici: list[str],
    ) -> dict[str, Any] | None:
        sql = """
            SELECT ti.codice_interno AS tipo_codice,
                   v.indirizzo_display, v.indirizzo_libero, v.cap,
                   v.comune_descrizione, v.provincia_sigla, v.stato_iso2
              FROM anagrafiche.vw_indirizzi_resolved_soggetto v
              JOIN config.tipi_indirizzi ti ON ti.id = v.tipo_indirizzo_id
              JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = v.soggetto_id
             WHERE sr.id = %s
               AND ti.codice_interno = ANY(%s)
             ORDER BY array_position(%s::text[], ti.codice_interno)
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, tipi_codici, tipi_codici])
            row = row_to_dict(cursor)
        if row is None:
            return None
        snapshot = {
            "via": row["indirizzo_display"] or row["indirizzo_libero"] or "",
            "cap": row["cap"] or "",
            "citta": row["comune_descrizione"] or "",
            # char(n) a DB: trim del padding.
            "prov": (row["provincia_sigla"] or "").strip(),
            "stato": (row["stato_iso2"] or "").strip(),
        }
        return {
            "tipo_codice": row["tipo_codice"],
            "snapshot": {k: v.strip() for k, v in snapshot.items() if v.strip()},
        }

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
        """
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
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_row_id, documento_id])
            return cursor.fetchone() is not None
