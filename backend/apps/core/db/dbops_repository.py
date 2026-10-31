# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository generico per funzioni dbops cross-schema (lookup, utility,
#        task registry multi-dominio, audit log).
# ------------------------------------------------------------

# Accesso SQL a funzioni dello schema dbops riusabili da tutti i domini applicativi.

from datetime import date
from typing import cast

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    colonne_identita,
    escape_ilike,
    fetch_paged_with_total,
    pattern_contiene,
    predicato_giorno_operativo,
    sql_order_clause,
)
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository
from apps.core.services.service_errors import ServiceError
from apps.core.types import (
    AuditLogRow,
    DominioTaskRow,
    ErrorLogRow,
    TaskRegistryImplRow,
    TaskRegistryRow,
)

# ⛔ La whitelist del lookup generico NON e' piu' qui: dal 2026-09-25 e' la
#    tabella `config.tabelle_gestibili` (colonna `lookup`), letta da
#    `TabelleGestibiliRepository` (brief-db-pannello-config-verbo-generico). Fino
#    a quel giorno era la costante `REL_CONSENTITE`, con una terza copia nel
#    frontend; il verbo del pannello legge la stessa riga del DB, e una
#    costante accanto sarebbe tornata a essere una seconda sede.
#    `dbops.fn_get_lookup_codici` valida poi la struttura delle colonne.


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

