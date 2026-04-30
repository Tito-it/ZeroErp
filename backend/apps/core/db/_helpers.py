# Helper condivisi per tutti i repository DB.

from __future__ import annotations

import json
from typing import Any

from django.db import connection


def row_to_dict(cursor) -> dict[str, Any] | None:
    """Converte la riga corrente (fetchone) in dict {colonna: valore}.

    Restituisce None se non ci sono righe.
    """
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [c.name for c in cursor.description]
    return dict(zip(cols, row))


def rows_to_list(cursor) -> list[dict[str, Any]]:
    """Converte tutte le righe (fetchall) in lista di dict."""
    cols = [c.name for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def call_jsonb_fn(fn_name: str, *args: Any) -> dict[str, Any]:
    """Chiama una funzione PostgreSQL che ritorna jsonb e la mappa a dict.

    Pattern condiviso per i wrapper "capability" dei detail API
    (Fase 1 refactor frontend vendite): preventivi/contratti/promo articoli
    chiamano `script.fn_*_<entita>(id)` e ricevono un blob JSONB con
    `available_actions`, `can_*`, `non_editable_fields`.

    Ritorna `{}` se la fn ritorna NULL (entita inesistente — il caller
    deve aver gia' verificato l'esistenza via get_<entita>).
    `psycopg3` adatta jsonb a dict; il branch `isinstance(payload, str)`
    copre solo i backend che ritornano il payload serializzato come testo.

    Esempio:
        capabilities = call_jsonb_fn(
            "script.fn_available_actions_preventivo", preventivo_id,
        )
    """
    placeholders = ", ".join(["%s"] * len(args))
    sql = f"SELECT {fn_name}({placeholders}) AS payload"  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(sql, list(args))
        row = cursor.fetchone()
        if not row or row[0] is None:
            return {}
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload


def dynamic_update(table: str, pk: int, **kwargs: Any) -> bool:
    """UPDATE dinamico generico: costruisce SET da kwargs non-None, strip stringhe.

    Pre-processare i valori prima della chiamata per trasformazioni extra
    (es. upper()). Restituisce True se almeno una riga aggiornata.
    """
    fields: list[str] = []
    params: list[Any] = []
    for col, val in kwargs.items():
        if val is not None:
            if isinstance(val, str):
                val = val.strip()
            fields.append(f"{col} = %s")
            params.append(val)
    if not fields:
        return False
    params.append(pk)
    sql = f"UPDATE {table} SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
