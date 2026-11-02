# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cache Redis L2 per i permessi utente.
# Integra la cache per-request (L1 dict) con Redis (L2)
# per evitare query DB su ogni richiesta HTTP.
#
# ⛔ La chiave NON e' l'auth_user: e' la coppia (utente, CONTESTO DI
#    SESSIONE). I valori in cache li calcolano funzioni SQL che leggono le
#    GUC della richiesta — `app.ruolo_applicativo` (deriva dall'identita', cioe'
#    dalla veste) e `app.current_emittente_id` (l'emittente attivo) — quindi
#    lo stesso utente ha risposte diverse in due vesti o in due emittenti.
#    Fino al 2026-09-24 la chiave era `perms:user:<id>`: chi cambiava
#    emittente, o entrava con un'altra veste, riceveva livelli e perimetro
#    dell'altro contesto (analisi-be-difetti-emersi-verifica-doc-api-core M-1).
#
# ⭐ Invalidazione per GENERAZIONE, non per cancellazione: le voci di un
#    utente sono tante quanti i suoi contesti, e cercarle per pattern
#    dipenderebbe dal backend (la LocMemCache non ha `delete_pattern`, e su
#    django-redis il prefisso lo aggiunge lui — S-3). Ogni voce porta le
#    generazioni (utente, globale) lette PRIMA di calcolarla; invalidare vuol
#    dire cambiare generazione, e le voci vecchie non tornano piu' valide.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_KEY_PREFIX = "perms:user"
_GEN_UTENTE_PREFIX = "perms:gen:user"
_GEN_GLOBALE = "perms:gen:all"

# Generazioni lette al caricamento: (utente, globale).
Generazioni = tuple[str, str]


# Scopo: Contesto di sessione da cui dipendono i valori in cache: l'identita'
#        (quindi la veste) e l'emittente EFFETTIVO, cioe' quello che la GUC
#        porta davvero — non il claim: un claim su un emittente disattivato
#        lascia la GUC vuota, e i valori calcolati li' sono quelli di «tutti».
def contesto_sessione(identita_id: int | str, emittente_effettivo_id: int | str | None) -> str:
    emittente = str(emittente_effettivo_id) if emittente_effettivo_id not in (None, "") else "-"
    return f"i{identita_id}:e{emittente}"


def _cache_key(user_id: int, contesto: str) -> str:
    """Scopo: Genera la chiave Redis per i permessi di un utente in un contesto."""
    return f"{_KEY_PREFIX}:{user_id}:{contesto}"


def _gen_key(user_id: int) -> str:
    """Scopo: Chiave della generazione dei permessi di un utente."""
    return f"{_GEN_UTENTE_PREFIX}:{user_id}"


def _ttl() -> int:
    """Scopo: Restituisce il TTL della cache permessi in secondi."""
    return getattr(settings, "PERMISSIONS_CACHE_TTL", 300)


def _nuova_generazione() -> str:
    """Scopo: Valore opaco di generazione (mai riusato)."""
    return uuid.uuid4().hex


# Scopo: Generazione corrente di una chiave, creandola se manca. Una
#        generazione assente non vale come «nessuna»: se valesse, una chiave
#        sfrattata farebbe tornare valide le voci scritte prima di
#        un'invalidazione. `add` non sovrascrive chi l'ha creata per primo.
#        None = la cache non la conserva (sfrattata subito, backend che non
#        memorizza): niente generazione, niente salvataggio.
def _generazione(key: str, letta: Any) -> str | None:
    if isinstance(letta, str):
        return letta
    cache.add(key, _nuova_generazione(), timeout=None)
    corrente = cache.get(key)
    return corrente if isinstance(corrente, str) else None


