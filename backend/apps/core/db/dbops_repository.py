# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository generico per funzioni dbops cross-schema (lookup, utility,
#        task registry multi-dominio, audit log).
# ------------------------------------------------------------

# Accesso SQL a funzioni dello schema dbops riusabili da tutti i domini applicativi.

from typing import cast

from django.db import connection

from apps.core.db._helpers import escape_ilike, fetch_paged_with_total, jsonb_out, sql_order_clause
from apps.core.services.service_errors import ServiceError
from apps.core.types import (
    AuditLogRow,
    DominioTaskRow,
    ErrorLogRow,
    TaskRegistryImplRow,
    TaskRegistryRow,
)

# Whitelist relazioni consentite per la lookup generica.
# Include tutte le tabelle config con struttura id/codice/descrizione.
# La funzione DB fn_get_lookup_codici valida ulteriormente la struttura delle colonne.
_REL_CONSENTITE: frozenset[str] = frozenset(
    {
        # --- config ---
        "config.ambiti",
        "config.aree_funzionali",
        "config.aspetti_beni",
        "config.assets_ownership",
        "config.canali_pratiche",
        "config.categoria_accisa",
        "config.causali_trasporto",
        "config.classi_utenze",
        "config.conti_contabili",
        "config.email_account",
        "config.esiti_flussi_pratiche",
        "config.forme_giuridiche",
        "config.iva",
        "config.tipi_titolo_iva",
        "config.iva_assoggettamenti",
        "config.iva_natura",
        "config.lingue",
        "config.listini_tipologie",
        "config.modalita_addebito_trasporto",
        "config.modalita_pagamento",
        # Modo di approvvigionamento dell'articolo (brief-db-modifiche-certe-
        # ciclo-vendita-e-articolo, Blocco B). ⭐ Una riga qui e non un endpoint:
        # e' un vocabolario codice/descrizione come `config.nature_vendita`, il
        # suo modello dichiarato, e il drawer articolo lo monta con
        # `<LookupSelect rel="config.modi_approvvigionamento">`.
        "config.modi_approvvigionamento",
        "config.nature_doc_fiscale",
        "config.nature_vendita",
        "config.note_stili",
        "config.priorita_pratiche",
        "config.profili_accesso",
        "config.qualifiche",
        # I registri che `script.vw_giornale_entita` cuce (brief-db-registri-
        # giornale-catalogo, 2026-09-19): la tendina «Registro» del giornale
        # trasversale li legge da qui, e il filtro `registro` del backend li
        # valida contro la stessa tabella. ⚠️ Senza `attivo` (D3 del brief) e
        # con `etichetta_key`: e' una specializzata, vedi `_LOOKUP_SPECIALIZZATE`.
        "config.registri_giornale",
        "config.sistema_codici",
        "config.sorgenti",
        # ⛔ NON `config.stati` (le nazioni): senza `codice`/`codice_interno`,
        #    `fn_get_lookup_codici` la rifiuta con E_LOOKUP_STRUTTURA_TABELLA_INVALIDA
        #    — era qui dichiarata ammessa ed era un 500 a ogni chiamata (trovato
        #    dal presidio `test_config_panel_registro_db` il 2026-09-21). Ha il
        #    lookup dedicato `GET /anagrafiche/stati/lookup/` e `StatiDrawer`.
        "config.stati_assets",
        "config.stati_cliente",
        "config.stati_fornitore",
        "config.stati_doc_contratti",
        "config.stati_doc_ddt",
        "config.stati_doc_fiscale",
        "config.stati_doc_offerte",
        "config.stati_doc_ordini",
        "config.stati_doc_preventivi",
        "config.stati_doc_reso",
        "config.stati_flussi_pratiche",
        "config.stati_pdp",
        "config.stati_pratiche",
        "config.stati_sdi",
        "config.termini_pagamento",
        "config.tipi_allegato",
        "config.tipi_attivita",
        "config.tipi_contatti",
        "config.tipi_doc_fiscale",
        "config.tipi_documenti",
        "config.tipi_evento_assets",
        "config.tipi_indirizzi",
        "config.tipi_nota",
        "config.tipi_reso",
        "config.tipi_ruoli",
        # ⛔ NON `config.titoli_cortesia`: solo `descrizione` + `descrizione_breve`,
        #    senza `codice` ne' `attivo` — il lookup la rifiuta (stesso 500 di
        #    `config.stati`, stesso presidio, 2026-09-21). Nessun consumatore
        #    nel BE ne' nel FE: che cosa farne e' una domanda al DB (piano
        #    anagrafiche-fuori-dal-pannello-config §7).
        "config.tipi_soggetto_dettaglio",
        "config.tipi_ubicazione",
        "config.tipi_utenze",
        "config.unita_organizzative",
        "config.utilities",
        "config.valute",
        # --- anagrafiche ---
        "anagrafiche.categorie_clienti",
        # --- catalogo ---
        "catalogo.uom_tipi",
        "catalogo.unita_misura",
        # --- documenti ---
        "documenti.render_engine_documento",
        "documenti.tipi_asset_documento",
        "documenti.tipi_documento_output",
        "documenti.tipi_file_documento",
        # --- magazzino ---
        "magazzino.causali",
        "magazzino.magazzini",
        "magazzino.ubicazioni",
        # --- pagamenti ---
        "pagamenti.centri_riscossione",
        "pagamenti.enti_incasso",
        "pagamenti.vendite_contabili_righe_stati",
        "pagamenti.vendite_contabili_stati",
        # --- pratiche ---
        "pratiche.handler_flussi",
        "pratiche.template_flussi",
        "pratiche.tipi_prestazione",
        # --- ui (personalizzazioni liste) ---
        "ui.lista_definizione",
        # --- vendite ---
        "vendite.area_geografica_fatturazione",
        # Famiglie di documento numerate su un registro. Serve al form del
        # CRUD registri (2026-09-01). ⭐ WHITELIST, non un endpoint dedicato:
        # e' una tabella codice/descrizione e il lookup generico la legge gia'
        # — verificato sul database vivo, dbops.fn_get_lookup_codici deriva il
        # `codice` da `codice_interno`, che qui e' l'unica delle due colonne
        # a esistere (`feedback_lookup_whitelist_first`).
        # ⚠️ Il valore da spedire e' `codice_interno`: e' quello che la FK
        #    `fk_registri_fatturazione_famiglia` referenzia.
        "vendite.famiglie_documento",

        "vendite.articoli_gruppi",
        "vendite.articoli_spesa",
        "vendite.articoli_tipologie",
        "vendite.listini",
        "vendite.stati_commessa",
        "vendite.tipi_fondi_fattura",
    }
)


