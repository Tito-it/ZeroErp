# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo SCOPE dei job OPERATORE su `dbops.coda_lavori`: la `scope_key`
#        canonica (fonte UNICA del formato, estratta 2026-07-21 dalla
#        `_scope_key_fatturazione` di vendite, regola del 2: la stessa
#        derivazione serve a polling/liste/badge della UI code —
#        brief-be-fe-gestione-code-lavori-stampa I-1) e, dal 2026-09-15, la
#        CATTURA dello scope intero dalla richiesta web di chi accoda
#        (`scope_operatore_da_request`), estratta alla seconda occorrenza —
#        il giro di fatturazione dal cockpit e «Esegui ora» dal drawer dei
#        processi — con l'ok di Tid (piano-be-fe-avvio-manuale §3.3).
# Note: ⛔ Lo scope catturato NON e' un dettaglio di trasporto: e' cio' con cui
#        il drenatore, minuti dopo e senza token, ripropone l'identita' di chi
#        ha premuto (`operator_identity_context`, 5 GUC, RLS come nel web) ed
#        e' il token di ownership con cui la UI code dice «e' mio». Due copie
#        di questa cattura sarebbero due modi di dire chi sei, e la seconda
#        resterebbe indietro alla prima chiave nuova.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.core.db.emittente_attivo_repository import EmittenteAttivoRepository
from apps.core.services.auth_helpers import (
    extract_emittente_attivo_from_request,
    extract_identita_id_from_request,
)
from apps.core.services.coda_lavori.context import E_SCOPE_OPERATORE
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver

# Chiave dello scope "vede tutto" (whitelist emittenti None = admin globale).
SCOPE_KEY_ALL = "ALL"


# Scopo: Chiave canonica dello SCOPE emittente di un job — "ALL" per l'admin
#        globale (whitelist None), altrimenti gli emittenti autorizzati
#        ORDINATI e joinati. Ha DUE ruoli, per costruzione coerenti:
#        (1) componente-scope della chiave di BUSINESS dei job (dedup dei job
#        VIVI — stesso scope+parametri → stesso job); (2) token di OWNERSHIP
#        di polling/liste/azioni — chi condivide la STESSA scope_key condivide
#        job e visibilità. È sicuro: un operatore può ricevere via dedup solo
#        un job con la PROPRIA scope_key, quindi l'ownership scope-based non
#        allarga la visibilità oltre ciò a cui è già autorizzato.
def scope_key_da_emittenti(emittente_ids: list[int] | None) -> str:
    if emittente_ids is None:
        return SCOPE_KEY_ALL
    return ",".join(str(e) for e in sorted(emittente_ids))


# Scopo: Lo scope COMPLETO di un lavoro OPERATORE, catturato ADESSO dalla
#        richiesta di chi lo accoda: la terna dell'identita' (auth_user_id +
#        username + identita_id dal JWT), l'emittente attivo congelato, la
#        whitelist degli emittenti e la `scope_key` che ne deriva. E' il dict
#        che si passa a `CodaLavoriRepository.accoda(scope=...)`.
#
# ⭐ L'id e' quello VERO (`user.id`, anche per un superuser) — NON
#    `get_scope_user_id`, che per un superuser e' None e bloccherebbe l'admin
#    globale: qui l'identita' serve all'audit e alla RLS del worker, non allo
#    scope di una lista.
# ⛔ La TERNA e' obbligatoria e si rifiuta QUI, prima di accodare: un lavoro
#    OPERATORE senza `identita_id` nascerebbe e morirebbe un minuto dopo nel
#    drenatore (`operator_identity_context` solleva lo stesso codice). Dirlo
#    adesso a chi puo' fare qualcosa — un superuser Django senza identita'
#    OPERATORE non accoda lavori per conto proprio — e' l'unica differenza.
# ⚠️ L'emittente ATTIVO si cattura PRIMA della whitelist, ed e' un ordine che
#    conta: dal 2026-08-04 le funzioni di scope intersecano con l'emittente
#    attivo, quindi `emittente_ids` (e con esso `scope_key`) riflette gia'
#    l'impersonazione. Le due cose devono raccontare la stessa storia.
def scope_operatore_da_request(request: Any) -> dict[str, Any]:
    user = request.user
    identita_id = extract_identita_id_from_request(request)
    ErrorManager.require(
        identita_id is not None,
        code=E_SCOPE_OPERATORE,
        message="Identità operatore non risolta dal token: il lavoro non si accoda.",
        detail=f"auth_user_id={getattr(user, 'id', None)!r}",
    )
    emittente_attivo_id = extract_emittente_attivo_from_request(request)
    emittente_ids = PermissionResolver.get_emittenti_pk_ids(user)
    return {
        "auth_user_id": int(user.id),
        "username": str(user.username),
        "identita_id": identita_id,
        # Congelato all'enqueue: il worker esegue minuti dopo, senza token, e
        # senza questo valore girerebbe in modalita' globale — un giro chiesto
        # «dentro A» toccherebbe anche B, in silenzio.
        "emittente_attivo_id": emittente_attivo_id,
        "emittente_ids": emittente_ids,
        # Token di ownership del polling e delle liste: scope-based (chi
        # condivide lo scope vede il job condiviso via dedup).
        "scope_key": scope_key_da_emittenti(emittente_ids),
    }


