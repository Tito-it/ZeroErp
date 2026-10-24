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

import json
from typing import Any

from django.db import connection

from apps.config.sorgenti import SORGENTE_OFFERTA_COMMERCIALE
from apps.core.api.constants import DEFAULT_LIMIT
from apps.catalogo.db.catalogo_repository import CatalogoRepository
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    call_jsonb_fn,
    colonne_identita,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.righe_lista_mixin import RigheListaMixin
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.db._indirizzi_repo_mixin import IndirizziDocumentoRepositoryMixin
from apps.vendite.db._lineage_sintesi import unisci_sintesi_lineage


# Colonne jsonb delle tre tabelle scritte qui (testata, eccezioni, utility):
# dichiarate al BB `execute_dynamic_insert`/`execute_dynamic_update`, cosi' una
# STRINGA che vi arrivasse e' letta come testo JSON (regola Tid 2026-09-26) e
# non come uno scalare stringa jsonb.
# ⭐ 2026-09-26: qui vivevano `_ph_and_val`/`_build_insert`/`_build_update`,
#    copia locale della composizione dinamica (gemella di quella di
#    `contratti_repository`), ritirata a favore del BB core. Il loro filtro
#    `if col in data` SCARTAVA IN SILENZIO le chiavi fuori lista: ora e'
#    `RuntimeError` nel BB, e il contratto dell'operatore lo fa rispettare il
#    service (`validate_allowed_keys`, 400) prima di arrivare qui.
_JSONB_COLS: tuple[str, ...] = ("meta",)
# ⚠️ Il padre (`offerta_id`) delle INSERT figlie arriva dal PATH e si mette
#    per ULTIMO nel dict (`{**data, "offerta_id": ...}`): se `data` lo
#    portasse, vince il path — mai una riga scritta sotto un altro padre. Che
#    `data` non lo porti lo garantisce il service (le sue whitelist non lo
#    contengono).


# Whitelist ORDER BY per la lista offerte (SQL injection safe).
# Colonne che la ricerca libera SA cercare nella lista `vendite.offerte`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
_RICERCA_OFFERTE = RicercaFull(
    "vendite.offerte",
    (
        "codice", "ragione_sociale_completa", "ba_codice", "id_fiscale_univoco_cf_piva",
    ),
)

