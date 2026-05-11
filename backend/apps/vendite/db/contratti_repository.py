# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per vendite.contratti + contratti_righe +
#        contratti_utilities (CRUD v5).
#
#        Il contratto e' il ponte commerciale cliente->listino. Ha tre
#        modalita' di pricing (A: listino + variazione globale,
#        B: listino + override righe, C: interamente negoziato). I
#        vincoli modalita' sono enforced da CHECK + trigger DB; il
#        repository e' sottile e si limita a esporre le colonne
#        whitelisted per INSERT/UPDATE. La generazione del numero e'
#        demandata al service (script.fn_generate_codice('contratto')).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import call_jsonb_fn, row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param


# Mappa colonna -> tipo, usata per placeholder/cast jsonb e adattamento param.
# Solo le colonne che richiedono trattamento speciale devono comparire qui
# (il resto usa '%s' semplice e valore Python passato cosi' com'e').
_COLUMN_TYPES: dict[str, str] = {"meta": "jsonb"}


# Scopo: Restituisce placeholder e value adattati al tipo colonna.
def _ph_and_val(col: str, value: Any) -> tuple[str, Any]:
    col_type = _COLUMN_TYPES.get(col)
    if col_type is None:
        return "%s", value
    return sql_placeholder(col_type), to_write_param(value, col_type)


# Scopo: Whitelist colonne ORDER BY per la lista contratti (SQL injection safe).
_ORDER_COLS_CONTRATTI: dict[str, str] = {
    "numero": "c.numero",
    "data": "c.data",
    "valido_dal": "c.valido_dal",
    "valido_al": "c.valido_al",
    "ba_codice": "ba.codice",
    "ba_ragione_sociale": "ba.ragione_sociale",
    "stato_codice": "sd.codice_interno",
    "categoria_cliente_snapshot_codice": "cc_snap.codice",
    "data_insert": "c.data_insert",
    "data_update": "c.data_update",
}


_SELECT_COLS_CONTRATTO = """
    c.id,
    c.uid,
    c.numero,
    c.billing_account_id,
    srd.ragione_sociale_completa AS ba_ragione_sociale,
    ba.codice AS ba_codice,
    c.istanza_utility_id,
    c.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    c.ambito,
    c.data,
    c.valido_dal,
    c.valido_al,
    c.parent_contratto_id,
    c.stato_doc_contratto_id,
    sd.codice_interno AS stato_codice,
    sd.descrizione AS stato_descrizione,
    c.listino_id,
    l.codice AS listino_codice,
    l.descrizione AS listino_descrizione,
    c.tipo_variazione_globale,
    c.valore_variazione_globale,
    c.categoria_cliente_id_snapshot,
    cc_snap.codice AS categoria_cliente_snapshot_codice,
    cc_snap.descrizione AS categoria_cliente_snapshot_descrizione,
    c.meta,
    c.data_insert,
    c.user_insert,
    c.data_update,
    c.user_update
"""


_FROM_JOINS_CONTRATTO = """
    FROM vendite.contratti c
    JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
    JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
    JOIN config.utilities u ON u.id = c.utility_id
    JOIN config.stati_doc_contratti sd ON sd.id = c.stato_doc_contratto_id
    LEFT JOIN vendite.listini l ON l.id = c.listino_id
    LEFT JOIN anagrafiche.categorie_clienti cc_snap ON cc_snap.id = c.categoria_cliente_id_snapshot
"""


_SELECT_COLS_RIGA = """
    r.id,
    r.contratto_id,
    r.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    r.uom_operativa_id,
    um.codice AS uom_codice,
    um.descrizione AS uom_descrizione,
    r.tipo_erogazione,
    r.fonte_quantita_attesa,
    r.periodicita,
    r.generazione_canone,
    r.competenza_canone,
    r.prezzo_unitario,
    r.quantita,
    r.qta_operativa,
    r.factor_to_base,
    r.ordine,
    r.attivo,
    r.meta,
    r.data_insert,
    r.user_insert,
    r.data_update,
    r.user_update
"""


