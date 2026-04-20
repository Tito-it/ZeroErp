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
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.services.auth_constants import JWT_CLAIM_IDENTITA_ID

logger = logging.getLogger(__name__)


E_JWT_SENZA_IDENTITA = "E_JWT_SENZA_IDENTITA"
E_IDENTITA_NON_ATTIVA = "E_IDENTITA_NON_ATTIVA"


class JwtSenzaIdentitaError(AuthenticationFailed):
    """JWT validato ma privo del claim `identita_id` (§8.3.2).

    Accade con token emessi prima del refactor multi-face (pre-§8.3.2)
    o manipolati. Il client deve fare login di nuovo. 401 per coerenza
    con le altre eccezioni di autenticazione; il codice E_* specifico
    consente al FE di distinguere dal fallimento credenziali standard.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = E_JWT_SENZA_IDENTITA
    default_detail = "Token senza identita: rigenera sessione."


class IdentitaNonAttivaError(AuthenticationFailed):
    """Il claim `identita_id` non corrisponde a identita attiva.

    Scenari: identita disattivata o scaduta dopo l'emissione del JWT,
    identita_id non appartenente all'auth_user del JWT (token
    manomesso). Richiede nuovo login.

    Rationale 401 vs 403: si usa 401 (non 403) perche' semanticamente
    la sessione e' invalida e il client deve rigenerarla facendo
    login; un 403 suggerirebbe "credenziali ok ma manca permesso",
    mentre qui il problema e' che il JWT e' diventato obsoleto.
    401 + codice E_IDENTITA_NON_ATTIVA permette al FE di distinguere
    dalla credenziale errata (E_AUTHENTICATION_FAILED).
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = E_IDENTITA_NON_ATTIVA
    default_detail = "Identita digitale non attiva: rigenera sessione."


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
#
#        Parametro `identita_id` (§8.3.4): OBBLIGATORIO post modello
#        1:N. La CTE valida esplicitamente la coppia (auth_user, identita)
#        e la usa per popolare le 3 GUC di identita. Se None, ritorna
#        subito False senza query — nel modello multi-face un auth_user
#        puo' avere N identita attive, risolvere "la prima" porterebbe
#        a escalation/downgrade silenziosi (GUC con veste errata).
#        I caller DEVONO fornire l'identita_id (dal claim JWT) o
#        gestire il False (log + procedere con GUC vuote).
#        Ritorna True se la coppia e' attiva, False altrimenti.
def set_jwt_gucs(
    *,
    username: str,
    user_id: int | str,
    identita_id: int | str | None = None,
    request: Any | None = None,
) -> bool:
    # Guard §8.3.4: modello 1:N non ammette risoluzione implicita.
    # Senza identita_id esplicito le GUC non vengono toccate.
    if identita_id is None:
        return False
    try:
        with connection.cursor() as cursor:
            # Unica query CTE: valida (user, identita) + setta i 5 GUC
            # + ritorna il count delle righe (1 se valida, 0 se revocata
            # o non appartenente a quell'auth_user).
            cursor.execute(
                """
                WITH id_row AS (
                    SELECT id, ruolo_applicativo, soggetto_ruolo_id
                      FROM anagrafiche.identita_digitali
                     WHERE id = %s AND auth_user_id = %s
                       AND attivo = true
                )
                SELECT
                    set_config('app.jwt_user',            %s,                                                     false),
                    set_config('app.current_user_id',     %s,                                                     false),
                    set_config('app.current_identita_id', COALESCE((SELECT id::text               FROM id_row), ''), false),
                    set_config('app.ruolo_applicativo',   COALESCE((SELECT ruolo_applicativo::text FROM id_row), ''), false),
                    set_config('app.soggetto_ruolo_id',   COALESCE((SELECT soggetto_ruolo_id::text FROM id_row), ''), false),
                    (SELECT COUNT(*) FROM id_row)                                                                AS identita_count
                """,
                [str(identita_id), str(user_id), str(username), str(user_id)],
            )
            row = cursor.fetchone()
            identita_trovata = bool(row) and row[-1] > 0
    except DatabaseError:
        logger.warning(
            "jwt_audit_authentication.set_gucs_failed user_id=%s",
            user_id,
            exc_info=True,
        )
        return False

    if identita_trovata and request is not None:
        request._zeroerp_jwt_guc_set = True  # type: ignore[attr-defined]
    return identita_trovata


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
    # valida il claim identita_id + popola le GUC in singola query CTE.
    # §8.3.4 multi-face: serve identita_id esplicito per discriminare
    # la "veste" del JWT (token emessi da MultiVesteTokenSerializer,
    # §8.3.2). Fail 401 specifici:
    #   - E_JWT_SENZA_IDENTITA se il claim manca (token pre-refactor)
    #   - E_IDENTITA_NON_ATTIVA se la coppia (user, identita) non e'
    #     attiva (identita revocata o token manomesso)
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        # Difensivo: il parent garantisce un User reale, ma se per
        # qualche motivo manca .id (es. mock in test che non patcha
        # questa subclass) saltiamo la propagazione.
        user_id = getattr(user, "id", None)
        if user_id is None:
            return result

        # Pattern test pre-§8.3.4: molti test mockano
        # `JWTAuthentication.authenticate` con `return_value=(Mock(), None)`
        # per bypassare l'auth chain. In produzione SimpleJWT garantisce
        # sempre un token validato; questo guard evita un AttributeError
        # su `None.get()` nei test senza toccare il flusso reale.
        if validated_token is None:
            return result

        # Claim obbligatorio post-§8.3.2. Fail subito se assente:
        # significa token vecchio stile, rigenerare sessione.
        identita_id = validated_token.get(JWT_CLAIM_IDENTITA_ID)
        if identita_id is None:
            logger.warning(
                "security.jwt_senza_identita user_id=%s", user_id
            )
            raise JwtSenzaIdentitaError()

        # Popolazione GUC + verifica identita in singola query CTE.
        # Se non trovata attiva per questa coppia (user, identita),
        # le GUC restano vuote e set_jwt_gucs ritorna False.
        identita_ok = self._set_gucs(request, user, user_id, int(identita_id))
        if not identita_ok:
            logger.warning(
                "security.identita_non_attiva user_id=%s identita_id=%s",
                user_id, identita_id,
            )
            raise IdentitaNonAttivaError()

        return result

    # Scopo: Imposta le 5 GUC sulla connessione corrente, validando la
    # coppia (auth_user, identita_id). Metodo separato e mockabile dai
    # test che non vogliono toccare il DB (vedi
    # apps/core/tests/_helpers/jwt_mock.py). Ritorna True se l'identita
    # richiesta e' attiva per quell'auth_user, False altrimenti.
    def _set_gucs(self, request, user, user_id, identita_id) -> bool:
        return set_jwt_gucs(
            username=str(user),
            user_id=user_id,
            identita_id=identita_id,
            request=request,
        )
