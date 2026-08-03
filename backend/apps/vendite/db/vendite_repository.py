# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema vendite (query, liste, decodifiche).
# ------------------------------------------------------------

# Contiene operazioni generiche sullo schema vendite che non appartengono
# a nessun sottodominio specifico (pipeline, reset, ecc.).

import logging
import re
from datetime import date
from typing import Any

from django.db import DatabaseError, connection, transaction

from apps.core.db._helpers import (
    LIST_MAX_LIMIT,
    jsonb_out,
    query_paged_view,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.services.error_manager import ErrorManager
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashBacklogRiepilogoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaCommessaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaGruppiRiepilogoRow,
    DashCompetenzaGruppoRow,
    DashCompetenzaGruppoTipoRow,
    DashCompetenzaMensileRow,
    LineageNodoRow,
    LineagePassaggioRow,
    LineageSorgenteRow,
    LottoFattureRow,
    LottoListRow,
)

logger = logging.getLogger(__name__)

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
# Valore SINTETICO di `tipo_gruppo` per le righe sourceless (oneri di
# commessa): non e' un `config.sorgenti.codice_interno` ma il COALESCE della
# vista vw_dash_competenza_gruppi. Costante e non letterale sparso: e' il
# discriminante degli oneri nel riepilogo e nel filtro per tipo, ed e' anche il
# motivo per cui la tendina non si puo' costruire da `config.sorgenti` (dove
# questo valore non esiste).
TIPO_GRUPPO_ONERI = "ONERI_COMMESSA"

DASH_STADIO_DA_APPROVARE = "DA_APPROVARE"
DASH_COMPETENZA_STADI: tuple[str, ...] = (
    DASH_STADIO_DA_APPROVARE,
    "DA_EMETTERE",
    "EMESSA_NON_FATTURATA",
    "FATTURATA",
)

