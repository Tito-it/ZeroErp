# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema catalogo (articoli e lookup UoM).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import fetch_con_sonda, row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

# `attivo` e' NUCLEO: lo stato ordina sempre. Aggiunta in anticipo sul seed
# della lista articoli (passata unica 2026-08-01, richiesta del team DB: la
# stessa voce mancava su nove whitelist e sarebbe arrivata un lotto per volta).
ARTICOLI_ORDER_COLUMNS: dict[str, str] = {
    "codice": "a.codice",
    "descrizione": "a.descrizione",
    "uom_codice": "a.uom_codice",
    "attivo": "a.attivo",
    "data_insert": "a.data_insert",
    "data_update": "a.data_update",
}

# Whitelist ORDER BY delle liste UoM (tipi / unita' / conversioni). Costanti di
# modulo (non piu' dict locali ai metodi) cosi' il service deriva le sue
# `_*_ORDER_BY_VALIDI` da qui, unica fonte di verita' — stesso schema di
# ARTICOLI_ORDER_COLUMNS / LISTINI_ORDER_COLUMNS.
# ⚠️ Ogni mappa vale SOLO per la query omonima: l'alias `ut` e' `uom_tipi` in
# `list_uom_tipi`/`list_unita_misura` ma e' l'unita' di misura di DESTINAZIONE
# in `list_uom_conversioni`. Non sono intercambiabili.
#
# `attivo` aggiunta il 2026-08-01 col seed del terzo lotto: la colonna *Attivo*
# e' visibile su tutte e tre le liste, e lo stato appartiene al nucleo sempre
# ordinabile.
UOM_TIPI_ORDER_COLUMNS: dict[str, str] = {  # alias: ut = catalogo.uom_tipi
    "codice": "ut.codice",
    "codice_interno": "ut.codice_interno",
    "descrizione": "ut.descrizione",
    "attivo": "ut.attivo",
    "data_insert": "ut.data_insert",
    "data_update": "ut.data_update",
}

UOM_ORDER_COLUMNS: dict[str, str] = {  # alias: u = catalogo.unita_misura
    "codice": "u.codice",
    "descrizione": "u.descrizione",
    "attivo": "u.attivo",
    "data_insert": "u.data_insert",
    "data_update": "u.data_update",
}

# alias: c = unita_misura_conversioni, uf = UoM origine, ut = UoM destinazione
#
# `valido_dal`/`valido_al` pronte dal 2026-08-01 (regola di dominio: le date di
# validita', quando una lista le mostra, ordinano SEMPRE — e `valido_al` e' il
# default d'elezione). Il seed delle due colonne e' arrivato dal team DB lo
# stesso giorno (lista_colonna 296/297, `ordinabile=t`): contratto allineato,
# presidiato da test_liste_configurabili_seed.
UOM_CONVERSIONI_ORDER_COLUMNS: dict[str, str] = {
    "uom_from_codice": "uf.codice",
    "uom_to_codice": "ut.codice",
    "fattore": "c.fattore",
    "valido_dal": "c.valido_dal",
    "valido_al": "COALESCE(c.valido_al, 'infinity'::date)",
    "attivo": "c.attivo",
}

ARTICOLI_CREATE_COLUMNS: dict[str, str] = {
    "codice": "text",
    "descrizione": "text",
    "descrizione_breve": "text",
    "uom_id": "int",
    "tipo_voce_id": "int",
    "gruppo_voce_id": "int",
    "spesa_id": "int",
    "iva_id": "int",
    "conto_contabile_vendita_id": "int",
    "conto_contabile_acquisto_id": "int",
    "is_composito": "bool",
    "is_solo_componente": "bool",
    "requires_serial": "bool",
    "listino_tipologia_id": "int",
    "natura_vendita_id": "int",
    # Blocco B del brief modifiche certe (2026-09-13): DA DOVE arriva l'articolo.
    # `modo_approvvigionamento_id` e' NOT NULL con DEFAULT ACQUISTO (come
    # `natura_vendita_id`), `gestito_a_magazzino` NOT NULL DEFAULT false
    # (fail-safe), `lead_time_giorni` nullable con CHECK >= 0 (NULL = «non si
    # applica», per una prestazione; `0` NON e' «non si applica»).
    "modo_approvvigionamento_id": "int",
    "gestito_a_magazzino": "bool",
    "lead_time_giorni": "int",
    "meta": "jsonb",
}

