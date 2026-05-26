# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per vendite.offerte_commerciali + eccezioni +
#        utilities 1:1 (CRUD iniziale, step DB 1-4 atterrati 2026-05-24).
#
#        L'offerta commerciale e' lo specchio strutturale del contratto:
#        testata mono-utility (istanza_utility_id + utility_id NOT NULL),
#        eccezioni come mirror di contratti_righe (tipo_eccezione enum
#        vendite.tipo_eccezione_contratto), utility 1:1 (UNIQUE offerta_id).
#        Il pricing/guard di stato e' gestito da trigger DB
#        (trgfn_offerte_commerciali_guard_transizione): qui niente logica
#        di business, solo CRUD sottile sulle colonne whitelisted.
#
#        Stato 2026-05-25: tutti gli step DB 1-9 atterrati e cablati
#        (numerazione automatica `OFC-*` via trigger BEFORE INSERT,
#        `crea_revisione` + `list_revisioni`, `push_a_contratto` +
#        `get_contratto_minimal`). Nessun metodo "fuori scope" residuo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import call_jsonb_fn, row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param


# Mappa colonna -> tipo speciale (jsonb). Le altre colonne usano '%s'.
_COLUMN_TYPES: dict[str, str] = {"meta": "jsonb"}


# Scopo: Adatta placeholder e value per colonne con tipo speciale (jsonb).
def _ph_and_val(col: str, value: Any) -> tuple[str, Any]:
    col_type = _COLUMN_TYPES.get(col)
    if col_type is None:
        return "%s", value
    return sql_placeholder(col_type), to_write_param(value, col_type)


# Scopo: Costruisce SQL INSERT e relativi parametri filtrando `data` sulla
#        whitelist colonne `write_cols`. `fixed_cols` permette di inserire
#        colonne valorizzate dal repository (es. `offerta_id` figli) che non
#        provengono dal payload. Ritorna (sql_str, params).
def _build_insert(
    table: str,
    write_cols: tuple[str, ...],
    data: dict[str, Any],
    *,
    fixed_cols: dict[str, Any] | None = None,
    returning: str = "id",
) -> tuple[str, list[Any]]:
    cols: list[str] = []
    vals: list[Any] = []
    placeholders: list[str] = []
    for col, val in (fixed_cols or {}).items():
        cols.append(col)
        placeholders.append("%s")
        vals.append(val)
    for col in write_cols:
        if col in data:
            ph, v = _ph_and_val(col, data[col])
            cols.append(col)
            placeholders.append(ph)
            vals.append(v)
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) "  # noqa: S608
        f"VALUES ({', '.join(placeholders)}) RETURNING {returning}"
    )
    return sql, vals


# Scopo: Costruisce SQL UPDATE e relativi parametri filtrando `data` sulla
#        whitelist colonne `write_cols`. Aggiunge il WHERE su `where_col` =
#        `where_val`. Se `data` non porta alcuna colonna mutabile, ritorna
#        (None, ...) per segnalare no-op al chiamante.
def _build_update(
    table: str,
    write_cols: tuple[str, ...],
    data: dict[str, Any],
    *,
    where_col: str,
    where_val: Any,
) -> tuple[str | None, list[Any]]:
    set_parts: list[str] = []
    vals: list[Any] = []
    for col in write_cols:
        if col in data:
            ph, v = _ph_and_val(col, data[col])
            set_parts.append(f"{col} = {ph}")
            vals.append(v)
    if not set_parts:
        return None, vals
    vals.append(where_val)
    sql = (
        f"UPDATE {table} SET {', '.join(set_parts)} "  # noqa: S608
        f"WHERE {where_col} = %s"
    )
    return sql, vals


# Whitelist ORDER BY per la lista offerte (SQL injection safe).
_ORDER_COLS_OFFERTE: dict[str, str] = {
    "codice": "o.codice",
    "validita_dal": "o.validita_dal",
    "validita_al": "o.validita_al",
    "data_emissione": "o.data_emissione",
    # Alias coerente col display field del SELECT (rinominato 2026-05-26).
    "billing_account_display": "srd.ragione_sociale_completa",
    "stato_codice": "sd.codice_interno",
    "data_insert": "o.data_insert",
    "data_update": "o.data_update",
}


