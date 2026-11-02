# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Leggi prima la testata» in una funzione sola: carica un record per
#        id e, se non c'e', solleva il codice NOT_FOUND del dominio. E' il
#        guard con cui un endpoint satellite (righe, riepilogo IVA, revisioni,
#        componenti) risponde 404 su un padre fuori perimetro invece di un
#        200 con lista vuota.
# Note: ⚠️ Non e' una difesa aggiuntiva alla RLS: e' l'ORDINE giusto di
#        lettura (api.md §«Scope emittente»). La RLS filtra gia' il satellite;
#        senza questo guard pero' il client riceve un pannello vuoto e non sa
#        distinguere «non ci sono righe» da «non puoi vederlo».
#        ⭐ Regola del 2 (2026-09-21): `ordini_service` e `ddt_service` avevano
#        gia' un `_get_testata_or_raise` identico a meno di codice e messaggio;
#        `preventivi` e `resi` erano la terza e la quarta copia in arrivo.
#        I domini tengono il proprio nome (`_get_testata_or_raise`) e delegano
#        qui: codice, messaggio e `detail` si compongono in un posto solo.
#        ⭐ Stessa regola, stesso giorno, per `riga_del_padre_o_not_found`: il
#        guard «la riga esiste ED appartiene al documento dell'URL» viveva in
#        undici copie (ordini, DDT, resi) piu' due varianti a due passi
#        (preventivi, contratti). Non e' una regola di dominio ripetuta: e' la
#        coerenza del PERCORSO — senza, `/ordini/999/righe/24/` aprirebbe la
#        riga 24 di un altro ordine.
#        ⭐ Stessa regola il 2026-10-04 per `pagina_dopo_testata` (§9.6 del
#        brief-db-liste-righe-documento, Tid): la pagina della lista delle
#        righe era scritta sei volte — preventivo, ordine, DDT, reso, fattura,
#        contratto — piu' la distinta del catalogo, ognuna con la sua lettura
#        della testata davanti, e nessun test la provava: toglierla lasciava la
#        suite verde e trasformava un 404 in una lista vuota.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from apps.core.services.error_manager import ErrorManager

T = TypeVar("T")


# Scopo: Il nucleo: un'entita' GIA' letta, o il 404 del dominio. Ritorna
#        l'entita' (narrowing per il type checker compreso) o solleva
#        `ServiceError` con `code`, che deve essere di classe NON_TROVATO.
#        E' la sede unica della regola: `testata_o_not_found` legge e delega
#        qui, `anagrafiche._validators.require_found` (l'helper storico di
#        quel dominio) delega qui.
def o_not_found(
    entita: T | None,
    *,
    code: str,
    message: str,
    detail: str | None = None,
    function_name: str | None = None,
) -> T:
    # Senza `function_name` resta il default di ErrorManager: non si
    # inventa un nome per un chiamante che non lo dichiara.
    nome_funzione: dict[str, Any] = (
        {"function_name": function_name} if function_name else {}
    )
    ErrorManager.require(
        entita is not None,
        code=code,
        message=message,
        detail=detail,
        **nome_funzione,
    )
    assert entita is not None
    return entita


# Scopo: Carica la testata con `getter(entity_id)` e la ritorna; se il getter
#        risponde `None` (id inesistente O fuori perimetro RLS: per il client
#        sono la stessa cosa) solleva `ServiceError` con `code` — che deve essere
#        un codice di classe NON_TROVATO, cosi' il middleware risponde 404.
#        `id_name` e' il nome del parametro nel `detail` (`ordine_id=7`).
def testata_o_not_found(
    getter: Callable[[int], T | None],
    entity_id: int,
    *,
    code: str,
    message: str,
    id_name: str,
    function_name: str,
) -> T:
    return o_not_found(
        getter(entity_id),
        code=code, message=message,
        detail=f"{id_name}={entity_id}", function_name=function_name,
    )


# Scopo: Carica la riga con `getter(riga_id)` e la ritorna se esiste ED e'
#        del padre richiesto (`riga[chiave_padre] == padre_id`); altrimenti
#        solleva `ServiceError` con `code` (classe NON_TROVATO → 404).
#        ⚠️ Un id incrociato nell'URL — riga di un altro documento — e' lo
#        stesso 404 di una riga inesistente: al client non si dice a chi
#        appartiene. Il `detail` porta i due id CHIESTI, per il log.
def riga_del_padre_o_not_found(
    getter: Callable[[int], dict[str, Any] | None],
    riga_id: int,
    *,
    padre_id: int,
    chiave_padre: str,
    code: str,
    message: str,
    function_name: str,
) -> dict[str, Any]:
    riga = getter(riga_id)
    # `int(...)` su entrambi i lati: la riga arriva dal DB (int), il padre
    # dall'URL (int) o da un chiamante interno; un confronto `7 == "7"` falso
    # sarebbe un 404 muto su una riga che invece esiste.
    appartiene = (
        riga is not None
        and riga.get(chiave_padre) is not None
        and int(riga[chiave_padre]) == int(padre_id)
    )
    ErrorManager.require(
        appartiene,
        code=code,
        message=message,
        detail=f"{chiave_padre}={padre_id} riga_id={riga_id}",
        function_name=function_name,
    )
    assert riga is not None
    return riga


# Scopo: «Leggi prima la testata» per una PAGINA di righe: `leggi_testata()`
#        (che solleva il 404 del dominio, di solito il `_get_testata_or_raise`
#        del service) e solo dopo `leggi_pagina(padre_id, **opzioni)` (il
#        `list_righe_pagina` del repository: ricerca, ordinamento, pagina,
#        filtri propri). Ritorna `(righe, totale)`.
# ⛔ L'ORDINE e' la regola, ed e' la ragione per cui sta in un posto solo: le
#    righe stanno dietro RLS e una vista `security_invoker`, quindi lette per
#    prime su un padre fuori perimetro rispondono zero righe — un 200 con la
#    lista vuota, che al client dice «non ci sono righe» invece di «non puoi
#    vederlo».
def pagina_dopo_testata(
    leggi_testata: Callable[[], object],
    leggi_pagina: Callable[..., tuple[list[dict[str, Any]], int]],
    padre_id: Any,
    **opzioni: Any,
) -> tuple[list[dict[str, Any]], int]:
    leggi_testata()
    return leggi_pagina(padre_id, **opzioni)
