# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Permission class DRF centrale per ZeroErp.
# Risolve automaticamente l'area funzionale dallo schema del model
# e verifica il livello di accesso tramite PermissionResolver.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.core.services.permissions_cache import load_user_cache, save_user_cache
from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver


class ZeroERPPermission(BasePermission):
    """Permission class centrale di Zero ERP.

    Risolve automaticamente l'area funzionale dallo schema del model
    e verifica il livello di accesso tramite PermissionResolver.

    Per ViewSet usa ``view.action`` (list, retrieve, create, ...).
    Per APIView usa ``request.method`` (GET, POST, PUT, ...).

    Le view possono dichiarare:
    - ``area_funzionale = "vendite"`` per indicare l'area quando non c'e' queryset
    - ``<action>_permission = "codename"`` per azioni di processo custom
      (es. ``post_permission = "genera_fatture_lotti"``)
    """

    # Mapping azione ViewSet -> tipo di accesso CRUD richiesto
    ACTION_REQUIRES: dict[str, str] = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }

    # Mapping metodo HTTP -> tipo di accesso (fallback per APIView)
    METHOD_REQUIRES: dict[str, str] = {
        "GET": "view",
        "HEAD": "view",
        "OPTIONS": "view",
        "POST": "add",
        "PUT": "change",
        "PATCH": "change",
        "DELETE": "delete",
    }

    # Scopo: Verifica i permessi di accesso per la richiesta corrente.
    # Per APIView senza action usa il metodo HTTP.
    # Per ViewSet usa l'action. Per azioni custom con attributo
    # <action>_permission, verifica l'azione di processo.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Django superuser bypass
        if user.is_superuser:
            return True

        # Inizializza cache per-request (pre-popolata da Redis L2 se disponibile)
        cache = self._get_cache(request)

        try:
            # Check ruolo_sistema
            ruolo = PermissionResolver.get_ruolo_sistema(user, cache=cache)
            if ruolo == "DISABILITATO":
                self.message = "Utente disabilitato. Contattare l'amministratore."
                return False
            if ruolo == "ADMIN":
                return True

            # Determina l'azione richiesta
            action = getattr(view, "action", None)

            # Azione custom con permesso esplicito
            # (es. run_pipeline_permission = 'genera_fatture_lotti')
            if action:
                action_perm = getattr(view, f"{action}_permission", None)
                if action_perm:
                    result = PermissionResolver.check_azione(
                        user, action_perm, cache=cache
                    )
                    if not result:
                        self.message = "Non hai i permessi per questa operazione."
                    return result

            # Fallback per APIView: controlla <method>_permission
            if not action:
                method = request.method
                if method:
                    method_perm = getattr(
                        view, f"{method.lower()}_permission", None
                    )
                    if method_perm:
                        result = PermissionResolver.check_azione(
                            user, method_perm, cache=cache
                        )
                        if not result:
                            self.message = "Non hai i permessi per questa operazione."
                        return result

            # CRUD standard: determina il tipo di accesso richiesto
            if action:
                required = self.ACTION_REQUIRES.get(action)
            else:
                required = self.METHOD_REQUIRES.get(request.method or "")

            if required is None:
                # Azione sconosciuta -> permetti (safe per azioni custom non CRUD)
                return True

            # Determina area funzionale dal model o dall'attributo della view
            area_schema_db = self._resolve_area(view, cache)
            if area_schema_db is None:
                # Nessun model collegato e nessun area_funzionale dichiarata
                return True

            # Risolvi livello (oggetto o area)
            app_label, model_name = self._get_model_meta(view)
            if app_label and model_name:
                livello = PermissionResolver.get_livello_oggetto(
                    user, app_label, model_name, area_schema_db, cache=cache
                )
            else:
                livello = PermissionResolver.get_livello_area(
                    user, area_schema_db, cache=cache
                )

            allowed_actions = LIVELLO_MAP.get(livello, frozenset())
            if required not in allowed_actions:
                self._set_deny_message(user, ruolo, area_schema_db, cache)
                return False
            return True
        finally:
            self._save_cache_to_redis(request)

    # Scopo: Imposta il messaggio di errore specifico per il diniego.
    # Distingue tra reparto senza profilo e permesso negato generico.
    def _set_deny_message(
        self,
        user: Any,
        ruolo: str | None,
        area_schema_db: str,
        cache: dict[str, Any],
    ) -> None:
        if ruolo == "OPERATIVO" and not PermissionResolver.has_profilo_reparto_area(
            user, area_schema_db, cache=cache
        ):
            self.message = (
                "Il reparto non ha ancora un profilo permessi configurato."
            )
        else:
            self.message = "Non hai i permessi per questa operazione."

    @staticmethod
    def _get_cache(request: Request) -> dict[str, Any]:
        """Scopo: Restituisce o crea la cache permessi per-request.
        Tenta di pre-popolare da Redis (L2) se la cache L1 non esiste."""
        if not hasattr(request, "_zeroerp_perms_cache"):
            user = request.user
            redis_data = load_user_cache(user.id) if user and user.is_authenticated else None
            request._zeroerp_perms_cache = redis_data or {}  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_loaded_from_redis = redis_data is not None  # type: ignore[attr-defined]
        return request._zeroerp_perms_cache  # type: ignore[attr-defined]

    @staticmethod
    def _save_cache_to_redis(request: Request) -> None:
        """Scopo: Persiste la cache per-request su Redis se e' stata arricchita."""
        user = request.user
        if not user or not user.is_authenticated:
            return
        cache_dict = getattr(request, "_zeroerp_perms_cache", None)
        if not cache_dict:
            return
        # Salva solo se la cache non proveniva gia' da Redis invariata
        already_from_redis = getattr(request, "_zeroerp_perms_cache_loaded_from_redis", False)
        if not already_from_redis or len(cache_dict) > 0:
            save_user_cache(user.id, cache_dict)

    @staticmethod
    def _get_model_meta(view: Any) -> tuple[str | None, str | None]:
        """Scopo: Estrae app_label e model_name dal queryset della view."""
        qs = getattr(view, "queryset", None)
        if qs is not None:
            model = qs.model
            return model._meta.app_label, model._meta.model_name
        return None, None

    @classmethod
    def _resolve_area(
        cls, view: Any, cache: dict[str, Any]
    ) -> str | None:
        """Scopo: Determina l'area funzionale dalla view.
        1. Prova dal queryset model (schema DB)
        2. Fallback all'attributo area_funzionale della view."""
        app_label, model_name = cls._get_model_meta(view)
        if app_label and model_name:
            return PermissionResolver.get_area_schema_db(app_label, model_name)

        # Fallback: attributo esplicito sulla view
        return getattr(view, "area_funzionale", None)
