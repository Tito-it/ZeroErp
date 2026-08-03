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

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.db._indirizzi_repo_mixin import IndirizziDocumentoRepositoryMixin


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
#        La lista legge dalla vista `vendite.vw_contratti_lista` (alias `v`),
#        quindi le chiavi sono i `campo_sorgente` del catalogo liste
#        (`ui.lista_colonna` di 'vendite.contratti') che il FE invia come
#        sortField della DataTable. Niente alias `ba_*` su cliente/id_fiscale
#        (nomi canonici del soggetto, lezione DEF-8).
_ORDER_COLS_CONTRATTI: dict[str, str] = {
    "numero": "v.numero",
    "data": "v.data",
    "valido_dal": "v.valido_dal",
    "valido_al": "COALESCE(v.valido_al, 'infinity'::date)",
    "ba_codice": "v.ba_codice",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "utility_codice": "v.utility_codice",
    "utility_descrizione": "v.utility_descrizione",
    "ambito": "v.ambito",
    "listino_codice": "v.listino_codice",
    "listino_versione_codice": "v.listino_versione_codice",
    "tipo_variazione_globale": "v.tipo_variazione_globale",
    "valore_variazione_globale": "v.valore_variazione_globale",
    "valuta_codice": "v.valuta_codice",
    "stato_descrizione": "v.stato_descrizione",
    # `stato_codice_interno`, `stato_codice` ed `emittente_fiscale_codice` sono
    # uscite il 2026-07-31: nessuna colonna del catalogo le usa come
    # `campo_sorgente` (le prime due sono tecniche — danno la severity al Tag di
    # stato, nel seed sono invisibili e `ordinabile=f`; la colonna Emittente
    # legge `emittente_ragione_sociale`). Una voce che nessuna colonna puo'
    # richiedere e' una capacita' irraggiungibile, non una riserva.
    "categoria_cliente_snapshot_codice": "v.categoria_cliente_snapshot_codice",
    "data_insert": "v.data_insert",
    "data_update": "v.data_update",
    # Colonne lineage (Fase B): pratica + fase ordinabili (frontiera no).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}


_SELECT_COLS_CONTRATTO = """
    c.id,
    c.uid,
    c.numero,
    c.emittente_fiscale_id,
    -- Denormalizzazione EF (pattern preventivi/offerte): il FE
    -- `EmittenteFiscaleField` in edit mode legge codice + descrizione dal
    -- record per costruire la option singola del Select disabled. Senza
    -- questi campi il display resta vuoto in modifica nonostante
    -- `emittente_fiscale_id` valorizzato.
    ef.codice           AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa
                        AS emittente_ragione_sociale,
    c.billing_account_id,
    -- soggetto_ruolo del cliente (BA): serve al FE per la gestione
    -- indirizzi documento (elenco anagrafico cascata).
    ba.soggetto_ruolo_id,
    srd.ragione_sociale_completa AS ba_ragione_sociale,
    ba.codice AS ba_codice,
    -- ID fiscale univoco del soggetto del BA (CF persona fisica o P.IVA).
    -- Esposto dalla vista `anagrafiche.vw_soggetti_ruoli_dettaglio`. Allinea
    -- offerte/preventivi: colonna visibile nella lista per
    -- ricerca/confronto rapido del cliente.
    srd.id_fiscale_univoco_cf_piva AS id_fiscale,
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
    sd.codice_interno AS stato_codice_interno,
    sd.codice AS stato_codice,
    sd.descrizione AS stato_descrizione,
    c.listino_id,
    l.codice AS listino_codice,
    l.descrizione AS listino_descrizione,
    c.listino_versione_id,
    lv.codice_versione AS listino_versione_codice,
    c.tipo_variazione_globale,
    c.valore_variazione_globale,
    c.categoria_cliente_id_snapshot,
    cc_snap.codice AS categoria_cliente_snapshot_codice,
    cc_snap.descrizione AS categoria_cliente_snapshot_descrizione,
    c.valuta_id,
    v_val.codice AS valuta_codice,
    v_val.descrizione AS valuta_descrizione,
    -- Corsia di instradamento della fatturazione (Fase B del brief emissione
    -- mirata): «questo contratto va fatturato subito». Modificabile solo
    -- prima del push in commessa (guard DB); in ATTIVO la whitelist di patch
    -- non lo ammette, quindi il FE lo mostra readonly da li' in poi.
    c.fatturazione_immediata,
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
    LEFT JOIN vendite.listini_versioni lv ON lv.id = c.listino_versione_id
    LEFT JOIN anagrafiche.categorie_clienti cc_snap ON cc_snap.id = c.categoria_cliente_id_snapshot
    LEFT JOIN config.valute v_val ON v_val.id = c.valuta_id
    -- Decode emittente fiscale (codice + ragione sociale) per la
    -- denormalizzazione richiesta da `EmittenteFiscaleField` in edit
    -- mode. Pattern allineato a preventivi/offerte. LEFT JOIN per safety,
    -- la colonna `emittente_fiscale_id` e' NOT NULL ma il join resta
    -- difensivo rispetto a eventuali emittenti soft-disabled.
    LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = c.emittente_fiscale_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
"""


_SELECT_COLS_RIGA = """
    r.id,
    r.contratto_id,
    r.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    a.is_composito AS is_composito,
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
    r.tipo_eccezione,
    r.stato_approvazione_prezzo,
    r.pratica_approvazione_prezzo_id,
    r.data_insert,
    r.user_insert,
    r.data_update,
    r.user_update,
    -- Aggregato componenti BoM persistiti per expansion FE (data-driven
    -- `ComponentiPanel`). Serve al ramo "senza_listino" (forma C): le righe
    -- AGGIUNTA bundle vivono in contratti_righe e qui non passavano per la
    -- preview, quindi senza questo aggregato l'expander non vedeva i figli.
    -- Pattern speculare a offerte_repository (`_FROM_JOINS_ECCEZIONE`).
    -- Default '[]' se la riga non e' composita o non ha componenti attivi:
    -- il pannello salta il render.
    COALESCE(comp.componenti, '[]'::jsonb) AS componenti
"""


_FROM_JOINS_RIGA = """
    FROM vendite.contratti_righe r
    JOIN catalogo.articoli a ON a.id = r.articolo_id
    LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_operativa_id
    LEFT JOIN LATERAL (
      SELECT jsonb_agg(
               jsonb_build_object(
                 'id',                     c.id,
                 'componente_id',          c.componente_id,
                 'componente_codice',      ca.codice,
                 'componente_descrizione', ca.descrizione,
                 'coeff_qta_snapshot',     c.coeff_qta_snapshot,
                 'quantita',               c.quantita,
                 'uom_operativa_id',       c.uom_operativa_id,
                 'uom_codice',             uc.codice,
                 'prezzo_unitario',        c.prezzo_unitario,
                 'iva_id',                 c.iva_id,
                 'iva_codice',             ivc.codice,
                 'iva_aliquota',           ivc.aliquota_iva,
                 'origine_prezzo',         c.origine_prezzo,
                 'ordine',                 c.ordine,
                 'attivo',                 c.attivo
               )
               ORDER BY c.ordine NULLS LAST, c.id
             ) AS componenti
        FROM vendite.contratti_righe_componenti c
        JOIN catalogo.articoli ca ON ca.id = c.componente_id
        LEFT JOIN catalogo.unita_misura uc ON uc.id = c.uom_operativa_id
        LEFT JOIN config.iva ivc          ON ivc.id = c.iva_id
       WHERE c.riga_contratto_id = r.id
         AND c.attivo = TRUE
    ) comp ON TRUE
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


class ContrattiRepository(ComponentiRepositoryMixin, IndirizziDocumentoRepositoryMixin):
    """Accesso DB a `vendite.contratti` + righe + utility 1:1.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    modello unificato (`contratti_righe_componenti`). I metodi specifici
    `init_componenti_riga` (chiama `fn_contratto_riga_componenti_init`)
    e `preview_componenti_riga` (chiama `fn_contratto_riga_componenti_preview`)
    sono definiti localmente.
    """

    # Configurazione mixin componenti.
    _componenti_table_name = "vendite.contratti_righe_componenti"
    _componenti_fk_riga = "riga_contratto_id"

    # Configurazione mixin indirizzi documento.
    _indirizzi_table = "vendite.contratti_indirizzi"
    _indirizzi_fk_documento = "contratto_id"
    _indirizzi_ambito = "CONTRATTI"
    _indirizzi_documento_table = "vendite.contratti"
    # Precontrattuale: istanza congelata in testata (vedi preventivi).
    _indirizzi_doc_istanza_column = "istanza_utility_id"

    # =================================================================
    # Lista e dettaglio testata
    # =================================================================

    # Scopo: Lista paginata contratti filtrabile per cliente/stato/utility/
    #        ambito + search su numero + intervallo validita' esplicito.
    #        Lo scope emittente (multi-face) viene applicato direttamente
    #        sulla colonna `c.emittente_fiscale_id` (post brief simmetria
    #        2026-05-26) via `script.fn_get_emittenti_scope_pk_ids`, allineato
    #        al pattern preventivi: NULL = nessun filtro (admin globale),
    #        ALL ELSE = whitelist degli EF visibili all'utente.
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
        auth_user_id: int | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS_CONTRATTI.get(order_by, _ORDER_COLS_CONTRATTI["data"])
        direction = sql_order_direction(order_dir)
        # `max_limit`: lista cap 200 (gia' via parse_list_params), export fino a
        # EXPORT_MAX_ROWS+1 per non troncare in silenzio (guard su COUNT reale).
        safe_limit = max(1, min(int(limit), max_limit))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if stato_doc_contratto_id is not None:
            conditions.append("v.stato_doc_contratto_id = %s")
            params.append(stato_doc_contratto_id)
        if utility_id is not None:
            conditions.append("v.utility_id = %s")
            params.append(utility_id)
        if ambito is not None:
            conditions.append("v.ambito = %s")
            params.append(ambito)
        if listino_id is not None:
            conditions.append("v.listino_id = %s")
            params.append(listino_id)
        # Filtro validita': un contratto e' nel periodo se [valido_dal,
        # valido_al] overlappa [data_da, data_a]. La vista non espone il
        # daterange `validita` (colonna generata sulla tabella base): il
        # predicato e' ricostruito in modo equivalente da valido_dal/al.
        # (valido_al NULL = validita' aperta verso il futuro.)
        if data_da is not None and data_a is not None:
            conditions.append(
                "(v.valido_dal <= %s::date"
                " AND (v.valido_al IS NULL OR v.valido_al >= %s::date))"
            )
            params.extend([data_a, data_da])
        elif data_da is not None:
            conditions.append("(v.valido_al IS NULL OR v.valido_al >= %s::date)")
            params.append(data_da)
        elif data_a is not None:
            conditions.append("v.valido_dal <= %s::date")
            params.append(data_a)
        # Filtro scadenza mese: contratti il cui ultimo giorno di validita'
        # (`valido_al`) cade nel mese indicato (formato YYYY-MM).
        if scadenza_mese is not None:
            conditions.append(
                "(v.valido_al IS NOT NULL"
                " AND v.valido_al >= %s::date"
                " AND v.valido_al < (%s::date + interval '1 month')::date)"
            )
            primo_mese = f"{scadenza_mese}-01"
            params.extend([primo_mese, primo_mese])
        if search:
            conditions.append("(v.numero ILIKE %s OR v.ragione_sociale_completa ILIKE %s)")
            like = f"%{search.strip()}%"
            params.extend([like, like])

        # Scope emittente (defense-in-depth applicativa). La vista
        # `vw_contratti_lista` e' `security_invoker=on`: la RLS della tabella
        # base `vendite.contratti` filtra gia' per emittente in scope a
        # livello DB. Questo filtro applicativo si somma (api.md §"Scope
        # emittente"). Array risolto UNA volta in Python dal BB condiviso; convenzione PK su
        # `emittenti_fiscali.id` (NON `_sr_ids` = soggetto_ruolo_id);
        # `v.emittente_fiscale_id` e' la PK (memoria
        # `feedback_emittente_pk_vs_soggetto_ruolo`).
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  FROM vendite.vw_contratti_lista v
                {where_clause}
                """,  # noqa: S608
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT v.*, s.codice_interno AS frontiera_tipo_codice
                  FROM vendite.vw_contratti_lista v
                  LEFT JOIN config.sorgenti s ON s.id = v.frontiera_tipo_id
                {where_clause}
                 ORDER BY {order_column} {direction}, v.id ASC
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

    # Scopo: Risolve la versione listino operativa per un listino, alla data.
    #        Replica la stessa regola applicata in `fn_contratto_righe_preview`
    #        (migration 20260516-04): ATTIVA/CHIUSA validità @ data_riferimento,
    #        BOZZA esclusa, ordinato per (ATTIVA prima). Lookup puro su
    #        `listini_versioni` — il caller decide se chiamarlo o se ha gia'
    #        lo snapshot dalla testata contratto (evita round-trip extra).
    #        Usato dal pricing gate L2 contratti per popolare
    #        `listino_versione_id_preferito` del resolver pricing v2 quando
    #        il contratto e' DRAFT (snapshot non fissato) → evita il drift
    #        cascata CATEGORIA quando il BA ha mappa categorie_clienti_listini
    #        su un listino diverso. Ritorna None se nessuna versione operativa.
    def get_listino_versione_attiva_alla_data(
        self, listino_id: int, data_riferimento: date,
    ) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT lv.id
                  FROM vendite.listini_versioni lv
                 WHERE lv.listino_id = %s
                   AND lv.attivo     = TRUE
                   AND lv.stato      IN ('ATTIVA', 'CHIUSA')
                   AND lv.validita  @> %s::date
                 ORDER BY (lv.stato = 'ATTIVA') DESC
                 LIMIT 1
                """,
                [listino_id, data_riferimento],
            )
            row = cursor.fetchone()
            if not row:
                return None
            return row[0]

    # Scopo: Restituisce il contesto minimo richiesto dal motore documentale
    #        per generare un documento da contratto: `id`, `uid` e
    #        `emittente_fiscale_id`. Post brief simmetria 2026-05-26 la
    #        colonna e' nativa NOT NULL su `vendite.contratti`: lettura
    #        diretta, niente piu' derivazione runtime via
    #        `anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.
    def get_for_documento_generation(
        self, contratto_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                c.id,
                c.uid::text AS uid,
                c.emittente_fiscale_id
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

    # Scopo: Restituisce il contesto pricing del contratto in forma compatta
    #        per il banner FE (refactor 2026-05-15, mutuato dal pattern
    #        preventivi `resolve_contesto_pricing`). Espone forma (con/senza
    #        listino), riferimento listino + versione (FISSATA se ATTIVO,
    #        CORRENTE se DRAFT), variazione globale, categoria cliente.
    #        Pura lettura: nessun side-effect. Restituisce None se contratto
    #        non esiste.
    def resolve_contesto_pricing_contratto(
        self, contratto_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            WITH cnt AS (
                SELECT c.id,
                       c.billing_account_id,
                       c.listino_id,
                       c.listino_versione_id,
                       c.tipo_variazione_globale,
                       c.valore_variazione_globale,
                       c.categoria_cliente_id_snapshot,
                       sd.codice_interno AS stato_codice_interno
                  FROM vendite.contratti c
                  JOIN config.stati_doc_contratti sd
                    ON sd.id = c.stato_doc_contratto_id
                 WHERE c.id = %s
            ),
            -- Versione listino: fissata se ATTIVO (qualunque stato,
            -- inclusa una CHIUSA post-attivazione perche' i prezzi
            -- snapshot restano fatturabili), altrimenti la versione
            -- OPERATIVA corrente per DRAFT — regola §6 brief 2026-05-16:
            -- attivo + stato IN ('ATTIVA','CHIUSA') + validita @> data.
            -- BOZZA esclusa: e' preparazione, non versione operativa.
            ver AS (
                SELECT lv.id, lv.codice_versione, lv.listino_id
                  FROM vendite.listini_versioni lv
                  JOIN cnt ON cnt.listino_id = lv.listino_id
                 WHERE lv.attivo = TRUE
                   AND (
                       (cnt.listino_versione_id IS NOT NULL
                            AND lv.id = cnt.listino_versione_id)
                       OR
                       (cnt.listino_versione_id IS NULL
                            AND lv.stato IN ('ATTIVA','CHIUSA')
                            AND lv.validita @> CURRENT_DATE)
                   )
                 ORDER BY (lv.stato = 'ATTIVA') DESC
                 LIMIT 1
            ),
            -- Versione operativa CORRENTE del listino oggi (drift detection
            -- FE 2.4 refactor-contratti-modalita): la versione ATTIVA del
            -- listino con validita' che include oggi. Serve per confrontare
            -- contro la versione FISSATA dal contratto e segnalare al banner
            -- se il listino ha evoluto post-attivazione contratto (il
            -- contratto resta sulla fissata, ma l'operatore vede che ne
            -- esiste una piu' recente). Per contratti DRAFT (no fissaggio)
            -- ver_corrente coincide con ver, quindi mai drift.
            ver_corrente AS (
                SELECT lv.id, lv.codice_versione
                  FROM vendite.listini_versioni lv
                  JOIN cnt ON cnt.listino_id = lv.listino_id
                 WHERE lv.attivo = TRUE
                   AND lv.stato = 'ATTIVA'
                   AND lv.validita @> CURRENT_DATE
                 LIMIT 1
            )
            SELECT
                cnt.id AS contratto_id,
                CASE WHEN cnt.listino_id IS NULL THEN 'senza_listino'
                     ELSE 'con_listino' END AS forma,
                cnt.stato_codice_interno,
                cnt.listino_id,
                l.codice AS listino_codice,
                l.descrizione AS listino_descrizione,
                COALESCE(cnt.listino_versione_id, ver.id) AS listino_versione_id,
                ver.codice_versione AS listino_versione_codice,
                -- True se il contratto e' ATTIVO con versione fissata: i prezzi
                -- non drifteranno con nuove versioni del listino.
                (cnt.listino_versione_id IS NOT NULL) AS listino_versione_fissata,
                -- Versione operativa CORRENTE del listino (drift detection):
                -- diversa dalla fissata se il listino e' stato aggiornato
                -- dopo l'attivazione del contratto. NULL se il listino non
                -- ha nessuna versione ATTIVA oggi (caso limite: listino
                -- senza versioni operative correnti). FE mostra Tag drift
                -- quando il contratto e' fissato e id differiscono.
                ver_corrente.id AS listino_versione_corrente_id,
                ver_corrente.codice_versione AS listino_versione_corrente_codice,
                (
                    cnt.listino_versione_id IS NOT NULL
                    AND ver_corrente.id IS NOT NULL
                    AND ver_corrente.id <> cnt.listino_versione_id
                ) AS drift_versione_listino,
                cnt.tipo_variazione_globale,
                cnt.valore_variazione_globale,
                COALESCE(cnt.categoria_cliente_id_snapshot, ba.categoria_cliente_id)
                    AS categoria_cliente_id,
                cc.codice AS categoria_cliente_codice,
                cc.descrizione AS categoria_cliente_descrizione
              FROM cnt
              LEFT JOIN anagrafiche.billing_account ba ON ba.id = cnt.billing_account_id
              LEFT JOIN vendite.listini l ON l.id = cnt.listino_id
              LEFT JOIN ver ON TRUE
              LEFT JOIN ver_corrente ON TRUE
              LEFT JOIN anagrafiche.categorie_clienti cc
                ON cc.id = COALESCE(
                    cnt.categoria_cliente_id_snapshot, ba.categoria_cliente_id
                )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contratto_id])
            return row_to_dict(cursor)

    # Scopo: Conta le eccezioni "bloccanti" (OVERRIDE / ESCLUSIONE) attive
    #        sul contratto. Usato dal service per impedire la rimozione del
    #        listino dalla testata: senza listino di riferimento, OVERRIDE
    #        e ESCLUSIONE perdono significato (refactor modalita 2026-05-15
    #        §3-bis-F). AGGIUNTA non blocca (resta valida senza listino).
    # Scopo: Conta le righe persistite attive (qualsiasi tipo_eccezione) di
    #        un contratto. Usato dal service per bloccare la modifica di
    #        `listino_id`, `tipo_variazione_globale`, `valore_variazione_globale`
    #        in stato DRAFT quando ci sono righe già caricate: cambiare il
    #        contesto pricing (listino o variazione globale) con eccezioni
    #        persistite causerebbe drift semantico silente (prezzi calcolati
    #        contro un riferimento diverso da quello che le righe assumevano).
    #        Pattern coerente con `count_eccezioni_bloccanti` ma generico:
    #        anche le AGGIUNTA su contratti senza listino contano.
    def count_righe_attive(self, contratto_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)::int
                  FROM vendite.contratti_righe
                 WHERE contratto_id = %s
                   AND attivo = TRUE
                """,
                [contratto_id],
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def count_eccezioni_bloccanti(
        self, contratto_id: int,
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tipo_eccezione, COUNT(*)::int
                  FROM vendite.contratti_righe
                 WHERE contratto_id = %s
                   AND attivo = TRUE
                   AND tipo_eccezione IN ('OVERRIDE', 'ESCLUSIONE')
                 GROUP BY tipo_eccezione
                """,
                [contratto_id],
            )
            counts = {"OVERRIDE": 0, "ESCLUSIONE": 0}
            for tipo, n in cursor.fetchall():
                counts[tipo] = int(n)
            return counts

    # Scopo: Creazione atomica del contratto via funzione madre DB.
    #        Obiettivo: fondere in UNA sola statement (vendite.fn_create_contratto)
    #        la generazione del numero (`fn_generate_codice`), l'INSERT testata
    #        (stato DRAFT risolto dalla fn) e l'eventuale INSERT utility 1:1.
    #        Perimetro: o tutto o rollback totale (contatore numero incluso) —
    #        niente piu' contratto orfano + numero consumato se la utility fallisce
    #        (fix analisi-fix-transazioni Classe A, finding #2; prima erano
    #        generate_numero + 2 INSERT separati in autocommit).
    #        La fn e' SECURITY INVOKER: RLS e scope emittente su contratti restano
    #        valutati come dal Python (vincolo invariante §2-bis).
    #
    #        Input:
    #          - testata: dict dei campi testata gia' validati/mappati dal service
    #            (`_build_create_data_testata`). La fn whitelista le chiavi note e
    #            risolve numero + stato DRAFT internamente (le chiavi `numero`/
    #            `stato_doc_contratto_id` NON vanno passate).
    #          - utility: dict della riga utility 1:1 (`_build_utility_data`) oppure
    #            None se il contratto non ha utility.
    #        Output: id del contratto creato.
    #        Serializzazione: json.dumps(..., default=str) per date/Decimal; `meta`
    #        e' un dict e resta oggetto JSON annidato (colonna jsonb).
    def create_contratto_atomico(
        self, *, testata: dict[str, Any], utility: dict[str, Any] | None,
    ) -> int:
        p_testata = json.dumps(testata, default=str)
        p_utility = json.dumps(utility, default=str) if utility else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT contratto_id, numero
                  FROM vendite.fn_create_contratto(%s::jsonb, %s::jsonb)
                """,
                [p_testata, p_utility],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna una testata contratto. `numero` immutabile (trigger
    #        lock_columns). stato_doc_contratto_id si aggiorna via
    #        update_stato() per leggibilita'.
    # Colonne scrivibili dalla PATCH di testata: ULTIMO dei tre anelli della
    # catena `_UPDATE_KEYS_TESTATA` → `_build_update_data_testata` → qui. Se una
    # colonna manca in uno qualsiasi dei tre, l'UPDATE non la scrive e nessuno
    # se ne accorge — e' il difetto costato un giro su `fatturazione_immediata`
    # (2026-07-27). Promossa da locale a costante di classe per renderla
    # ISPEZIONABILE dal guardrail `ContrattiCatenaUpdateTests`, che confronta i
    # tre anelli fra loro: senza un punto di accesso, il terzo anello non era
    # verificabile da un test.
    _UPDATE_WRITE_COLS: tuple[str, ...] = (
        "ambito",
        "valido_dal",
        "valido_al",
        "parent_contratto_id",
        "data",
        "listino_id",
        "tipo_variazione_globale",
        "valore_variazione_globale",
        "categoria_cliente_id_snapshot",
        # Corsia di instradamento (Fase B brief emissione mirata): il guard
        # DB respinge l'UPDATE dopo il push in commessa, e la whitelist di
        # patch per stato lo ammette solo in DRAFT.
        "fatturazione_immediata",
        "meta",
    )

    def update_contratto(self, contratto_id: int, data: dict[str, Any]) -> bool:
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in self._UPDATE_WRITE_COLS:
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

    # Scopo: Pre-check applicativo overlap per l'attivazione manuale del
    #        contratto (guard §3.3 brief refactor-overlap). Delega alla fn di
    #        dominio `vendite.fn_contratto_sovrapposto` (firma invariata,
    #        semantica DRAFT-escluso dal 2026-06-02) passando gli attributi del
    #        contratto STESSO. Ritorna l'incumbent ATTIVO sovrapposto
    #        (id + numero + validita') o None. Read-only: non tenta l'INSERT/
    #        UPDATE, serve solo a dare un messaggio che NOMINA il contratto in
    #        conflitto prima che l'EXCLUDE `ex_contratti_no_overlap` sollevi
    #        all'attivazione (defense-in-depth, l'EXCLUDE resta la difesa dura).
    #        Il contratto stesso (DRAFT in attivazione) non si auto-conflitta:
    #        la fn ignora i DRAFT.
    def get_contratto_sovrapposto(self, contratto_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT inc.id, inc.numero, inc.valido_dal, inc.valido_al
                  FROM vendite.contratti c
                  JOIN vendite.contratti inc
                    ON inc.id = vendite.fn_contratto_sovrapposto(
                           c.billing_account_id,
                           c.istanza_utility_id,
                           c.utility_id,
                           c.ambito,
                           c.valido_dal,
                           c.valido_al
                       )
                   -- Safeguard: se emetti() fosse invocato su un contratto gia'
                   -- ATTIVO (re-emit), la fn potrebbe restituire se stesso ->
                   -- escludo l'auto-match. Nel caso normale (contratto DRAFT in
                   -- attivazione) la fn ignora gia' i DRAFT, quindi e' un no-op.
                   AND inc.id <> c.id
                 WHERE c.id = %s
                """,
                [contratto_id],
            )
            return row_to_dict(cursor)

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

    # Scopo: Preview righe operative del contratto (standalone + bundle).
    #        Thin wrapper su vendite.fn_contratto_righe_preview (migration
    #        20260516-04). La funzione DB unifica in 4 parti:
    #          1a) Righe standalone dal listino (origine='DA_LISTINO' +
    #              overlay OVERRIDE/ESCLUSIONE da contratti_righe)
    #          1b) Bundle dal listino (padre composito + figli aggregati
    #              in componenti JSONB via listini_righe_componenti)
    #          2a) Eccezioni AGGIUNTA standalone (contratti_righe)
    #          2b) Eccezioni AGGIUNTA bundle (componenti da
    #              contratti_righe_componenti)
    #        Versione listino operativa: regola §6 brief 2026-05-16
    #        (attivo=TRUE + stato IN ('ATTIVA','CHIUSA') + validita @> data).
    #        Lo SQL inline precedente (UNION manuale) e' stato rimosso:
    #        ogni estensione di shape o logica vive ora in DB.
    def list_righe_preview(self, contratto_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_contratto_righe_preview(%s)",
                [contratto_id],
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

    # Scopo: Inserisce una riga contratto come eccezione tipizzata
    #        (refactor modalita 2026-05-15). `tipo_eccezione` NOT NULL nello
    #        schema; trigger DB chk_contrighe_prezzo_per_tipo_eccezione
    #        valida la coerenza prezzo_unitario per tipo. Trigger
    #        trgfn_contratti_righe_guard_aggiunta_fuori_listino blocca
    #        AGGIUNTA su articoli presenti nel listino di riferimento.
    def create_riga(self, contratto_id: int, data: dict[str, Any]) -> int:
        write_cols = (
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
            # Workflow L3 approvazione prezzo (simmetria preventivi_righe,
            # migrations DB 20260518-01/02). Popolati solo dal flusso L3
            # (gestisci_riga con richiesta_approvazione=True che viola L2):
            # nei flussi normali restano NULL.
            "stato_approvazione_prezzo",
            "pratica_approvazione_prezzo_id",
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
            # Workflow L3: la transizione PENDING -> APPROVED/REJECTED e
            # l'aggancio della pratica passano da qui (allowlist trigger
            # `trgfn_contratti_righe_guard_pending` ammette workflow + meta
            # + audit, blocca ogni altra modifica struttura su righe PENDING).
            "stato_approvazione_prezzo",
            "pratica_approvazione_prezzo_id",
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

    # Scopo: Lookup soggetto_ruolo_id dell'emittente fiscale. Thin delegate
    # cross-dominio (Fase H residue 2026-05-14): implementazione in
    # `apps.anagrafiche.db.emittenti_fiscali_repository.EmittentiFiscaliRepository.get_sr_id_by_fiscale_id`.
    # I caller `contratti_service` continuano a usare `self._repo.X` (no
    # churn lato caller + mock test backward-compat).
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository().get_sr_id_by_fiscale_id(fiscale_id)

    # Scopo: Deriva i campi di contesto pratica (emittente_fiscale_id +
    #        soggetto_id + soggetto_ruolo_id) dal contratto. Speculare a
    #        `PreventiviRepository.resolve_contesto_pratica`, usato dal
    #        workflow L3 (`approvazioni_prezzo_service.crea_richiesta_approvazione_contratto`)
    #        per creare la pratica APPROVAZIONE_PREZZO con scope corretto.
    #        Post brief simmetria 2026-05-26 `emittente_fiscale_id` e' nativo
    #        su `vendite.contratti`: lettura diretta della colonna invece
    #        della derivazione runtime via fn anagrafiche.
    def resolve_contesto_pratica(self, contratto_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                c.emittente_fiscale_id,
                sr.soggetto_id::text AS soggetto_id,
                ba.soggetto_ruolo_id
            FROM vendite.contratti c
            JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
            JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contratto_id])
            return row_to_dict(cursor)

    # Scopo: Verifica se un articolo e' composito. Usato dal service per
    # decidere se invocare auto-init componenti dopo `create_riga`. Thin
    # delegate cross-dominio (Fase H residue 2026-05-14): implementazione
    # in `apps.catalogo.db.catalogo_repository.CatalogoRepository.is_articolo_composito`.
    def is_articolo_composito(self, articolo_id: str) -> bool:
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Load atomico di un componente con guard scope completo
    # (componente → riga → contratto) in UN'unica query JOIN. Sostituisce
    # la sequenza 3-query (`get_componente` + `get_riga` + `get_contratto`)
    # del service `_load_componente_for_modification` (Fix #2 perf,
    # refactor-componenti.md §13). Ritorna `None` se il componente non
    # esiste; altrimenti `{componente_id, riga_id, contratto_id,
    # stato_codice}` con i 4 dati strettamente necessari ai check del
    # service. Defense-in-depth: il caller verifica scope `riga_id` URL +
    # `contratto_id` + stato modificabile sulla tupla ritornata.
    def load_componente_with_scope(
        self, componente_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT c.id          AS componente_id,
                   c.riga_contratto_id,
                   r.contratto_id,
                   sd.codice_interno AS stato_codice_interno
              FROM vendite.contratti_righe_componenti c
              JOIN vendite.contratti_righe r ON r.id = c.riga_contratto_id
              JOIN vendite.contratti co      ON co.id = r.contratto_id
              JOIN config.stati_doc_contratti sd
                                             ON sd.id = co.stato_doc_contratto_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

    # =================================================================
    # Componenti BoM riga contratto (modello unificato 2026-05-13)
    # =================================================================
    # Specchio simmetrico di `preventivi_righe_componenti`. La FK e' qui
    # `riga_contratto_id` (vs `riga_preventivo_id`); le altre colonne sono
    # identiche per design del modello unificato.
    #
    # Fn DB chiamate:
    #   - vendite.fn_contratto_riga_componenti_init(riga_id, emittente_sr_id,
    #       data_riferimento, componenti_overrides::jsonb) -> integer
    #   - vendite.fn_contratto_riga_componenti_preview(articolo_id, uom_id,
    #       quantita_padre, data_riferimento, ba_id, utility_id,
    #       emittente_sr_id, classe_utenza_id) -> SETOF record
    #
    # Trigger DB attivi su `contratti_righe_componenti`:
    #   - trg_contratti_righe_propaga_qta_componenti: ricalcolo quantita
    #     componente al cambio quantita padre
    #   - trgfn_contratti_righe_componenti_guard_pending: immutabilita' su
    #     righe con `stato_approvazione_prezzo = PENDING`

    # Scopo: Init componenti BoM per una riga padre composita. Wrapper
    # `fn_contratto_riga_componenti_init`. La fn DB e' idempotente: no-op
    # se componenti gia' presenti o articolo non composito. Modello unificato
    # 2026-05-13: default `attivo=TRUE` per tutti i componenti (BoM contratto
    # immutabile, vedi changelog-decisioni-componenti.md §9.3).
    #
    # `componenti_overrides`: mappa `{componente_id::text: prezzo_numeric}`
    # per override prezzo manuale. Componenti senza override → resolver
    # bundle-aware con `p_articolo_padre_contesto=padre`.
    def init_componenti_riga(
        self,
        *,
        riga_id: int,
        emittente_soggetto_ruolo_id: int,
        data_riferimento: date,
        componenti_overrides: dict[str, Any] | None = None,
    ) -> int:
        # Cast esplicito a jsonb per disambiguare overload fn DB: None -> NULL.
        # Il caller (service) valida la forma valori prima di passarli qui.
        overrides_json: str | None
        if componenti_overrides is None:
            overrides_json = None
        else:
            overrides_json = json.dumps(
                {str(k): str(v) for k, v in componenti_overrides.items()},
            )
        sql = (
            "SELECT vendite.fn_contratto_riga_componenti_init("
            "%s, %s, %s, %s::jsonb)"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                riga_id, emittente_soggetto_ruolo_id, data_riferimento,
                overrides_json,
            ])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # Scopo: Preview componenti BoM per drawer riga contratto (modello
    # unificato). Read-only STABLE. Per ogni componente attivo e valido alla
    # data ritorna prezzo_suggerito (NULL se resolver fail) +
    # resolver_error_reason. Consumato dal FE per pre-popolare ComponentiDialog
    # PRIMA del save riga.
    def preview_componenti_riga(
        self,
        *,
        articolo_id: str,
        uom_id: int | None,
        quantita_padre,
        data_riferimento: date,
        ba_id: int | None,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
        # Proiezione allineata alla fn DB modello unificato. `iva_codice` NON
        # esposto: l'aliquota componente coincide con quella del padre
        # (vincolo IVA BoM trigger DB).
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
                   esposto_in_fattura
              FROM vendite.fn_contratto_riga_componenti_preview(
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

    # CRUD componenti (list/get/update/delete/purge) ereditato da
    # `ComponentiRepositoryMixin`. Vedi `_componenti_repo_mixin.py`.

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
