# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio principale dell'assistente AI.
#        Orchestrazione completa: riceve input utente, costruisce
#        prompt, chiama provider LLM, esegue tool_call in loop,
#        formula risposta e logga l'interazione.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.ai_assistant.db.ai_query_log_repository import AIQueryLogRepository
from apps.ai_assistant.providers.base import AIProvider
from apps.ai_assistant.providers.factory import get_ai_provider
from apps.ai_assistant.services.prompt_builder import build_system_prompt
from apps.ai_assistant.services.tool_registry import (
    get_tool_by_name,
    get_tools_for_user,
    is_tool_allowed_for_user,
)
from apps.ai_assistant.types import AIQueryResult
from apps.core.db.sola_lettura import transazione_sola_lettura
from apps.core.services.auth_constants import JWT_CLAIM_IDENTITA_ID
from apps.core.services.error_manager import ErrorManager
from apps.core.services.request_context import get_request_id

logger = logging.getLogger(__name__)

# Limite massimo iterazioni tool_call per singola richiesta
MAX_TOOL_ITERATIONS = 8

# Timeout complessivo per il loop tool_call (secondi)
MAX_TOOL_LOOP_TIMEOUT = 30

# Conversazioni in-memory.
# Struttura:
#   {conversation_id: {
#       "owner_user_id": int,         # auth_user.id proprietario (scope)
#       "owner_identita_id": int|None,# identita_digitali.id (scope per veste)
#       "messages": [...],
#       "last_activity": datetime,
#   }}
#
# Scope sicurezza (post-fix 23-04-2026, data leak cross-user):
#   - Lookup di una conversation_id esistente verifica owner_user_id e
#     owner_identita_id: se non combacia con l'utente corrente, il service
#     tratta la riga come "non esistente" e ne crea una nuova sotto stesso
#     UUID (impossibile lato FE visto che l'UUID e' lato server, ma defense
#     in depth). Pre-fix: chiunque conosceva l'UUID leggeva chat altrui.
_conversations: dict[str, dict[str, Any]] = {}

# Conferme pendenti: persistite in cache (django.core.cache) per durare tra i
# worker gunicorn (Redis in prod; LocMemCache in CI/test). La chiave include lo
# scope conversazione+proprietario, quindi:
#  - una conferma pendente per (conversazione, owner): un nuovo preview sovrascrive;
#  - l'isolamento sicurezza e' nella chiave (un altro owner calcola una chiave
#    diversa → non vede/annulla la conferma altrui, come il vecchio scope-match);
#  - la scadenza e' gestita dal TTL nativo della cache (niente pulizia lazy).
# Dato persistito: tool_name, params, conv_id, owner_user_id, owner_identita_id,
# confirmation_id (per l'azione frontend).

# TTL conferme pendenti (5 minuti — piu' corto delle conversazioni)
_CONFIRMATION_TTL = 300


# Scopo: Chiave cache della conferma pendente per scope (conversazione+owner).
def _pending_confirm_key(
    conversation_id: str, owner_user_id: int, owner_identita_id: int | None
) -> str:
    return f"ai:pending_confirm:{owner_user_id}:{owner_identita_id}:{conversation_id}"


# Scopo: Salva la conferma pendente in cache con TTL nativo.
def _store_pending_confirmation(
    *, conversation_id: str, owner_user_id: int, owner_identita_id: int | None,
    data: dict[str, Any],
) -> None:
    cache.set(
        _pending_confirm_key(conversation_id, owner_user_id, owner_identita_id),
        data,
        timeout=_CONFIRMATION_TTL,
    )


# Scopo: Recupera la conferma pendente per scope (None se assente/scaduta).
def _get_pending_confirmation(
    *, conversation_id: str, owner_user_id: int, owner_identita_id: int | None
) -> dict[str, Any] | None:
    return cache.get(
        _pending_confirm_key(conversation_id, owner_user_id, owner_identita_id)
    )


# Scopo: Rimuove la conferma pendente per scope.
def _delete_pending_confirmation(
    *, conversation_id: str, owner_user_id: int, owner_identita_id: int | None
) -> None:
    cache.delete(
        _pending_confirm_key(conversation_id, owner_user_id, owner_identita_id)
    )


