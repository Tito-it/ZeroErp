# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema catalogo (articoli e lookup UoM).
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    predicato_giorno_operativo,
    limiti_pagina,
    pattern_contiene,
    RicercaFull,
    add_ricerca_full_condition,
    fetch_con_sonda,
    fetch_paged_with_total,
    row_to_dict,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update

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
# ⭐ Dal 2026-11-11 (BE21-c di brief-db-revisione-catalogo) la lista legge la
#    vista `catalogo.vw_unita_misura_conversioni_dettaglio` (la `vista_sql`
#    della lista 22): codici e descrizioni delle due unita' sono colonne della
#    vista, non piu' due JOIN scritte qui.
UOM_CONVERSIONI_ORDER_COLUMNS: dict[str, str] = {
    "uom_from_codice": "c.uom_from_codice",
    "uom_to_codice": "c.uom_to_codice",
    "fattore": "c.fattore",
    "valido_dal": "c.valido_dal",
    "valido_al": "COALESCE(c.valido_al, 'infinity'::date)",
    "attivo": "c.attivo",
}

# Colonne DATA delle whitelist qui sopra: senza `order_dir` ordinano DESC
# (`sql_order_clause(colonne_desc=…)`, regola di Tid del 2026-09-02). Insiemi
# confrontati col seed da `test_liste_configurabili_seed` (test 10): devono
# coincidere con le colonne `date`/`datetime` ordinabili del catalogo.
ARTICOLI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_insert", "data_update"})
UOM_TIPI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_insert", "data_update"})
UOM_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_insert", "data_update"})
UOM_CONVERSIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"valido_dal", "valido_al"})

# Colonne SCRIVIBILI di `catalogo.articoli`: la whitelist RIGIDA del BB
# `execute_dynamic_insert`/`execute_dynamic_update`. ⭐ Dal 2026-09-26 e' un
# insieme di NOMI, non piu' una mappa nome -> tipo: il tipo serviva solo a
# `sql_placeholder`/`to_write_param` (ritirati), e `meta` — l'unica jsonb —
# arriva dal service sempre come dict o None (`_extract_meta`), che il BB
# casta da solo. Nessuna stringa-testo-JSON: `jsonb=` non serve.
ARTICOLI_CREATE_COLUMNS: frozenset[str] = frozenset({
    "codice",
    "descrizione",
    "descrizione_breve",
    "uom_id",
    "tipo_voce_id",
    "gruppo_voce_id",
    "spesa_id",
    "iva_id",
    "conto_contabile_vendita_id",
    "conto_contabile_acquisto_id",
    "is_composito",
    "is_solo_componente",
    "requires_serial",
    # Lotto 2 di magazzino (brief §4.9, M-5): l'articolo decide se si
    # movimenta per PARTITE — o sempre o mai. Gemello di `requires_serial`,
    # ⛔ ma FUORI dal lock BoM (Lotto 1 §4.3): non entra in
    # `lock_columns_conditional` ne' nei `non_editable_fields`.
    "requires_lotto",
    "listino_tipologia_id",
    "natura_vendita_id",
    # Blocco B del brief modifiche certe (2026-09-13): DA DOVE arriva l'articolo.
    # `modo_approvvigionamento_id` e' NOT NULL con DEFAULT ACQUISTO (come
    # `natura_vendita_id`), `gestito_a_magazzino` NOT NULL DEFAULT false
    # (fail-safe), `lead_time_giorni` nullable con CHECK >= 0 (NULL = «non si
    # applica», per una prestazione; `0` NON e' «non si applica»).
    "modo_approvvigionamento_id",
    "gestito_a_magazzino",
    "lead_time_giorni",
    "meta",
})

# Scopo: Whitelist colonne UPDATE articolo. Esclude codice e uom_id che sono
# entrambi immutabili (lock_columns DDL). Esclude attivo (Fase 7: la
# disattivazione/riattivazione passa solo dagli endpoint dedicati
# /disattiva/ e /riattiva/, non da PATCH).
ARTICOLI_UPDATE_COLUMNS: frozenset[str] = ARTICOLI_CREATE_COLUMNS - {"codice", "uom_id"}

