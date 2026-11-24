# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione contesto richiesta.
# ------------------------------------------------------------


from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar

# Contesto richiesta API (request_id/idempotency_key) accessibile nei layer core.

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_idempotency_key_var: ContextVar[str | None] = ContextVar("idempotency_key", default=None)
# L'ordinamento di partenza di una lista configurabile
# (`apps.core.services.ordinamento_di_partenza`), in DUE tempi:
#   - PROPOSTO: la base view l'ha messo nella query di una richiesta che non
#     ne portava uno;
#   - APPLICATO: chi risolve la chiave nella whitelist del repository
#     (`apps.core.db._helpers.colonna_ordinamento`) l'ha accettato. Solo
#     questo va nella risposta, `meta.ordinamento`.
# ⭐ Perche' due: proporre non e' applicare. Una lista che ordina nel browser
#    non risolve nessuna chiave, e una chiave fuori whitelist il repository la
#    rifiuta: in entrambi i casi la risposta direbbe un ordinamento che i dati
#    non hanno (`/verifica` di brief-db-revisione-ui, 2026-11-22).
_ordinamento_proposto_var: ContextVar[dict[str, str] | None] = ContextVar(
    "ordinamento_proposto", default=None,
)
_ordinamento_applicato_var: ContextVar[dict[str, str] | None] = ContextVar(
    "ordinamento_applicato", default=None,
)
# La misura di partenza di una lista configurabile, quando la richiesta non
# porta `limit` (BE10 di brief-db-revisione-ui, 2026-11-22): la base view
# ci mette la LETTURA, non il numero (`applica_misura_di_partenza`), e
# `pagina_da_query`, l'unico lettore di `limit`, la chiama solo se gli serve.
# Un dettaglio o una scrittura della stessa view non pagano la query.
_misura_di_partenza_var: ContextVar[Callable[[], int] | None] = ContextVar(
    "misura_di_partenza", default=None,
)
# Le colonne della lista della richiesta il cui VUOTO si ordina come il MASSIMO
# (`ui.lista_colonna.vuoto_ordinato_come_massimo`,
# brief-db-lista-colonna-vuoto-in-ordine): la base view ci mette la LETTURA
# (`applica_vuoti_come_massimo`), come per la misura, e il BB dell'ordinamento
# (`apps.core.db._helpers.sql_order_direction_lista`) la chiama solo quando
# risolve una colonna. Una richiesta che non ordina non paga la query.
_vuoti_come_massimo_var: ContextVar[Callable[[], frozenset[str]] | None] = ContextVar(
    "vuoti_come_massimo", default=None,
)


# Scopo: il rifiuto della chiave PROPOSTA dalla base view (non chiesta dal
#        client): la chiave sta fuori dalla whitelist del repository.
# ⭐ E' un `ValueError("order_by_invalid")` come ogni chiave fuori whitelist,
#    quindi fuori da una `DomainAPIView` resta il 400 di sempre. La base view
#    lo intercetta e rilegge la lista SENZA la proposta
#    (`DomainAPIView.handle_exception`): l'operatore non ha chiesto niente, e
#    un errore di configurazione del catalogo non gli chiude la lista.
class OrdinamentoPropostoRifiutato(ValueError):
    pass


# Scopo: Aggiorna `request_context` con i valori richiesti dal flusso corrente.
def set_request_context(*, request_id: str | None, idempotency_key: str | None) -> None:
    _request_id_var.set(request_id)
    _idempotency_key_var.set(idempotency_key)
    # ⚠️ Anche all'APERTURA, non solo alla chiusura: un worker riusa il suo
    #    thread, e un ordinamento rimasto dalla richiesta prima finirebbe nel
    #    `meta` di una risposta che non l'ha applicato.
    _ordinamento_proposto_var.set(None)
    _ordinamento_applicato_var.set(None)
    _misura_di_partenza_var.set(None)
    _vuoti_come_massimo_var.set(None)