# Scopo: estrae la coppia (owner_user_id, owner_identita_id) che definisce
#        lo scope sicurezza per conversazioni e conferme pendenti.
#        user_id viene da request.user (Django); identita_id dal claim JWT
#        validato in request.auth quando disponibile.
#        Se il claim manca (es. test che mocca auth), identita_id e' None;
#        lo scope resta ben definito ma meno granulare — l'isolamento per
#        auth_user rimane comunque enforced.
def _extract_scope(user: Any, request: Any) -> tuple[int, int | None]:
    user_id = int(getattr(user, "id", 0) or 0)
    identita_id: int | None = None
    auth = getattr(request, "auth", None) if request is not None else None
    if auth is not None:
        # auth puo' essere un Token (DRF SimpleJWT) indicizzabile per chiave
        claim: Any = None
        if hasattr(auth, "get"):
            try:
                claim = auth.get(JWT_CLAIM_IDENTITA_ID)
            except Exception:  # auth oggetto opaco
                claim = None
        elif isinstance(auth, dict):
            claim = auth.get(JWT_CLAIM_IDENTITA_ID)
        if claim is not None:
            try:
                identita_id = int(claim)
            except (TypeError, ValueError):
                identita_id = None
    return user_id, identita_id


# Scopo: Esegue una query AI completa.
#        Flusso: validazione → prompt → provider → loop tool_call → log → risposta.
#        E' il punto di ingresso unico per il service AI.
def query(
    *,
    user: Any,
    request: Any,
    message: str,
    conversation_id: str | None = None,
) -> AIQueryResult:
    start_time = time.monotonic()

    # Scope sicurezza: user + identita vincolano la proprieta' di
    # conversazione e conferme pendenti. Estratto una volta, propagato
    # a tutti gli helper.
    owner_user_id, owner_identita_id = _extract_scope(user, request)

    # Gestione conferma/annullamento operazione in scrittura (prima della validazione)
    if message.strip() == "__confirm__" and conversation_id:
        return _execute_confirmation(
            user=user, request=request, conversation_id=conversation_id,
            start_time=start_time,
            owner_user_id=owner_user_id, owner_identita_id=owner_identita_id,
        )
    if message.strip() == "__cancel__" and conversation_id:
        return _cancel_confirmation(
            conversation_id=conversation_id,
            owner_user_id=owner_user_id, owner_identita_id=owner_identita_id,
        )

    # Validazione input
    _validate_input(message)

    # Gestione conversazione con enforcement dello scope proprietario
    conv_id = conversation_id or str(uuid.uuid4())
    messages = _get_or_create_conversation(
        conv_id,
        owner_user_id=owner_user_id,
        owner_identita_id=owner_identita_id,
    )

    # Aggiungi messaggio utente
    messages.append({"role": "user", "content": message})

    # Recupera tool disponibili per questo utente
    tools = get_tools_for_user(user)

    # Costruisci system prompt
    system_prompt = build_system_prompt(user, tools)

    # Prepara catalogo tool per il provider
    tool_schemas = [t.to_tool_schema() for t in tools]

    # Chiama provider con loop tool_call
    provider = get_ai_provider()
    # Fallback allineati ai default di settings.py: claude-sonnet-4 e' ritirato
    # (15-06-2026) e 4096 troncherebbe le risposte di Opus 5, dove il thinking
    # attivo per default consuma lo stesso budget del testo.
    model = getattr(settings, "AI_MODEL", "claude-opus-5")
    max_tokens = getattr(settings, "AI_MAX_TOKENS", 16000)

    tools_used: list[str] = []
    tools_log: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    token_counter = {"input": 0, "output": 0}
    response_text: str | None = None
    error_code: str | None = None
    has_more = False

    try:
        response_text, has_more = _run_tool_loop(
            provider=provider,
            messages=messages,
            tool_schemas=tool_schemas,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            request=request,
            tools_used=tools_used,
            tools_log=tools_log,
            all_actions=all_actions,
            token_counter=token_counter,
            conversation_id=conv_id,
            owner_user_id=owner_user_id,
            owner_identita_id=owner_identita_id,
        )
    except Exception as exc:
        error_code = getattr(exc, "code", "E_AI_PROVIDER_ERROR")
        logger.exception("Errore provider AI: %s", exc)
        response_text = "Mi dispiace, si e' verificato un errore nella comunicazione con l'assistente AI."

    # Salva risposta nella conversazione
    if response_text:
        messages.append({"role": "assistant", "content": response_text})

    # Log in dbops.ai_query_log (best-effort, non blocca la risposta)
    duration_ms = int((time.monotonic() - start_time) * 1000)
    _log_query(
        user_id=user.id,
        input_text=message,
        tools_log=tools_log,
        response_text=response_text,
        duration_ms=duration_ms,
        total_input_tokens=token_counter["input"],
        total_output_tokens=token_counter["output"],
        error_code=error_code,
    )

    return AIQueryResult(
        conversation_id=conv_id,
        response=response_text or "",
        tools_used=tools_used,
        actions=all_actions,
        has_more=has_more,
    )


