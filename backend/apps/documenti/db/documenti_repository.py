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

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import (
    execute_dynamic_insert,
    execute_dynamic_update,
)
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
    # Ordinabile a catalogo dal 2026-10-21 (lista 24, colonna «Standard», brief-
    # db-modelli-documento-standard): senza la voce qui la freccia rispondeva 400.
    "standard": "t.standard",
    "data_insert": "t.data_insert",
    "data_update": "t.data_update",
}


# Whitelist ORDER BY dei documenti generati di una sorgente (lista 84,
# `documenti.documenti_sorgente`). ⛔ Chiavata sul `campo_sorgente` FISICO del
# catalogo, che e' cio' che il frontend manda come `order_by`. «Originale»
# (`has_file_principale`) e le azioni NON ordinano a catalogo: fuori whitelist.
DOCUMENTI_SORGENTE_ORDER_COLUMNS: dict[str, str] = {
    "progressivo_sorgente": "d.progressivo_sorgente",
    "generato_at": "d.generato_at",
    "titolo": "d.titolo",
    "nome_file": "d.nome_file",
    "stato": "d.stato",
}

# Colonne DATA della whitelist qui sopra: senza `order_dir` ordinano DESC
# (`sql_order_clause(colonne_desc=…)`, regola di Tid del 2026-09-02). Insieme
# confrontato col seed da `test_liste_configurabili_seed` (test 10).
DOCUMENTI_SORGENTE_SORT_COLONNE_DATA: frozenset[str] = frozenset({"generato_at"})

# Whitelist ORDER BY delle versioni di un template (lista 88,
# `documenti.template_versioni`). `valido_al` vuota = senza scadenza: con
# `COALESCE(…, 'infinity')` sta IN CIMA al DESC, come in ogni lista con
# validita' del progetto (una versione aperta e' la piu' «lunga»).
TEMPLATE_VERSIONI_ORDER_COLUMNS: dict[str, str] = {
    "versione": "v.versione",
    "titolo": "v.titolo",
    "stato": "v.stato",
    "valido_dal": "v.valido_dal",
    "valido_al": "COALESCE(v.valido_al, 'infinity'::date)",
    "attivo": "v.attivo",
    "data_update": "v.data_update",
}

# Colonne DATA della whitelist delle versioni (vedi sopra).
TEMPLATE_VERSIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset(
    {"valido_dal", "valido_al", "data_update"}
)


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
    "versione_contesto",
    "context_schema",
    "meta",
    "attivo",
    # L'origine di una copia dello standard: la scrive solo «personalizza»
    # sulla prima versione (brief-db-modelli-documento-standard §4.1 Q-5).
    # Che punti a una versione standard della stessa coppia lo controlla il
    # guard DB (E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA).
    "derivata_da_versione_id",
)


# Whitelist colonne ammesse in UPDATE su template_documenti_versioni.
# Immutabili escluse: `template_documento_id`, `versione`, `stato`.
# La transizione di stato passa solo dal comando dedicato pubblica_versione.
# Il trigger DB A1 (protect_pubblicata) blocca comunque l'update di
# html/css/render/layout/valido_* se OLD.stato='PUBBLICATA' — defense-in-depth.
# `versione_contesto` (la forma dei dati che la versione legge, NOT NULL senza
# default) e' nel suo `UPDATE OF` dal 20260930-17: si cambia solo in BOZZA.
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
    "versione_contesto",
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

# Colonne jsonb delle scritture dinamiche, dichiarate al BB (`jsonb=`).
# ⭐ Regola decisa da Tid il 2026-09-26: una STRINGA destinata a una colonna
#    jsonb e' TESTO JSON, non uno scalare stringa — dict/list il BB li
#    serializza da solo. Fino a quel giorno queste tre tabelle passavano da
#    `to_write_param` (sempre `json.dumps`): una stringa sarebbe diventata lo
#    scalare `"..."`. Oggi i chiamanti passano solo dict (`context_json` e'
#    il `json.loads` del contesto canonico, `detail`/`meta` letterali), quindi
#    nessun valore scritto cambia.
_DOCUMENTO_GENERATO_JSONB: tuple[str, ...] = ("context_json", "meta")
_DOCUMENTO_GENERATO_FILE_JSONB: tuple[str, ...] = ("meta",)
_EVENTO_DOCUMENTO_JSONB: tuple[str, ...] = ("detail", "meta")
_TEMPLATE_JSONB: tuple[str, ...] = ("meta",)
_ASSET_JSONB: tuple[str, ...] = ("meta",)
_VERSIONE_JSONB: tuple[str, ...] = ("context_schema", "meta")

