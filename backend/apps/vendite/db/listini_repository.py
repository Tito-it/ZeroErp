# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per il sottodominio vendite/listini.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

LISTINI_ORDER_COLUMNS: dict[str, str] = {
    "codice": "l.codice",
    "descrizione": "l.descrizione",
    "dominio": "l.dominio",
    "data_insert": "l.data_insert",
    "data_update": "l.data_update",
}

LISTINO_CREATE_COLUMNS: dict[str, str] = {
    "codice": "text",
    "descrizione": "text",
    "dominio": "text",
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
    "priorita": "int",
    "meta": "jsonb",
    "attivo": "bool",
}

VERSIONE_UPDATE_COLUMNS: dict[str, str] = dict(VERSIONE_CREATE_COLUMNS)

RIGA_CREATE_COLUMNS: dict[str, str] = {
    "articolo_id": "uuid",
    "uom_id": "int",
    "billing_account_id": "int",
    "utility_id": "int",
    "emittente_soggetto_ruolo_id": "int",
    "prezzo": "numeric",
    "meta": "jsonb",
    "attivo": "bool",
}

RIGA_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in RIGA_CREATE_COLUMNS.items() if key not in {"articolo_id", "uom_id"}
}

ASSOCIAZIONE_CREATE_COLUMNS: dict[str, str] = {
    "billing_account_id": "int",
    "utility_id": "int",
    "emittente_soggetto_ruolo_id": "int",
    "priorita": "int",
    "valido_dal": "date",
    "valido_al": "date",
    "meta": "jsonb",
    "attivo": "bool",
}