# Scopo: Esegue il loop tool_call fino a risposta testuale o limite iterazioni.
#        Ad ogni iterazione: chiama provider → se tool_call, esegui tool →
#        aggiungi tool_result ai messaggi → ripeti. Se risposta testuale, esci.
def _run_tool_loop(
    *,
    provider: AIProvider,
    messages: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]],
    system_prompt: str,
    model: str,
    max_tokens: int,
    request: Any,
    tools_used: list[str],
    tools_log: list[dict[str, Any]],
    all_actions: list[dict[str, Any]],
    token_counter: dict[str, int],
    conversation_id: str = "",
    owner_user_id: int = 0,
    owner_identita_id: int | None = None,
) -> tuple[str | None, bool]:
    loop_start = time.monotonic()
    for _iterazione in range(MAX_TOOL_ITERATIONS):
        # Check timeout complessivo
        if time.monotonic() - loop_start > MAX_TOOL_LOOP_TIMEOUT:
            logger.warning("Timeout loop tool_call (%ds)", MAX_TOOL_LOOP_TIMEOUT)
            return (
                "Ho raggiunto il tempo massimo per questa richiesta. "
                "Ecco i risultati parziali ottenuti finora.",
                True,
            )

        response = provider.send_message(
            messages=messages,
            tools=tool_schemas,
            system=system_prompt,
            model=model,
            max_tokens=max_tokens,
        )

        token_counter["input"] += response["usage"]["input_tokens"]
        token_counter["output"] += response["usage"]["output_tokens"]

        # Se risposta testuale (no tool_call), fine loop
        if response["stop_reason"] != "tool_use" or not response["tool_calls"]:
            return response["content"], False

        # Esegui ogni tool_call
        tool_results_content: list[dict[str, Any]] = []
        for tool_call in response["tool_calls"]:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]
            tool_id = tool_call["id"]

            tools_used.append(tool_name)

            tool_start = time.monotonic()
            tool_obj = get_tool_by_name(tool_name)

            if tool_obj is None:
                # Tool non trovato nel registro
                tool_result_content = json.dumps({
                    "error": f"Strumento '{tool_name}' non disponibile."
                })
                logger.warning("LLM ha richiesto tool non registrato: %s", tool_name)
            elif not is_tool_allowed_for_user(request.user, tool_obj):
                # Ri-check permessi a execution-time: il catalogo inviato e' gia'
                # filtrato, ma un tool_call puo' arrivare per un tool fuori scope
                # (prompt injection / errore modello) o dopo un downgrade permessi.
                # Difesa-in-profondita' coerente col filtro catalogo (stesso predicato).
                tool_result_content = json.dumps({
                    "error": f"Strumento '{tool_name}' non disponibile."
                })
                logger.warning(
                    "Tool non permesso richiesto dall'LLM: %s (user=%s)",
                    tool_name, getattr(request.user, "id", None),
                )
            elif tool_obj.requires_confirmation:
                # Tool in scrittura: preview + richiesta conferma.
                # ⭐ L'anteprima non deve scrivere niente, e lo garantisce il DB:
                #    gira in una transazione di sola lettura (§5.3 punto 3).
                try:
                    with transazione_sola_lettura(chi=f"tool:{tool_name}"):
                        preview_result = tool_obj.preview(tool_input, request)
                    confirmation_id = str(uuid.uuid4())
                    _store_pending_confirmation(
                        conversation_id=conversation_id,
                        owner_user_id=owner_user_id,
                        owner_identita_id=owner_identita_id,
                        data={
                            "tool_name": tool_name,
                            "params": tool_input,
                            "conv_id": conversation_id,
                            "owner_user_id": owner_user_id,
                            "owner_identita_id": owner_identita_id,
                            "confirmation_id": confirmation_id,
                        },
                    )
                    preview_result["requires_confirmation"] = True
                    preview_result["confirmation_id"] = confirmation_id
                    tool_result_content = json.dumps(preview_result, default=str)

                    # Aggiungi azione di conferma per il frontend
                    all_actions.append({
                        "type": "confirm",
                        "label": preview_result.get("summary", "Conferma operazione"),
                        "confirmation_id": confirmation_id,
                    })
                except Exception as exc:
                    tool_result_content = json.dumps({
                        "error": f"Errore preparazione operazione: {exc}"
                    })
                    logger.exception("Errore preview tool %s: %s", tool_name, exc)
            else:
                try:
                    # ⭐ Un tool che legge non scrive, e lo garantisce il DB:
                    #    se lo tenta (classificazione sbagliata, o un service
                    #    che scrive piu' di quanto dice) PostgreSQL lo ferma
                    #    con `25006`, anche dentro una funzione DEFINER
                    #    (brief-db-area-funzionale-assistente-ai §5.3 punto 3).
                    #    ⛔ Restano FUORI l'INSERT in `dbops.ai_query_log` e
                    #    l'esecuzione confermata di una scrittura.
                    with transazione_sola_lettura(chi=f"tool:{tool_name}"):
                        result = tool_obj.execute(tool_input, request)
                    # Prefisso centralizzato: istruisce l'LLM a non modificare i dati
                    result["_istruzione"] = (
                        "DATI REALI DAL DATABASE. Copia ESATTAMENTE questi valori "
                        "nella risposta. Non modificare codici fiscali, partite IVA, "
                        "codici pratica, date, importi o qualsiasi altro dato."
                    )
                    tool_result_content = json.dumps(result, default=str)

                    # Estrai azioni di navigazione
                    actions = tool_obj.extract_actions(result)
                    all_actions.extend(actions)
                except Exception as exc:
                    tool_result_content = json.dumps({
                        "error": f"Errore esecuzione strumento: {exc}"
                    })
                    logger.exception("Errore esecuzione tool %s: %s", tool_name, exc)

            tool_duration = int((time.monotonic() - tool_start) * 1000)
            tools_log.append({
                "name": tool_name,
                "input": tool_input,
                "duration_ms": tool_duration,
            })

            tool_results_content.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": tool_result_content,
            })

        # Aggiungi la risposta del modello (con i tool_use) ai messaggi
        assistant_content: list[dict[str, Any]] = []
        if response["content"]:
            assistant_content.append({"type": "text", "text": response["content"]})
        for tc in response["tool_calls"]:
            assistant_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["input"],
            })
        messages.append({"role": "assistant", "content": assistant_content})

        # Aggiungi i risultati dei tool come messaggio user
        messages.append({"role": "user", "content": tool_results_content})

    # Limite iterazioni raggiunto
    logger.warning("Limite iterazioni tool_call raggiunto (%d)", MAX_TOOL_ITERATIONS)
    return (
        "Ho raggiunto il limite di operazioni per questa richiesta. "
        "Ecco i risultati parziali ottenuti finora.",
        True,
    )


