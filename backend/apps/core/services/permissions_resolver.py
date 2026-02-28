# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Risolutore centrale permessi ZeroErp.
# Implementa la catena di risoluzione:
#   ruolo_sistema -> override oggetto -> override area -> profilo reparto -> BLOCCATO.
# Ogni metodo accetta un dict `cache` opzionale per evitare query duplicate
# nella stessa richiesta HTTP.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.utils import timezone


# Mapping livello -> set di azioni CRUD consentite.
LIVELLO_MAP: dict[str, frozenset[str]] = {
    "TUTTO": frozenset({"view", "add", "change", "delete"}),
    "LETTURA": frozenset({"view"}),
    "BLOCCATO": frozenset(),
}


def _today_filter() -> Q:
    """Scopo: Restituisce il filtro Q per validita' temporale override."""
    today = timezone.now().date()
    return (
        (Q(valido_dal__isnull=True) | Q(valido_dal__lte=today))
        & (Q(valido_al__isnull=True) | Q(valido_al__gte=today))
    )


class PermissionResolver:
    """Risolve il livello di accesso effettivo per un utente ZeroErp."""

    # ── Metodi pubblici ────────────────────────────────────

    @classmethod
    def get_ruolo_sistema(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> str | None:
        """Scopo: Restituisce il ruolo_sistema dell'utente dalla tabella ponte.
        Ritorna None se l'utente non ha un record in risorse_umane_auth_user."""
        if cache is not None and "ruolo_sistema" in cache:
            return cache["ruolo_sistema"]

        from apps.anagrafiche.models import RisorseUmaneAuthUser

        try:
            bridge = RisorseUmaneAuthUser.objects.get(auth_user_id=user.id)
            ruolo = bridge.ruolo_sistema
        except RisorseUmaneAuthUser.DoesNotExist:
            ruolo = None

        if cache is not None:
            cache["ruolo_sistema"] = ruolo
        return ruolo

    @classmethod
    def get_livello_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Restituisce il livello effettivo per un'area funzionale.
        Catena: ruolo_sistema -> override utente area -> profilo reparto -> BLOCCATO."""
        cache_key = f"area:{area_schema_db}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]

        # 1. Check ruolo_sistema
        ruolo = cls.get_ruolo_sistema(user, cache=cache)
        if ruolo == "DISABILITATO":
            result = "BLOCCATO"
        elif ruolo == "ADMIN":
            result = "TUTTO"
        else:
            result = cls._resolve_livello_area(user, area_schema_db, cache=cache)

        if cache is not None:
            cache[cache_key] = result
        return result

    @classmethod
    def get_livello_oggetto(
        cls,
        user: Any,
        app_label: str,
        model_name: str,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Restituisce il livello effettivo per un singolo model.
        Catena: override oggetto -> override area -> profilo reparto -> BLOCCATO."""
        cache_key = f"oggetto:{app_label}.{model_name}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]

        # Check ruolo_sistema prima di tutto
        ruolo = cls.get_ruolo_sistema(user, cache=cache)
        if ruolo == "DISABILITATO":
            result = "BLOCCATO"
        elif ruolo == "ADMIN":
            result = "TUTTO"
        else:
            result = cls._resolve_livello_oggetto(
                user, app_label, model_name, area_schema_db, cache=cache
            )

        if cache is not None:
            cache[cache_key] = result
        return result

    @classmethod
    def check_azione(
        cls,
        user: Any,
        permission_codename: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Verifica se un'azione di processo e' abilitata.
        Catena: ruolo_sistema -> override utente -> profilo reparto -> negata."""
        cache_key = f"azione:{permission_codename}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]

        # 1. Check ruolo_sistema
        ruolo = cls.get_ruolo_sistema(user, cache=cache)
        if ruolo == "DISABILITATO":
            result = False
        elif ruolo == "ADMIN":
            result = True
        else:
            result = cls._resolve_azione(user, permission_codename, cache=cache)

        if cache is not None:
            cache[cache_key] = result
        return result

    @classmethod
    def get_emittenti_ids(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> list[int] | None:
        """Scopo: Restituisce gli ID emittenti fiscali autorizzati per l'utente.
        Restituisce None se l'utente non ha restrizioni (whitelist vuota = tutto)."""
        if cache is not None and "emittenti_ids" in cache:
            return cache["emittenti_ids"]

        from apps.config.models import UserEmittenteFiscale

        ids = list(
            UserEmittenteFiscale.objects.filter(
                auth_user_id=user.id
            ).values_list("emittente_fiscale_id", flat=True)
        )
        result: list[int] | None = ids if ids else None

        if cache is not None:
            cache["emittenti_ids"] = result
        return result

    @classmethod
    def get_area_schema_db(cls, app_label: str, model_name: str) -> str:
        """Scopo: Determina lo schema_db dell'area per un model.
        1. Controlla override in area_model_overrides
        2. Altrimenti usa app_label (che corrisponde allo schema)."""
        from apps.config.models import AreaModelOverride

        override = (
            AreaModelOverride.objects.filter(
                app_label=app_label,
                model_name=model_name,
            )
            .select_related("area")
            .first()
        )

        if override:
            return override.area.schema_db

        return app_label

    @classmethod
    def has_profilo_reparto_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Verifica se il reparto dell'utente ha un profilo per l'area.
        Usato per distinguere 'BLOCCATO da profilo' da 'nessun profilo configurato'."""
        from apps.config.models import ProfiloRepartoArea

        uo_id = cls._get_unita_organizzativa_id(user, cache=cache)
        if uo_id is None:
            return False

        cache_key = f"has_profilo:{area_schema_db}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]

        result = ProfiloRepartoArea.objects.filter(
            unita_organizzativa_id=uo_id,
            area__schema_db=area_schema_db,
        ).exists()

        if cache is not None:
            cache[cache_key] = result
        return result

    # ── Metodi interni di risoluzione ──────────────────────

    @classmethod
    def _resolve_livello_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Risoluzione area per utenti OPERATIVO.
        Catena: UserOverrideArea -> ProfiloRepartoArea -> BLOCCATO."""
        from apps.config.models import ProfiloRepartoArea, UserOverrideArea

        # 1. Override utente su area
        override = (
            UserOverrideArea.objects.filter(
                auth_user_id=user.id,
                area__schema_db=area_schema_db,
            )
            .filter(_today_filter())
            .first()
        )
        if override:
            return override.livello

        # 2. Profilo reparto
        uo_id = cls._get_unita_organizzativa_id(user, cache=cache)
        if uo_id is not None:
            profilo = ProfiloRepartoArea.objects.filter(
                unita_organizzativa_id=uo_id,
                area__schema_db=area_schema_db,
            ).first()
            if profilo:
                return profilo.livello

        # 3. Default sicuro
        return "BLOCCATO"

    @classmethod
    def _resolve_livello_oggetto(
        cls,
        user: Any,
        app_label: str,
        model_name: str,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Risoluzione oggetto per utenti OPERATIVO.
        Catena: UserOverrideOggetto -> get_livello_area."""
        from apps.config.models import UserOverrideOggetto

        # 1. Override utente su oggetto
        override = (
            UserOverrideOggetto.objects.filter(
                auth_user_id=user.id,
                app_label=app_label,
                model_name=model_name,
            )
            .filter(_today_filter())
            .first()
        )
        if override:
            return override.livello

        # 2. Risale alla catena area
        return cls._resolve_livello_area(user, area_schema_db, cache=cache)

    @classmethod
    def _resolve_azione(
        cls,
        user: Any,
        permission_codename: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Risoluzione azione per utenti OPERATIVO.
        Catena: UserOverrideAzione -> ProfiloRepartoAzione -> negata."""
        from apps.config.models import ProfiloRepartoAzione, UserOverrideAzione

        # 1. Override utente su azione
        override = (
            UserOverrideAzione.objects.filter(
                auth_user_id=user.id,
                azione__permission_codename=permission_codename,
            )
            .filter(_today_filter())
            .first()
        )
        if override:
            return override.abilitata

        # 2. Profilo reparto
        uo_id = cls._get_unita_organizzativa_id(user, cache=cache)
        if uo_id is not None:
            profilo = ProfiloRepartoAzione.objects.filter(
                unita_organizzativa_id=uo_id,
                azione__permission_codename=permission_codename,
            ).first()
            if profilo:
                return profilo.abilitata

        # 3. Default: negata
        return False

    @classmethod
    def _get_unita_organizzativa_id(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> int | None:
        """Scopo: Risale alla unita' organizzativa dell'utente
        via bridge risorse_umane_auth_user -> risorse_umane."""
        if cache is not None and "uo_id" in cache:
            return cache["uo_id"]

        from apps.anagrafiche.models import RisorseUmaneAuthUser

        try:
            bridge = RisorseUmaneAuthUser.objects.select_related(
                "risorsa_umana"
            ).get(auth_user_id=user.id)
            uo_id = bridge.risorsa_umana.unita_organizzativa_id
        except RisorseUmaneAuthUser.DoesNotExist:
            uo_id = None

        if cache is not None:
            cache["uo_id"] = uo_id
        return uo_id
