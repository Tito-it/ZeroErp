# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema pratiche (CRUD pratiche,
#        flussi, giornale, prerequisiti, canali).
# ------------------------------------------------------------

import json
from datetime import date, datetime
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI
from apps.core.db._helpers import (
    predicato_giorno_operativo,
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    coerce_jsonb_dict,
    fetch_paged_with_total,
    resolve_config_id_by_codice_interno,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.services.error_manager import ErrorManager
from apps.pratiche.types import RUOLO_LINK_ROOT

# coerce_jsonb_dict: promosso in apps.core.db._helpers (regola del 2,
# 2026-07-12) — qui resta il re-export storico per i caller esistenti
# (pratiche_service, test). Origine: bug handler_params={} sul dispatch
# CONFERMA, smoke pratica 2026-06-11.
__all__ = ["PraticheRepository", "coerce_jsonb_dict"]


# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# 'pratiche.pratiche' (e' quello che `<ListaConfigurabile>` invia come
# sortField), valore = espressione SQL. Qualificata dove la chiave e' una
# colonna fisica (la query joina otto tabelle); nuda dove e' un alias di output
# della SELECT, che ORDER BY risolve solo cosi'.
PRATICHE_ORDER_COLS: dict[str, str] = {
    # `id` aggiunto il 2026-08-02 (commessa BE 7° lotto, voce «migliora»): la
    # coda approvazioni prezzo mostra la colonna e passa da questa whitelist.
    "id": "p.id",
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "data_apertura": "p.data_apertura",
    "data_scadenza": "p.data_scadenza",
    "data_insert": "p.data_insert",
    "tipo_prestazione_descrizione": "tipo_prestazione_descrizione",
    "stato_descrizione": "stato_descrizione",
    "priorita_descrizione": "priorita_descrizione",
    "soggetto_display": "soggetto_display",
    "risorsa_umana_display": "risorsa_umana_display",
}


# -- Descrittore stato sorgente (proiezione V10, fase MOSTRA) ----------------
# Proietta lo stato VIVO del documento di dominio collegato (preventivo,
# offerta, ...) come display fields `doc_*`, via script.vw_stato_sorgente
# (union dei resolver di dominio) + pratiche.pratiche_sorgenti. Read-time,
# nessun mirror: il documento resta l'unica verita' (brief design V10).
#   doc_risolto=true  → proiezione reale del dominio;
#   doc_risolto=false → collegamento presente ma dominio senza resolver
#                       (fallback: il FE mostra il milestone come oggi);
#   doc_* NULL        → nessun documento collegato all'ancora.
_DOC_SORGENTE_SELECT = """
        ds.risolto AS doc_risolto,
        ds.stato_codice_interno AS doc_stato_codice_interno,
        ds.stato_descrizione AS doc_stato_descrizione,
        ds.fase AS doc_fase,
        ds.esito AS doc_esito,
        ds.terminale AS doc_terminale,
        ds.sorgente_descrizione AS doc_sorgente_descrizione
"""


# Scopo: frammento LATERAL del descrittore per l'aggancio PER-FLUSSO (percorso/
# coda): `anchor_cond` = "ps.flusso_id = f.id", SEMPRE statico, mai input utente.
# COALESCE su risolto: link presente ma dominio senza resolver → false
# (decisione C del brief design), non NULL.
# NB l'ancora PRATICA-LEVEL (dettaglio/lista) NON usa piu' questo frammento: e'
# stata promossa alla vista DB condivisa script.vw_pratica_doc_sorgente (roll-out
# offerte/ordini/contratti), che accende anche i COLLEGATO senza flusso_id. Qui
# resta solo il per-flusso, finche' D4 (pinning per-step del COLLEGATO, mappa
# step→sorgente condivisa con GUIDA) non promuovera' anche questo.
# Riferimento semantico del fallback: pratiche.fn_stato_sorgente (sentinella
# UNKNOWN); il join diretto alla vista e' la via sancita per le liste
# (doc fn_stato_sorgente: "niente N+1").
# ⚠️ Il resolver si cerca sulla chiave NATIVA del link, un ramo per chiave
#    (`sorgente_chiave_uuid = ps.sorgente_uid`, `sorgente_chiave_id =
#    ps.sorgente_id`): sotto RLS l'uguaglianza fra colonne native arriva
#    all'indice di ogni ramo della union, un OR sulle due chiavi no (legge
#    tutte le tabelle-documento). Stessa forma di script.vw_pratica_doc_sorgente
#    dal giro P.1 di brief-db-sorgente-documento-e-riga (2026-11-08), quando
#    `pratiche_sorgenti` e' passata alle colonne del modello e i BB
#    `script.fn_sorgente_chiave_uuid/_id` non servono piu'.
# ⏭️ E' la seconda copia della regola «link → stato del documento» (la prima
#    e' la vista): la sede per-flusso e' una richiesta al team DB (brief, §8.16).
def _doc_sorgente_lateral(anchor_cond: str) -> str:
    return f"""
        LEFT JOIN LATERAL (
            SELECT COALESCE(ss.risolto, false) AS risolto,
                   ss.stato_codice_interno, ss.stato_descrizione,
                   ss.fase, ss.esito, ss.terminale,
                   so.descrizione AS sorgente_descrizione
            FROM pratiche.pratiche_sorgenti ps
            JOIN config.sorgenti so ON so.id = ps.sorgente_tipo_id
            LEFT JOIN LATERAL (
                SELECT v.risolto, v.stato_codice_interno, v.stato_descrizione,
                       v.fase, v.esito, v.terminale
                FROM script.vw_stato_sorgente v
                WHERE v.sorgente_tipo_id = ps.sorgente_tipo_id
                  AND v.sorgente_chiave_uuid = ps.sorgente_uid
                UNION ALL
                SELECT v.risolto, v.stato_codice_interno, v.stato_descrizione,
                       v.fase, v.esito, v.terminale
                FROM script.vw_stato_sorgente v
                WHERE v.sorgente_tipo_id = ps.sorgente_tipo_id
                  AND v.sorgente_chiave_id = ps.sorgente_id
            ) ss ON true
            WHERE {anchor_cond}
            ORDER BY (ps.ruolo_link = '{RUOLO_LINK_ROOT}') DESC, ps.id DESC
            LIMIT 1
        ) ds ON true
    """  # noqa: S608 — anchor_cond letterale dei chiamanti e costante Final, mai da input


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⚠️ La stessa query serve `vendite.approvazioni_prezzo`, che non accende
#    colonne e non passa mai `search` (`lista_coda`): il giorno in cui
#    cercasse, la dichiarazione va passata dal chiamante, per lista.
_RICERCA_PRATICHE = RicercaFull("pratiche.pratiche", {
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "soggetto_display": "s.ragione_sociale_completa",
})


# Whitelist ORDER BY della lista `pratiche.flussi` (lista 85, tab «Flussi» del
# drawer pratica — brief-db-liste-datatable-grezze §4.1 riga 3). Chiave = il
# `campo_sorgente` del catalogo (e' cio' che il FE manda come `order_by`),
# valore = l'espressione che la `SELECT` proietta con quel nome: si ordina la
# colonna che si vede. `esito_descrizione` e non `esito`: la lista mostra la
# descrizione del vocabolario, non il codice grezzo (§8 punto 3, Tid).
# ⚠️ I vuoti (reparto, operatore, esito, scadenza) li colloca il BB
#    (`sql_order_direction`: ASC NULLS FIRST / DESC NULLS LAST, «il vuoto sta
#    dove starebbe lo zero»), come in ogni altra lista: niente `NULLS` scritto
#    a mano accanto a una sola chiave.
FLUSSI_ORDER_COLS: dict[str, str] = {
    "sequenza": "f.sequenza",
    "template_flusso_descrizione": "tf.descrizione",
    "stato_descrizione": "sf.descrizione",
    "esito_descrizione": "ef.descrizione",
    "data_scadenza": "f.data_scadenza",
    "risorsa_umana_display": "sru.ragione_sociale_completa",
    "unita_organizzativa_descrizione": "uo.descrizione",
    "data_insert": "f.data_insert",
}

# Colonne DATA della whitelist flussi: senza `order_dir` ordinano DESC (regola
# di Tid del 2026-09-02). Confrontate col seed da `test_liste_configurabili_seed`
# (test 10): devono coincidere con le colonne date/datetime ordinabili.
FLUSSI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_scadenza", "data_insert"})

# Il passo del percorso e' l'unica colonna che il catalogo accende alla ricerca
# (lista_colonna 954): la chiave e' il nome di USCITA, il valore l'espressione.
_RICERCA_FLUSSI = RicercaFull("pratiche.flussi", {
    "template_flusso_descrizione": "tf.descrizione",
})



# Scopo: i campi di una PATCH di pratica e il loro frammento di SET. La legge
#        anche il service (`aggiorna_pratica`), che rifiuta con un 400 una
#        chiave che non sta qui (brief-be-verifica-documentazione-api §B2).
PRATICA_UPDATE_SET: dict[str, str] = {
    "descrizione": "descrizione = %s",
    "data_scadenza": "data_scadenza = %s",
    "soggetto_id": "soggetto_id = %s",
    "risorsa_umana_id": "risorsa_umana_id = %s",
    "unita_organizzativa_id": "unita_organizzativa_id = %s",
    "meta": "meta = %s::jsonb",
}

class PraticheRepository:

    # -- SQL comuni pratiche (JOIN display fields) --

    _PRATICA_SELECT = """
        p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
        p.soggetto_id, p.soggetto_ruolo_id, p.istanza_utility_id,
        -- Il cliente di cui parla la pratica, a grana fine: colonna della pratica
        -- dal 2026-10-08 (brief-db-istanza-nasce-col-ba, D-9), non piu' derivato
        -- dall'istanza (un'istanza ha un BA per utility). NULL = pratica di un
        -- altro ruolo, interna, o senza istanza. Alimenta pre-fill+lock e gating
        -- documenti (offerta/contratto richiedono BA) aprendo un documento dal flusso.
        p.billing_account_id,
        p.stato_id, p.priorita_id,
        p.risorsa_umana_id, p.unita_organizzativa_id,
        p.pratica_padre_id, p.flusso_origine_id, p.canale_origine_id,
        p.codice, p.descrizione, p.data_apertura, p.data_scadenza,
        p.meta, p.data_insert, p.user_insert,
        tp.codice AS tipo_prestazione_codice,
        tp.descrizione AS tipo_prestazione_descrizione,
        sp.codice_interno AS stato_codice_interno,
        sp.descrizione AS stato_descrizione,
        pp.codice_interno AS priorita_codice_interno,
        pp.descrizione AS priorita_descrizione,
        s.ragione_sociale_completa AS soggetto_display,
        s.id_fiscale_univoco_cf_piva AS soggetto_id_fiscale,
        sru.ragione_sociale_completa AS risorsa_umana_display,
        uo.descrizione AS unita_organizzativa_descrizione,
    """ + _DOC_SORGENTE_SELECT

    # JOIN base (senza LATERAL): per la COUNT della lista, che non proietta
    # colonne — il LATERAL del descrittore e' cardinalita'-neutro (LIMIT 1)
    # ma costerebbe una risoluzione per riga filtrata, per zero output.
    _PRATICA_JOINS_BASE = """
        JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
        JOIN config.stati_pratiche sp ON sp.id = p.stato_id
        JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
        LEFT JOIN anagrafiche.soggetti s ON s.id = p.soggetto_id
        LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = p.risorsa_umana_id
        LEFT JOIN anagrafiche.soggetti_ruoli srr ON srr.id = ru.soggetto_ruolo_id
        LEFT JOIN anagrafiche.soggetti sru ON sru.id = srr.soggetto_id
        LEFT JOIN config.unita_organizzative uo ON uo.id = p.unita_organizzativa_id
    """

    # Descrittore doc_*: ancora pratica-level = documento PIU' VIVO della pratica
    # (proiezione V10, roll-out offerte/ordini/contratti). La regola d'ancora
    # (risolto → non-terminale → ROOT → piu' recente) vive ora nella vista DB
    # condivisa script.vw_pratica_doc_sorgente (una riga per pratica, DISTINCT ON),
    # non piu' inline: cosi' i documenti COLLEGATO senza flusso_id (ordine/commessa
    # da post-smistamento) si accendono a livello pratica. LEFT JOIN: pratica senza
    # sorgenti → doc_* NULL. Le colonne combaciano con _DOC_SORGENTE_SELECT.
    _PRATICA_JOINS = _PRATICA_JOINS_BASE + """
        LEFT JOIN script.vw_pratica_doc_sorgente ds ON ds.pratica_id = p.id
    """

    # -- Metodi pubblici per SQL comuni (usati anche da GenerazioneRepository) --

    @classmethod
    def pratica_select_sql(cls) -> str:
        """Restituisce il frammento SELECT per pratiche con display fields."""
        return cls._PRATICA_SELECT

    @classmethod
    def pratica_joins_sql(cls) -> str:
        """Restituisce il frammento JOIN per pratiche con display fields."""
        return cls._PRATICA_JOINS

    # -- PRATICHE --------------------------------------------------------

    # Scopo: Restituisce elenco pratiche paginato con filtri opzionali.
    # Perimetro: sola lettura, nessun side-effect.
    # Risultato: tuple (lista PraticaRow, conteggio totale).
    def list_pratiche(
        self,
        *,
        emittente_fiscale_id: int,
        stato_codice_interno: str | None = None,
        tipo_prestazione_id: int | None = None,
        soggetto_id: str | None = None,
        soggetto_ruolo_id: int | None = None,
        istanza_utility_id: int | None = None,
        solo_interne: bool = False,
        priorita_id: int | None = None,
        risorsa_umana_id: int | None = None,
        search: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        limit: int,
        offset: int,
        order_by: str = "data_insert",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=PRATICHE_ORDER_COLS,
            default=PRATICHE_ORDER_COLS["data_insert"],
            tiebreak="p.id",
            # Il default e' una DATA: parte dalla piu' recente (regola di Tid
            # 2026-09-02). Fino al 2026-10-20 mancava, e la lista partiva ASC.
            default_desc=True,
        )

        conditions: list[str] = ["p.emittente_fiscale_id = %s"]
        params: list[Any] = [emittente_fiscale_id]

        # Lente di contesto canonica (D1): la verita' del filtro vive nella fn
        # DB fn_lista_pratiche_per_contesto (bucket ruolo/istanza/interne);
        # qui si compone come semi-join per mantenere proiezione display,
        # filtri e paginazione della lista standard.
        if soggetto_ruolo_id is not None or istanza_utility_id is not None or solo_interne:
            conditions.append("""p.id IN (
                SELECT c.pratica_id
                FROM pratiche.fn_lista_pratiche_per_contesto(%s, %s, %s, %s) c
            )""")
            params.extend([
                emittente_fiscale_id, soggetto_ruolo_id,
                istanza_utility_id, solo_interne,
            ])

        if stato_codice_interno is not None:
            conditions.append("sp.codice_interno = %s")
            params.append(stato_codice_interno)
        if tipo_prestazione_id is not None:
            conditions.append("p.tipo_prestazione_id = %s")
            params.append(tipo_prestazione_id)
        if soggetto_id is not None:
            conditions.append("p.soggetto_id = %s")
            params.append(soggetto_id)
        if priorita_id is not None:
            conditions.append("p.priorita_id = %s")
            params.append(priorita_id)
        if risorsa_umana_id is not None:
            conditions.append("p.risorsa_umana_id = %s")
            params.append(risorsa_umana_id)
        # Giorni dell'AZIENDA, `data_a` incluso (BB, brief un-solo-fuso-aziendale B-4).
        giorno_sql, giorno_params = predicato_giorno_operativo("p.data_insert", data_da, data_a)
        conditions.append(giorno_sql)
        params.extend(giorno_params)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_PRATICHE)

        where_clause = "WHERE " + " AND ".join(conditions)

        count_sql = f"""
            SELECT COUNT(*)
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS_BASE}
            {where_clause}
        """  # noqa: S608 — join costanti di classe, WHERE da frammenti letterali + colonne _RICERCA_PRATICHE, valori come parametri

        data_sql = f"""
            SELECT {self._PRATICA_SELECT}
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS}
            {where_clause}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
        """  # noqa: S608 — costanti di classe, WHERE letterale, ORDER BY da sql_order_clause su PRATICHE_ORDER_COLS, valori come parametri

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_PRATICA_QUERY",
                message="Errore conteggio pratiche",
            )
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            result = rows_to_list(cursor)

        return result, total_count

    # Scopo: Restituisce il dettaglio di una singola pratica per ID con display fields.
    def get_pratica(self, pratica_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._PRATICA_SELECT}
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS}
            WHERE p.id = %s
        """  # noqa: S608 — _PRATICA_SELECT/_JOINS costanti di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova pratica e ritorna l'ID generato.
    def create_pratica(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.pratiche (
                emittente_fiscale_id, tipo_prestazione_id, soggetto_id,
                soggetto_ruolo_id, istanza_utility_id, billing_account_id,
                stato_id, priorita_id, risorsa_umana_id,
                unita_organizzativa_id, canale_origine_id,
                descrizione, data_scadenza, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        params = [
            data["emittente_fiscale_id"],
            data["tipo_prestazione_id"],
            data.get("soggetto_id"),
            data.get("soggetto_ruolo_id"),
            data.get("istanza_utility_id"),
            data.get("billing_account_id"),
            data["stato_id"],
            data["priorita_id"],
            data.get("risorsa_umana_id"),
            data.get("unita_organizzativa_id"),
            data.get("canale_origine_id"),
            data.get("descrizione"),
            data.get("data_scadenza"),
            json.dumps(data.get("meta", {})),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_PRATICA_INSERT",
                message="Errore inserimento pratica (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna i campi modificabili di una pratica esistente.
    def update_pratica(self, pratica_id: int, data: dict[str, Any]) -> None:
        # Costruzione SET dinamica con whitelist campi aggiornabili.
        set_parts: list[str] = []
        params: list[Any] = []
        for field_name, sql_fragment in PRATICA_UPDATE_SET.items():
            if field_name in data:
                set_parts.append(sql_fragment)
                if field_name == "meta":
                    params.append(json.dumps(data[field_name]))
                else:
                    params.append(data[field_name])

        if not set_parts:
            return

        params.append(pratica_id)
        sql = f"""
            UPDATE pratiche.pratiche
            SET {', '.join(set_parts)}
            WHERE id = %s
        """  # noqa: S608 — SET dalla whitelist locale allowed_fields, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    # Scopo: Aggiorna lo stato di una pratica tramite codice_interno dello stato.
    # Risolve lo stato prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
    # `codice_errore`/`campo`: quando lo stato l'ha scelto il client (vedi il BB).
    def update_stato_pratica(
        self, pratica_id: int, stato_codice_interno: str,
        *, codice_errore: str = "E_CONFIG_MANCANTE", campo: str | None = None,
    ) -> None:
        stato_id = self.resolve_stato_pratica(
            stato_codice_interno, codice_errore=codice_errore, campo=campo,
        )
        sql = """
            UPDATE pratiche.pratiche
            SET stato_id = %s
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, pratica_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_PRATICA_NOT_FOUND",
                message=f"Pratica {pratica_id} non trovata",
            )

    # -- FLUSSI ----------------------------------------------------------

    _FLUSSO_SELECT = """
        f.id, f.pratica_id, f.template_flusso_id, f.stato_id,
        f.flusso_padre_id, f.risorsa_umana_id,
        f.unita_organizzativa_id, f.sequenza,
        f.esito, f.note_esito, f.data_scadenza,
        f.meta, f.data_insert, f.user_insert,
        sf.codice_interno AS stato_codice_interno,
        sf.descrizione AS stato_descrizione,
        -- Descrizione umana dell'esito registrato (vocabolario globale
        -- config.esiti_flussi_pratiche): il FE mostra esito_descrizione, non il codice.
        ef.descrizione AS esito_descrizione,
        tf.codice AS template_flusso_codice,
        tf.descrizione AS template_flusso_descrizione,
        -- Configurazione esito dello step (20260617-01): governa come il FE
        -- (FlussoDrawer) presenta avvio/completamento. MANUALE = avvio poi form
        -- esito; AUTOMATICO = avvia+completa con esito_default; CONTESTUALE =
        -- avvio+esito in un'unica azione (esito_default pre-selezionato).
        tf.modalita_esito AS template_modalita_esito,
        tf.esito_default AS template_esito_default,
        -- GUIDA (D4): sorgente-documento attesa dal milestone (G1). NON NULL =
        -- step PROJECTION-DRIVEN → il FE instrada «Accetta/Rifiuta» sul DOCUMENTO
        -- (non completa il flusso; il milestone avanza da solo via trigger DB).
        tf.attende_sorgente_tipo_id AS template_attende_sorgente_tipo_id,
        -- Attività UI data-driven (catalogo pratiche.azioni_ui): chiave risolta
        -- dal registry FE → drawer di dominio da aprire dal flusso. NULL = nessuna.
        au.azione_ui_key AS template_azione_ui_key,
        p.codice AS pratica_codice,
        p.data_apertura AS pratica_data_apertura,
        p.istanza_utility_id AS pratica_istanza_utility_id,
        p.billing_account_id AS pratica_billing_account_id,
        s.ragione_sociale_completa AS pratica_soggetto_display,
        s.id_fiscale_univoco_cf_piva AS pratica_soggetto_id_fiscale,
        -- Assegnazione del singolo step (20260618): operatore + reparto con
        -- display fields via JOIN (no lookup client-side). Mirror del pattern
        -- della lista pratiche.
        sru.ragione_sociale_completa AS risorsa_umana_display,
        uo.descrizione AS unita_organizzativa_descrizione
    """

    _FLUSSO_JOINS = """
        JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
        LEFT JOIN config.esiti_flussi_pratiche ef ON ef.codice_interno = f.esito
        LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
        LEFT JOIN pratiche.azioni_ui au ON au.id = tf.azione_ui_id
        JOIN pratiche.pratiche p ON p.id = f.pratica_id
        LEFT JOIN anagrafiche.soggetti s ON s.id = p.soggetto_id
        LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = f.risorsa_umana_id
        LEFT JOIN anagrafiche.soggetti_ruoli srr ON srr.id = ru.soggetto_ruolo_id
        LEFT JOIN anagrafiche.soggetti sru ON sru.id = srr.soggetto_id
        LEFT JOIN config.unita_organizzative uo ON uo.id = f.unita_organizzativa_id
    """

    # Scopo: la LISTA `pratiche.flussi` (lista 85): i flussi di una pratica,
    #        paginati, ordinati sulla whitelist e con la ricerca del catalogo.
    #        Restituisce (righe, totale).
    #
    # ⛔ IL JOIN SU `pratiche.pratiche` RESTA ANCHE NEL CONTEGGIO, ed e' la
    #    stessa ragione di `get_pratica_di_flusso`: `pratiche.flussi` non ha
    #    RLS, la pratica si'. Un `COUNT` sulla sola `flussi` conterebbe i
    #    flussi di una pratica fuori perimetro e direbbe «12» mostrandone 0.
    #    Per questo il ripiego del conteggio usa lo STESSO frammento
    #    FROM+JOIN+WHERE della pagina, non uno riscritto piu' magro.
    # ⚠️ Default = l'ordine storico del tab (`sequenza`, poi `id`): e' la
    #    posizione del flusso nella pratica, ed e' come la si legge.
    def list_flussi_pagina(
        self,
        pratica_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=FLUSSI_ORDER_COLS, default="f.sequenza", tiebreak="f.id",
            colonne_desc=FLUSSI_SORT_COLONNE_DATA,
        )
        conditions: list[str] = ["f.pratica_id = %s"]
        params: list[Any] = [pratica_id]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_FLUSSI)
        from_where = (
            f"FROM pratiche.flussi f {self._FLUSSO_JOINS} "
            f"WHERE {' AND '.join(conditions)}"
        )
        return fetch_paged_with_total(
            f"""
            SELECT {self._FLUSSO_SELECT},
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist FLUSSI_ORDER_COLS, WHERE da condizioni letterali + add_ricerca_full_condition, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

    # Scopo: TUTTI i flussi di una pratica ordinati per sequenza, con display
    #        fields — la lettura intera per chi ragiona sul percorso (il tool
    #        dell'assistente AI), non la lista a video.
    # ⚠️ La lista del tab e' `list_flussi_pagina`: stessa proiezione e stessi
    #    JOIN (`_FLUSSO_SELECT`/`_FLUSSO_JOINS`), ma pagina, ordinamento e
    #    ricerca sono dell'operatore. Qui l'ordine e' quello del percorso.
    def list_flussi(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._FLUSSO_SELECT}
            FROM pratiche.flussi f
            {self._FLUSSO_JOINS}
            WHERE f.pratica_id = %s
            ORDER BY f.sequenza, f.id
        """  # noqa: S608 — _FLUSSO_SELECT/_JOINS costanti di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Restituisce il dettaglio di un singolo flusso con display fields.
    def get_flusso(self, flusso_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._FLUSSO_SELECT}
            FROM pratiche.flussi f
            {self._FLUSSO_JOINS}
            WHERE f.id = %s
        """  # noqa: S608 — _FLUSSO_SELECT/_JOINS costanti di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            return row_to_dict(cursor)

    # Scopo: ⭐ La pratica a cui un flusso appartiene, dal solo id del flusso.
    #
    # ⚠️ NON si riusa `get_flusso`, e le ragioni sono due — la seconda e' quella
    #    che conta. (1) COSTO: quella proiezione fa NOVE join (soggetti, risorse
    #    umane, azioni_ui, unita organizzative...) per restituire una colonna;
    #    e' la stessa ragione per cui esiste `get_flusso_esito_config`, poco piu'
    #    sotto. (2) ⛔ VISIBILITA': la sua risposta dipende anche da join che con
    #    la domanda non c'entrano, e qui la domanda e' una sola.
    #
    # ⛔ IL JOIN SU `pratiche` NON E' DECORATIVO — misurato il 2026-08-24:
    #    `pratiche.flussi` **non ha RLS**, `pratiche.pratiche` si'. Una lettura
    #    del solo `flussi` risponderebbe per QUALUNQUE flusso, anche di una
    #    pratica fuori dal perimetro di chi chiede: un id di troppo, e un
    #    pulsante che porta su una schermata che rifiutera' di aprirsi.
    #    Con il join la RLS della pratica decide, e un flusso non raggiungibile
    #    e' indistinguibile da uno che non esiste — che per chi opera e' la
    #    stessa cosa.
    def get_pratica_di_flusso(self, flusso_id: int) -> int | None:
        sql = """
            SELECT f.pratica_id
              FROM pratiche.flussi f
              JOIN pratiche.pratiche p ON p.id = f.pratica_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Config esito dello step (modalita_esito + esito_default dal template).
    # Query leggera per il path di avvio (evita la proiezione completa di get_flusso,
    # che fa JOIN soggetti/azioni_ui + fn BA per soli 2 campi). Ritorna
    # (modalita_esito, esito_default) o None se il flusso non esiste; template
    # assente (flusso legacy senza template) → modalita MANUALE.
    def get_flusso_esito_config(self, flusso_id: int) -> tuple[str, str | None] | None:
        sql = """
            SELECT COALESCE(tf.modalita_esito, 'MANUALE') AS modalita_esito,
                   tf.esito_default
            FROM pratiche.flussi f
            LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
            WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            row = cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1])

    # Scopo: Voce del vocabolario esiti per codice_interno (attivo + is_verdetto).
    # Fonte unica di verita' per la validazione applicativa degli esiti (errore
    # parlante prima del round-trip di scrittura): sostituisce i mirror
    # hardcoded ESITI_FLUSSO_AMMESSI/ESITI_FLUSSO_RAMO del service.
    # is_verdetto true = esito deciso dall'operatore (selezionabile a mano);
    # false = esito di ramo calcolato dal dominio (DEFAULT fail-closed a DB).
    # Ritorna (attivo, is_verdetto) o None se il codice non e' a vocabolario.
    def get_esito_flusso_vocabolario(self, codice_interno: str) -> tuple[bool, bool] | None:
        sql = """
            SELECT e.attivo, e.is_verdetto
            FROM config.esiti_flussi_pratiche e
            WHERE e.codice_interno = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
        if row is None:
            return None
        return (bool(row[0]), bool(row[1]))

    # Scopo: Aggiorna i campi di assegnazione di un flusso (whitelist).
    # L'UPDATE di risorsa_umana_id/unita_organizzativa_id attiva il trigger
    # giornale trg_flussi_z90_giornale_assegnazione_upd. Guard not-found esplicito.
    def update_flusso(self, flusso_id: int, data: dict[str, Any]) -> None:
        allowed_fields: dict[str, str] = {
            "risorsa_umana_id": "risorsa_umana_id = %s",
            "unita_organizzativa_id": "unita_organizzativa_id = %s",
        }

        set_parts: list[str] = []
        params: list[Any] = []
        for field_name, sql_fragment in allowed_fields.items():
            if field_name in data:
                set_parts.append(sql_fragment)
                params.append(data[field_name])

        if not set_parts:
            return

        params.append(flusso_id)
        sql = f"""
            UPDATE pratiche.flussi
            SET {', '.join(set_parts)}
            WHERE id = %s
        """  # noqa: S608 — SET dalla whitelist locale allowed_fields, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_FLUSSO_NOT_FOUND",
                message=f"Flusso {flusso_id} non trovato",
            )

    # Scopo: Operatori (risorse umane attive) di un reparto, per il picker di
    # assegnazione flusso. Display = ragione sociale del soggetto collegato.
    def list_operatori_reparto(self, unita_organizzativa_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT ru.id,
                   sru.ragione_sociale_completa AS display
            FROM anagrafiche.risorse_umane ru
            JOIN anagrafiche.soggetti_ruoli srr ON srr.id = ru.soggetto_ruolo_id
            JOIN anagrafiche.soggetti sru ON sru.id = srr.soggetto_id
            WHERE ru.unita_organizzativa_id = %s
              AND ru.attivo = true
            ORDER BY sru.ragione_sociale_completa, ru.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [unita_organizzativa_id])
            return rows_to_list(cursor)

    # Scopo: Percorso suggerito della pratica = template_flussi del suo
    #        tipo_prestazione (in ordine), LEFT JOIN i flussi gia' istanziati.
    #        Ogni riga: lo step (codice/sequenza/obbligatorio/has_handler) +,
    #        se istanziato, flusso_id/stato/esito. Alimenta la roadmap FE (i
    #        flussi NON sono materializzati alla creazione: si creano
    #        progressivamente, §6 brief FE).
    def get_percorso_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        # Arricchimento workflow v2 (D3/D4): per ogni step la fn DB dice se e'
        # ripetibile ADESSO (regola template + ultima istanza) e lo stato del
        # ramo da fn_check_chiusura_pratica (completato / percorribile /
        # bloccante). `ramo` e' la sintesi per la resa FE:
        #   COMPLETATO   → almeno un'istanza chiusa;
        #   PERCORRIBILE → prerequisiti soddisfatti, eseguibile ora;
        #   RAMO_CHIUSO  → un prerequisito e' stato DECISO (istanza COMPLETATO)
        #                  ma mai con l'esito richiesto: il bivio ha preso
        #                  l'altra strada (allo stato attuale: un retry del
        #                  predecessore puo' riaprirlo);
        #   FUTURO       → prerequisiti non ancora decisi (step a valle).
        # Proiezione V10 (fase MOSTRA): per ogni step con documento agganciato
        # al SUO flusso (pratiche_sorgenti.flusso_id), i display fields doc_*
        # proiettano lo stato vivo del documento (vista-racconto: "il flusso
        # si chiude all'emissione, il preventivo continua a vivere").
        sql = f"""
            SELECT
                tf.id AS template_flusso_id,
                tf.codice AS template_flusso_codice,
                tf.descrizione AS template_flusso_descrizione,
                tf.sequenza,
                tf.obbligatorio,
                tf.direzione,
                (tf.handler_id IS NOT NULL) AS has_handler,
                -- GUIDA (D4): flag PROJECTION-DRIVEN (vedi SELECT dettaglio flusso).
                tf.attende_sorgente_tipo_id AS template_attende_sorgente_tipo_id,
                au.azione_ui_key AS template_azione_ui_key,
                f.id AS flusso_id,
                sf.codice_interno AS stato_codice_interno,
                sf.descrizione AS stato_descrizione,
                f.esito,
                ef.descrizione AS esito_descrizione,
                pratiche.fn_check_ripetibilita_flusso(p.id, tf.id) AS ripetibile_adesso,
                COALESCE(cc.completato, false) AS completato,
                COALESCE(cc.percorribile, false) AS percorribile,
                COALESCE(cc.bloccante, false) AS bloccante,
                CASE
                    WHEN COALESCE(cc.completato, false) THEN 'COMPLETATO'
                    WHEN COALESCE(cc.percorribile, false) THEN 'PERCORRIBILE'
                    -- RAMO_CHIUSO: un prerequisito NON soddisfatto (verita'
                    -- esito-aware delegata alla fn DB, niente regole
                    -- duplicate qui) il cui template e' pero' gia' stato
                    -- DECISO (almeno un'istanza COMPLETATO) → il bivio ha
                    -- preso l'altra strada. Senza prerequisiti decisi e'
                    -- solo uno step FUTURO.
                    WHEN EXISTS (
                        SELECT 1
                        FROM pratiche.fn_check_prerequisiti_flusso(p.id, tf.id) pr
                        WHERE NOT pr.soddisfatto
                          AND EXISTS (
                              SELECT 1
                              FROM pratiche.flussi pf
                              JOIN config.stati_flussi_pratiche psf
                                ON psf.id = pf.stato_id
                              WHERE pf.pratica_id = p.id
                                AND pf.template_flusso_id = pr.prerequisito_id
                                AND psf.codice_interno = 'COMPLETATO'
                          )
                    ) THEN 'RAMO_CHIUSO'
                    ELSE 'FUTURO'
                END AS ramo,
                {_DOC_SORGENTE_SELECT}
            FROM pratiche.pratiche p
            -- Percorso definizione-aware (workflow versionati, Fase 1 / companion
            -- BE-2.2): i template si selezionano per la DEFINIZIONE pinnata sulla
            -- pratica, non per tipo. Da quando esistono più definizioni dello
            -- stesso tipo (fork, Fase 2) la join per tipo duplicherebbe le righe.
            JOIN pratiche.template_flussi tf
              ON tf.definizione_id = p.definizione_id AND tf.attivo
            LEFT JOIN pratiche.azioni_ui au ON au.id = tf.azione_ui_id
            LEFT JOIN pratiche.fn_check_chiusura_pratica(%s) cc
              ON cc.template_flusso_id = tf.id
            LEFT JOIN LATERAL (
                SELECT ff.id, ff.stato_id, ff.esito
                FROM pratiche.flussi ff
                WHERE ff.pratica_id = p.id AND ff.template_flusso_id = tf.id
                ORDER BY ff.id DESC
                LIMIT 1
            ) f ON true
            LEFT JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
            -- Descrizione umana dell'esito (data-driven da config.esiti_flussi_pratiche,
            -- vocabolario globale): il FE mostra `esito_descrizione`, non il codice grezzo.
            LEFT JOIN config.esiti_flussi_pratiche ef ON ef.codice_interno = f.esito
            {_doc_sorgente_lateral("ps.pratica_id = p.id AND ps.flusso_id = f.id")}
            WHERE p.id = %s
            ORDER BY tf.sequenza, tf.id
        """  # noqa: S608 — _DOC_SORGENTE_SELECT costante e lateral con anchor letterale, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, pratica_id])
            return rows_to_list(cursor)

    # Scopo: Inserisce un nuovo flusso. Il trigger DB valida i prerequisiti.
    def create_flusso(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.flussi (
                pratica_id, template_flusso_id, stato_id,
                flusso_padre_id, risorsa_umana_id,
                unita_organizzativa_id, sequenza, data_scadenza, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        params = [
            data["pratica_id"],
            data.get("template_flusso_id"),
            data["stato_id"],
            data.get("flusso_padre_id"),
            data.get("risorsa_umana_id"),
            data.get("unita_organizzativa_id"),
            data.get("sequenza", 0),
            data.get("data_scadenza"),
            json.dumps(data.get("meta", {})),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_FLUSSO_INSERT",
                message="Errore inserimento flusso (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna lo stato di un flusso tramite codice_interno.
    # Risolve lo stato prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
    def update_stato_flusso(
        self, flusso_id: int, stato_codice_interno: str,
        esito: str | None = None, note_esito: str | None = None,
        *, codice_errore: str = "E_CONFIG_MANCANTE", campo: str | None = None,
    ) -> None:
        stato_id = self.resolve_stato_flusso(
            stato_codice_interno, codice_errore=codice_errore, campo=campo,
        )
        sql = """
            UPDATE pratiche.flussi
            SET stato_id = %s,
                esito = COALESCE(%s, esito),
                note_esito = COALESCE(%s, note_esito)
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, esito, note_esito, flusso_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_FLUSSO_NOT_FOUND",
                message=f"Flusso {flusso_id} non trovato",
            )

    # -- PREREQUISITI ----------------------------------------------------

    # Scopo: Chiama fn_check_prerequisiti_flusso per verifica prerequisiti.
    # Ritorna una riga per ogni prerequisito con flag soddisfatto.
    def check_prerequisiti(
        self, pratica_id: int, template_flusso_id: int,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT prerequisito_id, codice, descrizione, soddisfatto
            FROM pratiche.fn_check_prerequisiti_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, template_flusso_id])
            return rows_to_list(cursor)

    # -- GIORNALE --------------------------------------------------------

    # Scopo: Restituisce il giornale di bordo di una pratica (audit trail).
    # Ordinato cronologicamente (piu' recente in cima), include tx_id per tracciabilita'.
    def get_giornale_pratica(
        self, pratica_id: int, *, limit: int = DEFAULT_LIMIT_EVENTI, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)

        count_sql = """
            SELECT COUNT(*)
            FROM pratiche.giornale
            WHERE pratica_id = %s
        """
        # Display fields (no lookup client-side): descrizione del flusso a cui
        # l'evento si riferisce (giornale.flusso_id → template) e decode degli
        # stati della transizione FLUSSO_STATO_CAMBIATO (dettaglio jsonb porta gli
        # id). Il decode stati usa config.stati_flussi_pratiche SOLO per gli eventi
        # di flusso (g.flusso_id NOT NULL): gli eventi di pratica (flusso_id NULL)
        # referenziano un'altra tabella stati → niente join fuorviante.
        data_sql = """
            SELECT
                g.id, g.pratica_id, g.flusso_id, g.azione,
                g.origine, g.dettaglio, g.tx_id,
                g.data_insert, g.user_insert,
                tf.codice AS flusso_template_codice,
                tf.descrizione AS flusso_template_descrizione,
                sp.descrizione AS dettaglio_stato_precedente,
                sn.descrizione AS dettaglio_stato_nuovo
            FROM pratiche.giornale g
            LEFT JOIN pratiche.flussi f ON f.id = g.flusso_id
            LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
            LEFT JOIN config.stati_flussi_pratiche sp
                ON g.flusso_id IS NOT NULL
               AND sp.id = NULLIF(g.dettaglio->>'stato_precedente_id', '')::int
            LEFT JOIN config.stati_flussi_pratiche sn
                ON g.flusso_id IS NOT NULL
               AND sn.id = NULLIF(g.dettaglio->>'stato_nuovo_id', '')::int
            WHERE g.pratica_id = %s
            ORDER BY g.data_insert DESC, g.id DESC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, [pratica_id])
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_GIORNALE_QUERY",
                message="Errore conteggio giornale",
            )
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, [pratica_id, safe_limit, safe_offset])
            result = rows_to_list(cursor)

        return result, total_count

    # Scopo: Scrive un evento di dominio DOMINIO_* sul giornale via la fn DB
    # dedicata (append-only, origine='HANDLER', forma DOMINIO_* garantita dal
    # CHECK chk_giornale_azione). Unico canale applicativo di scrittura.
    def log_evento_dominio(
        self, *, pratica_id: int, flusso_id: int | None,
        tipo_evento: str, meta: dict[str, Any] | None = None,
    ) -> int:
        sql = """
            SELECT pratiche.fn_log_evento_dominio(
                p_pratica_id => %s,
                p_flusso_id => %s,
                p_tipo_evento => %s,
                p_meta => %s::jsonb
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, flusso_id, tipo_evento, json.dumps(meta or {})])
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # -- SORGENTI --------------------------------------------------------

    # Scopo: Aggancia (idempotente) una sorgente alla pratica.
    # ⭐ La PROVENIENZA la sceglie il BB del DB, non questo metodo:
    #    `script.fn_sorgente_provenienza(codice, chiave)` da' il tipo e la sola
    #    chiave che il `key_selector` del tipo vuole (`sorgente_id` per ordine e
    #    commessa, `sorgente_uid` per il preventivo), da una chiave QUALSIASI del
    #    documento in testo, e solleva su un codice che non e' un tipo
    #    (`E_SORG_CONF`) o su un documento che non c'e' o non si vede. E' lo
    #    stesso BB dei verbi DB che scrivono il link (giro P.1 di
    #    brief-db-sorgente-documento-e-riga, 2026-11-08): scegliere la colonna a
    #    mano sarebbe una seconda copia del catalogo delle sorgenti.
    # ON CONFLICT sull'unicita' del modello, `uq_pratiche_sorgenti_pratica_
    # sorgente_ruolo` (pratica, tipo, le due chiavi, ruolo; NULLS NOT DISTINCT):
    # in una pratica, con lo stesso ruolo, un documento compare una volta sola.
    # La ri-chiamata NON e' un no-op totale — aggiorna flusso_id (se fornito)
    # per ri-ancorare il link all'istanza corrente.
    # Caso reale: step ripetuto ("Ripeti") → nuova istanza flusso; con DO
    # NOTHING il ROOT restava ancorato al flusso vecchio e la proiezione
    # doc_* (LATERAL su ps.flusso_id = f.id, f = ultima istanza) spariva.
    def upsert_pratica_sorgente(
        self, *, pratica_id: int, sorgente_codice: str, sorgente_chiave: str,
        ruolo_link: str = RUOLO_LINK_ROOT, sorgente_riga: int | None = None,
        flusso_id: int | None = None, meta: dict[str, Any] | None = None,
    ) -> None:
        # flusso_id ancora il ROOT documento->flusso d'origine (aggancio per-flusso,
        # brief-db-aggancio-documento-flusso). NULL per i COLLEGATO a valle
        # (commessa/ordine): non nascono da un flusso, non vincolati. L'indice
        # parziale uq_pratiche_sorgenti_flusso_root impedisce due ROOT sullo stesso
        # flusso; il trigger guard verifica che il flusso sia DI questa pratica.
        sql = """
            INSERT INTO pratiche.pratiche_sorgenti (
                pratica_id, sorgente_tipo_id, sorgente_id, sorgente_uid,
                sorgente_riga, ruolo_link, flusso_id, meta
            )
            SELECT %s, p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid,
                   %s, %s, %s, %s::jsonb
              FROM script.fn_sorgente_provenienza(%s, %s::text) p
            ON CONFLICT ON CONSTRAINT uq_pratiche_sorgenti_pratica_sorgente_ruolo
            DO UPDATE SET flusso_id = COALESCE(
                EXCLUDED.flusso_id, pratiche_sorgenti.flusso_id
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                pratica_id, sorgente_riga, ruolo_link, flusso_id,
                json.dumps(meta or {}), sorgente_codice, sorgente_chiave,
            ])
            # ROWS 1: il BB solleva, non torna vuoto; e l'ON CONFLICT DO UPDATE
            # conta la riga anche quando il link c'era. Zero righe e' il patto
            # del DB rotto: RuntimeError e non `assert`, resta acceso con `-O`.
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "fn_sorgente_provenienza senza riga e senza errore",
                )

    # Scopo: Reverse di upsert_pratica_sorgente — risolve la pratica cui una
    # sorgente e' agganciata (codice del tipo + una chiave qualsiasi del
    # documento in testo, opzionalmente per ruolo). None se non agganciata.
    # Usato dagli step ordine del percorso pratica (CONFERMA_ORDINE/
    # INVIO_COMMESSA) per risalire alla pratica dall'ordine COLLEGATO e
    # auto-completare il flusso all'azione standalone. Cross-schema read
    # consentito. ruolo_link=None = qualunque ruolo.
    # ⭐ La coppia da cercare la da' il BB che la scrive (stessa sede dello
    #    scrittore qui sopra), e il link si incontra con la regola del modello,
    #    una delle due chiavi: come `OrdiniRepository.get_ordine_by_documento_origine`.
    #    ⚠️ Il BB solleva se il documento non e' visibile: un documento fuori
    #    perimetro non ha pratiche da cercare.
    def get_pratica_id_by_sorgente(
        self, *, sorgente_codice: str, sorgente_chiave: str, ruolo_link: str | None = None,
    ) -> int | None:
        sql = """
            SELECT ps.pratica_id
              FROM script.fn_sorgente_provenienza(%s, %s::text) p
              JOIN pratiche.pratiche_sorgenti ps
                ON ps.sorgente_tipo_id = p.sorgente_tipo_id
               AND (ps.sorgente_id = p.sorgente_id OR ps.sorgente_uid = p.sorgente_uid)
             WHERE (%s::text IS NULL OR ps.ruolo_link = %s)
             ORDER BY ps.id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [sorgente_codice, sorgente_chiave, ruolo_link, ruolo_link])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # -- CANALI ----------------------------------------------------------

    # Scopo: Restituisce i canali abilitati per un template flusso.
    def get_canali_flusso(self, template_flusso_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT cp.id, cp.codice, cp.descrizione, cp.codice_interno
            FROM pratiche.template_flussi_canali tfc
            JOIN config.canali_pratiche cp ON cp.id = tfc.canale_id
            WHERE tfc.template_flusso_id = %s
              AND tfc.attivo = true
              AND cp.attivo = true
            ORDER BY cp.codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            return rows_to_list(cursor)

    # -- SOSPENSIONI -----------------------------------------------------

    _SOSPENSIONE_COLS = """
        id, pratica_id, flusso_id, data_inizio, data_fine,
        data_riattivazione_prevista, motivo,
        data_insert, user_insert, data_update, user_update
    """

    # Scopo: Inserisce una nuova sospensione per pratica (o flusso) e ritorna l'ID.
    # data_inizio opzionale (ISO): se assente usa NOW() (retro-compatibile); se
    # valorizzato consente la data/ora manuale, anche retroattiva. Il guard DB
    # (trg a10) rifiuta le date nel futuro; l'EXCLUDE ex_sospensioni_no_overlap
    # rifiuta i periodi sovrapposti sullo stesso scope.
    def create_sospensione(
        self,
        pratica_id: int,
        motivo: str,
        *,
        flusso_id: int | None = None,
        data_riattivazione_prevista: str | None = None,
        data_inizio: datetime | None = None,
    ) -> int:
        sql = """
            INSERT INTO pratiche.sospensioni (
                pratica_id, flusso_id, data_inizio, motivo,
                data_riattivazione_prevista
            ) VALUES (
                %s, %s, COALESCE(%s::timestamptz, NOW()), %s, %s
            )
            RETURNING id
        """
        params = [
            pratica_id,
            flusso_id,
            data_inizio,
            motivo,
            data_riattivazione_prevista,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_SOSPENSIONE_INSERT",
                message="Errore inserimento sospensione (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Chiude la sospensione attiva impostando data_fine.
    # data_fine opzionale (ISO): se assente usa NOW() (retro-compatibile); se
    # valorizzato consente la data/ora manuale di riattivazione. Il CHECK DB
    # garantisce data_fine > data_inizio, il guard a10 rifiuta date future.
    # Il trigger DB gestisce la riattivazione (ripristino stati flussi).
    def chiudi_sospensione(
        self,
        sospensione_id: int,
        *,
        data_fine: datetime | None = None,
    ) -> None:
        sql = """
            UPDATE pratiche.sospensioni
            SET data_fine = COALESCE(%s::timestamptz, NOW())
            WHERE id = %s AND data_fine IS NULL
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [data_fine, sospensione_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_SOSPENSIONE_NOT_FOUND",
                message=f"Sospensione {sospensione_id} non trovata o gia' chiusa",
            )

    # Scopo: Trova la sospensione attiva (data_fine IS NULL) per una pratica intera.
    def get_sospensione_attiva_pratica(self, pratica_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id IS NULL AND data_fine IS NULL
            LIMIT 1
        """  # noqa: S608 — _SOSPENSIONE_COLS costante di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return row_to_dict(cursor)

    # Scopo: Trova la sospensione attiva per un flusso specifico.
    def get_sospensione_attiva_flusso(self, pratica_id: int, flusso_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id = %s AND data_fine IS NULL
            LIMIT 1
        """  # noqa: S608 — _SOSPENSIONE_COLS costante di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, flusso_id])
            return row_to_dict(cursor)

    # Scopo: Restituisce le sospensioni di una pratica (tutte, ordinate per data).
    def list_sospensioni(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s
            ORDER BY data_inizio DESC, id DESC
        """  # noqa: S608 — _SOSPENSIONE_COLS costante di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # -- NOTE PRATICHE ---------------------------------------------------

    _NOTA_SELECT = """
        n.id, n.pratica_id, n.tipo_nota_id,
        tn.codice_interno AS tipo_nota_codice,
        tn.descrizione AS tipo_nota_descrizione,
        n.contenuto, n.data_insert, n.user_insert,
        n.data_update, n.user_update
    """

    _NOTA_JOINS = """
        JOIN config.tipi_nota tn ON tn.id = n.tipo_nota_id
    """

    # Scopo: Restituisce le note di una pratica con tipo nota display.
    def list_note_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._NOTA_SELECT}
            FROM pratiche.note_pratiche n
            {self._NOTA_JOINS}
            WHERE n.pratica_id = %s
            ORDER BY n.data_insert DESC, n.id DESC
        """  # noqa: S608 — _NOTA_SELECT/_JOINS costanti di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Crea una nota per la pratica. Risolve tipo_nota da codice_interno.
    def create_nota_pratica(
        self, pratica_id: int, tipo_nota_codice: str, contenuto: str,
    ) -> int:
        # Risolve tipo_nota_id prima dell'INSERT per errore chiaro
        tipo_nota_id = resolve_config_id_by_codice_interno(
            "config.tipi_nota",
            tipo_nota_codice,
            etichetta="Tipo nota",
            not_found_message=(
                f"Tipo nota '{tipo_nota_codice}' non trovato o non attivo"
            ),
            # Il codice l'ha scelto il client: e' un valore sbagliato, 400.
            codice_errore="E_PRATICA_VALIDATION", campo="tipo_nota_codice",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pratiche.note_pratiche (pratica_id, tipo_nota_id, contenuto)
                   VALUES (%s, %s, %s) RETURNING id""",
                [pratica_id, tipo_nota_id, contenuto],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_NOTA_INSERT",
                message="Errore inserimento nota (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna il contenuto di una nota (ownership check su pratica_id).
    def update_nota_pratica(
        self, nota_id: int, pratica_id: int, contenuto: str,
    ) -> bool:
        sql = """
            UPDATE pratiche.note_pratiche
            SET contenuto = %s
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contenuto, nota_id, pratica_id])
            return cursor.rowcount > 0

    # Scopo: Elimina una nota (ownership check su pratica_id).
    def delete_nota_pratica(self, nota_id: int, pratica_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.note_pratiche
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [nota_id, pratica_id])
            return cursor.rowcount > 0

    # -- ALLEGATI PRATICHE -----------------------------------------------

    _ALLEGATO_SELECT = """
        a.id, a.pratica_id, a.tipo_allegato_id,
        ta.codice_interno AS tipo_allegato_codice,
        ta.descrizione AS tipo_allegato_descrizione,
        a.nome_file, a.percorso, a.mime_type, a.dimensione,
        a.allegato_padre_id, a.data_insert, a.user_insert
    """

    _ALLEGATO_JOINS = """
        JOIN config.tipi_allegato ta ON ta.id = a.tipo_allegato_id
    """

    # Scopo: Restituisce gli allegati di una pratica con tipo allegato display.
    def list_allegati_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._ALLEGATO_SELECT}
            FROM pratiche.allegati_pratiche a
            {self._ALLEGATO_JOINS}
            WHERE a.pratica_id = %s
            ORDER BY a.data_insert DESC, a.id DESC
        """  # noqa: S608 — _ALLEGATO_SELECT/_JOINS costanti di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Crea un record allegato (senza upload file — solo metadati).
    # Il file verra' caricato in una fase successiva.
    def create_allegato_pratica(
        self, pratica_id: int, tipo_allegato_codice: str,
        nome_file: str, *, percorso: str | None = None,
        mime_type: str | None = None, dimensione: int | None = None,
        allegato_padre_id: int | None = None,
    ) -> int:
        # Risolve tipo_allegato_id prima dell'INSERT per errore chiaro
        tipo_allegato_id = resolve_config_id_by_codice_interno(
            "config.tipi_allegato",
            tipo_allegato_codice,
            etichetta="Tipo allegato",
            not_found_message=(
                f"Tipo allegato '{tipo_allegato_codice}' non trovato o non attivo"
            ),
            # Il codice l'ha scelto il client: e' un valore sbagliato, 400.
            codice_errore="E_PRATICA_VALIDATION", campo="tipo_allegato_codice",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pratiche.allegati_pratiche (
                       pratica_id, tipo_allegato_id, nome_file,
                       percorso, mime_type, dimensione, allegato_padre_id
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                [pratica_id, tipo_allegato_id, nome_file,
                 percorso, mime_type, dimensione, allegato_padre_id],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_ALLEGATO_INSERT",
                message="Errore inserimento allegato (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Elimina un allegato (ownership check su pratica_id).
    # Gli allegati sono immutabili (no update), solo delete per rimozione.
    def delete_allegato_pratica(self, allegato_id: int, pratica_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.allegati_pratiche
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [allegato_id, pratica_id])
            return cursor.rowcount > 0

    # -- CALCOLI TEMPO ---------------------------------------------------

    # Scopo: Restituisce i calcoli tempo di una pratica arricchiti con stato_tempo live.
    # Usa LEFT JOIN LATERAL su fn_valuta_tempo_esecuzione_da_a per calcolare
    # giorni_rimanenti e stato_tempo (OK/WARNING/CRITICO/SFORATO) in tempo reale.
    def list_calcoli_tempo(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT ct.id, ct.pratica_id, ct.flusso_da_id, ct.flusso_a_id,
                   ct.formula_tempo_id, ct.data_inizio_calcolo, ct.data_fine_calcolo,
                   ct.giorni_lordi, ct.giorni_sospensione, ct.giorni_netti,
                   ct.giorni_formula, ct.sforato,
                   v.giorni_rimanenti, v.stato_tempo
            FROM pratiche.calcoli_tempo ct
            LEFT JOIN LATERAL pratiche.fn_valuta_tempo_esecuzione_da_a(
                ct.pratica_id, ct.flusso_da_id, ct.flusso_a_id
            ) v ON true
            WHERE ct.pratica_id = %s
            ORDER BY ct.data_inizio_calcolo, ct.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # -- FORMULE TEMPO -----------------------------------------------------

    # Scopo: Restituisce le formule tempo attive per un tipo prestazione.
    def list_formule_tempo(self, tipo_prestazione_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT ft.id, ft.tipo_prestazione_id,
                   ft.template_flusso_da_id, ft.template_flusso_a_id,
                   ft.giorni_esecuzione, ft.giorni_warning, ft.giorni_critico,
                   ft.attivo, ft.descrizione, ft.meta
            FROM pratiche.formule_tempo ft
            WHERE ft.tipo_prestazione_id = %s AND ft.attivo = true
            ORDER BY ft.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_prestazione_id])
            return rows_to_list(cursor)

    # -- RISOLUZIONE STATO -----------------------------------------------

    # Scopo: Risolve l'ID di uno stato da codice_interno su una tabella config.
    # Metodo generico usato dai wrapper resolve_stato_pratica / resolve_stato_flusso.
    # `codice_errore`/`campo`: per un codice scelto dal CLIENT (vedi il BB).
    def _resolve_stato(
        self, tabella: str, codice_interno: str, etichetta: str,
        *, codice_errore: str = "E_CONFIG_MANCANTE", campo: str | None = None,
    ) -> int:
        return resolve_config_id_by_codice_interno(
            tabella,
            codice_interno,
            etichetta=f"Stato {etichetta}",
            not_found_message=(
                f"Stato {etichetta} '{codice_interno}' non trovato in {tabella}"
            ),
            codice_errore=codice_errore,
            campo=campo,
        )

    # Scopo: Risolve l'ID di uno stato pratica da codice_interno.
    def resolve_stato_pratica(
        self, codice_interno: str,
        *, codice_errore: str = "E_CONFIG_MANCANTE", campo: str | None = None,
    ) -> int:
        return self._resolve_stato(
            "config.stati_pratiche", codice_interno, "pratica",
            codice_errore=codice_errore, campo=campo,
        )

    # Scopo: Risolve l'ID di uno stato flusso da codice_interno.
    def resolve_stato_flusso(
        self, codice_interno: str,
        *, codice_errore: str = "E_CONFIG_MANCANTE", campo: str | None = None,
    ) -> int:
        return self._resolve_stato(
            "config.stati_flussi_pratiche", codice_interno, "flusso",
            codice_errore=codice_errore, campo=campo,
        )

    # Scopo: Risolve l'ID di una priorita' pratica da codice_interno
    #        (default NORMALE in crea_pratica — mai id hardcodato).
    def resolve_priorita_pratica(self, codice_interno: str) -> int:
        return self._resolve_stato("config.priorita_pratiche", codice_interno, "priorita")

    # -- HANDLER KEY -----------------------------------------------------

    # Scopo: Recupera l'handler_key dal template flusso (via handler_flussi).
    def get_handler_key(self, template_flusso_id: int) -> str | None:
        sql = """
            SELECT hf.handler_key
            FROM pratiche.template_flussi tf
            JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
            WHERE tf.id = %s AND hf.attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            row = cursor.fetchone()
        if not row:
            return None
        return str(row[0])

    # Scopo: Recupera handler_key e handler_params dal template flusso.
    # Restituisce entrambi per il dispatch: la key per il lookup nel registry,
    # i params per la configurazione statica passata all'handler.
    def get_handler_info(self, template_flusso_id: int) -> tuple[str, dict[str, Any]] | None:
        sql = """
            SELECT hf.handler_key, tf.handler_params
            FROM pratiche.template_flussi tf
            JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
            WHERE tf.id = %s AND hf.attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            row = cursor.fetchone()
        if not row:
            return None
        return str(row[0]), coerce_jsonb_dict(row[1])

    # Scopo: Binding handler legati a un EVENTO di flusso (template_flussi_handler_eventi).
    # Generalizza il dispatch oltre l'avvio: per (template, evento) restituisce gli
    # handler attivi il cui esito_richiesto combacia con l'esito effettivo (NULL =
    # qualsiasi esito), ordinati per sequenza. Lista di (handler_key, handler_params).
    def get_handler_eventi(
        self, template_flusso_id: int, evento: str, esito: str | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        sql = """
            SELECT hf.handler_key, tfhe.handler_params
            FROM pratiche.template_flussi_handler_eventi tfhe
            JOIN pratiche.handler_flussi hf ON hf.id = tfhe.handler_id
            WHERE tfhe.template_flusso_id = %s
              AND tfhe.evento = %s
              AND tfhe.attivo = true
              AND hf.attivo = true
              AND (tfhe.esito_richiesto IS NULL OR tfhe.esito_richiesto = %s)
            ORDER BY tfhe.sequenza, tfhe.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id, evento, esito])
            rows = cursor.fetchall()
        return [(str(r[0]), coerce_jsonb_dict(r[1])) for r in rows]

    # -- TIPO PRESTAZIONE ------------------------------------------------

    # Scopo: Legge pre_attivazione e post_attivazione dal tipo prestazione.
    # Usato dal service per il guard di ammissibilita' pratica.
    def get_tipo_prestazione_attivazione(self, tipo_prestazione_id: int) -> dict[str, bool]:
        sql = """
            SELECT pre_attivazione, post_attivazione
            FROM pratiche.tipi_prestazione
            WHERE id = %s AND attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_prestazione_id])
            row = cursor.fetchone()
        ErrorManager.require(
            row is not None,
            code="E_CONFIG_MANCANTE",
            message=f"Tipo prestazione {tipo_prestazione_id} non trovato o non attivo",
        )
        assert row is not None
        return {"pre_attivazione": bool(row[0]), "post_attivazione": bool(row[1])}

    # -- CODA LAVORO OPERATORE ------------------------------------------

    # Scopo: Restituisce la coda di lavoro di un operatore su tre livelli
    #        (ASSEGNATO, COMPETENZA, REPARTO) chiamando la funzione DB.
    # La fn resta l'unica fonte della coda; il wrapper aggiunge i display
    # fields doc_* (proiezione V10) sul documento agganciato al flusso in coda.
    def list_coda_lavoro(
        self,
        risorsa_umana_id: int,
        emittente_fiscale_id: int,
    ) -> list[dict[str, Any]]:
        # WITH ORDINALITY + ORDER BY: l'ordinamento e' PROPRIETA' della fn
        # (livello, priorita, scadenza, ...) e joinare la fn non lo garantisce
        # piu' contrattualmente — l'ordinale lo preserva senza duplicarne le
        # chiavi qui. La colonna `ordinality` viaggia nel payload ed e' inerte
        # per il FE.
        sql = f"""
            SELECT c.*,
                {_DOC_SORGENTE_SELECT}
            FROM pratiche.fn_coda_lavoro_operatore(%s, %s) WITH ORDINALITY c
            {_doc_sorgente_lateral("ps.pratica_id = c.pratica_id AND ps.flusso_id = c.flusso_id")}
            ORDER BY c.ordinality
        """  # noqa: S608 — _DOC_SORGENTE_SELECT costante e lateral con anchor letterale, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [risorsa_umana_id, emittente_fiscale_id])
            return rows_to_list(cursor)

    # -- PRENDI IN CARICO FLUSSO -----------------------------------------

    # Scopo: Assegna un flusso DA_ESEGUIRE all'operatore, verificando competenza.
    # Delega alla funzione DB che gestisce lock (FOR UPDATE) e validazione.
    # Ritorna True se assegnato, False se gia' assegnato allo stesso operatore.
    def prendi_in_carico_flusso(
        self,
        flusso_id: int,
        risorsa_umana_id: int,
    ) -> bool:
        sql = """
            SELECT pratiche.fn_prendi_in_carico_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id, risorsa_umana_id])
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_FLUSSO_PRESA_IN_CARICO",
                message="Errore presa in carico flusso",
            )
            assert row is not None
        return bool(row[0])

    # -- COMPETENZE FLUSSI -----------------------------------------------

    # Scopo: Restituisce le competenze flussi con display fields da JOIN.
    def list_competenze_flussi(self) -> list[dict[str, Any]]:
        sql = """
            SELECT cf.id, cf.template_flusso_id, cf.unita_organizzativa_id,
                   cf.risorsa_umana_id, cf.attivo,
                   tf.codice AS template_flusso_codice,
                   tf.descrizione AS template_flusso_descrizione,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   sog.ragione_sociale_completa AS risorsa_umana_display
            FROM pratiche.competenze_flussi cf
            JOIN pratiche.template_flussi tf ON tf.id = cf.template_flusso_id
            JOIN config.unita_organizzative uo ON uo.id = cf.unita_organizzativa_id
            JOIN anagrafiche.risorse_umane ru ON ru.id = cf.risorsa_umana_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti sog ON sog.id = sr.soggetto_id
            ORDER BY tf.codice, uo.descrizione, sog.ragione_sociale_completa
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Crea una competenza flusso e ritorna l'ID.
    def create_competenza_flusso(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.competenze_flussi (
                template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = [
            data["template_flusso_id"],
            data["unita_organizzativa_id"],
            data["risorsa_umana_id"],
            data.get("attivo", True),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_FLUSSO_COMPETENZA_INSERT",
                message="Errore inserimento competenza flusso (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Elimina una competenza flusso per ID.
    def delete_competenza_flusso(self, competenza_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.competenze_flussi
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [competenza_id])
            return cursor.rowcount > 0

    # -- VERIFICA STATO BA SOGGETTO (cross-schema) ----------------------

    # Scopo: Verifica se il soggetto ha un billing_account attivo per l'emittente.
    # Ritorna True se esiste un cliente il cui periodo contiene il giorno operativo.
    # Usato dal guard pre/post-attivazione in crea_pratica.
    # La query attraversa: clienti → billing_account → istanze_utilities.
    # ⭐ «Attivo» e' il PERIODO (C-8 di brief-db-cliente-manuale-uno-per-soggetto-
    #    e-utility, 2026-10-14), la misura del modello: la stessa di
    #    `ex_clienti_no_overlap_stesso_pdp`, `anagrafiche.fn_check_pdp_occupato`
    #    e `fn_clienti_stessa_chiave`. Il periodo lo deriva il DB
    #    (`trgfn_clienti_set_periodo`): AN e PR non ne hanno, un sospeso occupa.
    #    ⛔ Fino al 2026-10-15 si leggeva «`data_attivazione NOT NULL AND
    #    data_chiusura IS NULL`»: una chiusura con data futura valeva «non
    #    attivo» gia' oggi, e un'attivazione con data futura valeva «attivo».
    def ha_ba_attivo(self, soggetto_id: str, emittente_fiscale_id: int) -> bool:
        # Scope emittente via fn ufficiale sul BA: l'istanza NON ha un
        # emittente (la relazione vive su billing_account -> efba, fallback
        # gestore default incapsulato nella fn, che ritorna la PK reale
        # dell'EF — feedback_emittente_pk_vs_soggetto_ruolo).
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM anagrafiche.clienti cl
                JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
                JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
                WHERE iu.soggetto_id = %s::uuid
                  AND anagrafiche.fn_get_emittente_fiscale_pk(ba.id) = %s
                  AND cl.periodo @> script.fn_data_operativa()
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, emittente_fiscale_id])
            row = cursor.fetchone()
        return bool(row[0]) if row else False
