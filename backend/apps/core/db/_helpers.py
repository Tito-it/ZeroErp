# Helper condivisi per tutti i repository DB.

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager


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


def escape_ilike(value: str) -> str:
    """Escapa i metacaratteri ILIKE (`%`, `_`, `\\`) nel termine di ricerca.

    Senza escape l'input utente agisce da wildcard (es. cercare "BA_123" o
    "50%" matcha oltre l'atteso). L'escape del backslash va fatto per primo.
    Regola del 2: estratto dai lookup billing_account / istanze_utility /
    soggetti-ruoli che lo duplicavano localmente.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def fetchone_scalar(cursor) -> Any:
    """Ritorna il primo valore della riga corrente (fetchone), riga garantita.

    Pattern per query `INSERT/UPDATE ... RETURNING <col>` e SELECT scalari dove
    il contesto garantisce esattamente una riga. L'`assert` e' un invariante (e
    type-narrowing per il checker): se la query non produce righe e' un bug di
    programmazione, non un input utente da validare.
    """
    row = cursor.fetchone()
    assert row is not None
    return row[0]


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


def resolve_config_id_by_codice_interno(
    tabella: str,
    codice_interno: str,
    *,
    etichetta: str,
    not_found_message: str | None = None,
    function_name: str = "django_service",
) -> int:
    """Risolve l'`id` di una riga config/lookup dal `codice_interno` IMMUTABILE.

    Match SEMPRE sulla colonna `codice_interno` (lockata da
    `script.trgfn_lock_columns`), MAI sul `codice` mutabile (etichetta a video):
    confrontare un literale di logica contro `codice` e' un bug latente (si
    rompe se l'utente rinomina il codice). Filtra `attivo = true`. Solleva
    `E_CONFIG_MANCANTE` se la riga non esiste o non e' attiva.

    Regola del 2: centralizza il pattern
    `SELECT id FROM <config> WHERE codice_interno = %s AND attivo = true`
    ripetuto in piu' repository/service (estratto da
    `pratiche_repository._resolve_stato`; vedi `analisi-hardcoded-codice.md`).

    `tabella` deve essere un identificatore schema-qualificato controllato dal
    codice (mai input utente): viene interpolato nella query.

    `not_found_message` permette al chiamante di preservare un messaggio
    diagnostico specifico (es. hint sul seed mancante); in assenza usa un
    default costruito da `etichetta`.
    """
    sql = f"""
        SELECT id FROM {tabella}
        WHERE codice_interno = %s AND attivo = true
        LIMIT 1
    """  # noqa: S608 — `tabella` e' un identificatore controllato dal codice
    with connection.cursor() as cursor:
        cursor.execute(sql, [codice_interno])
        row = cursor.fetchone()
    ErrorManager.require(
        row is not None,
        code="E_CONFIG_MANCANTE",
        message=(
            not_found_message
            or f"{etichetta} '{codice_interno}' non trovato in {tabella} "
            "(o non attivo)."
        ),
        function_name=function_name,
    )
    assert row is not None
    return int(row[0])


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
