# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Mixin per filtrare queryset in base allo scope emittente fiscale.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from apps.core.services.permissions_resolver import PermissionResolver


class EmittenteFiscaleScopeMixin:
    """Filtra il queryset in base agli emittenti fiscali dell'utente.

    Se l'utente non ha righe in ``user_emittenti_fiscali``, vede tutto.
    Se ha almeno una riga, vede solo gli emittenti autorizzati.

    Uso: impostare ``emittente_field`` nella view con il path
    al campo emittente (es. ``"emittente_fiscale_id"``,
    ``"billing_account__emittente_fiscale_id"``).
    """

    emittente_field: str | None = None

    # Scopo: Filtra il queryset base per scope emittente fiscale.
    # Superuser e SUPER_ADMIN non vengono filtrati. Se l'utente non
    # ha righe in user_emittenti_fiscali, vede tutto.
    def get_queryset(self) -> QuerySet[Any]:
        qs: QuerySet[Any] = super().get_queryset()  # type: ignore[misc]
        user = self.request.user  # type: ignore[attr-defined]

        if user.is_superuser or self.emittente_field is None:
            return qs

        # SUPER_ADMIN bypass: nessun filtro scope
        cache: dict[str, Any] = getattr(
            self.request, "_zeroerp_perms_cache", {}  # type: ignore[attr-defined]
        )
        if PermissionResolver.is_super_admin(user, cache=cache):
            return qs

        emittenti_ids = PermissionResolver.get_emittenti_ids(user, cache=cache)
        if emittenti_ids is None:
            # Nessuna restrizione
            return qs

        filter_kwarg = {f"{self.emittente_field}__in": emittenti_ids}
        return qs.filter(**filter_kwarg)
