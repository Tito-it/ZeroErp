# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per `documenti.template_documenti` e
#        `documenti.template_documenti_versioni`. Read (list/get) +
#        write (create/update template testata, Tranche E). Forward-compatibile
#        con comandi versione (Tranche F) e endpoint di generazione documento
#        (sorgente -> template applicabile, Tranche H/J).
#        Scope emittente passato dal service tramite lista whitelist
#        (`PermissionResolver.get_emittenti_pk_ids`); admin globale
#        riceve `None` e non filtra.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import RicercaFull, add_ricerca_full_condition, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param
from apps.core.services.error_manager import ErrorManager


# Mappatura colonne ammesse per ORDER BY lato lista template.
# Whitelist anti-injection: i nomi vengono interpolati nella SQL e
# non possono provenire da input utente non validati.
# `attivo` e' NUCLEO: lo stato ordina sempre (regola di dominio, seed lista
# 'documenti.template_documenti'). Le quattro voci di decodifica restano nude
# perche' sono alias di output della SELECT (colonne di tabelle JOINte):
# ORDER BY le risolve per alias.
TEMPLATES_ORDER_COLUMNS: dict[str, str] = {
    "codice": "t.codice",
    "codice_interno": "t.codice_interno",
    "descrizione": "t.descrizione",
    "attivo": "t.attivo",
    "is_default": "t.is_default",
    "tipo_documento_output_descrizione": "tipo_documento_output_descrizione",
    "sorgente_tipo_descrizione": "sorgente_tipo_descrizione",
    "emittente_ragione_sociale": "emittente_ragione_sociale",
    "data_insert": "t.data_insert",
    "data_update": "t.data_update",
}


# Whitelist colonne ammesse in INSERT (testata template).
# Audit (`data_insert/update`, `user_insert/update`) gestita dal DB.
# `tx_id`/`storicizza` lasciate ai default.
TEMPLATE_CREATE_COLUMNS: tuple[str, ...] = (
    "tipo_documento_output_id",
    "codice",
    "codice_interno",
    "descrizione",
    "sorgente_tipo_id",
    "context_builder_code",
    "file_name_pattern",
    "emittente_fiscale_id",
    "is_default",
    "attivo",
    "meta",
)


# Whitelist colonne ammesse in UPDATE.
# Immutabili dopo create: `tipo_documento_output_id`, `sorgente_tipo_id`,
# `emittente_fiscale_id` (la chiave logica del template e' (output, sorgente,
# emittente) — cambiarla equivale a creare un nuovo template).
# `codice` e `codice_interno` sono UPDATEable per consentire correzione
# tipi/normalizzazione, ma il service decide eventualmente di vincolarli.
TEMPLATE_UPDATE_COLUMNS: tuple[str, ...] = (
    "codice",
    "codice_interno",
    "descrizione",
    "context_builder_code",
    "file_name_pattern",
    "is_default",
    "attivo",
    "meta",
)


# Whitelist colonne ammesse in INSERT su template_documenti_versioni.
# `versione` calcolata dal service (next_versione_num), `stato` sempre
# 'BOZZA' su create (transizione PUBBLICATA passa solo dal comando dedicato
# pubblica_versione). `validita` e' STORED generated column (PG 18) da
# `valido_dal`/`valido_al`, non scrivibile.
VERSIONE_CREATE_COLUMNS: tuple[str, ...] = (
    "template_documento_id",
    "versione",
    "stato",
    "titolo",
    "formato_template",
    "html_template",
    "css_template",
    "markdown_template",
    "render_engine_id",
    "page_format",
    "page_orientation",
    "margin_top_mm",
    "margin_right_mm",
    "margin_bottom_mm",
    "margin_left_mm",
    "valido_dal",
    "valido_al",
    "context_schema",
    "meta",
    "attivo",
)


# Whitelist colonne ammesse in UPDATE su template_documenti_versioni.
# Immutabili escluse: `template_documento_id`, `versione`, `stato`.
# La transizione di stato passa solo dal comando dedicato pubblica_versione.
# Il trigger DB A1 (protect_pubblicata) blocca comunque l'update di
# html/css/render/layout/valido_* se OLD.stato='PUBBLICATA' — defense-in-depth.
VERSIONE_UPDATE_COLUMNS: tuple[str, ...] = (
    "titolo",
    "formato_template",
    "html_template",
    "css_template",
    "markdown_template",
    "render_engine_id",
    "page_format",
    "page_orientation",
    "margin_top_mm",
    "margin_right_mm",
    "margin_bottom_mm",
    "margin_left_mm",
    "valido_dal",
    "valido_al",
    "context_schema",
    "meta",
    "attivo",
)


# Mappatura colonne ammesse per ORDER BY lato lista asset.
# `attivo` e' NUCLEO (lo stato ordina sempre). `valido_al` aggiunta insieme a
# `valido_dal` gia' presente: dove una lista mostra le date di validita', quelle
# colonne ordinano — e `valido_al` DESC e' il default d'elezione (i NULL, cioe'
# gli asset senza scadenza, salgono in testa; le scadenze vecchie vanno in fondo).
# `asset_tipo_descrizione` ed `emittente_ragione_sociale` restano nude: sono
# alias di output della SELECT (colonne di tabelle JOINte).
ASSET_ORDER_COLUMNS: dict[str, str] = {
    "codice": "a.codice",
    "codice_interno": "a.codice_interno",
    "descrizione": "a.descrizione",
    "attivo": "a.attivo",
    "asset_tipo_descrizione": "asset_tipo_descrizione",
    "emittente_ragione_sociale": "emittente_ragione_sociale",
    "file_name": "a.file_name",
    "file_size_bytes": "a.file_size_bytes",
    "mime_type": "a.mime_type",
    "data_insert": "a.data_insert",
    "data_update": "a.data_update",
    "valido_dal": "a.valido_dal",
    "valido_al": "COALESCE(a.valido_al, 'infinity'::date)",
}