# Colonne di `template_documenti_versioni` le cui stringhe NON si strippano
# (`letterali=` del BB, 2026-09-26): sono il CORPO del template, dove uno
# spazio o un a-capo ai bordi e' contenuto (un `<pre>`, un blocco markdown
# indentato), non rumore d'input.
_VERSIONE_LETTERALI: tuple[str, ...] = (
    "html_template",
    "css_template",
    "markdown_template",
)


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

# Cosa si PUO' cercare nei documenti generati di una sorgente (lista 84) e nelle
# versioni di un template (lista 88). Colonne semplici della tabella nel `FROM`,
# proiettate con lo stesso nome: forma a tupla, alias passato al BB.
_RICERCA_DOCUMENTI_SORGENTE = RicercaFull("documenti.documenti_sorgente", ("titolo", "nome_file"))
_RICERCA_TEMPLATE_VERSIONI = RicercaFull("documenti.template_versioni", ("titolo",))

# Quando un asset e' UTILIZZABILE nel render di oggi: attivo e valido oggi.
# ⭐ Una condizione sola, letta da due punti (regola del 2): la risoluzione di
#    `asset:<codice_interno>` nel render (`get_asset_per_render`) e il filtro
#    `utilizzabili` della lista, con cui l'editor dei template mostra gli asset
#    da richiamare. Se le due divergessero, l'editor proporrebbe un asset che
#    il render rifiuta. La validita' si legge dalla colonna generata
#    `validita`, mai ricalcolata da `valido_dal`/`valido_al`.
_ASSET_UTILIZZABILE_OGGI = "(a.attivo AND a.validita @> (SELECT script.fn_data_operativa()))"

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
    t.standard,
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

# ⚠️ L'emittente e' in LEFT JOIN: il modello standard non ne ha uno
#    (`chk_template_documenti_standard_senza_emittente`), e un JOIN interno lo
#    toglierebbe da ogni lettura senza nessun errore.
_TEMPLATES_FROM = """
    FROM documenti.template_documenti t
    JOIN documenti.tipi_documento_output tdo ON tdo.id = t.tipo_documento_output_id
    JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
    LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t.emittente_fiscale_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
"""

