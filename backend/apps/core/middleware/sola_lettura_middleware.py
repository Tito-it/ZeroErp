# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Ogni `GET`/`HEAD` delle API gira in una transazione di SOLA LETTURA
#        (brief-be-letture-in-transazione-sola-lettura): «una lettura non
#        scrive» smette di essere una promessa del codice e diventa una
#        garanzia del DB. Una scrittura tentata dentro la view fallisce, e il
#        BB la traduce in `E_SCRITTURA_IN_LETTURA` col nome della view nel log.
# Note: ⭐ Il blocco e' il BB `transazione_sola_lettura`, lo stesso dei tool
#       dell'assistente (regola del 2): qui si decide solo QUANDO aprirlo.
#       ⭐ Si apre in `process_view` e si chiude in `__call__`, con questo
#       middleware ULTIMO della catena: dentro ci sono la view (autenticazione,
#       permessi, service) e la conversione dell'errore in risposta; fuori ci
#       sono gli altri middleware, cioe' `RequestLogMiddleware` e le scritture
#       di osservabilita' dopo la risposta (§2.1 punto 3).
#       ⚠️ Le risposte in streaming producono il contenuto dopo la chiusura:
#       quella parte legge fuori dal blocco (§2.1 punto 6, api.md).
#       ⛔ Una view che DEVE scrivere in una GET lo dichiara con l'attributo
#       `scrittura_in_get = "<motivo>"`; il presidio le elenca per nome.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from django.db import connection
from django.http import HttpRequest, HttpResponse

from apps.core.db.sola_lettura import transazione_sola_lettura

logger = logging.getLogger(__name__)

METODI_DI_LETTURA = frozenset({"GET", "HEAD"})
PREFISSO_API = "/api/"
ATTRIBUTO_ECCEZIONE = "scrittura_in_get"

_BLOCCO = "_zeroerp_sola_lettura"


# Scopo: Il DB e' vietato su questa connessione? Succede SOLO nei test unitari
# (`SimpleTestCase`): Django sostituisce `connect` con un `_DatabaseFailure` che
# solleva. Li' la view e' tutta mockata e non c'e' niente da proteggere, mentre
# aprire la transazione farebbe fallire il test per una ragione che non e' sua.
# ⚠️ Il nome della classe e non `isinstance`: importare `django.test` nel
# codice di produzione per riconoscere un caso di test sarebbe peggio.
# ⛔ Non e' un'uscita per i test sul DB vero: li' la connessione e' permessa e
# la sola lettura c'e', ed e' cosi' che la suite trova le GET che scrivono.
def _connessione_vietata() -> bool:
    return type(connection.connect).__name__ == "_DatabaseFailure"


# Scopo: La classe dietro una view (DRF `cls`, Django `view_class`), o la
# funzione stessa per le view a funzione.
def classe_della_view(view_func: Callable[..., Any]) -> Any:
    return getattr(view_func, "cls", None) or getattr(view_func, "view_class", None) or view_func


# Scopo: Il motivo per cui una view scrive in una GET, se lo dichiara.
# ⛔ Un attributo vuoto o non testuale non e' una dichiarazione: la regola
# vuole il motivo scritto accanto (§2.2), e un `True` non ne ha.
def motivo_scrittura_in_get(view_func: Callable[..., Any]) -> str | None:
    motivo = getattr(classe_della_view(view_func), ATTRIBUTO_ECCEZIONE, None)
    return motivo.strip() if isinstance(motivo, str) and motivo.strip() else None


# Scopo: La richiesta va in sola lettura? Metodo di lettura, rotta delle API,
# view senza eccezione dichiarata. Una sede sola: la usa anche il presidio.
def va_in_sola_lettura(request: HttpRequest, view_func: Callable[..., Any]) -> bool:
    return (
        request.method in METODI_DI_LETTURA
        and request.path.startswith(PREFISSO_API)
        and motivo_scrittura_in_get(view_func) is None
    )


# Scopo: Il nome della view per il log: modulo e classe (o funzione).
def nome_della_view(view_func: Callable[..., Any]) -> str:
    classe = classe_della_view(view_func)
    return f"{getattr(classe, '__module__', '?')}.{getattr(classe, '__qualname__', '?')}"


class SolaLetturaMiddleware:
    """Apre la transazione di sola lettura attorno alla view di una GET/HEAD."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    # Scopo: Chiude il blocco aperto in `process_view`, dopo la view e dopo la
    # conversione dell'errore in risposta. `get_response` non solleva (Django
    # converte le eccezioni in risposta prima di tornare qui), ma il blocco si
    # chiude comunque in `finally`: una transazione lasciata aperta passerebbe
    # alla richiesta dopo, sulla stessa connessione.
    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return self.get_response(request)
        finally:
            blocco: AbstractContextManager[None] | None = request.__dict__.pop(_BLOCCO, None)
            if blocco is not None:
                blocco.__exit__(None, None, None)

    # Scopo: Apre il blocco subito prima della view.
    # ⚠️ Dentro una transazione gia' aperta la sola lettura non si puo' piu'
    # impostare (il BB rifiuta di partire). In una richiesta vera non succede:
    # nessun middleware apre una transazione e `ATOMIC_REQUESTS` e' spento. Succede
    # nei test che avvolgono il client in `transaction.atomic()`: li' si salta,
    # e il presidio che la sola lettura ci sia davvero gira fuori da una
    # transazione (`test_sola_lettura_middleware_db`).
    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., Any],
        view_args: tuple[Any, ...],
        view_kwargs: dict[str, Any],
    ) -> HttpResponse | None:
        if not va_in_sola_lettura(request, view_func):
            return None
        if _connessione_vietata():
            return None
        if connection.in_atomic_block:
            logger.debug("sola_lettura: transazione gia' aperta, salto path=%s", request.path)
            return None
        blocco = transazione_sola_lettura(chi=nome_della_view(view_func))
        blocco.__enter__()
        request.__dict__[_BLOCCO] = blocco
        return None
