# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per audit trail permessi — query UNION ALL
#        sulle 7 tabelle storico del sistema permessi.
# ------------------------------------------------------------

from __future__ import annotations

import math
from typing import Any

from django.db import connection


class PermissionsAuditRepository:
    """Accesso SQL alle tabelle storico del sistema permessi."""

    _OP_LABELS: dict[int, str] = {
        1: "INIZIALE",
        2: "MODIFICA",
        3: "ELIMINAZIONE",
    }

    # Tabelle storico filtrate per auth_user_id nello snapshot
    _USER_TABLES: list[tuple[str, str]] = [
        ("storico.user_override_aree", "user_override_aree"),
        ("storico.user_override_oggetti", "user_override_oggetti"),
        ("storico.user_override_azioni", "user_override_azioni"),
        ("storico.user_emittenti_fiscali", "user_emittenti_fiscali"),
        ("storico.risorse_umane_auth_user", "risorse_umane_auth_user"),
    ]

    # Tabelle storico filtrate per unita_organizzativa_id nello snapshot
    _DEPT_TABLES: list[tuple[str, str]] = [
        ("storico.profili_reparto_aree", "profili_reparto_aree"),
        ("storico.profili_reparto_azioni", "profili_reparto_azioni"),
    ]

    # Whitelist dei nomi tabella accettati dal filtro `tabella`
    _VALID_TABLE_NAMES: frozenset[str] = frozenset(
        label for _, label in _USER_TABLES + _DEPT_TABLES
    )

    # Scopo: Restituisce la timeline paginata degli eventi audit permessi per un utente.
    # Interroga le 7 tabelle storico via UNION ALL: 5 filtrate per auth_user_id,
    # 2 filtrate per unita_organizzativa_id (escluse se uo_id e' None).
    # Risultato: dict con count, page, page_size, total_pages, events.
    def list_audit_events(
        self,
        *,
        auth_user_id: int,
        uo_id: int | None = None,
        data_da: str | None = None,
        data_a: str | None = None,
        tabella: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        unions: list[str] = []
        params: list[Any] = []

        # Costruisce sub-query per tabelle utente (filtro auth_user_id)
        for schema_table, label in self._USER_TABLES:
            if tabella and tabella != label:
                continue
            unions.append(
                f"SELECT '{label}' AS tabella, "
                f"s.valid_from, s.tipo_operazione, s.user_insert, "
                f"s.snapshot, s.tx_id::text "
                f"FROM {schema_table} s "
                f"WHERE (s.snapshot->>'auth_user_id')::int = %s"
            )
            params.append(auth_user_id)

        # Costruisce sub-query per tabelle reparto (filtro uo_id)
        if uo_id is not None:
            for schema_table, label in self._DEPT_TABLES:
                if tabella and tabella != label:
                    continue
                unions.append(
                    f"SELECT '{label}' AS tabella, "
                    f"s.valid_from, s.tipo_operazione, s.user_insert, "
                    f"s.snapshot, s.tx_id::text "
                    f"FROM {schema_table} s "
                    f"WHERE (s.snapshot->>'unita_organizzativa_id')::int = %s"
                )
                params.append(uo_id)

        if not unions:
            return self._empty_result(page, page_size)

        # Wrapper con filtri data e paginazione
        sql = f"WITH events AS ({' UNION ALL '.join(unions)}) "
        sql += "SELECT tabella, valid_from, tipo_operazione, user_insert, "
        sql += "snapshot, tx_id, COUNT(*) OVER() AS total_count "
        sql += "FROM events WHERE true "

        if data_da:
            sql += "AND valid_from >= %s::timestamptz "
            params.append(data_da)
        if data_a:
            sql += "AND valid_from <= %s::timestamptz "
            params.append(data_a)

        sql += "ORDER BY valid_from DESC, id DESC "

        offset = (page - 1) * page_size
        sql += "LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        if not rows:
            return self._empty_result(page, page_size)

        total_count = rows[0][6]
        events = [
            {
                "tabella": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "tipo_operazione": self._OP_LABELS.get(row[2], str(row[2])),
                "user_modifica": row[3],
                "snapshot": row[4],
                "tx_id": row[5],
            }
            for row in rows
        ]

        return {
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total_count / page_size),
            "events": events,
        }

    @staticmethod
    def _empty_result(page: int, page_size: int) -> dict[str, Any]:
        return {
            "count": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "events": [],
        }