# Colonne AGGIORNABILI delle tabelle UoM (whitelist RIGIDA di
# `execute_dynamic_update`, 2026-09-26). Fino a quel giorno erano tuple
# letterali dentro i metodi, e una chiave fuori tupla veniva IGNORATA in
# silenzio; il service ne teneva una copia a mano per il 400. Ora il service
# deriva la sua whitelist da qui: una fonte sola (come ARTICOLI_*_COLUMNS).
# ⚠️ Il contratto dell'operatore puo' essere piu' stretto, mai piu' largo.
UOM_TIPI_UPDATE_COLUMNS: frozenset[str] = frozenset({"descrizione", "attivo"})
UNITA_MISURA_UPDATE_COLUMNS: frozenset[str] = frozenset({
    "descrizione", "descrizione_fattura", "tipo_uom_id", "attivo",
})
# `uom_from_id`/`uom_to_id` immutabili dopo la create (exclude daterange).
CONVERSIONI_UPDATE_COLUMNS: frozenset[str] = frozenset({
    "fattore", "valido_dal", "valido_al", "attivo",
})

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
    "a.requires_lotto",
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
    # Onere (20261103-53, brief-db-addebito-trasporto-ordine §9.9): l'articolo
    # e' un addebito, non un bene. Il form articolo spegne magazzino, composito,
    # lotto e seriale, che il guard DB rifiuta su un onere.
    "a.e_onere",
    "a.causale_onere_id",
)


# Cosa si PUO' cercare nelle liste di catalogo; cosa si cerca lo dice il
# catalogo (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue §2).
# La soglia di ciascuna lista la dichiara il catalogo (`ricerca_min_caratteri`).
# ⭐ Articoli dal 2026-09-24, dopo il seed che accende codice e descrizione
#    (brief-db-ricerca-full-colonne-da-accendere §3.1, righe 321-322).
_RICERCA_ARTICOLI = RicercaFull("catalogo.articoli", ("codice", "descrizione"))
# ⛔ Il `codice_interno` NON si cerca (Tid, 2026-09-23): e' la chiave immutabile
#    del sistema, non il codice dell'operatore. Tolto il 2026-09-24, DOPO che il
#    seed l'ha spento a catalogo (riga 276, brief DB §3.4): nell'ordine inverso
#    il catalogo avrebbe acceso una colonna sconosciuta alla dichiarazione.
_RICERCA_UOM_TIPI = RicercaFull("catalogo.uom_tipi", ("codice", "descrizione"))
_RICERCA_UNITA_MISURA = RicercaFull("catalogo.unita_misura", ("codice", "descrizione"))
_RICERCA_CONVERSIONI = RicercaFull("catalogo.conversioni_uom", (
    "uom_from_codice", "uom_from_descrizione", "uom_to_codice", "uom_to_descrizione",
))

# La proiezione di una conversione, lista e dettaglio: le colonne della vista
# e la capability di riga del BB del DB `catalogo.fn_uom_conversione_capability`
# (G1-G2, 2026-11-11), la stessa regola con cui `trgfn_uom_guard_storia`
# rifiuta. Il backend la TRASPORTA: `puo_eliminarsi` / `motivo_non_eliminabile`
# per il cestino, `puo_cambiare_attivo` per l'interruttore, `puo_chiudersi` /
# `data_min_chiusura` / `data_default_chiusura` / `motivo_non_chiudibile` per
# la data di fine.
_CONVERSIONE_COLONNE = """
    c.id, c.uom_from_id, c.uom_to_id, c.fattore,
    c.valido_dal, c.valido_al, c.attivo,
    c.uom_from_codice, c.uom_from_descrizione,
    c.uom_to_codice, c.uom_to_descrizione,
    c.puo_eliminarsi, c.motivo_non_eliminabile,
    c.puo_cambiare_attivo, c.puo_chiudersi,
    c.data_min_chiusura, c.data_default_chiusura, c.motivo_non_chiudibile
"""


# Il tetto dei picker degli articoli (ricerca libera e righe di documento): una
# sede sola, la leggono il repository (che taglia) e il service (che rifiuta un
# `limit` oltre). Due numeri scritti a mano divergerebbero al primo ritocco.
LOOKUP_ARTICOLI_MAX = 50


