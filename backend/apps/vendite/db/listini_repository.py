# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per il sottodominio vendite/listini.
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

LISTINI_ORDER_COLUMNS: dict[str, str] = {
    "codice": "l.codice",
    "descrizione": "l.descrizione",
    "utility_descrizione": "u.descrizione",
    "tipologia_descrizione": "lt.descrizione",
    "data_insert": "l.data_insert",
    "data_update": "l.data_update",
}

LISTINO_CREATE_COLUMNS: dict[str, str] = {
    "codice": "text",
    "descrizione": "text",
    "utility_id": "int",
    "tipologia_id": "int",
    "emittente_soggetto_ruolo_id": "int",
    "meta": "jsonb",
    "attivo": "bool",
}

LISTINO_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in LISTINO_CREATE_COLUMNS.items() if key != "codice"
}

VERSIONE_CREATE_COLUMNS: dict[str, str] = {
    "codice_versione": "text",
    "valido_dal": "date",
    "valido_al": "date",
    "meta": "jsonb",
    "attivo": "bool",
}

VERSIONE_UPDATE_COLUMNS: dict[str, str] = dict(VERSIONE_CREATE_COLUMNS)

RIGA_CREATE_COLUMNS: dict[str, str] = {
    "articolo_id": "uuid",
    "uom_id": "int",
    "prezzo": "numeric",
    "meta": "jsonb",
    "attivo": "bool",
}

RIGA_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in RIGA_CREATE_COLUMNS.items() if key not in {"articolo_id", "uom_id"}
}

RIGHE_ORDER_COLUMNS: dict[str, str] = {
    "articolo_codice": "ad.codice",
    "articolo_descrizione": "ad.descrizione",
    "uom_codice": "u.codice",
    "prezzo": "r.prezzo",
    "billing_account_codice": "ba.codice",
    "billing_account_descrizione": "srd_ba.ragione_sociale_completa",
    "utility_descrizione": "cu.descrizione",
}


# Scopo: Aggiunge condizione ILIKE parametrica su due colonne testuali.
def _append_ilike_search(
    *,
    conditions: list[str],
    params: list[Any],
    left_column: str,
    right_column: str,
    search: str | None,
) -> None:
    if search is None:
        return
    conditions.append(f"({left_column} ILIKE %s OR {right_column} ILIKE %s)")
    like_value = f"%{search}%"
    params.extend([like_value, like_value])


# Scopo: Prepara colonne, placeholder e parametri per un INSERT dinamico su colonne whitelisted.
def _prepare_insert_parts(
    *,
    base_fields: list[tuple[str, Any]],
    extra_data: dict[str, Any],
    column_types: dict[str, str],
) -> tuple[list[str], str, list[Any]]:
    fields = list(base_fields) + [
        (key, value) for key, value in extra_data.items() if key in column_types
    ]
    column_names = [field_name for field_name, _ in fields]
    placeholders = ", ".join(
        "%s" if field_name not in column_types else sql_placeholder(column_types[field_name])
        for field_name, _ in fields
    )
    params = [
        field_value if field_name not in column_types else to_write_param(field_value, column_types[field_name])
        for field_name, field_value in fields
    ]
    return column_names, placeholders, params


# Scopo: Prepara SET clause e parametri per un UPDATE dinamico su colonne whitelisted.
def _prepare_update_parts(
    *,
    data: dict[str, Any],
    column_types: dict[str, str],
) -> tuple[str, list[Any]] | None:
    fields = [(key, value) for key, value in data.items() if key in column_types]
    if not fields:
        return None
    set_clause = ", ".join(
        f"{field_name} = {sql_placeholder(column_types[field_name])}" for field_name, _ in fields
    )
    params = [
        to_write_param(field_value, column_types[field_name])
        for field_name, field_value in fields
    ]
    return set_clause, params