# Scopo: Esegue un'operazione in scrittura precedentemente confermata dall'utente.
#        Recupera i parametri salvati dalla preview, esegue il tool reale,
#        logga con flag confirmed e restituisce il risultato.
def _execute_confirmation(
    *,
    user: Any,
    request: Any,
    conversation_id: str,
    start_time: float,
    owner_user_id: int,
    owner_identita_id: int | None,
) -> AIQueryResult:
    # Recupera la conferma pendente per questa conversazione. La scadenza e' gestita
    # dal TTL della cache. Scope enforcement: la chiave include owner_user_id +
    # owner_identita_id → un chiamante con scope diverso calcola una chiave diversa e
    # la conferma resta "invisibile" (impedisce takeover di scrittura altrui).
    scope: dict[str, Any] = {
        "conversation_id": conversation_id,
        "owner_user_id": owner_user_id,
        "owner_identita_id": owner_identita_id,
    }
    pending = _get_pending_confirmation(**scope)

    if pending is None:
        return AIQueryResult(
            conversation_id=conversation_id,
            response="Nessuna operazione in attesa di conferma.",
            tools_used=[],
            actions=[],
            has_more=False,
        )

    # Recupera il tool e esegui
    tool_obj = get_tool_by_name(pending["tool_name"])
    if tool_obj is None:
        _delete_pending_confirmation(**scope)
        return AIQueryResult(
            conversation_id=conversation_id,
            response="Strumento non piu' disponibile.",
            tools_used=[],
            actions=[],
            has_more=False,
        )

    # Ri-check permessi a execution-time (chiude il TOCTOU): tra preview e conferma
    # il livello dell'operatore puo' essere cambiato (revoca/declassamento). I service
    # chiamati dai tool non rifanno il check area-level (vive nel layer view, che l'AI
    # non attraversa) → il backstop deve stare qui.
    if not is_tool_allowed_for_user(user, tool_obj):
        _delete_pending_confirmation(**scope)
        logger.warning(
            "Conferma rifiutata: permesso non piu' disponibile per tool=%s (user=%s)",
            pending["tool_name"], getattr(user, "id", None),
        )
        return AIQueryResult(
            conversation_id=conversation_id,
            response="Operazione non piu' consentita: permessi non sufficienti.",
            tools_used=[],
            actions=[],
            has_more=False,
        )

    try:
        result = tool_obj.execute(pending["params"], request)
        response_text = result.get("message", "Operazione completata con successo.")

        # Log con flag confirmed
        duration_ms = int((time.monotonic() - start_time) * 1000)
        _log_query(
            user_id=user.id,
            input_text="__confirm__",
            tools_log=[{
                "name": pending["tool_name"],
                "input": pending["params"],
                "confirmed": True,
                "duration_ms": duration_ms,
            }],
            response_text=response_text,
            duration_ms=duration_ms,
            total_input_tokens=0,
            total_output_tokens=0,
            error_code=None,
            # Scrittura confermata: audit affidabile (alert ERROR se il log fallisce).
            reliable=True,
        )

        # Rimuovi conferma pendente
        _delete_pending_confirmation(**scope)

        return AIQueryResult(
            conversation_id=conversation_id,
            response=response_text,
            tools_used=[pending["tool_name"]],
            actions=[],
            has_more=False,
        )
    except Exception as exc:
        _delete_pending_confirmation(**scope)
        logger.exception("Errore esecuzione confermata %s: %s", pending["tool_name"], exc)
        error_msg = getattr(exc, "message", str(exc))
        return AIQueryResult(
            conversation_id=conversation_id,
            response=f"Errore nell'esecuzione dell'operazione: {error_msg}",
            tools_used=[pending["tool_name"]],
            actions=[],
            has_more=False,
        )


