# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper di dominio `documenti` per autenticazione utente +
#        risoluzione/verifica scope `emittente_fiscale`. Estratti dai
#        service Tranche E/G/I che duplicavano la stessa logica
#        (auth check + `PermissionResolver.get_emittenti_pk_ids` + verifica
#        appartenenza id alla whitelist). Tutti gli errori sollevano
#        `E_DOCUMENTI_VALIDATION` per coerenza con il resto del dominio
#        (no 403/404 leak: l'utente non sa se l'id non esiste o e' fuori
#        scope, evitiamo enumeration).
# ------------------------------------------------------------

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver

E_VALIDATION = "E_DOCUMENTI_VALIDATION"


# Scopo: Solleva `E_DOCUMENTI_VALIDATION` se l'utente non e' autenticato.
#        Usato da tutti i service di scrittura/generazione: il livello API
#        applica gia' JWT, ma il guard service-side e' difesa in profondita'
#        (es. service invocati da pipeline interne).
def guard_user_authenticated(
    user: AbstractBaseUser | AnonymousUser | None,
) -> None:
    if user is None or not getattr(user, "is_authenticated", False):
        ErrorManager.raise_error(
            code=E_VALIDATION,
            message="Utente non autenticato.",
        )


# Scopo: Risolve la whitelist degli emittenti autorizzati per l'utente.
#        Admin globale + superuser -> None (vede tutto). Operatore -> lista
#        di id (eventualmente vuota = nessun risultato).
#        Wrapper esplicito per consentire ai chiamanti di cachare il valore
#        in una sola invocazione end-to-end (Tranche I evita 2 round-trip).
def resolve_emittente_scope(
    user: AbstractBaseUser | AnonymousUser,
) -> list[int] | None:
    return PermissionResolver.get_emittenti_pk_ids(user)


# Scopo: Verifica `emittente_fiscale_id` rispetto allo scope precaricato.
#        Admin globale (`scope=None`) passa qualunque id valido (la FK DB
#        blocca id inesistenti). Operatore: id deve essere nella whitelist;
#        altrimenti `E_DOCUMENTI_VALIDATION` (no 403/404 leak).
def guard_emittente_in_scope(
    scope: list[int] | None,
    emittente_fiscale_id: int,
) -> None:
    if scope is None:
        return
    if emittente_fiscale_id not in scope:
        ErrorManager.raise_error(
            code=E_VALIDATION,
            message="emittente_fiscale_id non valido o non accessibile.",
            detail=f"emittente_fiscale_id={emittente_fiscale_id}",
        )


# Scopo: Composizione end-to-end auth + resolve scope + verifica id. Comodo
#        quando il chiamante non ha bisogno di riusare lo scope (un solo
#        check in tutto il flusso). Per chiamanti che fanno piu' di un
#        check (es. orchestrator generazione documenti) usare le 3 utility
#        separate cachando il valore di `resolve_emittente_scope`.
def guard_emittente_in_scope_for_user(
    user: AbstractBaseUser | AnonymousUser | None,
    emittente_fiscale_id: int,
) -> None:
    guard_user_authenticated(user)
    assert user is not None
    guard_emittente_in_scope(
        resolve_emittente_scope(user), emittente_fiscale_id,
    )