# Il perimetro di lettura dei modelli: quelli degli emittenti in whitelist,
# piu' gli standard, che servono a tutti (brief-db-modelli-documento-standard
# §6). Un parametro: la whitelist `bigint[]`.
_TEMPLATE_IN_SCOPE = "(t.standard OR t.emittente_fiscale_id = ANY(%s))"


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
    v.versione_contesto,
    v.derivata_da_versione_id,
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
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        if order_by not in TEMPLATES_ORDER_COLUMNS:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Colonna di ordinamento non valida: '{order_by}'.",
                detail=f"ammesse={sorted(TEMPLATES_ORDER_COLUMNS.keys())!r}",
            )
        # ⛔ Direzione dal BB (`sql_order_clause`), non da un confronto scritto
        #    qui: fino al 2026-09-26 `"DESC" if order_dir.lower() == "desc" else
        #    "ASC"` trasformava in ASC, in silenzio, qualunque valore estraneo.
        #    Ora `?order_dir=giu` e' un 400, e i NULL stanno dove starebbe lo
        #    zero come in ogni altra lista. La colonna e' gia' stata verificata
        #    sopra col codice di dominio: `rifiuta_fuori_whitelist` lo dichiara,
        #    e `default` e' il `default_order` della view.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=TEMPLATES_ORDER_COLUMNS, default="t.codice", tiebreak="t.id",
            rifiuta_fuori_whitelist=True,
        )

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
            # Lista vuota = nessun emittente -> i soli standard.
            conditions.append(_TEMPLATE_IN_SCOPE)
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
            ORDER BY {ordinamento}
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
            conditions.append(_TEMPLATE_IN_SCOPE)
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

    # Scopo: Lista paginata delle versioni di un template (lista
    #        configurabile `documenti.template_versioni`, 88): proiezione
    #        leggera, senza html/css/markdown. Filtri opzionali `attivo` e
    #        `stato`, ricerca sul titolo, ordinamento dalla whitelist
    #        `TEMPLATE_VERSIONI_ORDER_COLUMNS`; di partenza `versione DESC`
    #        (la piu' recente in cima, come il preset a catalogo).
    # ⭐ Fino al 2026-09-27 non era paginata («il ciclo BOZZA→PUBBLICATA→
    #    OBSOLETA ha cardinalita' contenuta»): e' una previsione sui DATI, e le
    #    previsioni sui dati non decidono la forma di una lista. Pagina e
    #    totale escono da UNA query (`fetch_paged_with_total`).
    def list_versioni(
        self,
        template_documento_id: int,
        *,
        attivo: bool | None,
        stato: str | None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=TEMPLATE_VERSIONI_ORDER_COLUMNS,
            default="v.versione", default_desc=True, tiebreak="v.id",
            colonne_desc=TEMPLATE_VERSIONI_SORT_COLONNE_DATA,
        )

        conditions = ["v.template_documento_id = %s"]
        params: list[Any] = [int(template_documento_id)]
        if attivo is not None:
            conditions.append("v.attivo = %s")
            params.append(attivo)
        if stato is not None:
            conditions.append("v.stato = %s")
            params.append(stato)
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_TEMPLATE_VERSIONI, alias="v",
        )
        from_where = f"{_VERSIONI_FROM} WHERE {' AND '.join(conditions)}"

        return fetch_paged_with_total(
            f"""
            SELECT {_VERSIONI_PROJECTION},
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist TEMPLATE_VERSIONI_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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

    # Scopo: INSERT testata template col BB `execute_dynamic_insert`, whitelist
    #        TEMPLATE_CREATE_COLUMNS. Eventuali violazioni UNIQUE/CHECK/FK
    #        vengono propagate al service che le mappa via map_integrity_error.
    #        ⛔ Dal 2026-09-26 una chiave fuori whitelist e' `RuntimeError`, non
    #        piu' uno scarto silenzioso: il service valida le chiavi del payload
    #        (`validate_allowed_keys`, 400) prima di arrivare qui.
    #        ⚠️ Fino a quel giorno `meta` (dict da `optional_meta`) arrivava
    #        nudo al cursor: psycopg non adatta un dict, quindi ogni create con
    #        `meta` era un 500. Il BB lo serializza (`::jsonb`).
    def create_template(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "documenti.template_documenti", data,
            allowed=TEMPLATE_CREATE_COLUMNS, jsonb=_TEMPLATE_JSONB,
        )
        return int(riga["id"])

    # Scopo: UPDATE testata template sui soli campi presenti in `data` (BB
    #        `execute_dynamic_update`). Ritorna True se almeno una riga
    #        aggiornata, False se id assente (il service traduce in 404) o
    #        `data` vuoto. Le immutabili (output/sorgente/emittente) sono escluse
    #        dalla whitelist TEMPLATE_UPDATE_COLUMNS: il service le rifiuta con
    #        un 400 parlante, qui sarebbero `RuntimeError`.
    def update_template(self, template_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "documenti.template_documenti", int(template_id), data,
            allowed=TEMPLATE_UPDATE_COLUMNS, jsonb=_TEMPLATE_JSONB,
        )

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

    # Scopo: La versione dello standard da cui parte «personalizza»: la
    #        PUBBLICATA col numero piu' alto, cioe' quella con cui la vista
    #        `vw_template_personalizzati_scarto` confronta le copie (una copia
    #        che parte da li' esce ALLINEATA). Attiva: il DB rifiuta una
    #        derivazione da una versione spenta (trigger a10 sulla FK).
    #        None se lo standard non ne ha.
    def get_ultima_versione_pubblicata(
        self, template_documento_id: int,
    ) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_VERSIONI_PROJECTION_DETAIL}
            {_VERSIONI_FROM}
            WHERE v.template_documento_id = %s
              AND v.stato = 'PUBBLICATA'
              AND v.attivo
            ORDER BY v.versione DESC
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(template_documento_id)])
            results = rows_to_list(cursor)
        return results[0] if results else None

    # Scopo: INSERT versione template (BB `execute_dynamic_insert`) sulle
    #        colonne di VERSIONE_CREATE_COLUMNS. `validita` (daterange) e'
    #        STORED generated column (PG 18) calcolata da `valido_dal`/
    #        `valido_al`. Eventuali violazioni unique/check vengono propagate
    #        al service. None scrive NULL (il clone azzera le date cosi').
    # ⭐ 2026-09-26: migrato sul BB con `letterali=` sui corpi del template
    #    (`_VERSIONE_LETTERALI`): uno spazio ai bordi di un HTML/CSS/markdown e'
    #    contenuto, e il CLONE copia il testo del sorgente cosi' com'e'.
    #    `context_schema`/`meta` in `jsonb=`: dal payload arrivano dict (fino a
    #    quel giorno andavano nudi al cursor, che non li sa adattare: 500); dal
    #    clone arriva il TESTO letto dal DB (la connessione Django rende il
    #    jsonb come stringa), che e' testo JSON e passa cosi' com'e'.
    #    ⛔ Una chiave fuori whitelist e' `RuntimeError`, non piu' uno scarto
    #    silenzioso: il service valida le chiavi del payload (400) e compone
    #    da se' `template_documento_id`/`versione`/`stato`.
    def create_versione(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "documenti.template_documenti_versioni", data,
            allowed=VERSIONE_CREATE_COLUMNS, jsonb=_VERSIONE_JSONB,
            letterali=_VERSIONE_LETTERALI,
        )
        return int(riga["id"])

    # Scopo: UPDATE versione sui soli campi presenti in `data` (BB
    #        `execute_dynamic_update`, stesse `jsonb`/`letterali` del create).
    #        False se `data` vuoto o id assente. Il trigger DB A1
    #        (protect_pubblicata) blocca l'update se OLD.stato='PUBBLICATA'
    #        — defense-in-depth: il service controlla lo stato, ma il DB
    #        rifiuta comunque le modifiche. Le immutabili (template, numero,
    #        stato) sono fuori da VERSIONE_UPDATE_COLUMNS: `RuntimeError`.
    def update_versione(self, versione_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "documenti.template_documenti_versioni", int(versione_id), data,
            allowed=VERSIONE_UPDATE_COLUMNS, jsonb=_VERSIONE_JSONB,
            letterali=_VERSIONE_LETTERALI,
        )

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
    #        `versione_contesto` e' la forma dei dati che il builder del
    #        template produce (`CONTEXT_VERSION`): obbligatoria e senza default
    #        a DB, la versione si pubblica solo se dichiara di leggere quella
    #        (E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA, 20260930-21).
    def pubblica_versione(
        self,
        versione_id: int,
        *,
        valido_dal: Any,
        valido_al: Any,
        versione_contesto: int,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT versione_id
                  FROM documenti.fn_pubblica_template_documento_versione(
                    p_versione_id       => %s,
                    p_valido_dal        => %s,
                    p_versione_contesto => %s,
                    p_valido_al         => %s
                  )
                """,
                [int(versione_id), valido_dal, int(versione_contesto), valido_al],
            )
            return cursor.fetchone() is not None

    # Scopo: Il patto fra una versione di template e la forma dei dati, chiesto
    #        al DB PRIMA del render: `documenti.fn_guard_versione_contesto`
    #        solleva se la versione non legge `versione_contesto` (la forma che
    #        il builder produce). E' la stessa funzione che il trigger
    #        sull'INSERT di `documenti_generati` chiama sul contesto congelato:
    #        chiederla prima evita un PDF generato e poi rifiutato. La regola non
    #        si ricopia in Python (confronto sul `versione_contesto` letto): una
    #        funzione, tre chiamanti.
    def guard_versione_contesto(
        self, template_versione_id: int, versione_contesto: int,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT documenti.fn_guard_versione_contesto(%s, %s)",
                [int(template_versione_id), int(versione_contesto)],
            )

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
        utilizzabili: bool | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        if order_by not in ASSET_ORDER_COLUMNS:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Colonna di ordinamento non valida: '{order_by}'.",
                detail=f"ammesse={sorted(ASSET_ORDER_COLUMNS.keys())!r}",
            )
        # ⛔ Direzione dal BB, come `list_templates` (2026-09-26): prima un
        #    valore estraneo diventava ASC in silenzio.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ASSET_ORDER_COLUMNS, default="a.codice", tiebreak="a.id",
            rifiuta_fuori_whitelist=True,
        )

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        # Filtro (lo sceglie il client, assente = nessun filtro): True = solo
        # gli asset che il render accetta oggi, False = solo quelli che rifiuta.
        if utilizzabili is not None:
            conditions.append(
                _ASSET_UTILIZZABILE_OGGI if utilizzabili
                else f"NOT {_ASSET_UTILIZZABILE_OGGI}"
            )
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
            ORDER BY {ordinamento}
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

    # Scopo: L'asset che un template richiama nel render con
    #        `asset:<codice_interno>` (brief-be-documenti-risorse-esterne-render-pdf).
    #        La chiave e' `(emittente del template, codice_interno)`, la stessa
    #        del vincolo `uq_template_asset_emittente_codice_interno`: al piu'
    #        una riga, e il `codice_interno` non si modifica (lock automatico),
    #        quindi un asset rinominato non rompe i template che lo citano.
    #        `solo_validi`: generazione e anteprima vedono solo gli asset
    #        attivi e validi oggi; la ristampa fedele passa False, perche'
    #        l'asset e' immutabile e non si cancella, e quello di allora resta
    #        quello giusto anche se oggi e' scaduto (decisione Tid 2026-10-01).
    #        «Attivo e valido oggi» e' `_ASSET_UTILIZZABILE_OGGI`, la stessa
    #        condizione del filtro `utilizzabili` della lista.
    def get_asset_per_render(
        self,
        emittente_fiscale_id: int,
        codice_interno: str,
        *,
        solo_validi: bool,
    ) -> dict[str, Any] | None:
        conditions = ["a.emittente_fiscale_id = %s", "a.codice_interno = %s"]
        if solo_validi:
            conditions.append(_ASSET_UTILIZZABILE_OGGI)
        sql = f"""
            SELECT a.id, a.storage_key, a.mime_type, a.sha256
            FROM documenti.template_asset a
            WHERE {" AND ".join(conditions)}
        """  # noqa: S608 — WHERE da condizioni letterali, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(emittente_fiscale_id), codice_interno])
            results = rows_to_list(cursor)
        return results[0] if results else None

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

    # Scopo: INSERT asset col BB `execute_dynamic_insert`, whitelist
    #        ASSET_CREATE_COLUMNS. `validita` (daterange) e' STORED generated
    #        column (PG 18) calcolata da `valido_dal`/`valido_al`. Il vincolo
    #        unique (emittente_fiscale_id, sha256) garantisce dedup natural:
    #        re-upload dello stesso file -> IntegrityError mappato.
    #        ⚠️ Lo strip del BB tocca anche `sha256`/`storage_key`/`file_name`:
    #        li calcola il service (digest esadecimale, chiave composta, nome
    #        gia' ripulito da `_sanitize_file_name`), nessuno ha spazi ai bordi.
    #        `meta` come in `create_template` (prima del 2026-09-26: 500).
    def create_asset(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "documenti.template_asset", data,
            allowed=ASSET_CREATE_COLUMNS, jsonb=_ASSET_JSONB,
        )
        return int(riga["id"])

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
    #        guardrail finale: ASSET_UPDATE_COLUMNS le esclude per design, e dal
    #        2026-09-26 passarle qui e' `RuntimeError` (BB), non uno scarto
    #        silenzioso: il service le rifiuta prima con un 400.
    def update_asset_metadati(
        self, asset_id: int, data: dict[str, Any]
    ) -> bool:
        return execute_dynamic_update(
            "documenti.template_asset", int(asset_id), data,
            allowed=ASSET_UPDATE_COLUMNS, jsonb=_ASSET_JSONB,
        )

    # =================================================================
    # Resolve template + versione per render (Tranche I)
    # =================================================================

    # Scopo: Il modello e la versione con cui si stampa un documento della
    #        sorgente per l'emittente del documento, chiesti alla porta unica
    #        del DB: `documenti.fn_risolvi_template_applicabile`
    #        (brief-db-modelli-documento-standard §10.3 K-2). Senza
    #        `template_documento_id` il DB lo SCEGLIE coi due livelli (strada B,
    #        §4.1 Q-2): il predefinito dell'emittente se ha modelli suoi che
    #        possono stampare, se no il predefinito standard. Con
    #        `template_documento_id` il DB lo VERIFICA: adatto al documento
    #        (sorgente, tipo, emittente oppure standard) e stampabile oggi.
    #        Ritorna `{template_documento_id, livello, template_versione_id}`,
    #        livello `EMITTENTE` | `STANDARD` | `INDICATO`; ogni rifiuto lo
    #        solleva la funzione, col suo codice (SENZA_PREDEFINITO,
    #        NON_RISOLTO, AMBIGUO, NON_COERENTE, NON_STAMPABILE).
    # ⭐ Modello E versione: «puo' stampare» e' scritto una volta sola, nella
    #    vista `vw_template_versioni_stampabili` che la funzione legge.
    #    Ricercare la versione qui con filtri nostri ne farebbe una seconda
    #    copia, ed e' successo: fino al 2026-10-21 il modello indicato passava
    #    da `get_versione_pubblicata_attiva`, che non guardava se il modello
    #    era attivo (un modello spento indicato a mano stampava ancora) e
    #    usava il giorno del BE invece di `script.fn_data_operativa()`.
    # ⛔ La regola non si ricopia qui: fino al 2026-10-19 il BE la scriveva da
    #    se' (`ORDER BY t.id LIMIT 1`, cioe' l'id piu' basso quando il tipo
    #    mancava) e con una seconda query (`count_templates_attivi_no_default`)
    #    ne ricopiava i filtri per scegliere il messaggio.
    #    Il perimetro non si rifa': l'emittente e' quello del documento, che il
    #    chiamante ha gia' verificato nella whitelist, e il modello indicato lo
    #    legge il chiamante dentro lo scope prima di chiederlo qui.
    def risolvi_template_applicabile(
        self,
        *,
        sorgente_tipo_id: int,
        emittente_fiscale_id: int,
        tipo_documento_output_id: int | None,
        template_documento_id: int | None = None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT template_documento_id, livello, template_versione_id
                  FROM documenti.fn_risolvi_template_applicabile(%s, %s, %s, %s)
                """,
                [
                    int(sorgente_tipo_id),
                    int(emittente_fiscale_id),
                    int(tipo_documento_output_id) if tipo_documento_output_id is not None else None,
                    int(template_documento_id) if template_documento_id is not None else None,
                ],
            )
            results = rows_to_list(cursor)
        # La funzione restituisce una riga o solleva: zero righe e' il patto del
        # DB rotto. RuntimeError e non `assert`: il patto lo tiene il DB, non
        # questo file, e il controllo resta acceso anche con `python -O`.
        if not results:
            raise RuntimeError("fn_risolvi_template_applicabile senza riga e senza errore")
        return results[0]

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

    # Scopo: INSERT documento generato col BB `execute_dynamic_insert`,
    #        whitelist DOCUMENTO_GENERATO_CREATE_COLUMNS. Ritorna (id, uid). I
    #        trigger DB calcolano `tx_id` (Decisione 76), audit, validita e
    #        coerenza testata; il CHECK A coerenza blocca incongruenze
    #        (output/template/versione/sorgente_tipo/emittente).
    #        ⛔ Dal 2026-09-26 una chiave fuori whitelist e' `RuntimeError`: i
    #        dict li compone l'orchestratore (`document_generation_service`),
    #        mai dal payload del client.
    #        ⚠️ Lo strip del BB tocca anche gli hash (`context_hash`,
    #        `template_hash`, `pdf_hash`): digest esadecimali calcolati dal
    #        service, senza spazi ai bordi — lo strip non li cambia.
    def create_documento_generato(
        self, data: dict[str, Any]
    ) -> tuple[int, str]:
        riga = execute_dynamic_insert(
            "documenti.documenti_generati", data,
            allowed=DOCUMENTO_GENERATO_CREATE_COLUMNS,
            jsonb=_DOCUMENTO_GENERATO_JSONB,
            returning="id, uid",
        )
        return int(riga["id"]), str(riga["uid"])

    # Scopo: INSERT file persistito collegato al documento generato (BB
    #        `execute_dynamic_insert`). Ritorna l'id riga. Vincoli rilevanti
    #        DDL: `is_principale` partial-unique per documento (un solo
    #        principale per doc), unique `(documento_generato_id, file_tipo_id,
    #        ordinamento)`.
    def create_documento_generato_file(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "documenti.documenti_generati_file", data,
            allowed=DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS,
            jsonb=_DOCUMENTO_GENERATO_FILE_JSONB,
        )
        return int(riga["id"])

    # Scopo: INSERT evento timeline append-only (BB `execute_dynamic_insert`).
    #        Decisione 76: NO `tx_id` esplicito (la popola l'automation regola
    #        4) — fuori da EVENTO_DOCUMENTO_CREATE_COLUMNS, quindi passarla qui
    #        e' `RuntimeError` (fino al 2026-09-26 veniva scartata in silenzio).
    #        Il caller passa `evento_tipo` ∈ {GENERATO, SCARICATO, ...} (set
    #        chiuso dal CHECK DB). I guard DB A5/A6 bloccano UPDATE/DELETE
    #        successivi.
    def emit_evento_documento(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "documenti.documenti_generati_eventi", data,
            allowed=EVENTO_DOCUMENTO_CREATE_COLUMNS,
            jsonb=_EVENTO_DOCUMENTO_JSONB,
        )
        return int(riga["id"])

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
    # Lista documenti generati per sorgente (Tranche K). Il lookup della
    # sorgente per codice sta in `apps.config.db.sorgenti_repository`.
    # =================================================================

    # Scopo: Lista paginata documenti generati per una sorgente specifica
    #        (lista configurabile `documenti.documenti_sorgente`, 84).
    #        Filtra su (sorgente_tipo_id, sorgente_uid) e opzionalmente
    #        `sorgente_riga`. Scope emittente whitelist via `ANY(%s)`.
    #        Ordinamento dalla whitelist `DOCUMENTI_SORGENTE_ORDER_COLUMNS`;
    #        di partenza `generato_at DESC, id DESC` (timeline naturale per
    #        l'utente: piu' recenti in alto), tiebreaker `id` nello stesso
    #        verso per una paginazione deterministica.
    # ⭐ Dal 2026-09-27 pagina e totale escono da UNA query (`COUNT(*) OVER ()`
    #    via `fetch_paged_with_total`): prima erano due, con due copie dello
    #    stesso WHERE. Il ripiego del conteggio scatta solo sulla pagina oltre
    #    l'ultima, con lo stesso FROM/WHERE della pagina.
    def list_documenti_per_sorgente(
        self,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None,
        emittente_ids_scope: list[int] | None,
        limit: int,
        offset: int,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # ⚠️ Il default e' la colonna DATA e ripiega DESC anche lui: una
        #    lista che si apre senza ordinamento deve mostrare l'ultimo
        #    documento emesso, come faceva la query scritta a mano.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DOCUMENTI_SORGENTE_ORDER_COLUMNS,
            default="d.generato_at", default_desc=True, tiebreak="d.id",
            colonne_desc=DOCUMENTI_SORGENTE_SORT_COLONNE_DATA,
        )

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
        # Un punto solo: la stessa condizione serve pagina e ripiego del conto.
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_DOCUMENTI_SORGENTE, alias="d",
        )
        from_where = (
            "FROM documenti.documenti_generati d "
            f"WHERE {' AND '.join(conditions)}"
        )

        return fetch_paged_with_total(
            f"""
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
                -- documenti e' l'unico percorso possibile. E' anche la colonna
                -- «Originale» della lista (campo_sorgente `has_file_principale`).
                EXISTS (
                    SELECT 1
                      FROM documenti.documenti_generati_file f
                     WHERE f.documento_generato_id = d.id
                       AND f.is_principale = true
                ) AS has_file_principale,
                COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # noqa: S608 — ORDER BY da sql_order_clause su whitelist DOCUMENTI_SORGENTE_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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
    #        e' esattamente quella con cui il documento nacque. La stampa
    #        nuova invece legge la versione che le dice la porta unica
    #        (`risolvi_template_applicabile`), e `get_versione` la lega al
    #        suo modello: tutte e due non servono qui.
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
