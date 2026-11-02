# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per audit sessioni — INSERT e query su dbops.sessioni_utente.
#        Traccia login, refresh, logout, scadenza, revoca token JWT.
#        Espone query sessioni attive per l'utente (CTE con stato derivato).
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    RicercaFull,
    rows_to_list,
    sql_order_clause,
)


# Le sessioni ATTIVE di un utente, in tre pezzi che la lista completa, la
# pagina del pannello e il conteggio compongono: la CTE (ultimo evento per sid
# + primo LOGIN), la proiezione e il FROM/WHERE. Una sede sola per la regola
# «attiva»: fino al 2026-09-27 c'era una query sola, e la pagina e il
# conteggio ne avrebbero fatte due copie.
# ⚠️ La CTE prende l'utente DUE volte (`%s` posizionali): i parametri si
#    scrivono `[auth_user_id, auth_user_id, ...]`.
_SESSIONI_ATTIVE_CTE = """
    WITH ranked AS (
        SELECT jti, evento, ip_address, user_agent, data_insert,
               -- `id DESC` spareggia due eventi dello stesso sid con lo stesso
               -- istante (LOGOUT e REFRESH nella stessa transazione): senza, la
               -- sessione a volte risulta attiva e a volte no.
               ROW_NUMBER() OVER (PARTITION BY jti ORDER BY data_insert DESC, id DESC) AS rn
          FROM dbops.sessioni_utente
         WHERE auth_user_id = %s
           AND jti IS NOT NULL
           AND jti != ''
    ),
    primo_login AS (
        SELECT jti, MIN(data_insert) AS data_inizio
          FROM dbops.sessioni_utente
         WHERE auth_user_id = %s
           AND jti IS NOT NULL
           AND jti != ''
           AND evento = 'LOGIN'
      GROUP BY jti
    )
"""

# ⭐ `host(ip_address)` e non `ip_address::text` (2026-09-27): il cast a testo di
#    un `inet` porta la maschera, e il pannello mostrava «127.0.0.1/32». Stessa
#    espressione nella ricerca (`_RICERCA_SESSIONI_ATTIVE`): si cerca su cio'
#    che si mostra.
_SESSIONI_ATTIVE_SELECT = """
    SELECT r.jti,
           r.evento            AS ultimo_evento,
           host(r.ip_address)  AS ip_address,
           r.user_agent,
           pl.data_inizio,
           r.data_insert       AS data_ultimo_evento
"""

_SESSIONI_ATTIVE_FROM = """
      FROM ranked r
      LEFT JOIN primo_login pl ON pl.jti = r.jti
     WHERE r.rn = 1
       AND r.evento IN ('LOGIN', 'REFRESH')
       AND r.data_insert > now() - INTERVAL '1 day'
"""

# Whitelist ORDER BY della lista `core.sessioni_attive`: chiave = `campo_sorgente`
# del catalogo (cio' che il frontend manda come `order_by`), valore = colonna
# della CTE. `ip_address` ordina l'`inet` vero, non il testo: `10.0.0.9` prima
# di `10.0.0.10`.
# ⚠️ `data_inizio` e' NULL quando il LOGIN della sessione non e' piu' nel
#    registro: col verso naturale DESC (`colonne_desc`) il vuoto va in fondo,
#    in ASC in testa — la regola «NULL = minimo» di `sql_order_direction`.
# `dispositivo` (lo user agent) NON ordina: a video e' «browser / sistema»
# ricavato dal frontend, e ordinare la stringa grezza metterebbe in fila
# «Mozilla/5.0 (…» senza un ordine che l'operatore riconosca.
SESSIONI_ATTIVE_ORDER_COLUMNS: dict[str, str] = {
    "ip_address": "r.ip_address",
    "data_ultimo_evento": "r.data_insert",
    "data_inizio": "pl.data_inizio",
}

# Colonne DATA della whitelist qui sopra: senza `order_dir` ordinano DESC
# (regola di Tid del 2026-09-02, presidio `test_liste_configurabili_seed` test 10).
SESSIONI_ATTIVE_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_ultimo_evento", "data_inizio"})

# Cosa si PUO' cercare nella lista; cosa si cerca lo dice il catalogo
# (`add_ricerca_full_condition`). ⭐ «Dispositivo» cerca lo user agent GREZZO:
# «firefox» o «windows» lo trovano, ed e' da li' che il frontend ricava cio'
# che mostra.
_RICERCA_SESSIONI_ATTIVE = RicercaFull("core.sessioni_attive", {
    "user_agent": "r.user_agent",
    "ip_address": "host(r.ip_address)",
})