# Scopo: Whitelist colonne UPDATE articolo. Esclude codice e uom_id che sono
# entrambi immutabili (lock_columns DDL). Esclude attivo (Fase 7: la
# disattivazione/riattivazione passa solo dagli endpoint dedicati
# /disattiva/ e /riattiva/, non da PATCH).
ARTICOLI_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in ARTICOLI_CREATE_COLUMNS.items() if key not in {"codice", "uom_id"}
}

ARTICOLI_DETAIL_COLUMNS: tuple[str, ...] = (
    "a.id",
    "a.codice",
    "a.descrizione",
    "a.descrizione_breve",
    "a.uom_id",
    "a.tipo_voce_id",
    "a.gruppo_voce_id",
    "a.spesa_id",
    "a.iva_id",
    "a.conto_contabile_vendita_id",
    "a.conto_contabile_acquisto_id",
    "a.is_composito",
    "a.is_solo_componente",
    "a.requires_serial",
    "a.listino_tipologia_id",
    "a.meta",
    "a.user_insert",
    "a.user_update",
    "a.data_insert",
    "a.data_update",
    "a.tx_id",
    "a.storicizza",
    "a.attivo",
    "a.note_target_tipo",
    "a.note_id",
    "a.uom_ref_id",
    "a.uom_codice",
    "a.uom_descrizione",
    "a.tipologia_ref_id",
    "a.tipologia_codice",
    "a.tipologia_descrizione",
    "a.gruppo_ref_id",
    "a.gruppo_codice",
    "a.gruppo_descrizione",
    "a.spesa_ref_id",
    "a.spesa_codice",
    "a.spesa_descrizione",
    "a.iva_ref_id",
    "a.iva_codice",
    "a.iva_descrizione",
    "a.iva_aliquota_iva",
    "a.tipologia_listino_codice",
    "a.tipologia_listino_descrizione",
    # Natura di vendita (modello split: instradamento ordine/commessa/contratto).
    "a.natura_vendita_id",
    "a.natura_vendita_codice_interno",
    "a.natura_vendita_descrizione",
    "a.natura_vendita_destinazione_tipo",
    # Capability BoM (Fase 6): true se l'articolo puo' avere distinta base.
    # motivo_non_gestibile_bom: 'ARTICOLO_SOLO_COMPONENTE' | 'ARTICOLO_NON_COMPOSITO' | NULL.
    "a.puo_gestire_bom",
    "a.motivo_non_gestibile_bom",
    # Modo di approvvigionamento (Blocco B, brief modifiche certe): decodifica
    # sulla forma di `natura_vendita_*` — `codice_interno` per la logica,
    # `descrizione` a video. ⛔ NON `_codice`: il valore viene dalla colonna
    # immutabile e il nome mentirebbe sulla sorgente (linee-guida-sql §6c).
    # ⚠️ Proiezione ESPLICITA: senza queste righe le colonne della lista 26
    # (747-749) e il drawer non vedrebbero niente — cella vuota, nessun rosso.
    "a.modo_approvvigionamento_id",
    "a.modo_approvvigionamento_codice_interno",
    "a.modo_approvvigionamento_descrizione",
    "a.gestito_a_magazzino",
    "a.lead_time_giorni",
)


# Scopo: Aggiunge una condizione di ricerca ILIKE su due colonne testuali.
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

