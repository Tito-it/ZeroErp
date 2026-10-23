from collections.abc import Callable, Mapping
import json
import logging
from typing import Any, cast

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.payload_validators import errore_corpo
from apps.core.api.request_parsers import parse_json_body
from apps.core.api.success_responses import success_response
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.idempotency_store import IdempotencyStore
from apps.core.services.request_context import get_request_id
from apps.core.services.service_errors import ServiceError
from apps.core.services.request_context import get_idempotency_key

# Helper condivisi per endpoint dominio: riducono boilerplate parsing/error handling.

logger = logging.getLogger(__name__)


# Scopo: Restituisce l'auth_user_id per il filtro scope emittente DB-first.
# Superuser Django bypassa il filtro (None); per gli altri si usa user.id.
# ⛔ Serve SOLO al PERIMETRO di una lettura: `None` vuol dire «nessun limite».
#    Non e' l'utente che agisce: per gate, audit e pratiche usa
#    `get_actor_user_id`. Passato a un gate prezzi, il `None` del superuser
#    diventa «chiamata senza utente» e il gate blocca proprio il superuser
#    (E_PRICING_OVERRIDE_NON_AUTORIZZATO su offerte e contratti, 2026-10-07).
def get_scope_user_id(request: HttpRequest | Request) -> int | None:
    user = request.user
    return None if user.is_superuser else user.id


# Scopo: Restituisce l'id dell'utente che AGISCE nella richiesta: quello che i
#        gate autorizzativi controllano (prezzi L1/L2, approvazioni), che
#        l'audit registra e che apre le pratiche. `None` solo se la richiesta
#        non e' autenticata, e per i gate vuol dire «blocca».
# ⭐ Il gemello di `get_scope_user_id`, con la semantica opposta sul
#    superuser: qui il superuser e' un utente come gli altri (il bypass lo
#    decide il gate, non la view).
def get_actor_user_id(request: HttpRequest | Request) -> int | None:
    user = request.user
    return user.id if user and user.is_authenticated else None


# Scopo: L'utente AUTENTICATO della richiesta, col tipo che il resto del codice
#        si aspetta (`User`; l'id e' un `int`). Sulle view col JWT obbligatorio
#        c'e' sempre — `ZeroERPPermission` rifiuta l'anonimo prima della view —
#        e qui quella garanzia diventa ESPLICITA: un anonimo e' un 401
#        `E_NOT_AUTHENTICATED`, mai un `None` (o un `AnonymousUser`) che arriva
#        a un service.
# ⭐ Building block del 2026-10-09 (regola del 2, ok Tid, L3 di
#    piano-be-type-checker): sostituisce `request.user` / `request.user.id`
#    letti a mano dove serve l'utente vero. Dove `None` e' un valore legittimo
#    («blocca», «nessuno») resta `get_actor_user_id`.
def utente_autenticato(request: HttpRequest | Request) -> User:
    user = request.user
    if user is None or not user.is_authenticated:
        raise NotAuthenticated()
    return cast(User, user)


# Scopo: l'id dell'utente autenticato (vedi `utente_autenticato`).
def utente_autenticato_id(request: HttpRequest | Request) -> int:
    return utente_autenticato(request).id