# Le colonne del payload del lookup generico che possono fare da VALORE di una
# `<LookupSelect>` (`valueField`), cioe' le colonne che una FK puo' referenziare
# e che `fn_get_lookup_codici` restituisce per ogni riga. `descrizione`,
# `attivo` e `codice_stabile` viaggiano anch'esse ma non sono chiavi di
# nessuna FK. Lo legge il metadata del pannello config per decidere se una FK
# e' montabile come lookup (`references_lookup`).
LOOKUP_COLONNE_VALORE: frozenset[str] = frozenset({"id", "codice", "codice_interno"})


# Cap massimo righe sorgente per la CTE lookup. Il dataset atteso è molto più piccolo
# (tabelle config con poche decine/centinaia di record); il cap è una guardia di sicurezza.
LOOKUP_MAX_SOURCE_ROWS = 10_000


# Lookup specializzati: relazioni che estendono il contratto generico
# (id/codice/codice_interno/descrizione/attivo/codice_stabile) con UNA colonna
# in piu' per il frontend, senza endpoint dedicati. Estratto alla 2ª occorrenza
# (regola del 2: unita_misura + tipi_prestazione) in un unico handler
# parametrico — le prossime relazioni aggiungono una riga qui, non 70 di SQL.
#   extra_col          → nome della colonna aggiuntiva nel payload
#   extra_expr         → (opzionale) espressione SQL sorgente quando il nome
#                        API differisce dalla colonna fisica (layering: il
#                        contratto parla la lingua del consumer, la verita'
#                        memorizzata resta una sola); default `t.<extra_col>`
#   has_codice_interno → la tabella ha codice_interno (ricerca + codice_stabile)
#   has_obsoleto       → la tabella ha obsoleto_dal (filtro includi_obsoleti,
#                        stessa semantica della fn generica: esclude
#                        obsoleto_dal <= CURRENT_DATE quando false)
#   has_attivo         → (opzionale, default True) la tabella ha `attivo`.
#                        A False il payload porta `attivo = NULL` e
#                        `attivo_only` non filtra — la stessa cosa che fa
#                        `dbops.fn_get_lookup_codici` su una tabella senza la
#                        colonna (`NULL::boolean AS attivo`). ⛔ Fino al
#                        2026-09-19 l'handler scriveva `t.attivo` fisso: la
#                        prima specializzata senza il flag —
#                        `config.registri_giornale`, un vocabolario che nessuno
#                        «assegna» e che si ritira con `obsoleto_dal` — sarebbe
#                        stata un 500 alla prima chiamata, con la rel dichiarata
#                        ammessa (`feedback_contratto_dichiarato_provalo_intero`).
# ⛔ Le tabelle del PANNELLO CONFIG sono ESATTAMENTE `_REL_CONSENTITE`: il
#    pannello lista le righe col lookup generico, quindi una tabella che il
#    lookup non sa servire non la sa servire nemmeno il pannello. Fino al
#    2026-09-21 qui c'era un superset `CONFIG_TABLES = _REL_CONSENTITE | {lotti}`,
#    nato per `magazzino.lotti` (senza `descrizione`) con la promessa «il pannello
#    legge information_schema e non ne ha bisogno» — vera per il drawer, falsa
#    per la LISTA: a video la tabella era vuota con un 400 ingoiato. Due nomi
#    per lo stesso insieme sono la forma in cui divergono: ne resta uno.
#    Le anagrafiche di magazzino (magazzini, ubicazioni, lotti) hanno endpoint e
#    drawer propri: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.