_ORDER_COLS_OFFERTE: dict[str, str] = {
    # Whitelist colonne sortable LISTA (SQL injection safe). Mappate sulla vista
    # canonica `vendite.vw_offerte_commerciali_lista` (alias `v`, DEF-8). Le
    # chiavi sono i `campo_sorgente` del catalogo 'vendite.offerte' che il FE
    # invia come sortField (`<ListaConfigurabile>` usa `:field="campo_sorgente"`).
    # `revisione_numero` volutamente ASSENTE: non ordinabile (decisione §7.3).
    "codice": "v.codice",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "utility_codice": "v.utility_codice",
    "utility_descrizione": "v.utility_descrizione",
    "listino_codice": "v.listino_codice",
    "validita_dal": "v.validita_dal",
    "validita_al": "COALESCE(v.validita_al, 'infinity'::date)",
    "data_emissione": "v.data_emissione",
    "stato_descrizione": "v.stato_descrizione",
    "data_accettazione": "v.data_accettazione",
    "data_rifiuto": "v.data_rifiuto",
    "data_annullamento": "v.data_annullamento",
    "data_insert": "v.data_insert",
    # Colonne lineage (Fase B): pratica + fase ordinabili (frontiera no).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}

# Le colonne DATA della whitelist: senza direzione indicata partono DESC (regola
# Tid 2026-09-02, `colonne_desc` di `sql_order_clause`). Coincidono con le date
# ordinabili del seed — lo verifica `test_liste_configurabili_seed` (test 10).
_ORDER_COLS_OFFERTE_DATA: frozenset[str] = frozenset({
    "validita_dal", "validita_al", "data_emissione", "data_accettazione",
    "data_rifiuto", "data_annullamento", "data_insert",
})


# Scopo: whitelist ORDER BY del tab «Revisioni» del drawer offerta (lista
#        `vendite.offerta_revisioni`, alias `v` su `vw_offerte_commerciali_lista`).
# ⛔ COSTANTE SEPARATA da `_ORDER_COLS_OFFERTE`, e `revisione_numero` NON va
#    aggiunto la': nella lista principale e' volutamente assente (§7.3). Qui
#    invece e' l'ordine naturale della catena.
# ⚠️ Chiavi = `campo_sorgente` della lista 90. Le colonne sono GEMELLE di
#    quelle dei preventivi (stessi codici `rev`/`data`), ma il campo sorgente
#    e' dell'offerta: `revisione_numero`, `data_emissione`.
# ⚠️ `data_emissione` e' NULL sulle bozze: il vuoto si ordina come il valore
#    minimo (`sql_order_direction`, decisione Tid 2026-07-19) — in coda nel
#    verso naturale DESC, in testa se l'operatore inverte.
# ⚠️ `codice` (colonna «numero») e `stato_descrizione` dal 2026-09-28
#    (§9.1 dello stesso brief), gemelle di quelle dei preventivi.
OFFERTA_REVISIONI_ORDER_COLUMNS: dict[str, str] = {
    "revisione_numero": "v.revisione_numero",
    "codice": "v.codice",
    "data_emissione": "v.data_emissione",
    "stato_descrizione": "v.stato_descrizione",
}

# Colonne DATA della whitelist qui sopra (ripiego DESC senza `order_dir`),
# confrontate col seed da `test_liste_configurabili_seed` (test 10).
OFFERTA_REVISIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_emissione"})

# === Costante LISTA (vista canonica DEF-8, 2026-06-03) ===
# La lista paginata legge dalla vista canonica self-contained
# `vendite.vw_offerte_commerciali_lista`, che espone i nomi CANONICI senza alias
# (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice) richiesti dal
# catalogo liste 'vendite.offerte', e materializza listino_codice,
# listino_versione_codice, valuta_codice, is_scaduta (prima JOIN/derivati nel
# repository). Nessun JOIN ulteriore qui: la vista basta. Il detail
# (`get_offerta`) usa la propria proiezione `_SELECT_COLS_OFFERTA` + JOIN.
_FROM_LISTA_OFFERTE = "FROM vendite.vw_offerte_commerciali_lista v"


_SELECT_COLS_OFFERTA = """
    o.id,
    o.uid,
    o.codice,
    o.emittente_fiscale_id,
    -- Denormalizzazione EF (pattern preventivi): il FE `EmittenteFiscaleField`
    -- in edit mode legge codice + ragione sociale dal record per costruire la
    -- option singola del Select disabled. Senza questi campi il display
    -- resta vuoto in modifica nonostante `emittente_fiscale_id` valorizzato.
    ef.codice           AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa
                        AS emittente_ragione_sociale,
    o.billing_account_id,
    -- soggetto_ruolo del cliente (BA): serve al FE per la gestione
    -- indirizzi documento (elenco anagrafico cascata).
    ba.soggetto_ruolo_id,
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
    o.valuta_id,
    v_val.codice             AS valuta_codice,
    v_val.descrizione        AS valuta_descrizione,
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
    LEFT JOIN config.valute v_val ON v_val.id = o.valuta_id
    -- LEFT JOIN col contratto VIVO generato dal push. Il FE usa
    -- contratto_id/numero per il dialog "gia' generato" e per il deep-link a
    -- ContrattoDrawer post-push.
    -- ⛔ Il filtro sui vivi NON e' facoltativo (brief-db-annullo-documento-con-
    --    legami R-5, 2026-10-11): `uq_contratti_offerta_id` vale sui soli
    --    contratti non abortiti, quindi un'offerta puo' avere un contratto
    --    annullato e uno vivo. Senza il filtro la riga dell'offerta si DUPLICA;
    --    con il filtro resta «0 o 1», ed e' lo stesso predicato dell'indice.
    LEFT JOIN vendite.contratti c ON c.offerta_id = o.id AND NOT c.is_abortito_snapshot
    -- Decode emittente fiscale: codice + ragione sociale del soggetto
    -- (nessun fallback a `emittenti_fiscali.descrizione`, rimosso col brief
    -- emittente-ragione-sociale-dal-soggetto). Pattern allineato a
    -- preventivi_repository per UX uniforme nei drawer (EmittenteFiscaleField
    -- in edit legge questi campi denormalizzati senza round-trip).
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
    a.is_composito           AS is_composito,
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
    e.meta,
    -- Stato approvazione prezzo L3 (migration 20260601-01): il FE mostra il
    -- badge PENDING/APPROVED/REJECTED sulla riga eccezione, come per contratti.
    e.stato_approvazione_prezzo,
    e.pratica_approvazione_prezzo_id,
    -- Aggregato componenti BoM persistiti per expansion FE (data-driven
    -- `ComponentiPanel`). NULL se l'eccezione non e' composita o non
    -- ha componenti attivi: il pannello salta il render.
    COALESCE(comp.componenti, '[]'::jsonb) AS componenti
"""


_FROM_JOINS_ECCEZIONE = """
    FROM vendite.offerte_commerciali_eccezioni e
    JOIN catalogo.articoli a ON a.id = e.articolo_id
    LEFT JOIN catalogo.unita_misura um ON um.id = e.uom_operativa_id
    LEFT JOIN LATERAL (
      SELECT jsonb_agg(
               jsonb_build_object(
                 'id',                  c.id,
                 'componente_id',       c.componente_id,
                 'componente_codice',   ca.codice,
                 'componente_descrizione', ca.descrizione,
                 'coeff_qta_snapshot',  c.coeff_qta_snapshot,
                 'quantita',            c.quantita,
                 'uom_operativa_id',    c.uom_operativa_id,
                 'uom_codice',          uc.codice,
                 'prezzo_unitario',     c.prezzo_unitario,
                 'iva_id',              c.iva_id,
                 'iva_codice',          ivc.codice,
                 'iva_aliquota',        ivc.aliquota_iva,
                 'origine_prezzo',      c.origine_prezzo,
                 'ordine',              c.ordine,
                 'attivo',              c.attivo
               )
               ORDER BY c.ordine NULLS LAST, c.id
             ) AS componenti
        FROM vendite.offerte_commerciali_eccezioni_componenti c
        JOIN catalogo.articoli ca ON ca.id = c.componente_id
        LEFT JOIN catalogo.unita_misura uc ON uc.id = c.uom_operativa_id
        LEFT JOIN config.iva ivc          ON ivc.id = c.iva_id
       WHERE c.eccezione_offerta_id = e.id
         AND c.attivo = TRUE
    ) comp ON TRUE
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


class OfferteRepository(ComponentiRepositoryMixin, IndirizziDocumentoRepositoryMixin):
    """Accesso DB a `vendite.offerte_commerciali` + eccezioni + utility 1:1.

    Specchio di `ContrattiRepository` per la testata, le eccezioni
    (mirror di `contratti_righe`), la utility 1:1 (mirror di
    `contratti_utilities`) e i componenti BoM su eccezione composita
    (mirror di `contratti_righe_componenti`, simmetria piena 2026-05-26).

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    (list/get/update/delete/purge) — vedi `_componenti_repo_mixin.py`.
    `init_componenti_eccezione` e `preview_componenti_eccezione` restano
    qui perche' chiamano fn DB specifiche dell'offerta.
    """

    _componenti_table_name = "vendite.offerte_commerciali_eccezioni_componenti"
    _componenti_fk_riga = "eccezione_offerta_id"

    # Configurazione mixin indirizzi documento.
    _indirizzi_table = "vendite.offerte_commerciali_indirizzi"
    _indirizzi_fk_documento = "offerta_id"
    _indirizzi_documento = SORGENTE_OFFERTA_COMMERCIALE

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
        solo_ultima_revisione: bool = True,
        auth_user_id: int | None = None,
    ) -> tuple[str, list[Any]]:
        # Filtri sulla vista canonica `vw_offerte_commerciali_lista` (alias `v`).
        # Tutti i campi consumati qui sono esposti dalla vista — nessun JOIN
        # ulteriore nel filter builder.
        wheres: list[str] = []
        params: list[Any] = []
        # Scope emittente (defense-in-depth applicativa, stesso calco di
        # preventivi e contratti — era l'unica lista di testata del dominio
        # senza, il B1 dell'analisi RLS; allineata il 2026-09-21). La vista e'
        # `security_invoker=on`: la RLS filtra gia', questo si somma (api.md
        # §"Scope emittente"). `v.emittente_fiscale_id` e' la PK reale →
        # convenzione `pk` (memoria feedback_emittente_pk_vs_soggetto_ruolo).
        add_emittente_scope_condition(
            wheres, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )
        if billing_account_id is not None:
            wheres.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if stato_codice_interno:
            wheres.append("v.stato_codice_interno = %s")
            params.append(stato_codice_interno)
        if utility_id is not None:
            wheres.append("v.utility_id = %s")
            params.append(utility_id)
        if listino_id is not None:
            wheres.append("v.listino_id = %s")
            params.append(listino_id)
        if validita_dal_min:
            wheres.append("v.validita_dal >= %s")
            params.append(validita_dal_min)
        if validita_dal_max:
            wheres.append("v.validita_dal <= %s")
            params.append(validita_dal_max)
        add_ricerca_full_condition(wheres, params, search, _RICERCA_OFFERTE)
        # Filtro ultima revisione (mirror preventivi): di default mostra solo la
        # revisione non rimpiazzata per lineage. Quando false, storico completo.
        #
        # ⛔ ERA `is_attiva IS TRUE`, e il commento di allora dichiarava il difetto
        #    senza vederlo: «predicato: stato NOT IN ('SUPERATA','ANNULLATA')».
        #    Sono DUE domande in un flag solo — *superata* e' una posizione nella
        #    catena delle revisioni, *annullata* e' uno STATO — e in AND non si
        #    separano piu'. Conseguenza identica ai preventivi: il filtro di stato
        #    «Annullata» non poteva restituire niente.
        #    (brief-db-revisione-attiva-due-domande, 2026-08-28)
        if solo_ultima_revisione:
            wheres.append("v.is_superata IS FALSE")
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
        solo_ultima_revisione: bool = True,
        order_by: str = "data_insert",
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        auth_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        # ⛔ Ordinamento dal BB `sql_order_clause` (2026-09-26). La copia a mano
        #    che c'era («tutto cio' che non e' ASC e' DESC») trasformava in DESC
        #    qualunque direzione estranea, e inchiodava lo spareggio `v.id` a
        #    DESC anche ordinando ASC. Ora: direzione estranea = `ValueError`,
        #    NULL come valore minimo, spareggio allineato al verso. Il service
        #    ha gia' validato colonna e direzione col codice di dominio
        #    (`validate_order_by`); il BB rifiuta comunque un `order_by` fuori
        #    whitelist (`colonna_ordinamento`).
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_OFFERTE, default="v.data_insert",
            default_desc=True, colonne_desc=_ORDER_COLS_OFFERTE_DATA,
            tiebreak="v.id",
        )
        where_clause, params = self._build_offerte_filters(
            billing_account_id=billing_account_id,
            stato_codice_interno=stato_codice_interno,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            search=search,
            solo_ultima_revisione=solo_ultima_revisione,
            auth_user_id=auth_user_id,
        )
        sql = f"""
            SELECT v.*
              {_FROM_LISTA_OFFERTE}
              {where_clause}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = rows_to_list(cursor)

        # Le colonne del grafo dalla sintesi, per le chiavi della pagina
        # (brief-db-lineage-seminata-per-chiave B1): la vista non le porta piu'.
        unisci_sintesi_lineage(results, tipo_codice_interno=SORGENTE_OFFERTA_COMMERCIALE)
        return results

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
        solo_ultima_revisione: bool = True,
        auth_user_id: int | None = None,
    ) -> int:
        where_clause, params = self._build_offerte_filters(
            billing_account_id=billing_account_id,
            stato_codice_interno=stato_codice_interno,
            utility_id=utility_id,
            listino_id=listino_id,
            validita_dal_min=validita_dal_min,
            validita_dal_max=validita_dal_max,
            search=search,
            solo_ultima_revisione=solo_ultima_revisione,
            auth_user_id=auth_user_id,
        )
        sql = f"""
            SELECT COUNT(*)
              {_FROM_LISTA_OFFERTE}
              {where_clause}
        """
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
                """,
                [offerta_id],
            )
            return row_to_dict(cursor)

    # Scopo: Contesto minimo richiesto dal motore documentale (mirror di
    #        `PreventiviRepository.get_for_documento_generation` /
    #        `ContrattiRepository`) per generare un documento dall'offerta:
    #        `id`, `uid` (UUID stringa -> `documenti_generati.sorgente_uid`),
    #        `emittente_fiscale_id` (colonna nativa NOT NULL su
    #        `vendite.offerte_commerciali`, denormalizzata). Niente JOIN:
    #        lettura diretta. Ritorna None se id inesistente.
    def get_for_documento_generation(
        self, offerta_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                uid::text AS uid,
                emittente_fiscale_id
              FROM vendite.offerte_commerciali
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(offerta_id)])
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

    # Scopo: Crea una testata offerta. Lo stato non si scrive (non e' in
    #        whitelist): lo mette il DB, lo stato iniziale del vocabolario
    #        (`script.trgfn_doc_stato_iniziale`).
    #        Il `codice` arriva dal payload: la generazione automatica via
    #        sistema_codici (step 5 brief DB) non e' ancora cablata.
    # Colonne scrivibili in create (whitelist). Le immutabili (`uid`, audit,
    # data_*` di transizione) restano fuori e non sono accettate dal pattern.
    # `codice` escluso da Step 5 (2026-05-25): generato dal trigger DB
    # `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT); il repository
    # non lo tocca, defense-in-depth applicativa.
    TESTATA_CREATE_COLUMNS: frozenset[str] = frozenset({
        "emittente_fiscale_id",
        "billing_account_id",
        "istanza_utility_id",
        "utility_id",
        "listino_id",
        "listino_versione_id",
        "valuta_id",
        "valore_variazione_globale",
        "tipo_variazione_globale",
        "validita_dal",
        "validita_al",
        "revisione_numero",
        "revisione_padre_id",
        "meta",
    })

    # Colonne aggiornabili in update (sotto-set di create senza chiavi
    # gestionali: `codice`, `stato_doc_offerta_id`, `revisione_*`).
    # `valuta_id`: snapshot fissato al CREATE, immutabile in update (simmetrico
    # a `vendite.preventivi`; eventuale lock applicativo a discrezione del DB).
    TESTATA_UPDATE_COLUMNS: frozenset[str] = frozenset({
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
    })

    # ⛔ Whitelist RIGIDA (BB): una chiave fuori `TESTATA_CREATE_COLUMNS` e'
    #    `RuntimeError`, non piu' uno scarto silenzioso (2026-09-26).
    def create_offerta(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "vendite.offerte_commerciali", data,
            allowed=self.TESTATA_CREATE_COLUMNS, jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna testata offerta. `codice`/`uid`/`stato_doc_offerta_id`
    #        immutabili tramite questo metodo (per lo stato c'e' update_stato).
    def update_offerta(self, offerta_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "vendite.offerte_commerciali", offerta_id, data,
            allowed=self.TESTATA_UPDATE_COLUMNS, jsonb=_JSONB_COLS,
        )

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
                """,
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
                """,
                [eccezione_id],
            )
            return row_to_dict(cursor)

    # Colonne scrivibili eccezione: in create includono `articolo_id`/
    # `tipo_eccezione` (immutabili dopo INSERT), assenti da
    # `ECCEZIONE_UPDATE_COLUMNS` (in update sono `RuntimeError`, non scartate). `offerta_id` NON e' qui: arriva dall'URL
    # e lo aggiunge `create_eccezione`.
    ECCEZIONE_CREATE_COLUMNS: frozenset[str] = frozenset({
        "articolo_id",
        "tipo_eccezione",
        "tipo_erogazione",
        "fonte_quantita_attesa",
        "periodicita",
        "generazione_canone",
        "competenza_canone",
        "prezzo_unitario",
        # ⛔ Niente `quantita`: la calcola il DB (`trgfn_qta_from_operativa`).
        "qta_operativa",
        "uom_operativa_id",
        "factor_to_base",
        "ordine",
        "attivo",
        "meta",
        # Approvazione prezzo L3 (migration 20260601-01, simmetria contratti_righe).
        "stato_approvazione_prezzo",
        "pratica_approvazione_prezzo_id",
    })

    ECCEZIONE_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "tipo_erogazione",
        "fonte_quantita_attesa",
        "periodicita",
        "generazione_canone",
        "competenza_canone",
        "prezzo_unitario",
        "qta_operativa",
        "uom_operativa_id",
        "factor_to_base",
        "ordine",
        "attivo",
        "meta",
        # Approvazione prezzo L3: aggiornabili dal workflow approvazioni
        # (`_update_riga_offerta`) e dal gate (REJECTED/meta motivazione).
        "stato_approvazione_prezzo",
        "pratica_approvazione_prezzo_id",
    })

    # Scopo: Inserisce un'eccezione offerta. I 5 CHECK constraint DB
    #        (chk_offerte_eccezioni_*) validano coerenza prezzo/canone/
    #        fonte/erogazione/qta — qui solo passaggio colonne whitelisted.
    def create_eccezione(self, offerta_id: int, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "vendite.offerte_commerciali_eccezioni",
            {**data, "offerta_id": offerta_id},
            allowed={"offerta_id", *self.ECCEZIONE_CREATE_COLUMNS},
            jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna un'eccezione offerta sul subset mutabile (articolo_id
    #        e tipo_eccezione immutabili — un cambio = delete+create).
    def update_eccezione(self, eccezione_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "vendite.offerte_commerciali_eccezioni", eccezione_id, data,
            allowed=self.ECCEZIONE_UPDATE_COLUMNS, jsonb=_JSONB_COLS,
        )

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
    # Componenti BoM su eccezione composita (mirror contratti_righe_componenti)
    # =================================================================
    # CRUD singoli (list/get/update/delete/purge) ereditato da
    # `ComponentiRepositoryMixin`. Init e preview chiamano fn DB specifiche
    # dell'offerta:
    #   - vendite.fn_offerta_eccezione_componenti_init(eccezione_id,
    #       emittente_sr_id, data_riferimento, componenti_overrides::jsonb)
    #       -> integer (n. componenti inseriti)
    #   - vendite.fn_offerta_eccezione_componenti_preview(articolo_id,
    #       uom_id, quantita_padre, data_riferimento, ba_id, utility_id,
    #       emittente_sr_id, classe_utenza_id) -> SETOF record

    # Scopo: Init componenti BoM per eccezione padre composita. Wrapper
    # `fn_offerta_eccezione_componenti_init`. La fn DB e' idempotente.
    def init_componenti_eccezione(
        self,
        *,
        eccezione_id: int,
        emittente_soggetto_ruolo_id: int,
        data_riferimento,
        componenti_overrides: dict[str, Any] | None = None,
    ) -> int:
        overrides_json: str | None
        if componenti_overrides is None:
            overrides_json = None
        else:
            overrides_json = json.dumps(
                {str(k): str(v) for k, v in componenti_overrides.items()},
            )
        sql = (
            "SELECT vendite.fn_offerta_eccezione_componenti_init("
            "%s, %s, %s, %s::jsonb)"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                eccezione_id, emittente_soggetto_ruolo_id, data_riferimento,
                overrides_json,
            ])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # Scopo: Preview componenti BoM per drawer eccezione offerta. Read-only
    # STABLE. Consumato dal FE per pre-popolare ComponentiDialog PRIMA del
    # save eccezione. Proiezione allineata a fn DB (mirror contratti).
    def preview_componenti_eccezione(
        self,
        *,
        articolo_id: str,
        uom_id: int | None,
        quantita_padre,
        data_riferimento,
        ba_id: int | None,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
        # Proiezione allineata al RETURNS TABLE della fn DB
        # `fn_offerta_eccezione_componenti_preview` (rev 2026-05-27, modello
        # unificato: filtro sul flag di esposizione rimosso dal WHERE +
        # `obbligatorio`/esposizione esposti nella proiezione; dal 2026-10-01
        # `esposizione_in_fattura` e' il codice del modo, non un booleano). Shape
        # ora identica a `fn_contratto_riga_componenti_preview`: il
        # ComponentiDialog rende i badge "Obbligatorio" / "In fattura".
        sql = """
            SELECT articolo_componente_id,
                   componente_id,
                   componente_codice,
                   componente_descrizione,
                   coeff_qta_snapshot,
                   quantita_componente,
                   uom_id,
                   uom_codice,
                   iva_id,
                   prezzo_suggerito,
                   origine_prezzo,
                   resolver_error_reason,
                   obbligatorio,
                   esposizione_in_fattura
              FROM vendite.fn_offerta_eccezione_componenti_preview(
                  %s, %s, %s, %s, %s, %s, %s, %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                articolo_id, uom_id, quantita_padre, data_riferimento,
                ba_id, utility_id, emittente_soggetto_ruolo_id,
                classe_utenza_id,
            ])
            return rows_to_list(cursor)

    # Scopo: Lookup emittente_soggetto_ruolo_id a partire da emittente_fiscale_id.
    # Usato da `resolve_emittente_sr_id_for_testata` per derivare l'sr_id da
    # passare alle fn DB componenti. Mirror di `ContrattiRepository`.
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali "
                "WHERE id = %s",
                [fiscale_id],
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    # Scopo: Articolo composito (delega a catalogo). Usato dai service di
    # dominio per decidere se invocare `init_componenti_eccezione` post-INSERT.
    def is_articolo_composito(self, articolo_id: str) -> bool:
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Contesto pratica APPROVAZIONE_PREZZO derivato dall'offerta
    #        (emittente + soggetto + soggetto_ruolo del BA). Mirror di
    #        `ContrattiRepository.resolve_contesto_pratica`. Usato dal workflow
    #        L3 (`approvazioni_prezzo_service.crea_richiesta_approvazione_offerta`)
    #        per creare la pratica. Ritorna None se offerta inesistente.
    def resolve_contesto_pratica(self, offerta_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                o.emittente_fiscale_id,
                sr.soggetto_id::text AS soggetto_id,
                ba.soggetto_ruolo_id,
                -- Il cliente a grana fine della pratica (D-9 di
                -- brief-db-istanza-nasce-col-ba): il BA del documento.
                ba.id AS billing_account_id
            FROM vendite.offerte_commerciali o
            JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
            JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            WHERE o.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [offerta_id])
            return row_to_dict(cursor)

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
                """,
                [offerta_id],
            )
            return row_to_dict(cursor)

    # Colonne scrivibili utility (create con istanza_utility_id/utility_id,
    # update senza — immutabili: cambio = delete+create).
    UTILITY_CREATE_COLUMNS: frozenset[str] = frozenset({
        "istanza_utility_id",
        "utility_id",
        "istanza_dati_precontrattuali_id",
        "tipo_utenza_id",
        "classe_utenza_id",
        "param_1_num",
        "param_2_txt",
        "meta",
    })

    UTILITY_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "istanza_dati_precontrattuali_id",
        "tipo_utenza_id",
        "classe_utenza_id",
        "param_1_num",
        "param_2_txt",
        "meta",
    })

    # Scopo: Crea il record utility 1:1 (UNIQUE offerta_id; un INSERT
    #        duplicato fallisce con violazione UNIQUE → mappato dal service).
    def create_utility(self, offerta_id: int, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "vendite.offerte_commerciali_utilities",
            {**data, "offerta_id": offerta_id},
            allowed={"offerta_id", *self.UTILITY_CREATE_COLUMNS},
            jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna il record utility sul subset mutabile (istanza_utility_id
    #        e utility_id NON modificabili: cambiano solo eliminando+ricreando
    #        l'offerta, come per il contratto).
    def update_utility(self, utility_row_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "vendite.offerte_commerciali_utilities", utility_row_id, data,
            allowed=self.UTILITY_UPDATE_COLUMNS, jsonb=_JSONB_COLS,
        )

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

    # Scopo: La COPPIA della fornitura sulla testata (cliente, istanza,
    #        utility): serve a sapere se un aggiornamento la cambia, perche'
    #        allora la scheda di fornitura la rifa' il DB (D-5 di
    #        brief-db-indirizzi-documento-seguono-il-cliente). None se
    #        l'offerta non e' visibile.
    def get_coppia(self, offerta_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT o.billing_account_id, o.istanza_utility_id, o.utility_id"
                "  FROM vendite.offerte_commerciali o WHERE o.id = %s",
                [offerta_id],
            )
            return row_to_dict(cursor)

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
    #          - overlap sulla quintupla (BA, istanza, utility, ambito,
    #            validita): se esiste un contratto sovrapposto non abortito e
    #            `chiudi_esistente` e' False -> E_CONTRATTO_OVERLAP_ESISTENTE
    #            (caso B); se True -> chiude il contratto esistente per
    #            successione (caso C) poi crea il nuovo (rev4 DB 2026-05-31).
    #
    #        Ritorna l'id del nuovo contratto DRAFT.
    def push_a_contratto(
        self,
        offerta_id: int,
        pratica_id: int | None = None,
        chiudi_esistente: bool = False,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_push_offerta_a_contratto(%s, %s, %s)",
                [offerta_id, pratica_id, chiudi_esistente],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return int(row[0])

    # Scopo: Genera un ordine DRAFT dall'offerta ACCETTATA col verbo DB
    #        `vendite.fn_genera_ordine_da_offerta` (gemello del push al
    #        contratto, brief-db-offerta-emissione-ed-erogazione I-D2): stato,
    #        documenti vivi, righe, testata con la provenienza, indirizzo di
    #        default e righe espanse coi prezzi negoziati, in una transazione.
    #        Ritorna l'id dell'ordine.
    def genera_ordine(self, offerta_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_genera_ordine_da_offerta(%s)",
                [int(offerta_id)],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return int(row[0])

    # Scopo: Ritorna il contratto (non abortito) la cui validita' si sovrappone
    #        a quella che il push genererebbe per questa offerta, riusando la
    #        fn di dominio contratti `vendite.fn_contratto_sovrapposto` (brief
    #        successione §3.2.1). Read-only: alimenta il dialog FE di
    #        successione (contratto in conflitto + validita') senza tentare
    #        l'INSERT. `ambito` = 'COMMODITY' (default colonna usato dall'INSERT
    #        del push). Ritorna None se nessun overlap.
    def get_contratto_sovrapposto(self, offerta_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.numero, c.valido_dal, c.valido_al
                  FROM vendite.offerte_commerciali o
                  JOIN vendite.contratti c
                    ON c.id = vendite.fn_contratto_sovrapposto(
                           o.billing_account_id,
                           o.istanza_utility_id,
                           o.utility_id,
                           'COMMODITY',
                           o.validita_dal,
                           o.validita_al
                       )
                 WHERE o.id = %s
                """,
                [offerta_id],
            )
            return row_to_dict(cursor)

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

    # Scopo: Lista PAGINATA della catena revisioni dell'offerta passata (lista
    #        `vendite.offerta_revisioni`): tutte le righe con la sua stessa
    #        `revisione_radice_id` (l'id della rev.1), default
    #        `revisione_numero` ASC. Legge la vista canonica
    #        `vw_offerte_commerciali_lista`: `is_attiva` e `stato_descrizione`
    #        ci sono gia'.
    # ⭐ La catena e' un fatto della RIGA, fissato alla nascita (decisione di
    #    Tid del 2026-09-27, brief-db-liste-datatable-grezze §3.2): la radice la
    #    deriva il trigger BEFORE INSERT dal padre ed e' immutabile
    #    (E_OFFERTA_REVISIONE_CATENA_IMMUTABILE). Si legge per UGUAGLIANZA, come
    #    `numero` sui preventivi.
    # ⛔ Fino al 2026-09-27 qui c'era una CTE RICORSIVA (risalita alla radice via
    #    `revisione_padre_id`, poi ridiscesa ai discendenti), rifatta a ogni
    #    apertura del tab e senza LIMIT: non paginabile se non contando la
    #    ricorsione due volte. Ritirata col seed della colonna.
    # ⚠️ Nessun filtro emittente, come sui preventivi: l'`emittente_fiscale_id`
    #    del tab lo legge solo il cancello di perimetro (`lista_emittente_param`
    #    della view). Una catena e' di un emittente solo per costruzione, e un
    #    filtro in piu' renderebbe un id sbagliato una lista vuota senza errore.
    def list_revisioni(
        self, offerta_id: int, *,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str | None = "revisione_numero", order_dir: str | None = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=OFFERTA_REVISIONI_ORDER_COLUMNS, default="v.revisione_numero",
            tiebreak="v.id",
            colonne_desc=OFFERTA_REVISIONI_SORT_COLONNE_DATA,
        )
        params: list[Any] = [offerta_id]
        from_where = (
            f"{_FROM_LISTA_OFFERTE} WHERE v.revisione_radice_id = ("  # noqa: S608 — frammento letterale del modulo, l'id come parametro
            "SELECT revisione_radice_id FROM vendite.offerte_commerciali WHERE id = %s)"
        )
        return fetch_paged_with_total(
            f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )


