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


def coerce_jsonb_dict(value: Any) -> dict[str, Any]:
    """Coercion difensiva jsonb -> dict (il driver puo' restituire jsonb come str).

    Promozione regola-del-2 del clone nato in pratiche_repository (2026-06-11)
    e replicato in ui_admin/vendite: JSON malformato o non-oggetto -> {} (mai
    raise: i chiamanti sono path di lettura/display, non validazione input).
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


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


def sql_order_direction(
    order_dir: str | None,
    *,
    default_desc: bool = False,
) -> str:
    """Clausola di direzione ORDER BY con **NULL ordinato come valore MINIMO**.

    Ritorna `'ASC NULLS FIRST'` oppure `'DESC NULLS LAST'`, da interpolare al
    posto della sola direzione: `ORDER BY {col} {direction}, <tiebreak>`.

    **Perche' i NULLS espliciti** (decisione Tid 2026-07-19): i default
    PostgreSQL sono l'opposto (ASC -> NULLS LAST, DESC -> NULLS FIRST), quindi
    un campo vuoto finiva **in cima** proprio ordinando dal piu' recente — il
    caso della lista DDT, dove `numero` e' NULL su TUTTE le bozze (lo assegna
    il trigger a EMESSO). Con questa regola il vuoto sta dove starebbe lo zero.

    Regola del 2 (ok Tid): unifica **29 call-site** in 6 varianti sintattiche
    della stessa espressione (`upper()`/`lower()`/`(order_dir or "")`), di cui
    3 avevano un `NULLS LAST` fisso incollato al template — semantica diversa
    ("il vuoto sempre in coda") che qui viene **uniformata**.

    `default_desc=True` per le liste che ordinano dal piu' recente quando il
    chiamante non specifica nulla.
    """
    fallback = "desc" if default_desc else "asc"
    is_desc = (order_dir or fallback).strip().lower() == "desc"
    return "DESC NULLS LAST" if is_desc else "ASC NULLS FIRST"


def extract_paginated(cursor) -> tuple[list[dict[str, Any]], int]:
    """Estrae risultati paginati da query con COUNT(*) OVER() AS total_count.

    Restituisce (lista dict senza total_count, conteggio totale).
    Pre-computa mappa indici per evitare O(n*m) su cols.index().

    Promozione a BB core (regola del 2, 2026-07-18): nato in
    `anagrafiche/db/_helpers.py` (6 repository), lo stesso lavoro era
    riscritto inline in ~15 siti core/amm (email, dbops, lookup, search...).
    NB: a pagina oltre l'ultima (0 righe) il totale e' 0 — se il chiamante
    deve distinguere "lista vuota" da "pagina stantia" usi
    `fetch_paged_with_total` col fallback.
    """
    rows = cursor.fetchall()
    if not rows:
        return [], 0
    cols = [c.name for c in cursor.description]
    tc_idx = cols.index("total_count")
    total_count = rows[0][tc_idx]
    col_idx = {c: i for i, c in enumerate(cols) if c != "total_count"}
    results = [
        {c: row[i] for c, i in col_idx.items()}
        for row in rows
    ]
    return results, total_count


def fetch_paged_with_total(
    data_sql: str,
    params: list[Any],
    *,
    fallback_count_sql: str | None = None,
    fallback_params: list[Any] | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Esegue una query paginata in UNA valutazione (COUNT(*) OVER()).

    `data_sql` DEVE proiettare `COUNT(*) OVER () AS total_count` e portare
    LIMIT/OFFSET nei propri `params`. Ritorna (righe dict, totale).

    Fallback pagina-oltre-l'ultima: con `offset > 0` e 0 righe la window
    function non puo' dire il totale — se `fallback_count_sql` e' fornita
    viene eseguita SOLO in quel caso (raro), cosi' il chiamante non dichiara
    "0 risultati" a un utente rimasto su una pagina stantia di una lista che
    si e' accorciata sotto di lui (es. code di lavoro che si auto-svuotano).
    Senza fallback il totale e' 0 (comportamento dei siti storici).

    Regola del 2 (2026-07-18): unifica il pattern COUNT-OVER inline dei
    repository core con la variante fallback nata per le code resi.
    """
    with connection.cursor() as cursor:
        cursor.execute(data_sql, params)
        results, total_count = extract_paginated(cursor)
        if not results and offset > 0 and fallback_count_sql is not None:
            cursor.execute(fallback_count_sql, fallback_params or [])
            row = cursor.fetchone()
            total_count = row[0] if row else 0
    return results, total_count


def query_paged_view(
    *,
    select_sql: str,
    order_by: str,
    params: list[Any],
    limit: int,
    offset: int,
    max_limit: int = 200,
) -> tuple[list[tuple], int]:
    """Query paginata su vista/union costosa in UNA valutazione, con CLAMP.

    CTE materializzata + COUNT(*) OVER() + OFFSET clampato all'ultima pagina
    direttamente in SQL: il rientro da una pagina stantia non costa 2-3
    valutazioni della union (data vuota + count fallback + refetch FE) — il
    BE serve subito l'ultima pagina REALE e il service dichiara la pagina
    effettiva nell'envelope. Semantica diversa da `fetch_paged_with_total`
    (che serve la pagina RICHIESTA): usare il clamp solo dove il contratto
    API espone la pagina effettiva (famiglia cruscotti + usePagedDashFetch).

    `select_sql` = SELECT...FROM...WHERE gia' parametrizzato, SENZA
    ORDER/LIMIT; `order_by` = clausola ORDER BY completa su NOMI COLONNA DI
    OUTPUT della SELECT (whitelist a carico del chiamante, MAI input utente).
    Ritorna (rows, total_count): total_count e' SEMPRE l'ultima colonna.

    Promozione a BB core (regola del 2, 2026-07-18) da
    `VenditeRepository._query_paged_view` (estratto 2026-07-07, ok Tid).
    """
    safe_limit = max(1, min(int(limit), max_limit))
    safe_offset = max(0, int(offset))
    # MATERIALIZED esplicito: la CTE e' referenziata due volte (righe +
    # count del clamp) e deve essere valutata una volta sola.
    sql = f"""
        WITH righe AS MATERIALIZED (
            {select_sql}
        )
        SELECT r.*, COUNT(*) OVER () AS total_count
        FROM righe r
        {order_by}
        LIMIT %s
        OFFSET LEAST(
            %s,
            (SELECT GREATEST(COUNT(*) - 1, 0) / %s * %s FROM righe)
        )
    """  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(
            sql, params + [safe_limit, safe_offset, safe_limit, safe_limit]
        )
        rows = cursor.fetchall()
    total_count = int(rows[0][-1]) if rows else 0
    return list(rows), total_count


def dynamic_update(table: str, pk: int, **kwargs: Any) -> bool:
    """UPDATE dinamico "kwargs espliciti": SET dai soli kwargs non-None.

    Delegatore di `sql_write_helpers.execute_dynamic_update(skip_none=True)`
    (unificazione 2026-07-13): None = "non toccare" — per AZZERARE campi
    nullable (PATCH whitelisted) usare il BB direttamente con skip_none=False.
    """
    from apps.core.db.sql_write_helpers import execute_dynamic_update

    return execute_dynamic_update(table, pk, kwargs, skip_none=True)