ASSOCIAZIONE_UPDATE_COLUMNS: dict[str, str] = dict(ASSOCIAZIONE_CREATE_COLUMNS)


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
    """Repository SQL per listini, versioni, righe, associazioni e resolver."""

    # Scopo: Restituisce l'elenco listini con filtri opzionali, count e ordinamento whitelist.
    def list_listini(
        self,
        *,
        dominio: str | None,
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

        if dominio is not None:
            conditions.append("l.dominio = %s")
            params.append(dominio)
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
            {where_clause}
        """
        data_sql = f"""
            SELECT
                l.id,
                l.codice,
                l.descrizione,
                l.dominio,
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
                ) AS versioni_count,
                (
                    SELECT COUNT(*)
                      FROM vendite.listini_associazioni a
                     WHERE a.listino_id = l.id
                ) AS associazioni_count
              FROM vendite.listini l
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
                    l.dominio,
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
                    ) AS versioni_count,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_associazioni a
                         WHERE a.listino_id = l.id
                    ) AS associazioni_count
                  FROM vendite.listini l
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
                    v.priorita,
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
                    v.priorita,
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

    # Scopo: Restituisce le righe prezzo della versione con display fields articolo/UoM e contesto.
    def list_righe(self, listino_id: int, versione_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.listino_versione_id,
                    r.articolo_id,
                    ad.codice AS articolo_codice,
                    ad.descrizione AS articolo_descrizione,
                    r.uom_id,
                    u.codice AS uom_codice,
                    u.descrizione AS uom_descrizione,
                    r.billing_account_id,
                    ba.codice AS billing_account_codice,
                    srd_ba.ragione_sociale_completa AS billing_account_descrizione,
                    r.utility_id,
                    cu.codice AS utility_codice,
                    cu.descrizione AS utility_descrizione,
                    r.emittente_soggetto_ruolo_id,
                    srd_em.ragione_sociale_completa AS emittente_descrizione,
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
                  LEFT JOIN catalogo.vw_articoli_dettaglio ad
                    ON ad.id = r.articolo_id
                  LEFT JOIN catalogo.unita_misura u
                    ON u.id = r.uom_id
                  LEFT JOIN anagrafiche.billing_account ba
                    ON ba.id = r.billing_account_id
                  LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd_ba
                    ON srd_ba.soggetto_ruolo_id = ba.soggetto_ruolo_id
                  LEFT JOIN config.utilities cu
                    ON cu.id = r.utility_id
                  LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd_em
                    ON srd_em.soggetto_ruolo_id = r.emittente_soggetto_ruolo_id
                 WHERE r.listino_versione_id = %s
                 ORDER BY ad.codice ASC NULLS LAST, u.codice ASC NULLS LAST, r.id ASC
                """,
                [listino_id, versione_id],
            )
            return rows_to_list(cursor)

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
                    r.billing_account_id,
                    r.utility_id,
                    r.emittente_soggetto_ruolo_id,
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

    # Scopo: Restituisce le associazioni del listino con display fields di contesto,
    #        arricchiti per precaricare l'AutoComplete BA in modalita' edit
    #        (id_fiscale + pdp) senza round-trip aggiuntivi.
    def list_associazioni(self, listino_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.listino_id,
                    a.billing_account_id,
                    ba.codice AS billing_account_codice,
                    ba.utility_id AS billing_account_utility_id,
                    ba.parent_account_id AS billing_account_parent_id,
                    ba_parent.codice AS billing_account_parent_codice,
                    srd_ba.ragione_sociale_completa AS billing_account_ragione_sociale,
                    srd_ba.id_fiscale_univoco_cf_piva AS billing_account_id_fiscale,
                    p_ba.pdp AS billing_account_pdp,
                    ba_u.codice AS billing_account_utility_codice,
                    a.utility_id,
                    cu.codice AS utility_codice,
                    cu.descrizione AS utility_descrizione,
                    a.emittente_soggetto_ruolo_id,
                    srd_em.ragione_sociale_completa AS emittente_descrizione,
                    a.priorita,
                    a.valido_dal,
                    a.valido_al,
                    a.meta,
                    a.attivo,
                    a.data_insert,
                    a.user_insert,
                    a.data_update,
                    a.user_update
                  FROM vendite.listini_associazioni a
                  LEFT JOIN anagrafiche.billing_account ba
                    ON ba.id = a.billing_account_id
                  LEFT JOIN anagrafiche.billing_account ba_parent
                    ON ba_parent.id = ba.parent_account_id
                  LEFT JOIN config.utilities ba_u
                    ON ba_u.id = ba.utility_id
                  LEFT JOIN anagrafiche.istanze_utilities iu_ba
                    ON iu_ba.id = ba.istanza_utility_id
                  LEFT JOIN anagrafiche.pdp p_ba
                    ON p_ba.id = iu_ba.pdp_id
                  LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd_ba
                    ON srd_ba.soggetto_ruolo_id = ba.soggetto_ruolo_id
                  LEFT JOIN config.utilities cu
                    ON cu.id = a.utility_id
                  LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd_em
                    ON srd_em.soggetto_ruolo_id = a.emittente_soggetto_ruolo_id
                 WHERE a.listino_id = %s
                 ORDER BY a.priorita ASC, a.valido_dal DESC, a.id ASC
                """,
                [listino_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce una singola associazione nel perimetro del listino.
    def get_associazione(self, listino_id: int, associazione_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.listino_id,
                    a.billing_account_id,
                    a.utility_id,
                    a.emittente_soggetto_ruolo_id,
                    a.priorita,
                    a.valido_dal,
                    a.valido_al,
                    a.meta,
                    a.attivo,
                    a.data_insert,
                    a.user_insert,
                    a.data_update,
                    a.user_update
                  FROM vendite.listini_associazioni a
                 WHERE a.listino_id = %s
                   AND a.id = %s
                """,
                [listino_id, associazione_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova associazione sul listino target.
    def create_associazione(self, listino_id: int, data: dict[str, Any]) -> int:
        column_names, placeholders, params = _prepare_insert_parts(
            base_fields=[("listino_id", listino_id)],
            extra_data=data,
            column_types=ASSOCIAZIONE_CREATE_COLUMNS,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.listini_associazioni ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una associazione nel perimetro del listino.
    def update_associazione(self, listino_id: int, associazione_id: int, data: dict[str, Any]) -> bool:
        update_parts = _prepare_update_parts(data=data, column_types=ASSOCIAZIONE_UPDATE_COLUMNS)
        if update_parts is None:
            return False
        set_clause, params = update_parts
        params.extend([listino_id, associazione_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini_associazioni
                   SET {set_clause}
                 WHERE listino_id = %s
                   AND id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina una associazione nel perimetro del listino.
    def delete_associazione(self, listino_id: int, associazione_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM vendite.listini_associazioni
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [listino_id, associazione_id],
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

    # Scopo: Esegue il resolver prezzo listino e arricchisce l'output con codici listino/versione.
    def test_resolver(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        billing_account_id: int | None,
        utility_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.listino_id,
                    l.codice AS listino_codice,
                    l.descrizione AS listino_descrizione,
                    r.listino_versione_id,
                    v.codice_versione,
                    v.stato AS versione_stato,
                    r.listino_riga_id,
                    r.listino_associazione_id,
                    r.prezzo,
                    r.match_level
                  FROM vendite.fn_resolve_prezzo_listino(%s, %s, %s, %s, %s, %s) r
                  JOIN vendite.listini l
                    ON l.id = r.listino_id
                  JOIN vendite.listini_versioni v
                    ON v.id = r.listino_versione_id
                """,
                [
                    articolo_id,
                    uom_id,
                    data_riferimento,
                    billing_account_id,
                    utility_id,
                    emittente_soggetto_ruolo_id,
                ],
            )
            result = row_to_dict(cursor)

        assert result is not None
        return result