# Scopo: le colonne per cui si ordina una lookup di codici, generica o
#        specializzata: SEDE UNICA (2026-09-26, regola del 2). Le legge anche
#        `lookup_service` per validare `order_by` col codice del dominio —
#        prima ne aveva una sua copia, `{codice, descrizione}` scritto a mano
#        due volte, che oggi coincideva e domani no.
LOOKUP_ORDER_COLONNE: tuple[str, ...] = ("codice", "descrizione")


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
#                        obsoleto_dal <= fn_data_operativa() quando false)
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
# ⛔ Le tabelle del PANNELLO CONFIG sono un SOTTOINSIEME di quelle del lookup
#    (`config.tabelle_gestibili`: `pannello` implica `lookup`, fuori le quattro
#    con RLS, D-P2): il pannello lista le righe col lookup generico, quindi una
#    tabella che il lookup non sa servire non la sa servire nemmeno il pannello. Fino al
#    2026-09-21 qui c'era un superset `CONFIG_TABLES = REL_CONSENTITE | {lotti}`,
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
    "config.esposizioni_componente": {
        # etichetta_key: come per i registri, l'indirizzo i18n che il DB
        # dichiara per ciascuno dei tre modi di esporre in fattura un
        # componente di kit (NASCOSTO / DESCRITTIVO / VALORIZZATO). Il frontend
        # lo rende con `useLookupEtichettato`: la scelta nella distinta e il
        # modo per esteso nei componenti (brief-db-esposizione-componenti-kit-
        # in-fattura, R-BE-6).
        # ⚠️ Niente `attivo` e niente `obsoleto_dal` (§9.2): i tre valori sono
        #    la semantica di `vw_fattura_righe_esposte`, non una configurazione.
        "extra_col": "etichetta_key",
        "has_codice_interno": True,
        "has_obsoleto": False,
        "has_attivo": False,
    },
    # I tre vocabolari di una versione di template (formato del sorgente,
    # formato e orientamento della pagina): le tendine del drawer della
    # versione li rendono con `useLookupEtichettato` sul `codice_interno`, la
    # chiave che la FK di `template_documenti_versioni` valida
    # (brief-db-vocabolari-versione-template, R-BE-V1).
    # ⚠️ Niente `attivo` e niente `obsoleto_dal` (§5.2): sono cio' che il
    #    motore di stampa sa onorare, non una configurazione.
    "documenti.formati_template": {
        "extra_col": "etichetta_key",
        "has_codice_interno": True,
        "has_obsoleto": False,
        "has_attivo": False,
    },
    "documenti.formati_pagina": {
        "extra_col": "etichetta_key",
        "has_codice_interno": True,
        "has_obsoleto": False,
        "has_attivo": False,
    },
    "documenti.orientamenti_pagina": {
        "extra_col": "etichetta_key",
        "has_codice_interno": True,
        "has_obsoleto": False,
        "has_attivo": False,
    },
    # emittente_fiscale_id: il magazzino di un documento (bolla, reso) e'
    # dell'emittente del documento (M-6; guard DB `script.fn_magazzino_dell_emittente`).
    # Il FE filtra la tendina sull'emittente del documento (`filterField` di
    # LookupSelect), invece di far scegliere un magazzino che il DB rifiuterebbe
    # al salvataggio con E_DDT_/E_RESO_MAGAZZINO_INCOERENTE (piano-be-fe-
    # magazzino-lotto-3, A2, decisione di Tid del 2026-10-12).
    "magazzino.magazzini": {
        "extra_col": "emittente_fiscale_id",
        "has_codice_interno": False,
        "has_obsoleto": False,
    },
    # causale_magazzino: il codice_interno della causale di magazzino che la
    # causale di trasporto muove (D-L3-g), NULL se non muove merce. Il FE ne
    # ricava se la bolla vuole il magazzino di ARRIVO (`TRASF_OUT`, la stessa
    # regola di `vendite.trgfn_ddt_guard_magazzino` e `script.fn_check_ddt_merce`).
    "config.causali_trasporto": {
        "extra_col": "causale_magazzino",
        "has_codice_interno": False,
        "has_obsoleto": False,
    },
    # mesi: la durata del periodo. Il FE ordina la tendina della periodicita'
    # (riga a canone, riga e kit di listino) sul ritmo e non sull'alfabeto, e
    # il valore della tendina e' il `codice`, quello della FK
    # (brief-db-contratto-righe-periodiche-in-commessa §7.5, D-6).
    # ⚠️ Niente `codice_interno`, `attivo` e `obsoleto_dal`: il vocabolario e'
    #    del modello, non una configurazione (fuori dal pannello).
    "config.periodicita": {
        "extra_col": "mesi",
        "has_codice_interno": False,
        "has_obsoleto": False,
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


# Scopo: La `rel` e' ammessa al lookup generico? La risposta e' della lista a DB
# (`config.tabelle_gestibili.lookup`); altrimenti 400, come prima. ⭐ Il nome
# che finisce negli SQL dinamici e' quello di una riga della lista (CHECK di
# forma), quindi il controllo e' anche la difesa dall'iniezione.
def _richiedi_rel_lookup(rel: str) -> None:
    voce = TabelleGestibiliRepository().voce(rel)
    if voce is None or not voce["lookup"]:
        raise ServiceError(
            code="E_CORE_VALIDATION",
            message="Relazione non consentita.",
            detail=f"rel '{rel}' non e' fra le tabelle del lookup (config.tabelle_gestibili).",
        )


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
        search_pattern = pattern_contiene(search)
        order_map = {c: f"t.{c}" for c in LOOKUP_ORDER_COLONNE}
        # ⛔ Clausola dal BB (2026-09-26), non `{order_col} {order_dir}`
        #    interpolati: la direzione si fidava della validazione a monte, e
        #    un chiamante diretto con un valore estraneo l'avrebbe scritta
        #    nell'SQL. Il BB la rifiuta, mette i NULL come valore minimo e
        #    allinea lo spareggio.
        ordinamento = sql_order_clause(
            order_col, order_dir,
            colonne=order_map, default="t.descrizione", tiebreak="t.id",
        )

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
            " OR t.obsoleto_dal IS NULL OR t.obsoleto_dal > (SELECT script.fn_data_operativa()))"
            if spec["has_obsoleto"]
            else ""
        )
        search_codice_interno = (
            "OR t.codice_interno ILIKE %(search)s" if spec["has_codice_interno"] else ""
        )
        extra_expr = spec.get("extra_expr", f"t.{spec['extra_col']}")

        # ⭐ Un frammento FROM+WHERE per la pagina e per il conteggio di
        #    ripiego: il perimetro del totale e' quello della lista.
        #    Identificatori interpolati: rel verificata su config.tabelle_gestibili
        #    (CHECK di forma) e in _LOOKUP_SPECIALIZZATE, colonne da spec
        #    costante, ORDER BY dal BB sql_order_clause; valori come parametri.
        from_where = f"""
                  FROM {rel} t
                 WHERE {attivo_pred}
                   {obsoleto_pred}
                   AND (
                       %(search)s::text IS NULL
                       OR t.codice ILIKE %(search)s
                       {search_codice_interno}
                       OR t.descrizione ILIKE %(search)s
                   )"""
        params = {
            "attivo_only": attivo_only,
            "includi_obsoleti": includi_obsoleti,
            "search": search_pattern,
            "limit": limit,
            "offset": offset,
        }
        # ⛔ Oltre l'ultima pagina la window function non vede righe e il
        #    totale era 0 (F-8 dell'analisi difetti doc API core): il BB
        #    `fetch_paged_with_total` lo ricalcola col conteggio di ripiego.
        righe, total_count = fetch_paged_with_total(
            f"""
                SELECT
                    t.id,
                    t.codice,
                    {codice_interno_sql} AS codice_interno,
                    t.descrizione,
                    {attivo_sql} AS attivo,
                    {extra_expr} AS {spec["extra_col"]},
                    COUNT(*) OVER () AS total_count
                {from_where}
                 ORDER BY {ordinamento}
                 LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
            fallback_count_sql=f"SELECT COUNT(*)::int {from_where}",
            fallback_params=params,
            offset=offset,
        )
        results = [
            {**r, "codice_stabile": r["codice_interno"] or r["codice"]}  # COALESCE(codice_interno, codice)
            for r in righe
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
        _richiedi_rel_lookup(rel)

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
        search_pattern = pattern_contiene(search)

        # Wrappa fn_get_lookup_codici in una CTE con filtro ILIKE e paginazione esterna.
        # Il limit interno (LOOKUP_MAX_SOURCE_ROWS) è una guardia; il filtro è applicato sul risultato.
        # ⛔ L'ORDER BY lo scrive il BB `sql_order_clause` (2026-09-26): prima
        #    `{order_col} {order_dir}` interpolati, fidandosi della whitelist
        #    del service, e lo spareggio `id` sempre ASC.
        ordinamento = sql_order_clause(
            order_col, order_dir,
            colonne=colonne_identita(*LOOKUP_ORDER_COLONNE),
            default="descrizione", tiebreak="id",
        )
        # ⭐ Un frammento (CTE + WHERE) per la pagina e per il conteggio di
        #    ripiego: il perimetro del totale e' quello della lista.
        base_where = """
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
                SELECT {colonne}
                  FROM base
                 WHERE (
                     %s::text IS NULL
                     OR codice ILIKE %s
                     OR codice_interno ILIKE %s
                     OR descrizione ILIKE %s
                 )"""
        params_base = [
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
        ]
        data_sql = base_where.format(
            colonne="id, codice, codice_interno, descrizione, attivo, COUNT(*) OVER () AS total_count",
        ) + f"""
                 ORDER BY {ordinamento}
                 LIMIT %s OFFSET %s"""
        # ⛔ Oltre l'ultima pagina la window function non vede righe e il
        #    totale era 0 (F-8 dell'analisi difetti doc API core): il BB
        #    `fetch_paged_with_total` lo ricalcola col conteggio di ripiego.
        righe, total_count = fetch_paged_with_total(
            data_sql,
            [*params_base, limit, offset],
            fallback_count_sql=base_where.format(colonne="COUNT(*)::int"),
            fallback_params=params_base,
            offset=offset,
        )
        results = [
            {**r, "codice_stabile": r["codice_interno"] or r["codice"]}  # COALESCE(codice_interno, codice)
            for r in righe
        ]
        return results, total_count

    # Scopo: Verifica esistenza di un record in una tabella config whitelisted per ID.
    #        Se la tabella ha la colonna `attivo` il record deve anche essere attivo;
    #        per le anagrafiche fisse senza `attivo` (es. config.utilities) vale la sola
    #        esistenza (quelle tabelle non hanno il concetto di attivazione).
    def check_lookup_id_exists(self, *, rel: str, record_id: int) -> bool:
        _richiedi_rel_lookup(rel)
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
                f"SELECT EXISTS(SELECT 1 FROM {rel} WHERE id = %s{predicate})",  # noqa: S608 — rel verificata su config.tabelle_gestibili (CHECK di forma schema.tabella), predicato letterale, valori come parametri
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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[DominioTaskRow], int]:
        search_pattern = pattern_contiene(search)
        rows, total_count = fetch_paged_with_total(
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
            offset=offset,
        )
        results: list[DominioTaskRow] = [
            DominioTaskRow(
                id=r["id"], codice=r["codice"], descrizione=r["descrizione"], attivo=r["attivo"],
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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryRow], int]:
        search_pattern = pattern_contiene(search)
        rows, total_count = fetch_paged_with_total(
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
            offset=offset,
        )
        results: list[TaskRegistryRow] = [
            TaskRegistryRow(
                id=r["id"], dominio_id=r["dominio_id"], dominio_codice=r["dominio_codice"],
                task_code=r["task_code"], descrizione=r["descrizione"], attivo=r["attivo"],
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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryImplRow], int]:
        rows, total_count = fetch_paged_with_total(
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
            offset=offset,
        )
        results: list[TaskRegistryImplRow] = [
            TaskRegistryImplRow(
                id=r["id"], task_registry_id=r["task_registry_id"], task_code=r["task_code"],
                implementation_key=r["implementation_key"], handler_code=r["handler_code"],
                is_default=r["is_default"], attivo=r["attivo"],
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
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[AuditLogRow], int]:
        search_pattern = pattern_contiene(search)
        # Giorni dell'azienda, `date_to` incluso (BB): fino al 2026-10-09 era
        # `<= %s::timestamptz + 1 day`, mezzanotte della sessione e confine
        # alto compreso.
        giorno_sql, giorno_params = predicato_giorno_operativo("executed_at", date_from, date_to)
        # Guardia e filtro leggono lo STESSO valore: con la guardia sul nome
        # grezzo, «  » passava la guardia e finiva in `ILIKE NULL` (zero righe).
        function_pattern = pattern_contiene(function_name)
        rows, total_count = fetch_paged_with_total(
            f"""
            SELECT id, function_name, executed_by, executed_at::text,
                   status, message, duration_ms, tx_id::text,
                   exec_mode, rule_type, dry_run, rows_affected,
                   params, result,
                   COUNT(*) OVER () AS total_count
              FROM dbops.audit_log
             WHERE (%s::text IS NULL OR status = %s)
               AND (%s::text IS NULL OR function_name ILIKE %s)
               AND {giorno_sql}
               AND (%s::text IS NULL
                    OR function_name ILIKE %s
                    OR message ILIKE %s)
             ORDER BY executed_at DESC, id DESC
             LIMIT %s OFFSET %s
            """,  # noqa: S608 — frammento del BB predicato_giorno_operativo (colonna validata), valori come parametri
            [
                status, status,
                function_pattern, function_pattern,
                *giorno_params,
                search_pattern, search_pattern, search_pattern,
                limit, offset,
            ],
            offset=offset,
        )
        results: list[AuditLogRow] = [
            AuditLogRow(
                id=r["id"], function_name=r["function_name"], executed_by=r["executed_by"],
                executed_at=r["executed_at"], status=r["status"], message=r["message"],
                duration_ms=r["duration_ms"], tx_id=r["tx_id"], exec_mode=r["exec_mode"],
                rule_type=r["rule_type"], dry_run=r["dry_run"], rows_affected=r["rows_affected"],
                # `params` e `result` decodificati dal lettore comune.
                params=r["params"],
                result=r["result"],
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
    #   `data_da`/`data_a` su `occurred_at`, giorni dell'AZIENDA (BB `predicato_giorno_operativo`) → `ix_error_log_occurred_at`
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
        limit: int = DEFAULT_LIMIT,
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
        # Giorni dell'azienda (BB). Le date arrivano ISO gia' validate dalla
        # view (`_filtri_error_log`, che le tiene stringa per l'export).
        giorno_sql, giorno_params = predicato_giorno_operativo(
            "e.occurred_at",
            date.fromisoformat(data_da) if data_da else None,
            date.fromisoformat(data_a) if data_a else None,
        )
        # Un WHERE per la pagina e per il suo conteggio di ripiego.
        where_sql = f"""WHERE (%s::text IS NULL OR e.area = %s)
               AND (%s::text IS NULL OR e.function_name LIKE %s)
               AND (%s::text IS NULL OR e.messaggio_errore_id IN (
                        SELECT mm.id FROM config.messaggi_errore mm WHERE mm.codice = %s))
               AND (%s::uuid IS NULL OR e.tx_id = %s::uuid)
               AND {giorno_sql}"""  # noqa: S608 — frammento del BB predicato_giorno_operativo (colonna validata), valori come parametri
        where_params = [
            area, area,
            prefisso, prefisso,
            codice, codice,
            tx_id, tx_id,
            *giorno_params,
        ]
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
             {where_sql}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
            """,  # noqa: S608 — ORDER BY da sql_order_clause su whitelist ERROR_LOG_SORT_COLUMNS, valori come parametri
            [*where_params, limit, offset],
            # Stesso FROM della pagina meno il LEFT JOIN (non cambia il numero).
            fallback_count_sql=f"""
                SELECT COUNT(*) FROM dbops.error_log e
                  JOIN config.messaggi_errore m ON m.id = e.messaggio_errore_id
                 {where_sql}
            """,  # noqa: S608 — WHERE costante, valori come parametri
            fallback_params=where_params,
            offset=offset,
        )
        risultato: list[ErrorLogRow] = [
            cast(ErrorLogRow, {
                **r,
                # `occurred_at` e' NOT NULL a DB: niente ramo per il None.
                "occurred_at": r["occurred_at"].isoformat(),
                # Decodificato dal lettore comune. La colonna e' NOT NULL
                # DEFAULT '{}', quindi qui arriva sempre un oggetto — gli
                # appunti del tecnico, intatti.
                "context": r["context"],
            })
            for r in righe
        ]
        return risultato, totale
