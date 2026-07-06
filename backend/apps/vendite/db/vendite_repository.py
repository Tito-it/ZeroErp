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
    DashBacklogDocumentoRow,
    DashBacklogRiepilogoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaMensileRow,
    DashFatturazioneFermoRow,
    LottoFattureRow,
    LottoListRow,
)

# Whitelist colonne ordinamento per list_lotto_fatture; mai interpolate direttamente.
_SORT_COLUMNS: dict[str, str] = {
    "fattura_id": "fllf.fattura_id",
    "nominativo": "srd.ragione_sociale_completa",
    "totale_doc": "f.totale_doc",
}

# Aree della dashboard fatturazione, nell'ordine del funnel (brief
# brief-design-dashboard-fatturazione §4). Allineate al discriminante `area`
# della union vendite.vw_dash_fatturazione_documenti.
DASH_FATTURAZIONE_AREE: tuple[str, ...] = (
    "PREVENTIVI",
    "ORDINI",
    "OFFERTE",
    "CONTRATTI",
    "COMMESSE",
)

# Aree con valore monetario (imponibile, decisione D-4). OFFERTE e CONTRATTI
# restano a conteggi in v1 (decisioni D-2/D-3): valore_* = NULL.
DASH_FATTURAZIONE_AREE_EURO: frozenset[str] = frozenset(
    {"PREVENTIVI", "ORDINI", "COMMESSE"}
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

    # Scopo: Restituisce le righe non vuote (area × mese) dell'aggregata
    #        dashboard fatturazione per un anno. Il completamento a griglia
    #        12 mesi × 5 aree (contratto D-5: mesi/aree vuoti = zeri) è a carico
    #        del service — qui NON si duplica, si legge solo ciò che esiste.
    # Perimetro: sola lettura su vw_dash_fatturazione_mensile (invoker → la RLS
    #        emittente su preventivi/ordini/offerte/contratti filtra da sola).
    # Risultato: lista piatta delle sole (area, mese) con almeno un documento
    #        (≤ 60 righe).
    def list_dash_fatturazione_mensile(self, *, anno: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                competenza_mese,
                area,
                valore_totale,
                valore_transitato,
                n_documenti,
                n_transitati,
                n_fermi,
                n_abortiti
            FROM vendite.vw_dash_fatturazione_mensile
            WHERE competenza_mese >= make_date(%s, 1, 1)
              AND competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            ORDER BY competenza_mese, area
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [anno, anno])
            rows = cursor.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "competenza_mese": row[0].isoformat(),
                    "area": str(row[1]),
                    "valore_totale": str(row[2]) if row[2] is not None else None,
                    "valore_transitato": str(row[3]) if row[3] is not None else None,
                    "n_documenti": int(row[4]),
                    "n_transitati": int(row[5]),
                    "n_fermi": int(row[6]),
                    "n_abortiti": int(row[7]),
                }
            )
        return result

    # Scopo: Restituisce il drill-down paginato degli elementi FERMI di
    #        un'area in un mese di competenza (vw_dash_fatturazione_documenti,
    #        predicato NOT is_transitato AND NOT is_abortito).
    # Perimetro: sola lettura; lo scope emittente e' interamente DB-side —
    #        RLS invoker per le 4 aree documento, filtro nel resolver
    #        vw_dash_fatturazione_commesse via GUC app.current_user_id per le
    #        COMMESSE (migration 20260703-60). Nessun filtro applicativo qui.
    # Risultato: tuple (lista DashFatturazioneFermoRow, conteggio totale).
    def list_dash_fatturazione_fermi(
        self,
        *,
        area: str,
        competenza_mese: date,
        limit: int,
        offset: int,
    ) -> tuple[list[DashFatturazioneFermoRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = [
            "d.area = %s",
            "d.competenza_mese = %s",
            "NOT d.is_transitato",
            "NOT d.is_abortito",
        ]
        params: list[Any] = [area, competenza_mese]

        where_clause = "WHERE " + " AND ".join(conditions)

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.vw_dash_fatturazione_documenti d
            {where_clause}
        """

        data_sql = f"""
            SELECT
                d.documento_id,
                d.documento_uid,
                d.codice,
                d.cliente_display,
                d.valore_totale,
                d.valore_transitato,
                d.unita_totali,
                d.unita_transitate,
                d.motivo_fermo,
                d.stato_codice_interno,
                d.stato_codice,
                d.fase
            FROM vendite.vw_dash_fatturazione_documenti d
            {where_clause}
            ORDER BY d.valore_totale DESC NULLS LAST, d.codice ASC, d.documento_id ASC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[DashFatturazioneFermoRow] = []
        for row in rows:
            result.append(
                {
                    "documento_id": int(row[0]),
                    "documento_uid": None if row[1] is None else str(row[1]),
                    "codice": None if row[2] is None else str(row[2]),
                    "cliente_display": None if row[3] is None else str(row[3]),
                    "valore_totale": str(row[4]) if row[4] is not None else None,
                    "valore_transitato": str(row[5]) if row[5] is not None else None,
                    "unita_totali": None if row[6] is None else int(row[6]),
                    "unita_transitate": None if row[7] is None else int(row[7]),
                    "motivo_fermo": None if row[8] is None else str(row[8]),
                    "stato_codice_interno": None if row[9] is None else str(row[9]),
                    "stato_codice": None if row[10] is None else str(row[10]),
                    "fase": None if row[11] is None else str(row[11]),
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
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []
        if competenza_mese is not None:
            # date_trunc simmetrico al conteggio mensile: la competenza dei
            # lotti non e' vincolata al 1° del mese (nessun CHECK sul DB).
            conditions.append("date_trunc('month', e.competenza_mese)::date = %s")
            params.append(competenza_mese)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # La union (anti-join task_runs + LATERAL fatture_log) e' la query piu'
        # costosa della pagina: COUNT(*) OVER() nella stessa query evita di
        # valutarla due volte. La union non ha una PK: tiebreaker deterministico
        # su tutte le chiavi naturali (evento, lotto, fattura, task).
        data_sql = f"""
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
                e.data_evento,
                COUNT(*) OVER () AS total_count
            FROM vendite.vw_dash_competenza_errori e
            {where_clause}
            ORDER BY e.data_evento DESC NULLS LAST, e.tipo_evento ASC,
                     e.lotto_id ASC NULLS LAST, e.fattura_id ASC NULLS LAST,
                     e.task_code ASC NULLS LAST
            LIMIT %s OFFSET %s
        """

        # Fallback COUNT separato SOLO per offset oltre l'ultima pagina (zero
        # righe ma popolazione non vuota): serve al FE per il rientro in
        # pagina 1 (usePagedDashFetch controlla count > 0).
        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.vw_dash_competenza_errori e
            {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()
            if rows:
                total_count = int(rows[0][13])
            elif safe_offset > 0:
                cursor.execute(count_sql, params)
                row = cursor.fetchone()
                assert row is not None
                total_count = int(row[0])
            else:
                total_count = 0

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
    #        RLS invoker + scope GUC commesse). COUNT(*) OVER() nella stessa
    #        query: la union e' la parte costosa, si valuta una volta sola.
    # Risultato: tuple (lista DashBacklogDocumentoRow, conteggio totale).
    def list_dash_backlog_documenti(
        self,
        *,
        classe: str | None,
        area: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashBacklogDocumentoRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []
        if classe is not None:
            conditions.append("d.classe = %s")
            params.append(classe)
        if area is not None:
            conditions.append("d.area = %s")
            params.append(area)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        data_sql = f"""
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
                d.fase,
                COUNT(*) OVER () AS total_count
            FROM vendite.vw_dash_backlog_documenti d
            {where_clause}
            ORDER BY d.data_riferimento ASC NULLS LAST,
                     d.valore_fermo DESC NULLS LAST,
                     d.area ASC, d.documento_id ASC
            LIMIT %s OFFSET %s
        """

        # Fallback COUNT separato SOLO per offset oltre l'ultima pagina (zero
        # righe ma popolazione non vuota): serve al FE per il rientro in
        # pagina 1 (usePagedDashFetch controlla count > 0).
        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.vw_dash_backlog_documenti d
            {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()
            if rows:
                total_count = int(rows[0][16])
            elif safe_offset > 0:
                cursor.execute(count_sql, params)
                row = cursor.fetchone()
                assert row is not None
                total_count = int(row[0])
            else:
                total_count = 0

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