class SessionAuditRepository:
    """Accesso SQL alla tabella dbops.sessioni_utente (insert-only)."""

    # Scopo: Inserisce un evento di sessione nella tabella dbops.sessioni_utente.
    def log_session_event(
        self,
        *,
        auth_user_id: int,
        evento: str,
        jti: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        dettaglio: dict[str, Any] | None = None,
    ) -> None:
        sql = """
            INSERT INTO dbops.sessioni_utente
                (auth_user_id, evento, jti, ip_address, user_agent,
                 request_id, dettaglio)
            VALUES
                (%s, %s, %s, %s::inet, %s, %s::uuid, %s::jsonb)
        """
        params: list[Any] = [
            auth_user_id,
            evento,
            jti,
            ip_address,
            user_agent,
            request_id,
            json.dumps(dettaglio or {}),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    # Scopo: Recupera le sessioni attive per un utente, TUTTE e senza pagine.
    # Una sessione e' attiva se l'ultimo evento per quel jti e' LOGIN o REFRESH
    # e il timestamp e' entro il TTL del refresh token (1 giorno).
    # ⚠️ Non e' la lista del pannello (quella e' `list_sessioni_attive_paginata`):
    #    la legge «revoca tutte» (`SessioniRevocaTutteView`), che deve scrivere
    #    una REVOCA per OGNI sessione attiva — una pagina ne perderebbe.
    def list_sessioni_attive(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = (
            f"{_SESSIONI_ATTIVE_CTE} {_SESSIONI_ATTIVE_SELECT} {_SESSIONI_ATTIVE_FROM}"
            " ORDER BY r.data_insert DESC"
        )  # frammenti SQL letterali del modulo, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id, auth_user_id])
            return rows_to_list(cursor)

    # Scopo: La lista del pannello «altre sessioni attive» (`core.sessioni_attive`):
    #        paginata, ordinata sulla whitelist e con la ricerca libera del
    #        catalogo. Ritorna (righe della pagina, totale).
    # ⛔ La sessione corrente si esclude QUI, nella SQL (`escludi_jti`), e non
    #    piu' nella view: filtrata in Python DOPO la pagina, il conteggio
    #    avrebbe contato una riga in piu' e l'ultima pagina ne avrebbe mostrata
    #    una in meno (brief-db-liste-datatable-grezze §4.1 riga 1).
    # ⚠️ `IS DISTINCT FROM` e non `<>`: senza sid (`None`) non c'e' niente da
    #    escludere, e `r.jti <> NULL` avrebbe tolto TUTTE le righe.
    def list_sessioni_attive_paginata(
        self, auth_user_id: int, *, escludi_jti: str | None,
        search: str | None = None,
        order_by: str | None = None, order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=SESSIONI_ATTIVE_ORDER_COLUMNS, default="r.data_insert",
            default_desc=True, tiebreak="r.jti",
            colonne_desc=SESSIONI_ATTIVE_SORT_COLONNE_DATA,
        )
        conditions, params = self._condizioni_altre_sessioni(auth_user_id, escludi_jti)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_SESSIONI_ATTIVE)
        from_where = self._from_where(conditions)
        return fetch_paged_with_total(
            f"""
            {_SESSIONI_ATTIVE_CTE}
            {_SESSIONI_ATTIVE_SELECT},
                   COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # frammenti letterali del modulo, ORDER BY da sql_order_clause su SESSIONI_ATTIVE_ORDER_COLUMNS, ricerca da add_ricerca_full_condition, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=self._sql_conta(from_where),  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

    # Scopo: Quante sono le ALTRE sessioni attive dell'utente, a prescindere
    #        dalla ricerca: e' il numero di cui parlano il badge del pannello e
    #        la conferma di «revoca tutte», che revoca tutte e non le trovate.
    def conta_sessioni_attive(self, auth_user_id: int, *, escludi_jti: str | None) -> int:
        conditions, params = self._condizioni_altre_sessioni(auth_user_id, escludi_jti)
        with connection.cursor() as cursor:
            cursor.execute(self._sql_conta(self._from_where(conditions)), params)
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    # Scopo: FROM/WHERE delle sessioni attive con le condizioni in piu'.
    @staticmethod
    def _from_where(conditions: list[str]) -> str:
        return f"{_SESSIONI_ATTIVE_FROM} AND " + " AND ".join(conditions)

    # Scopo: il conteggio su un FROM/WHERE: una sede sola per il fallback della
    #        pagina e per `conta_sessioni_attive`, che non devono divergere.
    @staticmethod
    def _sql_conta(from_where: str) -> str:
        return f"{_SESSIONI_ATTIVE_CTE} SELECT COUNT(*) {from_where}"  # frammenti SQL letterali del modulo, valori come parametri

    # Scopo: i parametri della CTE (l'utente, due volte) e la condizione che
    #        toglie la sessione corrente — la parte comune a pagina e conteggio.
    @staticmethod
    def _condizioni_altre_sessioni(
        auth_user_id: int, escludi_jti: str | None,
    ) -> tuple[list[str], list[Any]]:
        return ["r.jti IS DISTINCT FROM %s"], [auth_user_id, auth_user_id, escludi_jti]