# =================================================================
# Righe dell'offerta come LISTA CONFIGURABILE (`vendite.offerta_righe`, 106)
# =================================================================

# Whitelist ORDER BY: i `campo_sorgente` `ordinabile = t` della lista 106,
# gemella campo per campo della 103 del contratto (brief-db-righe-esclusione-
# solo-non-si-vende §10.2), che la funzione espone con lo stesso nome.
_ORDER_COLS_RIGHE_OFFERTA: dict[str, str] = colonne_identita(
    "articolo_codice", "articolo_descrizione", "qta_operativa", "prezzo_finale",
    "override_prezzo", "uom_codice", "tipo_erogazione", "prezzo_listino", "origine",
)
# Le `ricercabile_full = t` del seed. `test_ricerca_full_seed` legge questa costante.
_RICERCA_RIGHE_OFFERTA = RicercaFull(
    "vendite.offerta_righe", ("articolo_codice", "articolo_descrizione"),
)


class OffertaRigheListaRepository(RigheListaMixin):
    """Le righe OPERATIVE di un'offerta come lista paginata (BB
    `RigheListaMixin`): le righe della versione operativa del listino con
    l'overlay delle eccezioni, piu' le aggiunte.

    ⭐ La sorgente e' la FUNZIONE `vendite.fn_offerta_righe_preview`, involucro
    del corpo comune col contratto (`vendite.fn_documento_righe_preview`):
    stesse colonne, stessi verbi (`azioni`), stesso motivo che spegne
    «Escludi» (`escludi_blocco_codice`). Il backend li trasporta, non li deduce.

    ⚠️ Stesse scelte della gemella `ContrattoRigheListaRepository`: ordine di
    partenza il codice articolo (le righe del listino non hanno un numero di
    riga), `riga_key` come spareggio, nessun filtro `attivo` (la funzione
    legge gia' le sole eccezioni attive), solo la PAGINA.
    """

    _righe_funzione = "vendite.fn_offerta_righe_preview"
    _righe_ordine_documento = "articolo_codice"
    _righe_chiave = "riga_key"
    _righe_solo_attive = False
    _righe_ordinamento = _ORDER_COLS_RIGHE_OFFERTA
    _righe_ricerca = _RICERCA_RIGHE_OFFERTA
