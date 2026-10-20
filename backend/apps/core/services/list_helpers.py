# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per la validazione dei parametri lista nei service
#        (ordinamento, ...). BB cross-dominio estratto con la "regola del 2":
#        il pattern "order_by in whitelist + order_dir in {asc,desc}" era
#        duplicato in catalogo_service e listini_service (4 occorrenze).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, overload

from collections.abc import Collection

from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import order_dir_ammessa
from apps.core.services.error_manager import ErrorManager


# Scopo: Valida order_by contro una whitelist di colonne e order_dir col
#        predicato unico `order_dir_ammessa`. Il chiamante passa la propria
#        whitelist (`allowed_columns`) e il proprio `error_code` di dominio.
#        Solleva ServiceError (loggato a DB) sul primo parametro non valido;
#        ritorna la coppia validata, con `order_dir` NORMALIZZATO (`asc`/`desc`
#        minuscolo, `None` se assente).
#
#        NB: DISTINTO da `apps.core.api.search_validators.validate_order_params`,
#        che ha semantica diversa (normalizza maiuscole, ritorna tupla opzionale,
#        nessun error_code di dominio). Questo opera nei service con rigore
#        fail-fast e codice errore parametrico.
# ⭐ Il contratto per il type checker (2026-10-09): con un `order_by` presente
#    la colonna torna presente; solo un `order_by` assente (con `nullable`) puo'
#    tornare `None`.
@overload
def validate_order_params(
    order_by: str,
    order_dir: str | None,
    *,
    allowed_columns: Collection[str],
    error_code: str,
    function_name: str,
    nullable: bool = False,
) -> tuple[str, str | None]: ...
@overload
def validate_order_params(
    order_by: str | None,
    order_dir: str | None,
    *,
    allowed_columns: Collection[str],
    error_code: str,
    function_name: str,
    nullable: bool = False,
) -> tuple[str | None, str | None]: ...
def validate_order_params(
    order_by: str | None,
    order_dir: str | None,
    *,
    allowed_columns: Collection[str],
    error_code: str,
    function_name: str,
    nullable: bool = False,
) -> tuple[str | None, str | None]:
    # ⭐ `nullable` per le liste in cui «non specificato» e' un valore legittimo:
    #    l'ordine lo decide allora il DEFAULT del repository, che e' quello
    #    dichiarato a catalogo. E' la stessa apertura che `validate_enum_param`
    #    ha da sempre per i filtri opzionali — senza, ogni dominio che ammette
    #    l'assenza si riscrive il guard in casa, ed e' esattamente quello che era
    #    successo in `vendite_service` (sette copie).
    # ⚠️ `Collection[str]` e non `frozenset[str]`: le whitelist di vendite sono
    #    `dict[chiave esposta -> colonna SQL]`, e `in`/`sorted()` su un dict
    #    guardano le chiavi — che sono proprio i valori ammessi. L'annotazione
    #    stretta era l'unica cosa che diceva «questo BB non fa per te».
    # ⛔ La DIREZIONE la giudica `order_dir_ammessa`, la stessa regola di
    #    `sql_order_direction` e di `PayloadValidator.validate_order_by`
    #    (decisione Tid 2026-09-26). Fino a quel giorno qui c'era una seconda
    #    regola, case-sensitive: `DESC` era un 400 sulle liste validate qui e
    #    passava su tutte le altre, e meta' dei chiamanti rimediava con un
    #    `.lower()` scritto a mano prima della chiamata. Ora maiuscole e spazi
    #    ai lati sono ammessi ovunque, e un valore estraneo e' rifiutato
    #    ovunque — qui col codice del dominio.
    # ⭐ Il valore ritorna NORMALIZZATO: diversi chiamanti passano la coppia
    #    ritornata a una funzione DB o a un repository, e la forma canonica
    #    toglie a valle ogni dubbio sulle maiuscole.
    # ⚠️ `nullable` resta la regola sulla PRESENZA, che e' del chiamante: senza,
    #    una direzione assente (None, vuota, soli spazi) e' un 400 come prima.
    #    Con, torna `None` e l'ordine lo decide il default del repository.
    ErrorManager.require(
        (nullable and order_by is None) or order_by in allowed_columns,
        code=error_code,
        message="Parametri ordinamento non validi.",
        detail="order_by deve essere uno tra: " + ", ".join(sorted(allowed_columns)),
        context={"order_by": order_by},
        function_name=function_name,
        log_to_db=True,
    )
    direzione = (order_dir or "").strip().lower() or None
    ErrorManager.require(
        order_dir_ammessa(order_dir) and (nullable or direzione is not None),
        code=error_code,
        message="Parametri ordinamento non validi.",
        detail="order_dir deve essere 'asc' o 'desc'",
        context={"order_dir": order_dir},
        function_name=function_name,
        log_to_db=True,
    )
    return order_by, direzione