# Scopo: Gestisce `clear_request_context` nel flusso applicativo del modulo.
def clear_request_context() -> None:
    set_request_context(request_id=None, idempotency_key=None)


# Scopo: registra l'ordinamento PROPOSTO alla richiesta corrente (`None` lo
#        ritira); l'applicato riparte da zero.
def proponi_ordinamento(ordinamento: dict[str, str] | None) -> None:
    _ordinamento_proposto_var.set(ordinamento)
    _ordinamento_applicato_var.set(None)


# Scopo: la chiave `order_by` e' quella proposta dalla base view?
def e_chiave_proposta(chiave: str) -> bool:
    proposto = _ordinamento_proposto_var.get()
    return proposto is not None and proposto.get("order_by") == chiave


# Scopo: il repository ha accettato la chiave proposta: da qui la risposta lo
#        dice in `meta.ordinamento`.
def conferma_ordinamento_proposto() -> None:
    _ordinamento_applicato_var.set(_ordinamento_proposto_var.get())


# Scopo: fissa l'ordinamento applicato (i test che simulano una richiesta).
def set_ordinamento_applicato(ordinamento: dict[str, str] | None) -> None:
    _ordinamento_applicato_var.set(ordinamento)


# Scopo: l'ordinamento di partenza APPLICATO alla richiesta corrente, o `None`.
def get_ordinamento_applicato() -> dict[str, str] | None:
    return _ordinamento_applicato_var.get()


# Scopo: registra la LETTURA della misura di partenza della richiesta corrente
#        (`None` la toglie).
def imposta_misura_di_partenza(lettura: Callable[[], int] | None) -> None:
    _misura_di_partenza_var.set(lettura)


# Scopo: la misura di partenza della richiesta corrente, letta (dal DB) alla
#        prima domanda, o `None` se la richiesta non ne ha una (non e' di una
#        lista configurabile, o porta `limit`).
def get_misura_di_partenza() -> int | None:
    lettura = _misura_di_partenza_var.get()
    if lettura is None:
        return None
    misura = lettura()
    # Letta una volta: la seconda domanda della stessa richiesta non rilegge.
    _misura_di_partenza_var.set(lambda: misura)
    return misura


# Scopo: registra la LETTURA delle colonne «vuoto come il massimo» della lista
#        della richiesta corrente (`None` la toglie).
def imposta_vuoti_come_massimo(lettura: Callable[[], frozenset[str]] | None) -> None:
    _vuoti_come_massimo_var.set(lettura)


# Scopo: la colonna `campo_sorgente` della lista della richiesta corrente
#        ordina il vuoto come il MASSIMO? `False` fuori da una lista di
#        catalogo (nessuna lettura registrata): vale la regola generale.
# ⚠️ Letta una volta per richiesta, alla prima domanda.
def vuoto_come_massimo(campo_sorgente: str) -> bool:
    lettura = _vuoti_come_massimo_var.get()
    if lettura is None:
        return False
    colonne = lettura()
    _vuoti_come_massimo_var.set(lambda: colonne)
    return campo_sorgente in colonne


# Scopo: Recupera `request_id` dal contesto applicativo o dal database.
def get_request_id() -> str | None:
    return _request_id_var.get()


# Scopo: Recupera `idempotency_key` dal contesto applicativo o dal database.
def get_idempotency_key() -> str | None:
    return _idempotency_key_var.get()


# --------------- HTTP request helpers ---------------

import ipaddress
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest

from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.service_errors import ServiceError


