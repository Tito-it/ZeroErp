# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per vendite.promo_articoli (CRUD admin).
#        Overlay promo temporale per (articolo, uom) — STADIO 0 del resolver
#        prezzi v5: batte listini e matrice categoria. E' l'unico livello
#        che ammette tipo_variazione PREZZO_FISSO (prezzo assoluto).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update


# Colonne jsonb di `vendite.promo_articoli`, dichiarate al BB: una stringa li'
# e' testo JSON (regola Tid 2026-09-26). Il service manda sempre un dict
# (`optional_meta`).
_JSONB_COLS: tuple[str, ...] = ("meta",)


# Whitelist colonne ammesse per ORDER BY (SQL injection safe).
_ORDER_COLS: dict[str, str] = {
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "articolo_codice": "a.codice",
    "articolo_descrizione": "a.descrizione",
    "uom_codice": "um.codice",
    "valido_dal": "p.valido_dal",
    "valido_al": "p.valido_al",
    "attivo": "p.attivo",
    # `tipo_variazione` NON e' in whitelist: nel catalogo la colonna e'
    # `ordinabile=f` (a video e' una cella composita «TIPO: valore», ordinarla
    # per il solo tipo direbbe poco). Tenerla qui sarebbe una capacita' che
    # nessuna colonna puo' richiedere. Se il seed la ribalta a `t`, e' una riga.
    "data_insert": "p.data_insert",
    "data_update": "p.data_update",
}


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ Forma a MAPPA: `articolo_*` sono nomi di USCITA della `_SELECT_COLS`, e il
#    valore e' la STESSA espressione che la SELECT proietta con quel nome — si
#    cerca su cio' che si mostra. `articolo_descrizione` e' la colonna nuova a
#    catalogo (brief-db-ricerca-full-colonne-da-accendere §3.2-bis, Tid).
# ⛔ Il `codice_interno` dell'articolo NON si cerca (Tid, 2026-09-23): e' la
#    chiave del sistema, non il codice dell'operatore.
_RICERCA_PROMO = RicercaFull(
    "vendite.promo_articoli",
    {
        "codice": "p.codice",
        "descrizione": "p.descrizione",
        "articolo_codice": "a.codice",
        "articolo_descrizione": "a.descrizione",
    },
)


_SELECT_COLS = """
    p.id,
    p.codice,
    p.descrizione,
    p.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    p.uom_id,
    um.codice AS uom_codice,
    um.descrizione AS uom_descrizione,
    p.tipo_variazione,
    p.valore_variazione,
    p.valido_dal,
    p.valido_al,
    p.meta,
    p.attivo,
    p.data_insert,
    p.user_insert,
    p.data_update,
    p.user_update
"""


_FROM_JOINS = """
    FROM vendite.promo_articoli p
    JOIN catalogo.articoli a ON a.id = p.articolo_id
    JOIN catalogo.unita_misura um ON um.id = p.uom_id
"""


class PromoArticoliRepository:
    """Accesso DB a `vendite.promo_articoli`."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata delle promo con filtri dimensionali e validita'.
    def list_promo(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        articolo_id: str | None = None,
        uom_id: int | None = None,
        tipo_variazione: str | None = None,
        valid_at: date | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "valido_dal",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["valido_dal"],
            tiebreak="p.id",
            # Il default e' una DATA: parte dalla piu' recente (regola di Tid
            # 2026-09-02). Fino al 2026-10-20 mancava, e la lista partiva ASC.
            default_desc=True,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("p.attivo = %s")
            params.append(attivo)
        if articolo_id is not None:
            conditions.append("p.articolo_id = %s::uuid")
            params.append(str(articolo_id))
        if uom_id is not None:
            conditions.append("p.uom_id = %s")
            params.append(uom_id)
        if tipo_variazione is not None:
            conditions.append("p.tipo_variazione = %s")
            params.append(tipo_variazione)
        if valid_at is not None:
            conditions.append("p.validita @> %s::date")
            params.append(valid_at)
        # ⚠️ Una condizione sola per conteggio e pagina (stessi `conditions`).
        #    Lista non di configurazione: soglia di default del BB, sotto la
        #    quale il termine si ignora (brief §6).
        add_ricerca_full_condition(conditions, params, search, _RICERCA_PROMO)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  {_FROM_JOINS}
                {where_clause}
                """,
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  {_FROM_JOINS}
                {where_clause}
                 ORDER BY {ordinamento}
                 LIMIT %s OFFSET %s
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singola promo con display joinati.
    def get_promo(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  {_FROM_JOINS}
                 WHERE p.id = %s
                """,
                [record_id],
            )
            return row_to_dict(cursor)

    # Scopo: Capability promo per il detail API (Fase 1.B3 refactor frontend
    #        vendite). Wrapper su `script.fn_capability_promo_articolo` che
    #        ritorna jsonb con stato_temporale (FUTURA/INIZIATA/SCADUTA),
    #        can_update (+ reason), min_valido_dal/al, non_editable_fields.
    #        Modello data-driven: nessuna available_actions (no transizioni
    #        manuali). Blob opaco lato Python: passato al FE intatto.
    #        Ritorna {} se la fn ritorna NULL (promo inesistente — caller deve
    #        aver gia' verificato l'esistenza).
    def get_capabilities(self, record_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_capability_promo_articolo", record_id)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Colonne scrivibili in create. `validita` NON c'e': la calcola il trigger
    # da valido_dal/al.
    # ⭐ 2026-09-26: la composizione a mano (`write_cols` + `if col in data`)
    #    e' ritirata a favore del BB core. Il filtro SCARTAVA IN SILENZIO le
    #    chiavi fuori lista: ora e' `RuntimeError`, e il contratto
    #    dell'operatore lo tiene il service (mapper espliciti
    #    `_build_create_data`/`_build_update_data` dopo `validate_allowed_keys`).
    CREATE_COLUMNS: frozenset[str] = frozenset({
        "codice",
        "descrizione",
        "articolo_id",
        "uom_id",
        "tipo_variazione",
        "valore_variazione",
        "valido_dal",
        "valido_al",
        "meta",
        "attivo",
    })

    # Colonne scrivibili in update: `codice`, `articolo_id`, `uom_id` assenti
    # (immutabili). La policy per stato della promo (iniziata = campi
    # ristretti) resta del service.
    UPDATE_COLUMNS: frozenset[str] = frozenset({
        "descrizione",
        "tipo_variazione",
        "valore_variazione",
        "valido_dal",
        "valido_al",
        "meta",
        "attivo",
    })

    # Scopo: Inserisce una nuova promo sulle colonne whitelisted.
    #        `articolo_id` e' uuid: cast esplicito come prima della migrazione.
    def create_promo(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "vendite.promo_articoli", data,
            allowed=self.CREATE_COLUMNS, jsonb=_JSONB_COLS,
            casts={"articolo_id": "uuid"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna una promo sui soli campi forniti.
    def update_promo(self, record_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "vendite.promo_articoli", record_id, data,
            allowed=self.UPDATE_COLUMNS, jsonb=_JSONB_COLS,
        )
