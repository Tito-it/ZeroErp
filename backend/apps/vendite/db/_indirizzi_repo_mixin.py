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
    - ``_indirizzi_doc_istanza_column`` (opzionale): colonna istanza NATIVA
      della testata. La dichiarano i soli documenti **precontrattuali**
      (preventivi, offerte, contratti), che scelgono l'istanza prima che
      esista un BA e la congelano sulla testata. Gli **esecutivi** (ordini,
      DDT, fatture) hanno sempre un BA e l'istanza e' univoca da li'
      (``ba.istanza_utility_id``, FK NOT NULL): non duplicano la colonna.
      Vedi guida `gestione-delle-istanze-utility` §«relazione 1:1 per utility».
    """

    _indirizzi_table: str
    _indirizzi_fk_documento: str
    _indirizzi_ambito: str
    _indirizzi_documento_table: str
    _indirizzi_doc_sr_column: str | None = None
    _indirizzi_doc_istanza_column: str | None = None

    # Scopo: Ancora del documento per la risoluzione indirizzi: la coppia
    #        (soggetto_ruolo, istanza_utility). Una sola query, perche' i due
    #        valori stanno sulla stessa riga di testata.
    #        - soggetto_ruolo: colonna nativa se dichiarata (fallback BA);
    #        - istanza: colonna nativa se dichiarata (precontrattuali),
    #          altrimenti da `ba.istanza_utility_id` (esecutivi).
    #        LEFT JOIN sul BA: un documento senza BA ma con colonna nativa
    #        resta risolvibile (ordine prospect, DDT da evasione senza BA).
    #        (None, None) se il documento non esiste.
    def get_ancora_indirizzi_documento(
        self, documento_id: int,
    ) -> tuple[int | None, int | None]:
        sr_col = self._indirizzi_doc_sr_column
        ist_col = self._indirizzi_doc_istanza_column
        sr_expr = f"COALESCE(d.{sr_col}, ba.soggetto_ruolo_id)" if sr_col \
            else "ba.soggetto_ruolo_id"
        ist_expr = f"COALESCE(d.{ist_col}, ba.istanza_utility_id)" if ist_col \
            else "ba.istanza_utility_id"
        sql = f"""
            SELECT {sr_expr}, {ist_expr}
              FROM {self._indirizzi_documento_table} d
              LEFT JOIN anagrafiche.billing_account ba
                ON ba.id = d.billing_account_id
             WHERE d.id = %s
        """  # noqa: S608 — tabella/colonne da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            row = cursor.fetchone()
            return (row[0], row[1]) if row else (None, None)

    # Scopo: soggetto_ruolo del CLIENTE/DESTINATARIO del documento, ancora
    #        unica per il guard di ownership del picker. Delega alla coppia
    #        sopra: un solo SQL da mantenere.
    def get_soggetto_ruolo_documento(self, documento_id: int) -> int | None:
        soggetto_ruolo, _ = self.get_ancora_indirizzi_documento(documento_id)
        return soggetto_ruolo

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
        """  # noqa: S608 — tabella/colonne da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return [_snapshot_to_dict(r) for r in rows_to_list(cursor)]

    # Scopo: Risolve l'indirizzo di un tipo per il documento delegando a
    #        `script.fn_resolve_indirizzo_documento` (2026-07-31): catena a due
    #        layer RUOLO → SOGGETTO con **precedenza all'istanza** del documento.
    #        Ritorna {snapshot, origine_indirizzo_id, origine_soggetto_ruolo_id}
    #        oppure None se nessun layer ha risposto (l'obbligatorieta' la
    #        decide il chiamante, non questa).
    #
    # ⚠️ Perche' l'SQL non sta piu' qui. Fino al 2026-07-30 il mixin aveva due
    #    metodi propri (`find_indirizzo_ruolo_per_tipi` +
    #    `find_snapshot_soggetto_per_tipi`) con la catena replicata in Python, e
    #    stava per nascerne una **terza** copia per il task fattura. Ora la
    #    catena ha un solo proprietario a DB (regola del 2 / D-5: lo snapshot si
    #    compone server-side, mai a mano).
    #    Due conseguenze di merito, entrambe volute:
    #      1. l'ordinamento e' cambiato. Il vecchio SQL faceva
    #         `ORDER BY ... i.istanza_utility_id NULLS FIRST`, cioe' preferiva
    #         l'indirizzo **generico** e ignorava l'istanza del documento; la
    #         funzione DB fa `ORDER BY (istanza_utility_id IS NULL)` e mette
    #         davanti quello **dell'istanza richiesta**. Per un ERP di utilities
    #         e' il verso giusto;
    #      2. il layer SOGGETTO non compone piu' lo snapshot in Python (5 chiavi
    #         assemblate a mano): lo produce `fn_snapshot_indirizzo_soggetto`
    #         con lo **stesso shape canonico** del layer RUOLO.
    def resolve_indirizzo_documento(
        self,
        *,
        soggetto_ruolo_id: int,
        istanza_utility_id: int | None,
        tipo_codice: str,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT snapshot, origine_indirizzo_id, origine_soggetto_ruolo_id
              FROM script.fn_resolve_indirizzo_documento(%s, %s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, istanza_utility_id, tipo_codice])
            row = row_to_dict(cursor)
        if row is None:
            return None
        return _snapshot_to_dict(row)

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