# Scopo: Annulla una conferma pendente e pulisce la memoria.
#        Enforcement scope: annullabile solo dal proprietario originario
#        (coppia owner_user_id + owner_identita_id).
def _cancel_confirmation(
    *,
    conversation_id: str,
    owner_user_id: int,
    owner_identita_id: int | None,
) -> AIQueryResult:
    scope: dict[str, Any] = {
        "conversation_id": conversation_id,
        "owner_user_id": owner_user_id,
        "owner_identita_id": owner_identita_id,
    }
    cancelled = _get_pending_confirmation(**scope) is not None
    if cancelled:
        _delete_pending_confirmation(**scope)

    return AIQueryResult(
        conversation_id=conversation_id,
        response="Operazione annullata." if cancelled else "Nessuna operazione in attesa.",
        tools_used=[],
        actions=[],
        has_more=False,
    )


# Scopo: Validazione input utente.
def _validate_input(message: str) -> None:
    ErrorManager.require(
        bool(message and message.strip()),
        code="E_AI_QUERY_EMPTY",
        message="Il messaggio non puo' essere vuoto.",
        context={"field": "message"},
    )
    ErrorManager.require(
        len(message) <= 2000,
        code="E_AI_QUERY_TOO_LONG",
        message="Il messaggio supera la lunghezza massima di 2000 caratteri.",
        context={"field": "message", "len": len(message)},
    )