_LOOKUP_SPECIALIZZATE: dict[str, dict] = {
    "catalogo.unita_misura": {
        # tipo_uom_id: usato dal FE per filtrare conversioni same-type.
        "extra_col": "tipo_uom_id",
        "has_codice_interno": False,
        "has_obsoleto": False,
    },
    "config.esiti_flussi_pratiche": {
        # selezionabile_operatore: derivato da is_verdetto (true = verdetto
        # dell'operatore; false = esito di ramo calcolato dal dominio). Il FE
        # filtra il Select esiti; il guard BE rifiuta i non-verdetto sul
        # percorso operatore (pratiche_service).
        "extra_col": "selezionabile_operatore",
        "extra_expr": "t.is_verdetto",
        "has_codice_interno": True,
        "has_obsoleto": False,
    },
    "config.tipi_titolo_iva": {
        # ha_plafond: distingue le due specie della famiglia dei titoli (D10) —
        # solo l'INTENTO ha un contatore che si consuma. Il FE la usa per
        # mostrare il campo plafond SOLO dove un tetto esiste: proporlo altrove
        # produrrebbe un numero che nessuno consuma, cioe' un campo che promette
        # una cosa che non succede.
        # ⛔ Senza questa riga il lookup generico proietta solo
        #   id/codice/descrizione e il drawer non saprebbe MAI che il tipo ha un
        #   tetto: il campo non comparirebbe mai, in silenzio.
        "extra_col": "ha_plafond",
        "has_codice_interno": True,
        "has_obsoleto": False,
    },
    "pratiche.tipi_prestazione": {
        # categoria: usata dalla home pratiche per raggruppare le tile.
        "extra_col": "categoria",
        "has_codice_interno": True,
        "has_obsoleto": True,
    },
    "config.registri_giornale": {
        # etichetta_key: l'INDIRIZZO i18n che il DB dichiara riga per riga
        # (`config.registri_giornale.<codice_interno minuscolo>`, pinnato dal
        # pgTAP del catalogo, test 8). Il frontend lo rende con `labelOrCode`
        # — la tendina «Registro» del giornale e la sua colonna. ⭐ Qui e non
        # ricostruito nel FE dalla convenzione (brief §8.4): la chiave la
        # dichiara il database, come per `tipi_entita` ed `eventi_dominio`.
        # ⚠️ Niente `attivo` (D3): il ritiro di un registro ha un asse solo,
        #    `obsoleto_dal`, e le righe vecchie del diario restano leggibili.
        "extra_col": "etichetta_key",
        "has_codice_interno": True,
        "has_obsoleto": True,
        "has_attivo": False,
    },
}


