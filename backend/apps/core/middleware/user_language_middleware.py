# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware Django che propaga la lingua preferita del client
#        come GUC PostgreSQL `myapp.user_language`. La GUC e` letta da
#        `script.fn_get_messaggio` e `script.fn_log_and_raise_error` per
#        selezionare la lingua dei messaggi di errore DB (i18n).
#
#        Sorgente: header HTTP standard `Accept-Language` inviato dal
#        client (vue-i18n). Il primo codice ISO-2 supportato vince;
#        fallback a `it` se header assente o lingua non supportata.
#
#        La GUC e` session-scoped (`set_config(..., is_local=false)`)
#        per coerenza con le 5 GUC `app.*` propagate da
#        `JwtAuditAuthentication`. Reset simmetrico in process_response
#        difende da leak fra request in scenari pgbouncer transaction-mode
#        o `CONN_MAX_AGE > 0`.
#
#        Nota prefisso: la GUC usa il prefisso legacy `myapp.*`, non il
#        piu` recente `app.*`. Il DB storicamente legge `myapp.user_language`
#        in `fn_log_and_raise_error` / `fn_get_messaggio`; allineare in
#        futuro richiederebbe un rename coordinato DB+BE.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Scopo: Import tollerante di DatabaseOperationForbidden, eccezione raised
#        dall'harness Django test quando un SimpleTestCase tenta di aprire
#        una connessione DB (databases={} per isolation). Fuori dal contesto
#        test il nome puntera' a un placeholder mai raised. Coerente con la
#        filosofia best-effort del middleware: non bloccare la request.
try:
    # ⚠️ Il nome esiste (Django 6.1, `django/test/testcases.py`) ma gli stub non
    #    lo dichiarano: l'ignore e' per lo stub, non per il codice.
    from django.test.testcases import DatabaseOperationForbidden  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    class DatabaseOperationForbidden(Exception):  # type: ignore[no-redef]
        pass

logger = logging.getLogger(__name__)


# Scopo: Lingue ISO-2 attualmente supportate dal DB per i messaggi errore.
#        Allineare con le righe presenti in `config.lingue` (attivo=true)
#        e con le traduzioni popolate in `config.messaggi_errore`.
#        Tuple immutabile: estendere qui + seed DB per nuove lingue.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("it", "en")

# Scopo: Lingua di default quando header assente o lingua client non supportata.
#        Coerente con il default di `config.messaggi_errore.lingua` ('it')
#        e con il fallback hardcoded in `fn_get_messaggio`.
DEFAULT_LANGUAGE: str = "it"

# Scopo: Nome della GUC PostgreSQL letta dalle funzioni i18n dominio.
GUC_NAME: str = "myapp.user_language"


class UserLanguageMiddleware(MiddlewareMixin):
    """Propaga `Accept-Language` client come GUC `myapp.user_language`.

    Attivo solo su richieste ``/api/``: le altre (admin, static) non
    invocano le funzioni DB i18n e non giustificano il round-trip.

    Marker ``request._zeroerp_user_language_set`` abilita il reset
    simmetrico in ``process_response``.
    """

    # Scopo: Imposta la GUC sulla connessione corrente PRIMA che la view
    #        (o la DRF auth chain) interroghi il DB. Best-effort: se il
    #        DB e` irraggiungibile il middleware non blocca la request.
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if not request.path.startswith("/api/"):
            return None
        language = self._resolve_language(request)
        try:
            with connection.cursor() as cursor:
                # set_config con is_local=false: session-scoped, persiste
                # sulla connessione fino a reset o chiusura. Coerente con
                # il pattern di JwtAuditAuthentication.set_jwt_gucs.
                cursor.execute(
                    "SELECT set_config(%s, %s, false)",
                    [GUC_NAME, language],
                )
            # Marcatore DINAMICO sulla request (lo rilegge `process_response`).
            # ⚠️ Fino al 2026-10-09 qui c'era un `# type: ignore` su una riga
            #    propria, cioe' su nessuna istruzione: non ignorava niente.
            setattr(request, "_zeroerp_user_language_set", True)  # noqa: B010 — attributo dinamico: assegnato col punto, mypy lo rifiuta (il tipo non lo dichiara)
        except (DatabaseError, DatabaseOperationForbidden):
            logger.warning(
                "user_language_middleware.set_failed lang=%s path=%s",
                language, request.path, exc_info=True,
            )
        return None

    # Scopo: Reset simmetrico. Difende da leak in scenari connection
    #        pooling esterno (pgbouncer transaction-mode) dove la stessa
    #        connessione serve request di utenti diversi.
    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        if not getattr(request, "_zeroerp_user_language_set", False):
            return response
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config(%s, '', false)",
                    [GUC_NAME],
                )
        except (DatabaseError, DatabaseOperationForbidden):
            logger.warning(
                "user_language_middleware.reset_failed", exc_info=True
            )
        return response

    # Scopo: Parse header HTTP `Accept-Language` secondo RFC 7231 sintassi
    #        semplificata. Prende il primo token con codice base (ISO-2)
    #        presente nella whitelist; ignora i q-values (ordine gia`
    #        secondo preferenza dichiarata dal client).
    #        Esempi:
    #          "en-US,en;q=0.9,it;q=0.8" -> "en"
    #          "it-IT"                   -> "it"
    #          "fr-FR,fr;q=0.9"          -> "it" (fallback, fr non supportata)
    #          ""                        -> "it" (fallback)
    @staticmethod
    def _resolve_language(request: HttpRequest) -> str:
        raw = request.META.get("HTTP_ACCEPT_LANGUAGE", "") or ""
        if not raw:
            return DEFAULT_LANGUAGE
        for token in raw.split(","):
            # Token forma: "en-US;q=0.9" -> prendi prima di ";" e lowercase
            code = token.strip().split(";", 1)[0].strip().lower()
            if not code:
                continue
            # Normalizza "en-us" -> "en"
            base = code.split("-", 1)[0]
            if base in SUPPORTED_LANGUAGES:
                return base
        return DEFAULT_LANGUAGE