# Scopo: Restituisce il risorsa_umana_id dell'utente autenticato.
# Risolve dalla MADRE `anagrafiche.identita_digitali` (veste OPERATORE, attiva)
# verso `risorse_umane` (attiva) per `soggetto_ruolo_id`: la STESSA catena e
# gli STESSI filtri di `script.fn_get_uo_id_for_user`, la funzione DB che
# risponde alla domanda gemella («l'UO di questo utente»).
# ⚠️ La risposta e' DETERMINATA per struttura, non per `LIMIT 1`: al piu' una
#    identita' OPERATORE attiva per utente (`uq_identita_digitali_auth_user_
#    ruolo_attivo`) e al piu' una risorsa umana per soggetto_ruolo
#    (`uq_risorse_umane_soggetto_ruolo`). Senza il filtro `attivo` la scelta
#    fra un'identita' viva e una spenta sarebbe casuale.
# ⚠️ E' la terza sede della catena (con `fn_get_uo_id_for_user` e il profilo):
#    la forma giusta e' una `fn_get_risorsa_umana_id_for_user` gemella, e
#    questo helper un wrapper — chiesta al DB in analisi-software-per-dati-morti
#    §6. Finche' non c'e', la copia resta allineata alla sorella DB, non
#    inventata qui.
# ⛔ Fino al 2026-09-12 leggeva la vista `anagrafiche.risorse_umane_auth_user`:
#    il nome vecchio del ponte RU↔utente, che nasconde nel proprio corpo il
#    filtro OPERATORE e la proiezione di compatibilita' (analisi-software-per-
#    dati-morti §2.1, «strato 2»). Il DB la ritira: il lettore va sulla madre
#    PRIMA del DROP, o l'endpoint risponde 500 (lezione del 12-09).
# Ritorna None se l'utente non e' associato a una risorsa umana.
def get_risorsa_umana_id(request: HttpRequest | Request) -> int | None:
    user = request.user
    if not user or not user.is_authenticated:
        return None
    # Cache per-request: evita query ripetute nella stessa richiesta HTTP.
    cache_attr = "_risorsa_umana_id"
    if hasattr(request, cache_attr):
        return getattr(request, cache_attr)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ru.id
              FROM anagrafiche.identita_digitali id
              JOIN anagrafiche.risorse_umane ru
                ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
             WHERE id.auth_user_id = %s
               AND id.ruolo_applicativo = %s
               AND id.attivo = true
               AND ru.attivo = true
             LIMIT 1
            """,
            [user.id, RUOLO_APPLICATIVO_OPERATORE],
        )
        row = cursor.fetchone()
    result = int(row[0]) if row else None
    setattr(request, cache_attr, result)
    return result


# Scopo: Gestisce endpoint POST JSON con parsing, validazione, idempotency opzionale e envelope uniforme.
def handle_post_json(
    request: HttpRequest | Request,
    *,
    handler: Callable[[dict[str, Any]], Mapping[str, Any] | list[Any]],
    require_idempotency_key: bool = False,
) -> JsonResponse:
    # ⭐ Corpo illeggibile o non oggetto: 400 `E_VALIDATION_INPUT` nell'envelope,
    #    come le view DRF (`corpo_oggetto`) — una regola, una forma (E-6).
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return exception_to_error_response(errore_corpo(exc))

    try:
        idempotency_key = get_idempotency_key()
        request_id = get_request_id()
        idempotency_claimed = False
        if require_idempotency_key and not idempotency_key:
            raise ServiceError(
                code="E_IDEMPOTENCY_KEY_REQUIRED",
                message=USER_MESSAGE_FALLBACK["E_IDEMPOTENCY_KEY_REQUIRED"],
                detail="Header Idempotency-Key mancante.",
            )

        strong_idempotency_enabled = (
            require_idempotency_key
            and bool(idempotency_key)
            and getattr(settings, "API_STRONG_IDEMPOTENCY_ENABLED", False)
        )
        if strong_idempotency_enabled:
            assert idempotency_key is not None
            decision = IdempotencyStore.claim_or_replay(
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            if decision.replay_payload is not None:
                logger.info(
                    "idempotency_replay key=%s request_id=%s",
                    idempotency_key,
                    request_id,
                )
                response = JsonResponse(decision.replay_payload, status=200)
                response["X-Idempotency-Replayed"] = "1"
                return response
            if decision.in_progress:
                logger.info(
                    "idempotency_in_progress key=%s request_id=%s",
                    idempotency_key,
                    request_id,
                )
                raise ServiceError(
                    code="E_IDEMPOTENCY_IN_PROGRESS",
                    # ⭐ La frase sta nel ripiego, non qui: era ricopiata a mano
                    #    e divergeva dal catalogo a ogni revisione (D4).
                    message=USER_MESSAGE_FALLBACK["E_IDEMPOTENCY_IN_PROGRESS"],
                    detail="La stessa Idempotency-Key e` gia` in corso.",
                    retryable=True,
                )
            idempotency_claimed = True
            logger.info(
                "idempotency_first_execution key=%s request_id=%s",
                idempotency_key,
                request_id,
            )

        response_payload = handler(payload)
        response = success_response(response_payload)
        if strong_idempotency_enabled and idempotency_claimed:
            assert idempotency_key is not None
            IdempotencyStore.mark_completed(
                idempotency_key=idempotency_key,
                response_payload=_extract_json_payload(response),
                request_id=request_id,
            )
            logger.info(
                "idempotency_completed key=%s request_id=%s",
                idempotency_key,
                request_id,
            )
        return response
    # ⚠️ Un `ValueError` dell'handler passa di qui come ogni altra eccezione: il
    #    translator lo porta a 400 `E_VALIDATION_INPUT` col suo messaggio. Fino
    #    al 2026-10-07 aveva un ramo suo che rispondeva `{"error":
    #    "invalid_payload"}` e buttava codice e messaggio (E-6).
    except Exception as exc:
        if idempotency_claimed and idempotency_key and getattr(
            settings,
            "API_STRONG_IDEMPOTENCY_ENABLED",
            False,
        ):
            IdempotencyStore.mark_failed(idempotency_key=idempotency_key, request_id=request_id)
            logger.warning(
                "idempotency_failed_exception key=%s request_id=%s error=%s",
                idempotency_key,
                request_id,
                type(exc).__name__,
            )
        return exception_to_error_response(exc)


# Scopo: Handler standard PATCH di dettaglio: parsing/envelope via handle_post_json
#        + delega a update_fn(pk, payload). Centralizza il pattern ripetuto nelle
#        view detail (lambda p: Service().update_X(pk, p)).
def handle_detail_patch(
    request: HttpRequest | Request,
    update_fn: Callable[[int, dict[str, Any]], Mapping[str, Any] | list[Any]],
    pk: int,
    *,
    require_idempotency_key: bool = False,
) -> JsonResponse:
    return handle_post_json(
        request,
        handler=lambda payload: update_fn(pk, payload),
        require_idempotency_key=require_idempotency_key,
    )


# Scopo: Estrae il payload JSON da request e gestisce fallback parser/errore strutturato.
def _extract_json_payload(response: JsonResponse) -> dict[str, Any]:
    return json.loads(response.content.decode("utf-8"))
