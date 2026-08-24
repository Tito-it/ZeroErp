# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dello schema `pagamenti` — letture di lista e dettaglio,
#        scritture semplici, e chiamate alle funzioni madri del database.
# Note: ⛔ Un repository PER SCHEMA e non uno per entita': distinte e righe
#       stanno insieme finche' non nasce un sottodominio con orchestrazione
#       propria (convenzione di naming, AGENTS.md).
#
#       🔴 TUTTE le tabelle di `pagamenti` hanno la row security accesa (lotto
#       DB 6) e le policy pretendono `app.ruolo_applicativo = 'OPERATORE'` per
#       LEGGERE e per SCRIVERE. Un percorso che le tocchi senza quella GUC non
#       vede niente e non scrive niente: la impostano il middleware JWT (ciclo
#       web) e il contesto della coda lavori (worker).
#
#       ⛔ E per la stessa ragione questi metodi NON vanno chiamati da un canale
#       di sistema (ruolo BYPASSRLS): li' il perimetro non filtra e le liste
#       mostrerebbero il denaro di tutti gli emittenti. Il guard e' esplicito
#       nelle letture di lista, non affidato al ricordo.
# ------------------------------------------------------------

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    fetch_paged_with_total,
    jsonb_out,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.system_context import connection_role_bypasses_rls
from apps.pagamenti.types import (
    DistintaRow,
    RicevutaPosting,
    RigaContabileRow,
    StatoCatalogoRow,
    StatoRigaCatalogoRow,
)

_FN = "pagamenti.pagamenti_repository"

# Codice usato dai soli guard strutturali di questo modulo (canale di sistema):
# non e' un errore che un operatore possa causare compilando qualcosa.
_E_CHIAMATA = "E_PAGAMENTI_CHIAMATA_NON_VALIDA"


# ══════════════════════════════════════════════════════════════════
#  Frammenti SQL condivisi
# ══════════════════════════════════════════════════════════════════

# I totali derivati della distinta. ⚠️ Contano le righe ATTIVE, SCARTATA
# compresa: e' la stessa somma che il guard di validazione confronta con
# `importo_dichiarato` — se una riga scartata uscisse dal conto, il primo
# scarto romperebbe la quadratura di una distinta sana.
_TOTALI_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT
            count(*)::int                                          AS righe_totali,
            count(*) FILTER (WHERE rs.is_postabile)::int           AS righe_registrabili,
            COALESCE(sum(r.importo), 0)                            AS totale_righe,
            COALESCE(sum(r.importo) FILTER (WHERE rs.is_postabile), 0) AS totale_registrabile
          FROM pagamenti.vendite_contabili_righe r
          JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
         WHERE r.contabile_id = c.id
           AND r.attivo IS TRUE
    ) tot ON TRUE
"""

_DISTINTA_SELECT = """
    SELECT
        c.id,
        c.codice,
        c.centro_riscossione_id,
        cr.codice          AS centro_codice,
        cr.descrizione     AS centro_descrizione,
        c.ente_incasso_id,
        ei.codice          AS ente_codice,
        ei.descrizione     AS ente_descrizione,
        c.data_contabile,
        c.data_registrazione,
        c.stato_id,
        st.codice_interno  AS stato_codice,
        st.descrizione     AS stato_descrizione,
        st.is_final        AS stato_is_final,
        c.origine,
        c.importo_dichiarato,
        c.data_conferma,
        c.user_conferma,
        lot.lotti_ids,
        c.meta,
        tot.righe_totali,
        tot.righe_registrabili,
        tot.totale_righe,
        tot.totale_registrabile,
        -- Lo scarto esiste solo se qualcuno ha dichiarato un totale: NULL non
        -- e' zero, e mostrare «scarto 0» dove nessuno ha dichiarato niente
        -- direbbe che la distinta quadra quando non c'e' niente da quadrare.
        CASE WHEN c.importo_dichiarato IS NULL THEN NULL
             ELSE tot.totale_righe - c.importo_dichiarato
        END AS scarto_dichiarato
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.centri_riscossione cr        ON cr.id = c.centro_riscossione_id
      LEFT JOIN pagamenti.enti_incasso ei         ON ei.id = c.ente_incasso_id
      LEFT JOIN pagamenti.vendite_contabili_stati st ON st.id = c.stato_id
      -- 🔴 I lotti si AGGREGANO, non si joinano. L'unico e' su
      -- `(lotto_id, contabile_id)` e NON sul solo `contabile_id`: una distinta
      -- puo' legittimamente appartenere a piu' lotti, e un LEFT JOIN diretto
      -- avrebbe DUPLICATO la riga nell'elenco — con il conteggio totale
      -- sbagliato di conseguenza, che e' il modo silenzioso di rompersi.
      LEFT JOIN LATERAL (
          SELECT array_agg(l.lotto_id ORDER BY l.lotto_id) AS lotti_ids
            FROM pagamenti.vendite_contabili_lotti l
           WHERE l.contabile_id = c.id
      ) lot ON TRUE
