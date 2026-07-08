# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema vendite (query, liste, decodifiche).
# ------------------------------------------------------------

# Contiene operazioni generiche sullo schema vendite che non appartengono
# a nessun sottodominio specifico (pipeline, reset, ecc.).

from datetime import date
from typing import Any

from django.db import connection

from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashBacklogRiepilogoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaMensileRow,
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
# brief-design-dashboard-fatturazione §4). Allineate al discriminante `area`
# della union vendite.vw_dash_fatturazione_documenti. Usate dalla Lente 2
# Backlog (che include COMMESSE).
DASH_FATTURAZIONE_AREE: tuple[str, ...] = (
    "PREVENTIVI",
    "ORDINI",
    "OFFERTE",
    "CONTRATTI",
    "COMMESSE",
)

# Aree con valore monetario (imponibile, decisione D-4). OFFERTE e CONTRATTI
# restano a conteggi (decisioni D-2/D-3 confermate da DL-11): valore_* = NULL.
DASH_FATTURAZIONE_AREE_EURO: frozenset[str] = frozenset(
    {"PREVENTIVI", "ORDINI", "COMMESSE"}
)

# Aree della Situazione aperta (stock documenti, §6-bis design due-lenti):
# le 4 aree documento nell'ordine del funnel — NIENTE COMMESSE (coperte
# dalla Lente 1). Allineate al WHERE di vendite.vw_dash_aperto_documenti.
DASH_APERTO_AREE: tuple[str, ...] = (
    "PREVENTIVI",
    "ORDINI",
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
# vendite.vw_dash_competenza_attivita.
DASH_COMPETENZA_STADI: tuple[str, ...] = (
    "DA_APPROVARE",
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

    # Scopo: Esegue una query paginata su vista/union costosa in UNA SOLA
    #        valutazione: CTE materializzata + COUNT(*) OVER() + OFFSET
    #        clampato all'ultima pagina direttamente in SQL. Il rientro da
    #        una pagina stantia (lista ridotta da altri utenti) non costa
    #        piu' 2-3 valutazioni della union (data vuota + count fallback +
    #        refetch FE): il BE serve subito l'ultima pagina reale e il
    #        service dichiara la pagina effettiva nell'envelope. Estratto
    #        2026-07-07 (regola del 2 alla 3ª occorrenza + fix efficienza,
    #        ok Tid): unifica il pattern di aperto/backlog/errori.
    #        `select_sql` = SELECT...FROM...WHERE gia' parametrizzato, SENZA
    #        ORDER/LIMIT; `order_by` = clausola ORDER BY completa su NOMI
    #        COLONNA DI OUTPUT della SELECT (whitelist a carico del
    #        chiamante, MAI input utente). Ritorna (rows, total_count):
    #        total_count e' SEMPRE l'ultima colonna delle righe.
    def _query_paged_view(
        self,
        *,
        select_sql: str,
        order_by: str,
        params: list[Any],
        limit: int,
        offset: int,
    ) -> tuple[list[tuple], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        # MATERIALIZED esplicito: la CTE e' referenziata due volte (righe +
        # count del clamp) e deve essere valutata una volta sola.
        sql = f"""
            WITH righe AS MATERIALIZED (
                {select_sql}
            )
            SELECT r.*, COUNT(*) OVER () AS total_count
            FROM righe r
            {order_by}
            LIMIT %s
            OFFSET LEAST(
                %s,
                (SELECT GREATEST(COUNT(*) - 1, 0) / %s * %s FROM righe)
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql, params + [safe_limit, safe_offset, safe_limit, safe_limit]
            )
            rows = cursor.fetchall()
        total_count = int(rows[0][-1]) if rows else 0
        return list(rows), total_count

    # Scopo: Aggiunge la condizione WHERE per scope emittente DB-first.
    # La funzione SQL risolve ruolo, whitelist e mappatura soggetto_ruolo.
    @staticmethod
    def _add_scope_emittente(
        auth_user_id: int | None,
        field: str,
        conditions: list[str],
        params: list[Any],
    ) -> None:
        if auth_user_id is not None:
            conditions.append(
                f"(script.fn_get_emittenti_scope_sr_ids(%s) IS NULL "
                f"OR {field} = ANY("
                f"script.fn_get_emittenti_scope_sr_ids(%s)))"
            )
            params.extend([auth_user_id, auth_user_id])

    # Scopo: Restituisce elenco lotti paginato con JOIN decodifica e filtri opzionali.
    # Obiettivo: lista generica fatturazione_lotti con decodifiche config.
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

        joins = """
            LEFT JOIN config.utilities u
                ON u.id = fl.utility_id
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = fl.stato_doc_fiscale_id
            LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = fl.tipo_doc_fiscale_id
            LEFT JOIN vendite.area_geografica_fatturazione agf
                ON agf.id = fl.area_geografica_id
        """

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.fatturazione_lotti fl
            {joins}
            {where_clause}
        """

        data_sql = f"""
            SELECT
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

        result: list[LottoListRow] = []
        for row in rows:
            result.append(
                {
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
            )
        return result, total_count

    # Scopo: Restituisce le celle non vuote (area × fase) del serbatoio
    #        pre-commessa. Il completamento a griglia 4 aree × 3 fasi
    #        (celle vuote = zeri, DL-13) e' a carico del service — qui NON si
    #        duplica, si legge solo cio' che esiste.
    # Perimetro: sola lettura su vw_dash_aperto_riepilogo v2 (security_invoker →
    #        la RLS emittente sulle 4 aree documento filtra da sola; perimetro
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
    #        (vw_dash_aperto_documenti v2: 4 aree documento, perimetro
    #        aperti-non-chiusi lato vista), con filtri opzionali area/fase e
    #        ritardo_giorni ("aperti da oltre N giorni" su data_riferimento,
    #        DL-17). anzianita_giorni derivata in SELECT (GREATEST). Ordinamento
    #        BE-side (le viste non garantiscono ORDER): piu' vecchio prima, poi
    #        valore.
    # Perimetro: sola lettura; scope emittente interamente DB-side (RLS
    #        invoker sulle 4 aree documento). Una sola valutazione della
    #        union + clamp offset via _query_paged_view.
    # Risultato: tuple (lista DashApertoDocumentoRow, conteggio totale).
    def list_dash_aperto_documenti(
        self,
        *,
        area: str | None,
        fase: str | None,
        ritardo_giorni: int | None,
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

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by="""
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_totale DESC NULLS LAST,
                     area ASC, documento_id ASC
            """,
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
    def list_dash_competenza_attivita(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        solo_ritardo: bool,
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
            ORDER BY a.valore DESC NULLS LAST, a.commessa_codice ASC,
                     a.commessa_attivita_id ASC
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
    #        4 aree documento + scope GUC nel resolver commesse).
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
    def list_dash_backlog_documenti(
        self,
        *,
        classe: str | None,
        area: str | None,
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

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by="""
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_fermo DESC NULLS LAST,
                     area ASC, documento_id ASC
            """,
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
                srd.id_fiscale_univoco_cf_piva
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
                }
            )
        return result, total_count
