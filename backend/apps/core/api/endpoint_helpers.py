from collections.abc import Callable, Mapping
from enum import StrEnum
import json
import logging
from typing import Any, cast

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.payload_validators import errore_corpo
from apps.core.api.request_parsers import parse_json_body
from apps.core.api.success_responses import success_response
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.error_manager import ErrorManager
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


# Scopo: COME e' fatta l'operazione di un endpoint in modalita' forte, cioe'
#        se una key rimasta `in_progress` si puo' riprendere (decisione di Tid
#        del 2026-10-23, brief-be-verifica-documentazione-api §I.7.2).
# ⭐ ATOMICA: l'handler e l'esito `completed` stanno nella STESSA transazione,
#    e l'operazione finisce dentro la richiesta (niente lavoro che continua in
#    un thread o in un job tenendo la key). Una key orfana vuol dire «nessun
#    commit», e oltre la soglia si riprende.
# ⭐ A_PASSI: l'operazione committa un passo alla volta (la pipeline del lotto,
#    la numerazione del lotto, il push delle commesse). Una key orfana puo'
#    coprire lavoro gia' salvato: non si riprende, resta IN_CORSO finche' scade
#    o il frontend ne genera una nuova. Niente `atomic` esterno: ne
#    cambierebbe il comportamento.
# ⚠️ ATOMICA e' il default. Un endpoint a passi che non lo dichiara non
#    rischia il doppione — il suo lavoro finisce in un `atomic` solo, e la
#    ripresa resta sicura — ma perde i commit intermedi, e se ne accorge al
#    primo errore. I quattro di oggi li presidia
#    `apps/core/tests/test_unita_di_lavoro.py`.
class UnitaDiLavoro(StrEnum):
    ATOMICA = "ATOMICA"
    A_PASSI = "A_PASSI"


# Scopo: L'endpoint a cui la key resta legata (D7): metodo e percorso, senza
#        query string. E' la stessa richiesta se e solo se e' lo stesso verbo
#        sulla stessa risorsa.
def _endpoint_della_richiesta(request: HttpRequest | Request) -> str:
    return f"{request.method} {request.path}"


# Scopo: Gestisce endpoint POST JSON con parsing, validazione, idempotency opzionale e envelope uniforme.
# ⭐ `unita_di_lavoro` conta solo in modalita' forte (`require_idempotency_key`
#    e `API_STRONG_IDEMPOTENCY_ENABLED`, vedi `UnitaDiLavoro`): l'`atomic`
#    esterno esiste per tenere insieme operazione ed esito `completed`, e senza
#    registro delle key non c'e' un esito da tenere insieme.
#    ⚠️ Per questo la suite Django, che spegne la modalita' forte, non lo
#    esercita: lo prova `apps/core/tests/db/test_idempotency_prenota_db.py`
#    sul DB vero.
def handle_post_json(
    request: HttpRequest | Request,
    *,
    handler: Callable[[dict[str, Any]], Mapping[str, Any] | list[Any]],
    require_idempotency_key: bool = False,
    unita_di_lavoro: UnitaDiLavoro = UnitaDiLavoro.ATOMICA,
) -> JsonResponse:
    # ⭐ Corpo illeggibile o non oggetto: 400 `E_VALIDATION_INPUT` nell'envelope,
    #    come le view DRF (`corpo_oggetto`) — una regola, una forma (E-6).
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return exception_to_error_response(errore_corpo(exc))

    idempotency_key = get_idempotency_key()
    request_id = get_request_id()
    idempotency_claimed = False
    try:
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
                auth_user_id=get_actor_user_id(request),
                endpoint=_endpoint_della_richiesta(request),
                ripresa_ammessa=unita_di_lavoro is UnitaDiLavoro.ATOMICA,
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

        def _esegui() -> JsonResponse:
            response = success_response(handler(payload))
            if idempotency_claimed:
                assert idempotency_key is not None
                IdempotencyStore.mark_completed(
                    idempotency_key=idempotency_key,
                    response_payload=_extract_json_payload(response),
                    request_id=request_id,
                )
            return response

        if idempotency_claimed and unita_di_lavoro is UnitaDiLavoro.ATOMICA:
            # ⭐ BE-2: operazione ed esito `completed` nella stessa transazione.
            # ⚠️ Il diario aspetta la fine dell'`atomic` (l'ordine dei due
            #    `with` e' quello): dopo un errore DB catturato la transazione
            #    e' abortita, e una riga scritta li' sparirebbe in silenzio.
            with ErrorManager.diario_dopo_la_transazione(), transaction.atomic():
                response = _esegui()
        else:
            response = _esegui()
        if idempotency_claimed:
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
    # ⭐ `mark_failed` sta FUORI dall'`atomic`, dopo il rollback: dentro, sparirebbe
    #    con l'operazione e la key resterebbe `in_progress`.
    except Exception as exc:
        if idempotency_claimed:
            assert idempotency_key is not None
            IdempotencyStore.mark_failed(idempotency_key=idempotency_key, request_id=request_id)
            logger.warning(
                "idempotency_failed_exception key=%s request_id=%s error=%s",
                idempotency_key,
                request_id,
                type(exc).__name__,
            )
        return exception_to_error_response(exc)


# Scopo: Estrae il payload JSON da request e gestisce fallback parser/errore strutturato.
def _extract_json_payload(response: JsonResponse) -> dict[str, Any]:
    return json.loads(response.content.decode("utf-8"))
