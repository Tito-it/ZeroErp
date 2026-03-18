# Helper condivisi per tutti i repository DB.

from __future__ import annotations

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
