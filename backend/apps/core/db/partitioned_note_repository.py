# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository generico per partizioni della tabella vendite.note
#        (LIST PARTITION su target_tipo). Una sola implementazione
#        riusabile da qualunque dominio sorgente (PREVENTIVO, CONTRATTO,
#        ORDINE, DDT, FATTURA, ATTIVITAFT) e da futuri schemi che
#        adotteranno lo stesso pattern partizionato.
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import fetchone_scalar, row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Regex per validare SQL identifier dotted (schema.tabella). I parametri del
# constructor sono governati dal codice applicativo, ma il guard intercetta
# typo da refactor (es. spazi, virgolette, punto-virgola) prima che diventino
# SQL injection latente.
_SQL_IDENTIFIER_DOTTED = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
_SQL_IDENTIFIER_PLAIN = re.compile(r"^[a-z_][a-z0-9_]*$")


def _validate_sql_identifier(value: str, *, kind: str, dotted: bool) -> None:
    pattern = _SQL_IDENTIFIER_DOTTED if dotted else _SQL_IDENTIFIER_PLAIN
    if not isinstance(value, str) or not pattern.match(value):
        raise ValueError(
            f"{kind}='{value}' non valido "
            f"(atteso identifier{' dotted (schema.nome)' if dotted else ''})"
        )

# Whitelist colonne scrivibili in CREATE.
# `target_tipo` e `target_id` sono valorizzati dal repository (mai dal payload);
# `target_riga_id` e' immutabile post-create (spostare una nota fra righe = delete+create).
_NOTE_CREATE_COLUMNS: frozenset[str] = frozenset({
    "anchor_tipo",
    "posizione",
    "seq",
    "testo",
    "testo_md",
    "visibile",
    "solo_stampa",
    "id_stile",
    "id_lingua",
    "meta",
    "target_riga_id",
})

# Colonne dell'INSERT: la whitelist del payload + le due chiavi imposte dal
# repository.
_NOTE_INSERT_COLUMNS: frozenset[str] = _NOTE_CREATE_COLUMNS | {"target_tipo", "target_id"}

# Colonne jsonb dichiarate al BB (regola Tid 2026-09-26: una stringa li' e'
# testo JSON; il service oggi passa solo dict da `optional_meta`).
_NOTE_JSONB: tuple[str, ...] = ("meta",)

# Whitelist colonne aggiornabili in UPDATE (esclude target_*).
_NOTE_UPDATE_COLUMNS: frozenset[str] = frozenset({
    "anchor_tipo",
    "posizione",
    "seq",
    "testo",
    "testo_md",
    "visibile",
    "solo_stampa",
    "id_stile",
    "id_lingua",
    "meta",
})

# Whitelist valori CHECK partizione note (vendite).
# Allineata a chk_note_target_tipo / chk_note_anchor_tipo / chk_note_posizione.
TARGET_TIPI_AMMESSI: frozenset[str] = frozenset({
    "PREVENTIVO", "CONTRATTO", "OFFERTA",
    "ORDINE", "DDT", "FATTURA", "ATTIVITAFT",
})
ANCHOR_TIPI_AMMESSI: frozenset[str] = frozenset({"DOCUMENTO", "RIGA"})
POSIZIONI_AMMESSE: frozenset[str] = frozenset({
    "HEADER", "SEZIONE", "FOOTER", "BEFORE", "AFTER",
})

# Colonne lette in SELECT base. Decode via LEFT JOIN: stile da
# config.note_stili (codice + codice_interno + descrizione), lingua da
# config.lingue (codice_iso + descrizione, NULL se id_lingua NULL).
_SELECT_COLUMNS = """
    n.id,
    n.target_tipo,
    n.target_id,
    n.target_riga_id,
    n.anchor_tipo,
    n.posizione,
    n.seq,
    n.testo,
    n.testo_md,
    n.visibile,
    n.solo_stampa,
    n.meta,
    n.id_stile,
    s.codice          AS stile_codice,
    s.codice_interno  AS stile_codice_interno,
    s.descrizione     AS stile_descrizione,
    n.id_lingua,
    l.codice_iso      AS lingua_codice_iso,
    l.descrizione     AS lingua_descrizione,
    n.data_insert,
    n.user_insert,
    n.data_update,
    n.user_update
"""