class ListiniRepository:
    """Repository SQL per listini, versioni, righe (F2-BE-13: rimosso CRUD associazioni)."""

    # Scopo: Restituisce l'elenco listini con filtri opzionali, count e ordinamento whitelist.
    def list_listini(
        self,
        *,
        utility_id: int | None,
        tipologia_id: int | None,
        attivo: bool | None,
        search: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = LISTINI_ORDER_COLUMNS[order_by]
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if utility_id is not None:
            conditions.append("l.utility_id = %s")
            params.append(utility_id)
        if tipologia_id is not None:
            conditions.append("l.tipologia_id = %s")
            params.append(tipologia_id)
        if attivo is not None:
            conditions.append("l.attivo = %s")
            params.append(attivo)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="l.codice",
            right_column="l.descrizione",
            search=search,
        )
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
              FROM vendite.listini l
              LEFT JOIN config.utilities u ON u.id = l.utility_id
              LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
            {where_clause}
        """
        data_sql = f"""
            SELECT
                l.id,
                l.codice,
                l.descrizione,
                l.utility_id,
                u.codice AS utility_codice,
                u.descrizione AS utility_descrizione,
                l.tipologia_id,
                lt.codice AS tipologia_codice,
                lt.descrizione AS tipologia_descrizione,
                l.meta,
                l.attivo,
                l.data_insert,
                l.user_insert,
                l.data_update,
                l.user_update,
                (
                    SELECT COUNT(*)
                      FROM vendite.listini_versioni v
                     WHERE v.listino_id = l.id
                ) AS versioni_count
              FROM vendite.listini l
              LEFT JOIN config.utilities u ON u.id = l.utility_id
              LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
            {where_clause}
             ORDER BY {order_column} {safe_order_dir}, l.id ASC
             LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce il dettaglio singolo del listino con metadati aggregati minimi.
    def get_listino(self, listino_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    l.id,
                    l.codice,
                    l.descrizione,
                    l.utility_id,
                    u.codice AS utility_codice,
                    u.descrizione AS utility_descrizione,
                    l.tipologia_id,
                    lt.codice AS tipologia_codice,
                    lt.descrizione AS tipologia_descrizione,
                    l.meta,
                    l.attivo,
                    l.data_insert,
                    l.user_insert,
                    l.data_update,
                    l.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_versioni v
                         WHERE v.listino_id = l.id
                    ) AS versioni_count
                  FROM vendite.listini l
                  LEFT JOIN config.utilities u ON u.id = l.utility_id
                  LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
                 WHERE l.id = %s
                """,
                [listino_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce il listino usando solo colonne write ammesse.
    def create_listino(self, data: dict[str, Any]) -> int:
        insert_parts = _prepare_insert_parts(
            base_fields=[],
            extra_data=data,
            column_types=LISTINO_CREATE_COLUMNS,
        )
        column_names, placeholders, params = insert_parts
        if not column_names:
            raise ValueError("create_listino_empty_payload")

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.listini ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna il listino sui soli campi forniti nel payload.
    def update_listino(self, listino_id: int, data: dict[str, Any]) -> bool:
        update_parts = _prepare_update_parts(data=data, column_types=LISTINO_UPDATE_COLUMNS)
        if update_parts is None:
            return False
        set_clause, params = update_parts
        params.append(listino_id)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini
                   SET {set_clause}
                 WHERE id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina un listino. Usato solo quando il listino non ha figli
    #        (zero versioni): il guard di counts e' nel service.
    def delete_listino(self, listino_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.listini WHERE id = %s",
                [listino_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce le versioni del listino con conteggio righe e ordinamento stabile.
    def list_versioni(self, listino_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    v.id,
                    v.listino_id,
                    v.codice_versione,
                    v.valido_dal,
                    v.valido_al,
                    v.stato,
                    v.meta,
                    v.attivo,
                    v.data_insert,
                    v.user_insert,
                    v.data_update,
                    v.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_righe r
                         WHERE r.listino_versione_id = v.id
                    ) AS righe_count
                  FROM vendite.listini_versioni v
                 WHERE v.listino_id = %s
                 ORDER BY v.valido_dal DESC, v.id DESC
                """,
                [listino_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce il dettaglio singolo della versione verificando l'appartenenza al listino.
    def get_versione(self, listino_id: int, versione_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    v.id,
                    v.listino_id,
                    v.codice_versione,
                    v.valido_dal,
                    v.valido_al,
                    v.stato,
                    v.meta,
                    v.attivo,
                    v.data_insert,
                    v.user_insert,
                    v.data_update,
                    v.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_righe r
                         WHERE r.listino_versione_id = v.id
                    ) AS righe_count
                  FROM vendite.listini_versioni v
                 WHERE v.listino_id = %s
                   AND v.id = %s
                """,
                [listino_id, versione_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova versione nel listino target.
    def create_versione(self, listino_id: int, data: dict[str, Any]) -> int:
        column_names, placeholders, params = _prepare_insert_parts(
            base_fields=[("listino_id", listino_id)],
            extra_data=data,
            column_types=VERSIONE_CREATE_COLUMNS,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.listini_versioni ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna la versione mantenendo il perimetro del listino.
    def update_versione(self, listino_id: int, versione_id: int, data: dict[str, Any]) -> bool:
        update_parts = _prepare_update_parts(data=data, column_types=VERSIONE_UPDATE_COLUMNS)
        if update_parts is None:
            return False
        set_clause, params = update_parts
        params.extend([listino_id, versione_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini_versioni
                   SET {set_clause}
                 WHERE listino_id = %s
                   AND id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Clona una versione esistente in una nuova versione BOZZA dello stesso
    #        listino, copiando tutte le righe attive della sorgente. La nuova versione
    #        prende i dati di testata dal payload (codice_versione, valido_dal,
    #        valido_al); meta e attivo derivano dai default DB. Restituisce
    #        l'id della nuova versione. Esegue tutto in transazione gestita dal caller.
    def clone_versione(
        self,
        listino_id: int,
        src_versione_id: int,
        target_data: dict[str, Any],
    ) -> int:
        # 1) INSERT testata nuova versione (forza stato BOZZA, ignora attivo/meta dal payload)
        target_columns: dict[str, str] = {
            key: value
            for key, value in VERSIONE_CREATE_COLUMNS.items()
            if key in {"codice_versione", "valido_dal", "valido_al"}
        }
        column_names, placeholders, params = _prepare_insert_parts(
            base_fields=[("listino_id", listino_id)],
            extra_data=target_data,
            column_types=target_columns,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.listini_versioni ({", ".join(column_names)}, stato)
                VALUES ({placeholders}, 'BOZZA')
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            target_versione_id = int(row[0])

            # 2) Copy delle righe ATTIVE della sorgente nella nuova versione.
            #    Pricing v5: le dimensioni contesto (BA/utility/emittente)
            #    sono state droppate da listini_righe (F1-DB-25). La riga
            #    e' (articolo, uom, prezzo, meta). Forziamo attivo=TRUE sulla
            #    copia. user_insert/data_insert sono gestiti dai default audit.
            cursor.execute(
                """
                INSERT INTO vendite.listini_righe (
                    listino_versione_id,
                    articolo_id,
                    uom_id,
                    prezzo,
                    meta,
                    attivo
                )
                SELECT
                    %s,
                    articolo_id,
                    uom_id,
                    prezzo,
                    meta,
                    TRUE
                  FROM vendite.listini_righe
                 WHERE listino_versione_id = %s
                   AND attivo IS TRUE
                """,
                [target_versione_id, src_versione_id],
            )

        return target_versione_id

    # Scopo: Elimina una versione e le sue righe in cascata. Usato solo per
    #        versioni in stato BOZZA: il guard di stato e' nel service. La cascade
    #        sulle righe e` esplicita perche' la FK puo' non avere ON DELETE CASCADE
    #        (le righe ATTIVE non vanno mai cancellate, qui si parla solo di BOZZA).
    def delete_versione(self, listino_id: int, versione_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.listini_righe WHERE listino_versione_id = %s",
                [versione_id],
            )
            cursor.execute(
                """
                DELETE FROM vendite.listini_versioni
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce le versioni candidate all'auto-close quando si attiva
    #        una nuova versione (decisione D3). Sono le versioni dello stesso
    #        listino con `attivo = TRUE`, `valido_dal < nuova.valido_dal`, e la
    #        cui `validita` (daterange) si sovrappone al nuovo intervallo. La
    #        versione che si sta per attivare viene esclusa per id. Il filtro
    #        si basa sulla validita` (data-driven), mai sullo stato persistito:
    #        lo stato e` un flag informativo che potrebbe essere stantio, la
    #        data e` la fonte di verita` operativa (principio fail-safe).
    def find_versioni_per_autoclose(
        self,
        listino_id: int,
        exclude_versione_id: int,
        nuova_valido_dal: date,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    codice_versione,
                    valido_dal,
                    valido_al
                  FROM vendite.listini_versioni
                 WHERE listino_id = %s
                   AND id <> %s
                   AND attivo IS TRUE
                   AND valido_dal < %s
                   AND validita && daterange(%s, NULL, '[)')
                 ORDER BY valido_dal
                """,
                [listino_id, exclude_versione_id, nuova_valido_dal, nuova_valido_dal],
            )
            return rows_to_list(cursor)

    # Scopo: Aggiorna solo il valido_al di una versione (usato dall'auto-close
    #        all'attivazione: chiude la precedente al giorno prima della nuova
    #        decorrenza). Operazione atomica usata dentro una transazione caller.
    #        Filtra anche per listino_id come safety guard contro chiamate errate.
    def set_versione_valido_al(self, *, listino_id: int, versione_id: int, valido_al: date) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_versioni
                   SET valido_al = %s
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [valido_al, listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Aggiorna lo stato della versione con check di appartenenza al listino.
    def change_versione_state(self, listino_id: int, versione_id: int, stato: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_versioni
                   SET stato = %s
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [stato, listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Conta le righe prezzo della versione per guard di pubblicazione.
    def count_active_righe_versione(self, versione_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                  FROM vendite.listini_righe
                 WHERE listino_versione_id = %s
                   AND attivo IS TRUE
                """,
                [versione_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Restituisce le righe prezzo della versione con display fields articolo/UoM e contesto,
    #        paginazione server-side e filtri opzionali (search articolo, billing_account, utility).
    def list_righe(
        self,
        listino_id: int,
        versione_id: int,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        attivo: bool | None = True,
        order_by: str = "articolo_descrizione",
        order_dir: str = "asc",
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = RIGHE_ORDER_COLUMNS.get(order_by, "ad.descrizione")
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = ["r.listino_versione_id = %s"]
        params: list[Any] = [versione_id]

        # Join guard: la versione deve appartenere al listino richiesto.
        join_guard_params: list[Any] = [listino_id]

        # billing_account_id / utility_id / emittente_soggetto_ruolo_id sono
        # stati droppati da listini_righe nel cleanup v5 (F1-DB-25): le
        # dimensioni di contesto vivono ora sul listino o sul contratto.
        # I parametri restano nella firma per retrocompatibilita' chiamanti
        # ma sono ignorati.
        _ = billing_account_id
        _ = utility_id
        if attivo is not None:
            conditions.append("r.attivo = %s")
            params.append(attivo)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="ad.codice",
            right_column="ad.descrizione",
            search=search,
        )

        where_clause = "WHERE " + " AND ".join(conditions)

        from_clause = """
              FROM vendite.listini_righe r
              JOIN vendite.listini_versioni v
                ON v.id = r.listino_versione_id
               AND v.listino_id = %s
              LEFT JOIN catalogo.vw_articoli_dettaglio ad
                ON ad.id = r.articolo_id
              LEFT JOIN catalogo.unita_misura u
                ON u.id = r.uom_id
        """

        count_sql = f"SELECT COUNT(*) {from_clause} {where_clause}"
        data_sql = f"""
            SELECT
                r.id,
                r.listino_versione_id,
                r.articolo_id,
                ad.codice AS articolo_codice,
                ad.descrizione AS articolo_descrizione,
                r.uom_id,
                u.codice AS uom_codice,
                u.descrizione AS uom_descrizione,
                r.prezzo,
                r.meta,
                r.attivo,
                r.data_insert,
                r.user_insert,
                r.data_update,
                r.user_update
            {from_clause}
            {where_clause}
             ORDER BY {order_column} {safe_order_dir} NULLS LAST, r.id ASC
             LIMIT %s OFFSET %s
        """

        # Parametri: join_guard (listino_id) + where params, duplicati per count e data.
        count_params = join_guard_params + params
        data_params = join_guard_params + params + [safe_limit, safe_offset]

        with connection.cursor() as cursor:
            cursor.execute(count_sql, count_params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, data_params)
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce il dettaglio singolo della riga prezzo in perimetro listino/versione.
    def get_riga(self, listino_id: int, versione_id: int, riga_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.listino_versione_id,
                    r.articolo_id,
                    r.uom_id,
                    r.prezzo,
                    r.meta,
                    r.attivo,
                    r.data_insert,
                    r.user_insert,
                    r.data_update,
                    r.user_update
                  FROM vendite.listini_righe r
                  JOIN vendite.listini_versioni v
                    ON v.id = r.listino_versione_id
                   AND v.listino_id = %s
                 WHERE r.listino_versione_id = %s
                   AND r.id = %s
                """,
                [listino_id, versione_id, riga_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una riga prezzo nella versione target.
    def create_riga(self, versione_id: int, data: dict[str, Any]) -> int:
        column_names, placeholders, params = _prepare_insert_parts(
            base_fields=[("listino_versione_id", versione_id)],
            extra_data=data,
            column_types=RIGA_CREATE_COLUMNS,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.listini_righe ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una riga prezzo nel perimetro listino/versione.
    def update_riga(self, listino_id: int, versione_id: int, riga_id: int, data: dict[str, Any]) -> bool:
        update_parts = _prepare_update_parts(data=data, column_types=RIGA_UPDATE_COLUMNS)
        if update_parts is None:
            return False
        set_clause, params = update_parts
        params.extend([listino_id, versione_id, riga_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini_righe r
                   SET {set_clause}
                  FROM vendite.listini_versioni v
                 WHERE r.listino_versione_id = v.id
                   AND v.listino_id = %s
                   AND r.listino_versione_id = %s
                   AND r.id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina una riga prezzo mantenendo il check di appartenenza gerarchica.
    def delete_riga(self, listino_id: int, versione_id: int, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM vendite.listini_righe r
                 USING vendite.listini_versioni v
                 WHERE r.listino_versione_id = v.id
                   AND v.listino_id = %s
                   AND r.listino_versione_id = %s
                   AND r.id = %s
                """,
                [listino_id, versione_id, riga_id],
            )
            return cursor.rowcount > 0

    # Scopo: Verifica in un solo round-trip articolo attivo, UoM attiva e coerenza articolo/UoM.
    def get_articolo_uom_validation(self, articolo_id: UUID | str, uom_id: int) -> dict[str, bool]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    EXISTS(
                        SELECT 1
                          FROM catalogo.articoli a
                         WHERE a.id = %s
                           AND a.attivo IS TRUE
                    ) AS articolo_attivo,
                    EXISTS(
                        SELECT 1
                          FROM catalogo.unita_misura u
                         WHERE u.id = %s
                           AND u.attivo IS TRUE
                    ) AS uom_attiva,
                    EXISTS(
                        SELECT 1
                          FROM catalogo.articoli a
                         WHERE a.id = %s
                           AND a.attivo IS TRUE
                           AND a.uom_id = %s
                        UNION ALL
                        SELECT 1
                          FROM catalogo.articoli_uom_operativa uo
                         WHERE uo.articolo_id = %s
                           AND uo.uom_id = %s
                           AND uo.attivo IS TRUE
                    ) AS uom_compatibile
                """,
                [articolo_id, uom_id, articolo_id, uom_id, articolo_id, uom_id],
            )
            row = cursor.fetchone()

        assert row is not None
        return {
            "articolo_attivo": bool(row[0]),
            "uom_attiva": bool(row[1]),
            "uom_compatibile": bool(row[2]),
        }

    # Scopo: Blocca la riga con FOR UPDATE per prevenire race condition durante
    #        la rettifica controllata N6. Restituisce True se la riga esiste.
    def lock_riga_for_update(self, versione_id: int, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM vendite.listini_righe
                 WHERE id = %s AND listino_versione_id = %s
                   FOR UPDATE
                """,
                [riga_id, versione_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Controlla se una riga listino e` stata propagata in commesse o
    #        attivita` fatturabili. Tabelle controllate documentate per espansione
    #        concentrica: commesse_attivita, attivita_fatturabili.
    def check_riga_propagata(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM vendite.commesse_attivita
                     WHERE listino_riga_id = %(riga_id)s
                ) OR EXISTS (
                    SELECT 1 FROM vendite.attivita_fatturabili
                     WHERE listino_riga_id = %(riga_id)s
                ) AS propagata
                """,
                {"riga_id": riga_id},
            )
            row = cursor.fetchone()
            assert row is not None
            return bool(row[0])

    # Scopo: Aggiorna il prezzo di una riga per rettifica controllata N6.
    #        Aggiorna anche meta con audit trail. Caller gestisce transazione.
    def update_riga_prezzo_rettifica(
        self,
        riga_id: int,
        nuovo_prezzo: str,
        meta_aggiornata: dict[str, Any] | None,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_righe
                   SET prezzo = %(prezzo)s::numeric,
                       meta = %(meta)s::jsonb,
                       data_update = now()
                 WHERE id = %(riga_id)s
                """,
                {
                    "riga_id": riga_id,
                    "prezzo": nuovo_prezzo,
                    "meta": json.dumps(meta_aggiornata) if meta_aggiornata else None,
                },
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce versioni ATTIVE in scadenza entro N giorni senza successore.
    #        Filtro temporale isolato per facilitare futura migrazione daterange (N1).
    def _filter_versioni_in_scadenza(self) -> str:
        return (
            "upper(v.validita) IS NOT NULL "
            "AND upper(v.validita) <= CURRENT_DATE + %(giorni)s * INTERVAL '1 day'"
        )

    # Scopo: Lista versioni operativamente attive oggi che scadono entro `giorni`
    #        e non hanno una versione successiva (BOZZA o operativa) che subentra.
    #        Filtri data-driven: "operativamente attiva oggi" = `validita @> CURRENT_DATE`.
    #        Lo stato persistito non viene usato come discriminante (principio
    #        fail-safe: data = fonte di verita`, stato = solo flag informativo
    #        eventualmente stantio). BOZZA e` l'unico stato ammesso come "successore
    #        che subentrera`" perche` monotono e non soggetto a drift.
    def listini_in_scadenza(self, giorni: int) -> list[dict[str, Any]]:
        filtro_scadenza = self._filter_versioni_in_scadenza()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    l.id AS listino_id,
                    l.codice AS listino_codice,
                    l.descrizione AS listino_descrizione,
                    l.utility_id,
                    u.descrizione AS utility_descrizione,
                    v.id AS versione_id,
                    v.codice_versione,
                    v.valido_dal,
                    upper(v.validita) AS valido_al,
                    upper(v.validita) - CURRENT_DATE AS giorni_rimanenti
                  FROM vendite.listini_versioni v
                  JOIN vendite.listini l ON l.id = v.listino_id
                  LEFT JOIN config.utilities u ON u.id = l.utility_id
                 WHERE v.validita @> CURRENT_DATE
                   AND v.attivo IS TRUE
                   AND l.attivo IS TRUE
                   AND {filtro_scadenza}
                   AND NOT EXISTS (
                       SELECT 1
                         FROM vendite.listini_versioni succ
                        WHERE succ.listino_id = v.listino_id
                          AND succ.id != v.id
                          AND succ.attivo IS TRUE
                          AND succ.valido_dal > upper(v.validita)
                          AND (
                              succ.stato = 'BOZZA'
                              OR succ.validita && daterange(upper(v.validita), NULL, '[)')
                          )
                   )
                 ORDER BY v.valido_al ASC, l.codice
                """,
                {"giorni": giorni},
            )
            return rows_to_list(cursor)

    # Scopo: Applica variazione percentuale massa ai prezzi delle righe attive
    #        di una versione. Se dry_run=True restituisce la preview senza modificare.
    #        Restituisce (righe_aggiornate, preview_rows).
    def applica_variazione_percentuale(
        self,
        versione_id: int,
        variazione_pct: str,
        arrotondamento_decimali: int,
        filtro_articoli: list[str] | None = None,
        *,
        dry_run: bool = False,
    ) -> tuple[int, list[dict[str, Any]]]:
        with connection.cursor() as cursor:
            if dry_run:
                # Scopo: calcola i prezzi senza modificare, per preview frontend.
                cursor.execute(
                    """
                    SELECT
                        r.id AS riga_id,
                        a.codice AS articolo_codice,
                        a.descrizione AS articolo_descrizione,
                        r.prezzo AS prezzo_attuale,
                        ROUND(r.prezzo * (1 + %(pct)s::numeric / 100.0), %(dec)s) AS prezzo_calcolato
                      FROM vendite.listini_righe r
                      JOIN catalogo.articoli a ON a.id = r.articolo_id
                     WHERE r.listino_versione_id = %(ver_id)s
                       AND r.attivo IS TRUE
                       AND (%(filtro)s::uuid[] IS NULL
                            OR r.articolo_id = ANY(%(filtro)s::uuid[]))
                     ORDER BY a.codice, r.id
                    """,
                    {
                        "ver_id": versione_id,
                        "pct": variazione_pct,
                        "dec": arrotondamento_decimali,
                        "filtro": filtro_articoli,
                    },
                )
                preview = rows_to_list(cursor)
                return len(preview), preview

            # Scopo: applica UPDATE reale sulle righe.
            cursor.execute(
                """
                UPDATE vendite.listini_righe
                   SET prezzo = ROUND(prezzo * (1 + %(pct)s::numeric / 100.0), %(dec)s),
                       data_update = now()
                 WHERE listino_versione_id = %(ver_id)s
                   AND attivo IS TRUE
                   AND (%(filtro)s::uuid[] IS NULL
                        OR articolo_id = ANY(%(filtro)s::uuid[]))
                """,
                {
                    "ver_id": versione_id,
                    "pct": variazione_pct,
                    "dec": arrotondamento_decimali,
                    "filtro": filtro_articoli,
                },
            )
            return cursor.rowcount, []

    # Scopo: Restituisce le tipologie listino ammesse per una utility, leggendo
    #        la matrice config.listini_tipologie_utilities (solo righe attive).
    def list_tipologie_per_utility(self, utility_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    lt.id,
                    lt.codice,
                    lt.descrizione,
                    lt.e_consumo,
                    lt.e_quota_fissa,
                    lt.e_imposta,
                    lt.e_onere,
                    lt.e_prodotto,
                    lt.e_servizio,
                    lt.ordinamento
                  FROM config.listini_tipologie lt
                  JOIN config.listini_tipologie_utilities m
                    ON m.tipologia_id = lt.id
                 WHERE m.utility_id = %s
                   AND m.attivo = true
                   AND lt.attivo = true
                 ORDER BY lt.ordinamento, lt.descrizione
                """,
                [utility_id],
            )
            return rows_to_list(cursor)