# Scopo: Estrae l'IP del client dalla request, fidandosi solo dei proxy dichiarati.
# ⭐ E' l'UNICA sede della regola «quale hop e' fidato» (audit, log richieste,
# throttle, freno del login): `settings.TRUSTED_PROXY_COUNT` = N.
#   - N = 0 → `REMOTE_ADDR`; `X-Forwarded-For` ignorato (lo scrive il client);
#   - N > 0 → l'N-esimo valore di `X-Forwarded-For` DA DESTRA: ogni proxy
#     (Nginx: `$proxy_add_x_forwarded_for`) accoda l'indirizzo da cui riceve,
#     quindi solo gli ultimi N valori sono stati scritti da un proxy fidato.
#     ⛔ Mai il primo: e' quello che il client dichiara, e lo cambia a piacere.
# Ritorna una stringa valida per `inet`, oppure None se l'IP non si ricava
# (header assente o con meno di N valori — la richiesta non e' passata dalla
# catena dichiarata —, valore malformato). None non si sostituisce con un
# ripiego: chi ne fa una chiave di sicurezza deve rifiutare, non indovinare.
def get_client_ip(request: HttpRequest) -> str | None:
    proxy_fidati = settings.TRUSTED_PROXY_COUNT
    if proxy_fidati == 0:
        return _normalizza_ip(request.META.get("REMOTE_ADDR"))
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if not xff:
        return None
    valori = xff.split(",")
    if len(valori) < proxy_fidati:
        return None
    return _normalizza_ip(valori[-proxy_fidati])


# Scopo: La `HttpRequest` di Django sotto la `Request` di DRF (o la richiesta
#        stessa, se e' gia' di Django): per i BB che leggono `META` e `path`
#        e per chi li chiama. ⭐ Regola del 2 (2026-10-02): era scritto a mano
#        in dieci view.
def richiesta_django(request: Any) -> HttpRequest:
    return getattr(request, "_request", request)


# Scopo: Il `sid` (la sessione) del JWT della richiesta corrente; None se la
#        richiesta non porta un token (una `HttpRequest` di Django, un test).
#        ⭐ Regola del 2 (2026-10-03): era `_get_current_sid` di
#        `sessioni_view`; il secondo consumatore e' il freno della password
#        dentro una sessione, che chiude QUELLA sessione.
def sid_corrente(request: Any) -> str | None:
    auth = getattr(request, "auth", None)
    return str(auth.get(JWT_CLAIM_SID, "")) if auth else None


# Scopo: La provenienza di una richiesta di autenticazione, o il rifiuto:
#        la provenienza e' la chiave del freno sulla credenziale, e senza il
#        freno non si applica (fail-closed). Causa tipica del rifiuto: la
#        richiesta non e' passata dalla catena di proxy dichiarata
#        (DJANGO_TRUSTED_PROXY_COUNT). Accetta la `Request` di DRF o la
#        `HttpRequest` di Django.
#        ⭐ Regola del 2: login, secondo passo e self-service del secondo
#        fattore. Fino al 2026-10-02 il BB dava il solo errore e la lettura
#        era copiata nei tre chiamanti: ora e' una.
def provenienza_obbligatoria(request: Any) -> str:
    django_request = richiesta_django(request)
    provenienza = get_client_ip(django_request)
    if provenienza is None:
        raise _errore_provenienza_assente(django_request)
    return provenienza


# Scopo: Il rifiuto senza provenienza; il log di sicurezza lo scrive qui.
def _errore_provenienza_assente(request: HttpRequest) -> ServiceError:
    logging.getLogger("security").error(
        "security.provenienza_assente path=%s remote_addr=%s xff=%s",
        request.path,
        request.META.get("REMOTE_ADDR"),
        request.META.get("HTTP_X_FORWARDED_FOR"),
    )
    return ServiceError(
        code="E_AUTH_CHIAMATA_NON_VALIDA",
        message="Chiamata non valida: provenienza assente.",
        detail="IP del chiamante non ricavabile dalla catena di proxy dichiarata.",
    )


# Scopo: Valida un indirizzo IP (v4/v6) e lo riporta in forma canonica; None se non lo e'.
def _normalizza_ip(valore: str | None) -> str | None:
    if not valore:
        return None
    try:
        return str(ipaddress.ip_address(valore.strip()))
    except ValueError:
        return None


# Scopo: Estrae lo User-Agent dalla request, troncato a 500 caratteri.
def get_user_agent(request: HttpRequest) -> str | None:
    ua = request.META.get("HTTP_USER_AGENT")
    return ua[:500] if ua else None
