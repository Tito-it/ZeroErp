# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i repository dello schema `magazzino` condividono — il
#        guard contro il canale di sistema (le tabelle sono sotto RLS: lette da
#        un ruolo BYPASSRLS perderebbero il perimetro) e la lista paginata in
#        UNA valutazione (`COUNT(*) OVER ()` + conteggio di ripiego).
# Note: Stampo `magazzino/services/_helpers.py`: materiale INTERNO del dominio,
#       non un building block di progetto. Nato il 2026-09-21 alla seconda
#       occorrenza — `anagrafiche_magazzino_repository` (magazzini, ubicazioni,
#       lotti: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config)
#       avrebbe ricopiato i due staticmethod di `MagazzinoRepository`.
#
#       ⚠️ `order_clause` si compone dalle WHITELIST e MAI da input utente: qui
#       dentro finisce in una stringa SQL.
#
#       ⭐ 2026-09-26: `meta_mai_null`, la regola `meta` NOT NULL che i due
#       repository scrivevano ciascuno a modo suo dentro la composizione SQL
#       (`_valore` qui, `json.dumps(val or {})` nel documento interno) — la
#       composizione e' passata ai BB core `execute_dynamic_insert` /
#       `execute_dynamic_update` / `sql_set_clause`, la regola di DOMINIO resta qui.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db._helpers import fetch_paged_with_total
from apps.core.services.error_manager import ErrorManager
from apps.core.services.system_context import connection_role_bypasses_rls

# Il guard di parametro del dominio, gia' a catalogo (TECNICO): e' il codice
# dei soli guard strutturali dei repository, che un operatore non puo'
# causare compilando qualcosa.
E_CHIAMATA = "E_MAG_CHIAMATA_NON_VALIDA"


# Scopo: Impedisce che una lettura di perimetro giri su un ruolo BYPASSRLS.
# Contesto: le policy di `magazzino` sono il cancello delle liste (piu' lo
#        scope applicativo che si somma). Su un ruolo che le scavalca la lista
#        non fallirebbe: mostrerebbe la merce di TUTTI gli emittenti.
def guard_canale_sistema(function_name: str) -> None:
    ErrorManager.require(
        not connection_role_bypasses_rls(),
        code=E_CHIAMATA,
        message="Operazione non disponibile dal canale di sistema.",
        detail=(
            "Le tabelle di magazzino sono protette da RLS: lette da un "
            "ruolo BYPASSRLS perderebbero il perimetro emittente. Usare "
            "la connessione dell'utente della richiesta."
        ),
        function_name=function_name,
    )


# Scopo: La colonna `meta` di OGNI tabella scritta dal dominio (magazzini,
#        ubicazioni, lotti, testate e righe del documento interno) e' `jsonb
#        NOT NULL DEFAULT '{}'` (docs/it/dbzero/magazzino/tabelle): un `None`
#        diventerebbe NULL e un 23502, quindi `None` vale «meta vuoto» — `{}`.
#        Non si tocca un `meta` ASSENTE: all'INSERT resta il DEFAULT del DB, in
#        un PATCH la colonna non viaggia. Restituisce una COPIA se cambia.
def meta_mai_null(valori: dict[str, Any]) -> dict[str, Any]:
    if "meta" in valori and valori["meta"] is None:
        return {**valori, "meta": {}}
    return valori


# Scopo: Esegue una lista paginata: pagina + totale in UNA valutazione
#        (`COUNT(*) OVER ()`), e il conteggio di ripiego sulla pagina stantia.
def lista_paginata(
    *,
    select_sql: str,
    params: list[Any],
    order_clause: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    data_sql = f"""
        SELECT *, COUNT(*) OVER () AS total_count FROM (
            {select_sql}
        ) q
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
    """  # noqa: S608 — select_sql dalle SELECT costanti dei repository del dominio, order_clause da sql_order_clause/whitelist *_SORT_COLUMNS; valori come parametri
    count_sql = f"SELECT COUNT(*) FROM ({select_sql}) q"  # noqa: S608 — select_sql dalle SELECT costanti dei repository del dominio; valori come parametri
    return fetch_paged_with_total(
        data_sql,
        [*params, limit, offset],
        fallback_count_sql=count_sql,
        fallback_params=list(params),
        offset=offset,
    )
