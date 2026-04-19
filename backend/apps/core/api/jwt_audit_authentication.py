# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Subclass DRF JWTAuthentication che propaga l'identita
#        utente come GUC PostgreSQL (`app.jwt_user`,
#        `app.current_user_id`) subito dopo l'autenticazione, prima
#        che il view body inizi a fare INSERT/UPDATE. E' il punto
#        corretto del flusso DRF in cui l'identita JWT e gia
#        risolta E il view body non e ancora partito → i trigger
#        DB di audit e di scope vedono le GUC durante le scritture.
#
#        Vedi guida: docs/it/guide/risorse-umane-e-accessi.md
#        sezione "Propagazione identita utente al database (GUC)".
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import DatabaseError, connection
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


# Scopo: Imposta i 5 GUC di sessione che identificano l'utente corrente
#        sulla connessione PostgreSQL. Helper riusabile sia da
#        `JwtAuditAuthentication.authenticate()` (caso standard:
#        endpoint authenticated con Bearer access token) sia dalle view
#        di auth (login/refresh) che NON passano dalla DRF
#        authentication chain ma conoscono comunque l'identita utente
#        subito dopo il successo dell'operazione.
#
#        I 5 GUC propagati (single round-trip via CTE):
#          - app.jwt_user           -> username Django
#          - app.current_user_id    -> auth_user.id
#          - app.current_identita_id-> identita_digitali.id (vuoto se orfano)
#          - app.ruolo_applicativo  -> ruolo_applicativo dell'identita attiva
#          - app.soggetto_ruolo_id  -> soggetti_ruoli.id dell'identita
#
#        Invariante "tutto o niente": i 3 GUC di identita sono popolati
#        insieme o restano vuoti tutti (fail-open documentato, i trigger
#        DB di scope/RLS trattano GUC vuoto come "nessuna identita").
#
#        Best-effort: se `set_config` fallisce a livello DB, logga e
#        prosegue. I trigger DB di audit/scope sono fail-open.
#
#        Se `request` e' fornito, marca `_zeroerp_jwt_guc_set` per il
#        reset simmetrico operato dal
#        `JwtAuditMiddleware.process_response`. Senza marker, le GUC
#        resterebbero sulla connessione fino alla chiusura.
def set_jwt_gucs(
    *,
    username: str,
    user_id: int | str,
    request: Any | None = None,
) -> None:
    try:
        with connection.cursor() as cursor:
            # Scopo: Un'unica query con CTE risolve l'identita attiva
            # e setta i 5 GUC. Se l'utente non ha identita attiva
            # (caso orfano), i 3 GUC di identita restano stringhe
            # vuote — i trigger DB leggono vuoto come "non impostato".
            cursor.execute(
                """
                WITH id_row AS (
                    SELECT id, ruolo_applicativo, soggetto_ruolo_id
                      FROM anagrafiche.identita_digitali
                     WHERE auth_user_id = %s AND attivo = true
                     LIMIT 1
                )
                SELECT
                    set_config('app.jwt_user',            %s,                         false),
                    set_config('app.current_user_id',     %s,                         false),
                    set_config('app.current_identita_id', COALESCE((SELECT id::text           FROM id_row), ''), false),
                    set_config('app.ruolo_applicativo',   COALESCE((SELECT ruolo_applicativo FROM id_row), ''), false),
                    set_config('app.soggetto_ruolo_id',   COALESCE((SELECT soggetto_ruolo_id::text FROM id_row), ''), false)
                """,
                [str(user_id), str(username), str(user_id)],
            )
    except DatabaseError:
        logger.warning(
            "jwt_audit_authentication.set_gucs_failed user_id=%s",
            user_id,
            exc_info=True,
        )
        return

    if request is not None:
        request._zeroerp_jwt_guc_set = True  # type: ignore[attr-defined]


class JwtAuditAuthentication(JWTAuthentication):
    """JWT auth class che propaga l'identita utente al DB.

    Estende `rest_framework_simplejwt.authentication.JWTAuthentication`:
    delega l'autenticazione al parent e, se l'autenticazione ha
    successo, propaga `app.jwt_user` e `app.current_user_id` come GUC
    session-scoped sulla connessione PostgreSQL corrente.

    Le GUC sono session-scoped (`set_config(..., is_local=false)`)
    perche' a `authenticate()` time il view body non ha ancora aperto
    la sua `transaction.atomic()`: un `SET LOCAL` verrebbe perso al
    COMMIT autocommit immediato. Session-scope persiste sulla
    connessione fino al reset esplicito (operato da
    `JwtAuditMiddleware.process_response`) o alla chiusura connessione
    (`CONN_MAX_AGE=0` di default chiude a fine request).

    Il flag `request._zeroerp_jwt_guc_set` viene impostato come
    "marker" per il middleware: solo se il marker e True il middleware
    eseguira il reset, evitando query inutili sulle request anonime.
    """

    # Scopo: Esegue authenticate parent e, in caso di successo,
    # propaga l'identita come GUC session-scoped.
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, _validated_token = result
        # Difensivo: il parent garantisce un User reale, ma se per
        # qualche motivo manca .id (es. mock in test che non patcha
        # questa subclass) saltiamo la propagazione.
        user_id = getattr(user, "id", None)
        if user_id is None:
            return result

        self._set_gucs(request, user, user_id)
        return result

    # Scopo: Imposta le GUC `app.jwt_user` e `app.current_user_id`
    # sulla connessione corrente. Metodo separato e mockabile dai
    # test che non vogliono toccare il DB (vedi
    # apps/core/tests/_helpers/jwt_mock.py). Delega all'helper
    # module-level `set_jwt_gucs` per riuso (login/refresh views).
    def _set_gucs(self, request, user, user_id) -> None:
        set_jwt_gucs(username=str(user), user_id=user_id, request=request)