# Whitelist colonne ammesse in INSERT su documenti_generati (Tranche I).
# Audit (`data_*`/`user_*`) gestita dai trigger DB; `tx_id` popolata da
# `dbops.trgfn_tx_id_managed` (Decisione 76 — INSERT senza tx_id esplicito);
# `uid` default `uuidv7()` dal DDL; `stato` default `'GENERATO'`.
DOCUMENTO_GENERATO_CREATE_COLUMNS: tuple[str, ...] = (
    "tipo_documento_output_id",
    "template_documento_id",
    "template_versione_id",
    "sorgente_tipo_id",
    "sorgente_uid",
    "sorgente_riga",
    "progressivo_sorgente",
    "stato",
    "titolo",
    "nome_file",
    "context_json",
    "context_hash",
    "template_hash",
    "pdf_hash",
    "generato_da_user_id",
    "emittente_fiscale_id",
    "meta",
)


# Whitelist colonne ammesse in INSERT su documenti_generati_file.
# Audit + tx_id gestiti dal DB.
DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS: tuple[str, ...] = (
    "documento_generato_id",
    "file_tipo_id",
    "mime_type",
    "file_name",
    "file_size_bytes",
    "storage_key",
    "sha256",
    "ordinamento",
    "is_principale",
    "meta",
)


# Whitelist colonne ammesse in INSERT su documenti_generati_eventi.
# Decisione 76: `tx_id` NON va passata esplicitamente (la popola
# l'automation regola 4). Append-only: niente UPDATE/DELETE colonne.
EVENTO_DOCUMENTO_CREATE_COLUMNS: tuple[str, ...] = (
    "documento_generato_id",
    "evento_tipo",
    "user_id",
    "esito",
    "messaggio",
    "detail",
    "meta",
)

_DOCUMENTO_GENERATO_COLUMN_TYPES: dict[str, str] = {
    "context_json": "jsonb",
    "meta": "jsonb",
}

_DOCUMENTO_GENERATO_FILE_COLUMN_TYPES: dict[str, str] = {
    "meta": "jsonb",
}

_EVENTO_DOCUMENTO_COLUMN_TYPES: dict[str, str] = {
    "detail": "jsonb",
    "meta": "jsonb",
}


# Whitelist colonne ammesse in INSERT su template_asset.
# Audit (`data_*`/`user_*`) gestiti dal DB; `validita` e' STORED generated
# column (PG 18) da `valido_dal`/`valido_al`, non scrivibile. `tx_id`/`storicizza`
# lasciate ai default.
ASSET_CREATE_COLUMNS: tuple[str, ...] = (
    "codice",
    "codice_interno",
    "descrizione",
    "asset_tipo_id",
    "mime_type",
    "file_name",
    "file_size_bytes",
    "storage_key",
    "sha256",
    "emittente_fiscale_id",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
)


# Whitelist colonne ammesse in UPDATE su template_asset.
# **Immutabili dopo create** (trigger DB A4 protect_file): storage_key,
# sha256, file_size_bytes, mime_type, file_name.
# **Immutabili anagraficamente** (logica service): codice, codice_interno,
# asset_tipo_id, emittente_fiscale_id (la chiave logica e' (emittente, codice)).
# Modificabili: descrizione, valido_dal, valido_al, attivo, meta.
ASSET_UPDATE_COLUMNS: tuple[str, ...] = (
    "descrizione",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
)


# Proiezione lista asset (no asset binario, no SQL pesante).
_ASSET_PROJECTION = """
    a.id,
    a.codice,
    a.codice_interno,
    a.descrizione,
    a.asset_tipo_id,
    tad.codice            AS asset_tipo_codice,
    tad.descrizione       AS asset_tipo_descrizione,
    a.mime_type,
    a.file_name,
    a.file_size_bytes,
    a.storage_key,
    a.sha256,
    a.emittente_fiscale_id,
    ef.codice             AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa
                          AS emittente_ragione_sociale,
    a.valido_dal,
    a.valido_al,
    a.attivo,
    a.data_insert,
    a.data_update
"""

_ASSET_PROJECTION_DETAIL = (
    _ASSET_PROJECTION + ",\n    a.meta,\n    a.storicizza,\n    a.user_insert,\n    a.user_update"
)

# Cosa si PUO' cercare nelle liste dei template e degli asset; cosa si cerca lo
# dice il catalogo della lista (`add_ricerca_full_condition`, brief-be-ricerca-
# full-liste-residue §2). Colonne semplici delle tabelle nel `FROM` (alias `t` e
# `a`), proiettate con lo stesso nome: forma a tupla.
# ⛔ Il `codice_interno` NON si cerca (Tid, 2026-09-23 — brief §7-bis): e' la
#    chiave immutabile del sistema, non il codice dell'operatore. Fino al
#    2026-09-24 la ricerca scritta a mano lo cercava; il catalogo non lo accende.
# ⭐ Senza 400 sotto soglia: template e asset sono tabelle di
#    CONFIGURAZIONE (Tid, 2026-09-24 — brief §6 e §13.3 a), come le altre
#    dell'area config. La soglia la dichiara il catalogo della lista
#    (`ricerca_min_caratteri`), non questo modulo.
_RICERCA_TEMPLATE_DOCUMENTI = RicercaFull("documenti.template_documenti", ("codice", "descrizione"))
_RICERCA_TEMPLATE_ASSET = RicercaFull("documenti.template_asset", ("codice", "descrizione", "file_name"))