"""

_RIGA_SELECT = """
    SELECT
        r.id,
        r.contabile_id,
        r.importo,
        r.riferimento_ente,
        r.data_pagamento,
        r.data_valuta,
        r.data_operazione,
        r.fattura_id,
        f.numero           AS fattura_numero,
        f.anno             AS fattura_anno,
        f.serie            AS fattura_serie,
        r.billing_account_id,
        ba.codice          AS billing_account_codice,
        srd.ragione_sociale_completa AS billing_account_descrizione,
        r.scadenza_id,
        sc.numero_rata     AS scadenza_numero_rata,
        sc.data_scadenza   AS scadenza_data,
        r.forzata,
        r.motivo_forzatura,
        r.stato_id,
        rs.codice_interno  AS stato_codice,
        rs.descrizione     AS stato_descrizione,
        rs.is_postabile    AS stato_is_postabile,
        rs.richiede_abbinamento AS stato_richiede_abbinamento,
        r.motivo_sospeso,
        r.fondo_source_id,
        r.attivo,
        r.meta
      FROM pagamenti.vendite_contabili_righe r
      LEFT JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
      LEFT JOIN vendite.fatture f            ON f.id = r.fattura_id
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = r.billing_account_id
      -- Il nome del cliente non sta sul billing account: la vista di dettaglio
      -- e' la sede unica della ragione sociale (persone fisiche e giuridiche
      -- si compongono in modo diverso, e ricomporla qui sarebbe una copia).
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
             ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
      LEFT JOIN vendite.fatture_scadenze sc  ON sc.id = r.scadenza_id
