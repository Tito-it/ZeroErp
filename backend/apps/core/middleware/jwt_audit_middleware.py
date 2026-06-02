# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware Django per le request `/api/*`. Tre responsabilita:
#        1) Reset GUC PG d'identita all'INIZIO di ogni richiesta /api/
#           (process_request): lavagna pulita prima dell'auth, fail-closed.
#           Chiude il leak cross-request su connessioni persistenti.
#        2) Pre-load cache permessi Redis L2 sulla request (process_view)
#        3) Rifiuto early DISABILITATO con 403 (process_view)
#
#        NOTA: la propagazione delle GUC `app.jwt_user` /
#        `app.current_user_id` non avviene PIU' in questo middleware
#        ma nella DRF auth class JwtAuditAuthentication. Vedi guida:
#        docs/it/guide/risorse-umane-e-accessi.md sezione
#        "Propagazione identita utente al database (GUC)".
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_DISABILITATO
from apps.core.services.permissions_cache import load_user_cache
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.request_context import get_idempotency_key, get_request_id

logger = logging.getLogger(__name__)


def _json_error(code: str, message: str, status: int) -> JsonResponse:
    """Risposta errore JSON con envelope standard
    ``{error:{code,message}, meta:{request_id?, idempotency_key?}}``.

    Usato per le risposte hard-coded del middleware (DISABILITATO,
    reset GUC fallito) che NON passano dal DRF exception handler:
    centralizza l'envelope per non duplicarlo a ogni call-site.
    """
    payload: dict = {"error": {"code": code, "message": message}}
    meta: dict[str, str] = {}
    request_id = get_request_id()
    if request_id:
        meta["request_id"] = request_id
    idempotency_key = get_idempotency_key()
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=status)


class JwtAuditMiddleware(MiddlewareMixin):
    """Reset GUC d'identita, pre-load cache permessi, rifiuto DISABILITATO.

    Per ogni richiesta ``/api/`` (anche anonima):

    1. ``process_request`` azzera i 5 GUC PG d'identita (``app.jwt_user``,
       ``app.current_user_id``, ``app.current_identita_id``,
       ``app.ruolo_applicativo``, ``app.soggetto_ruolo_id``) **prima**
       dell'auth e di ogni query. Reset incondizionato (non dipende dal
       marker auth) e FAIL-CLOSED (500 se non riesce). Chiude il leak
       cross-request su connessioni persistenti (``CONN_MAX_AGE > 0`` /
       pooling): una richiesta non eredita piu' i GUC della precedente
       sulla stessa connessione. Sostituisce il vecchio reset di fine
       richiesta (best-effort, che falliva verso il leak).

    Per le richieste ``/api/`` di utenti autenticati (``process_view``):

    2. Pre-carica la cache permessi da Redis L2 su
       ``request._zeroerp_perms_cache``, riusata da
       ``ZeroERPPermission._get_cache()`` senza query aggiuntive.
    3. Rifiuta immediatamente gli utenti con ``ruolo_applicativo = DISABILITATO``
       restituendo 403, prima che la request raggiunga la view.

    **Le GUC reali NON vengono settate qui**: la propagazione e' fatta da
    ``apps.core.api.jwt_audit_authentication.JwtAuditAuthentication``
    durante ``authenticate()`` del flusso DRF, perche' a ``process_view``
    time ``request.user`` e' AnonymousUser per le request JWT (DRF
    authentication gira nel view dispatch dopo i Django middleware).
    Vedi guida ``risorse-umane-e-accessi.md`` sezione "Propagazione
    identita utente al database (GUC)".
    """

    def process_view(
        self,
        request: HttpRequest,
        view_func: object,
        view_args: tuple,
        view_kwargs: dict,
    ) -> HttpResponse | None:
        del view_func, view_args, view_kwargs
        # Solo per API: pre-load cache permessi e check DISABILITATO.
        if not request.path.startswith("/api/"):
            return None
        user = getattr(request, "user", None)
        if not (user and getattr(user, "is_authenticated", False)):
            return None

        # Scopo: Pre-carica cache permessi da Redis L2 (riusata da
        # ZeroERPPermission._get_cache senza query aggiuntive).
        if not hasattr(request, "_zeroerp_perms_cache"):
            redis_data = load_user_cache(user.id)
            request._zeroerp_perms_cache = redis_data or {}  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_loaded_from_redis = redis_data is not None  # type: ignore[attr-defined]

        # Scopo: Rifiuto early DISABILITATO con 403 strutturato.
        # Check diretto su ruolo_applicativo (GUC-first, vedi
        # PermissionResolver.get_ruolo_applicativo).
        ruolo_app = PermissionResolver.get_ruolo_applicativo(
            user, cache=request._zeroerp_perms_cache  # type: ignore[attr-defined]
        )
        if ruolo_app != RUOLO_APPLICATIVO_DISABILITATO:
            return None

        logger.warning(
            "security.user_disabilitato user_id=%s path=%s",
            user.id, request.path,
        )
        return _json_error("E_USER_DISABILITATO", "Utente disabilitato.", 403)

    # Scopo: lavagna pulita dei GUC d'identita all'INIZIO di ogni
    # richiesta `/api/`, PRIMA che la DRF auth class (JwtAuditAuthentication)
    # li ripopoli e prima di qualunque query della view.
    #
    # Perche' all'inizio e non alla fine: i GUC sono session-scoped
    # (set_config(..., is_local=false)) e con CONN_MAX_AGE>0 / pooling le
    # connessioni vengono riusate fra richieste. Un reset di FINE richiesta
    # e' best-effort (saltato se process_response non gira: eccezione a
    # valle, crash, ritorno al pool) e fallisce verso il LEAK. Il reset di
    # INIZIO garantisce che ogni richiesta parta da vuoto a prescindere da
    # com'e' finita la precedente sulla stessa connessione.
    #
    # Incondizionato: azzera anche per le richieste anonime (che NON
    # passano da set_jwt_gucs) — altrimenti erediterebbero i GUC della
    # richiesta autenticata precedente. Dopo il reset, l'auth class
    # ripopola i valori reali per gli autenticati; gli anonimi restano
    # vuoti (fail-closed lato RLS).
    #
    # FAIL-CLOSED: se il reset non riesce, la richiesta NON viene servita
    # (500). Meglio un errore che servire dati con uno scope ereditato.
    #
    # Gate `connection.connection is not None`: si resetta SOLO se esiste
    # gia' una connessione stabilita (quindi potenzialmente "sporca" di
    # GUC di una richiesta precedente con CONN_MAX_AGE>0). Una connessione
    # NUOVA ha per definizione i GUC puliti (sessione PG fresca): non c'e'
    # nulla da azzerare. Questo gate e' al tempo stesso (a) corretto — il
    # leak vive solo sulle connessioni riusate — e (b) test-safe: nei test
    # `SimpleTestCase` senza DB la connessione non e' mai aperta, quindi il
    # middleware non la tocca e non scatta DatabaseOperationForbidden. NON
    # e' un gate sull'auth: una richiesta anonima su connessione riusata
    # viene comunque ripulita (fail-closed sul leak).
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if not request.path.startswith("/api/"):
            return None
        if connection.connection is None:
            return None  # connessione fresca → GUC gia' puliti
        try:
            with connection.cursor() as cursor:
                cursor.execute(JWT_GUC_RESET_SQL)
        except DatabaseError:
            logger.error(
                "jwt_audit_middleware.guc_reset_at_start_failed path=%s",
                request.path,
                exc_info=True,
            )
            return _json_error(
                "E_GUC_RESET_FAILED",
                "Errore interno di sicurezza sessione.",
                500,
            )
        return None
