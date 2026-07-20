# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema vendite (query, liste, decodifiche).
# ------------------------------------------------------------

# Contiene operazioni generiche sullo schema vendite che non appartengono
# a nessun sottodominio specifico (pipeline, reset, ecc.).

import re
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    query_paged_view,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashBacklogRiepilogoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaMensileRow,
    LineageNodoRow,
    LineagePassaggioRow,
    LineageSorgenteRow,
    LottoFattureRow,
    LottoListRow,
)

# Whitelist colonne ordinamento per list_lotto_fatture; mai interpolate direttamente.
_SORT_COLUMNS: dict[str, str] = {
    "fattura_id": "fllf.fattura_id",
    "nominativo": "srd.ragione_sociale_completa",
    "totale_doc": "f.totale_doc",
}

# Aree della famiglia dash fatturazione, nell'ordine del funnel (brief
# brief-design-dashboard-fatturazione §4 + §6-quater design due-lenti,
# DL-21/24). Allineate al discriminante `area` della union
# vendite.vw_dash_fatturazione_documenti (6 aree documento) + il ramo RESI
# che vive SOLO nel Backlog (union dedicata in vw_dash_backlog_documenti,
# fuori dal funnel pre-commessa). Usate dalla Lente 2 Backlog (che include
# COMMESSE e RESI).
DASH_FATTURAZIONE_AREE: tuple[str, ...] = (
    "PREVENTIVI",
    "ORDINI",
    "DDT",
    "OFFERTE",
    "CONTRATTI",
    "COMMESSE",
    "RESI",
)

# Aree con valore monetario (imponibile, decisione D-4). OFFERTE e CONTRATTI
# restano a conteggi (decisioni D-2/D-3 confermate da DL-11), RESI idem
# (DL-24: nessun importo sui resi in questa slice): valore_* = NULL.
DASH_FATTURAZIONE_AREE_EURO: frozenset[str] = frozenset(
    {"PREVENTIVI", "ORDINI", "DDT", "COMMESSE"}
)

# Aree della Situazione aperta (stock documenti, §6-bis/§6-quater design
# due-lenti): le 5 aree documento nell'ordine del funnel — NIENTE COMMESSE
# (coperte dalla Lente 1), NIENTE RESI (DL-24: REVERSE_FLOW, non serbatoio).
# Il DDT entra con la popolazione ristretta del resolver (DL-21: solo DDT
# con ruolo di fatturazione). Allineate al WHERE di
# vendite.vw_dash_aperto_documenti.
DASH_APERTO_AREE: tuple[str, ...] = (
    "PREVENTIVI",
    "ORDINI",
    "DDT",
    "OFFERTE",
    "CONTRATTI",
)

# Fasi VIVE del serbatoio pre-commessa (v2, DL-15/16): solo aperti-non-chiusi
# → niente CHIUSO. Ordine = maturita' verso la commessa (DL-10): bozza interna
# → palla al cliente → da lavorare. Non tutte le aree emettono tutte le fasi
# (es. ORDINI non ha IN_ATTESA): il pivot le espone comunque tutte (griglia
# simmetrica, il FE decide quali card mostrare — DL-13).
DASH_APERTO_FASI: tuple[str, ...] = (
    "APERTO",
    "IN_ATTESA",
    "IN_CORSO",
)

# Stadi del funnel Lente 1 Competenza, nell'ordine commessa → fattura (brief
# brief-db-fatturazione-due-lenti §4.1). Allineati al CASE `stadio` di
# vendite.vw_dash_competenza_attivita. Il primo stadio ha una costante puntuale:
# e' il perimetro dell'approvazione massiva A-2 (un solo owner del letterale).
DASH_STADIO_DA_APPROVARE = "DA_APPROVARE"
DASH_COMPETENZA_STADI: tuple[str, ...] = (
    DASH_STADIO_DA_APPROVARE,
    "DA_EMETTERE",
    "EMESSA_NON_FATTURATA",
    "FATTURATA",
)

# Classi di azionabilita' della Lente 2 Backlog, nell'ordine di esposizione UI
# del design (§5: contatori 🟠 recuperabile · 🔵 sollecito cliente · 🔴
# anomalia). Il FISIOLOGICO 🟢 e' escluso a monte dalla vista. Allineate al
# CHECK di config.motivi_fermo (DL-6).
DASH_BACKLOG_CLASSI: tuple[str, ...] = (
    "RECUPERABILE",
    "SOLLECITO_CLIENTE",
    "ANOMALIA",
)