# Scopo: Carica la cache permessi di (utente, contesto) da Redis.
#        Ritorna i valori (o None se assenti / di una generazione superata) e
#        le generazioni correnti, da ripassare a `save_user_cache`: e' con
#        QUELLE che si salva, cosi' un'invalidazione arrivata a meta' richiesta
#        rende la voce salvata gia' scaduta. Generazioni None = Redis
#        irraggiungibile, o una generazione che la cache non conserva:
#        niente salvataggio.
def load_user_cache(
    user_id: int, contesto: str
) -> tuple[dict[str, Any] | None, Generazioni | None]:
    try:
        data_key, gen_key = _cache_key(user_id, contesto), _gen_key(user_id)
        lette = cache.get_many([data_key, gen_key, _GEN_GLOBALE])
        gen_utente = _generazione(gen_key, lette.get(gen_key))
        gen_globale = _generazione(_GEN_GLOBALE, lette.get(_GEN_GLOBALE))
        if gen_utente is None or gen_globale is None:
            return None, None
        generazioni = (gen_utente, gen_globale)
        voce = lette.get(data_key)
        if (
            isinstance(voce, dict)
            and voce.get("gen") == list(generazioni)
            and isinstance(voce.get("valori"), dict)
        ):
            return voce["valori"], generazioni
        return None, generazioni
    except Exception:
        logger.debug("permissions_cache: errore lettura Redis per user=%s", user_id)
    return None, None


def save_user_cache(
    user_id: int, contesto: str, valori: dict[str, Any], generazioni: Generazioni
) -> None:
    """Scopo: Salva la cache permessi di (utente, contesto) con le generazioni
    lette al caricamento."""
    try:
        cache.set(
            _cache_key(user_id, contesto),
            {"gen": list(generazioni), "valori": valori},
            timeout=_ttl(),
        )
    except Exception:
        logger.debug("permissions_cache: errore scrittura Redis per user=%s", user_id)


def invalidate_user(user_id: int) -> None:
    """Scopo: Invalida la cache permessi di un utente, in tutti i suoi contesti."""
    try:
        cache.set(_gen_key(user_id), _nuova_generazione(), timeout=None)
    except Exception:
        logger.warning("permissions_cache: errore invalidazione user=%s", user_id)


def invalidate_department(uo_id: int) -> None:
    """Scopo: Invalida la cache permessi per tutti gli utenti di un reparto.
    Cerca gli utenti associati al reparto e invalida ciascuno.

    Il legame reparto → utente passa dalla MADRE: `risorse_umane` (che porta
    l'UO) → `identita_digitali` per `soggetto_ruolo_id` → `auth_user_id`.
    ⛔ Fino al 2026-09-12 leggeva il model della vista col nome vecchio del
    ponte RU↔utente (`risorse_umane_auth_user` — analisi-software-per-dati-morti
    §2.1, «strato 2»): model ritirato, il DB ritira la vista.
    ⚠️ Nessun filtro su `attivo` o sulla veste, di proposito: invalidare un
    utente in piu' e' innocuo mentre uno in meno e' il difetto (permessi
    stantii dopo un cambio di profilo).
    """
    try:
        from apps.anagrafiche.models import IdentitaDigitale, RisorseUmane

        user_ids = list(
            IdentitaDigitale.objects.filter(
                soggetto_ruolo_id__in=RisorseUmane.objects.filter(
                    unita_organizzativa_id=uo_id
                ).values("soggetto_ruolo_id")
            ).values_list("auth_user_id", flat=True)
        )
        if user_ids:
            cache.set_many(
                {_gen_key(uid): _nuova_generazione() for uid in user_ids},
                timeout=None,
            )
            logger.info(
                "permissions_cache: invalidati %d utenti per reparto uo_id=%s",
                len(user_ids),
                uo_id,
            )
    except Exception:
        logger.warning("permissions_cache: errore invalidazione reparto uo_id=%s", uo_id)


def invalidate_all() -> None:
    """Scopo: Invalida tutta la cache permessi (tutti gli utenti, tutti i
    contesti) cambiando la generazione globale."""
    try:
        cache.set(_GEN_GLOBALE, _nuova_generazione(), timeout=None)
        logger.info("permissions_cache: invalidata tutta la cache permessi")
    except Exception:
        logger.warning("permissions_cache: errore invalidazione globale")