_FROM_JOINS_RIGA = """
    FROM vendite.contratti_righe r
    JOIN catalogo.articoli a ON a.id = r.articolo_id
    LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_operativa_id
"""


_SELECT_COLS_UTILITY = """
    cu.id,
    cu.contratto_id,
    cu.istanza_utility_id,
    cu.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    cu.istanza_dati_precontrattuali_id,
    cu.tipo_utenza_id,
    tu.codice AS tipo_utenza_codice,
    tu.descrizione AS tipo_utenza_descrizione,
    cu.classe_utenza_id,
    clu.codice AS classe_utenza_codice,
    clu.descrizione AS classe_utenza_descrizione,
    cu.param_1_num,
    cu.param_2_txt,
    cu.meta,
    cu.data_insert,
    cu.user_insert,
    cu.data_update,
    cu.user_update
"""


_FROM_JOINS_UTILITY = """
    FROM vendite.contratti_utilities cu
    JOIN config.utilities u ON u.id = cu.utility_id
    LEFT JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
    LEFT JOIN config.classi_utenze clu ON clu.id = cu.classe_utenza_id
"""


class ContrattiRepository:
    """Accesso DB a `vendite.contratti` + righe + utility 1:1."""

    # =================================================================
    # Lista e dettaglio testata
    # =================================================================

    # Scopo: Lista paginata contratti filtrabile per cliente/stato/utility/
    #        ambito + search su numero + intervallo validita' esplicito.
    def list_contratti(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_doc_contratto_id: int | None = None,
        utility_id: int | None = None,
        ambito: str | None = None,
        listino_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        scadenza_mese: str | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "data",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS_CONTRATTI.get(order_by, _ORDER_COLS_CONTRATTI["data"])
        direction = "DESC" if order_dir and order_dir.lower() == "desc" else "ASC"
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        if billing_account_id is not None:
            conditions.append("c.billing_account_id = %s")
            params.append(billing_account_id)
        if stato_doc_contratto_id is not None:
            conditions.append("c.stato_doc_contratto_id = %s")
            params.append(stato_doc_contratto_id)
        if utility_id is not None:
            conditions.append("c.utility_id = %s")
            params.append(utility_id)
        if ambito is not None:
            conditions.append("c.ambito = %s")
            params.append(ambito)
        if listino_id is not None:
            conditions.append("c.listino_id = %s")
            params.append(listino_id)
        # Filtro validita': un contratto e' nel periodo se il suo daterange
        # overlappa con [data_da, data_a]. Usiamo il tipo daterange nativo.
        if data_da is not None and data_a is not None:
            conditions.append("c.validita && daterange(%s::date, %s::date, '[]')")
            params.extend([data_da, data_a])
        elif data_da is not None:
            conditions.append("(upper(c.validita) IS NULL OR upper(c.validita) > %s::date)")
            params.append(data_da)
        elif data_a is not None:
            conditions.append("lower(c.validita) <= %s::date")
            params.append(data_a)
        # Filtro scadenza mese: contratti il cui ultimo giorno di validita'
        # cade nel mese indicato (formato YYYY-MM). PostgreSQL daterange
        # upper() ritorna il bound ESCLUSIVO (giorno dopo l'ultimo incluso):
        # per [2026-01-01, 2026-12-31] il DB salva [2026-01-01, 2027-01-01)
        # e upper() = 2027-01-01. Il giorno effettivo e' upper()-1.
        if scadenza_mese is not None:
            conditions.append(
                "(upper(c.validita) IS NOT NULL"
                " AND (upper(c.validita) - 1) >= %s::date"
                " AND (upper(c.validita) - 1) < (%s::date + interval '1 month')::date)"
            )
            primo_mese = f"{scadenza_mese}-01"
            params.extend([primo_mese, primo_mese])
        if search:
            conditions.append("(c.numero ILIKE %s OR srd.ragione_sociale_completa ILIKE %s)")
            like = f"%{search.strip()}%"
            params.extend([like, like])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  {_FROM_JOINS_CONTRATTO}
                {where_clause}
                """,  # noqa: S608
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_CONTRATTO}
                  {_FROM_JOINS_CONTRATTO}
                {where_clause}
                 ORDER BY {order_column} {direction}, c.id ASC
                 LIMIT %s OFFSET %s
                """,  # noqa: S608
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singolo contratto (solo testata, senza righe/utility).
    def get_contratto(self, contratto_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_CONTRATTO}
                  {_FROM_JOINS_CONTRATTO}
                 WHERE c.id = %s
                """,  # noqa: S608
                [contratto_id],
            )
            return row_to_dict(cursor)

    # Scopo: Restituisce il contesto minimo richiesto dal motore documentale
    #        per generare un documento da contratto: `id`, `uid` e
    #        `emittente_fiscale_id`. I contratti non hanno la colonna
    #        emittente diretta: si risolve la PK reale dell'emittente dalla
    #        catena del billing account tramite funzione anagrafiche.
    def get_for_documento_generation(
        self, contratto_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                c.id,
                c.uid::text AS uid,
                anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id)
                    AS emittente_fiscale_id
              FROM vendite.contratti c
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contratto_id)])
            return row_to_dict(cursor)

    # Scopo: Capability del contratto per il detail API (Fase 1.B2 refactor
    #        frontend vendite). Wrapper su `script.fn_available_actions_contratto`
    #        che ritorna jsonb con available_actions (azione "cessa" arricchita
    #        runtime con default_date e min_date), can_change_state,
    #        can_edit_testata/righe, non_editable_fields, stato_codice.
    #        Blob opaco lato Python: passato al FE intatto.
    #        Ritorna {} se la fn ritorna NULL (contratto inesistente — caller
    #        deve aver gia' verificato l'esistenza).
    def get_capabilities(self, contratto_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_contratto", contratto_id)

    # =================================================================
    # Mutazioni testata
    # =================================================================

    # Scopo: Inserisce un contratto. `numero` gia' generato dal service.
    #        Colonne whitelisted. Trigger DB impostera' `validita` da
    #        valido_dal/al e validera' coerenza modalita' via CHECK.
    def create_contratto(self, data: dict[str, Any]) -> int:
        write_cols = (
            "numero",
            "billing_account_id",
            "istanza_utility_id",
            "utility_id",
            "ambito",
            "valido_dal",
            "valido_al",
            "parent_contratto_id",
            "stato_doc_contratto_id",
            "data",
            "listino_id",
            "tipo_variazione_globale",
            "valore_variazione_globale",
            "categoria_cliente_id_snapshot",
            "meta",
        )
        cols: list[str] = []
        vals: list[Any] = []
        placeholders: list[str] = []
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                cols.append(col)
                placeholders.append(ph)
                vals.append(val)
        sql = f"""
            INSERT INTO vendite.contratti ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna una testata contratto. `numero` immutabile (trigger
    #        lock_columns). stato_doc_contratto_id si aggiorna via
    #        update_stato() per leggibilita'.
    def update_contratto(self, contratto_id: int, data: dict[str, Any]) -> bool:
        write_cols = (
            "ambito",
            "valido_dal",
            "valido_al",
            "parent_contratto_id",
            "data",
            "listino_id",
            "tipo_variazione_globale",
            "valore_variazione_globale",
            "categoria_cliente_id_snapshot",
            "meta",
        )
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                set_parts.append(f"{col} = {ph}")
                vals.append(val)
        if not set_parts:
            return False
        vals.append(contratto_id)
        sql = f"""
            UPDATE vendite.contratti
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Cambia lo stato documentale del contratto. Il trigger
    #        trgfn_contratti_guard_modalita_c_activation fa fail-fast
    #        se modalita' C e righe incomplete.
    def update_stato(self, contratto_id: int, stato_doc_contratto_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.contratti
                   SET stato_doc_contratto_id = %s
                 WHERE id = %s
                """,
                [stato_doc_contratto_id, contratto_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Contratti_righe
    # =================================================================

    # Scopo: Lista righe di un contratto, ordinate per campo `ordine` poi id.
    def list_righe(self, contratto_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_RIGA}
                  {_FROM_JOINS_RIGA}
                 WHERE r.contratto_id = %s
                 ORDER BY r.ordine ASC, r.id ASC
                """,  # noqa: S608
                [contratto_id],
            )
            return rows_to_list(cursor)

    # Scopo: Preview righe applicate dal contratto in modalita' A o B.
    #        Restituisce due insiemi UNIONati:
    #          1. Righe del listino associato (versione operativa oggi via
    #             `validita @> CURRENT_DATE`) con prezzo_finale = override se
    #             esiste, altrimenti prezzo listino + variazione globale.
    #          2. Righe override del contratto (contratti_righe) che NON
    #             trovano corrispondenza articolo+uom nel listino: scenario
    #             tipico in modalita' B con prodotti negoziati a parte non
    #             inclusi nel listino base.
    #        Modalita' C ritorna lista vuota dal service (nessun listino, le
    #        righe vivono gia' in contratti_righe e sono lette da list_righe).
    #
    #        Origine per riga:
    #          'OVERRIDE'    -> esiste contratti_righe (sia con match listino
    #                           sia extra-listino: il prezzo_finale e' override)
    #          'DA_LISTINO'  -> riga listino senza override, prezzo calcolato
    #
    #        Formula variazione (riga listino senza override):
    #          PERCENTUALE  -> prezzo_listino * (1 + valore_variazione/100.0)
    #          VALORE_FISSO -> prezzo_listino + valore_variazione
    #          NULL/altro   -> prezzo_listino tal quale
    #        Replica la logica di `vendite.fn_resolve_prezzo_listino_v2` per
    #        lo stadio CONTRATTO_LISTINO (single-pass batch, no round-trip
    #        per riga). Tenere allineato in caso di estensioni della formula.
    def list_righe_preview(self, contratto_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                -- Parte 1: righe del listino con eventuale override matched
                -- per (articolo, uom). prezzo_finale = override se esiste,
                -- altrimenti prezzo listino con variazione globale applicata.
                SELECT
                    a.id AS articolo_id,
                    a.codice AS articolo_codice,
                    a.descrizione AS articolo_descrizione,
                    lr.uom_id,
                    um.codice AS uom_codice,
                    um.descrizione AS uom_descrizione,
                    lr.prezzo AS prezzo_listino,
                    c.tipo_variazione_globale AS tipo_variazione,
                    c.valore_variazione_globale AS valore_variazione,
                    cr.id AS override_riga_id,
                    cr.prezzo_unitario AS override_prezzo,
                    CASE
                        WHEN cr.id IS NOT NULL THEN 'OVERRIDE'
                        ELSE 'DA_LISTINO'
                    END AS origine,
                    CASE
                        WHEN cr.id IS NOT NULL THEN cr.prezzo_unitario
                        WHEN c.tipo_variazione_globale = 'PERCENTUALE' THEN
                            lr.prezzo * (1 + c.valore_variazione_globale / 100.0)
                        WHEN c.tipo_variazione_globale = 'VALORE_FISSO' THEN
                            lr.prezzo + c.valore_variazione_globale
                        ELSE lr.prezzo
                    END AS prezzo_finale
                  FROM vendite.contratti c
                  JOIN vendite.listini_versioni lv ON lv.listino_id = c.listino_id
                                                  AND lv.validita @> CURRENT_DATE
                                                  AND lv.attivo = TRUE
                  JOIN vendite.listini_righe lr ON lr.listino_versione_id = lv.id
                                               AND lr.attivo = TRUE
                  JOIN catalogo.articoli a ON a.id = lr.articolo_id
                  LEFT JOIN catalogo.unita_misura um ON um.id = lr.uom_id
                  LEFT JOIN vendite.contratti_righe cr
                         ON cr.contratto_id = c.id
                        AND cr.articolo_id = lr.articolo_id
                        AND cr.uom_operativa_id = lr.uom_id
                        AND cr.attivo = TRUE
                 WHERE c.id = %s
                   AND c.listino_id IS NOT NULL

                UNION ALL

                -- Parte 2: override extra-listino. Righe contratto che non
                -- hanno match (articolo, uom) nelle righe del listino
                -- operativo oggi. Tipicamente prodotti negoziati a parte
                -- non presenti nel listino base. prezzo_listino e
                -- tipo/valore variazione sono NULL: l'origine e' OVERRIDE
                -- e il prezzo_finale e' direttamente cr.prezzo_unitario.
                SELECT
                    a.id AS articolo_id,
                    a.codice AS articolo_codice,
                    a.descrizione AS articolo_descrizione,
                    cr.uom_operativa_id AS uom_id,
                    um.codice AS uom_codice,
                    um.descrizione AS uom_descrizione,
                    NULL::numeric AS prezzo_listino,
                    NULL::text AS tipo_variazione,
                    NULL::numeric AS valore_variazione,
                    cr.id AS override_riga_id,
                    cr.prezzo_unitario AS override_prezzo,
                    'OVERRIDE' AS origine,
                    cr.prezzo_unitario AS prezzo_finale
                  FROM vendite.contratti_righe cr
                  JOIN catalogo.articoli a ON a.id = cr.articolo_id
                  LEFT JOIN catalogo.unita_misura um ON um.id = cr.uom_operativa_id
                 WHERE cr.contratto_id = %s
                   AND cr.attivo = TRUE
                   AND NOT EXISTS (
                       SELECT 1
                         FROM vendite.contratti c2
                         JOIN vendite.listini_versioni lv2
                              ON lv2.listino_id = c2.listino_id
                             AND lv2.validita @> CURRENT_DATE
                             AND lv2.attivo = TRUE
                         JOIN vendite.listini_righe lr2
                              ON lr2.listino_versione_id = lv2.id
                             AND lr2.articolo_id = cr.articolo_id
                             AND lr2.uom_id = cr.uom_operativa_id
                             AND lr2.attivo = TRUE
                        WHERE c2.id = cr.contratto_id
                   )

                 ORDER BY articolo_codice ASC, uom_codice ASC
                """,
                [contratto_id, contratto_id],
            )
            return rows_to_list(cursor)

    # Scopo: Dettaglio singola riga (per read-after-write dopo create/update).
    def get_riga(self, riga_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_RIGA}
                  {_FROM_JOINS_RIGA}
                 WHERE r.id = %s
                """,  # noqa: S608
                [riga_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una riga contratto. Il trigger guard modalita' C
    #        scatta se contratto e' ATTIVO e prezzo_unitario NULL.
    def create_riga(self, contratto_id: int, data: dict[str, Any]) -> int:
        write_cols = (
            "articolo_id",
            "tipo_erogazione",
            "fonte_quantita_attesa",
            "periodicita",
            "generazione_canone",
            "competenza_canone",
            "prezzo_unitario",
            "quantita",
            "qta_operativa",
            "uom_operativa_id",
            "factor_to_base",
            "ordine",
            "attivo",
            "meta",
        )
        cols = ["contratto_id"]
        vals: list[Any] = [contratto_id]
        placeholders: list[str] = ["%s"]
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                cols.append(col)
                placeholders.append(ph)
                vals.append(val)
        sql = f"""
            INSERT INTO vendite.contratti_righe ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna una riga contratto sui soli campi forniti.
    def update_riga(self, riga_id: int, data: dict[str, Any]) -> bool:
        write_cols = (
            "tipo_erogazione",
            "fonte_quantita_attesa",
            "periodicita",
            "generazione_canone",
            "competenza_canone",
            "prezzo_unitario",
            "quantita",
            "qta_operativa",
            "uom_operativa_id",
            "factor_to_base",
            "ordine",
            "attivo",
            "meta",
        )
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                set_parts.append(f"{col} = {ph}")
                vals.append(val)
        if not set_parts:
            return False
        vals.append(riga_id)
        sql = f"""
            UPDATE vendite.contratti_righe
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Cancella una riga contratto (hard delete). Il trigger
    #        prevent_deactivate_if_children blocca se ci sono note_contratto
    #        collegate.
    def delete_riga(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.contratti_righe WHERE id = %s",
                [riga_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Contratti_utilities (1:1 con contratto)
    # =================================================================

    # Scopo: Recupera la riga utility associata al contratto (1:1).
    def get_utility(self, contratto_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_UTILITY}
                  {_FROM_JOINS_UTILITY}
                 WHERE cu.contratto_id = %s
                """,  # noqa: S608
                [contratto_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce la riga utility (1:1). Trigger guard tipo/classe
    #        valida coerenza con ambito del contratto.
    def create_utility(self, contratto_id: int, data: dict[str, Any]) -> int:
        write_cols = (
            "istanza_utility_id",
            "utility_id",
            "istanza_dati_precontrattuali_id",
            "tipo_utenza_id",
            "classe_utenza_id",
            "param_1_num",
            "param_2_txt",
            "meta",
        )
        cols = ["contratto_id"]
        vals: list[Any] = [contratto_id]
        placeholders: list[str] = ["%s"]
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                cols.append(col)
                placeholders.append(ph)
                vals.append(val)
        sql = f"""
            INSERT INTO vendite.contratti_utilities ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna la riga utility sul solo subset mutabile.
    def update_utility(self, utility_row_id: int, data: dict[str, Any]) -> bool:
        write_cols = (
            "istanza_dati_precontrattuali_id",
            "tipo_utenza_id",
            "classe_utenza_id",
            "param_1_num",
            "param_2_txt",
            "meta",
        )
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in write_cols:
            if col in data:
                ph, val = _ph_and_val(col, data[col])
                set_parts.append(f"{col} = {ph}")
                vals.append(val)
        if not set_parts:
            return False
        vals.append(utility_row_id)
        sql = f"""
            UPDATE vendite.contratti_utilities
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # =================================================================
    # Lookup tecnici usati dal service
    # =================================================================

    # Codice tipo usato in config.sistema_codici (prefix=CNT, len=7).
    _NUMERO_CODICE_TIPO = "contratto"

    # Scopo: Genera il numero contratto via script.fn_generate_codice.
    def generate_numero(self) -> str:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_generate_codice(%s)",
                [self._NUMERO_CODICE_TIPO],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return str(row[0])

    # Scopo: Risolve stato DRAFT (o lo stato richiesto) dal codice_interno.
    #        Usato in create per impostare stato iniziale standard.
    def get_stato_id_by_codice(self, codice_interno: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM config.stati_doc_contratti
                 WHERE codice_interno = %s
                """,
                [codice_interno],
            )
            row = cursor.fetchone()
            return None if row is None else int(row[0])

    # Scopo: Ritorna il codice_interno dello stato corrente del contratto.
    def get_stato_codice(self, contratto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sd.codice_interno
                  FROM vendite.contratti c
                  JOIN config.stati_doc_contratti sd
                    ON sd.id = c.stato_doc_contratto_id
                 WHERE c.id = %s
                """,
                [contratto_id],
            )
            row = cursor.fetchone()
            return None if row is None else str(row[0])

    # Scopo: Ritorna il codice dell'utility associata al contratto
    #        (necessario al service per decidere se tipo/classe utenza
    #        sono richiesti o vietati — guard pre-DB per UX, il trigger
    #        DB e' autoritativo).
    def get_utility_codice(self, utility_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT codice FROM config.utilities WHERE id = %s",
                [utility_id],
            )
            row = cursor.fetchone()
            return None if row is None else str(row[0])