# Ordinamenti ammessi sulla consultazione di `dbops.error_log` (pezzo E del
# piano BE/FE dell'osservabilita', 2026-09-19).
# ⛔ Le chiavi sono i `campo_sorgente` FISICI del catalogo `dbops.error_log`
#    (`ui.lista_colonna`): il frontend manda quelli (api.md §whitelist).
# ⚠️ `codice` ordina sul catalogo (JOIN): e' la colonna che si vede.
# ⛔ `messaggio`, `context`, `causa`, `soluzione` NON sono ordinabili: mettere
#    in ordine alfabetico delle frasi non risponde a nessuna domanda, e le
#    loro righe a catalogo sono `ordinabile = f` (test_liste_configurabili_seed).
ERROR_LOG_SORT_COLUMNS: dict[str, str] = {
    "occurred_at": "e.occurred_at",
    "area": "e.area",
    "function_name": "e.function_name",
    "codice": "m.codice",
    "classe": "ce.classe",
    "tx_id": "e.tx_id",
}
# Le colonne DATA della whitelist: ripiego DESC senza `order_dir` (regola di
# Tid del 2026-09-02, letta dal test 10 del presidio delle liste).
_ERROR_LOG_COLONNE_DESC: frozenset[str] = frozenset({"occurred_at"})


# Scopo: il prefisso di `function_name` reso sicuro per un `LIKE 'x%'` che
#        usi l'indice `text_pattern_ops`: `\`, `%` e `_` escapati.
# ⛔ `_` E' UN JOLLY DI `LIKE`, e i nomi di funzione ne sono pieni (P-3 del
#    brief osservabilita', verificato con EXPLAIN il 19-09): senza escape
#    `LIKE 'fn_get_lotto%'` ha come prefisso fisso solo `fn` e il planner torna
#    a scandire la tabella — e `fn_get` combacerebbe con `fnXget`, che e' anche
#    la risposta sbagliata. Con l'escape il prefisso e' letterale.
# ⭐ L'escape e' quello del BB `escape_ilike` (stessi tre metacaratteri, stesso
#    ordine — il backslash per primo): qui si aggiunge solo il `%` di coda.
#    Riscriverlo era la copia numero quattro dello stesso `replace` a catena.
def _prefisso_like(valore: str) -> str:
    return escape_ilike(valore) + "%"