# Scopo: Le AZIENDE in cui nasce un lavoro OPERATORE accodato da questa
#        richiesta: l'emittente attivo, se l'operatore ne ha scelto uno;
#        altrimenti (modalità globale) ognuna di quelle che potrebbe scegliere
#        nella combo di topbar. Ogni voce è la riga di
#        `EmittenteAttivoRepository.list_selezionabili`: `emittente_fiscale_id`
#        (PK), `codice`, `ragione_sociale`, `soggetto_ruolo_id`.
# ⭐ BE10 (a) di brief-db-revisione-dbops (decisione di Tid, 2026-11-07): un
#    lavoro OPERATORE nasce dentro un'azienda — la porta `fn_accoda_lavoro`
#    rifiuta lo scope senza emittente attivo (`E_CODA_LAVORO_SENZA_EMITTENTE`)
#    e un lavoro che copre più aziende non esiste. In modalità globale se ne
#    accoda uno per azienda.
# ⭐ La fonte è la COMBO, e non è un caso: «le aziende per cui posso
#    lavorare» è la stessa domanda di «le aziende che posso scegliere», e una
#    seconda risposta scritta qui potrebbe dare un'azienda che la combo non
#    offre (e che la porta rifiuterebbe come fuori perimetro).
# ⛔ Nessuna azienda (perimetro vuoto, o l'emittente attivo non è più
#    selezionabile) → `E_PERMISSION_DENIED` subito, prima di accodare: zero
#    lavori accodati con un 200 sarebbe un «fatto» che non ha fatto niente.
def aziende_della_richiesta(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    attivo = scope.get("emittente_attivo_id")
    aziende = EmittenteAttivoRepository().list_selezionabili(
        int(scope["auth_user_id"]),
        solo_id=None if attivo is None else int(attivo),
    )
    ErrorManager.require(
        bool(aziende),
        code="E_PERMISSION_DENIED",
        message=(
            "Nessuna azienda per cui accodare il lavoro: l'azienda scelta non è "
            "più nel tuo perimetro, o il perimetro è vuoto."
        ),
        detail=f"auth_user_id={scope.get('auth_user_id')!r} emittente_attivo_id={attivo!r}",
    )
    return aziende


# Scopo: Lo scope di un lavoro OPERATORE dentro UN'azienda, a partire dallo
#        scope catturato dalla richiesta: stessa terna d'identità, emittente
#        attivo = quell'azienda, whitelist = quell'azienda sola, e la
#        `scope_key` che ne deriva.
# ⭐ È la stessa forma che avrebbe catturato l'operatore SCEGLIENDO l'azienda
#    nella combo (le funzioni di scope intersecano con l'emittente attivo), ed
#    è quella del giro notturno (`accoda_giri_fatturazione`): la chiave di
#    dedup è una per (atto, azienda), qualunque sia la strada da cui arriva.
def scope_in_azienda(scope: Mapping[str, Any], emittente_fiscale_id: int) -> dict[str, Any]:
    azienda = [int(emittente_fiscale_id)]
    return {
        **scope,
        "emittente_attivo_id": azienda[0],
        "emittente_ids": azienda,
        "scope_key": scope_key_da_emittenti(azienda),
    }