_SELECT_COLS_OFFERTA = """
    o.id,
    o.uid,
    o.codice,
    o.emittente_fiscale_id,
    -- Denormalizzazione EF (pattern preventivi): il FE `EmittenteFiscaleField`
    -- in edit mode legge codice + descrizione dal record per costruire la
    -- option singola del Select disabled. Senza questi campi il display
    -- resta vuoto in modifica nonostante `emittente_fiscale_id` valorizzato.
    ef.codice           AS emittente_fiscale_codice,
    COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)
                        AS emittente_fiscale_descrizione,
    o.billing_account_id,
    ba.codice                AS ba_codice,
    srd.ragione_sociale_completa AS billing_account_display,
    -- ID fiscale univoco del soggetto del BA (CF persona fisica o P.IVA).
    -- Esposto dalla vista `anagrafiche.vw_soggetti_ruoli_dettaglio`. Colonna
    -- visibile nella lista per ricerca/confronto rapido del cliente.
    srd.id_fiscale_univoco_cf_piva AS id_fiscale,
    o.istanza_utility_id,
    o.utility_id,
    u.codice                 AS utility_codice,
    u.descrizione            AS utility_display,
    o.listino_id,
    l.codice                 AS listino_codice,
    l.descrizione            AS listino_descrizione,
    o.listino_versione_id,
    lv.codice_versione       AS listino_versione_codice,
    o.tipo_variazione_globale,
    o.valore_variazione_globale,
    o.validita_dal,
    o.validita_al,
    o.stato_doc_offerta_id,
    sd.codice_interno        AS stato_codice_interno,
    sd.descrizione           AS stato_descrizione,
    o.revisione_numero,
    o.revisione_padre_id,
    o.data_emissione,
    o.data_accettazione,
    o.data_rifiuto,
    o.data_annullamento,
    o.motivazione_rifiuto,
    o.meta,
    c.id                     AS contratto_id,
    c.numero                 AS contratto_numero,
    o.data_insert,
    o.user_insert,
    o.data_update,
    o.user_update
"""


_FROM_JOINS_OFFERTA = """
    FROM vendite.offerte_commerciali o
    JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
    JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
      ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
    JOIN config.utilities u ON u.id = o.utility_id
    JOIN config.stati_doc_offerte sd ON sd.id = o.stato_doc_offerta_id
    LEFT JOIN vendite.listini l ON l.id = o.listino_id
    LEFT JOIN vendite.listini_versioni lv ON lv.id = o.listino_versione_id
    -- LEFT JOIN col contratto generato dal push (idempotenza Pattern A
    -- garantita da UNIQUE uq_contratti_offerta_id). 0 o 1 riga: nessun
    -- rischio di duplicazione. Il FE usa contratto_id/numero per il dialog
    -- "gia' generato" e per il deep-link a ContrattoDrawer post-push.
    LEFT JOIN vendite.contratti c ON c.offerta_id = o.id
    -- Decode emittente fiscale: codice + ragione sociale (con fallback a
    -- descrizione plain dell'EF). Pattern allineato a preventivi_repository
    -- per UX uniforme nei drawer (EmittenteFiscaleField in modalita' edit
    -- legge questi campi denormalizzati senza round-trip aggiuntivo).
    LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = o.emittente_fiscale_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
"""


_SELECT_COLS_ECCEZIONE = """
    e.id,
    e.offerta_id,
    e.articolo_id,
    a.codice                 AS articolo_codice,
    a.descrizione            AS articolo_descrizione,
    e.tipo_eccezione,
    e.tipo_erogazione,
    e.fonte_quantita_attesa,
    e.periodicita,
    e.generazione_canone,
    e.competenza_canone,
    e.prezzo_unitario,
    e.quantita,
    e.qta_operativa,
    e.uom_operativa_id,
    um.codice                AS uom_codice,
    e.factor_to_base,
    e.ordine,
    e.attivo,
    e.meta
"""