class DbopsRepository:
    """Repository per funzioni generiche dbops (lookup codici, utility)."""

    # Scopo: Handler unico dei lookup specializzati (_LOOKUP_SPECIALIZZATE):
    # contratto generico + una colonna extra, con filtri attivo/obsoleto e
    # ricerca ILIKE coerenti con la fn generica. Gli identificatori interpolati
    # nella SQL (tabella, colonna extra, order) vengono SOLO dalla config
    # statica e dalle whitelist di ordinamento gia' validate a monte.
    def _list_lookup_specializzato(
        self,
        *,
        rel: str,
        search: str | None,
        order_col: str,
        order_dir: str,
        attivo_only: bool,
        includi_obsoleti: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        spec = _LOOKUP_SPECIALIZZATE[rel]
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        order_map = {
            "codice": "t.codice",
            "descrizione": "t.descrizione",
        }
        order_column = order_map[order_col]

        codice_interno_sql = (
            "t.codice_interno" if spec["has_codice_interno"] else "NULL::text"
        )
        # Senza la colonna `attivo` il payload la porta NULL e `attivo_only`
        # non ha niente su cui filtrare: e' il contratto della fn generica.
        has_attivo = spec.get("has_attivo", True)
        attivo_sql = "t.attivo" if has_attivo else "NULL::boolean"
        attivo_pred = (
            "(%(attivo_only)s IS FALSE OR t.attivo = true)" if has_attivo else "TRUE"
        )
        obsoleto_pred = (
            "AND (%(includi_obsoleti)s IS TRUE"
            " OR t.obsoleto_dal IS NULL OR t.obsoleto_dal > CURRENT_DATE)"
            if spec["has_obsoleto"]
            else ""
        )
        search_codice_interno = (
            "OR t.codice_interno ILIKE %(search)s" if spec["has_codice_interno"] else ""
        )
        extra_expr = spec.get("extra_expr", f"t.{spec['extra_col']}")

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    t.id,
                    t.codice,
                    {codice_interno_sql} AS codice_interno,
                    t.descrizione,
                    {attivo_sql} AS attivo,
                    {extra_expr} AS {spec["extra_col"]},
                    COUNT(*) OVER () AS total_count
                  FROM {rel} t
                 WHERE {attivo_pred}
                   {obsoleto_pred}
                   AND (
                       %(search)s::text IS NULL
                       OR t.codice ILIKE %(search)s
                       {search_codice_interno}
                       OR t.descrizione ILIKE %(search)s
                   )
                 ORDER BY {order_column} {order_dir}, t.id {order_dir}
                 LIMIT %(limit)s OFFSET %(offset)s
                """,
                {
                    "attivo_only": attivo_only,
                    "includi_obsoleti": includi_obsoleti,
                    "search": search_pattern,
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][6]
        results = [
            {
                "id": row[0],
                "codice": row[1],
                "codice_interno": row[2],
                "descrizione": row[3],
                "attivo": row[4],
                "codice_stabile": row[2] or row[1],  # COALESCE(codice_interno, codice)
                spec["extra_col"]: row[5],
            }
            for row in rows
        ]
        return results, total_count

    # Scopo: Restituisce la lista dei valori lookup per una relazione config con filtro ILIKE
    # e paginazione. Chiama dbops.fn_get_lookup_codici con limit ampio per ottenere tutti i
    # record attivi e applica il filtro testo e la paginazione esternamente via SQL wrapper.
    # Obiettivo: evitare di modificare la funzione DB generica mantenendo la logica di ricerca
    # lato Python/SQL.
    # Perimetro: sola lettura; solleva ServiceError se la relazione non è in whitelist.
    # Risultato: tuple (list[dict], total_count) con campi id, codice, descrizione.
    def list_lookup_codici(
        self,
        *,
        rel: str,
        search: str | None = None,
        order_col: str = "descrizione",
        order_dir: str = "ASC",
        attivo_only: bool = True,
        includi_obsoleti: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        if rel not in _REL_CONSENTITE:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Relazione non consentita.",
                detail=f"rel '{rel}' non è nella whitelist delle lookup consentite.",
            )

        if rel in _LOOKUP_SPECIALIZZATE:
            return self._list_lookup_specializzato(
                rel=rel,
                search=search,
                order_col=order_col,
                order_dir=order_dir,
                attivo_only=attivo_only,
                includi_obsoleti=includi_obsoleti,
                limit=limit,
                offset=offset,
            )

        # Normalizzazione: search None o stringa vuota => nessun filtro.
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None

        with connection.cursor() as cursor:
            # Wrappa fn_get_lookup_codici in una CTE con filtro ILIKE e paginazione esterna.
            # Il limit interno (LOOKUP_MAX_SOURCE_ROWS) è una guardia; il filtro è applicato sul risultato.
            # order_col e order_dir sono gia' validati dal service contro whitelist
            # (frozenset {"codice","descrizione"} e {"asc","desc"}).
            # Non possono essere parametri SQL (%s), servono nel testo della query.
            sql = """
                WITH base AS (
                    SELECT id, codice, codice_interno, descrizione, attivo
                      FROM dbops.fn_get_lookup_codici(
                               %s::regclass,
                               %s,
                               %s,
                               %s,
                               %s,
                               0,
                               %s
                           )
                )
                SELECT
                    id,
                    codice,
                    codice_interno,
                    descrizione,
                    attivo,
                    COUNT(*) OVER () AS total_count
                  FROM base
                 WHERE (
                     %s::text IS NULL
                     OR codice ILIKE %s
                     OR codice_interno ILIKE %s
                     OR descrizione ILIKE %s
                 )
                 ORDER BY {} {}, id
                 LIMIT %s OFFSET %s
                """.format(order_col, order_dir)
            cursor.execute(
                sql,
                [
                    rel,
                    order_col,
                    order_dir,
                    attivo_only,
                    LOOKUP_MAX_SOURCE_ROWS,
                    includi_obsoleti,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    limit,
                    offset,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][5]
        results = [
            {
                "id": row[0],
                "codice": row[1],
                "codice_interno": row[2],
                "descrizione": row[3],
                "attivo": row[4],
                "codice_stabile": row[2] or row[1],  # COALESCE(codice_interno, codice)
            }
            for row in rows
        ]
        return results, total_count

    # Scopo: Verifica esistenza di un record in una tabella config whitelisted per ID.
    #        Se la tabella ha la colonna `attivo` il record deve anche essere attivo;
    #        per le anagrafiche fisse senza `attivo` (es. config.utilities) vale la sola
    #        esistenza (quelle tabelle non hanno il concetto di attivazione).
    def check_lookup_id_exists(self, *, rel: str, record_id: int) -> bool:
        if rel not in _REL_CONSENTITE:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Relazione non consentita.",
                detail=f"rel '{rel}' non e` nella whitelist delle lookup consentite.",
            )
        schema, _, table = rel.partition(".")
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s AND column_name = 'attivo'
                )
                """,
                [schema, table],
            )
            has_attivo = bool(cursor.fetchone()[0])
            predicate = " AND attivo = true" if has_attivo else ""
            cursor.execute(
                f"SELECT EXISTS(SELECT 1 FROM {rel} WHERE id = %s{predicate})",
                [record_id],
            )
            row = cursor.fetchone()
            return bool(row and row[0])

    # ------------------------------------------------------------------
    # Task Registry multi-dominio (dbops.domini_task, pipeline_task_registry,
    # pipeline_task_registry_impl)
    # ------------------------------------------------------------------

    # Scopo: Restituisce la lista dei domini task attivi con filtro opzionale.
    # Perimetro: sola lettura su dbops.domini_task.
    def list_domini_task(
        self,
        *,
        attivo_only: bool = True,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DominioTaskRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione, attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.domini_task
                 WHERE (%s IS FALSE OR attivo = true)
                   AND (%s::text IS NULL
                        OR codice ILIKE %s
                        OR descrizione ILIKE %s)
                 ORDER BY codice, id
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, search_pattern, search_pattern, search_pattern,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][4]
        results: list[DominioTaskRow] = [
            DominioTaskRow(
                id=r[0], codice=r[1], descrizione=r[2], attivo=r[3],
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Restituisce i task registrati per un dominio, con codice dominio in join.
    # Perimetro: sola lettura su pipeline_task_registry + domini_task.
    def list_task_registry(
        self,
        *,
        dominio_codice: str | None = None,
        attivo_only: bool = True,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.dominio_id, d.codice AS dominio_codice,
                       r.task_code, r.descrizione, r.attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.pipeline_task_registry r
                  JOIN dbops.domini_task d ON d.id = r.dominio_id
                 WHERE (%s IS FALSE OR r.attivo = true)
                   AND (%s::text IS NULL OR d.codice = %s)
                   AND (%s::text IS NULL
                        OR r.task_code ILIKE %s
                        OR r.descrizione ILIKE %s)
                 ORDER BY d.codice, r.task_code, r.id
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, dominio_codice, dominio_codice,
                 search_pattern, search_pattern, search_pattern,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][6]
        results: list[TaskRegistryRow] = [
            TaskRegistryRow(
                id=r[0], dominio_id=r[1], dominio_codice=r[2],
                task_code=r[3], descrizione=r[4], attivo=r[5],
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Restituisce le implementazioni di un task con dettaglio handler.
    # Perimetro: sola lettura su pipeline_task_registry_impl + pipeline_task_registry.
    def list_task_implementations(
        self,
        *,
        task_code: str | None = None,
        dominio_codice: str | None = None,
        attivo_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryImplRow], int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.id, i.task_registry_id, r.task_code,
                       i.implementation_key, i.handler_code,
                       i.is_default, i.attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.pipeline_task_registry_impl i
                  JOIN dbops.pipeline_task_registry r ON r.id = i.task_registry_id
                  JOIN dbops.domini_task d ON d.id = r.dominio_id
                 WHERE (%s IS FALSE OR i.attivo = true)
                   AND (%s::text IS NULL OR r.task_code = %s)
                   AND (%s::text IS NULL OR d.codice = %s)
                 ORDER BY r.task_code, i.implementation_key, i.id
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, task_code, task_code,
                 dominio_codice, dominio_codice,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][7]
        results: list[TaskRegistryImplRow] = [
            TaskRegistryImplRow(
                id=r[0], task_registry_id=r[1], task_code=r[2],
                implementation_key=r[3], handler_code=r[4],
                is_default=r[5], attivo=r[6],
            )
            for r in rows
        ]
        return results, total_count

    # ------------------------------------------------------------------
    # Audit Log (dbops.audit_log)
    # ------------------------------------------------------------------

    # Scopo: Restituisce le righe audit log con filtri opzionali su status, function_name e
    # intervallo temporale. Ordinamento cronologico decrescente.
    # Perimetro: sola lettura; paginazione esterna.
    def list_audit_logs(
        self,
        *,
        status: str | None = None,
        function_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLogRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, function_name, executed_by, executed_at::text,
                       status, message, duration_ms, tx_id::text,
                       exec_mode, rule_type, dry_run, rows_affected,
                       params, result,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.audit_log
                 WHERE (%s::text IS NULL OR status = %s)
                   AND (%s::text IS NULL OR function_name ILIKE %s)
                   AND (%s::text IS NULL OR executed_at >= %s::timestamptz)
                   AND (%s::text IS NULL OR executed_at <= %s::timestamptz + interval '1 day')
                   AND (%s::text IS NULL
                        OR function_name ILIKE %s
                        OR message ILIKE %s)
                 ORDER BY executed_at DESC, id DESC
                 LIMIT %s OFFSET %s
                """,
                [
                    status, status,
                    function_name, f"%{function_name}%" if function_name else None,
                    date_from, date_from,
                    date_to, date_to,
                    search_pattern, search_pattern, search_pattern,
                    limit, offset,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][14]
        results: list[AuditLogRow] = [
            AuditLogRow(
                id=r[0], function_name=r[1], executed_by=r[2],
                executed_at=r[3], status=r[4], message=r[5],
                duration_ms=r[6], tx_id=r[7], exec_mode=r[8],
                rule_type=r[9], dry_run=r[10], rows_affected=r[11],
                # ⛔ `jsonb_out` e non una decodifica a mano (2026-09-19): la
                #    forma precedente era il BB riscritto, con una parentesi in
                #    piu' che il presidio `test_coercizione_jsonb_dal_bb` non vedeva.
                params=jsonb_out(r[12]),
                result=jsonb_out(r[13]),
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: la CONSULTAZIONE di `dbops.error_log` per i tecnici — «quale
    #        funzione ha sollevato quale codice, quando, in quale transazione»
    #        (pezzo E del piano BE/FE dell'osservabilita', 2026-09-19). Righe
    #        paginate col totale in UNA valutazione + il catalogo per JOIN.
    #
    # ⭐ Sta ACCANTO a `list_audit_logs` e nella sua forma: due diari tecnici
    #    dello stesso schema, letti dalla stessa porta (`AdminAPIView`).
    # ⭐ `codice`, `classe`, `messaggio`, `causa`, `soluzione` arrivano dal
    #    catalogo (`config.messaggi_errore` → `config.codici_errore`), non
    #    ricostruiti: la frase e la soluzione hanno UNA sede, e `classe` e' il
    #    dato che distingue un GUASTO da un RIFIUTO LEGITTIMO — la domanda che
    #    questo registro, letto da solo, non sapeva fare.
    # ⚠️ `context` si espone COM'E': qui il lettore e' il tecnico e quegli sono
    #    i suoi appunti («non va ripulito o riscritto per renderlo
    #    presentabile», vincolo del Passo A). Nessun tentativo di renderlo
    #    leggibile — e' il loop che il vincolo esiste per spezzare.
    #
    # Filtri, tutti in whitelist e ognuno con l'indice da cui partire (P-3,
    # `20260919-06`, manuale `dbops/manual/error_log.md` §indici):
    #   `area`          esatto            → `ix_error_log_area_occurred_at`
    #   `function_name` PREFISSO, `LIKE`  → `ix_error_log_function_name_occurred_at`
    #                   (`text_pattern_ops`: serve `=` e `LIKE 'x%'`, MAI `ILIKE`;
    #                   i nomi sono minuscoli per convenzione; `_` escapato)
    #   `codice`        esatto, risolto PRIMA a `messaggio_errore_id` (tutte le
    #                   lingue del codice) → `ix_dbops_error_log_messaggio_errore_id`
    #   `tx_id`         esatto            → `ix_error_log_tx_id` (il PONTE dal
    #                   giornale agli appunti tecnici della stessa transazione)
    #   `data_da`/`data_a` su `occurred_at` (`[da, a + 1 giorno)`) → `ix_error_log_occurred_at`
    # ⚠️ I valori viaggiano nei `params`; l'SQL e' costante e l'ordinamento
    #    passa da `sql_order_clause` sulla whitelist.
    def list_error_logs(
        self,
        *,
        area: str | None = None,
        function_name: str | None = None,
        codice: str | None = None,
        tx_id: str | None = None,
        data_da: str | None = None,
        data_a: str | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[ErrorLogRow], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ERROR_LOG_SORT_COLUMNS,
            colonne_desc=_ERROR_LOG_COLONNE_DESC,
            default="e.occurred_at",
            default_desc=True,
            tiebreak="e.id",
        )
        prefisso = _prefisso_like(function_name.strip()) if function_name and function_name.strip() else None
        righe, totale = fetch_paged_with_total(
            f"""
            SELECT e.id, e.occurred_at, e.area, e.function_name,
                   m.codice, ce.classe, m.messaggio, m.causa, m.soluzione,
                   e.tx_id::text AS tx_id, e.context,
                   COUNT(*) OVER () AS total_count
              FROM dbops.error_log e
              JOIN config.messaggi_errore m ON m.id = e.messaggio_errore_id
              -- ⚠️ LEFT: un messaggio il cui codice fosse uscito dal catalogo dei
              --    codici non deve far sparire la riga dal diario.
              LEFT JOIN config.codici_errore ce ON ce.codice = m.codice
             WHERE (%s::text IS NULL OR e.area = %s)
               AND (%s::text IS NULL OR e.function_name LIKE %s)
               AND (%s::text IS NULL OR e.messaggio_errore_id IN (
                        SELECT mm.id FROM config.messaggi_errore mm WHERE mm.codice = %s))
               AND (%s::uuid IS NULL OR e.tx_id = %s::uuid)
               AND (%s::date IS NULL OR e.occurred_at >= %s::date)
               AND (%s::date IS NULL OR e.occurred_at < %s::date + interval '1 day')
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
            """,
            [
                area, area,
                prefisso, prefisso,
                codice, codice,
                tx_id, tx_id,
                data_da, data_da,
                data_a, data_a,
                limit, offset,
            ],
            offset=offset,
        )
        risultato: list[ErrorLogRow] = [
            cast(ErrorLogRow, {
                **r,
                # `occurred_at` e' NOT NULL a DB: niente ramo per il None.
                "occurred_at": r["occurred_at"].isoformat(),
                # ⛔ `jsonb_out`, non una decodifica a mano: il backend Django per
                #    psycopg 3 consegna i jsonb come `str` fuori dall'ORM, e il
                #    BB li decodifica PRESERVANDO il valore com'e' (un decode
                #    error su una colonna `jsonb` e' un bug da far esplodere).
                #    La colonna e' NOT NULL DEFAULT '{}', quindi qui arriva
                #    sempre un oggetto — gli appunti del tecnico, intatti.
                "context": jsonb_out(r["context"]),
            })
            for r in righe
        ]
        return risultato, totale
