# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware Django per le request `/api/*`. Due responsabilita:
#        1) Reset GUC PG d'identita all'INIZIO di ogni richiesta /api/
#           (process_request): lavagna pulita prima dell'auth, fail-closed.
#           Chiude il leak cross-request su connessioni persistenti.
#        2) Guard BYPASSRLS sulla connessione web (process_request).
#        ⛔ Il rifiuto dei DISABILITATO NON sta qui (ritirato il 2026-09-28,
#        analisi difetti doc API core S-2): sta nella catena di
#        `ZeroERPPermission`, l'unica sede che vede l'utente autenticato.
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
from apps.core.services.request_context import get_idempotency_key, get_request_id
from apps.core.services.system_context import connection_role_bypasses_rls

logger = logging.getLogger(__name__)

# Guard fail-open: la connessione del percorso richiesta NON deve mai essere un
# ruolo BYPASSRLS — sarebbe un `DB_USER` misconfigurato su un ruolo batch, e il
# risultato sarebbe un leak cross-tenant silenzioso. Verifica UNA volta per
# processo e memorizza: il ruolo della connessione web è COSTANTE.
# ⭐ Dal 2026-09-05 la cache è più solida di prima, non meno: il gateway che
# poteva ripuntare il `default` a un ruolo BYPASSRLS (`system_process_context`)
# è stato RITIRATO, e `test_system_context_usage_whitelist` presidia che non
# torni — pretendendo zero occorrenze invece di una whitelist. Quindi non c'è
# più nessun percorso applicativo che possa cambiare il ruolo sotto la cache.
# Resta a `False` finché il check non passa: connessione BYPASSRLS → ogni richiesta
# rifiutata (fail-closed), il deploy si rompe rumorosamente. NB: come il reset GUC,
# il check agisce sulle connessioni RIUSATE (CONN_MAX_AGE>0, default del progetto);
# è un backstop di difesa-in-profondità, non l'unica difesa (config + check statico).
_WEB_CONN_ROLE_VERIFIED = False


def _json_error(code: str, message: str, status: int) -> JsonResponse:
    """Risposta errore JSON con envelope standard
    ``{error:{code,message}, meta:{request_id?, idempotency_key?}}``.

    Usato per le risposte hard-coded del middleware (reset GUC fallito,
    connessione BYPASSRLS) che NON passano dal DRF exception handler:
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
    """Reset GUC d'identita e guard BYPASSRLS.

    Per ogni richiesta ``/api/`` (anche anonima):

    1. ``process_request`` azzera le GUC PG d'identita (l'elenco e' la tupla
       ``JWT_IDENTITY_GUCS``: non si ricopia qui) **prima**
       dell'auth e di ogni query. Reset incondizionato (non dipende dal
       marker auth) e FAIL-CLOSED (500 se non riesce). Chiude il leak
       cross-request su connessioni persistenti (``CONN_MAX_AGE > 0`` /
       pooling): una richiesta non eredita piu' i GUC della precedente
       sulla stessa connessione. Sostituisce il vecchio reset di fine
       richiesta (best-effort, che falliva verso il leak).

    ⛔ **Niente ``process_view``** (ritirato il 2026-09-28, S-2). Rifiutava i
    ``DISABILITATO`` con 403, ma a quel punto ``request.user`` e' l'utente di
    SESSIONE di Django: per un client Bearer e' ``AnonymousUser`` (l'auth DRF
    gira dopo, nel dispatch della view), quindi il ramo non scattava mai.
    Il rifiuto vero e' nella catena di ``ZeroERPPermission`` (passo del ruolo
    applicativo). Un controllo che non scatta non e' difesa in profondita':
    e' una seconda sede che sembra proteggere. ⚠️ Il modello AMMETTE una
    veste ``attivo`` col ruolo ``DISABILITATO`` (il guard di coerenza lo
    esenta): il caso esiste, ed e' la catena a coprirlo.

    ⛔ La cache permessi L2 NON si precarica qui (fino al 2026-09-24 si'): la
    sua chiave e' il contesto di sessione (identita' + emittente effettivo)
    che nasce in ``set_jwt_gucs``, cioe' DOPO questo punto. La carica una
    sede sola, ``ZeroERPPermission._get_cache()``.

    **Le GUC reali NON vengono settate qui**: la propagazione e' fatta da
    ``apps.core.api.jwt_audit_authentication.JwtAuditAuthentication``
    durante ``authenticate()`` del flusso DRF, perche' a ``process_view``
    time ``request.user`` e' AnonymousUser per le request JWT (DRF
    authentication gira nel view dispatch dopo i Django middleware).
    Vedi guida ``risorse-umane-e-accessi.md`` sezione "Propagazione
    identita utente al database (GUC)".
    """

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
            logger.exception(
                "jwt_audit_middleware.guc_reset_at_start_failed path=%s",
                request.path,
            )
            return _json_error(
                "E_GUC_RESET_FAILED",
                "Errore interno di sicurezza sessione.",
                500,
            )
        return self._guard_request_connection_not_bypassrls(request)

    # Scopo: guard fail-open (RLS Path A) — assicura che la connessione del percorso
    #        richiesta NON sia un ruolo BYPASSRLS. Controllo UNA volta per processo
    #        (il ruolo della connessione web è costante): becca un `DB_USER`
    #        misconfigurato sul ruolo batch o un misuse del gateway di sistema dentro
    #        il web. Fail-closed (500) se la connessione bypassa la RLS — meglio
    #        rifiutare che servire dati cross-tenant. Gate su connessione stabilita
    #        (test-safe come il reset GUC).
    def _guard_request_connection_not_bypassrls(
        self, request: HttpRequest,
    ) -> HttpResponse | None:
        global _WEB_CONN_ROLE_VERIFIED
        if _WEB_CONN_ROLE_VERIFIED:
            return None
        try:
            bypasses = connection_role_bypasses_rls()
        except DatabaseError:
            logger.exception(
                "jwt_audit_middleware.bypassrls_check_failed path=%s",
                request.path,
            )
            return _json_error(
                "E_DB_ROLE_UNSAFE",
                "Errore interno di sicurezza sessione.",
                500,
            )
        if bypasses:
            logger.critical(
                "security.web_connection_is_bypassrls path=%s — connessione web su "
                "ruolo BYPASSRLS, richiesta rifiutata (fail-closed)",
                request.path,
            )
            return _json_error(
                "E_DB_ROLE_UNSAFE",
                "Errore interno di sicurezza sessione.",
                500,
            )
        _WEB_CONN_ROLE_VERIFIED = True
        return None