_ASSET_FROM = """
    FROM documenti.template_asset a
    JOIN documenti.tipi_asset_documento tad ON tad.id = a.asset_tipo_id
    JOIN anagrafiche.emittenti_fiscali ef ON ef.id = a.emittente_fiscale_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
"""


# Proiezione "list" — niente HTML/CSS/markdown (pesanti).
# Comune a list e get_template per uniformita' contratto.
_TEMPLATES_PROJECTION = """
    t.id,
    t.codice,
    t.codice_interno,
    t.descrizione,
    t.is_default,
    t.attivo,
    t.tipo_documento_output_id,
    tdo.codice           AS tipo_documento_output_codice,
    tdo.descrizione      AS tipo_documento_output_descrizione,
    t.sorgente_tipo_id,
    s.codice             AS sorgente_tipo_codice,
    s.descrizione        AS sorgente_tipo_descrizione,
    t.context_builder_code,
    t.file_name_pattern,
    t.emittente_fiscale_id,
    ef.codice            AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa
                         AS emittente_ragione_sociale,
    t.data_insert,
    t.data_update
"""

_TEMPLATES_PROJECTION_DETAIL = (
    _TEMPLATES_PROJECTION
    + ",\n    t.meta,\n    t.storicizza,\n    t.user_insert,\n    t.user_update"
)

_TEMPLATES_FROM = """
    FROM documenti.template_documenti t
    JOIN documenti.tipi_documento_output tdo ON tdo.id = t.tipo_documento_output_id
    JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
    JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t.emittente_fiscale_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
"""


# Proiezione "list" versioni — esclude html_template/css_template/markdown_template.
_VERSIONI_PROJECTION = """
    v.id,
    v.template_documento_id,
    v.versione,
    v.stato,
    v.titolo,
    v.formato_template,
    v.render_engine_id,
    re.codice_interno    AS render_engine_codice_interno,
    re.codice            AS render_engine_codice,
    re.descrizione       AS render_engine_descrizione,
    v.page_format,
    v.page_orientation,
    v.valido_dal,
    v.valido_al,
    v.attivo,
    v.data_insert,
    v.data_update
"""

_VERSIONI_PROJECTION_DETAIL = (
    _VERSIONI_PROJECTION
    + ",\n    v.html_template,\n    v.css_template,\n    v.markdown_template,"
    + "\n    v.margin_top_mm, v.margin_right_mm, v.margin_bottom_mm, v.margin_left_mm,"
    + "\n    v.context_schema, v.meta, v.storicizza, v.user_insert, v.user_update"
)

_VERSIONI_FROM = """
    FROM documenti.template_documenti_versioni v
    JOIN documenti.render_engine_documento re ON re.id = v.render_engine_id
"""