# Scopo: Valida un parametro enum contro la whitelist del chiamante (aree,
#        stadi, sort key, ...). `None` e' ammesso quando `nullable` (filtro
#        opzionale assente). `allowed` come sequenza ORDINATA: l'ordine entra
#        nel messaggio `detail` (stabile per test e utenti). Estratto
#        2026-07-06 (regola del 2, ok Tid): unifica i blocchi
#        "ErrorManager.require(x in WHITELIST)" duplicati nei service vendite
#        (area fermi, stadio competenza, area backlog, sort_by/sort_dir lotto
#        fatture). Speculare a validate_order_params/validate_pagination.
def validate_enum_param(
    value: str | None,
    *,
    allowed: tuple[str, ...],
    param_name: str,
    error_code: str,
    function_name: str,
    nullable: bool = True,
    log_to_db: bool = False,
) -> str | None:
    ErrorManager.require(
        (value is None and nullable) or value in allowed,
        code=error_code,
        message=f"Parametro {param_name} non valido.",
        detail=f"Valori ammessi: {', '.join(allowed)}",
        # ⛔ Niente `field`: e' un parametro di QUERY, non un input del form
        # (api.md §«Escono solo i nomi», decisione di Tid 2026-10-20). Il nome
        # resta nel context diagnostico come `parametro`, e nel messaggio.
        context={param_name: value, "parametro": param_name},
        function_name=function_name,
        log_to_db=log_to_db,
    )
    return value


# Scopo: Valida i parametri di paginazione page-based (page >= 1,
#        1 <= page_size <= MAX_LIMIT) e ritorna l'offset calcolato `(page-1)*page_size`.
#        `error_code`/`function_name` parametrici. Speculare a `validate_order_params`.
#        NB: convenzione PAGE-based; per le liste offset-based esiste già
#        `parse_list_params` (apps/core/api/payload_validators.py).
def validate_pagination(
    page: int,
    page_size: int,
    *,
    error_code: str,
    function_name: str,
) -> int:
    ErrorManager.require(
        page >= 1,
        code=error_code,
        message="Parametri paginazione non validi.",
        detail="page deve essere >= 1",
        context={"page": page},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= page_size <= MAX_LIMIT,
        code=error_code,
        message="Parametri paginazione non validi.",
        detail=f"page_size deve essere compreso tra 1 e {MAX_LIMIT}",
        context={"page_size": page_size},
        function_name=function_name,
        log_to_db=True,
    )
    return (page - 1) * page_size


# Scopo: Envelope di una collezione CONSEGNATA PER INTERO — le figlie di
#        un'entita' (UoM operative, componenti, note, versioni di un listino).
#        Nessun `LIMIT` a monte, quindi `count` e' il totale e non una stima.
#
# ⭐ Qui `len(results)` e' legittimo, ed e' l'unico caso in cui lo e': non
#    descrive le righe consegnate, LE CONTA TUTTE — la query non ha tetto.
#
# ⛔ NON si usa per un LOOKUP, che un `LIMIT` puo' aver tagliato: li' `count`
#    varrebbe `limit` su un insieme piu' grande, cioe' CONFERMEREBBE il
#    troncamento invece di rivelarlo (api.md §«Il `count` non si deriva MAI
#    dalle righe che stai consegnando»). Il lookup dichiara `troncato` accanto
#    al conteggio, e per costruirlo c'e' `apps.core.db._helpers.fetch_con_sonda`.
#
# Regola del 2 (2026-09-10, ok Tid): lo stesso helper era scritto in
# `catalogo_service` e in `listini_service` con lo stesso nome privato. Il
# valore dell'estrazione non e' la riga risparmiata — e' che il NOME dica di
# quale delle due nature si tratta, perche' era proprio l'averle servite dallo
# stesso helper a rendere la forma sbagliata indistinguibile da quella giusta.
def collezione_completa(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {"count": len(results), "results": results}
