# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper service condivisi per la gestione componenti BoM
#        (modello unificato 2026-05-13). Funzioni pure riusate dai service
#        sorgente (preventivi/contratti/ordini/ddt) che gestiscono righe
#        composite.
#
#        NON contiene: `_load_componente_for_modification` (resta nei service
#        sorgente perche' solleva codici errore specifici dominio,
#        `E_PREV_*` vs `E_VENDITE_*`); helper SQL `_componenti_repo_mixin`
#        (gia' in apps.vendite.db.).
# ------------------------------------------------------------

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model

from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver


# Scopo: Valida e normalizza `componenti_overrides` (modello unificato).
# Forma attesa: {componente_id_uuid: prezzo_numeric}. Decimal-safe:
# scarta a monte boolean/oggetti/stringhe non numeriche che fallirebbero
# al CAST::numeric lato fn DB con un errore poco parlante.
#
# Restituisce un dict normalizzato a {str: str(Decimal)} (None/{} -> None).
# Solleva ServiceError(`error_code`) su valori invalidi (incluso Infinity/NaN).
#
# `error_code` parametrizzabile per dominio sorgente:
#   - preventivi: 'E_PREV_VALIDAZIONE'
#   - contratti/ordini/ddt: 'E_VENDITE_VALIDATION'
def normalize_componenti_overrides(
    overrides: Any,
    *,
    function_name: str,
    error_code: str = "E_VENDITE_VALIDATION",
) -> dict[str, str] | None:
    if overrides is None or overrides == {}:
        return None
    ErrorManager.require(
        isinstance(overrides, dict),
        code=error_code,
        message="componenti_overrides deve essere un oggetto JSON.",
        function_name=function_name,
    )
    assert isinstance(overrides, dict)
    normalized: dict[str, str] = {}
    for k, v in overrides.items():
        ErrorManager.require(
            v is not None and v != "",
            code=error_code,
            message=f"Prezzo override mancante per componente {k!r}.",
            function_name=function_name,
        )
        try:
            dec = Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError) as exc:
            ErrorManager.require(
                False,
                code=error_code,
                message=(
                    f"Prezzo override non valido per componente {k!r}: {v!r}."
                ),
                function_name=function_name,
            )
            raise AssertionError("unreachable") from exc
        # Defense-in-depth: `Decimal("Infinity")` e `Decimal("NaN")` superano
        # il cast ma non sono valori sensati per un prezzo.
        ErrorManager.require(
            dec.is_finite(),
            code=error_code,
            message=(
                f"Prezzo override non finito (Infinity/NaN) per componente "
                f"{k!r}: {v!r}."
            ),
            function_name=function_name,
        )
        normalized[str(k)] = format(dec, "f")
    return normalized or None


# Scopo: Valida e normalizza `componenti_attivazioni` (modello unificato).
# Forma attesa: {componente_id_uuid: bool}. Usata dai service che ammettono
# attivazione esplicita di opzionali (preventivi); altri sorgenti potrebbero
# non supportarla (contratti/ordini/ddt al momento non hanno questo flow).
# Restituisce dict normalizzato (None/{} -> None). Solleva su valori non-bool.
def normalize_componenti_attivazioni(
    attivazioni: Any,
    *,
    function_name: str,
    error_code: str = "E_VENDITE_VALIDATION",
) -> dict[str, bool] | None:
    if attivazioni is None or attivazioni == {}:
        return None
    ErrorManager.require(
        isinstance(attivazioni, dict),
        code=error_code,
        message="componenti_attivazioni deve essere un oggetto JSON.",
        function_name=function_name,
    )
    assert isinstance(attivazioni, dict)
    normalized: dict[str, bool] = {}
    for k, v in attivazioni.items():
        ErrorManager.require(
            isinstance(v, bool),
            code=error_code,
            message=(
                f"Valore attivazione non valido per componente {k!r}: "
                "atteso bool."
            ),
            function_name=function_name,
        )
        normalized[str(k)] = bool(v)
    return normalized or None


# Scopo: Best-effort lookup emittente_soggetto_ruolo_id dell'utente loggato.
# Ritorna None per admin globale (no emittenti assegnati) o utente
# inesistente, invece di sollevare. Usato dal flusso init componenti dei
# sorgenti dove l'init e' opzionale: se l'utente non ha emittente non c'e'
# modo di chiamare il resolver, ma cio' non deve bloccare la create di
# righe non composite.
def resolve_emittente_sr_id_safe(auth_user_id: int | None) -> int | None:
    if auth_user_id is None:
        return None
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        return None
    emittenti_sr = PermissionResolver.get_emittenti_sr_ids(user) or []
    if not emittenti_sr:
        return None
    return int(emittenti_sr[0])


# Scopo: Risolve l'emittente_soggetto_ruolo_id per le operazioni che
# dipendono dal contesto di una testata sorgente (preventivo/contratto/
# ordine/ddt). Precedenza: emittente esplicito sulla testata (campo
# `emittente_fiscale_id` se valorizzato) > emittente operatore loggato.
# Ritorna None se nessuna fonte: il caller decide skip silenzioso o
# sollevare.
#
# `repo_get_sr_id_by_fiscale_id`: callable che data una `emittente_fiscale_id`
# ritorna il suo `soggetto_ruolo_id` (None se non trovato). Il caller passa
# tipicamente `repo.get_emittente_sr_id_by_fiscale_id` come riferimento al
# metodo del repository sorgente.
def resolve_emittente_sr_id_for_testata(
    testata: dict[str, Any],
    auth_user_id: int | None,
    *,
    repo_get_sr_id_by_fiscale_id,
) -> int | None:
    emittente_fiscale_id = testata.get("emittente_fiscale_id")
    if emittente_fiscale_id is not None:
        sr_id = repo_get_sr_id_by_fiscale_id(int(emittente_fiscale_id))
        if sr_id is not None:
            return sr_id
    return resolve_emittente_sr_id_safe(auth_user_id)