class DocumentiRepository:
    """Accesso DB read-only per template documenti e versioni."""

    # Scopo: Lista paginata template con scope emittente, search, filtri base.
    #        Ordinamento whitelisted con `id` come tiebreaker (paginazione
    #        deterministica, vedi frontend-standards REGOLA CRITICA).
    def list_templates(
        self,
        *,
        attivo: bool | None,
        tipo_documento_output_id: int | None,
        sorgente_tipo_id: int | None,
        emittente_fiscale_id: int | None,
        search: str | None,
        emittente_ids_scope: list[int] | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        if order_by not in TEMPLATES_ORDER_COLUMNS:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Colonna di ordinamento non valida: '{order_by}'.",
                detail=f"ammesse={sorted(TEMPLATES_ORDER_COLUMNS.keys())!r}",
            )
            raise  # unreachable, per type checker
        order_column = TEMPLATES_ORDER_COLUMNS[order_by]
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("t.attivo = %s")
            params.append(attivo)
        if tipo_documento_output_id is not None:
            conditions.append("t.tipo_documento_output_id = %s")
            params.append(tipo_documento_output_id)
        if sorgente_tipo_id is not None:
            conditions.append("t.sorgente_tipo_id = %s")
            params.append(sorgente_tipo_id)
        if emittente_fiscale_id is not None:
            conditions.append("t.emittente_fiscale_id = %s")
            params.append(emittente_fiscale_id)
        if emittente_ids_scope is not None:
            # Scope operatore: lista whitelist degli emittenti autorizzati.
            # Lista vuota = nessun emittente -> 0 risultati senza errore.
            conditions.append("t.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        # Un punto solo: la stessa condizione serve count e pagina.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_TEMPLATE_DOCUMENTI, alias="t")

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
            {_TEMPLATES_FROM}
            {where_clause}
        """
        data_sql = f"""
            SELECT {_TEMPLATES_PROJECTION}
            {_TEMPLATES_FROM}
            {where_clause}
            ORDER BY {order_column} {safe_order_dir}, t.id {safe_order_dir}
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total

    # Scopo: Dettaglio singolo template. Ritorna None se non esiste o non
    #        rispetta lo scope emittente (il service traduce in 404).
    def get_template(
        self,
        template_id: int,
        *,
        emittente_ids_scope: list[int] | None,
    ) -> dict[str, Any] | None:
        conditions = ["t.id = %s"]
        params: list[Any] = [int(template_id)]
        if emittente_ids_scope is not None:
            conditions.append("t.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT {_TEMPLATES_PROJECTION_DETAIL}
            {_TEMPLATES_FROM}
            WHERE {where_clause}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Lista versioni di un template, ordinata per versione DESC.
    #        Niente paginazione: il numero di versioni per template e'
    #        contenuto per design (ciclo BOZZA->PUBBLICATA->OBSOLETA).
    def list_versioni(
        self,
        template_documento_id: int,
        *,
        attivo: bool | None,
        stato: str | None,
    ) -> list[dict[str, Any]]:
        conditions = ["v.template_documento_id = %s"]
        params: list[Any] = [int(template_documento_id)]
        if attivo is not None:
            conditions.append("v.attivo = %s")
            params.append(attivo)
        if stato is not None:
            conditions.append("v.stato = %s")
            params.append(stato)
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT {_VERSIONI_PROJECTION}
            {_VERSIONI_FROM}
            WHERE {where_clause}
            ORDER BY v.versione DESC, v.id DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: Dettaglio versione singola (incluso payload HTML/CSS/markdown).
    #        Filtro implicito su template_documento_id per defense-in-depth:
    #        evita che un id versione orfano di altro template venga
    #        servito tramite path di un template diverso.
    def get_versione(
        self,
        template_documento_id: int,
        versione_id: int,
    ) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_VERSIONI_PROJECTION_DETAIL}
            {_VERSIONI_FROM}
            WHERE v.id = %s AND v.template_documento_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(versione_id), int(template_documento_id)])
            results = rows_to_list(cursor)
        return results[0] if results else None

    # =================================================================
    # Mutazioni testata template (Tranche E)
    # =================================================================

    # Scopo: INSERT testata template usando solo colonne whitelisted in
    #        TEMPLATE_CREATE_COLUMNS. Eventuali violazioni UNIQUE/CHECK/FK
    #        vengono propagate al service che le mappa via map_integrity_error.
    def create_template(self, data: dict[str, Any]) -> int:
        cols: list[str] = []
        vals: list[Any] = []
        for col in TEMPLATE_CREATE_COLUMNS:
            if col in data:
                cols.append(col)
                vals.append(data[col])
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO documenti.template_documenti ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: UPDATE testata template sui soli campi presenti in `data`.
    #        Ritorna True se almeno una riga aggiornata, False se id assente
    #        (il service traduce in 404). Le immutabili (output/sorgente/emittente)
    #        sono escluse dalla whitelist TEMPLATE_UPDATE_COLUMNS.
    def update_template(self, template_id: int, data: dict[str, Any]) -> bool:
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in TEMPLATE_UPDATE_COLUMNS:
            if col in data:
                set_parts.append(f"{col} = %s")
                vals.append(data[col])
        if not set_parts:
            return False
        vals.append(int(template_id))
        sql = f"""
            UPDATE documenti.template_documenti
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # =================================================================
    # Mutazioni versione template (Tranche F)
    # =================================================================

    # Scopo: Calcola il prossimo numero di versione disponibile per un
    #        template. Usa MAX(versione) + 1 con COALESCE per il primo
    #        inserimento. Il vincolo UNIQUE (template_documento_id, versione)
    #        e' la garanzia finale: se due chiamate concorrenti calcolano
    #        lo stesso numero, l'INSERT del secondo solleva IntegrityError
    #        che il service mappa in errore parlante (rare race condition).
    def next_versione_num(self, template_documento_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(versione), 0) + 1
                  FROM documenti.template_documenti_versioni
                 WHERE template_documento_id = %s
                """,
                [int(template_documento_id)],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: INSERT versione template usando solo colonne whitelisted in
    #        VERSIONE_CREATE_COLUMNS. `validita` (daterange) e' STORED generated
    #        column (PG 18) calcolata da `valido_dal`/`valido_al`. Eventuali
    #        violazioni unique/check vengono propagate al service.
    def create_versione(self, data: dict[str, Any]) -> int:
        cols: list[str] = []
        vals: list[Any] = []
        for col in VERSIONE_CREATE_COLUMNS:
            if col in data:
                cols.append(col)
                vals.append(data[col])
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO documenti.template_documenti_versioni ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: UPDATE versione sui soli campi presenti in `data`. Il trigger
    #        DB A1 (protect_pubblicata) blocca l'update se OLD.stato='PUBBLICATA'
    #        — defense-in-depth: il service controlla lo stato, ma il DB
    #        rifiuta comunque le modifiche.
    def update_versione(self, versione_id: int, data: dict[str, Any]) -> bool:
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in VERSIONE_UPDATE_COLUMNS:
            if col in data:
                set_parts.append(f"{col} = %s")
                vals.append(data[col])
        if not set_parts:
            return False
        vals.append(int(versione_id))
        sql = f"""
            UPDATE documenti.template_documenti_versioni
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Hard DELETE versione. Il trigger DB A2 (block_delete) rifiuta
    #        l'operazione se OLD.stato in ('PUBBLICATA','OBSOLETA') o se
    #        esiste almeno un documento_generato che la referenzia. Il
    #        service mappa l'IntegrityError -> E_DOCUMENTI_VERSIONE_DELETE_BLOCKED.
    def delete_versione(self, versione_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM documenti.template_documenti_versioni WHERE id = %s",
                [int(versione_id)],
            )
            return cursor.rowcount > 0

    # Scopo: Delega alla funzione DB atomica la transizione BOZZA -> PUBBLICATA.
    #        La funzione blocca le versioni dello stesso template, auto-chiude
    #        eventuali PUBBLICATE precedenti sovrapposte e poi pubblica la BOZZA.
    #        Il vincolo EXCLUDE resta guardrail finale contro overlap residui.
    def pubblica_versione(
        self,
        versione_id: int,
        *,
        valido_dal: Any,
        valido_al: Any,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT versione_id
                  FROM documenti.fn_pubblica_template_documento_versione(
                    p_versione_id => %s,
                    p_valido_dal  => %s,
                    p_valido_al   => %s
                  )
                """,
                [int(versione_id), valido_dal, valido_al],
            )
            return cursor.fetchone() is not None

    # =================================================================
    # Asset documentali (Tranche G)
    # =================================================================

    # Scopo: Lista paginata asset con scope emittente e filtri base.
    #        Ordinamento whitelisted con `id` come tiebreaker.
    def list_asset(
        self,
        *,
        attivo: bool | None,
        asset_tipo_id: int | None,
        emittente_fiscale_id: int | None,
        search: str | None,
        emittente_ids_scope: list[int] | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        if order_by not in ASSET_ORDER_COLUMNS:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Colonna di ordinamento non valida: '{order_by}'.",
                detail=f"ammesse={sorted(ASSET_ORDER_COLUMNS.keys())!r}",
            )
            raise  # unreachable
        order_column = ASSET_ORDER_COLUMNS[order_by]
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if asset_tipo_id is not None:
            conditions.append("a.asset_tipo_id = %s")
            params.append(asset_tipo_id)
        if emittente_fiscale_id is not None:
            conditions.append("a.emittente_fiscale_id = %s")
            params.append(emittente_fiscale_id)
        if emittente_ids_scope is not None:
            conditions.append("a.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        # Un punto solo: la stessa condizione serve count e pagina.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_TEMPLATE_ASSET, alias="a")

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
            {_ASSET_FROM}
            {where_clause}
        """
        data_sql = f"""
            SELECT {_ASSET_PROJECTION}
            {_ASSET_FROM}
            {where_clause}
            ORDER BY {order_column} {safe_order_dir}, a.id {safe_order_dir}
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total

    # Scopo: Dettaglio asset. Ritorna None se inesistente o fuori scope
    #        (il service traduce in 404 unificato).
    def get_asset(
        self,
        asset_id: int,
        *,
        emittente_ids_scope: list[int] | None,
    ) -> dict[str, Any] | None:
        conditions = ["a.id = %s"]
        params: list[Any] = [int(asset_id)]
        if emittente_ids_scope is not None:
            conditions.append("a.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT {_ASSET_PROJECTION_DETAIL}
            {_ASSET_FROM}
            WHERE {where_clause}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: INSERT asset usando solo colonne whitelisted in
    #        ASSET_CREATE_COLUMNS. `validita` (daterange) e' STORED generated
    #        column (PG 18) calcolata da `valido_dal`/`valido_al`. Il vincolo
    #        unique (emittente_fiscale_id, sha256) garantisce dedup natural:
    #        re-upload dello stesso file -> IntegrityError mappato.
    def create_asset(self, data: dict[str, Any]) -> int:
        cols: list[str] = []
        vals: list[Any] = []
        for col in ASSET_CREATE_COLUMNS:
            if col in data:
                cols.append(col)
                vals.append(data[col])
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO documenti.template_asset ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Lookup tipo asset (id, codice_interno, attivo). Usato dal
    #        service admin per validare MIME contro whitelist Python
    #        per `codice_interno`. Ritorna None se id inesistente.
    def get_tipo_asset(self, asset_tipo_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice_interno, attivo
                  FROM documenti.tipi_asset_documento
                 WHERE id = %s
                """,
                [int(asset_tipo_id)],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {"id": int(row[0]), "codice_interno": str(row[1]), "attivo": bool(row[2])}

    # Scopo: UPDATE asset sui soli campi metadati editabili (no file).
    #        Il trigger DB A4 (protect_file) blocca comunque qualsiasi
    #        UPDATE su storage_key/sha256/file_size/mime/file_name come
    #        guardrail finale: ASSET_UPDATE_COLUMNS le esclude per design.
    def update_asset_metadati(
        self, asset_id: int, data: dict[str, Any]
    ) -> bool:
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in ASSET_UPDATE_COLUMNS:
            if col in data:
                set_parts.append(f"{col} = %s")
                vals.append(data[col])
        if not set_parts:
            return False
        vals.append(int(asset_id))
        sql = f"""
            UPDATE documenti.template_asset
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # =================================================================
    # Resolve template + versione per render (Tranche I)
    # =================================================================

    # Scopo: Risolve il template applicabile per (sorgente_tipo, emittente).
    #        Usa il flag `is_default=true` (partial-unique DDL) come selettore
    #        deterministico: in v1 esiste al massimo 1 template default per
    #        coppia (output, sorgente, emittente). Se `tipo_documento_output_id`
    #        e' fornito, vincola anche quel filtro (necessario quando lo stesso
    #        sorgente_tipo puo' produrre output diversi). Lo scope emittente
    #        del caller filtra come per get_template (whitelist `bigint[]`).
    #        Ritorna None se nessun template matcha (il service traduce in
    #        404 unificato).
    def find_template_applicabile(
        self,
        *,
        sorgente_tipo_id: int,
        emittente_fiscale_id: int,
        tipo_documento_output_id: int | None,
        emittente_ids_scope: list[int] | None,
    ) -> dict[str, Any] | None:
        conditions = [
            "t.sorgente_tipo_id = %s",
            "t.emittente_fiscale_id = %s",
            "t.attivo = true",
            "t.is_default = true",
        ]
        params: list[Any] = [int(sorgente_tipo_id), int(emittente_fiscale_id)]
        if tipo_documento_output_id is not None:
            conditions.append("t.tipo_documento_output_id = %s")
            params.append(int(tipo_documento_output_id))
        if emittente_ids_scope is not None:
            conditions.append("t.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT {_TEMPLATES_PROJECTION_DETAIL}
            {_TEMPLATES_FROM}
            WHERE {where_clause}
            ORDER BY t.id ASC
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Conta i template attivi che matchano (sorgente_tipo, emittente)
    #        ignorando il flag `is_default`. Serve al service per discriminare
    #        l'errore E_DOCUMENTI_NOT_FOUND: "non c'e' nessun template" vs
    #        "ci sono template ma nessuno e' marcato predefinito" — il secondo
    #        caso e' fix istantaneo lato admin (flag default), il primo richiede
    #        di caricare un template ex novo. Filtri identici a
    #        find_template_applicabile (output id opzionale, scope emittente
    #        opzionale) tranne il vincolo is_default.
    def count_templates_attivi_no_default(
        self,
        *,
        sorgente_tipo_id: int,
        emittente_fiscale_id: int,
        tipo_documento_output_id: int | None,
        emittente_ids_scope: list[int] | None,
    ) -> int:
        conditions = [
            "t.sorgente_tipo_id = %s",
            "t.emittente_fiscale_id = %s",
            "t.attivo = true",
        ]
        params: list[Any] = [int(sorgente_tipo_id), int(emittente_fiscale_id)]
        if tipo_documento_output_id is not None:
            conditions.append("t.tipo_documento_output_id = %s")
            params.append(int(tipo_documento_output_id))
        if emittente_ids_scope is not None:
            conditions.append("t.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT COUNT(*)
            FROM documenti.template_documenti t
            WHERE {where_clause}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    # Scopo: Carica la versione PUBBLICATA attiva con `validita @> %s`
    #        (CURRENT_DATE passata dal service per testabilita'). Ritorna
    #        la versione piu' recente (`versione DESC LIMIT 1`); se nessuna
    #        riga matcha, ritorna None (404 lato service).
    def get_versione_pubblicata_attiva(
        self,
        template_documento_id: int,
        *,
        today: Any,
    ) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_VERSIONI_PROJECTION_DETAIL}
            {_VERSIONI_FROM}
            WHERE v.template_documento_id = %s
              AND v.stato = 'PUBBLICATA'
              AND v.attivo = true
              AND v.validita @> %s::date
            ORDER BY v.versione DESC, v.id DESC
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(template_documento_id), today])
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Calcola il prossimo progressivo per (sorgente_tipo, sorgente_uid,
    #        sorgente_riga). `NULLS NOT DISTINCT` sull'unique vincolo DDL
    #        gestisce correttamente `sorgente_riga IS NULL` (caso testata).
    #        Race window protetta dall'unique: se due chiamate concorrenti
    #        calcolano lo stesso N, l'INSERT del secondo solleva
    #        IntegrityError che il service mappa.
    def next_progressivo_sorgente(
        self,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None,
    ) -> int:
        if sorgente_riga is None:
            sql = """
                SELECT COALESCE(MAX(progressivo_sorgente), 0) + 1
                  FROM documenti.documenti_generati
                 WHERE sorgente_tipo_id = %s
                   AND sorgente_uid     = %s
                   AND sorgente_riga IS NULL
            """
            params: list[Any] = [int(sorgente_tipo_id), sorgente_uid]
        else:
            sql = """
                SELECT COALESCE(MAX(progressivo_sorgente), 0) + 1
                  FROM documenti.documenti_generati
                 WHERE sorgente_tipo_id = %s
                   AND sorgente_uid     = %s
                   AND sorgente_riga    = %s
            """
            params = [int(sorgente_tipo_id), sorgente_uid, int(sorgente_riga)]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: INSERT documento generato. Usa solo colonne whitelisted in
    #        DOCUMENTO_GENERATO_CREATE_COLUMNS. Ritorna (id, uid). I trigger
    #        DB calcolano `tx_id` (Decisione 76), audit, validita e
    #        coerenza testata; il CHECK A coerenza blocca incongruenze
    #        (output/template/versione/sorgente_tipo/emittente).
    def create_documento_generato(
        self, data: dict[str, Any]
    ) -> tuple[int, str]:
        cols: list[str] = []
        vals: list[Any] = []
        placeholders: list[str] = []
        for col in DOCUMENTO_GENERATO_CREATE_COLUMNS:
            if col in data:
                column_type = _DOCUMENTO_GENERATO_COLUMN_TYPES.get(col, "text")
                cols.append(col)
                vals.append(to_write_param(data[col], column_type))
                placeholders.append(sql_placeholder(column_type))
        sql = f"""
            INSERT INTO documenti.documenti_generati ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id, uid
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0]), str(row[1])

    # Scopo: INSERT file persistito collegato al documento generato. Ritorna
    #        l'id riga. Vincoli rilevanti DDL: `is_principale` partial-unique
    #        per documento (un solo principale per doc), unique
    #        `(documento_generato_id, file_tipo_id, ordinamento)`.
    def create_documento_generato_file(self, data: dict[str, Any]) -> int:
        cols: list[str] = []
        vals: list[Any] = []
        placeholders: list[str] = []
        for col in DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS:
            if col in data:
                column_type = _DOCUMENTO_GENERATO_FILE_COLUMN_TYPES.get(col, "text")
                cols.append(col)
                vals.append(to_write_param(data[col], column_type))
                placeholders.append(sql_placeholder(column_type))
        sql = f"""
            INSERT INTO documenti.documenti_generati_file ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: INSERT evento timeline append-only. Decisione 76: NO `tx_id`
    #        esplicito (la popola l'automation regola 4). Il caller passa
    #        `evento_tipo` ∈ {GENERATO, SCARICATO, STORAGE_ORPHAN} (set chiuso
    #        v1). I guard DB A5/A6 bloccano UPDATE/DELETE successivi.
    def emit_evento_documento(self, data: dict[str, Any]) -> int:
        cols: list[str] = []
        vals: list[Any] = []
        placeholders: list[str] = []
        for col in EVENTO_DOCUMENTO_CREATE_COLUMNS:
            if col in data:
                column_type = _EVENTO_DOCUMENTO_COLUMN_TYPES.get(col, "text")
                cols.append(col)
                vals.append(to_write_param(data[col], column_type))
                placeholders.append(sql_placeholder(column_type))
        sql = f"""
            INSERT INTO documenti.documenti_generati_eventi ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608 — colonne whitelisted, valori parametrici
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Lookup tipo file per codice_interno (es. 'PDF_FINALE'). Match
    #        sulla colonna IMMUTABILE codice_interno (non `codice`, che e'
    #        l'etichetta a video mutabile). Usato dall'orchestratore per
    #        ottenere l'`id` da passare a
    #        `create_documento_generato_file.file_tipo_id` senza hardcodare ID
    #        numerici (memoria feedback_no_hardcoded_ids).
    def get_tipo_file_documento_by_codice(
        self, codice: str
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, attivo
                  FROM documenti.tipi_file_documento
                 WHERE codice_interno = %s
                """,
                [codice],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {"id": int(row[0]), "codice": str(row[1]), "attivo": bool(row[2])}

    # =================================================================
    # Lookup sorgente + lista documenti generati (Tranche K)
    # =================================================================

    # Scopo: Lookup `config.sorgenti.id` per codice_interno (es. 'PREVENTIVO').
    #        Match sulla colonna IMMUTABILE codice_interno (non `codice`
    #        mutabile). Usato dal caller (es. view di dominio Tranche K) per
    #        evitare ID numerici hardcoded a livello applicativo.
    def get_sorgente_tipo_id_by_codice(
        self, codice: str
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, attivo
                  FROM config.sorgenti
                 WHERE codice_interno = %s
                """,
                [codice],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {"id": int(row[0]), "codice": str(row[1]), "attivo": bool(row[2])}

    # Scopo: Lista paginata documenti generati per una sorgente specifica.
    #        Filtra su (sorgente_tipo_id, sorgente_uid) e opzionalmente
    #        `sorgente_riga`. Scope emittente whitelist via `ANY(%s)`.
    #        ORDER BY `generato_at DESC, id DESC` (timeline naturale per
    #        l'utente: piu' recenti in alto). Tiebreaker `id DESC` per
    #        paginazione deterministica.
    def list_documenti_per_sorgente(
        self,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None,
        emittente_ids_scope: list[int] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions = [
            "d.sorgente_tipo_id = %s",
            "d.sorgente_uid = %s",
        ]
        params: list[Any] = [int(sorgente_tipo_id), sorgente_uid]
        if sorgente_riga is None:
            conditions.append("d.sorgente_riga IS NULL")
        else:
            conditions.append("d.sorgente_riga = %s")
            params.append(int(sorgente_riga))
        if emittente_ids_scope is not None:
            conditions.append("d.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        count_sql = f"""
            SELECT COUNT(*)
              FROM documenti.documenti_generati d
             WHERE {where_clause}
        """  # noqa: S608 — colonne fisse, valori parametrici
        data_sql = f"""
            SELECT
                d.id,
                d.uid::text AS uid,
                d.tipo_documento_output_id,
                d.template_documento_id,
                d.template_versione_id,
                d.sorgente_tipo_id,
                d.sorgente_uid,
                d.sorgente_riga,
                d.progressivo_sorgente,
                d.stato,
                d.titolo,
                d.nome_file,
                d.pdf_hash,
                d.generato_da_user_id,
                d.generato_at,
                d.emittente_fiscale_id,
                -- Il file originale esiste? La persistenza dei file e' iniziata
                -- il 2026-07-21: i documenti anteriori NON hanno il file, e per
                -- loro «Scarica originale» risponderebbe 404. Il flag permette
                -- alla UI di disabilitare l'azione CON LA RAGIONE invece di
                -- lasciarla fallire (brief ristampa-fedele §5.2.2), e di
                -- proporre al suo posto la ristampa fedele, che per quei
                -- documenti e' l'unico percorso possibile.
                EXISTS (
                    SELECT 1
                      FROM documenti.documenti_generati_file f
                     WHERE f.documento_generato_id = d.id
                       AND f.is_principale = true
                ) AS has_file_principale
              FROM documenti.documenti_generati d
             WHERE {where_clause}
             ORDER BY d.generato_at DESC, d.id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total

    # Scopo: Dettaglio documento generato per id, con scope emittente.
    #        Ritorna None se inesistente o fuori scope (il service traduce
    #        in 404 unificato, no leak). Proiezione completa per audit.
    def get_documento_generato(
        self,
        documento_id: int,
        *,
        emittente_ids_scope: list[int] | None,
    ) -> dict[str, Any] | None:
        conditions = ["d.id = %s"]
        params: list[Any] = [int(documento_id)]
        if emittente_ids_scope is not None:
            conditions.append("d.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT
                d.id,
                d.uid::text AS uid,
                d.tipo_documento_output_id,
                d.template_documento_id,
                d.template_versione_id,
                d.sorgente_tipo_id,
                d.sorgente_uid,
                d.sorgente_riga,
                d.progressivo_sorgente,
                d.stato,
                d.titolo,
                d.nome_file,
                d.context_hash,
                d.template_hash,
                d.pdf_hash,
                d.generato_da_user_id,
                d.generato_at,
                d.emittente_fiscale_id,
                d.meta
              FROM documenti.documenti_generati d
             WHERE {where_clause}
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Snapshot CONGELATO di un documento generato: la testata + il
    #        `context_json` con cui fu stampato. Separato da
    #        `get_documento_generato` perche' il context puo' essere grande e
    #        serve SOLO alla ristampa fedele — le altre letture (download,
    #        liste, allegati) non devono pagarlo.
    #        ⚠️ E' la lettura portante della ristampa fedele: il contesto si
    #        LEGGE, non si ricostruisce (un contesto ricostruito e' un
    #        documento nuovo travestito da vecchio). Immutabilita' garantita a
    #        DB da `trgfn_documenti_generati_protect_snapshot`.
    def get_documento_generato_snapshot(
        self,
        documento_id: int,
        *,
        emittente_ids_scope: list[int] | None,
    ) -> dict[str, Any] | None:
        conditions = ["d.id = %s"]
        params: list[Any] = [int(documento_id)]
        if emittente_ids_scope is not None:
            conditions.append("d.emittente_fiscale_id = ANY(%s)")
            params.append(list(emittente_ids_scope))
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT
                d.id,
                d.uid::text AS uid,
                d.template_documento_id,
                d.template_versione_id,
                d.sorgente_tipo_id,
                d.sorgente_uid,
                d.sorgente_riga,
                d.stato,
                d.titolo,
                d.nome_file,
                d.context_json,
                d.context_hash,
                d.template_hash,
                d.pdf_hash,
                d.generato_at,
                d.emittente_fiscale_id
              FROM documenti.documenti_generati d
             WHERE {where_clause}
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Versione template per id SENZA filtri di stato ne' di template.
    #        E' la lettura della ristampa fedele: la versione pinnata sul
    #        documento va caricata **anche se OBSOLETA o non piu' attiva** —
    #        e' esattamente quella con cui il documento nacque. Le altre
    #        letture (`get_versione`, `get_versione_pubblicata_attiva`)
    #        filtrano di proposito e non servono qui.
    #        Nessun rischio di leak: l'id arriva da una riga di
    #        `documenti_generati` gia' passata per lo scope emittente.
    def get_versione_by_id(self, versione_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_VERSIONI_PROJECTION_DETAIL}
            {_VERSIONI_FROM}
            WHERE v.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(versione_id)])
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Recupera la riga `documenti_generati_file` principale del
    #        documento (`is_principale=true`, partial-unique per design v1
    #        garantisce al massimo 1 risultato). Ritorna metadati necessari
    #        al download: storage_key + mime_type + file_name + file_size.
    def get_documento_generato_file_principale(
        self, documento_generato_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.documento_generato_id,
                f.file_tipo_id,
                f.mime_type,
                f.file_name,
                f.file_size_bytes,
                f.storage_key,
                f.sha256,
                f.is_principale
              FROM documenti.documenti_generati_file f
             WHERE f.documento_generato_id = %s
               AND f.is_principale = true
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(documento_generato_id)])
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: Prossimo `ordinamento` globale per i file di un documento.
    #        Usato per accodare allegati (file secondari) dopo il principale:
    #        principale = 1, primo allegato = 2, ecc. Calcolo MAX+1 su tutti
    #        i file del documento (non per file_tipo) per ordering leggibile.
    def get_next_file_ordinamento(self, documento_generato_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(ordinamento), 0) + 1
                  FROM documenti.documenti_generati_file
                 WHERE documento_generato_id = %s
                """,
                [int(documento_generato_id)],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Lista di tutti i file di un documento generato (principale +
    #        allegati), ordinata per `ordinamento`. Usata dalla UI per
    #        elencare gli allegati e offrirne il download per id.
    def list_documento_generato_files(
        self, documento_generato_id: int,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                f.id,
                f.documento_generato_id,
                f.file_tipo_id,
                tf.codice          AS file_tipo_codice,
                f.mime_type,
                f.file_name,
                f.file_size_bytes,
                f.storage_key,
                f.sha256,
                f.ordinamento,
                f.is_principale
              FROM documenti.documenti_generati_file f
              JOIN documenti.tipi_file_documento tf ON tf.id = f.file_tipo_id
             WHERE f.documento_generato_id = %s
             ORDER BY f.ordinamento ASC, f.id ASC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(documento_generato_id)])
            return rows_to_list(cursor)

    # Scopo: Recupera una singola riga file (principale o allegato) per id,
    #        nel contesto di un documento. Ritorna metadati per il download.
    #        Filtra anche su `documento_generato_id` (defense-in-depth: il
    #        caller verifica lo scope sul documento, qui evitiamo cross-doc).
    def get_documento_generato_file(
        self, documento_generato_id: int, file_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.documento_generato_id,
                f.file_tipo_id,
                f.mime_type,
                f.file_name,
                f.file_size_bytes,
                f.storage_key,
                f.sha256,
                f.is_principale
              FROM documenti.documenti_generati_file f
             WHERE f.documento_generato_id = %s
               AND f.id = %s
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(documento_generato_id), int(file_id)])
            results = rows_to_list(cursor)
        return results[0] if results else None