class CatalogoRepository:
    """Repository generico per query articoli e lookup UoM."""

    # Scopo: Restituisce la proiezione SQL esplicita per la vista articoli dettaglio.
    @staticmethod
    def _articoli_detail_projection() -> str:
        return ",\n                    ".join(ARTICOLI_DETAIL_COLUMNS)

    # Scopo: Restituisce elenco articoli da vista dettaglio con filtri opzionali.
    def list_articoli(
        self,
        *,
        attivo: bool | None,
        is_composito: bool | None,
        tipo_voce_id: int | None,
        gruppo_voce_id: int | None,
        listino_tipologia_id: int | None,
        search: str | None,
        data_da: date | None,
        data_a: date | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = ARTICOLI_ORDER_COLUMNS[order_by]
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        # Scopo: Applica solo i filtri realmente valorizzati mantenendo SQL parametrico.
        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if is_composito is not None:
            conditions.append("a.is_composito = %s")
            params.append(is_composito)
        if tipo_voce_id is not None:
            conditions.append("a.tipo_voce_id = %s")
            params.append(tipo_voce_id)
        if gruppo_voce_id is not None:
            conditions.append("a.gruppo_voce_id = %s")
            params.append(gruppo_voce_id)
        if listino_tipologia_id is not None:
            conditions.append("a.listino_tipologia_id = %s")
            params.append(listino_tipologia_id)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="a.codice",
            right_column="a.descrizione",
            search=search,
        )
        if data_da is not None:
            conditions.append("a.data_insert::date >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("a.data_insert::date <= %s")
            params.append(data_a)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
            FROM catalogo.vw_articoli_dettaglio a
            {where_clause}
        """
        data_sql = f"""
            SELECT
                {self._articoli_detail_projection()}
            FROM catalogo.vw_articoli_dettaglio a
            {where_clause}
            ORDER BY {order_column} {safe_order_dir}, a.id {safe_order_dir}
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

    # Scopo: Restituisce singolo articolo arricchito dalla vista dettaglio.
    def get_articolo(self, articolo_id: UUID | str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.vw_articoli_dettaglio a
                WHERE a.id = %s
                """.format(projection=self._articoli_detail_projection()),
                [articolo_id],
            )
            return row_to_dict(cursor)

    # Scopo: Lookup lean del flag `is_composito` di un articolo. Single
    # source of truth per i caller cross-dominio (preventivi/contratti/
    # ordini/ddt) che devono decidere se invocare auto-init componenti
    # post create_riga. Ritorna False se articolo non trovato (defensive).
    # Estratto da `*Repository.is_articolo_composito` duplicato simmetrico
    # (Fase H residue 2026-05-14): i repo sorgente ora delegano qui.
    def is_articolo_composito(self, articolo_id: UUID | str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT is_composito FROM catalogo.articoli WHERE id = %s",
                [str(articolo_id)],
            )
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    # Scopo: Inserisce un articolo usando solo colonne esplicitamente ammesse.
    def create_articolo(self, data: dict[str, Any]) -> UUID:
        fields = [(key, value) for key, value in data.items() if key in ARTICOLI_CREATE_COLUMNS]
        if not fields:
            raise ValueError("create_articolo_empty_payload")

        column_names = [field_name for field_name, _ in fields]
        placeholders = ", ".join(
            sql_placeholder(ARTICOLI_CREATE_COLUMNS[field_name])
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, ARTICOLI_CREATE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO catalogo.articoli ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return row[0]

    # Scopo: Aggiorna i soli campi presenti nel payload, supportando anche NULL espliciti.
    def update_articolo(self, articolo_id: UUID | str, data: dict[str, Any]) -> bool:
        fields = [(key, value) for key, value in data.items() if key in ARTICOLI_UPDATE_COLUMNS]
        if not fields:
            return False

        set_clause = ", ".join(
            f"{field_name} = {sql_placeholder(ARTICOLI_UPDATE_COLUMNS[field_name])}"
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, ARTICOLI_UPDATE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]
        params.append(articolo_id)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli
                SET {set_clause}
                WHERE id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Disattiva un articolo mantenendo la semantica soft-delete prevista dal dominio.
    def deactivate_articolo(self, articolo_id: UUID | str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE catalogo.articoli
                SET attivo = FALSE
                WHERE id = %s
                  AND attivo IS DISTINCT FROM FALSE
                """,
                [articolo_id],
            )
            return cursor.rowcount > 0

    # Scopo: Riattiva un articolo via fn DB dedicata (Fase 7).
    # La fn `catalogo.fn_riattiva_articolo` e' idempotente su gia' attivo
    # e raise E_ARTICOLO_NOT_FOUND se id NULL/inesistente. Pattern "padre
    # prima, figli poi": non tocca i figli (UoM operative, righe BoM, ecc.).
    def reactivate_articolo(self, articolo_id: UUID | str) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT catalogo.fn_riattiva_articolo(%s)",
                [articolo_id],
            )

    # Scopo: Restituisce lookup articoli per autocomplete cross-dominio.
    def lookup_articoli(
        self,
        *,
        search: str | None,
        attivo: bool | None,
        is_composito: bool | None,
        is_solo_componente: bool | None = None,
        escludi_destinazione_tipi: list[str] | None = None,
        solo_oneri: bool = False,
        limit: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        safe_limit = max(1, min(int(limit), 50))
        conditions: list[str] = []
        params: list[Any] = []
        # Il JOIN sulla base `catalogo.articoli` serve a piu' filtri (natura,
        # causale onere): si aggiunge UNA volta sola, con lo stesso alias.
        needs_articoli_join = False
        join_clause = ""

        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="a.codice",
            right_column="a.descrizione",
            search=search,
        )
        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if is_composito is not None:
            conditions.append("a.is_composito = %s")
            params.append(is_composito)
        if is_solo_componente is not None:
            conditions.append("a.is_solo_componente = %s")
            params.append(is_solo_componente)
        # Filtro natura data-driven (difesa in profondità del modello split per
        # natura, brief-preventivi-ordini.md §7.3): esclude gli articoli la cui
        # natura ha una destinazione vietata sul documento chiamante — es. la
        # destinazione CONTRATTO (ricorrente) non è ammessa sul preventivo (D9).
        # Il filtro è sulla DESTINAZIONE, non sul codice natura (coerente col
        # guard DB data-driven). JOIN dalla base `catalogo.articoli` perché la
        # vista non espone la natura. **LEFT JOIN + NULL-tolerant**: un articolo
        # con natura NULL (pregresso/anomalia) NON viene nascosto silenziosamente
        # dal picker — viene escluso solo se la sua destinazione è tra quelle
        # vietate. Coerente col "NULL = include" di fn_list_preventivi_da_pushare.
        if escludi_destinazione_tipi:
            needs_articoli_join = True
            join_clause += " LEFT JOIN config.nature_vendita nv ON nv.id = art.natura_vendita_id"
            conditions.append(
                "(nv.destinazione_tipo IS NULL"
                " OR nv.destinazione_tipo <> ALL(%s::text[]))"
            )
            params.append(list(escludi_destinazione_tipi))

        # Porta oneri: un articolo E' un onere se ha una causale collegata
        # (`causale_onere_id` NOT NULL, legame 1:1 — brief porta-oneri §4c.8).
        # La vista dettaglio non espone la causale: JOIN sulla base + vocabolario
        # per portare a video la causale accanto all'articolo (display fields lato
        # BE, il FE non fa lookup client-side).
        extra_cols = ""
        if solo_oneri:
            needs_articoli_join = True
            join_clause += " JOIN config.causali_onere co ON co.id = art.causale_onere_id"
            conditions.append("art.causale_onere_id IS NOT NULL")
            extra_cols = (
                ",\n                    art.causale_onere_id,"
                "\n                    co.codice AS causale_onere_codice,"
                "\n                    co.descrizione AS causale_onere_descrizione"
            )

        if needs_articoli_join:
            join_clause = " LEFT JOIN catalogo.articoli art ON art.id = a.id" + join_clause

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # ⛔ Il TETTO lo conosce solo questo metodo, che clampa: la sonda si
        #    chiama da qui e non dal service, o il limite finirebbe scritto in
        #    due sedi che divergono al primo cambio. Il `+1`, il taglio e il
        #    flag stanno insieme dentro `fetch_con_sonda` — sono una cosa sola.
        #    Vedi migliorie-generali-BE-FE-da-test-valutazione.md §D6.
        # ⚠️ La sonda regge perche' i tre JOIN qui sopra sono 1:1 (`art` sulla
        #    PK, `nv` e `co` su una FK): un JOIN che moltiplicasse le righe le
        #    farebbe contare due volte, e l'elenco direbbe «troncato» quando e'
        #    intero. Chi aggiunge un JOIN a questa query deve guardare qui.
        return fetch_con_sonda(
            f"""
            SELECT
                a.id,
                a.codice,
                a.descrizione,
                a.uom_codice,
                a.uom_descrizione,
                a.is_composito,
                a.attivo,
                a.iva_id,
                a.iva_codice,
                a.iva_descrizione,
                a.iva_aliquota_iva{extra_cols}
            FROM catalogo.vw_articoli_dettaglio a
            {join_clause}
            {where_clause}
            ORDER BY a.codice ASC
            LIMIT %s
            """,  # noqa: S608 — frammenti da letterali interni, valori parametrizzati
            params,
            limite=safe_limit,
        )

    # --- Sezione CRUD uom_tipi ---

    # Scopo: Restituisce elenco paginato tipologie UoM con filtri opzionali.
    def list_uom_tipi(
        self,
        *,
        attivo: bool | None,
        search: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = UOM_TIPI_ORDER_COLUMNS.get(order_by, "ut.descrizione")
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("ut.attivo = %s")
            params.append(attivo)
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        if search_pattern:
            conditions.append(
                "(ut.codice ILIKE %s OR ut.codice_interno ILIKE %s OR ut.descrizione ILIKE %s)"
            )
            params.extend([search_pattern, search_pattern, search_pattern])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM catalogo.uom_tipi ut {where_clause}",
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT ut.id, ut.codice, ut.codice_interno, ut.descrizione, ut.attivo,
                       ut.user_insert, ut.user_update, ut.data_insert, ut.data_update
                FROM catalogo.uom_tipi ut
                {where_clause}
                ORDER BY {order_column} {safe_order_dir}, ut.id {safe_order_dir}
                LIMIT %s OFFSET %s
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce singola tipologia UoM per id.
    def get_uom_tipo(self, tipo_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ut.id, ut.codice, ut.codice_interno, ut.descrizione, ut.attivo,
                       ut.user_insert, ut.user_update, ut.data_insert, ut.data_update
                FROM catalogo.uom_tipi ut
                WHERE ut.id = %s
                """,
                [tipo_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova tipologia UoM.
    def create_uom_tipo(self, data: dict[str, Any]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO catalogo.uom_tipi (codice, codice_interno, descrizione)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                [data["codice"], data["codice_interno"], data["descrizione"]],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una tipologia UoM esistente.
    def update_uom_tipo(self, tipo_id: int, data: dict[str, Any]) -> bool:
        sets: list[str] = []
        params: list[Any] = []
        for key in ("descrizione", "attivo"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        if not sets:
            return False
        params.append(tipo_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE catalogo.uom_tipi SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            return cursor.rowcount > 0

    # --- Sezione CRUD unita_misura ---

    # Scopo: Restituisce elenco paginato unita' di misura con filtri opzionali.
    def list_unita_misura(
        self,
        *,
        attivo: bool | None,
        search: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = UOM_ORDER_COLUMNS.get(order_by, "u.codice")
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("u.attivo = %s")
            params.append(attivo)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="u.codice",
            right_column="u.descrizione",
            search=search,
        )

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM catalogo.unita_misura u {where_clause}",
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT u.id, u.codice, u.descrizione, u.descrizione_fattura,
                       u.tipo_uom_id, ut.codice AS tipo_uom_codice,
                       ut.descrizione AS tipo_uom_descrizione, u.attivo,
                       u.user_insert, u.user_update, u.data_insert, u.data_update
                FROM catalogo.unita_misura u
                JOIN catalogo.uom_tipi ut ON ut.id = u.tipo_uom_id
                {where_clause}
                ORDER BY {order_column} {safe_order_dir}, u.id {safe_order_dir}
                LIMIT %s OFFSET %s
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce singola unita' di misura per id.
    def get_unita_misura(self, uom_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.codice, u.descrizione, u.descrizione_fattura,
                       u.tipo_uom_id, ut.codice AS tipo_uom_codice,
                       ut.descrizione AS tipo_uom_descrizione, u.attivo,
                       u.user_insert, u.user_update, u.data_insert, u.data_update
                FROM catalogo.unita_misura u
                JOIN catalogo.uom_tipi ut ON ut.id = u.tipo_uom_id
                WHERE u.id = %s
                """,
                [uom_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova unita' di misura.
    def create_unita_misura(self, data: dict[str, Any]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO catalogo.unita_misura (codice, descrizione, descrizione_fattura, tipo_uom_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                [data["codice"], data["descrizione"], data.get("descrizione_fattura"), data["tipo_uom_id"]],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una unita' di misura esistente.
    def update_unita_misura(self, uom_id: int, data: dict[str, Any]) -> bool:
        sets: list[str] = []
        params: list[Any] = []
        for key in ("descrizione", "descrizione_fattura", "tipo_uom_id", "attivo"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        if not sets:
            return False
        params.append(uom_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE catalogo.unita_misura SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            return cursor.rowcount > 0

    # =================================================================
    # Conversioni UoM (catalogo.unita_misura_conversioni)
    # =================================================================

    # Scopo: Lista paginata delle conversioni UoM con filtri e join UoM.
    def list_conversioni(
        self, *, search: str | None = None, attivo: bool | None = True,
        uom_id: int | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "uom_from_codice", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = UOM_CONVERSIONI_ORDER_COLUMNS.get(order_by, "uf.codice")
        safe_order_dir = "DESC" if order_dir.upper() == "DESC" else "ASC"
        safe_limit = min(max(limit, 1), 200)
        safe_offset = max(offset, 0)

        conditions: list[str] = []
        params: list[Any] = []
        if attivo is not None:
            conditions.append("c.attivo = %s")
            params.append(attivo)
        if uom_id is not None:
            conditions.append("(c.uom_from_id = %s OR c.uom_to_id = %s)")
            params.extend([uom_id, uom_id])
        if search and search.strip():
            conditions.append("(uf.codice ILIKE %s OR uf.descrizione ILIKE %s OR ut.codice ILIKE %s OR ut.descrizione ILIKE %s)")
            p = f"%{search.strip()}%"
            params.extend([p, p, p, p])
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM catalogo.unita_misura_conversioni c JOIN catalogo.unita_misura uf ON uf.id = c.uom_from_id JOIN catalogo.unita_misura ut ON ut.id = c.uom_to_id {where_clause}", params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT c.id, c.uom_from_id, c.uom_to_id, c.fattore,
                       c.valido_dal, c.valido_al, c.attivo,
                       uf.codice AS uom_from_codice, uf.descrizione AS uom_from_descrizione,
                       ut.codice AS uom_to_codice, ut.descrizione AS uom_to_descrizione
                FROM catalogo.unita_misura_conversioni c
                JOIN catalogo.unita_misura uf ON uf.id = c.uom_from_id
                JOIN catalogo.unita_misura ut ON ut.id = c.uom_to_id
                {where_clause}
                ORDER BY {order_column} {safe_order_dir}, c.id {safe_order_dir}
                LIMIT %s OFFSET %s
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)
        return results, total_count

    # Scopo: Restituisce singola conversione UoM per id.
    def get_conversione(self, conv_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.uom_from_id, c.uom_to_id, c.fattore,
                       c.valido_dal, c.valido_al, c.attivo,
                       uf.codice AS uom_from_codice, uf.descrizione AS uom_from_descrizione,
                       ut.codice AS uom_to_codice, ut.descrizione AS uom_to_descrizione
                FROM catalogo.unita_misura_conversioni c
                JOIN catalogo.unita_misura uf ON uf.id = c.uom_from_id
                JOIN catalogo.unita_misura ut ON ut.id = c.uom_to_id
                WHERE c.id = %s
                """,
                [conv_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova conversione UoM.
    def create_conversione(self, data: dict[str, Any]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO catalogo.unita_misura_conversioni
                       (uom_from_id, uom_to_id, fattore, valido_dal, valido_al)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                [data["uom_from_id"], data["uom_to_id"], data["fattore"],
                 data.get("valido_dal"), data.get("valido_al")],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una conversione UoM esistente.
    def update_conversione(self, conv_id: int, data: dict[str, Any]) -> bool:
        sets: list[str] = []
        params: list[Any] = []
        for key in ("fattore", "valido_dal", "valido_al", "attivo"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        if not sets:
            return False
        params.append(conv_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE catalogo.unita_misura_conversioni SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Disattiva una unita' di misura (soft delete).
    def deactivate_unita_misura(self, uom_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE catalogo.unita_misura SET attivo = FALSE
                WHERE id = %s AND attivo IS DISTINCT FROM FALSE
                """,
                [uom_id],
            )
            return cursor.rowcount > 0