_FROM_JOINS_ECCEZIONE = """
    FROM vendite.offerte_commerciali_eccezioni e
    JOIN catalogo.articoli a ON a.id = e.articolo_id
    LEFT JOIN catalogo.unita_misura um ON um.id = e.uom_operativa_id
"""


_SELECT_COLS_UTILITY = """
    ou.id,
    ou.offerta_id,
    ou.istanza_utility_id,
    ou.utility_id,
    u.codice                 AS utility_codice,
    u.descrizione            AS utility_descrizione,
    ou.istanza_dati_precontrattuali_id,
    ou.tipo_utenza_id,
    tu.codice                AS tipo_utenza_codice,
    tu.descrizione           AS tipo_utenza_descrizione,
    ou.classe_utenza_id,
    clu.codice               AS classe_utenza_codice,
    clu.descrizione          AS classe_utenza_descrizione,
    ou.param_1_num,
    ou.param_2_txt,
    ou.meta
"""


_FROM_JOINS_UTILITY = """
    FROM vendite.offerte_commerciali_utilities ou
    JOIN config.utilities u ON u.id = ou.utility_id
    LEFT JOIN config.tipi_utenze tu ON tu.id = ou.tipo_utenza_id
    LEFT JOIN config.classi_utenze clu ON clu.id = ou.classe_utenza_id
"""