# Codice stabile (codice_interno di config.tipi_indirizzi) dello slot letto
# nella testata fattura per la stampa: indirizzo di fatturazione del cliente,
# dalla riga FATT del satellite congelato `fatture_indirizzi`. Costante passata
# come parametro SQL (mai letterale embedded — lezione review A+B sul letterale
# stadio). La gemella TIPO_INDIRIZZO_SEDE_LEGALE e' stata RITIRATA con la Fase 2
# satelliti (2026-07-31): la sede dell'emittente ora arriva gia' risolta dentro
# `emittente_snapshot->'sede'`, congelata a DB — qui non si risolve piu' nulla.
TIPO_INDIRIZZO_FATTURAZIONE = "FATT"

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
                sdf.codice_interno AS stato_doc_fiscale_codice,
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
            "stato_doc_fiscale_codice": row[10],
            "tipo_doc_fiscale_id": int(row[11]),
            "tipo_doc_fiscale_descrizione": row[12],
            "area_geografica_id": None if row[13] is None else int(row[13]),
            "area_geografica_descrizione": row[14],
            "emittente_soggetto_ruolo_id": None if row[15] is None else int(row[15]),
            "data_insert": row[16].isoformat() if row[16] is not None else None,
            "user_insert": str(row[17]),
        }

    # Colonne ordinabili della lista lotti: chiave esposta al FE -> espressione
    # SQL. Whitelist: nell'ORDER BY entrano solo chiavi note piu' la direzione
    # ASC/DESC, mai input utente grezzo. Stessa convenzione di
    # DASH_APERTO_SORT_COLUMNS e di `_ORDER_COLS_CONTRATTI`.
    #
    # ⚠️ La chiave e' il `campo_sorgente` del catalogo, NON il `codice` logico.
    # `<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`,
    # quindi `event.sortField` — e con esso `store.filters.order_by` — porta il
    # nome FISICO. Chiavare sui codici logici farebbe fallire con 400 proprio le
    # colonne in cui i due nomi divergono (`utility` vs `utility_descrizione`).
    #
    # Deve restare allineata al catalogo `vendite.lotti`: una colonna marcata
    # `ordinabile = t` nel seed ma assente qui mostra una freccia che non ordina;
    # il contrario lascia inutilizzabile una colonna ordinabile. `azioni` non c'e'
    # per costruzione (tipo_colonna='azione', nessun campo_sorgente).
    LOTTI_SORT_COLUMNS = {
        "codice": "fl.codice",
        "competenza_mese": "fl.competenza_mese",
        "tipo_lotto": "fl.tipo_lotto",
        "tipo_doc_fiscale_descrizione": "tdf.descrizione",
        "utility_descrizione": "u.descrizione",
        "area_geografica_descrizione": "agf.descrizione",
        "stato_lotto": "fl.stato_lotto",
        "stato_operativo": "fl.stato_operativo",
        "stato_doc_fiscale_descrizione": "sdf.descrizione",
        "data_insert": "fl.data_insert",
        "user_insert": "fl.user_insert",
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
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
        max_limit: int = LIST_MAX_LIMIT,
    ) -> tuple[list[LottoListRow], int]:
        # Il cap standard (LIST_MAX_LIMIT, fonte unica in core/db/_helpers)
        # protegge la lista a video; l'export lo alza esplicitamente (fino a
        # EXPORT_MAX_ROWS + 1, per poter *rilevare* il superamento del limite
        # invece di troncare in silenzio). Resta un cap passato dal chiamante:
        # nessun percorso senza tetto.
        safe_limit = max(1, min(int(limit), max_limit))
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

        # ORDER BY server-side (corretto su TUTTE le pagine, non solo su quella
        # visibile): colonna dalla whitelist + direzione, con tiebreak stabile
        # su fl.id per una paginazione deterministica anche a parita' di valore.
        # order_by assente o non ammesso -> ordine storico (il piu' recente
        # prima), cioe' esattamente il comportamento precedente: la lista non
        # cambia aspetto finche' l'utente non tocca un'intestazione.
        sort_col = self.LOTTI_SORT_COLUMNS.get(order_by or "")
        if sort_col is not None:
            direction = sql_order_direction(order_dir)
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = f"ORDER BY {sort_col} {direction}, fl.id {tiebreak_dir}"
        else:
            order_clause = "ORDER BY fl.data_insert DESC, fl.id DESC"

        data_sql = f"""
            SELECT {self._LOTTO_SELECT_COLS}
            FROM vendite.fatturazione_lotti fl
            {joins}
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

        result: list[LottoListRow] = [self._map_lotto_row(row) for row in rows]
        return result, total_count

    # Scopo: Conteggio lotti per mese di competenza di un anno (mese 1..12 → n).
    # Obiettivo: alimentare il badge per-mese della sidebar anno/mese del
    #            registro lotti (stile Lente Competenza). Fotografia completa:
    #            NESSUN filtro stato (il badge conta i lotti generati, non quelli
    #            dello stato filtrato — decisione UX). Scope emittente identico
    #            alla lista (RLS + whitelist applicativa via _add_scope_emittente).
    # Perimetro: sola lettura, nessun side-effect. Righe con competenza_mese NULL
    #            escluse dal confronto sull'anno (non sono di alcun mese).
    def count_lotti_per_mese(
        self, *, anno: int, auth_user_id: int | None = None,
    ) -> dict[int, int]:
        conditions: list[str] = ["EXTRACT(YEAR FROM fl.competenza_mese) = %s"]
        params: list[Any] = [anno]
        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )
        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT EXTRACT(MONTH FROM fl.competenza_mese)::int AS mese, COUNT(*)
            FROM vendite.fatturazione_lotti fl
            {where_clause}
            GROUP BY 1
        """  # noqa: S608 — where da frammenti interni, valori parametrizzati
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return {int(r[0]): int(r[1]) for r in cursor.fetchall()}

    # Scopo: Lotti in stato fiscale EMESSA per la competenza data → candidati
    #        alla numerazione di PERIMETRO (C-4). Query PURA (id+codice): lo
    #        `stato_doc_fiscale_id` EMESSA lo risolve+guarda il chiamante (handler,
    #        service layer), non il repo. Scope operatore via RLS — il chiamante
    #        gira sotto `operator_identity_context`, la policy
    #        `rls_fatturazione_lotti_ef_whitelist` filtra agli emittenti
    #        dell'operatore. NESSUN limite: no silent cap (i lotti EMESSA di un
    #        mese sono pochi, uno per terna emittente/tipo); il perimetro deve
    #        essere completo, non troncato.
    # Perimetro: sola lettura; nessun side-effect.
    def list_lotti_numerabili(
        self, *, competenza_mese: date, stato_doc_fiscale_id: int,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fl.id, fl.codice
                  FROM vendite.fatturazione_lotti fl
                 WHERE fl.competenza_mese = %s
                   AND fl.stato_doc_fiscale_id = %s
                 ORDER BY fl.id
                """,
                [competenza_mese, int(stato_doc_fiscale_id)],
            )
            return [
                {"id": int(row[0]), "codice": row[1]}
                for row in cursor.fetchall()
            ]

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
        # Estese 2026-08-03 (passata BE dashboard, 8° lotto liste): `stato_codice`
        # chiude il nucleo *stato* (la lista mostra la colonna e nasceva con la
        # freccia morta); `area`/`fase` per simmetria col gemello backlog, che
        # ordina `area` da subito — stessa colonna a video, stesso comportamento.
        "area": "area",
        "fase": "fase",
        "stato_codice": "stato_codice",
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
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                f"area ASC, documento_id {tiebreak_dir}"
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

    # Scopo: Conteggio FATTURE per (mese, stadio) della Lente 1 — la seconda
    #        misura delle card, accanto alle attivita'. Serve perche' le due
    #        grane divergono di molto e in modo non intuitivo: a luglio 2026,
    #        18 gruppi fatturabili hanno prodotto 6 fatture (una ne conteneva
    #        10). Chi legge «n attivita'» come «n fatture» sbaglia sempre, e
    #        di parecchio.
    # Perimetro: parte SEMPRE da `vw_dash_competenza_attivita`, che porta con
    #        se' lo scope emittente (GUC fail-closed) e le esclusioni di
    #        dominio: una query diretta sulle tabelle dovrebbe replicarli, e
    #        prima o poi divergerebbe.
    # Risultato: tupla `(conteggi, stadi_in_errore)`.
    #        · `conteggi`: {(competenza_mese_iso, stadio): n_fatture}
    #        · `stadi_in_errore`: gli stadi il cui calcolo e' FALLITO.
    #
    # ⚠️ I due esiti «non ho un numero» NON sono lo stesso esito, ed e' il
    #    motivo per cui questo metodo ritorna due cose invece di un dict solo:
    #      · lo stadio non e' calcolabile PER PROGETTO (DA_EMETTERE: la chiave
    #        documento non esiste ancora) -> la card tace, ed e' corretto;
    #      · il calcolo doveva riuscire e si e' ROTTO -> la card deve DIRLO.
    #    Fonderli su un unico «assente» ripeterebbe, un livello piu' in la',
    #    lo stesso appiattimento che qui sotto si evita fra `None` e `0`: il
    #    guasto prenderebbe l'aspetto del comportamento normale (rilievo di
    #    Tid, 2026-08-03).
    #
    # ⚠️ DUE MISURE DI NATURA DIVERSA, deliberatamente nello stesso metodo ma
    #    con due query:
    #    · FATTURATA          -> conteggio CERTO: le fatture esistono.
    #    · EMESSA_NON_FATTURATA -> PREVISIONE, calcolata con la funzione
    #      autoritativa `fn_build_fattura_key` sulle attivita' gia' emesse
    #      (che a questo stadio esistono come `attivita_fatturabili`): non e'
    #      una stima, e' la stessa chiave che il generatore usera'. Per lo
    #      stadio DA_EMETTERE la stessa cosa NON e' possibile — quelle righe
    #      sono `commesse_attivita` senza `attivita_fatturabili`, e la chiave
    #      si calcola solo da li': riscriverla altrove sarebbe un secondo
    #      risolutore delle condizioni di pagamento (vietato, brief scadenze
    #      §8) proprio sulle dimensioni che spaccano o uniscono le fatture.
    # Stadi per cui questo metodo SA produrre un conteggio. Vive qui, accanto
    # alle due query che lo rendono vero, e non nel service: e' il service a
    # doverlo chiedere al repository, altrimenti la stessa conoscenza starebbe
    # scritta in due posti e il giorno in cui una terza query si aggiunge
    # (previsione DA_EMETTERE, quando il DB esporra' la chiave a monte) uno
    # dei due resterebbe indietro in silenzio.
    DASH_STADI_CON_CONTEGGIO_FATTURE = frozenset(
        {"FATTURATA", "EMESSA_NON_FATTURATA"}
    )

    def count_dash_competenza_fatture_mensile(
        self, *, anno: int,
    ) -> tuple[dict[tuple[str, str], int], set[str]]:
        out: dict[tuple[str, str], int] = {}
        errori: set[str] = set()

        # --- FATTURATA: dato certo, nessuna funzione, nessun rischio.
        sql_reali = """
            SELECT competenza_mese, COUNT(DISTINCT fattura_id)::integer
            FROM vendite.vw_dash_competenza_attivita
            WHERE stadio = 'FATTURATA' AND fattura_id IS NOT NULL
              AND competenza_mese >= make_date(%s, 1, 1)
              AND competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY competenza_mese
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_reali, [anno, anno])
            for row in cursor.fetchall():
                out[(row[0].isoformat(), "FATTURATA")] = int(row[1])

        # --- EMESSA_NON_FATTURATA: previsione esatta, ma BEST-EFFORT.
        # `fn_build_fattura_key` e' VOLATILE (chiamata per riga) e SOLLEVA su
        # attivita' con chiave incompleta (BA mancante). Su un cruscotto —
        # la prima schermata che l'operatore apre — una singola riga
        # malformata renderebbe illeggibile l'INTERA pagina: sarebbe un
        # fail-closed nel posto sbagliato. Savepoint isolato: se salta,
        # si perde una misura secondaria, non il cruscotto.
        sql_previste = """
            SELECT v.competenza_mese,
                   COUNT(DISTINCT vendite.fn_build_fattura_key(af.id))::integer
            FROM vendite.vw_dash_competenza_attivita v
            JOIN vendite.attivita_fatturabili af
              ON af.commessa_attivita_id = v.commessa_attivita_id
            WHERE v.stadio = 'EMESSA_NON_FATTURATA'
              AND v.competenza_mese >= make_date(%s, 1, 1)
              AND v.competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY v.competenza_mese
        """
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql_previste, [anno, anno])
                    for row in cursor.fetchall():
                        out[(row[0].isoformat(), "EMESSA_NON_FATTURATA")] = int(row[1])
        except DatabaseError as exc:
            # Lo stadio entra in `errori`: il service lo tradurra' in uno stato
            # ESPLICITO verso il FE, che mostrera' un avvertimento invece di
            # tacere come fa sugli stadi non calcolabili per progetto.
            errori.add("EMESSA_NON_FATTURATA")
            # Traccia a DB oltre che nel file di log: un warning che vive solo
            # in un file rotante sul server e' una ricevuta che nessuno ritira.
            ErrorManager.log_error_only(
                code="E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA",
                context={
                    "anno": anno,
                    "stadio": "EMESSA_NON_FATTURATA",
                    "errore": str(exc)[:500],
                },
                area="vendite",
                function_name=(
                    "vendite.VenditeRepository."
                    "count_dash_competenza_fatture_mensile"
                ),
            )
            logger.warning(
                "Previsione fatture EMESSA_NON_FATTURATA non calcolabile "
                "(anno=%s): la card lo segnalera' all'operatore.",
                anno, exc_info=True,
            )

        return out, errori

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
    # NB: nomi di OUTPUT della SELECT (senza alias di tabella): l'ORDER BY di
    # `query_paged_view` si applica alla CTE `righe`, non alle tabelle sorgente.
    DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS = {
        "commessa_codice": "commessa_codice",
        "cliente_display": "cliente_display",
        "articolo_codice": "COALESCE(articolo_descrizione, articolo_codice)",
        "data_attivita": "data_attivita",
        "valore": "valore",
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
        # Direzione risolta PRIMA del ramo: il default (valore DESC) deve
        # avere il tiebreak coerente quanto la colonna scelta dall'utente.
        # `commessa_codice` raggruppa (resta ASC), `commessa_attivita_id` e' la
        # chiave tecnica univoca e segue la direzione (2026-08-03).
        direction = sql_order_direction(order_dir, default_desc=sort_col is None)
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"commessa_codice ASC, commessa_attivita_id {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            order_clause = f"ORDER BY valore DESC NULLS LAST, {tiebreak}"

        select_sql = f"""
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
                a.lotto_id,
                a.stato_fattura_codice_interno,
                a.stato_fattura_codice,
                a.valore_fatturato,
                a.fattura_critical
            FROM vendite.vw_dash_competenza_attivita a
            LEFT JOIN catalogo.articoli art
                ON art.id = a.articolo_id
            {where_clause}
        """

        # Una sola valutazione della vista (CTE materializzata + COUNT(*) OVER)
        # con CLAMP dell'offset all'ultima pagina reale, come le altre liste dei
        # cruscotti: il service dichiara poi la pagina effettiva nell'envelope.
        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

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
                    "lotto_id": None if row[21] is None else int(row[21]),
                    "stato_fattura_codice_interno": None if row[22] is None else str(row[22]),
                    "stato_fattura_codice": None if row[23] is None else str(row[23]),
                    "valore_fatturato": str(row[24]) if row[24] is not None else None,
                    "fattura_critical": bool(row[25]),
                }
            )
        return result, total_count

    # Colonne di ordinamento ammesse per il drill-down AGGREGATO per commessa.
    # Su aggregati si ordina per gli aggregati, non per le colonne di riga.
    DASH_COMPETENZA_COMMESSE_SORT_COLUMNS = {
        "commessa_codice": "commessa_codice",
        "cliente_display": "cliente_display",
        "n_attivita": "n_attivita",
        "valore_tot": "valore_tot",
        "data_attivita_max": "data_attivita_max",
    }

    # Scopo: Drill-down AGGREGATO per commessa (DEC-4) — una riga per commessa nel
    #        perimetro corrente (competenza_mese + stadio + solo_ritardo), con
    #        n attivita', totali valore/fatturato, estremi data e recuperi tardivi.
    #        Sostituisce la lista a grana attivita' quando l'operatore vuole la
    #        fotografia per commessa; il dettaglio resta nel drawer di gestione.
    # Perimetro: sola lettura su vw_dash_competenza_attivita (scope GUC in vista).
    # Risultato: tuple (lista DashCompetenzaCommessaRow, conteggio commesse).
    def list_dash_competenza_commesse(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        solo_ritardo: bool,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaCommessaRow], int]:
        conditions: list[str] = ["a.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("a.stadio = %s")
            params.append(stadio)
        if solo_ritardo:
            conditions.append("a.emessa_in_ritardo IS TRUE")

        where_clause = "WHERE " + " AND ".join(conditions)

        # ORDER BY server-side sugli aggregati (corretto su TUTTE le pagine):
        # colonna dalla whitelist + direzione, tiebreak stabile su commessa.
        # Assente/non ammesso -> default valore_tot DESC (le commesse piu' pesanti
        # prima), coerente col default a grana attivita'.
        sort_col = self.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS.get(order_by or "")
        # sql_order_direction ritorna gia' 'ASC NULLS FIRST'/'DESC NULLS LAST':
        # NON aggiungere un secondo NULLS (errore di sintassi PG). Direzione
        # risolta prima del ramo cosi' anche il default DESC ha il tiebreak
        # coerente; `commessa_codice` raggruppa, `commessa_id` segue.
        direction = sql_order_direction(order_dir, default_desc=sort_col is None)
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"commessa_codice ASC, commessa_id {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            order_clause = f"ORDER BY valore_tot DESC NULLS LAST, {tiebreak}"

        select_sql = f"""
            SELECT
                a.commessa_id,
                a.commessa_codice,
                a.cliente_display,
                COUNT(*)                                         AS n_attivita,
                COUNT(*) FILTER (WHERE a.emessa_in_ritardo IS TRUE) AS n_in_ritardo,
                SUM(a.valore)                                   AS valore_tot,
                SUM(a.valore_fatturato)                         AS valore_fatturato_tot,
                MIN(a.data_attivita)                            AS data_attivita_min,
                MAX(a.data_attivita)                            AS data_attivita_max
            FROM vendite.vw_dash_competenza_attivita a
            {where_clause}
            GROUP BY a.commessa_id, a.commessa_codice, a.cliente_display
        """

        # UNA sola valutazione della vista: prima il COUNT delle commesse
        # distinte era una seconda scansione con lo stesso GROUP BY. Qui il
        # `COUNT(*) OVER ()` della CTE conta le RIGHE raggruppate, che sono
        # esattamente le commesse distinte — stesso numero, meta' del lavoro.
        # In piu' arriva il CLAMP dell'offset: prima il service dichiarava la
        # pagina EFFETTIVA mentre il repository serviva quella RICHIESTA, e su
        # una pagina stantia l'envelope diceva «pagina 2» con zero righe — il
        # frontend ripiegava sulla pagina 1, cioe' nel posto sbagliato.
        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaCommessaRow] = []
        for row in rows:
            result.append(
                {
                    "commessa_id": int(row[0]),
                    "commessa_codice": None if row[1] is None else str(row[1]),
                    "cliente_display": None if row[2] is None else str(row[2]),
                    "n_attivita": int(row[3]),
                    "n_in_ritardo": int(row[4]),
                    "valore_tot": str(row[5]) if row[5] is not None else None,
                    "valore_fatturato_tot": str(row[6]) if row[6] is not None else None,
                    "data_attivita_min": row[7].isoformat() if row[7] is not None else None,
                    "data_attivita_max": row[8].isoformat() if row[8] is not None else None,
                }
            )
        return result, total_count

    # Colonne ordinabili dell'elenco GRUPPI FATTURABILI: chiave FE (field del
    # DataTable) -> colonna di OUTPUT della CTE `righe` (senza alias di
    # tabella: l'ORDER BY di `query_paged_view` si applica alla CTE, non alla
    # vista). Whitelist: nell'ORDER BY solo chiavi note + ASC/DESC (no injection).
    DASH_COMPETENZA_GRUPPI_SORT_COLUMNS = {
        "riferimento": "riferimento",
        "tipo_gruppo": "tipo_gruppo",
        "cliente_display": "cliente_display",
        "commessa_codice": "commessa_codice",
        "n_attivita": "n_attivita",
        "valore": "valore",
        "data_attivita_max": "data_attivita_max",
    }

    # Scopo: Elenco dei GRUPPI FATTURABILI di un mese/stadio — l'unita' su cui
    #        l'operatore decide nella card «Da emettere»: un documento sorgente
    #        (PRV-0012, CTR-0007…) oppure gli oneri di una commessa, che
    #        documento non hanno e altrimenti resterebbero lavoro invisibile e
    #        non azionabile. La `gruppo_key` esposta qui e' la STESSA che si
    #        rimanda al POST di emissione mirata: nessun mapping, nessuna
    #        possibilita' che elenco e criterio divergano.
    # Perimetro: sola lettura su vw_dash_competenza_gruppi (security_invoker:
    #        lo scope emittente e' applicato dalla vista, fail-closed senza GUC).
    # Risultato: tuple (lista DashCompetenzaGruppoRow, conteggio totale).
    # Scopo: predicato comune dell'elenco gruppi (lista + riepilogo), cosi' i
    #        totali non possono descrivere un perimetro diverso dalle righe che
    #        stanno sopra. `tipo_gruppo` e' opzionale: il filtro «tipo
    #        documento/sorgente» del cockpit. NON lo usa la facet, che deve
    #        vedere tutti i tipi anche quando uno e' selezionato (altrimenti
    #        scegliendo «Preventivi» le altre voci sparirebbero dalla tendina e
    #        non si potrebbe piu' cambiare idea).
    @staticmethod
    def _where_gruppi(
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = ["g.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("g.stadio = %s")
            params.append(stadio)
        if tipo_gruppo is not None:
            conditions.append("g.tipo_gruppo = %s")
            params.append(tipo_gruppo)
        return conditions, params

    def list_dash_competenza_gruppi(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaGruppoRow], int]:
        conditions, params = self._where_gruppi(
            competenza_mese=competenza_mese, stadio=stadio, tipo_gruppo=tipo_gruppo,
        )
        where_clause = "WHERE " + " AND ".join(conditions)

        # ⚠️ Tiebreak su (gruppo_key, stadio) e non sulla sola chiave: la vista
        # raggruppa per (competenza, gruppo_key, …, stadio), quindi SENZA il
        # filtro stadio — che e' opzionale — lo STESSO gruppo compare su piu'
        # righe (parte da emettere, parte gia' fatturata). Con il solo
        # gruppo_key l'ordine fra quelle righe sarebbe indefinito e la
        # paginazione non deterministica (frontend-standards §Paginazione
        # deterministica): righe ripetute o saltate cambiando pagina.
        sort_col = self.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS.get(order_by or "")
        # sql_order_direction ritorna gia' 'ASC NULLS FIRST'/'DESC NULLS LAST'.
        # Direzione prima del ramo: vale anche per il default DESC.
        direction = sql_order_direction(order_dir, default_desc=sort_col is None)
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"gruppo_key ASC, stadio {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            # Default: i gruppi che pesano di piu' in cima (stessa logica del
            # drill-down per commessa).
            order_clause = f"ORDER BY valore DESC NULLS LAST, {tiebreak}"

        # Clamp dell'offset all'ultima pagina reale in UNA valutazione, come le
        # altre liste dei cruscotti: il service dichiara poi la pagina effettiva
        # nell'envelope e `usePagedDashFetch` la adotta. Senza, una pagina
        # stantia tornerebbe VUOTA con count > 0 e il FE ripiegherebbe sulla
        # PRIMA pagina — un secondo giro, e per giunta nel posto sbagliato.
        # `documento_id`: il gruppo E' il documento sorgente, ma la vista ne
        # espone solo `sorgente_uid` (uuid) e il `riferimento` (codice) — e i
        # drawer di dominio si aprono per **id**. La LATERAL qui sotto risolve
        # l'id dalla STESSA riga da cui la vista prende il codice (stessa
        # coppia area+uid, stesso ORDER BY): id e codice non possono descrivere
        # due documenti diversi.
        # ⚠️ Drift noto e accettato: la regola di risoluzione e' scritta due
        # volte — qui e dentro `vw_dash_competenza_gruppi` (che proietta
        # `doc.codice`). Se il criterio cambiasse nella vista, va cambiato anche
        # qui. La soluzione pulita e' che la vista esponga `documento_id`
        # accanto al `riferimento`: e' una nota per il team DB, non un
        # prerequisito (nessun DDL serve al FE per aprire il documento).
        # Stesso schema — e stesso caveat dichiarato — di
        # `ui_repository.fetch_preset_base_snapshot`.
        # Gruppi SOURCELESS (oneri di commessa): `area_documento` NULL → la
        # LATERAL non produce righe → `documento_id` NULL. E' corretto: quei
        # gruppi un documento non ce l'hanno, e il FE offrira' la sola commessa.
        rows, total_count = self._query_paged_view(
            select_sql=f"""
            SELECT
                g.gruppo_key,
                g.tipo_gruppo,
                g.area_documento,
                g.riferimento,
                g.commessa_id,
                g.commessa_codice,
                g.cliente_display,
                g.stadio,
                g.n_attivita,
                g.valore,
                g.ha_oneri,
                g.data_attivita_min,
                g.data_attivita_max,
                doc.documento_id
            FROM vendite.vw_dash_competenza_gruppi g
            LEFT JOIN LATERAL (
                SELECT d.documento_id
                  FROM vendite.vw_dash_fatturazione_documenti d
                 WHERE g.area_documento IS NOT NULL
                   AND d.area = g.area_documento
                   AND d.documento_uid = g.sorgente_uid
                 ORDER BY d.competenza_mese DESC NULLS LAST
                 LIMIT 1
            ) doc ON TRUE
            {where_clause}
            """,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaGruppoRow] = []
        for row in rows:
            result.append(
                {
                    "gruppo_key": str(row[0]),
                    "tipo_gruppo": str(row[1]),
                    "area_documento": None if row[2] is None else str(row[2]),
                    "riferimento": None if row[3] is None else str(row[3]),
                    "commessa_id": None if row[4] is None else int(row[4]),
                    "commessa_codice": None if row[5] is None else str(row[5]),
                    "cliente_display": None if row[6] is None else str(row[6]),
                    "stadio": None if row[7] is None else str(row[7]),
                    "n_attivita": int(row[8]),
                    "valore": str(row[9]) if row[9] is not None else None,
                    "ha_oneri": bool(row[10]),
                    "data_attivita_min": row[11].isoformat() if row[11] is not None else None,
                    "data_attivita_max": row[12].isoformat() if row[12] is not None else None,
                    "documento_id": None if row[13] is None else int(row[13]),
                }
            )
        return result, total_count

    # Scopo: Totali di perimetro dell'elenco gruppi (riga di riconciliazione
    #        «N gruppi · M attivita' · X €»). Vengono dal DB e non dalla somma
    #        delle righe della pagina corrente, che sarebbe un parziale con
    #        l'aria di un totale — e nessuno somma a mano piu' pagine per
    #        accorgersene.
    # Perimetro: aggrega `vw_dash_competenza_gruppi` con lo STESSO predicato
    #        della lista (`_where_gruppi`, filtro tipo incluso): i totali
    #        descrivono esattamente le righe che stanno sopra, non un perimetro
    #        vicino.
    #        ⚠️ NON usa `vw_dash_competenza_gruppi_riepilogo`: quella vista
    #        aggrega per (competenza, stadio, emittente) e **non espone
    #        `tipo_gruppo`**, quindi non saprebbe seguire il filtro. I numeri
    #        sono gli stessi — e' l'aggregazione della stessa vista di
    #        dettaglio — ma qui la sorgente e' letteralmente quella della
    #        lista. La vista di riepilogo resta valida per altri consumatori.
    def get_dash_competenza_gruppi_riepilogo(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
    ) -> DashCompetenzaGruppiRiepilogoRow:
        conditions, params = self._where_gruppi(
            competenza_mese=competenza_mese, stadio=stadio, tipo_gruppo=tipo_gruppo,
        )
        where_clause = "WHERE " + " AND ".join(conditions)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    COUNT(*)::int,
                    COALESCE(SUM(g.n_attivita), 0)::bigint,
                    COALESCE(SUM(g.valore), 0),
                    COUNT(*) FILTER (WHERE g.tipo_gruppo = %s)::int
                FROM vendite.vw_dash_competenza_gruppi g
                {where_clause}
                """,
                [TIPO_GRUPPO_ONERI, *params],
            )
            row = cursor.fetchone()
        assert row is not None
        return {
            "n_gruppi": int(row[0]),
            "n_attivita": int(row[1]),
            "valore": str(row[2]) if row[2] is not None else None,
            "n_gruppi_oneri": int(row[3]),
        }

    # Scopo: Voci del filtro «tipo documento/sorgente» della lista gruppi,
    #        calcolate SUI DATI del perimetro (facet) con il conteggio accanto.
    #        Cosi' la tendina offre solo cio' che esiste davvero: un'opzione che
    #        dà sempre zero risultati e' peggio di nessun filtro.
    # ⚠️ Il predicato NON include `tipo_gruppo`: le facet devono restare tutte
    #        visibili anche quando una e' selezionata, altrimenti scegliendo
    #        «Preventivi» le altre voci sparirebbero e l'operatore resterebbe
    #        chiuso dentro il filtro appena messo.
    # Perimetro: sola lettura su vw_dash_competenza_gruppi (scope GUC in vista).
    def list_dash_competenza_gruppi_tipi(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
    ) -> list[DashCompetenzaGruppoTipoRow]:
        conditions, params = self._where_gruppi(
            competenza_mese=competenza_mese, stadio=stadio,
        )
        where_clause = "WHERE " + " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    g.tipo_gruppo,
                    MIN(g.area_documento) AS area_documento,
                    COUNT(*)::int         AS n_gruppi,
                    COALESCE(SUM(g.n_attivita), 0)::bigint AS n_attivita
                FROM vendite.vw_dash_competenza_gruppi g
                {where_clause}
                GROUP BY g.tipo_gruppo
                ORDER BY COUNT(*) DESC, g.tipo_gruppo ASC
                """,
                params,
            )
            rows = cursor.fetchall()
        return [
            {
                "tipo_gruppo": str(r[0]),
                "area_documento": None if r[1] is None else str(r[1]),
                "n_gruppi": int(r[2]),
                "n_attivita": int(r[3]),
            }
            for r in rows
        ]

    # Colonne ordinabili della lista errori vivi (8° lotto liste, 2026-08-03).
    # Alias di output della union: la vista non ha una PK e le colonne di
    # documento sono NULLABLE per costruzione (un errore di task non ha fattura,
    # una fattura critical non ha task) — NULLS LAST e' applicato nel metodo.
    DASH_COMPETENZA_ERRORI_SORT_COLUMNS = {
        "tipo_evento": "tipo_evento",
        "lotto_codice": "lotto_codice",
        "fattura_numero": "fattura_numero",
        "error_code": "error_code",
        "data_evento": "data_evento",
    }

    # Scopo: Restituisce la lista paginata degli errori vivi (blocco 4 Lente 1:
    #        task run in ERRORE non superati + fatture critical), con filtro
    #        opzionale per mese di competenza.
    # Perimetro: sola lettura su vw_dash_competenza_errori (scope GUC in vista).
    # Risultato: tuple (lista DashCompetenzaErroreRow, conteggio totale).
    def list_dash_competenza_errori(
        self,
        *,
        competenza_mese: date | None,
        order_by: str | None = None,
        order_dir: str | None = None,
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

        # ORDER BY server-side (stessa convenzione delle altre liste dash):
        # colonna dalla whitelist + direzione, NULLS LAST esplicito (le colonne
        # di documento sono NULL su meta' della union — in DESC finirebbero in
        # testa), tiebreak = la catena deterministica storica sulle chiavi
        # naturali. order_by assente -> ordine storico (eventi recenti prima).
        _tiebreak = """tipo_evento ASC,
                     lotto_id ASC NULLS LAST, fattura_id ASC NULLS LAST,
                     task_code ASC NULLS LAST"""
        sort_col = self.DASH_COMPETENZA_ERRORI_SORT_COLUMNS.get(order_by or "")
        if sort_col is not None:
            direction = sql_order_direction(order_dir)
            # Il tiebreak qui e' una catena di chiavi NATURALI (la union non ha
            # una PK): resta fissa, non e' uno spareggio tecnico da allineare.
            order_clause = (
                f"ORDER BY {sort_col} {direction} NULLS LAST, {_tiebreak}"
            )
        else:
            order_clause = f"ORDER BY data_evento DESC NULLS LAST, {_tiebreak}"

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
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
        # Estesa 2026-08-03 (passata BE dashboard, 8° lotto liste): la classe di
        # azionabilita' e' colonna a video (Tag) e vocabolario chiuso a 3 valori —
        # ordinarla raggruppa il lavoro per tipo di intervento.
        "classe": "classe",
    }

    def list_dash_backlog_documenti(
        self,
        *,
        classe: str | None,
        area: str | None,
        ritardo_giorni: int | None = None,
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
        # Filtro "fermo da oltre N giorni" su data documento — stessa semantica e
        # stesso SQL della Situazione aperta (DL-17). Solo sulla lista: le card
        # per classe restano la fotografia completa. Le righe con data ignota
        # (data_riferimento NULL, anzianita_giorni NULL) sono escluse dal
        # confronto — coerente: "fermo da N giorni" richiede un'età nota.
        if ritardo_giorni is not None:
            conditions.append(
                "d.data_riferimento <= current_date - make_interval(days => %s)"
            )
            params.append(ritardo_giorni)

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
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                f"area ASC, documento_id {tiebreak_dir}"
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
        safe_limit = max(1, min(int(limit), LIST_MAX_LIMIT))
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

    # Scopo: Testata fattura completa di decodifiche (cliente, emittente,
    #        pagamento, totali) per il context builder del PDF **e** per
    #        l'endpoint di dettaglio del drawer fattura.
    #
    #        ⚠️ RISTAMPA CONFORME (Fase 2 piano BE/FE satelliti, 2026-07-31):
    #        l'intestazione delle due parti NON si legge piu' dall'anagrafica
    #        viva ma dagli SNAPSHOT congelati allo step DRAFT dalla pipeline
    #        (`fn_snapshot_fattura_lotto`):
    #          - identita' fiscale emittente/cliente → `f.emittente_snapshot` /
    #            `f.cliente_snapshot` (testata, guard di congelamento);
    #          - indirizzo di fatturazione cliente → riga `FATT` di
    #            `vendite.fatture_indirizzi`.
    #        Le chiavi piatte esposte restano IDENTICHE (contratto del drawer
    #        FE e del template PDF): cambia solo la sorgente. NESSUN fallback
    #        alla vista live (§9 del piano): una fattura senza snapshot mostra
    #        i campi vuoti, ed e' giusto che si veda.
    #        La rimozione delle vecchie subquery su vw_indirizzi_resolved_ruolo
    #        chiude anche i DUE difetti del §10.3 del brief intestazione (il
    #        filtro confrontava codice_interno con la colonna `codice`, e la
    #        vista contiene il solo layer RUOLO — la sede legale dell'emittente
    #        non era MAI stata stampata).
    #
    #        Lettura pura: nessun calcolo fiscale in Python. None se la fattura
    #        non esiste (o è fuori scope RLS).
    #        `auth_user_id` opzionale = difesa in profondita' applicativa che si
    #        SOMMA alla RLS di `vendite.fatture` (policy `rls_fatture_ef_whitelist`,
    #        attiva sul ruolo dell'app: `zeroerp_app` non e' owner della tabella).
    #        Default `None` = nessun filtro applicativo: e' il percorso del motore
    #        documentale, che applica lo scope a monte e non va toccato.
    def get_fattura_testata(
        self,
        fattura_id: int,
        *,
        auth_user_id: int | None = None,
    ) -> dict[str, Any] | None:
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
                -- ===== Intestazione EMITTENTE: dallo snapshot congelato =====
                -- Chiavi piatte derivate dal jsonb per compatibilita' col
                -- contratto esistente (drawer FE + template PDF v1). NULL se
                -- lo snapshot manca (fattura pre-Fase 1): niente fallback.
                (f.emittente_snapshot->>'emittente_fiscale_id')::bigint
                                             AS emittente_fiscale_id,
                f.emittente_snapshot->>'emittente_codice'
                                             AS emittente_fiscale_codice,
                f.emittente_snapshot->>'denominazione'
                                             AS emittente_denominazione,
                f.emittente_snapshot->>'id_fiscale'
                                             AS emittente_piva,
                f.emittente_snapshot->>'codice_fiscale'
                                             AS emittente_cf,
                -- Sede legale: display dello snapshot indirizzo annidato
                -- (composto a DB da fn_resolve_indirizzo_documento, due layer).
                f.emittente_snapshot->'sede'->>'display'
                                             AS emittente_sede,
                -- Utility del documento: dalla COLONNA di testata (D-S,
                -- 2026-08-01), non dedotta dal billing account. Sono due
                -- derivazioni diverse e possono divergere: la chiave di
                -- aggregazione prende l'utility dal BA dell'**attivita'** (il
                -- figlio), mentre `f.billing_account_id` e' il BA della
                -- fattura (il **padre**, D-P). Finche' non esistono BA con
                -- `parent_account_id` le due coincidono, ma dedurla da `ba`
                -- rimetterebbe qui lo stesso difetto latente che D-S ha
                -- appena tolto dal ricalcolo totali.
                f.utility_id,
                util.codice                  AS utility_codice,
                util.descrizione             AS utility_descrizione,
                mpag.codice                  AS pagamento_modalita_codice,
                tpag.codice_interno          AS pagamento_termine_codice,
                f.billing_account_id,
                -- ===== Intestazione CLIENTE: dallo snapshot congelato =====
                f.cliente_snapshot->>'ba_codice'          AS ba_codice,
                (f.cliente_snapshot->>'soggetto_ruolo_id')::bigint
                                             AS cliente_soggetto_ruolo_id,
                (f.cliente_snapshot->>'soggetto_id')::uuid AS soggetto_id,
                f.cliente_snapshot->>'denominazione'
                                             AS ragione_sociale_completa,
                f.cliente_snapshot->>'id_fiscale'
                                             AS id_fiscale_univoco_cf_piva,
                -- Indirizzo di fatturazione cliente: riga FATT del satellite
                -- congelato (unica per la UNIQUE (fattura_id, tipo)). E' QUESTA
                -- la lettura che rende la ristampa conforme: modificare
                -- l'anagrafica non cambia piu' il documento.
                (SELECT fi.snapshot->>'display'
                   FROM vendite.fatture_indirizzi fi
                   JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
                  WHERE fi.fattura_id = f.id
                    AND ti.codice_interno = %s)
                                             AS cliente_indirizzo,
                -- Snapshot integrali: per i consumer che vorranno i campi
                -- ricchi (REA, forma giuridica, codice SDI) senza riaprire
                -- questa SELECT. Shape interno non contrattuale (brief §10.2).
                f.emittente_snapshot,
                f.cliente_snapshot,
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
              JOIN anagrafiche.billing_account ba
                ON ba.id = f.billing_account_id
              LEFT JOIN config.utilities util
                ON util.id = f.utility_id
              LEFT JOIN config.modalita_pagamento mpag
                ON mpag.id = f.modalita_pagamento_id
              LEFT JOIN config.termini_pagamento tpag
                ON tpag.id = f.termine_pagamento_id
              LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = f.tipo_doc_fiscale_id
              LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = f.stato_doc_fiscale_id
              LEFT JOIN config.valute val
                ON val.id = f.valuta_id
             WHERE f.id = %s
        """
        # Parametri nell'ordine dei %s: subquery indirizzo fatturazione
        # cliente (riga FATT del satellite), id fattura.
        params: list[Any] = [
            TIPO_INDIRIZZO_FATTURAZIONE,
            int(fattura_id),
        ]
        # Scope emittente applicativo (convenzione SR) appeso alla WHERE solo
        # quando il chiamante lo chiede: l'helper non aggiunge nulla per
        # auth_user_id None o per un utente che vede tutto (admin globale).
        conditions: list[str] = []
        self._add_scope_emittente(
            auth_user_id, "f.emittente_soggetto_ruolo_id", conditions, params,
        )
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = row_to_dict(cursor)
        if row is not None:
            # psycopg 3 fuori dall'ORM NON decodifica i jsonb: `meta` arriva
            # come `str`. Senza questa riga il consumer JSON riceverebbe una
            # STRINGA al posto dell'oggetto, e chi ci fa `.get()` muore al
            # primo accesso (BB `jsonb_out`, nato esattamente da questo bug).
            row["meta"] = jsonb_out(row.get("meta"))
            row["emittente_snapshot"] = jsonb_out(row.get("emittente_snapshot"))
            row["cliente_snapshot"] = jsonb_out(row.get("cliente_snapshot"))
        return row

    # Scopo: Righe fattura con decodifiche articolo/uom/iva per il context
    #        builder. Espone i nomi di CONTRATTO condivisi con ordini/DDT/
    #        preventivi (`quantita`, `importo_riga`), non i nomi di colonna DB:
    #        i template documento sono uniformi fra tipi documento.
    #        `importo_riga` è mantenuto dal DB — trigger `a20_importo` su
    #        `vendite.fatture_righe` (brief-fix-importi-riga-fattura-zero §4.1,
    #        requisito D1): fino al 2026-07-28 nessuno lo scriveva e ogni
    #        fattura valeva 0,00.
    #        `imposta_riga`/`totale_riga` NON esistono più (§4.3, D1-ter):
    #        l'imposta di riga non è un concetto del modello italiano e l'IVA è
    #        governata per aggregato in `fatture_riepiloghi_iva`.
    #        FONTE: `vendite.vw_fattura_righe_esposte`, NON la tabella. È la
    #        rappresentazione unica del documento (regola R17): PDF, XML SDI e
    #        portale devono mostrare lo stesso dettaglio, altrimenti due uscite
    #        dello stesso documento raccontano cose diverse. La vista risolve i
    #        kit — una riga `KIT_PADRE` con il totale, sotto i soli componenti
    #        con `kit_esposto_in_fattura`; sulle fatture senza kit è un
    #        passante. È l'unica regola che il DB non può presidiare da solo:
    #        il presidio è questa query.
    #        `tipo_riga` (NORMALE/KIT_PADRE/KIT_COMPONENTE) e `livello` (0/1)
    #        servono al template per rendere la gerarchia; `id` è NULL sulle
    #        righe KIT_PADRE, che non esistono in tabella.
    #        Ordine per `ordinamento` e non per `riga_nr`: è la colonna che
    #        tiene padre e componenti nella sequenza giusta.
    def list_fattura_righe(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                r.fatture_righe_id  AS id,
                r.fattura_id,
                r.tipo_riga,
                r.livello,
                r.riga_nr,
                r.articolo_id,
                a.codice            AS articolo_codice,
                a.descrizione       AS articolo_descrizione,
                r.descrizione,
                r.uom_id,
                um.codice           AS uom_codice,
                r.qta               AS quantita,
                r.prezzo_unitario,
                r.sconto_percentuale,
                r.iva_id,
                iva.codice          AS iva_codice,
                iva.descrizione     AS iva_descrizione,
                iva.aliquota_iva    AS iva_aliquota,
                r.iva_natura,
                r.imponibile        AS importo_riga
              FROM vendite.vw_fattura_righe_esposte r
              LEFT JOIN catalogo.articoli a      ON a.id  = r.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_id
              LEFT JOIN config.iva iva           ON iva.id = r.iva_id
             WHERE r.fattura_id = %s
             ORDER BY r.ordinamento, r.livello, r.riga_nr
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

    # Scopo: Scadenze (rate) della fattura per il context builder (piano
    #        pagamenti stampato in fattura). Lettura pura, ordine stabile per
    #        numero rata → data. `modalita_codice` (opz.) dal jsonb `meta` se il
    #        DB lo mantiene; la tabella non ha colonna dedicata.
    def list_fattura_scadenze(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                sc.id,
                sc.numero_rata,
                sc.data_scadenza,
                sc.importo,
                sc.meta
              FROM vendite.fatture_scadenze sc
             WHERE sc.fattura_id = %s
             ORDER BY sc.numero_rata NULLS LAST, sc.data_scadenza NULLS LAST, sc.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        # ⚠️ `meta` e' jsonb e da cursor RAW arriva come `str` (psycopg 3 non lo
        # decodifica fuori dall'ORM). Senza `jsonb_out` il `_shape_scadenza` del
        # context builder PDF esegue `meta.get("modalita_codice")` su una
        # stringa → AttributeError → 500 alla prima scadenza con meta non-NULL.
        # Latente finora solo perche' nessuna scadenza di test ha meta.
        for row in rows:
            row["meta"] = jsonb_out(row.get("meta"))
        return rows

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