# Scopo: Recupera o crea una conversazione in-memory, enforcing dello scope
#        utente + identita. Pulizia lazy delle conversazioni scadute.
#
#        Scope sicurezza (post-fix 23-04-2026):
#        Se il conversation_id esiste ma e' di proprieta' di un altro
#        (auth_user, identita_digitali), il service si comporta come se
#        non esistesse e crea una nuova riga sotto lo stesso UUID per il
#        nuovo proprietario. Questo evita qualunque data leak cross-user
#        (compreso il caso di UUID "conosciuto" da un altro utente
#        autenticato che tenta di leggere chat altrui via API).
def _get_or_create_conversation(
    conversation_id: str,
    *,
    owner_user_id: int,
    owner_identita_id: int | None,
) -> list[dict[str, Any]]:
    ttl = getattr(settings, "AI_CONVERSATION_TTL", 900)
    now = datetime.now(timezone.utc)

    # Pulizia lazy delle conversazioni scadute
    expired = [
        cid for cid, conv in _conversations.items()
        if (now - conv["last_activity"]).total_seconds() > ttl
    ]
    for cid in expired:
        del _conversations[cid]

    existing = _conversations.get(conversation_id)
    # Scope enforcement: riga appartenente a un altro proprietario =
    # trattata come non esistente. Nessun leak verso l'utente corrente.
    if existing is not None and (
        existing.get("owner_user_id") != owner_user_id
        or existing.get("owner_identita_id") != owner_identita_id
    ):
        logger.warning(
            "ai_assistant.conversation_scope_mismatch conv_id=%s "
            "owner_user=%s owner_identita=%s requester_user=%s requester_identita=%s",
            conversation_id,
            existing.get("owner_user_id"), existing.get("owner_identita_id"),
            owner_user_id, owner_identita_id,
        )
        existing = None  # fallthrough a creazione nuova sotto stesso UUID

    if existing is not None:
        existing["last_activity"] = now
        return existing["messages"]

    messages: list[dict[str, Any]] = []
    _conversations[conversation_id] = {
        "owner_user_id": owner_user_id,
        "owner_identita_id": owner_identita_id,
        "messages": messages,
        "last_activity": now,
    }
    return messages


# Scopo: Salva log dell'interazione in dbops.ai_query_log.
#        Best-effort: non blocca la risposta in caso di errore.
def _log_query(
    *,
    user_id: int,
    input_text: str,
    tools_log: list[dict[str, Any]],
    response_text: str | None,
    duration_ms: int,
    total_input_tokens: int,
    total_output_tokens: int,
    error_code: str | None,
    reliable: bool = False,
) -> None:
    request_id = get_request_id() or str(uuid.uuid4())
    provider_name = getattr(settings, "AI_PROVIDER", "mock")
    model_name = getattr(settings, "AI_MODEL", "unknown")

    repo = AIQueryLogRepository()
    repo.save_query_log(
        request_id=request_id,
        user_id=user_id,
        input_text=input_text,
        tools_called=tools_log if tools_log else None,
        response_text=response_text,
        provider=provider_name,
        model=model_name,
        tokens_input=total_input_tokens or None,
        tokens_output=total_output_tokens or None,
        duration_ms=duration_ms,
        error_code=error_code,
        reliable=reliable,
    )


# Scopo: Svuota le conversazioni in-memory. Solo per test.
#        Le conferme pendenti vivono in cache: i test che le esercitano usano
#        override_settings(LocMemCache) + cache.clear() nel proprio setUp, per non
#        rischiare un FLUSHDB su una Redis reale da questo helper condiviso.
def clear_conversations() -> None:
    _conversations.clear()