class PartitionedNoteRepository:
    """Accesso DB generico a una partizione di `vendite.note`.

    La PK composita `(target_tipo, id)` impone di filtrare SEMPRE per
    `target_tipo` in UPDATE/DELETE/GET — il routing alla partizione corretta
    e' garantito da PG, ma il filtro esplicito e' difesa contro tampering
    dell'`id` cross-target_tipo (vedi pattern catalogo `catalogo_bom_repository`).

    Costruito una volta per dominio sorgente:
        PartitionedNoteRepository(
            partition_table="vendite.note_preventivo",
            target_tipo="PREVENTIVO",
            parent_table="vendite.preventivi",
            parent_pk="id",
            child_table="vendite.preventivi_righe",
            child_parent_fk="preventivo_id",
        )

    `child_table`/`child_parent_fk` sono opzionali: servono solo se il
    dominio ammette note di riga (anchor_tipo='RIGA').
    """

    # Scopo: Inizializza il repository per una partizione specifica.
    #        I parametri SONO SQL identifiers controllati dal codice applicativo
    #        (no input utente): l'interpolazione diretta in stringa SQL e' sicura.
    def __init__(
        self,
        *,
        partition_table: str,
        target_tipo: str,
        parent_table: str,
        parent_pk: str = "id",
        child_table: str | None = None,
        child_parent_fk: str | None = None,
    ) -> None:
        if target_tipo not in TARGET_TIPI_AMMESSI:
            raise ValueError(
                f"target_tipo='{target_tipo}' non ammesso "
                f"(consentiti: {sorted(TARGET_TIPI_AMMESSI)})"
            )
        if (child_table is None) != (child_parent_fk is None):
            raise ValueError(
                "child_table e child_parent_fk vanno valorizzati entrambi o nessuno"
            )
        _validate_sql_identifier(partition_table, kind="partition_table", dotted=True)
        _validate_sql_identifier(parent_table, kind="parent_table", dotted=True)
        _validate_sql_identifier(parent_pk, kind="parent_pk", dotted=False)
        if child_table is not None:
            _validate_sql_identifier(child_table, kind="child_table", dotted=True)
        if child_parent_fk is not None:
            _validate_sql_identifier(child_parent_fk, kind="child_parent_fk", dotted=False)
        self._partition_table = partition_table
        self._target_tipo = target_tipo
        self._parent_table = parent_table
        self._parent_pk = parent_pk
        self._child_table = child_table
        self._child_parent_fk = child_parent_fk

    @property
    def target_tipo(self) -> str:
        return self._target_tipo

    @property
    def supports_riga(self) -> bool:
        """True se il dominio ammette note di riga (anchor_tipo='RIGA')."""
        return self._child_table is not None

    # Scopo: Verifica esistenza del documento padre (preventivo/contratto/ecc.).
    #        Usato dal service per 404 esplicito prima di scrivere/leggere note.
    def exists_parent(self, target_id: int) -> bool:
        sql = (
            f"SELECT 1 FROM {self._parent_table} "  # noqa: S608
            f"WHERE {self._parent_pk} = %s LIMIT 1"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [target_id])
            return cursor.fetchone() is not None

    # Scopo: Verifica che una riga figlio appartenga al documento padre indicato.
    #        Difesa applicativa anti-tampering URL (es. POST /preventivi/1/note/
    #        con target_riga_id che appartiene al preventivo 99). Il trigger DB
    #        `trgfn_note_validate_generic` e' la difesa finale.
    def riga_belongs_to_parent(self, target_id: int, riga_id: int) -> bool:
        if self._child_table is None or self._child_parent_fk is None:
            return False
        sql = (
            f"SELECT 1 FROM {self._child_table} "  # noqa: S608
            f"WHERE id = %s AND {self._child_parent_fk} = %s LIMIT 1"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id, target_id])
            return cursor.fetchone() is not None

    # Scopo: Lista note per un target_id (documento), filtrabile per riga,
    #        con paginazione e decode dello stile. Ordinamento deterministico:
    #        prima note documento, poi per riga; entro lo stesso scope per
    #        posizione/seq/id (tiebreaker id obbligatorio, vedi policy paginazione).
    def list(
        self,
        target_id: int,
        *,
        target_riga_id: int | None = None,
        include_invisible: bool = True,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["n.target_tipo = %s", "n.target_id = %s"]
        params: list[Any] = [self._target_tipo, target_id]
        if target_riga_id is not None:
            where.append("n.target_riga_id = %s")
            params.append(target_riga_id)
        if not include_invisible:
            where.append("n.visibile = TRUE")
        where_sql = " AND ".join(where)

        count_sql = (
            f"SELECT COUNT(*) FROM {self._partition_table} n "  # noqa: S608
            f"WHERE {where_sql}"
        )
        list_sql = (
            f"SELECT {_SELECT_COLUMNS} "  # noqa: S608
            f"FROM {self._partition_table} n "
            f"LEFT JOIN config.note_stili s ON s.id = n.id_stile "
            f"LEFT JOIN config.lingue l ON l.id = n.id_lingua "
            f"WHERE {where_sql} "
            f"ORDER BY "
            f"  (n.target_riga_id IS NOT NULL), "
            f"  n.target_riga_id NULLS FIRST, "
            f"  n.anchor_tipo, n.posizione, n.seq, n.id "
            f"LIMIT %s OFFSET %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            total = int(fetchone_scalar(cursor))
            if total == 0:
                return [], 0
            cursor.execute(list_sql, [*params, limit, offset])
            rows = rows_to_list(cursor)
        return rows, total

    # Scopo: Restituisce singola nota filtrata per pk composita (target_tipo, id)
    #        + target_id (anti-tampering). Ritorna None se non esiste.
    def get(self, note_id: int, target_id: int) -> dict[str, Any] | None:
        sql = (
            f"SELECT {_SELECT_COLUMNS} "  # noqa: S608
            f"FROM {self._partition_table} n "
            f"LEFT JOIN config.note_stili s ON s.id = n.id_stile "
            f"LEFT JOIN config.lingue l ON l.id = n.id_lingua "
            f"WHERE n.target_tipo = %s AND n.id = %s AND n.target_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [self._target_tipo, note_id, target_id])
            return row_to_dict(cursor)

    # Scopo: Conta note attive su un documento padre. Usato per badge UI.
    def count_for_parent(self, target_id: int) -> int:
        sql = (
            f"SELECT COUNT(*) FROM {self._partition_table} "  # noqa: S608
            f"WHERE target_tipo = %s AND target_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [self._target_tipo, target_id])
            return int(fetchone_scalar(cursor))

    # Scopo: INSERT su partizione (BB `execute_dynamic_insert`, 2026-09-26).
    #        `target_tipo`/`target_id` sono governati dal repository: imposti
    #        DOPO il payload, vincono. RETURNING id (la pk composita ha id locale
    #        alla partizione).
    #        ⛔ Whitelist RIGIDA: una chiave fuori `_NOTE_CREATE_COLUMNS` e'
    #        RuntimeError (prima scartata in silenzio). Il service valida le
    #        chiavi del client con un 400 (`validate_allowed_keys`).
    #        ⚠️ Fino a quel giorno `meta` (dict) arrivava nudo al cursor, che non
    #        lo sa adattare: ogni nota con `meta` era un 500. Il BB lo serializza.
    #        Lo strip del BB su `testo`/`testo_md` non cambia niente: il service
    #        li strippa gia' (`optional_string`).
    def create(self, target_id: int, payload: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            self._partition_table,
            {**payload, "target_tipo": self._target_tipo, "target_id": target_id},
            allowed=_NOTE_INSERT_COLUMNS,
            jsonb=_NOTE_JSONB,
        )
        return int(riga["id"])

    # Scopo: UPDATE su partizione con pk composita (target_tipo, id) + target_id
    #        difensivo. SET dal BB `sql_set_clause` (whitelist RIGIDA
    #        `_NOTE_UPDATE_COLUMNS`: `target_*` fuori lista e' RuntimeError).
    #        `patch` vuoto -> False senza SQL. Restituisce True se la riga e'
    #        stata aggiornata.
    def update(
        self, note_id: int, target_id: int, patch: dict[str, Any],
    ) -> bool:
        if not patch:
            return False
        clausola, params = sql_set_clause(
            patch, allowed=_NOTE_UPDATE_COLUMNS, jsonb=_NOTE_JSONB,
        )
        sql = (
            f"UPDATE {self._partition_table} "  # noqa: S608 — tabella dal costruttore (verificata da _validate_sql_identifier), colonne verificate da sql_set_clause, valori come parametri
            f"SET {clausola} "
            f"WHERE target_tipo = %s AND id = %s AND target_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [*params, self._target_tipo, note_id, target_id])
            return cursor.rowcount > 0

    # Scopo: DELETE su partizione. Hard delete (le note non hanno colonna `attivo`).
    #        Filtrata per pk composita + target_id (anti-tampering).
    def delete(self, note_id: int, target_id: int) -> bool:
        sql = (
            f"DELETE FROM {self._partition_table} "  # noqa: S608
            f"WHERE target_tipo = %s AND id = %s AND target_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [self._target_tipo, note_id, target_id])
            return cursor.rowcount > 0