"""

# Colonne ordinabili della lista distinte: whitelist chiusa, chiavi del
# contratto API -> espressioni SQL. ⛔ Mai input utente dentro l'ORDER BY.
DISTINTE_SORT_COLUMNS: dict[str, str] = {
    "data_contabile": "data_contabile",
    "codice": "codice",
    "stato": "stato_codice",
    "origine": "origine",
    "centro": "centro_codice",
    "totale_righe": "totale_righe",
}

# Colonne ordinabili della coda del riconciliatore (righe cross-distinta).
RIGHE_SORT_COLUMNS: dict[str, str] = {
    "data_pagamento": "data_pagamento",
    "importo": "importo",
    "stato": "stato_codice",
    "distinta": "contabile_codice",
}

# Colonne ordinabili dell'elenco delle rate fuori capienza.
RATE_FUORI_CAPIENZA_SORT_COLUMNS: dict[str, str] = {
    "data_scadenza": "data_scadenza",
    "motivo": "motivo",
    "residuo": "residuo",
    "importo_rata": "importo_rata",
    "fattura": "fattura_numero",
}

# Colonne jsonb che il driver restituisce come stringa fuori dall'ORM.
_JSONB_COLS = ("meta",)

# 🔴 Le colonne che questo repository accetta di aggiornare, e non e' una
# ripetizione della whitelist del service: quella dice che cosa il CONTRATTO
# API espone, questa e' l'ultimo cancello prima che un nome finisca dentro una
# stringa SQL. Il giorno in cui qualcuno chiamasse questi metodi con delle
# chiavi che arrivano da un payload, la differenza fra le due sarebbe una
# SQL injection.
_COLONNE_DISTINTA_AGGIORNABILI = frozenset(
    {"data_contabile", "data_registrazione", "ente_incasso_id",
     "importo_dichiarato", "meta"}
)
_COLONNE_RIGA_AGGIORNABILI = frozenset(
    {"importo", "riferimento_ente", "data_pagamento", "data_valuta",
     "data_operazione", "fattura_id", "billing_account_id", "scadenza_id",
     "forzata", "motivo_forzatura", "motivo_sospeso", "meta"}
)


class PagamentiRepository:
    """Accesso dati dello schema `pagamenti`."""

    # ══════════════════════════════════════════════════════════════
    #  Guard strutturale
    # ══════════════════════════════════════════════════════════════

    # Scopo: Impedisce che una lettura di perimetro giri su un ruolo BYPASSRLS.
    # Contesto: le policy di `pagamenti` sono l'unico cancello di queste liste.
    #        Su un ruolo che le scavalca la lista non fallirebbe: mostrerebbe
    #        il denaro di TUTTI gli emittenti, che e' molto peggio di un errore.
    @staticmethod
    def _guard_canale_sistema(metodo: str) -> None:
        ErrorManager.require(
            not connection_role_bypasses_rls(),
            code=_E_CHIAMATA,
            message="Operazione non disponibile dal canale di sistema.",
            detail=(
                "Le tabelle di pagamenti sono protette da RLS: lette da un "
                "ruolo BYPASSRLS perderebbero il perimetro emittente. Usare "
                "la connessione dell'utente della richiesta."
            ),
            function_name=f"{_FN}.{metodo}",
        )

    # ══════════════════════════════════════════════════════════════
    #  Cataloghi di stato
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il vocabolario degli stati della distinta, coi suoi flag.
    # Nota: `obsoleto_dal` filtra i valori RITIRATI — che restano leggibili
    #       sui documenti vecchi ma non si propongono piu' a nessuno.
    def list_stati_distinta(self) -> list[StatoCatalogoRow]:
        sql = """
            SELECT id, codice, codice_interno, descrizione, is_final, ordine
              FROM pagamenti.vendite_contabili_stati
             WHERE attivo IS TRUE
               AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)
             ORDER BY ordine NULLS LAST, id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # Scopo: Il vocabolario degli stati della riga, coi due flag che governano
    #        l'interfaccia — `is_postabile` (occupa spazio, si puo' registrare)
    #        e `richiede_abbinamento` (pretende fattura e cliente).
    def list_stati_riga(self) -> list[StatoRigaCatalogoRow]:
        sql = """
            SELECT id, codice, codice_interno, descrizione, is_final, ordine,
                   is_postabile, richiede_abbinamento
              FROM pagamenti.vendite_contabili_righe_stati
             WHERE attivo IS TRUE
               AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)
             ORDER BY ordine NULLS LAST, id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Distinte — lettura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Elenco paginato delle distinte contabili con i display field in
    #        JOIN e i totali derivati.
    # Perimetro: la RLS della testata; nessun filtro applicativo aggiuntivo
    #        (le policy passano dal canale e dalla fattura, non da una colonna
    #        emittente su questa tabella).
    def list_distinte(
        self,
        *,
        stato_codice: str | None = None,
        origine: str | None = None,
        centro_riscossione_id: int | None = None,
        ente_incasso_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[DistintaRow], int]:
        self._guard_canale_sistema("list_distinte")

        conditions: list[str] = []
        params: list[Any] = []
        if stato_codice is not None:
            conditions.append("st.codice_interno = %s")
            params.append(stato_codice)
        if origine is not None:
            conditions.append("c.origine = %s")
            params.append(origine)
        if centro_riscossione_id is not None:
            conditions.append("c.centro_riscossione_id = %s")
            params.append(centro_riscossione_id)
        if ente_incasso_id is not None:
            conditions.append("c.ente_incasso_id = %s")
            params.append(ente_incasso_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sort_col = DISTINTE_SORT_COLUMNS.get(order_by, "data_contabile")
        # ⚠️ La direzione la compone l'helper condiviso, e porta con se' la
        # posizione dei NULL: i vuoti vanno dove starebbe lo zero (in coda
        # scendendo, in testa salendo). ⛔ Non si incolla un `NULLS LAST` fisso:
        # sarebbe sintatticamente doppio, e su una lista che si ordina dal piu'
        # recente porterebbe i campi vuoti in cima.
        direction = sql_order_direction(order_dir, default_desc=True)
        # Tiebreak nella STESSA direzione della colonna primaria: due distinte
        # dello stesso giorno non devono cambiare posto fra una pagina e l'altra.
        tiebreak = sql_tiebreak_direction(direction)

        data_sql = f"""
            SELECT * , COUNT(*) OVER () AS total_count FROM (
                {_DISTINTA_SELECT}
                {_TOTALI_LATERAL}
                {where_clause}
            ) q
            ORDER BY {sort_col} {direction}, id {tiebreak}
            LIMIT %s OFFSET %s
        """
        # ⚠️ Il conteggio di ripiego serve SOLO nel caso raro «pagina oltre
        # l'ultima»: li' la window function non ha righe su cui calcolare il
        # totale e risponderebbe zero. Senza, a chi e' rimasto su una pagina
        # stantia di una lista che si e' accorciata sotto di lui diremmo
        # «nessun risultato» — cioe' una cosa falsa, con l'aria di un dato.
        count_sql = f"""
            SELECT COUNT(*) FROM (
                {_DISTINTA_SELECT}
                {_TOTALI_LATERAL}
                {where_clause}
            ) q
        """
        rows, total = fetch_paged_with_total(
            data_sql,
            [*params, limit, offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=offset,
        )
        return [self._shape(row) for row in rows], total

    # Scopo: Dettaglio di una distinta (testata + display + totali derivati).
    # Risultato: None se non esiste — o se il perimetro non la lascia vedere,
    #        e i due casi sono volutamente indistinguibili al chiamante.
    def get_distinta(self, contabile_id: int) -> DistintaRow | None:
        self._guard_canale_sistema("get_distinta")
        sql = f"""
            {_DISTINTA_SELECT}
            {_TOTALI_LATERAL}
            WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # ══════════════════════════════════════════════════════════════
    #  Distinte — scrittura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Apre (o ritrova) la distinta manuale dell'operatore.
    # ⭐ E' un GET **or** CREATE, e la chiave di riuso comprende CHI STA
    #    LAVORANDO oltre alla giornata e al canale: due operatori non si
    #    contendono la stessa distinta, e il lock che sarebbe servito a
    #    governarla non si costruisce.
    # ⛔ L'operatore NON si passa: lo mette la funzione dall'identita' della
    #    connessione. Passarlo dal backend sarebbe una seconda verita'.
    # ⚠️ Il valore di ritorno e' il solo `id`: «creata» e «riaperta» non si
    #    distinguono dalla chiamata — si leggono dal dettaglio (ha righe o no).
    def get_or_create_distinta(
        self,
        *,
        centro_riscossione_id: int,
        data_contabile: date,
        data_registrazione: date | None = None,
        ente_incasso_id: int | None = None,
        codice_stato_interno: str = "BOZZA",
        origine: str = "MANUALE",
        meta: str = "{}",
    ) -> int:
        sql = """
            SELECT pagamenti.fn_get_or_create_vendite_contabile(
                p_centro_riscossione_id := %s,
                p_data_contabile        := %s,
                p_data_registrazione    := COALESCE(%s, CURRENT_DATE),
                p_ente_incasso_id       := %s,
                p_codice_stato_interno  := %s,
                p_meta                  := %s::jsonb,
                p_origine               := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(centro_riscossione_id),
                    data_contabile,
                    data_registrazione,
                    ente_incasso_id,
                    codice_stato_interno,
                    meta,
                    origine,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Compone la clausola SET di un UPDATE parziale, verificando che
    #        OGNI nome di colonna sia nella whitelist del suo oggetto.
    # ⛔ Nessun nome arriva mai in SQL senza passare di qui.
    @staticmethod
    def _set_clause(
        campi: dict[str, Any], consentite: frozenset[str], metodo: str
    ) -> tuple[str, list[Any]]:
        fuori = sorted(c for c in campi if c not in consentite)
        ErrorManager.require(
            not fuori,
            code=_E_CHIAMATA,
            message="Aggiornamento non ammesso su queste colonne.",
            detail=f"Colonne non aggiornabili: {', '.join(fuori)}",
            function_name=f"{_FN}.{metodo}",
        )
        assegnazioni: list[str] = []
        params: list[Any] = []
        for colonna, valore in campi.items():
            assegnazioni.append(
                f"{colonna} = %s::jsonb" if colonna in _JSONB_COLS else f"{colonna} = %s"
            )
            params.append(valore)
        return ", ".join(assegnazioni), params

    # Scopo: Aggiorna i campi che una persona compila sulla testata.
    # ⛔ Lo stato NON passa di qui: cambiarlo e' un'azione, e la matrice delle
    #    transizioni ha un guard suo che va fatto parlare.
    # Risultato: numero di righe toccate (0 = distinta inesistente o fuori
    #        perimetro, e il service lo traduce in 404).
    def update_distinta(self, contabile_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_DISTINTA_AGGIORNABILI, "update_distinta"
        )
        params.append(int(contabile_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili
               SET {set_clause}
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato della distinta risolvendo il codice a catalogo.
    # ⚠️ Un UPDATE solo: la transizione la giudicano i guard del database
    #    (matrice, quadratura col dichiarato, riapertura solo se MANUALE,
    #    chiusura con righe ancora pronte). Il backend non li replica.
    def set_stato_distinta(self, contabile_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili c
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_stati st
             WHERE c.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), codice_stato_interno])
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  Righe
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di una distinta, ordine stabile.
    # Nota: nessuna paginazione — le righe sono il dettaglio di UN documento e
    #       si leggono insieme alla sua testata; la lista cross-distinta (la
    #       coda del riconciliatore) e' un'altra cosa e ha il suo metodo.
    def list_righe(self, contabile_id: int) -> list[RigaContabileRow]:
        self._guard_canale_sistema("list_righe")
        # ⚠️ Solo le righe ATTIVE, e senza un interruttore per vederle tutte:
        # una riga disattivata non e' un dato da mostrare con un filtro, e un
        # parametro che nessuno passa e' superficie che invecchia. Quando
        # servira' davvero, si aggiunge con il suo consumatore.
        sql = f"""
            {_RIGA_SELECT}
            WHERE r.contabile_id = %s
              AND r.attivo IS TRUE
            ORDER BY r.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return [self._shape(row) for row in rows]

    # Scopo: Dettaglio di una singola riga contabile.
    def get_riga(self, riga_id: int) -> RigaContabileRow | None:
        self._guard_canale_sistema("get_riga")
        sql = f"""
            {_RIGA_SELECT}
            WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # Scopo: Crea una riga sotto una distinta.
    # ⚠️ Lo stato si risolve dal catalogo per codice: gli id sono smallint
    #    seminati e non si scrivono a mano da nessuna parte (mai id cablati).
    def create_riga(
        self,
        *,
        contabile_id: int,
        importo: Decimal,
        codice_stato_interno: str,
        riferimento_ente: str | None = None,
        data_pagamento: date | None = None,
        data_valuta: date | None = None,
        data_operazione: date | None = None,
        motivo_sospeso: str | None = None,
        meta: str = "{}",
    ) -> int:
        # ⛔ Niente `fattura_id`, `billing_account_id`, `scadenza_id` qui: una
        # riga NASCE senza destinazione (`DA_ABBINARE`), e l'abbinamento e' un
        # verbo con le sue regole — la coerenza rata/fattura e la capienza. Dei
        # parametri accettati qui e mai passati sarebbero una seconda porta per
        # scriverli, che aggirerebbe quel verbo senza dirlo.
        sql = """
            INSERT INTO pagamenti.vendite_contabili_righe (
                contabile_id, importo, stato_id, riferimento_ente,
                data_pagamento, data_valuta, data_operazione,
                motivo_sospeso, meta
            )
            SELECT
                %s, %s, st.id, %s,
                %s, %s, %s,
                %s, %s::jsonb
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE st.codice_interno = %s
               AND st.attivo IS TRUE
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(contabile_id), importo, riferimento_ente,
                    data_pagamento, data_valuta, data_operazione,
                    motivo_sospeso, meta,
                    codice_stato_interno,
                ],
            )
            row = cursor.fetchone()
        # Nessuna riga di ritorno = il codice di stato non esiste a catalogo:
        # non e' un dato dell'operatore, e il service lo traduce come tale.
        ErrorManager.require(
            row is not None,
            code="E_CONTABILE_STATO_NON_CONFIGURATO",
            message="Stato riga contabile non configurato.",
            detail=f"codice_interno={codice_stato_interno} assente o non attivo.",
            function_name=f"{_FN}.create_riga",
        )
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna i FATTI di una riga (importo, date, riferimento) e le
    #        decisioni che non sono un'azione di dominio.
    def update_riga(self, riga_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_RIGA_AGGIORNABILI, "update_riga"
        )
        params.append(int(riga_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili_righe
               SET {set_clause}
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato di una riga risolvendo il codice a catalogo.
    # ⚠️ Come per la testata: un UPDATE solo, e i guard del database dicono se
    #    la transizione e' ammessa e se i dati che quello stato pretende ci
    #    sono (fattura e cliente su ABBINATA, per esempio).
    def set_stato_riga(self, riga_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id), codice_stato_interno])
            return cursor.rowcount

    # Scopo: Imputa una riga a una fattura (e, quando c'e', a una rata).
    # ⭐ UN SOLO `UPDATE`: i dati dell'abbinamento e lo stato viaggiano insieme,
    #    perche' sono lo stesso gesto — «questa riga e' di questo documento».
    #    Separarli lascerebbe per un istante una riga abbinata a meta', che i
    #    guard rifiuterebbero comunque, ma con un messaggio sull'ordine delle
    #    scritture invece che sul merito.
    # ⚠️ `forzata` e' il SECONDO TEMPO della capienza (D14-d): il primo
    #    tentativo arriva senza, il guard rifiuta con la ragione e i numeri, e
    #    la conferma dell'operatore torna qui come `forzata = true` — che resta
    #    SCRITTA sulla riga, ed e' cio' che l'elenco a valle legge.
    def abbina_riga(
        self,
        *,
        riga_id: int,
        fattura_id: int,
        billing_account_id: int,
        scadenza_id: int | None,
        forzata: bool,
        motivo_forzatura: str | None,
        codice_stato_interno: str,
    ) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET fattura_id         = %s,
                   billing_account_id = %s,
                   scadenza_id        = %s,
                   forzata            = %s,
                   motivo_forzatura   = %s,
                   stato_id           = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(fattura_id), int(billing_account_id), scadenza_id,
                    bool(forzata), motivo_forzatura,
                    int(riga_id), codice_stato_interno,
                ],
            )
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  I saldi — le tre letture, e nient'altro le chiama
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il saldo di una RATA: residuo, in lavorazione, incassato.
    # ⭐ Tre numeri e non uno: «quanto manca», «quanto e' gia' digitato ma non
    #    registrato» e «quanto e' entrato davvero in banca» sono tre domande
    #    diverse, e la terza esclude i centri interni (fondi, compensazioni).
    # ⚠️ `escludi_riga_id` serve a chiedere lo spazio PRIMA DI SE': e' cosi' che
    #    si verifica se una riga ci sta, senza contarsi addosso.
    def get_saldo_rata(
        self, scadenza_id: int, *, escludi_riga_id: int | None = None
    ) -> dict[str, Any] | None:
        sql = """
            SELECT saldo, in_lavorazione, incassato, has_movimenti
              FROM pagamenti.fn_get_saldo_rata(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(scadenza_id), escludi_riga_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Il residuo di un DOCUMENTO e il flag «ha movimenti».
    # ⚠️ Due numeri, non tre: a questo livello il database non sa ancora dire
    #    l'incassato (richiesta DB-10 al team DB). Chi compone la risposta lo
    #    dichiara `None`, e ⛔ non lo inventa sommando le rate: una riga puo'
    #    avere fattura SENZA rata — il fondo fattura e' esattamente cosi' — e
    #    quel denaro non comparirebbe in nessuna somma di rate.
    def get_saldo_fattura(self, fattura_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT saldo, has_movimenti
              FROM pagamenti.fn_get_saldo_fattura(%s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Il denaro di un documento gia' digitato ma NON ancora registrato.
    def get_saldo_fattura_contabili(self, fattura_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT saldo_contabile, has_righe_postabili
              FROM pagamenti.fn_get_saldo_fattura_contabili(%s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Le rate di un documento, con il loro saldo accanto.
    # ⭐ Sta in `pagamenti` e non in `vendite` benche' le rate siano di vendite:
    #    la domanda e' «quanto resta su questa rata», e a saperla rispondere e'
    #    questo schema. ⚠️ E `vendite` non potrebbe chiederglielo: le chiamate
    #    laterali fra moduli di pari livello non sono ammesse (api.md).
    def list_rate_con_saldo(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                sc.id                AS scadenza_id,
                sc.numero_rata,
                sc.data_scadenza,
                sc.importo,
                s.saldo              AS residuo,
                s.in_lavorazione,
                s.incassato,
                s.has_movimenti
              FROM vendite.fatture_scadenze sc
              CROSS JOIN LATERAL pagamenti.fn_get_saldo_rata(sc.id) s
             WHERE sc.fattura_id = %s
             ORDER BY sc.numero_rata NULLS LAST, sc.data_scadenza NULLS LAST, sc.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════════
    #  Le due code di lavoro
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di TUTTE le distinte in uno degli stati chiesti — la coda
    #        del riconciliatore.
    # ⭐ Un endpoint solo per due code: «da abbinare» e «sospese» sono due
    #    mestieri diversi (D12-f) e due voci di menu, ma la stessa lista con un
    #    filtro diverso gia' impostato. Due definizioni a catalogo per due
    #    schermate identiche sarebbero due cose da tenere allineate.
    def list_righe_coda(
        self,
        *,
        stati: tuple[str, ...],
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[RigaContabileRow], int]:
        self._guard_canale_sistema("list_righe_coda")

        conditions = ["r.attivo IS TRUE", "rs.codice_interno = ANY(%s)"]
        params: list[Any] = [list(stati)]
        if billing_account_id is not None:
            conditions.append("r.billing_account_id = %s")
            params.append(billing_account_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)

        sort_col = RIGHE_SORT_COLUMNS.get(order_by, "data_pagamento")
        direction = sql_order_direction(order_dir, default_desc=True)
        tiebreak = sql_tiebreak_direction(direction)

        # La coda porta con se' la sua distinta: una riga senza il documento da
        # cui viene non si lavora — l'operatore deve poterci tornare.
        select_sql = f"""
            {_RIGA_SELECT}
              JOIN pagamenti.vendite_contabili c ON c.id = r.contabile_id
             WHERE {" AND ".join(conditions)}
        """
        data_sql = f"""
            SELECT *, COUNT(*) OVER () AS total_count FROM (
                {select_sql}
            ) q
            ORDER BY {sort_col} {direction}, id {tiebreak}
            LIMIT %s OFFSET %s
        """
        count_sql = f"SELECT COUNT(*) FROM ({select_sql}) q"
        rows, total = fetch_paged_with_total(
            data_sql,
            [*params, limit, offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=offset,
        )
        return [self._shape(row) for row in rows], total

    # Scopo: L'elenco delle rate uscite dalla banda di capienza.
    # ⭐ Senza questo elenco la forzatura sarebbe «un modo per nascondere, non
    #    per registrare»: e' la ragione per cui la vista sta nello stesso lotto
    #    del guard che permette di forzare.
    # ⚠️ `motivo` ha due valori e vanno mostrati entrambi: `SOVRA_INCASSATA` e
    #    `MOVIMENTO_CONTRARIO` — un rimborso dove non era entrato niente e' il
    #    caso che ha fatto cadere l'asimmetria di D1-bis.
    def list_rate_fuori_capienza(
        self,
        *,
        motivo: str | None = None,
        billing_account_id: int | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_rate_fuori_capienza")

        conditions: list[str] = []
        params: list[Any] = []
        if motivo is not None:
            conditions.append("v.motivo = %s")
            params.append(motivo)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sort_col = RATE_FUORI_CAPIENZA_SORT_COLUMNS.get(order_by, "data_scadenza")
        direction = sql_order_direction(order_dir, default_desc=True)
        tiebreak = sql_tiebreak_direction(direction)

        select_sql = f"""
            SELECT v.*
              FROM pagamenti.vw_rate_fuori_capienza v
              {where_clause}
        """
        data_sql = f"""
            SELECT *, COUNT(*) OVER () AS total_count FROM (
                {select_sql}
            ) q
            ORDER BY {sort_col} {direction}, scadenza_id {tiebreak}
            LIMIT %s OFFSET %s
        """
        count_sql = f"SELECT COUNT(*) FROM ({select_sql}) q"
        return fetch_paged_with_total(
            data_sql,
            [*params, limit, offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=offset,
        )

    # ══════════════════════════════════════════════════════════════
    #  La madre del posting
    # ══════════════════════════════════════════════════════════════

    # Scopo: Registra la distinta — trasforma in movimenti contabili le righe
    #        pronte a diventarlo, e chiude la distinta.
    # ⭐ UNA SOLA `SELECT`, quindi atomica per costruzione: l'atomicita' e'
    #    DENTRO la funzione. ⛔ Nessun `transaction.atomic()` attorno a piu'
    #    statement, nessun ciclo che posta le righe una a una.
    # ⚠️ `righe_attese` e `totale_atteso` sono la DICHIARAZIONE di chi conferma
    #    (quante righe pronte aveva davanti e per che totale): sono facoltativi
    #    ma LEGATI — o tutti e due o nessuno. Mezza dichiarazione non si puo'
    #    verificare, e accettarla significherebbe registrare senza controllo
    #    credendo di averlo fatto.
    # ⭐ Non solleva su «niente da registrare»: risponde `NULLA_DA_POSTARE` ed
    #    e' un esito, non un errore. Il backend lo passa senza interpretarlo.
    def posta_contabile(
        self,
        *,
        contabile_id: int,
        righe_attese: int | None = None,
        totale_atteso: Decimal | None = None,
    ) -> RicevutaPosting:
        sql = """
            SELECT movimenti_creati, righe_postate, righe_saltate,
                   totale_postato, esito
              FROM pagamenti.fn_posta_contabile(
                   p_contabile_id  := %s,
                   p_righe_attese  := %s,
                   p_totale_atteso := %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), righe_attese, totale_atteso])
            rows = rows_to_list(cursor)
        # La funzione ritorna sempre una riga: se non ci fosse, il contratto
        # sarebbe cambiato sotto e tacere sarebbe la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La registrazione non ha prodotto nessuna ricevuta.",
            detail="pagamenti.fn_posta_contabile non ha restituito righe.",
            function_name=f"{_FN}.posta_contabile",
        )
        return rows[0]  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Mapping di riga
    # ══════════════════════════════════════════════════════════════

    # Scopo: Normalizza le colonne jsonb lette da cursor RAW (il driver le
    #        restituisce come stringa fuori dall'ORM: senza questo, il primo
    #        `.get()` del consumatore esplode su una `str`).
    # Nota: una funzione sola per testata e riga — erano due copie identiche, e
    #       due copie della stessa normalizzazione divergono alla prima colonna
    #       jsonb che se ne aggiunge.
    @staticmethod
    def _shape(row: dict[str, Any]) -> dict[str, Any]:
        for col in _JSONB_COLS:
            if col in row:
                row[col] = jsonb_out(row[col])
        return row
