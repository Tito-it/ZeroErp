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

from collections.abc import Mapping

from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.services._pricing_gate_helpers import (
    ORIGINE_PREZZO_MANUALE,
    check_permesso_override_prezzo,
)


# Scopo: il contratto dell'OPERATORE sulla PATCH di un componente BoM, uguale
#        per i cinque documenti (preventivi, contratti, offerte, ordini, ddt).
#        E' cio' che il client puo' mandare, NON cio' che il repository sa
#        scrivere (`COMPONENTE_UPDATE_ALLOWED` del mixin, che e' piu' largo).
#
# ⛔ La differenza fra i due insiemi e' il punto. Fino al 2026-09-26 preventivi,
#    contratti e offerte validavano il payload del client contro la whitelist
#    del REPOSITORY, che contiene anche `stato_approvazione_prezzo` e
#    `pratica_approvazione_prezzo_id`: un operatore poteva mandare
#    `{"stato_approvazione_prezzo": "APPROVED"}` su un componente PENDING e
#    approvarsi da solo un prezzo fuori policy (il guard DB ammette la
#    transizione PENDING->APPROVED quando cambia solo lo stato). Quei due
#    campi li scrive SOLO il workflow L3 (`approvazioni_prezzo_service`).
#
# ⛔ `origine_prezzo` NON arriva dal client: un prezzo scritto dall'operatore
#    e' `MANUALE` per definizione, e lo dice il server. Accettarlo dal client
#    permetteva di dichiarare «LISTINO» un prezzo scritto a mano. Negli ordini
#    e nei DDT, inoltre, il filtro locale lo scartava in silenzio: l'origine
#    manuale non veniva mai scritta.
COMPONENTE_PATCH_OPERATORE: frozenset[str] = frozenset({
    "prezzo_unitario",
    "attivo",
    "meta",
})


# Scopo: valida il payload della PATCH contro `COMPONENTE_PATCH_OPERATORE`
#        (400 con `error_code` del dominio sulle chiavi estranee), normalizza
#        le stringhe vuote a None e deriva `origine_prezzo` dal prezzo: un
#        prezzo scritto -> `MANUALE`; un prezzo tolto (solo i DDT lo ammettono,
#        prezzo e origine sono facoltativi insieme) -> origine NULL.
#        Un payload senza campi e' un 400 (BB `require_campi_da_aggiornare`).
# ⛔ Fino al 2026-10-14 il payload vuoto lo giudicava ogni documento a modo
#    suo, e DOPO la scrittura: ordini e DDT rispondevano «aggiornato» senza
#    aver scritto niente, il preventivo 404 su un componente che esiste,
#    contratto e offerta 400. Ora lo dice questo BB, uguale per i cinque.
# ⛔ Un prezzo SCRITTO (non nullo) e' un prezzo a mano, e passa dal gate L1
#    (`prezzo_override_manuale`), lo stesso della nascita del componente
#    (`validate_componenti_overrides_authorization`) e della riga. Fino al
#    2026-10-20 la PATCH non lo chiedeva in nessuno dei cinque documenti: lo
#    faceva solo il pannello del frontend, spegnendo la casella, e chiamando
#    l'API un operatore senza permesso scriveva il prezzo. Togliere il prezzo
#    (`null`, si torna al suggerito) non lo chiede, come alla nascita.
#    `auth_user_id` e' obbligatorio apposta: un consumatore nuovo non puo'
#    dimenticarlo.
def dati_patch_componente(
    payload: dict[str, Any],
    *,
    auth_user_id: int | None,
    function_name: str,
    error_code: str = "E_VENDITE_VALIDATION",
) -> dict[str, Any]:
    validator = PayloadValidator(validation_code=error_code)
    validator.validate_allowed_keys(
        payload, allowed=COMPONENTE_PATCH_OPERATORE,
        message="Payload componente non valido.",
        function_name=function_name,
    )
    data = {k: empty_to_none(v) for k, v in payload.items()}
    validator.require_campi_da_aggiornare(
        data, message="Nessun campo aggiornabile sul componente.",
        function_name=function_name,
    )
    if "prezzo_unitario" in data:
        if data["prezzo_unitario"] is not None:
            check_permesso_override_prezzo(auth_user_id, function_name=function_name)
        data["origine_prezzo"] = (
            ORIGINE_PREZZO_MANUALE if data["prezzo_unitario"] is not None else None
        )
    return data


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
            ErrorManager.raise_error(
                code=error_code,
                message=(
                    f"Prezzo override non valido per componente {k!r}: {v!r}."
                ),
                function_name=function_name,
                cause=exc,
            )
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
    testata: Mapping[str, Any],
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