class OfferteRepository:
    """Accesso DB a `vendite.offerte_commerciali` + eccezioni + utility 1:1.

    Specchio di `ContrattiRepository` per la testata, le eccezioni
    (mirror di `contratti_righe`) e la utility 1:1 (mirror di
    `contratti_utilities`). Niente componenti BoM in v1: l'eccezione
    e' atomica per articolo.
    """

    # =================================================================
    # Lista e dettaglio testata
    # =================================================================

    # Scopo: Costruisce la WHERE clause + relativi parametri condivisi da
    #        `list_offerte` e `count_offerte`. Mantiene un solo posto dove
    #        aggiungere/modificare filtri (no drift fra count e list).
    def _build_offerte_filters(
        self,
        *,
        billing_account_id: int | None,
        stato_codice_interno: str | None,
        utility_id: int | None,
        listino_id: int | None,
        validita_dal_min: str | None,
        validita_dal_max: str | None,
        search: str | None,
    ) -> tuple[str, list[Any]]:
        wheres: list[str] = []
        params: list[Any] = []
        if billing_account_id is not None:
            wheres.append("o.billing_account_id = %s")
            params.append(billing_account_id)
        if stato_codice_interno:
            wheres.append("sd.codice_interno = %s")
            params.append(stato_codice_interno)
        if utility_id is not None:
            wheres.append("o.utility_id = %s")
            params.append(utility_id)
        if listino_id is not None:
            wheres.append("o.listino_id = %s")
            params.append(listino_id)
        if validita_dal_min:
            wheres.append("o.validita_dal >= %s")
            params.append(validita_dal_min)
        if validita_dal_max:
            wheres.append("o.validita_dal <= %s")
            params.append(validita_dal_max)
        if search:
            # Search ILIKE su codice + ragione sociale BA. L'API impone >=3 char.
            wheres.append("(o.codice ILIKE %s OR srd.ragione_sociale_completa ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        return where_clause, params

    # Scopo: Lista paginata offerte filtrabile per BA/stato/utility/listino +
    #        intervallo validita' + search testuale sul codice.
    def list_offerte(
        self,
        *,
        billing_account_id: int | None = None,
        stato_codice_interno: str | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        search: str | None = None,
        order_by: str = "data_insert",
        order_dir: str = "DESC",
        limit: int = 25,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        order_col = _ORDER_COLS_OFFERTE.get(order_by, _ORDER_COLS_OFFERTE["data_insert"])
        order_dir_safe = "ASC" if str(order_dir).upper() == "ASC" else "DESC"
        where_clause, params = self._build_offerte_filters(
            billing_account_id=billing_account_id,
            stato_codice_interno=stato_codice_interno,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            search=search,
        )
        sql = f"""
            SELECT {_SELECT_COLS_OFFERTA}
              {_FROM_JOINS_OFFERTA}
              {where_clause}
             ORDER BY {order_col} {order_dir_safe}, o.id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: Conteggio totale per paginazione, stessi filtri di list_offerte.
    def count_offerte(
        self,
        *,
        billing_account_id: int | None = None,
        stato_codice_interno: str | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        search: str | None = None,
    ) -> int:
        where_clause, params = self._build_offerte_filters(
            billing_account_id=billing_account_id,
            stato_codice_interno=stato_codice_interno,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            search=search,
        )
        sql = f"""
            SELECT COUNT(*)
              {_FROM_JOINS_OFFERTA}
              {where_clause}
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Dettaglio testata con display fields.
    def get_offerta(self, offerta_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_OFFERTA}
                  {_FROM_JOINS_OFFERTA}
                 WHERE o.id = %s
                """,  # noqa: S608
                [offerta_id],
            )
            return row_to_dict(cursor)

    # Scopo: Capability dell'offerta per il detail API (refactor data-driven
    #        2026-05-26). Wrapper su `script.fn_available_actions_offerta`
    #        (consegnata dal team DB con migration `20260526-01`). Ritorna
    #        un jsonb opaco lato Python: il service lo merge-a nel dettaglio
    #        offerta e il FE lo consuma con `useEntityCapabilities` +
    #        `mapAvailableActionsToDrawerActions` come per contratto/preventivo.
    #        Struttura ritornata: { available_actions[], can_change_state,
    #        can_edit_testata, can_edit_eccezioni, can_edit_utility,
    #        can_create_revisione, can_push_contratto,
    #        can_push_contratto_reason, can_push_contratto_reason_key,
    #        non_editable_fields[], stato_codice }. Ritorna {} se la fn DB
    #        ritorna NULL (offerta inesistente: il caller verifica gia' 404).
    def get_available_actions(self, offerta_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_offerta", offerta_id)

    # Scopo: Crea una testata offerta (stato iniziale BOZZA gestito dal
    #        service che risolve l'id stato via get_stato_id_by_codice).
    #        Il `codice` arriva dal payload: la generazione automatica via
    #        sistema_codici (step 5 brief DB) non e' ancora cablata.
    # Colonne scrivibili in create (whitelist). Le immutabili (`uid`, audit,
    # data_*` di transizione) restano fuori e non sono accettate dal pattern.
    # `codice` escluso da Step 5 (2026-05-25): generato dal trigger DB
    # `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT); il repository
    # non lo tocca, defense-in-depth applicativa.
    _OFFERTA_CREATE_COLS: tuple[str, ...] = (
        "emittente_fiscale_id",
        "billing_account_id",
        "istanza_utility_id",
        "utility_id",
        "listino_id",
        "listino_versione_id",
        "valore_variazione_globale",
        "tipo_variazione_globale",
        "validita_dal",
        "validita_al",
        "stato_doc_offerta_id",
        "revisione_numero",
        "revisione_padre_id",
        "meta",
    )

    # Colonne aggiornabili in update (sotto-set di create senza chiavi
    # gestionali: `codice`, `stato_doc_offerta_id`, `revisione_*`).
    _OFFERTA_UPDATE_COLS: tuple[str, ...] = (
        "emittente_fiscale_id",
        "billing_account_id",
        "istanza_utility_id",
        "utility_id",
        "listino_id",
        "listino_versione_id",
        "valore_variazione_globale",
        "tipo_variazione_globale",
        "validita_dal",
        "validita_al",
        "meta",
    )

    def create_offerta(self, data: dict[str, Any]) -> int:
        sql, vals = _build_insert(
            "vendite.offerte_commerciali", self._OFFERTA_CREATE_COLS, data,
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna testata offerta. `codice`/`uid`/`stato_doc_offerta_id`
    #        immutabili tramite questo metodo (per lo stato c'e' update_stato).
    def update_offerta(self, offerta_id: int, data: dict[str, Any]) -> bool:
        sql, vals = _build_update(
            "vendite.offerte_commerciali", self._OFFERTA_UPDATE_COLS, data,
            where_col="id", where_val=offerta_id,
        )
        if sql is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Cambia lo stato documentale dell'offerta. Il trigger DB
    #        trgfn_offerte_commerciali_guard_transizione verifica che la
    #        transizione sia ammessa in config.stati_doc_offerte_transizioni
    #        e valorizza i timestamp `data_emissione`/`data_accettazione`/
    #        `data_rifiuto`/`data_annullamento`. La `motivazione_rifiuto` si
    #        aggiorna nello stesso UPDATE quando arriva da RIFIUTATA/ANNULLATA.
    def update_stato(
        self,
        offerta_id: int,
        stato_doc_offerta_id: int,
        *,
        motivazione_rifiuto: str | None = None,
    ) -> bool:
        set_parts = ["stato_doc_offerta_id = %s"]
        vals: list[Any] = [stato_doc_offerta_id]
        if motivazione_rifiuto is not None:
            set_parts.append("motivazione_rifiuto = %s")
            vals.append(motivazione_rifiuto)
        vals.append(offerta_id)
        sql = f"""
            UPDATE vendite.offerte_commerciali
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Cancella un'offerta (hard delete). Guard di stato (solo BOZZA)
    #        responsabilita' del service.
    def delete_offerta(self, offerta_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.offerte_commerciali WHERE id = %s",
                [offerta_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Eccezioni offerta
    # =================================================================

    # Scopo: Lista eccezioni di un'offerta, ordinate per `ordine` poi id.
    def list_eccezioni(self, offerta_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_ECCEZIONE}
                  {_FROM_JOINS_ECCEZIONE}
                 WHERE e.offerta_id = %s
                 ORDER BY e.ordine ASC, e.id ASC
                """,  # noqa: S608
                [offerta_id],
            )
            return rows_to_list(cursor)

    # Scopo: Dettaglio singola eccezione (read-after-write).
    def get_eccezione(self, eccezione_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_ECCEZIONE}
                  {_FROM_JOINS_ECCEZIONE}
                 WHERE e.id = %s
                """,  # noqa: S608
                [eccezione_id],
            )
            return row_to_dict(cursor)

    # Colonne scrivibili eccezione: in create includono `articolo_id`/
    # `tipo_eccezione` (immutabili dopo INSERT); in update vengono filtrati
    # via `_ECCEZIONE_UPDATE_COLS`.
    _ECCEZIONE_CREATE_COLS: tuple[str, ...] = (
        "articolo_id",
        "tipo_eccezione",
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

    _ECCEZIONE_UPDATE_COLS: tuple[str, ...] = (
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

    # Scopo: Inserisce un'eccezione offerta. I 5 CHECK constraint DB
    #        (chk_offerte_eccezioni_*) validano coerenza prezzo/canone/
    #        fonte/erogazione/qta — qui solo passaggio colonne whitelisted.
    def create_eccezione(self, offerta_id: int, data: dict[str, Any]) -> int:
        sql, vals = _build_insert(
            "vendite.offerte_commerciali_eccezioni",
            self._ECCEZIONE_CREATE_COLS,
            data,
            fixed_cols={"offerta_id": offerta_id},
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna un'eccezione offerta sul subset mutabile (articolo_id
    #        e tipo_eccezione immutabili — un cambio = delete+create).
    def update_eccezione(self, eccezione_id: int, data: dict[str, Any]) -> bool:
        sql, vals = _build_update(
            "vendite.offerte_commerciali_eccezioni",
            self._ECCEZIONE_UPDATE_COLS,
            data,
            where_col="id",
            where_val=eccezione_id,
        )
        if sql is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Cancella un'eccezione offerta (hard delete). Guard stato BOZZA
    #        a livello service.
    def delete_eccezione(self, eccezione_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.offerte_commerciali_eccezioni WHERE id = %s",
                [eccezione_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Utility 1:1
    # =================================================================

    # Scopo: Legge il record utility (1:1) di un'offerta.
    def get_utility(self, offerta_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS_UTILITY}
                  {_FROM_JOINS_UTILITY}
                 WHERE ou.offerta_id = %s
                """,  # noqa: S608
                [offerta_id],
            )
            return row_to_dict(cursor)

    # Colonne scrivibili utility (create con istanza_utility_id/utility_id,
    # update senza — immutabili: cambio = delete+create).
    _UTILITY_CREATE_COLS: tuple[str, ...] = (
        "istanza_utility_id",
        "utility_id",
        "istanza_dati_precontrattuali_id",
        "tipo_utenza_id",
        "classe_utenza_id",
        "param_1_num",
        "param_2_txt",
        "meta",
    )

    _UTILITY_UPDATE_COLS: tuple[str, ...] = (
        "istanza_dati_precontrattuali_id",
        "tipo_utenza_id",
        "classe_utenza_id",
        "param_1_num",
        "param_2_txt",
        "meta",
    )

    # Scopo: Crea il record utility 1:1 (UNIQUE offerta_id; un INSERT
    #        duplicato fallisce con violazione UNIQUE → mappato dal service).
    def create_utility(self, offerta_id: int, data: dict[str, Any]) -> int:
        sql, vals = _build_insert(
            "vendite.offerte_commerciali_utilities",
            self._UTILITY_CREATE_COLS,
            data,
            fixed_cols={"offerta_id": offerta_id},
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna il record utility sul subset mutabile (istanza_utility_id
    #        e utility_id NON modificabili: cambiano solo eliminando+ricreando
    #        l'offerta, come per il contratto).
    def update_utility(self, utility_row_id: int, data: dict[str, Any]) -> bool:
        sql, vals = _build_update(
            "vendite.offerte_commerciali_utilities",
            self._UTILITY_UPDATE_COLS,
            data,
            where_col="id",
            where_val=utility_row_id,
        )
        if sql is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # =================================================================
    # Lookup di supporto
    # =================================================================

    # Scopo: Risolve l'id di uno stato documento offerta dal codice_interno.
    #        Usato dal service per impostare stato iniziale (BOZZA) e per
    #        risolvere lo stato target nelle transizioni manuali (annulla,
    #        registra_esito, emetti).
    def get_stato_id_by_codice(self, codice_interno: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM config.stati_doc_offerte
                 WHERE codice_interno = %s
                """,
                [codice_interno],
            )
            row = cursor.fetchone()
            return None if row is None else int(row[0])

    # Scopo: Legge il `codice_interno` dello stato corrente di un'offerta.
    #        Usato dal service per validare le pre-condizioni dei cambi stato
    #        (emetti SOLO da BOZZA, registra_esito SOLO da EMESSA, ecc.).
    def get_stato_codice(self, offerta_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sd.codice_interno
                  FROM vendite.offerte_commerciali o
                  JOIN config.stati_doc_offerte sd
                    ON sd.id = o.stato_doc_offerta_id
                 WHERE o.id = %s
                """,
                [offerta_id],
            )
            row = cursor.fetchone()
            return None if row is None else str(row[0])

    # =================================================================
    # Revisioni (Step 6-7 brief DB, atterrati 2026-05-25)
    # =================================================================

    # Scopo: Crea rev.N+1 invocando `vendite.fn_crea_revisione_offerta`.
    #        La fn DB copia testata + eccezioni attive + utility 1:1, e il
    #        trigger `trg_offerte_commerciali_z90_revisione_ins` (AFTER INSERT)
    #        marca automaticamente la rev.N come SUPERATA. Ritorna l'id della
    #        nuova rev.N+1.
    #
    #        Guard di stato (EMESSA obbligatorio) gia' applicato dalla fn DB
    #        con codice `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`.
    def crea_revisione(self, offerta_id: int, user: str | None = None) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_crea_revisione_offerta(%s, %s)",
                [offerta_id, user],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return int(row[0])

    # =================================================================
    # Push a contratto (Step 8 brief DB, atterrato 2026-05-25)
    # =================================================================

    # Scopo: Push offerta ACCETTATA → contratto DRAFT invocando la fn DB
    #        `vendite.fn_push_offerta_a_contratto`. La fn:
    #          - guard stato ACCETTATA (E_OFFERTA_PUSH_STATO_NON_AMMESSO)
    #          - guard idempotenza UNIQUE su contratti.offerta_id
    #            (E_OFFERTA_CONTRATTO_GIA_GENERATO se gia' pushato)
    #          - INSERT contratto DRAFT con sorgente_tipo OFFERTA_COMMERCIALE +
    #            sorgente_uid + offerta_id
    #          - copia eccezioni 1:1 → contratti_righe
    #          - UPSERT utility 1:1 → contratti_utilities (sovrascrive il
    #            record gia' creato dal trigger snapshot_precontrattuali)
    #          - se p_pratica_id NOT NULL: INSERT pratiche.pratiche_sorgenti
    #
    #        Ritorna l'id del nuovo contratto DRAFT.
    def push_a_contratto(
        self, offerta_id: int, pratica_id: int | None = None
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_push_offerta_a_contratto(%s, %s)",
                [offerta_id, pratica_id],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return int(row[0])

    # Scopo: Lookup minimal del contratto post-push (id + numero + uid).
    #        Usato dal service per costruire `OffertaPushResult` senza
    #        invocare il `ContrattiService` (no cross-service coupling).
    #        Solo i 3 campi che il service consuma: niente JOIN superflui
    #        sulla tabella stati (fn DB garantisce stato DRAFT al push).
    def get_contratto_minimal(self, contratto_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, numero, uid
                  FROM vendite.contratti
                 WHERE id = %s
                """,
                [contratto_id],
            )
            return row_to_dict(cursor)

    # Scopo: Lista catena revisioni che condividono il medesimo "root"
    #        (rev.1) dell'offerta passata. Risale via `revisione_padre_id`
    #        fino alla radice, poi ridiscende a tutti i discendenti.
    #        Output ordinato per `revisione_numero` ASC.
    #
    #        Caso "lineare" (n revisioni in serie): ritorna [rev.1, ..., rev.N].
    #        Caso "fork" (es. due figli da rev.1, scenario teorico, non
    #        previsto dalla state machine ma supportato dalla query):
    #        ritorna tutti i nodi della componente connessa.
    def list_revisioni(self, offerta_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH RECURSIVE
                ancestors AS (
                    SELECT id, revisione_padre_id
                      FROM vendite.offerte_commerciali
                     WHERE id = %s
                    UNION ALL
                    SELECT o.id, o.revisione_padre_id
                      FROM vendite.offerte_commerciali o
                      JOIN ancestors a ON a.revisione_padre_id = o.id
                ),
                root_id AS (
                    SELECT id FROM ancestors WHERE revisione_padre_id IS NULL
                    LIMIT 1
                ),
                family AS (
                    SELECT o.id
                      FROM vendite.offerte_commerciali o, root_id
                     WHERE o.id = root_id.id
                    UNION ALL
                    SELECT o.id
                      FROM vendite.offerte_commerciali o
                      JOIN family f ON o.revisione_padre_id = f.id
                )
                SELECT {_SELECT_COLS_OFFERTA}
                  {_FROM_JOINS_OFFERTA}
                 WHERE o.id IN (SELECT id FROM family)
                 ORDER BY o.revisione_numero ASC, o.id ASC
                """,  # noqa: S608
                [offerta_id],
            )
            return rows_to_list(cursor)