# Le colonne dell'articolo che un picker porta a video: le stesse per la ricerca
# libera (`lookup_articoli`) e per le righe di documento
# (`lookup_articoli_ammessi`), che le uniscono da `catalogo.vw_articoli_dettaglio`
# (alias `a`). Una sede: i form di riga leggono questi campi dall'articolo scelto.
# I flag di MAGAZZINO (Lotto 2, 2026-09-18): il form di riga dell'inventario
# mostra lotto e seriale SOLO se l'articolo li pretende, e li legge dalla riga
# scelta nel picker — mai ricalcolati (piano-be-fe-magazzino-lotto-2-motore §5.3).
# L'ONERE (2026-11-03): sulla riga d'ordine nuova il form spegne le date di
# consegna se l'articolo scelto e' un onere (brief-db-addebito-trasporto-ordine §9.9).
_LOOKUP_ARTICOLI_COLONNE = """a.id,
                a.codice,
                a.descrizione,
                a.uom_codice,
                a.uom_descrizione,
                a.is_composito,
                a.attivo,
                a.iva_id,
                a.iva_codice,
                a.iva_descrizione,
                a.iva_aliquota_iva,
                a.gestito_a_magazzino,
                a.requires_lotto,
                a.requires_serial,
                a.e_onere,
                a.causale_onere_id"""


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
        order_by: str | None,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # ORDER BY dal BB (NULLS espliciti + tiebreak allineato). ⚠️ Fino al
        # 2026-09-26 qui c'era `ARTICOLI_ORDER_COLUMNS[order_by]`: KeyError
        # fuori whitelist, mentre le tre liste UoM ripiegavano sul default.
        # Il default e' quello del service e della view (`descrizione`).
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ARTICOLI_ORDER_COLUMNS, default="a.descrizione", tiebreak="a.id",
            colonne_desc=ARTICOLI_SORT_COLONNE_DATA,
        )

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
        # Colonne e soglia dal catalogo della lista (BB). Sotto soglia il
        # termine non filtra, e la view non risponde 400 (brief-db-be-fe-
        # ricerca-soglia-per-lista §6 a, Tid 2026-09-26).
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ARTICOLI, alias="a")
        # Giorni dell'AZIENDA, `data_a` incluso (BB): fino al 2026-10-09 era
        # `a.data_insert::date`, il giorno della sessione e niente indice.
        giorno_sql, giorno_params = predicato_giorno_operativo("a.data_insert", data_da, data_a)
        conditions.append(giorno_sql)
        params.extend(giorno_params)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        from_where = f"FROM catalogo.vw_articoli_dettaglio a {where_clause}"

        data_sql = f"""
            SELECT
                {self._articoli_detail_projection()},
                COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
        """  # proiezione da ARTICOLI_DETAIL_COLUMNS, ORDER BY da sql_order_clause su whitelist ARTICOLI_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
        # Totale in UNA valutazione; il COUNT separato gira solo su una pagina
        # oltre l'ultima, dove la window function non puo' dirlo.
        return fetch_paged_with_total(
            data_sql, params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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
    # ⛔ Dal 2026-09-26 (BB `execute_dynamic_insert`) una chiave fuori
    #    `ARTICOLI_CREATE_COLUMNS` e' `RuntimeError`, non piu' scartata in
    #    silenzio: il contratto dell'operatore lo fa rispettare il service con
    #    un 400 (`_extract_articolo_payload` -> `_validate_payload_keys`).
    #    None scrive NULL (nessun `skip_none`: come prima).
    def create_articolo(self, data: dict[str, Any]) -> UUID:
        riga = execute_dynamic_insert(
            "catalogo.articoli", data, allowed=ARTICOLI_CREATE_COLUMNS,
        )
        return riga["id"]

    # Scopo: Aggiorna i soli campi presenti nel payload, supportando anche NULL espliciti.
    # ⛔ Whitelist RIGIDA come la create (vedi sopra); payload vuoto -> False.
    def update_articolo(self, articolo_id: UUID | str, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "catalogo.articoli", articolo_id, data, allowed=ARTICOLI_UPDATE_COLUMNS,
        )

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

    # Scopo: Il SUPER_ADMIN corregge i flag strutturali di un articolo anche se
    #        usato (A-10 di brief-db-articoli-ammessi-per-documento): verbo
    #        `catalogo.fn_articolo_correggi_struttura`, la sola porta. Il permesso,
    #        la forma di `campi`, le colonne ammesse e l'esistenza li giudica il
    #        verbo: `campi` passa com'e' (None diventa il jsonb `null`, rifiutato).
    def correggi_struttura_articolo(self, articolo_id: UUID | str, campi: Any) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT catalogo.fn_articolo_correggi_struttura(%s, %s::jsonb)",
                [articolo_id, json.dumps(campi)],
            )

    # Scopo: Le colonne STRUTTURALI dell'articolo, quelle che la correzione
    #        riapre, dalla sede del DB `catalogo.fn_articolo_colonne_struttura`
    #        (R-DB-3, 2026-10-18: le regole del form sul predicato dell'uso),
    #        nell'ordine della dichiarazione. La stessa sede da cui il verbo
    #        della correzione legge le colonne ammesse.
    def colonne_struttura_articolo(self) -> list[str]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT catalogo.fn_articolo_colonne_struttura()")
            row = cursor.fetchone()
        assert row is not None
        return list(row[0] or [])

    # Scopo: Restituisce lookup articoli per autocomplete cross-dominio.
    def lookup_articoli(
        self,
        *,
        search: str | None,
        attivo: bool | None,
        is_composito: bool | None,
        gestito_a_magazzino: bool | None = None,
        solo_oneri: bool = False,
        limit: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        safe_limit = max(1, min(int(limit), LOOKUP_ARTICOLI_MAX))
        conditions: list[str] = []
        params: list[Any] = []
        join_clause = ""

        # ⚠️ La lookup NON e' una lista: non ha un catalogo da leggere e non passa
        #    dal BB `add_ricerca_full_condition` (brief-be-ricerca-full-liste-
        #    residue §7-bis, ultimo paragrafo). La ricerca resta scritta qui, con
        #    `escape_ilike` e `strip` come le altre lookup (`billing_account`,
        #    `istanze_utility`): senza escape «BA_1» o «50%» facevano da jolly.
        #    Un solo consumatore: niente helper (regola del 2). L'helper
        #    `_append_ilike_search` che la condivideva con la lista articoli e'
        #    ritirato il 2026-09-24 (brief §8).
        termine = search.strip() if search else ""
        if termine:
            like_value = pattern_contiene(termine)
            conditions.append("(a.codice ILIKE %s OR a.descrizione ILIKE %s)")
            params.extend([like_value, like_value])
        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if is_composito is not None:
            conditions.append("a.is_composito = %s")
            params.append(is_composito)
        # R-5 del brief magazzino 2-bis: il picker di riga di un inventario o
        # di una rettifica propone SOLO gli articoli gestiti a magazzino — un
        # articolo non gestito si potrebbe anche salvare, ma il piano lo
        # marcherebbe `NON_POSTABILE` e fermerebbe la registrazione.
        # ⛔ Non e' un filtro di default (`None` = nessun filtro, come
        #    `is_solo_componente`): altrove la tendina continua a proporre
        #    tutto. E non blocca niente — chi non lo passa vede gli stessi
        #    articoli di prima, e l'anteprima dei motivi lo dice comunque.
        if gestito_a_magazzino is not None:
            conditions.append("a.gestito_a_magazzino = %s")
            params.append(gestito_a_magazzino)
        # ⛔ Qui NON si filtra per le righe di un documento (natura, solo
        #    componente, composito): quali articoli ammette una riga lo dice il DB,
        #    in `lookup_articoli_ammessi` qui sotto. I filtri liberi che il
        #    chiamante sceglieva (`is_solo_componente`, `escludi_destinazione_tipi`)
        #    sono ritirati il 2026-10-14 (brief-db-articoli-ammessi-per-documento
        #    §9.6, Lotto 4): erano una copia della regola dei guard, e divergevano.
        #    Restano i filtri delle CONSULTAZIONI, che non sono righe di quella
        #    check: attivi/inattivi, `is_composito`, `gestito_a_magazzino`, oneri.
        # Porta oneri: un articolo E' un onere se ha una causale collegata
        # (`causale_onere_id` NOT NULL, legame 1:1 — brief porta-oneri §4c.8).
        # `e_onere` e `causale_onere_id` li espone la vista dal 20261103-53 (e
        # sono gia' fra le colonne del picker): qui si aggiunge solo il
        # vocabolario, per portare a video la causale accanto all'articolo
        # (display fields lato BE, il FE non fa lookup client-side).
        extra_cols = ""
        if solo_oneri:
            join_clause += " JOIN config.causali_onere co ON co.id = a.causale_onere_id"
            conditions.append("a.e_onere")
            extra_cols = (
                ",\n                    co.codice AS causale_onere_codice,"
                "\n                    co.descrizione AS causale_onere_descrizione"
            )

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # ⛔ Il TETTO lo conosce solo questo metodo, che clampa: la sonda si
        #    chiama da qui e non dal service, o il limite finirebbe scritto in
        #    due sedi che divergono al primo cambio. Il `+1`, il taglio e il
        #    flag stanno insieme dentro `fetch_con_sonda` — sono una cosa sola.
        #    Vedi migliorie-generali-BE-FE-da-test-valutazione.md §D6.
        # ⚠️ La sonda regge perche' il JOIN qui sopra e' 1:1 (`co` su una
        #    FK): un JOIN che moltiplicasse le righe le farebbe contare due
        #    volte, e l'elenco direbbe «troncato» quando e' intero. Chi
        #    aggiunge un JOIN a questa query deve guardare qui.
        return fetch_con_sonda(
            f"""
            SELECT
                {_LOOKUP_ARTICOLI_COLONNE}{extra_cols}
            FROM catalogo.vw_articoli_dettaglio a
            {join_clause}
            {where_clause}
            ORDER BY a.codice ASC
            LIMIT %s
            """,  # noqa: S608 — frammenti da letterali interni, valori parametrizzati
            params,
            limite=safe_limit,
        )

    # Scopo: Il picker degli articoli di una RIGA di documento: gli articoli
    #        attivi che la ricerca trova, ciascuno col primo motivo per cui il
    #        documento non lo ammette (`motivo` None = ammesso), prima gli
    #        ammessi. Ritorna `(righe, troncato)` come `lookup_articoli`.
    # ⭐ La regola la dice il DB, una volta: `catalogo.fn_articoli_ammessi` legge
    #    la stessa check dei guard di riga (brief-db-articoli-ammessi-per-documento
    #    §9.4, A-2). Il backend la trasporta: niente filtri scelti qui.
    # ⚠️ Il TETTO sta in una sede sola, `fetch_con_sonda`: alla funzione si passa
    #    `p_limit` NULL (nessun tetto) e il `LIMIT` esterno taglia sull'`ordine`
    #    che la funzione ha deciso dopo aver giudicato tutti i trovati. Due tetti
    #    (dentro e fuori) sarebbero due numeri da tenere uguali.
    # ⚠️ Il JOIN con la vista e' 1:1 (`articolo_id` = PK): la sonda regge.
    def lookup_articoli_ammessi(
        self,
        *,
        documento: str,
        documento_id: int | None,
        search: str | None,
        tipo_eccezione: str | None,
        articolo_padre_id: UUID | str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        safe_limit = max(1, min(int(limit), LOOKUP_ARTICOLI_MAX))
        righe, troncato = fetch_con_sonda(
            f"""
            SELECT
                {_LOOKUP_ARTICOLI_COLONNE},
                am.motivo
            FROM catalogo.fn_articoli_ammessi(
                %s, %s, %s, NULL,
                %s::vendite.tipo_eccezione_contratto, %s::uuid
            ) am
            JOIN catalogo.vw_articoli_dettaglio a ON a.id = am.articolo_id
            ORDER BY am.ordine
            LIMIT %s
            """,  # noqa: S608 — colonne da costante interna, valori parametrizzati
            [documento, documento_id, search, tipo_eccezione, articolo_padre_id],
            limite=safe_limit,
        )
        # ⚠️ `motivo` arriva decodificato dal lettore comune (`rows_to_list`): il
        #    NULL resta NULL, e qui vuol dire «ammesso».
        return righe, troncato

    # Scopo: Dice se `valore` e' un tipo d'eccezione di contratto/offerta
    #        (l'enum `vendite.tipo_eccezione_contratto`), prima di passarlo al
    #        picker col cast. Un valore fuori enum al cast sarebbe un 500
    #        (22P02); il vocabolario si legge dal DB, non si ricopia qui.
    def tipo_eccezione_valido(self, valore: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT %s = ANY(enum_range(NULL::vendite.tipo_eccezione_contratto)::text[])",
                [valore],
            )
            row = cursor.fetchone()
            assert row is not None
            return bool(row[0])

    # --- Sezione CRUD uom_tipi ---

    # Scopo: Restituisce elenco paginato tipologie UoM con filtri opzionali.
    def list_uom_tipi(
        self,
        *,
        attivo: bool | None,
        search: str | None,
        order_by: str | None,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=UOM_TIPI_ORDER_COLUMNS, default="ut.descrizione", tiebreak="ut.id",
            colonne_desc=UOM_TIPI_SORT_COLONNE_DATA,
        )

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("ut.attivo = %s")
            params.append(attivo)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_UOM_TIPI, alias="ut")

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        from_where = f"FROM catalogo.uom_tipi ut {where_clause}"

        return fetch_paged_with_total(
            f"""
            SELECT ut.id, ut.codice, ut.codice_interno, ut.descrizione, ut.attivo,
                   ut.user_insert, ut.user_update, ut.data_insert, ut.data_update,
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist UOM_TIPI_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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
        return execute_dynamic_update(
            "catalogo.uom_tipi", tipo_id, data, allowed=UOM_TIPI_UPDATE_COLUMNS,
        )

    # --- Sezione CRUD unita_misura ---

    # Scopo: Restituisce elenco paginato unita' di misura con filtri opzionali.
    def list_unita_misura(
        self,
        *,
        attivo: bool | None,
        search: str | None,
        order_by: str | None,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=UOM_ORDER_COLUMNS, default="u.codice", tiebreak="u.id",
            colonne_desc=UOM_SORT_COLONNE_DATA,
        )

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("u.attivo = %s")
            params.append(attivo)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_UNITA_MISURA, alias="u")

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        # ⚠️ Il COUNT storico leggeva la sola `unita_misura`, la pagina anche il
        #    JOIN su `uom_tipi`: FK NOT NULL, quindi stesso insieme. Ora il
        #    totale viene dalla pagina, e il ripiego ha lo stesso FROM.
        from_where = (
            "FROM catalogo.unita_misura u "
            "JOIN catalogo.uom_tipi ut ON ut.id = u.tipo_uom_id "
            f"{where_clause}"
        )

        return fetch_paged_with_total(
            f"""
            SELECT u.id, u.codice, u.descrizione, u.descrizione_fattura,
                   u.tipo_uom_id, ut.codice AS tipo_uom_codice,
                   ut.descrizione AS tipo_uom_descrizione, u.attivo,
                   u.user_insert, u.user_update, u.data_insert, u.data_update,
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist UOM_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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
        return execute_dynamic_update(
            "catalogo.unita_misura", uom_id, data, allowed=UNITA_MISURA_UPDATE_COLUMNS,
        )

    # =================================================================
    # Conversioni UoM (catalogo.unita_misura_conversioni)
    # =================================================================

    # Scopo: Lista paginata delle conversioni UoM (vista di dettaglio, con la capability di riga).
    def list_conversioni(
        self, *, search: str | None = None, attivo: bool | None = True,
        uom_id: int | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str | None = "uom_from_codice", order_dir: str | None = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # ⚠️ Fino al 2026-09-26 la direzione si confrontava con `.upper()` e
        #    nelle sorelle con `.lower()`: ora la legge il BB per tutte.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=UOM_CONVERSIONI_ORDER_COLUMNS, default="c.uom_from_codice", tiebreak="c.id",
            colonne_desc=UOM_CONVERSIONI_SORT_COLONNE_DATA,
        )

        conditions: list[str] = []
        params: list[Any] = []
        if attivo is not None:
            conditions.append("c.attivo = %s")
            params.append(attivo)
        if uom_id is not None:
            conditions.append("(c.uom_from_id = %s OR c.uom_to_id = %s)")
            params.extend([uom_id, uom_id])
        add_ricerca_full_condition(conditions, params, search, _RICERCA_CONVERSIONI, alias="c")
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        from_where = f"FROM catalogo.vw_unita_misura_conversioni_dettaglio c {where_clause}"

        return fetch_paged_with_total(
            f"""
            SELECT {_CONVERSIONE_COLONNE},
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist UOM_CONVERSIONI_ORDER_COLUMNS, WHERE da condizioni letterali + add_ricerca_full_condition (espressioni dichiarate nel repo), valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

    # Scopo: Restituisce singola conversione UoM per id, dalla stessa vista
    #        della lista: il drawer legge la stessa capability (BE21-e).
    def get_conversione(self, conv_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_CONVERSIONE_COLONNE} FROM catalogo.vw_unita_misura_conversioni_dettaglio c WHERE c.id = %s",  # noqa: S608 — proiezione dalla costante _CONVERSIONE_COLONNE, valore come parametro
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
        return execute_dynamic_update(
            "catalogo.unita_misura_conversioni", conv_id, data, allowed=CONVERSIONI_UPDATE_COLUMNS,
        )

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
