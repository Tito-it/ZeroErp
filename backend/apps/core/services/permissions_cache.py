# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cache Redis L2 per i permessi utente.
# Integra la cache per-request (L1 dict) con Redis (L2)
# per evitare query DB su ogni richiesta HTTP.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_KEY_PREFIX = "perms:user"


def _cache_key(user_id: int) -> str:
    """Scopo: Genera la chiave Redis per i permessi di un utente."""
    return f"{_KEY_PREFIX}:{user_id}"


def _ttl() -> int:
    """Scopo: Restituisce il TTL della cache permessi in secondi."""
    return getattr(settings, "PERMISSIONS_CACHE_TTL", 300)


def load_user_cache(user_id: int) -> dict[str, Any] | None:
    """Scopo: Carica la cache permessi da Redis per un utente.
    Restituisce None se non presente o in caso di errore Redis."""
    try:
        data = cache.get(_cache_key(user_id))
        if isinstance(data, dict):
            return data
    except Exception:
        logger.debug("permissions_cache: errore lettura Redis per user=%s", user_id)
    return None


def save_user_cache(user_id: int, cache_dict: dict[str, Any]) -> None:
    """Scopo: Salva la cache permessi su Redis per un utente."""
    try:
        cache.set(_cache_key(user_id), cache_dict, timeout=_ttl())
    except Exception:
        logger.debug("permissions_cache: errore scrittura Redis per user=%s", user_id)


def invalidate_user(user_id: int) -> None:
    """Scopo: Invalida la cache permessi per un singolo utente."""
    try:
        cache.delete(_cache_key(user_id))
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
    ⚠️ Nessun filtro su `attivo` o sulla veste, di proposito: la chiave di
    cache e' per `auth_user`, e invalidare una riga in piu' e' innocuo mentre
    una in meno e' il difetto (permessi stantii dopo un cambio di profilo).
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
            keys = [_cache_key(uid) for uid in user_ids]
            cache.delete_many(keys)
            logger.info(
                "permissions_cache: invalidati %d utenti per reparto uo_id=%s",
                len(user_ids),
                uo_id,
            )
    except Exception:
        logger.warning("permissions_cache: errore invalidazione reparto uo_id=%s", uo_id)


def invalidate_all() -> None:
    """Scopo: Invalida tutta la cache permessi (tutti gli utenti).
    Usa delete_pattern con il prefisso comune."""
    try:
        # django-redis supporta delete_pattern nativamente
        full_prefix = f"{settings.CACHES['default'].get('KEY_PREFIX', '')}:{_KEY_PREFIX}:*"
        cache.delete_pattern(full_prefix)
        logger.info("permissions_cache: invalidata tutta la cache permessi")
    except Exception:
        logger.warning("permissions_cache: errore invalidazione globale")