class VenditeRepository:

    # Scopo: Query paginata su vista/union costosa in UNA valutazione con
    #        CLAMP all'ultima pagina (il service dichiara la pagina effettiva
    #        nell'envelope). Estratto 2026-07-07 (regola del 2, ok Tid) per
    #        aperto/backlog/errori; PROMOSSO a BB core 2026-07-18
    #        (`apps.core.db._helpers.query_paged_view`, ok Tid): qui resta il
    #        delegatore per i call-site interni.
    def _query_paged_view(
        self,
        *,
        select_sql: str,
        order_by: str,
        params: list[Any],
        limit: int,
        offset: int,
    ) -> tuple[list[tuple], int]:
        return query_paged_view(
            select_sql=select_sql,
            order_by=order_by,
            params=params,
            limit=limit,
            offset=offset,
        )

    # Scopo: Aggiunge la condizione WHERE per scope emittente (convenzione SR:
    #        colonne <ruolo>_soggetto_ruolo_id). Delega al BB condiviso
    #        `add_emittente_scope_condition` (array risolto UNA volta in
    #        Python, non per riga — estrazione regola-del-2 dai 5 repo).
    @staticmethod
    def _add_scope_emittente(
        auth_user_id: int | None,
        field: str,
        conditions: list[str],
        params: list[Any],
    ) -> None:
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column=field,
            convention="sr",
        )

    # Scopo: Restituisce elenco lotti paginato con JOIN decodifica e filtri opzionali.
    # Obiettivo: lista generica fatturazione_lotti con decodifiche config.
    # Proiezione + JOIN + mapping condivisi da list_lotti e get_lotto (la testata
    # del dettaglio è la stessa riga della lista: nessuna vista/colonna nuova).
    _LOTTO_SELECT_COLS = """
                fl.id,
                fl.codice,
                fl.competenza_mese,
                fl.tipo_lotto,
                fl.utility_id,
                u.descrizione      AS utility_descrizione,
                fl.stato_lotto,
                fl.stato_operativo,
                fl.stato_doc_fiscale_id,
                sdf.descrizione    AS stato_doc_fiscale_descrizione,
                fl.tipo_doc_fiscale_id,
                tdf.descrizione    AS tipo_doc_fiscale_descrizione,
                fl.area_geografica_id,
                agf.descrizione    AS area_geografica_descrizione,
                fl.emittente_soggetto_ruolo_id,
                fl.data_insert,
                fl.user_insert
    """

    _LOTTO_JOINS = """
            LEFT JOIN config.utilities u
                ON u.id = fl.utility_id
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = fl.stato_doc_fiscale_id
            LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = fl.tipo_doc_fiscale_id
            LEFT JOIN vendite.area_geografica_fatturazione agf
                ON agf.id = fl.area_geografica_id
    """

    # Scopo: mappa una riga (ordine di _LOTTO_SELECT_COLS) in LottoListRow.
    @staticmethod
    def _map_lotto_row(row: tuple) -> LottoListRow:
        return {
            "id": int(row[0]),
            "codice": str(row[1]),
            "competenza_mese": row[2].isoformat() if row[2] is not None else None,
            "tipo_lotto": str(row[3]),
            "utility_id": None if row[4] is None else int(row[4]),
            "utility_descrizione": row[5],
            "stato_lotto": str(row[6]),
            "stato_operativo": str(row[7]),
            "stato_doc_fiscale_id": None if row[8] is None else int(row[8]),
            "stato_doc_fiscale_descrizione": row[9],
            "tipo_doc_fiscale_id": int(row[10]),
            "tipo_doc_fiscale_descrizione": row[11],
            "area_geografica_id": None if row[12] is None else int(row[12]),
            "area_geografica_descrizione": row[13],
            "emittente_soggetto_ruolo_id": None if row[14] is None else int(row[14]),
            "data_insert": row[15].isoformat() if row[15] is not None else None,
            "user_insert": str(row[16]),
        }

    # Perimetro: solo lettura; nessun side-effect.
    # Risultato: tuple (lista LottoListRow, conteggio totale).
    def list_lotti(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None,
        stato_lotto: str | None,
        area_geografica_id: int | None,
        tipo_doc_fiscale_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[LottoListRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        # Costruzione WHERE dinamica; ogni filtro è parametrizzato.
        if competenza_mese is not None:
            conditions.append("fl.competenza_mese = %s")
            params.append(competenza_mese)
        if utility_id is not None:
            conditions.append("fl.utility_id = %s")
            params.append(utility_id)
        if stato_lotto is not None:
            conditions.append("fl.stato_lotto = %s")
            params.append(stato_lotto)
        if area_geografica_id is not None:
            conditions.append("fl.area_geografica_id = %s")
            params.append(area_geografica_id)
        if tipo_doc_fiscale_id is not None:
            conditions.append("fl.tipo_doc_fiscale_id = %s")
            params.append(tipo_doc_fiscale_id)
        if emittente_soggetto_ruolo_id is not None:
            conditions.append("fl.emittente_soggetto_ruolo_id = %s")
            params.append(emittente_soggetto_ruolo_id)

        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        joins = self._LOTTO_JOINS

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.fatturazione_lotti fl
            {joins}
            {where_clause}
        """

        data_sql = f"""
            SELECT {self._LOTTO_SELECT_COLS}
            FROM vendite.fatturazione_lotti fl
            {joins}
            {where_clause}
            ORDER BY fl.data_insert DESC, fl.id DESC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[LottoListRow] = [self._map_lotto_row(row) for row in rows]
        return result, total_count

    # Scopo: Restituisce il dettaglio testata di un singolo lotto (stessa
    #        proiezione della lista), con scope emittente applicato: un lotto
    #        fuori scope torna None → il BE risponde 404 (indistinguibile da id
    #        inesistente, coerente con la RLS operatori, api.md §scope).
    # Perimetro: sola lettura; nessun side-effect.
    def get_lotto(
        self, *, lotto_id: int, auth_user_id: int | None = None,
    ) -> LottoListRow | None:
        conditions: list[str] = ["fl.id = %s"]
        params: list[Any] = [lotto_id]
        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )
        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT {self._LOTTO_SELECT_COLS}
            FROM vendite.fatturazione_lotti fl
            {self._LOTTO_JOINS}
            {where_clause}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        if row is None:
            return None
        return self._map_lotto_row(row)

    # Scopo: Restituisce le celle non vuote (area × fase) del serbatoio
    #        pre-commessa. Il completamento a griglia 5 aree × 3 fasi
    #        (celle vuote = zeri, DL-13) e' a carico del service — qui NON si
    #        duplica, si legge solo cio' che esiste.
    # Perimetro: sola lettura su vw_dash_aperto_riepilogo v2 (security_invoker →
    #        la RLS emittente sulle 5 aree documento filtra da sola; perimetro
    #        aperti-non-chiusi gia' nella vista, DL-15).
    # Risultato: lista piatta DashApertoRiepilogoRow (≤ 12 righe).
    def list_dash_aperto_riepilogo(self) -> list[DashApertoRiepilogoRow]:
        sql = """
            SELECT
                area,
                fase,
                n_documenti,
                valore_totale
            FROM vendite.vw_dash_aperto_riepilogo
            ORDER BY area, fase
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        result: list[DashApertoRiepilogoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "fase": str(row[1]),
                    "n_documenti": int(row[2]),
                    "valore_totale": str(row[3]) if row[3] is not None else None,
                }
            )
        return result

    # Scopo: Restituisce il drill-down paginato del serbatoio pre-commessa
    #        (vw_dash_aperto_documenti v2: 5 aree documento, perimetro
    #        aperti-non-chiusi lato vista), con filtri opzionali area/fase e
    #        ritardo_giorni ("aperti da oltre N giorni" su data_riferimento,
    #        DL-17). anzianita_giorni derivata in SELECT (GREATEST). Ordinamento
    #        BE-side (le viste non garantiscono ORDER): piu' vecchio prima, poi
    #        valore.
    # Perimetro: sola lettura; scope emittente interamente DB-side (RLS
    #        invoker sulle 5 aree documento). Una sola valutazione della
    #        union + clamp offset via _query_paged_view.
    # Risultato: tuple (lista DashApertoDocumentoRow, conteggio totale).
    # Colonne ordinabili del drill-down Situazione aperta: chiave esposta al FE
    # (allineata al `field` della colonna DataTable) -> colonna della CTE
    # `righe`. Whitelist: nell'ORDER BY entrano solo chiavi note + direzione
    # ASC/DESC, mai input utente grezzo (no SQL injection). Convenzione
    # order_by/order_dir come le liste standard (fn_search_soggetti_universale).
    DASH_APERTO_SORT_COLUMNS = {
        "anzianita_giorni": "anzianita_giorni",
        "codice": "codice",
        "cliente_display": "cliente_display",
        "valore_totale": "valore_totale",
    }

    def list_dash_aperto_documenti(
        self,
        *,
        area: str | None,
        fase: str | None,
        ritardo_giorni: int | None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashApertoDocumentoRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if area is not None:
            conditions.append("d.area = %s")
            params.append(area)
        if fase is not None:
            conditions.append("d.fase = %s")
            params.append(fase)
        # Filtro "aperti da oltre N giorni" su data documento (DL-17): soglia
        # solo sul drill-down (le card restano la fotografia completa). Costo
        # DB zero — nessuna funzione temporale sul totale delle card.
        if ritardo_giorni is not None:
            conditions.append(
                "d.data_riferimento <= current_date - make_interval(days => %s)"
            )
            params.append(ritardo_giorni)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_sql = f"""
            SELECT
                d.area,
                d.documento_id,
                d.documento_uid,
                d.codice,
                d.cliente_display,
                d.fase,
                d.stato_codice_interno,
                d.stato_codice,
                d.valore_totale,
                d.unita_totali,
                GREATEST((current_date - d.data_riferimento), 0) AS anzianita_giorni,
                d.motivo_fermo,
                d.data_riferimento
            FROM vendite.vw_dash_aperto_documenti d
            {where_clause}
        """

        # ORDER BY server-side (corretto su TUTTE le pagine, non solo quella
        # visibile): colonna dalla whitelist DASH_APERTO_SORT_COLUMNS + direzione
        # ASC/DESC, con tiebreak stabile (area, documento_id) per paginazione
        # deterministica. order_by assente/non ammesso -> ordine storico
        # "in essere da" (i piu' vecchi prima).
        sort_col = self.DASH_APERTO_SORT_COLUMNS.get(order_by or "")
        if sort_col is not None:
            direction = sql_order_direction(order_dir)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                "area ASC, documento_id ASC"
            )
        else:
            order_clause = """
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_totale DESC NULLS LAST,
                     area ASC, documento_id ASC
            """

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashApertoDocumentoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "documento_id": int(row[1]),
                    "documento_uid": None if row[2] is None else str(row[2]),
                    "codice": None if row[3] is None else str(row[3]),
                    "cliente_display": None if row[4] is None else str(row[4]),
                    "fase": None if row[5] is None else str(row[5]),
                    "stato_codice_interno": None if row[6] is None else str(row[6]),
                    "stato_codice": None if row[7] is None else str(row[7]),
                    "valore_totale": str(row[8]) if row[8] is not None else None,
                    "unita_totali": None if row[9] is None else int(row[9]),
                    "anzianita_giorni": int(row[10]),
                    "motivo_fermo": None if row[11] is None else str(row[11]),
                    "data_riferimento": (
                        row[12].isoformat() if row[12] is not None else None
                    ),
                }
            )
        return result, total_count

    # Scopo: Restituisce le righe non vuote (mese × stadio × stato fattura)
    #        dell'aggregata Lente 1 Competenza per un anno, in formato lungo.
    #        Il pivot ai 4 blocchi (griglia 12 mesi × 4 stadi + breakdown stato
    #        fattura) e' a carico del service — qui si legge solo cio' che esiste.
    # Perimetro: sola lettura su vw_dash_competenza_mensile (invoker + scope GUC
    #        fail-closed nel resolver attivita'). Decode etichetta stato fattura
    #        via JOIN su codice_interno (display field BE-side).
    # Risultato: lista piatta DashCompetenzaMensileRow ordinata per mese/stadio/
    #        ordine stato.
    def list_dash_competenza_mensile(self, *, anno: int) -> list[DashCompetenzaMensileRow]:
        sql = """
            SELECT
                m.competenza_mese,
                m.stadio,
                m.stato_fattura_codice_interno,
                sdf.codice          AS stato_fattura_codice,
                m.n_attivita,
                m.valore_tot,
                m.valore_fatturato_tot,
                m.n_in_ritardo,
                m.valore_in_ritardo
            FROM vendite.vw_dash_competenza_mensile m
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.codice_interno = m.stato_fattura_codice_interno
            WHERE m.competenza_mese >= make_date(%s, 1, 1)
              AND m.competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            ORDER BY m.competenza_mese, m.stadio,
                     sdf.ordine NULLS LAST, m.stato_fattura_codice_interno
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [anno, anno])
            rows = cursor.fetchall()

        result: list[DashCompetenzaMensileRow] = []
        for row in rows:
            result.append(
                {
                    "competenza_mese": row[0].isoformat(),
                    "stadio": str(row[1]),
                    "stato_fattura_codice_interno": None if row[2] is None else str(row[2]),
                    "stato_fattura_codice": None if row[3] is None else str(row[3]),
                    "n_attivita": int(row[4]),
                    "valore": str(row[5]) if row[5] is not None else "0",
                    "valore_fatturato": str(row[6]) if row[6] is not None else "0",
                    "n_in_ritardo": int(row[7]),
                    "valore_in_ritardo": str(row[8]) if row[8] is not None else "0",
                }
            )
        return result

    # Scopo: Restituisce il conteggio errori vivi (blocco 4 Lente 1) per mese
    #        di competenza di un anno — alimenta il semaforo/badge mensile
    #        senza caricare l'intera lista errori.
    # Perimetro: sola lettura su vw_dash_competenza_errori (scope GUC in vista).
    #        Il bucket mensile e' normalizzato con date_trunc: a differenza di
    #        commesse_attivita, fatturazione_lotti.competenza_mese NON ha un
    #        CHECK primo-del-mese, e una chiave a meta' mese non matcherebbe
    #        mai la griglia del service (errore invisibile).
    # Risultato: dict {competenza_mese_iso: n_errori} dei soli mesi con errori.
    def count_dash_competenza_errori_mensile(self, *, anno: int) -> dict[str, int]:
        sql = """
            SELECT date_trunc('month', competenza_mese)::date AS mese,
                   COUNT(*)::integer
            FROM vendite.vw_dash_competenza_errori
            WHERE competenza_mese >= make_date(%s, 1, 1)
              AND competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [anno, anno])
            rows = cursor.fetchall()
        return {row[0].isoformat(): int(row[1]) for row in rows}

    # Scopo: Restituisce il drill-down paginato delle attivita' di un mese di
    #        competenza (Lente 1, grana attivita'), con filtro opzionale per
    #        stadio del funnel e per recuperi tardivi.
    # Perimetro: sola lettura su vw_dash_competenza_attivita (scope GUC
    #        fail-closed in vista); decode articolo via JOIN (display field).
    # Risultato: tuple (lista DashCompetenzaAttivitaRow, conteggio totale).
    # Colonne ordinabili del drill-down attivita' Lente 1 Competenza: chiave FE
    # (field colonna DataTable) -> espressione SQL. Note: la cella "articolo"
    # mostra la descrizione (fallback codice) -> si ordina per il valore
    # mostrato; la data si ordina per la COLONNA data (non la stringa gg/mm/aaaa
    # del FE). Whitelist: nell'ORDER BY solo chiavi note + ASC/DESC (no injection).
    DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS = {
        "commessa_codice": "a.commessa_codice",
        "cliente_display": "a.cliente_display",
        "articolo_codice": "COALESCE(art.descrizione, art.codice)",
        "data_attivita": "a.data_attivita",
        "valore": "a.valore",
    }

    def list_dash_competenza_attivita(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        solo_ritardo: bool,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaAttivitaRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = ["a.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("a.stadio = %s")
            params.append(stadio)
        if solo_ritardo:
            conditions.append("a.emessa_in_ritardo IS TRUE")

        where_clause = "WHERE " + " AND ".join(conditions)

        # ORDER BY server-side (corretto su TUTTE le pagine): colonna dalla
        # whitelist + direzione ASC/DESC, tiebreak stabile (commessa,
        # commessa_attivita_id). order_by assente/non ammesso -> default storico
        # (valore DESC).
        sort_col = self.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS.get(order_by or "")
        if sort_col is not None:
            direction = sql_order_direction(order_dir)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                "a.commessa_codice ASC, a.commessa_attivita_id ASC"
            )
        else:
            order_clause = (
                "ORDER BY a.valore DESC NULLS LAST, a.commessa_codice ASC, "
                "a.commessa_attivita_id ASC"
            )

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.vw_dash_competenza_attivita a
            {where_clause}
        """

        data_sql = f"""
            SELECT
                a.commessa_attivita_id,
                a.commessa_id,
                a.commessa_codice,
                a.cliente_display,
                a.articolo_id,
                art.codice          AS articolo_codice,
                art.descrizione     AS articolo_descrizione,
                a.data_attivita,
                a.quantita,
                a.stadio,
                a.stato_approvazione,
                a.stato_emissione,
                a.valore,
                a.data_emissione,
                a.emessa_in_ritardo,
                a.sospesa,
                a.posticipa_al,
                a.fattura_id,
                a.fattura_anno,
                a.fattura_serie,
                a.fattura_numero,
                a.stato_fattura_codice_interno,
                a.stato_fattura_codice,
                a.valore_fatturato,
                a.fattura_critical
            FROM vendite.vw_dash_competenza_attivita a
            LEFT JOIN catalogo.articoli art
                ON art.id = a.articolo_id
            {where_clause}
            {order_clause}
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[DashCompetenzaAttivitaRow] = []
        for row in rows:
            result.append(
                {
                    "commessa_attivita_id": int(row[0]),
                    "commessa_id": int(row[1]),
                    "commessa_codice": None if row[2] is None else str(row[2]),
                    "cliente_display": None if row[3] is None else str(row[3]),
                    "articolo_id": None if row[4] is None else str(row[4]),
                    "articolo_codice": None if row[5] is None else str(row[5]),
                    "articolo_descrizione": None if row[6] is None else str(row[6]),
                    "data_attivita": row[7].isoformat() if row[7] is not None else None,
                    "quantita": str(row[8]) if row[8] is not None else None,
                    "stadio": str(row[9]),
                    "stato_approvazione": None if row[10] is None else str(row[10]),
                    "stato_emissione": None if row[11] is None else str(row[11]),
                    "valore": str(row[12]) if row[12] is not None else None,
                    "data_emissione": row[13].isoformat() if row[13] is not None else None,
                    "emessa_in_ritardo": None if row[14] is None else bool(row[14]),
                    "sospesa": None if row[15] is None else bool(row[15]),
                    "posticipa_al": row[16].isoformat() if row[16] is not None else None,
                    "fattura_id": None if row[17] is None else int(row[17]),
                    "fattura_anno": None if row[18] is None else int(row[18]),
                    "fattura_serie": None if row[19] is None else str(row[19]),
                    "fattura_numero": None if row[20] is None else int(row[20]),
                    "stato_fattura_codice_interno": None if row[21] is None else str(row[21]),
                    "stato_fattura_codice": None if row[22] is None else str(row[22]),
                    "valore_fatturato": str(row[23]) if row[23] is not None else None,
                    "fattura_critical": bool(row[24]),
                }
            )
        return result, total_count

    # Scopo: Restituisce la lista paginata degli errori vivi (blocco 4 Lente 1:
    #        task run in ERRORE non superati + fatture critical), con filtro
    #        opzionale per mese di competenza.
    # Perimetro: sola lettura su vw_dash_competenza_errori (scope GUC in vista).
    # Risultato: tuple (lista DashCompetenzaErroreRow, conteggio totale).
    def list_dash_competenza_errori(
        self,
        *,
        competenza_mese: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaErroreRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if competenza_mese is not None:
            # date_trunc simmetrico al conteggio mensile: la competenza dei
            # lotti non e' vincolata al 1° del mese (nessun CHECK sul DB).
            conditions.append("date_trunc('month', e.competenza_mese)::date = %s")
            params.append(competenza_mese)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # La union (anti-join task_runs + LATERAL fatture_log) e' la query piu'
        # costosa della pagina: una sola valutazione + clamp offset via
        # _query_paged_view. La union non ha una PK: tiebreaker deterministico
        # su tutte le chiavi naturali (evento, lotto, fattura, task).
        select_sql = f"""
            SELECT
                e.tipo_evento,
                e.competenza_mese,
                e.lotto_id,
                e.lotto_codice,
                e.stato_lotto,
                e.fattura_id,
                e.fattura_anno,
                e.fattura_serie,
                e.fattura_numero,
                e.task_code,
                e.error_code,
                e.messaggio,
                e.data_evento
            FROM vendite.vw_dash_competenza_errori e
            {where_clause}
        """

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by="""
            ORDER BY data_evento DESC NULLS LAST, tipo_evento ASC,
                     lotto_id ASC NULLS LAST, fattura_id ASC NULLS LAST,
                     task_code ASC NULLS LAST
            """,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaErroreRow] = []
        for row in rows:
            result.append(
                {
                    "tipo_evento": str(row[0]),
                    "competenza_mese": row[1].isoformat() if row[1] is not None else None,
                    "lotto_id": None if row[2] is None else int(row[2]),
                    "lotto_codice": None if row[3] is None else str(row[3]),
                    "stato_lotto": None if row[4] is None else str(row[4]),
                    "fattura_id": None if row[5] is None else int(row[5]),
                    "fattura_anno": None if row[6] is None else int(row[6]),
                    "fattura_serie": None if row[7] is None else str(row[7]),
                    "fattura_numero": None if row[8] is None else int(row[8]),
                    "task_code": None if row[9] is None else str(row[9]),
                    "error_code": None if row[10] is None else str(row[10]),
                    "messaggio": None if row[11] is None else str(row[11]),
                    "data_evento": row[12].isoformat() if row[12] is not None else None,
                }
            )
        return result, total_count

    # Scopo: Restituisce i contatori del backlog (Lente 2) a grana
    #        classe × area — il pivot per classe (3 classi sempre presenti)
    #        e' a carico del service.
    # Perimetro: sola lettura su vw_dash_backlog_riepilogo (RLS invoker sulle
    #        6 aree documento + rami resi + scope GUC nel resolver commesse).
    # Risultato: lista DashBacklogRiepilogoRow delle sole coppie non vuote.
    def list_dash_backlog_riepilogo(self) -> list[DashBacklogRiepilogoRow]:
        # GREATEST: data_riferimento futura (es. mese esploso contratti o
        # documento post-datato) produrrebbe anzianita' negativa — un "fermo
        # da -N giorni" non ha senso operativo, si legge come 0.
        sql = """
            SELECT
                classe,
                area,
                n_documenti,
                valore_fermo_tot,
                unita_ferme_tot,
                GREATEST(anzianita_max_giorni, 0) AS anzianita_max_giorni
            FROM vendite.vw_dash_backlog_riepilogo
            ORDER BY classe, area
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        result: list[DashBacklogRiepilogoRow] = []
        for row in rows:
            result.append(
                {
                    "classe": str(row[0]),
                    "area": str(row[1]),
                    "n_documenti": int(row[2]),
                    "valore_fermo_tot": str(row[3]) if row[3] is not None else None,
                    "unita_ferme_tot": int(row[4]) if row[4] is not None else 0,
                    "anzianita_max_giorni": None if row[5] is None else int(row[5]),
                }
            )
        return result

    # Scopo: Restituisce la lista paginata del backlog (Lente 2): documenti
    #        non-collegati non-verdi ordinati per anzianita' (i piu' vecchi
    #        prima — l'ordinamento e' BE-side per contratto, le viste non
    #        garantiscono ORDER; si ordina su data_riferimento ASC, colonna
    #        base equivalente ad anzianita' DESC ma piu' amichevole per il
    #        planner), con filtri opzionali per classe e area. Il filtro
    #        classe NON e' whitellistato: coerenza fail-visible col riepilogo
    #        (una classe futura del CHECK resta drillabile; sconosciuta =>
    #        lista vuota, mai 400).
    # Perimetro: sola lettura su vw_dash_backlog_documenti (union resolver:
    #        RLS invoker + scope GUC commesse). Una sola valutazione della
    #        union + clamp offset via _query_paged_view.
    # Risultato: tuple (lista DashBacklogDocumentoRow, conteggio totale).
    # Colonne ordinabili del backlog fatturazione: chiave FE (field della colonna
    # DataTable) -> colonna della CTE `righe`. Whitelist: nell'ORDER BY entrano
    # solo chiavi note + direzione ASC/DESC (no SQL injection). Convenzione
    # order_by/order_dir come le liste standard, gemella di DASH_APERTO_SORT_COLUMNS.
    DASH_BACKLOG_SORT_COLUMNS = {
        "anzianita_giorni": "anzianita_giorni",
        "area": "area",
        "codice": "codice",
        "cliente_display": "cliente_display",
        "valore_fermo": "valore_fermo",
        "stato_codice": "stato_codice",
    }

    def list_dash_backlog_documenti(
        self,
        *,
        classe: str | None,
        area: str | None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashBacklogDocumentoRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if classe is not None:
            conditions.append("d.classe = %s")
            params.append(classe)
        if area is not None:
            conditions.append("d.area = %s")
            params.append(area)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_sql = f"""
            SELECT
                d.area,
                d.competenza_mese,
                d.documento_id,
                d.documento_uid,
                d.codice,
                d.cliente_display,
                d.valore_fermo,
                d.unita_ferme,
                d.motivo_fermo,
                d.classe,
                d.azione,
                d.data_riferimento,
                GREATEST(d.anzianita_giorni, 0) AS anzianita_giorni,
                d.stato_codice_interno,
                d.stato_codice,
                d.fase
            FROM vendite.vw_dash_backlog_documenti d
            {where_clause}
        """

        # ORDER BY server-side (corretto su TUTTE le pagine): colonna dalla
        # whitelist DASH_BACKLOG_SORT_COLUMNS + direzione ASC/DESC, tiebreak
        # stabile (area, documento_id). order_by assente/non ammesso -> ordine
        # storico "fermo da" (i piu' vecchi prima).
        sort_col = self.DASH_BACKLOG_SORT_COLUMNS.get(order_by or "")
        if sort_col is not None:
            direction = sql_order_direction(order_dir)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                "area ASC, documento_id ASC"
            )
        else:
            order_clause = """
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_fermo DESC NULLS LAST,
                     area ASC, documento_id ASC
            """

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashBacklogDocumentoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "competenza_mese": row[1].isoformat() if row[1] is not None else None,
                    "documento_id": int(row[2]),
                    "documento_uid": None if row[3] is None else str(row[3]),
                    "codice": None if row[4] is None else str(row[4]),
                    "cliente_display": None if row[5] is None else str(row[5]),
                    "valore_fermo": str(row[6]) if row[6] is not None else None,
                    "unita_ferme": None if row[7] is None else int(row[7]),
                    "motivo_fermo": str(row[8]),
                    "classe": str(row[9]),
                    "azione": None if row[10] is None else str(row[10]),
                    "data_riferimento": row[11].isoformat() if row[11] is not None else None,
                    "anzianita_giorni": None if row[12] is None else int(row[12]),
                    "stato_codice_interno": None if row[13] is None else str(row[13]),
                    "stato_codice": None if row[14] is None else str(row[14]),
                    "fase": None if row[15] is None else str(row[15]),
                }
            )
        return result, total_count

    # Scopo: Restituisce elenco fatture di un lotto con decodifiche e filtri opzionali.
    # Obiettivo: lista paginata per lotto_id con JOIN anagrafiche, SDI, stato doc fiscale.
    # Perimetro: sola lettura; nessun side-effect.
    # Risultato: tuple (lista LottoFattureRow, conteggio totale).
    def list_lotto_fatture(
        self,
        *,
        lotto_id: int,
        stato_esecuzione: str | None,
        esclusa: bool | None,
        auth_user_id: int | None = None,
        sort_by: str,
        sort_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[LottoFattureRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        # Ordinamento: solo valori dalla whitelist entrano nella query.
        sort_col = _SORT_COLUMNS.get(sort_by, "fllf.fattura_id")
        safe_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"
        order_clause = f"{sort_col} {safe_dir}"
        if sort_by != "fattura_id":
            order_clause += ", fllf.fattura_id ASC"

        # WHERE obbligatorio su lotto_id; filtri opzionali aggiunti dinamicamente.
        conditions: list[str] = ["fllf.lotto_id = %s"]
        params: list[Any] = [lotto_id]

        if stato_esecuzione is not None:
            conditions.append("fllf.stato_esecuzione = %s")
            params.append(stato_esecuzione)
        if esclusa is not None:
            conditions.append("fllf.esclusa = %s")
            params.append(esclusa)

        self._add_scope_emittente(
            auth_user_id, "f.emittente_soggetto_ruolo_id", conditions, params
        )

        where_clause = "WHERE " + " AND ".join(conditions)

        joins = """
            INNER JOIN vendite.fatture f
                ON f.id = fllf.fattura_id
            INNER JOIN anagrafiche.billing_account ba
                ON ba.id = f.billing_account_id
            INNER JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
            LEFT JOIN config.stati_sdi ssdi
                ON ssdi.id = fllf.stato_sdi_id
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = fllf.stato_doc_fiscale_id
        """

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.fatturazione_lotti_fatture fllf
            {joins}
            {where_clause}
        """

        data_sql = f"""
            SELECT
                fllf.id,
                fllf.lotto_id,
                fllf.fattura_id,
                fllf.stato_sdi_id,
                ssdi.descrizione        AS stato_sdi_descrizione,
                fllf.stato_doc_fiscale_id,
                sdf.descrizione         AS stato_doc_fiscale_descrizione,
                fllf.stato_esecuzione,
                fllf.esclusa,
                f.numero,
                f.serie,
                f.data,
                f.billing_account_id,
                f.totale_doc,
                f.totale_a_pagare,
                srd.soggetto_id,
                srd.ragione_sociale_completa,
                srd.id_fiscale_univoco_cf_piva,
                sdf.codice_interno      AS stato_doc_fiscale_codice
            FROM vendite.fatturazione_lotti_fatture fllf
            {joins}
            {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[LottoFattureRow] = []
        for row in rows:
            result.append(
                {
                    "id": int(row[0]),
                    "lotto_id": int(row[1]),
                    "fattura_id": int(row[2]),
                    "stato_sdi_id": None if row[3] is None else int(row[3]),
                    "stato_sdi_descrizione": row[4],
                    "stato_doc_fiscale_id": None if row[5] is None else int(row[5]),
                    "stato_doc_fiscale_descrizione": row[6],
                    "stato_esecuzione": str(row[7]),
                    "esclusa": bool(row[8]),
                    "numero": None if row[9] is None else int(row[9]),
                    "serie": row[10],
                    "data": row[11].isoformat() if row[11] is not None else None,
                    "billing_account_id": int(row[12]),
                    "totale_doc": str(row[13]) if row[13] is not None else None,
                    "totale_a_pagare": str(row[14]) if row[14] is not None else None,
                    "soggetto_id": int(row[15]),
                    "ragione_sociale_completa": row[16],
                    "id_fiscale_univoco_cf_piva": row[17],
                    "stato_doc_fiscale_codice": row[18],
                }
            )
        return result, total_count

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Fattura (generazione documento / stampa, C-2)
    #  Read-side per il motore documentale (sorgente FATTURA). La fattura
    #  non ha un repository dedicato: i read vivono qui, accanto a
    #  list_lotto_fatture (convenzione AGENTS.md — `<schema>_repository`
    #  per le operazioni generiche vendite che non sono un sottodominio
    #  con orchestrazione propria).
    # ══════════════════════════════════════════════════════════

    # Scopo: Contesto minimo per la generazione documento (stampa PDF) della
    #        fattura. Mirror di OrdiniRepository.get_for_documento_generation,
    #        con la differenza-chiave FATTURA: la testata espone
    #        `emittente_soggetto_ruolo_id` (SR), mentre il motore documentale
    #        vuole `emittente_fiscale_id` (PK). Si risolve la PK con JOIN a
    #        anagrafiche.emittenti_fiscali (1:1 garantito da
    #        uq_emittenti_fiscali_ruolo) — memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo. LEFT JOIN, non INNER: se
    #        il record EF manca (dato sporco), la fattura ESISTE con
    #        emittente_fiscale_id NULL → il BB `resolve_contesto_documentale`
    #        distingue "non trovata" (404) da "emittente non risolto"
    #        (validation parlante); un INNER collasserebbe i due casi. Ritorna
    #        {id, uid, emittente_fiscale_id}; None se id inesistente o fuori
    #        scope RLS (indistinguibile per design → 404 unificato nel caller).
    def get_fattura_for_documento_generation(
        self, fattura_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.uid::text AS uid,
                ef.id       AS emittente_fiscale_id
              FROM vendite.fatture f
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return row_to_dict(cursor)

    # Scopo: Testata fattura per il context builder documentale (stampa).
    #        Denormalizza cliente (BA → soggetto), emittente (SR → EF PK+codice),
    #        stato/tipo doc fiscale e valuta; espone i totali di testata così
    #        come li mantiene la pipeline (`*_tot`, bollo, arrotondamento,
    #        totale_a_pagare). Lettura pura: nessun calcolo fiscale in Python.
    #        None se la fattura non esiste (o è fuori scope RLS).
    def get_fattura_testata(self, fattura_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.uid::text                  AS uid,
                f.anno,
                f.serie,
                f.numero,
                f.data,
                f.tipo_doc_fiscale_id,
                tdf.codice_interno           AS tipo_doc_fiscale_codice,
                tdf.descrizione              AS tipo_doc_fiscale_descrizione,
                f.stato_doc_fiscale_id,
                sdf.codice_interno           AS stato_codice_interno,
                sdf.descrizione              AS stato_descrizione,
                f.emittente_soggetto_ruolo_id,
                ef.id                        AS emittente_fiscale_id,
                ef.codice                    AS emittente_fiscale_codice,
                f.billing_account_id,
                ba.codice                    AS ba_codice,
                ba.soggetto_ruolo_id         AS cliente_soggetto_ruolo_id,
                srd.soggetto_id,
                srd.ragione_sociale_completa,
                srd.id_fiscale_univoco_cf_piva,
                f.valuta_id,
                val.iso_code                 AS valuta_codice,
                f.tasso_cambio,
                f.imponibile_tot,
                f.imposta_tot,
                f.bollo_applicato,
                f.bollo_importo,
                f.arrotondamento_attuale,
                f.totale_doc,
                f.totale_a_pagare,
                f.data_contabilizzazione,
                f.meta
              FROM vendite.fatture f
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
              JOIN anagrafiche.billing_account ba
                ON ba.id = f.billing_account_id
              JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
              LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = f.tipo_doc_fiscale_id
              LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = f.stato_doc_fiscale_id
              LEFT JOIN config.valute val
                ON val.id = f.valuta_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return row_to_dict(cursor)

    # Scopo: Righe fattura con decodifiche articolo/uom/iva per il context
    #        builder. Espone gli importi di riga già mantenuti dal DB
    #        (imponibile/imposta/totale) + `iva_natura` per le righe non
    #        imponibili. Ordine stabile per riga_nr. Lettura pura.
    def list_fattura_righe(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                r.id,
                r.fattura_id,
                r.riga_nr,
                r.articolo_id,
                a.codice            AS articolo_codice,
                a.descrizione       AS articolo_descrizione,
                r.descrizione,
                r.uom_id,
                um.codice           AS uom_codice,
                r.qta,
                r.prezzo_unitario,
                r.sconto_percentuale,
                r.iva_id,
                iva.codice          AS iva_codice,
                iva.descrizione     AS iva_descrizione,
                iva.aliquota_iva    AS iva_aliquota,
                r.iva_natura,
                r.imponibile_riga,
                r.imposta_riga,
                r.totale_riga
              FROM vendite.fatture_righe r
              LEFT JOIN catalogo.articoli a      ON a.id  = r.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_id
              LEFT JOIN config.iva iva           ON iva.id = r.iva_id
             WHERE r.fattura_id = %s
             ORDER BY r.riga_nr, r.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # Scopo: Riepilogo IVA della fattura, letto dalla tabella REALE
    #        `vendite.fatture_riepiloghi_iva` (a differenza degli ordini, che
    #        derivano il riepilogo on-the-fly da una vista): una riga per
    #        gruppo (iva/natura/esigibilità/split). Decodifica iva + natura via
    #        JOIN (display field). Lettura pura: gli importi sono già
    #        aggregati/arrotondati dalla pipeline di fatturazione.
    def list_fattura_riepilogo_iva(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                ri.id,
                ri.fattura_id,
                ri.iva_id,
                iva.codice          AS iva_codice,
                iva.descrizione     AS iva_descrizione,
                iva.aliquota_iva    AS iva_aliquota,
                ri.natura_id,
                nat.codice          AS natura_codice,
                ri.esigibilita,
                ri.split_payment,
                ri.imponibile,
                ri.imposta,
                ri.arrotondamento
              FROM vendite.fatture_riepiloghi_iva ri
              LEFT JOIN config.iva iva        ON iva.id  = ri.iva_id
              LEFT JOIN config.iva_natura nat ON nat.id  = ri.natura_id
             WHERE ri.fattura_id = %s
             ORDER BY iva.aliquota_iva NULLS LAST, ri.iva_id NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # ------------------------------------------------------------------
    # Lineage documenti (genealogia/transiti — brief-be-fe-lineage)
    # Letture generiche sulla famiglia vw_documento_lineage* +
    # fn_documento_lineage. Tutte security_invoker/SECURITY INVOKER: la
    # RLS emittente del chiamante si applica da sola (niente auth_user_id).
    # ------------------------------------------------------------------

    # Scopo: Risolve una sorgente lineage da config.sorgenti per
    #        codice_interno (chiave stabile): id, key_selector e tabella
    #        target per la traduzione doc_id -> chiave nodo polimorfa.
    def get_lineage_sorgente(self, codice_interno: str) -> LineageSorgenteRow | None:
        sql = """
            SELECT s.id, s.key_selector, s.target_table::text
            FROM config.sorgenti s
            WHERE s.codice_interno = %s
              AND s.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": int(row[0]),
            "key_selector": str(row[1]),
            "target_table": str(row[2]),
        }

    # Scopo: Traduce il doc_id di dominio nella chiave nodo lineage secondo
    #        la convenzione key_selector (config manual sorgenti): 'id' ->
    #        id::text senza round-trip; 'uid' -> SELECT uid dalla tabella
    #        target. Ritorna None se il documento non esiste (o e' fuori
    #        scope RLS: indistinguibile per design).
    def resolve_lineage_node_uid(
        self, *, target_table: str, key_selector: str, doc_id: int
    ) -> str | None:
        if key_selector == "id":
            return str(doc_id)
        # Guardia identifier: target_table viene da config.sorgenti
        # (regclass seedata), mai da input utente — la regex intercetta
        # solo dati sporchi da refactor (stesso pattern del repo note).
        if not re.fullmatch(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?", target_table):
            raise ValueError(f"target_table non valida: {target_table!r}")
        sql = f"SELECT uid::text FROM {target_table} WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [doc_id])
            row = cursor.fetchone()
        return None if not row else str(row[0])

    # Scopo: Riga summary lineage di un documento (nodo + pratica +
    #        frontiera + contatori) da vw_documento_lineage, con decodifica
    #        dei tipi in codice_interno via JOIN a config.sorgenti (mai id
    #        numerici verso il FE). None se il nodo non esiste.
    def get_lineage_nodo(self, *, tipo_id: int, node_uid: str) -> LineageNodoRow | None:
        sql = """
            SELECT
                l.tipo_id,
                s.codice_interno            AS tipo_codice,
                l.uid,
                l.codice,
                l.stato_codice_interno,
                l.stato_codice,
                l.stato_descrizione,
                l.fase,
                l.is_abortito,
                l.pratica_id,
                l.pratica_numero,
                l.n_pratiche,
                l.frontiera_tipo_id,
                sf.codice_interno           AS frontiera_tipo_codice,
                l.frontiera_uid,
                l.frontiera_codice,
                l.frontiera_stato_codice_interno,
                l.frontiera_fase,
                l.n_discendenti_diretti,
                l.n_discendenti_attivi,
                l.is_transitato,
                l.n_sorgenti,
                l.root_codice
            FROM vendite.vw_documento_lineage l
            JOIN config.sorgenti s ON s.id = l.tipo_id
            LEFT JOIN config.sorgenti sf ON sf.id = l.frontiera_tipo_id
            WHERE l.tipo_id = %s
              AND l.uid = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_id, node_uid])
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "tipo_id": int(row[0]),
            "tipo_codice": str(row[1]),
            "uid": str(row[2]),
            "codice": row[3],
            "stato_codice_interno": row[4],
            "stato_codice": row[5],
            "stato_descrizione": row[6],
            "fase": row[7],
            "is_abortito": bool(row[8]),
            "pratica_id": None if row[9] is None else int(row[9]),
            "pratica_numero": row[10],
            "n_pratiche": int(row[11]),
            "frontiera_tipo_id": None if row[12] is None else int(row[12]),
            "frontiera_tipo_codice": row[13],
            "frontiera_uid": row[14],
            "frontiera_codice": row[15],
            "frontiera_stato_codice_interno": row[16],
            "frontiera_fase": row[17],
            "n_discendenti_diretti": int(row[18]),
            "n_discendenti_attivi": int(row[19]),
            "is_transitato": bool(row[20]),
            "n_sorgenti": int(row[21]),
            "root_codice": row[22],
        }

    # Scopo: Catena dei passaggi di un documento via
    #        fn_documento_lineage(tipo, uid, direzione), decodificando i
    #        tipi degli estremi in codice_interno (JOIN config.sorgenti).
    #        Ordine stabile per il rendering timeline (colonna `ordine`).
    def list_lineage_passaggi(
        self, *, tipo_id: int, node_uid: str, direzione: str
    ) -> list[LineagePassaggioRow]:
        sql = """
            SELECT
                p.livello,
                p.ordine,
                p.arco,
                p.ruolo,
                p.from_tipo_id,
                sf.codice_interno           AS from_tipo_codice,
                p.from_uid,
                p.from_codice,
                nf.stato_codice_interno     AS from_stato_codice_interno,
                nf.fase                     AS from_fase,
                -- Id numerico apribile nel drawer di dettaglio: uid::bigint
                -- per i tipi id-keyed; traduzione uuid->id per preventivo/
                -- offerta (unici key_selector='uid'). NULL = fuori scope RLS
                -- o nodo senza drawer (fattura/commessa) -> FE non apre.
                COALESCE(pfrom.id, ofrom.id,
                    CASE WHEN sf.key_selector = 'id'
                         THEN NULLIF(p.from_uid, '')::bigint END) AS from_doc_id,
                p.to_tipo_id,
                st.codice_interno           AS to_tipo_codice,
                p.to_uid,
                p.to_codice,
                p.to_stato_codice_interno,
                p.to_fase,
                p.to_is_abortito,
                COALESCE(pto.id, oto.id,
                    CASE WHEN st.key_selector = 'id'
                         THEN NULLIF(p.to_uid, '')::bigint END) AS to_doc_id,
                p.is_ramo_inverso
            FROM vendite.fn_documento_lineage(%s, %s, %s) p
            LEFT JOIN config.sorgenti sf ON sf.id = p.from_tipo_id
            LEFT JOIN config.sorgenti st ON st.id = p.to_tipo_id
            LEFT JOIN vendite.vw_documento_lineage_nodi nf
                   ON nf.tipo_id = p.from_tipo_id AND nf.uid = p.from_uid
            LEFT JOIN vendite.preventivi pfrom
                   ON sf.codice_interno = 'PREVENTIVO' AND pfrom.uid::text = p.from_uid
            LEFT JOIN vendite.offerte_commerciali ofrom
                   ON sf.codice_interno = 'OFFERTA_COMMERCIALE' AND ofrom.uid::text = p.from_uid
            LEFT JOIN vendite.preventivi pto
                   ON st.codice_interno = 'PREVENTIVO' AND pto.uid::text = p.to_uid
            LEFT JOIN vendite.offerte_commerciali oto
                   ON st.codice_interno = 'OFFERTA_COMMERCIALE' AND oto.uid::text = p.to_uid
            ORDER BY p.ordine
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_id, node_uid, direzione])
            rows = cursor.fetchall()

        result: list[LineagePassaggioRow] = []
        for row in rows:
            result.append(
                {
                    "livello": int(row[0]),
                    "ordine": int(row[1]),
                    "arco": str(row[2]),
                    "ruolo": row[3],
                    "from_tipo_id": int(row[4]),
                    "from_tipo_codice": row[5],
                    "from_uid": str(row[6]),
                    "from_codice": row[7],
                    "from_stato_codice_interno": row[8],
                    "from_fase": row[9],
                    "from_doc_id": None if row[10] is None else int(row[10]),
                    "to_tipo_id": int(row[11]),
                    "to_tipo_codice": row[12],
                    "to_uid": str(row[13]),
                    "to_codice": row[14],
                    "to_stato_codice_interno": row[15],
                    "to_fase": row[16],
                    "to_is_abortito": bool(row[17]),
                    "to_doc_id": None if row[18] is None else int(row[18]),
                    "is_ramo_inverso": bool(row[19]),
                }
            )
        return result
